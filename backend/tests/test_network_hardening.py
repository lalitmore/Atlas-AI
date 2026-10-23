"""Exercise real ADK stages/HTTP contracts with offline provider responses and failures."""
import asyncio
import json
import logging
import os
import socket

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from google.adk.models import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from google.genai.errors import APIError

from atlas import models
from atlas.api import guardrails
from atlas.api.errors import RedactTraceback
from atlas.config import Settings, settings, validate_runtime_config
from japan_fixture import JAPAN_REQUEST, japan_model_responses


def sse_events(response):
    events = []
    for frame in response.text.replace("\r\n", "\n").split("\n\n"):
        fields = dict(line.split(": ", 1) for line in frame.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def install_local_responses(monkeypatch):
    responses = iter(japan_model_responses())
    calls = []

    async def provider(self, llm_request, stream=False):
        calls.append(self.model)
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=next(responses))]))

    monkeypatch.setattr(Gemini, "generate_content_async", provider)
    return calls


def test_ten_day_japan_pipeline_has_ordered_unique_stage_starts(monkeypatch):
    from atlas.api.main import app
    calls = install_local_responses(monkeypatch)
    with TestClient(app) as client:
        response = client.post("/api/plan", json={"request": JAPAN_REQUEST})
    events = sse_events(response)
    assert [payload["name"] for event, payload in events if event == "stage"] == [
        "intake", "research", "structure", "optimize", "itinerary",
    ]
    assert [event for event, _ in events] == ["stage"] * 5 + ["complete"]
    result = events[-1][1]
    assert len(calls) == 4
    assert result["trip_brief"]["party_size"] == 2
    assert result["trip_brief"]["constraints"]["dietary_restrictions"] == ["vegetarian"]
    assert result["itinerary"]["total_days"] == len(result["itinerary"]["day_plans"]) == 10
    assert sum(stop["days"] for stop in result["optimized_route"]) == 10


def test_start_reaches_stream_before_first_call_and_dns_maps_safely(monkeypatch, caplog):
    from atlas.api.main import plan_event_stream
    calls = []
    delays = []

    async def provider(self, llm_request, stream=False):
        calls.append(self.model)
        raise socket.gaierror(socket.EAI_NONAME, "offline DNS failure")
        yield  # async generator, matching the SDK adapter contract

    async def sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(Gemini, "generate_content_async", provider)
    monkeypatch.setattr(models, "retry_sleep", sleep)

    async def run():
        await guardrails.acquire_slot()
        stream = plan_event_stream(JAPAN_REQUEST)
        first = await anext(stream)
        assert first["event"] == "stage" and json.loads(first["data"])["name"] == "intake"
        assert calls == []  # The first start is yielded before contacting Gemini.
        error = await anext(stream)
        assert error["event"] == "error"
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
        return json.loads(error["data"])

    with caplog.at_level(logging.ERROR):
        error = asyncio.run(run())
    assert len(calls) == 3 and delays == [1.0, 2.0]
    assert error == {
        "code": "AI_CONNECTION_ERROR",
        "message": "Atlas couldn't reach the AI service. Check your connection and try again.",
        "stage": "intake",
    }
    assert "Traceback" in caplog.text and "offline DNS failure" in caplog.text
    assert "host=generativelanguage.googleapis.com" in caplog.text and "stage=intake" in caplog.text
    assert "offline DNS failure" not in error["message"]


def test_optimizer_start_precedes_optimization_failure(monkeypatch):
    from atlas.agents import optimizer
    from atlas.api.main import app
    calls = install_local_responses(monkeypatch)

    def fail(callback_context):
        raise RuntimeError("offline optimizer failure")

    monkeypatch.setattr(optimizer, "attach_optimized_route", fail)
    with TestClient(app) as client:
        events = sse_events(client.post("/api/plan", json={"request": JAPAN_REQUEST}))
    assert [payload["name"] for event, payload in events if event == "stage"] == [
        "intake", "research", "structure", "optimize",
    ]
    assert events[-1] == ("error", {
        "code": "PLANNING_FAILED",
        "message": "Atlas couldn't finish planning this trip. Please try again.",
        "stage": "optimize",
    })
    assert len(calls) == 3


@pytest.mark.parametrize("status,attempts", [
    (400, 1), (401, 1), (403, 1), (404, 1), (408, 1), (429, 3),
    (500, 1), (502, 1), (503, 3), (504, 1),
])
def test_only_429_and_503_statuses_are_retried(monkeypatch, status, attempts):
    calls = []
    delays = []

    async def provider(self, llm_request, stream=False):
        calls.append(1)
        assert llm_request.config.http_options.timeout == 30_000
        assert llm_request.config.http_options.retry_options.attempts == 1
        raise APIError(status, {"error": {"message": "offline API failure"}})
        yield

    async def sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(Gemini, "generate_content_async", provider)
    monkeypatch.setattr(models, "retry_sleep", sleep)

    async def run():
        async for _ in models.build_model().generate_content_async(LlmRequest()):
            pass

    with pytest.raises(APIError):
        asyncio.run(run())
    assert len(calls) == attempts and len(delays) == attempts - 1


