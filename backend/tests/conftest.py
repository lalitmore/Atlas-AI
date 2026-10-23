"""Tests are offline and use a dummy credential even when a real .env exists."""
import asyncio
import os
from datetime import date

import pytest

# Set these before importing Atlas: neither SDK nor settings should use a real test key.
os.environ["GOOGLE_API_KEY"] = "offline-test-key"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
# Local availability fallbacks must not change the offline test configuration.
os.environ["DEFAULT_MODEL"] = "gemini-3.5-flash-lite"
os.environ["ITINERARY_MODEL"] = "gemini-3.6-flash"
os.environ.pop("GOOGLE_GENAI_USE_ENTERPRISE", None)


@pytest.fixture(autouse=True)
def isolate_api_state(monkeypatch):
    from atlas.api import guardrails
    from atlas.config import settings
    monkeypatch.setattr(settings, "google_api_key", "offline-test-key")
    monkeypatch.setattr(settings, "enable_search_grounding", False)
    monkeypatch.setattr(settings, "google_genai_use_vertexai", False)
    monkeypatch.setattr(guardrails, "_ip_hits", guardrails.defaultdict(guardrails.deque))
    monkeypatch.setattr(guardrails, "_global", {"day": date.today(), "count": 0})
    monkeypatch.setattr(guardrails, "_sem", asyncio.Semaphore(guardrails.MAX_CONCURRENT))
