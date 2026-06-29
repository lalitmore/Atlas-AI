"""Deterministic route optimization, injected via an agent callback.

ADK 2.0 routes custom execution logic into Before/After-AgentCallbacks rather than
agent method overrides. Running it here means it executes unconditionally — no LLM
decides whether to invoke it — and always writes `optimized_route` to state."""
from __future__ import annotations

import json
from typing import Optional

from google.genai import types
from google.adk.agents.callback_context import CallbackContext

from atlas.optimization import optimize_route


def _as_dict(value) -> dict:
    """State values may be stored as a dict or a JSON string; normalize to dict."""
    if isinstance(value, str):
        return json.loads(value)
    return value or {}


def attach_optimized_route(callback_context: CallbackContext) -> Optional[types.Content]:
    """Compute the optimized route from research + brief, store it in state, and
    return None so the host agent proceeds normally."""
    research = _as_dict(callback_context.state.get("destination_research"))
    brief = _as_dict(callback_context.state.get("trip_brief"))

    candidate_areas = research.get("candidate_areas", [])
    total_days = int(brief.get("duration_days", len(candidate_areas) or 1))

    areas = [
        {
            "name": a.get("name", ""),
            "region": a.get("region", ""),
            "latitude": a["latitude"],
            "longitude": a["longitude"],
            "weight": len(a.get("matched_interests", [])) or 1,
        }
        for a in candidate_areas
        if "latitude" in a and "longitude" in a
    ]

    callback_context.state["optimized_route"] = optimize_route(areas, total_days)
    return None