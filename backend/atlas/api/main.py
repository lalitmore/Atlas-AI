"""FastAPI + SSE interface for the Atlas planning pipeline.

Run: uvicorn atlas.api.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# ADK's CLI loads this file automatically; uvicorn must do so before agent imports.
load_dotenv(Path(__file__).resolve().parents[1] / "agents" / "pipeline" / ".env")

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.encoders import jsonable_encoder  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sse_starlette.sse import EventSourceResponse  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from atlas.agents.pipeline.agent import root_agent  # noqa: E402
from atlas.agents.progress import STAGE_STATE_KEY  # noqa: E402
from atlas.api import guardrails  # noqa: E402
from atlas.api.errors import RedactTraceback, proxy_hosts, public_error  # noqa: E402
from atlas.config import settings, validate_runtime_config  # noqa: E402

logger = logging.getLogger(__name__)
logger.addFilter(RedactTraceback())
APP_NAME = "atlas"
USER_ID = "web_user"
session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime_config()
    yield


app = FastAPI(title="Atlas AI API", lifespan=lifespan)
_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: HTTPException):
    code = "RATE_LIMITED" if exc.status_code == 429 else "INVALID_REQUEST"
    detail = exc.detail if isinstance(exc.detail, dict) else {
        "code": code, "message": str(exc.detail), "stage": None,
    }
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": {
        "code": "INVALID_REQUEST", "message": "Send a trip description as text.", "stage": None,
    }})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Atlas HTTP request failed path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": public_error(exc)})


class PlanRequest(BaseModel):
    request: str


async def plan_event_stream(user_request: str):
    """Emit real stage starts, then a result or a public error with its failing stage."""
    session_id = str(uuid.uuid4())
    last_stage: str | None = None
    emitted_stages: set[str] = set()
    try:
        await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id,
        )
        message = types.Content(role="user", parts=[types.Part(text=user_request)])
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=message,
        ):
            delta = event.actions.state_delta if event.actions else {}
            # ADK yields the callback's state delta before invoking the agent/model.
            stage = delta.get(STAGE_STATE_KEY)
            if stage and stage["name"] not in emitted_stages:
                last_stage = stage["name"]
                emitted_stages.add(last_stage)
                yield {"event": "stage", "data": json.dumps(stage)}

        session = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id,
        )
        yield {
            "event": "complete",
            "data": json.dumps(jsonable_encoder({
                "trip_brief": session.state.get("trip_brief"),
                "optimized_route": session.state.get("optimized_route"),
                "itinerary": session.state.get("itinerary"),
                "research_grounded": settings.enable_search_grounding,
            })),
        }
    except Exception as exc:
        logger.exception(
            "Atlas planning failed session=%s stage=%s host=%s proxy_hosts=%s model=%s",
            session_id, last_stage, settings.gemini_host, proxy_hosts(), settings.default_model,
        )
        yield {"event": "error", "data": json.dumps(public_error(exc, last_stage))}
    finally:
        guardrails.release_slot()


@app.post("/api/plan")
async def plan(req: PlanRequest, request: Request):
    ip = guardrails.precheck(request, req.request)
    await guardrails.acquire_slot()
    guardrails.record(ip)
    return EventSourceResponse(plan_event_stream(req.request))


@app.get("/api/health")
async def health():
    return {"status": "ok"}
