"""Destination research, with live Search only when explicitly enabled."""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from atlas.models import build_model
from atlas.agents.progress import mark_stage_started
from atlas.config import settings
from atlas.agents.research.prompt import (
    GENERAL_RESEARCH_INSTRUCTION,
    GROUNDED_RESEARCH_INSTRUCTION,
)


def build_grounded_research_agent() -> LlmAgent:
    grounded = settings.enable_search_grounding
    return LlmAgent(
        name="grounded_research_agent",
        model=build_model(),
        before_agent_callback=mark_stage_started,
        description=(
            "Uses Google Search to gather current facts relevant to the trip."
            if grounded else "Suggests destinations from general knowledge without live search."
        ),
        instruction=GROUNDED_RESEARCH_INSTRUCTION if grounded else GENERAL_RESEARCH_INSTRUCTION,
        tools=[google_search] if grounded else [],
        output_key="research_findings",   # store the grounded text for the next stage
    )
