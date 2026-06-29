"""Grounded Research agent: searches the web for current facts. Returns text only —
no output_schema, because grounding and controlled generation can't coexist."""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from atlas.models import build_model
from atlas.agents.research.prompt import GROUNDED_RESEARCH_INSTRUCTION


def build_grounded_research_agent() -> LlmAgent:
    return LlmAgent(
        name="grounded_research_agent",
        model=build_model(),
        description="Uses Google Search to gather current facts relevant to the trip.",
        instruction=GROUNDED_RESEARCH_INSTRUCTION,
        tools=[google_search],            # grounding tool — NO output_schema alongside it
        output_key="research_findings",   # store the grounded text for the next stage
    )