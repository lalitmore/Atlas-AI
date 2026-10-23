"""One bounded retry policy for every Gemini stage, before any output is emitted."""
from __future__ import annotations

from asyncio import sleep as retry_sleep
import logging

from google.adk.models import Gemini
from google.genai import types

from atlas.api.errors import RedactTraceback, is_retryable
from atlas.config import settings

logger = logging.getLogger(__name__)
logger.addFilter(RedactTraceback())
MAX_RETRIES = 2
INITIAL_RETRY_DELAY = 1.0
# Disable the SDK's nested retry loop; the adapter below also handles raw DNS errors.
RETRY_OPTIONS = types.HttpRetryOptions(attempts=1)


class ResilientGemini(Gemini):
    async def generate_content_async(self, llm_request, stream=False):
        for attempt in range(MAX_RETRIES + 1):
            emitted = False
            # Preprocessing may append content/config. Start each attempt from the same request.
            request = llm_request.model_copy(update={
                "contents": [content.model_copy(deep=True) for content in llm_request.contents],
                "config": llm_request.config.model_copy(deep=True),
            })
            if request.config.http_options is None:
                request.config.http_options = types.HttpOptions()
            request.config.http_options.timeout = 30_000
            request.config.http_options.retry_options = RETRY_OPTIONS
            try:
                async for response in super().generate_content_async(request, stream=stream):
                    emitted = True
                    yield response
                return
            except Exception as exc:
                # Never replay a stream after partial output, nor retry auth/validation errors.
                if emitted or attempt == MAX_RETRIES or not is_retryable(exc):
                    raise
                delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    "Transient Gemini failure; retry %s/%s in %.1fs (%s)",
                    attempt + 1, MAX_RETRIES, delay, type(exc).__name__,
                )
                await retry_sleep(delay)


def build_model(model_name: str | None = None) -> Gemini:
    return ResilientGemini(model=model_name or settings.default_model, retry_options=RETRY_OPTIONS)
