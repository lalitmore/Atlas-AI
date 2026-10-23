"""Exercise the real API and ADK pipeline with local, deterministic model responses."""
import json

from fastapi.testclient import TestClient
from google.adk.models import Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from atlas.config import settings
from atlas.schemas import DestinationResearch, Itinerary, TripBrief


def test_plan_stream_with_free_tier_configuration(monkeypatch):
    monkeypatch.setattr(settings, "enable_search_grounding", False)
    monkeypatch.setattr(settings, "default_model", "gemini-3.5-flash-lite")
    responses = iter([
        TripBrief(destination="Japan", duration_days=2).model_dump_json(),
        "General knowledge: Tokyo has museums and parks. Verify hours before visiting.",
        DestinationResearch.model_validate({
            "destination": "Japan",
            "summary": "Two days in Tokyo.",
            "candidate_areas": [{
                "name": "Tokyo", "region": "Kanto", "latitude": 35.68,
                "longitude": 139.69, "why_it_fits": "Museums and parks.",
            }],
            "needs_grounding": ["Current opening hours"],
        }).model_dump_json(),
        Itinerary.model_validate({
            "destination": "Japan", "total_days": 2, "summary": "Explore Tokyo.",
            "day_plans": [
                {"day_number": day, "area": "Tokyo", "title": "Museums and parks"}
                for day in (1, 2)
            ],
            "transport": [{
                "area": "Tokyo", "getting_here": "Train from the airport.",
                "getting_around": "Local trains.",
            }],
            "open_items": ["Verify current opening hours."],
        }).model_dump_json(),
    ])
    called_models = []

    async def local_model(self, llm_request, stream=False):
        called_models.append(self.model)
        assert not any(
            tool.google_search is not None for tool in (llm_request.config.tools or [])
        )
        yield LlmResponse(content=types.Content(
            role="model", parts=[types.Part(text=next(responses))],
        ))

    monkeypatch.setattr(Gemini, "generate_content_async", local_model)
    # Import after setting configuration so the API builds its actual pipeline with it.
    from atlas.api.main import app

    with TestClient(app) as client:
        response = client.post("/api/plan", json={"request": "Two days in Tokyo."})

    assert response.status_code == 200
    frames = response.text.replace("\r\n", "\n").split("\n\n")
    events = []
    for frame in frames:
        fields = dict(line.split(": ", 1) for line in frame.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))

    assert not [payload for event, payload in events if event == "error"]
    assert {payload["name"] for event, payload in events if event == "stage"} == {
        "intake", "research", "structure", "optimize", "itinerary",
    }
    complete = next(payload for event, payload in events if event == "complete")
    assert complete["research_grounded"] is False
    assert complete["itinerary"]["total_days"] == 2
    assert sum(stop["days"] for stop in complete["optimized_route"]) == 2
    assert called_models == ["gemini-3.5-flash-lite"] * 3 + [settings.itinerary_model]
