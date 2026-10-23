"""A deterministic pipeline stage, with a start event before route computation."""
from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions

from atlas.agents.progress import mark_stage_started
from atlas.agents.route_callback import attach_optimized_route


class RouteOptimizer(BaseAgent):
    async def _run_async_impl(self, ctx):
        actions = EventActions()
        callback_context = CallbackContext(ctx, event_actions=actions)
        attach_optimized_route(callback_context)
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=actions,
        )


def build_route_optimizer() -> BaseAgent:
    return RouteOptimizer(name="route_optimizer", before_agent_callback=mark_stage_started)
