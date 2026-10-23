"""Observe requests at the SDK boundary, after actual ADK preprocessing."""
import asyncio
import pytest

from fastapi.testclient import TestClient
from google.genai import types
from google.genai.models import AsyncModels
from google.adk.models.llm_request import LlmRequest

from atlas.models import build_model
from japan_fixture import JAPAN_REQUEST, japan_model_responses


def response(text):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=[types.Part(text=text)]),
        finish_reason="STOP",
    )])


@pytest.mark.parametrize("grounding", [False, True])
def test_sequential_pipeline_requests_end_in_user_at_sdk_boundary(monkeypatch, grounding):
    from google.adk.agents import SequentialAgent
    from google.adk.runners import Runner
    from atlas.config import settings
    from atlas.agents.intake.agent import build_intake_agent
    from atlas.agents.research.grounded import build_grounded_research_agent
    from atlas.agents.research.structured import build_structured_research_agent
    from atlas.agents.optimizer import build_route_optimizer
    from atlas.agents.itinerary.agent import build_itinerary_agent
    monkeypatch.setattr(settings, "enable_search_grounding", grounding)
    outputs = iter(japan_model_responses())
    captured = []

    async def sdk_generate(self, *, model, contents, config):
        captured.append((model, [content.role for content in contents]))
        assert contents and contents[-1].role == "user"
        if len(captured) == 2:
            assert any(tool.google_search is not None for tool in (config.tools or [])) is grounding
        return response(next(outputs))

    monkeypatch.setattr(AsyncModels, "generate_content", sdk_generate)
    from atlas.api import main
    pipeline = SequentialAgent(name="atlas_pipeline", sub_agents=[
        build_intake_agent(), build_grounded_research_agent(),
        build_structured_research_agent(), build_route_optimizer(), build_itinerary_agent(),
    ])
    assert [a.name for a in pipeline.sub_agents] == [a.name for a in main.root_agent.sub_agents]
    monkeypatch.setattr(main, "runner", Runner(
        app_name=main.APP_NAME, agent=pipeline, session_service=main.session_service,
    ))
    with TestClient(main.app) as client:
        result = client.post("/api/plan", json={"request": JAPAN_REQUEST})
    assert "event: complete" in result.text
    assert "event: error" not in result.text
    assert [model for model, _ in captured] == ["gemini-3.5-flash-lite"] * 3 + ["gemini-3.6-flash"]
    print("SDK request roles:", captured)


def test_adk_adds_user_turn_after_trailing_model_without_dropping_history(monkeypatch):
    captured = []

    async def sdk_generate(self, *, model, contents, config):
        captured.extend(contents)
        return response("Done.")

    monkeypatch.setattr(AsyncModels, "generate_content", sdk_generate)
    request = LlmRequest(model="gemini-3.5-flash-lite", contents=[
        types.Content(role="user", parts=[types.Part(text="Original request")]),
        types.Content(role="model", parts=[types.Part(text="Previous model output")]),
    ])

    async def run():
        return [event async for event in build_model().generate_content_async(request)]

    asyncio.run(run())
    assert [content.role for content in captured] == ["user", "model", "user"]
    assert captured[1].parts[0].text == "Previous model output"
    assert "Continue processing" in captured[-1].parts[0].text
    assert len(request.contents) == 2  # Retry adapter does not mutate caller history.
