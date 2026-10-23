"""Public error contracts and safe server-side diagnostics."""
from __future__ import annotations

import logging
import os
import re
import socket
import traceback
from urllib.parse import urlsplit

import httpx
from google.genai.errors import APIError


def exception_chain(exc: BaseException):
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def api_status(exc: BaseException) -> int | None:
    for cause in exception_chain(exc):
        if isinstance(cause, APIError):
            return cause.code
        if isinstance(cause, httpx.HTTPStatusError):
            return cause.response.status_code
    return None


def is_network_error(exc: BaseException) -> bool:
    return any(isinstance(cause, (
        socket.gaierror, ConnectionError, TimeoutError,
        httpx.NetworkError, httpx.ProxyError, httpx.TimeoutException, httpx.RemoteProtocolError,
    )) for cause in exception_chain(exc))


def is_retryable(exc: BaseException) -> bool:
    status = api_status(exc)
    # An auth/validation response must never be retried, even if it wraps another error.
    return status in {429, 503} if status is not None else is_network_error(exc)


def public_error(exc: BaseException, stage: str | None = None) -> dict:
    status = api_status(exc)
    if status == 429:
        code, message = "AI_RATE_LIMITED", "The AI service is busy or its free quota is used up. Please try again later."
    elif status in {401, 403}:
        code, message = "AI_AUTH_ERROR", "Atlas couldn't authenticate with the AI service. Check the local API key configuration."
    elif status == 404:
        code, message = "AI_MODEL_UNAVAILABLE", "The configured AI model is unavailable. Check Atlas's model configuration."
    elif status == 503:
        code, message = "AI_UNAVAILABLE", "The AI service is temporarily unavailable. Please try again later."
    elif status is not None:
        code, message = "AI_REQUEST_FAILED", "The AI service couldn't process this trip. Please try again."
    elif is_network_error(exc):
        code, message = "AI_CONNECTION_ERROR", "Atlas couldn't reach the AI service. Check your connection and try again."
    else:
        code, message = "PLANNING_FAILED", "Atlas couldn't finish planning this trip. Please try again."
    return {"code": code, "message": message, "stage": stage}


def redact(text: str) -> str:
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                 "http_proxy", "https_proxy", "all_proxy"):
        value = os.environ.get(name)
        if value:
            text = text.replace(value, "[redacted]")
    text = re.sub(r"(?i)(https?://)[^/\s:@]+:[^/\s@]+@", r"\1[redacted]@", text)
    return re.sub(r"(?i)([?&](?:key|api_key|token)=)[^&\s]+", r"\1[redacted]", text)


class RedactTraceback(logging.Filter):
    """Keep full call stacks while stripping credentials from exception text/URLs."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        if record.exc_info:
            record.exc_text = redact("".join(traceback.format_exception(*record.exc_info)))
        return True


def proxy_hosts() -> str:
    hosts = set()
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        value = os.environ.get(name)
        if value:
            try:
                hosts.add(urlsplit(value).hostname or "invalid-proxy-host")
            except ValueError:
                hosts.add("invalid-proxy-host")
    return ",".join(sorted(hosts)) or "none"
