"""Research synthesis agent: turns grounded findings into structured DestinationResearch.
No tools — only this agent carries the output_schema."""
from __future__ import annotations

from google.adk.agents import LlmAgent

from atlas.models import build_model
from atlas.schemas import DestinationResearch
from atlas.agents.research.prompt import STRUCTURED_RESEARCH_INSTRUCTION
from atlas.agents.route_callback import attach_optimized_route


def build_structured_research_agent() -> LlmAgent:
    return LlmAgent(
        name="structured_research_agent",
        model=build_model(),
        description="Synthesizes grounded findings into a structured DestinationResearch.",
        instruction=STRUCTURED_RESEARCH_INSTRUCTION,
        output_schema=DestinationResearch,
        output_key="destination_research",
        after_agent_callback=attach_optimized_route,   # NEW: compute the route deterministically
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )