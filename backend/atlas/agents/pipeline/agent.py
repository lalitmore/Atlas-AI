"""The full Atlas planning pipeline: intake -> grounded research -> structured
research (which also computes the optimized route) -> itinerary writer."""
from __future__ import annotations

from google.adk.agents import SequentialAgent

from atlas.agents.intake.agent import build_intake_agent
from atlas.agents.research.grounded import build_grounded_research_agent
from atlas.agents.research.structured import build_structured_research_agent
from atlas.agents.itinerary.agent import build_itinerary_agent

root_agent = SequentialAgent(
    name="atlas_pipeline",
    description="Understand the request, research the web, optimize the route, write the itinerary.",
    sub_agents=[
        build_intake_agent(),
        build_grounded_research_agent(),
        build_structured_research_agent(),
        build_itinerary_agent(),
    ],
)