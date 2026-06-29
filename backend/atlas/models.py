"""Centralized, resilient LLM configuration.

Every agent builds its model here, so retry/backoff behavior is uniform across the whole
pipeline. We wrap the model name (from settings) in ADK's Gemini adapter with
HttpRetryOptions, so transient failures — short-window 429s and 5xx server errors — are
retried automatically at the HTTP layer, retrying ONLY the failed call.
"""
from __future__ import annotations

from google.adk.models import Gemini
from google.genai import types

from atlas.config import settings

# Exponential backoff + jitter. This rescues the two common live-demo failures: a
# short-window 429 (too many requests in the last minute) and a 503 (Gemini briefly
# overloaded). It deliberately does NOT wait out a full daily-quota exhaustion — those
# attempts exhaust within a couple of minutes and surface the error, which is correct.
RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=5,          # up to 5 tries after the first failure
    initial_delay=2.0,   # ~2s before the first retry
    max_delay=60.0,      # never wait more than 60s between tries
    exp_base=2.0,        # double the delay each round (2s → 4s → 8s → ...)
    jitter=0.2,          # ±20% randomness so parallel calls don't retry in lockstep
    http_status_codes=[408, 429, 500, 502, 503, 504],
)


# def build_model() -> Gemini:
#     """A fresh, retry-configured Gemini adapter for the model named in settings."""
#     return Gemini(model=settings.default_model, retry_options=RETRY_OPTIONS)

def build_model(model_name: str | None = None) -> Gemini:
    """A fresh, retry-configured Gemini adapter. Pass model_name to override the default
    (e.g. run a reasoning-heavy stage on full Flash while the rest stay on Flash-Lite)."""
    return Gemini(model=model_name or settings.default_model, retry_options=RETRY_OPTIONS)