@pytest.mark.parametrize("error", [socket.gaierror(8, "offline DNS"), httpx.ConnectError("offline connection"),
    httpx.ReadError("offline read"), httpx.RemoteProtocolError("offline peer closed")])
def test_transient_failure_can_recover_without_replaying_output(monkeypatch, error):
    calls = []

    async def provider(self, llm_request, stream=False):
        calls.append(1)
        if len(calls) == 1:
            raise error
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="recovered")]))

    async def sleep(delay):
        pass

    monkeypatch.setattr(Gemini, "generate_content_async", provider)
    monkeypatch.setattr(models, "retry_sleep", sleep)

    async def run():
        return [response async for response in models.build_model().generate_content_async(LlmRequest())]

    result = asyncio.run(run())
    assert len(result) == 1 and len(calls) == 2


def test_partially_emitted_stream_is_not_retried(monkeypatch):
    calls = []

    async def provider(self, llm_request, stream=False):
        calls.append(1)
        yield LlmResponse(partial=True)
        raise httpx.ConnectError("offline connection after output")

    monkeypatch.setattr(Gemini, "generate_content_async", provider)

    async def run():
        async for _ in models.build_model().generate_content_async(LlmRequest(), stream=True):
            pass

    with pytest.raises(httpx.ConnectError):
        asyncio.run(run())
    assert calls == [1]


def test_cancellation_is_not_retried_or_mapped(monkeypatch):
    from atlas.api.main import plan_event_stream
    calls = []

    async def provider(self, llm_request, stream=False):
        calls.append(1)
        raise asyncio.CancelledError()
        yield

    monkeypatch.setattr(Gemini, "generate_content_async", provider)

    async def run():
        await guardrails.acquire_slot()
        stream = plan_event_stream(JAPAN_REQUEST)
        assert (await anext(stream))["event"] == "stage"
        await anext(stream)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run())
    assert calls == [1]
    assert guardrails._sem._value == guardrails.MAX_CONCURRENT


def test_missing_key_refuses_fastapi_startup(monkeypatch):
    from atlas.api.main import app
    monkeypatch.setattr(settings, "google_api_key", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY is missing"):
        with TestClient(app):
            pytest.fail("The app should not accept requests without an API key")


def test_mode_whitespace_is_normalized_for_actual_sdk_environment(monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE ")
    config = Settings(_env_file=None)
    with caplog.at_level(logging.INFO):
        validate_runtime_config(config)
    assert config.google_genai_use_vertexai is False
    assert os.environ["GOOGLE_GENAI_USE_VERTEXAI"] == "false"
    assert "backend=Developer API" in caplog.text
    assert "offline-test-key" not in caplog.text


def test_conflicting_enterprise_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_ENTERPRISE", "true")
    with pytest.raises(RuntimeError, match="conflicts"):
        validate_runtime_config(Settings(_env_file=None))


@pytest.mark.parametrize("location,project", [("", "example"), ("us central1", "example"), ("us-central1", "")])
def test_vertex_misconfiguration_fails_before_calls(monkeypatch, location, project):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", location)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", project)
    with pytest.raises(RuntimeError, match="Vertex mode requires"):
        validate_runtime_config(Settings(_env_file=None))


def test_http_validation_and_rate_limit_use_same_error_shape(monkeypatch):
    from atlas.api.main import app
    with TestClient(app) as client:
        response = client.post("/api/plan", json={"request": " "})
        assert response.status_code == 400
        assert response.json()["detail"] == {
            "code": "INVALID_REQUEST", "message": "Tell Atlas about your trip first.", "stage": None,
        }
        response = client.post("/api/plan", json={"request": 123})
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_REQUEST"

        def limit(*args):
            raise HTTPException(429, "Offline limit test")

        monkeypatch.setattr(guardrails, "precheck", limit)
        response = client.post("/api/plan", json={"request": JAPAN_REQUEST})
        assert response.status_code == 429
        assert response.json()["detail"] == {
            "code": "RATE_LIMITED", "message": "Offline limit test", "stage": None,
        }


def test_traceback_redacts_key_and_proxy_credentials(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-private-key")
    monkeypatch.setenv("HTTPS_PROXY", "http://user:password@proxy.invalid:8080")
    try:
        raise ValueError("fake-private-key https://user:password@proxy.invalid:8080?key=other-secret")
    except ValueError:
        import sys
        record = logging.LogRecord("test", logging.ERROR, __file__, 1, "offline error", (), sys.exc_info())
    RedactTraceback().filter(record)
    text = logging.Formatter().format(record)
    assert "Traceback" in text and "ValueError" in text
    assert "fake-private-key" not in text and "password" not in text and "other-secret" not in text
