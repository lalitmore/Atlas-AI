"""ADK start markers are yielded before an agent can make an outbound call."""
from __future__ import annotations

from google.adk.agents.callback_context import CallbackContext

STAGE_STATE_KEY = "atlas_stage"
STAGE_LABELS = {
    "intake_agent": ("intake", "Understanding your request"),
    "grounded_research_agent": ("research", "Exploring destinations & travel options"),
    "structured_research_agent": ("structure", "Organizing the findings"),
    "route_optimizer": ("optimize", "Optimizing the route"),
    "itinerary_agent": ("itinerary", "Writing your day-by-day plan"),
}


def mark_stage_started(callback_context: CallbackContext):
    name, label = STAGE_LABELS[callback_context.agent_name]
    callback_context.state[STAGE_STATE_KEY] = {"name": name, "label": label}
