"""The Intake agent: free-text travel request -> validated TripBrief.

Exposes a factory so the agent can be reused as a building block in a pipeline
without sharing one instance across parents. Still exports `root_agent` so the
intake folder stays runnable on its own in `adk web`."""
from __future__ import annotations

from google.adk.agents import LlmAgent

from atlas.models import build_model
from atlas.schemas import TripBrief
from atlas.agents.intake.prompt import INTAKE_INSTRUCTION


def build_intake_agent() -> LlmAgent:
    """Construct a fresh Intake agent instance."""
    return LlmAgent(
        name="intake_agent",
        model=build_model(),
        description="Parses a traveler's free-text request into a structured, validated TripBrief.",
        instruction=INTAKE_INSTRUCTION,
        output_schema=TripBrief,
        output_key="trip_brief",
        # Inside a multi-agent pipeline, keep a schema agent from handing off
        # control (which would bypass schema enforcement). Harmless standalone.
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )


# Standalone entry point so `adk web atlas/agents` can still run intake alone.
root_agent = build_intake_agent()