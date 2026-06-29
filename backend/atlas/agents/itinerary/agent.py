"""The Itinerary writer: optimized route + research -> structured day-by-day Itinerary."""
from __future__ import annotations

from google.adk.agents import LlmAgent

from atlas.models import build_model
from atlas.schemas import Itinerary
from atlas.agents.itinerary.prompt import ITINERARY_INSTRUCTION


def build_itinerary_agent() -> LlmAgent:
    return LlmAgent(
        name="itinerary_agent",
        #model=build_model(),
        model=build_model("gemini-2.5-flash"),
        description="Writes the day-by-day itinerary from the optimized route and research.",
        instruction=ITINERARY_INSTRUCTION,
        output_schema=Itinerary,
        output_key="itinerary",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )