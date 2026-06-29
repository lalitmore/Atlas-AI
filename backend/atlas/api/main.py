"""Atlas AI — HTTP API.

A thin FastAPI layer over the ADK pipeline. It runs the same SequentialAgent we built
for `adk web`, but programmatically via the ADK Runner, and streams progress to the
browser over Server-Sent Events (SSE).

Run it:
    uvicorn atlas.api.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from dotenv import load_dotenv

# `adk web` auto-loads each agent folder's .env; uvicorn does NOT. So we load the same
# .env the pipeline already uses, and we do it BEFORE importing any agent — importing
# the pipeline instantiates `settings`, which needs GOOGLE_API_KEY present in the env.
load_dotenv(Path(__file__).resolve().parents[1] / "agents" / "pipeline" / ".env")

from fastapi import FastAPI  # noqa: E402  — imports intentionally follow load_dotenv
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sse_starlette.sse import EventSourceResponse  # noqa: E402
from google.genai import types  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402

from atlas.agents.pipeline.agent import root_agent  # noqa: E402

APP_NAME = "atlas"
USER_ID = "web_user"

# The Runner and session service are STATELESS and live for the whole process. Create
# them ONCE and reuse across requests; per-request isolation comes from session_id.
session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)

app = FastAPI(title="Atlas AI API")

# The Next.js dev server runs on :3000; let it call us from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlanRequest(BaseModel):
    """The traveler's free-text request — exactly what they'd type into the box."""
    request: str


# Maps each pipeline agent (event.author) to a clean, user-facing stage. The frontend
# only ever sees these named stages plus a final payload — never ADK's event shape.
STAGE_LABELS: dict[str, tuple[str, str]] = {
    "intake_agent": ("intake", "Understanding your request"),
    "grounded_research_agent": ("research", "Researching destinations, events & prices"),
    "structured_research_agent": ("structure", "Organizing the findings"),
    "itinerary_agent": ("itinerary", "Writing your day-by-day plan"),
}
# The route optimizer is an after-agent callback, so it has no agent events of its own.
# We surface it by watching for the moment its state write lands in the stream.
OPTIMIZE_STAGE = ("optimize", "Optimizing the route")


async def plan_event_stream(user_request: str):
    """Run the pipeline once and yield clean SSE events: a `stage` per pipeline step,
    a final `complete`, or an `error`."""
    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    message = types.Content(role="user", parts=[types.Part(text=user_request)])

    last_stage: str | None = None
    optimize_emitted = False
    try:
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=message
        ):
            # The optimizer writes `optimized_route` to state in an after-agent callback;
            # that write rides along as a state_delta on the next event — right between
            # structuring and the itinerary write. Emit the optimize step the instant we
            # see it. Checked BEFORE the author stages so it always lands in the right order.
            if (
                not optimize_emitted
                and event.actions
                and event.actions.state_delta
                and "optimized_route" in event.actions.state_delta
            ):
                optimize_emitted = True
                yield {
                    "event": "stage",
                    "data": json.dumps({"name": OPTIMIZE_STAGE[0], "label": OPTIMIZE_STAGE[1]}),
                }

            stage = STAGE_LABELS.get(event.author)
            if stage and stage[0] != last_stage:
                last_stage = stage[0]
                yield {
                    "event": "stage",
                    "data": json.dumps({"name": stage[0], "label": stage[1]}),
                }

        session = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        yield {
            "event": "complete",
            "data": json.dumps(
                {
                    "trip_brief": session.state.get("trip_brief"),
                    "optimized_route": session.state.get("optimized_route"),
                    "itinerary": session.state.get("itinerary"),
                }
            ),
        }
    except Exception as exc:
        yield {"event": "error", "data": json.dumps({"message": str(exc)})}

@app.post("/api/plan")
async def plan(req: PlanRequest):
    """Kick off a planning run; stream progress + the final itinerary over SSE."""
    return EventSourceResponse(plan_event_stream(req.request))


@app.get("/api/health")
async def health():
    return {"status": "ok"}