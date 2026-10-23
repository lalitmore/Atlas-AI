"""The Itinerary writer: optimized route + research -> structured day-by-day Itinerary."""
from __future__ import annotations

from google.adk.agents import LlmAgent

from atlas.models import build_model
from atlas.config import settings
from atlas.agents.progress import mark_stage_started
from atlas.schemas import Itinerary
from atlas.agents.itinerary.prompt import ITINERARY_INSTRUCTION


def build_itinerary_agent() -> LlmAgent:
    return LlmAgent(
        name="itinerary_agent",
        model=build_model(settings.itinerary_model),
        before_agent_callback=mark_stage_started,
        description="Writes the day-by-day itinerary from the optimized route and research.",
        instruction=ITINERARY_INSTRUCTION,
        output_schema=Itinerary,
        output_key="itinerary",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
