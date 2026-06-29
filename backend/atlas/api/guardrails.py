"""Abuse guardrails for the public planning endpoint.

Layered, in-process limits that protect the Gemini quota when Atlas is public:
  - input size cap      — reject oversized prompts
  - per-IP rate limit   — stop one visitor from hammering it
  - global daily cap    — the real quota protector: bounds total runs/day
  - concurrency limit   — cap simultaneous pipeline runs

State is in-process, so it's exact only when the service runs as a SINGLE
instance (deploy with --max-instances=1). For multi-instance scale, back these
with Redis instead — same logic, shared store.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import HTTPException, Request

MAX_INPUT_CHARS = 1200      # one trip description; much longer is almost certainly abuse
PER_IP_MAX = 5             # runs per IP...
PER_IP_WINDOW_S = 3600     # ...per hour
GLOBAL_DAILY_MAX = 75      # total runs/day across everyone (protects the quota)
MAX_CONCURRENT = 2         # simultaneous pipeline runs

_ip_hits: dict[str, deque] = defaultdict(deque)
_global = {"day": date.today(), "count": 0}
_sem = asyncio.Semaphore(MAX_CONCURRENT)


def _client_ip(request: Request) -> str:
    # Cloud Run puts the real client IP first in X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def precheck(request: Request, text: str) -> str:
    """Validate against all limits. Raises HTTPException if blocked; returns the
    caller's IP so the run can be recorded once it actually starts."""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Tell Atlas about your trip first.")
    if len(text) > MAX_INPUT_CHARS:
        raise HTTPException(status_code=400, detail=f"Please keep your request under {MAX_INPUT_CHARS} characters.")

    today = date.today()
    if _global["day"] != today:
        _global["day"], _global["count"] = today, 0
    if _global["count"] >= GLOBAL_DAILY_MAX:
        raise HTTPException(status_code=429, detail="Atlas has reached today's demo limit. Please check back tomorrow.")

    ip = _client_ip(request)
    now = time.monotonic()
    hits = _ip_hits[ip]
    while hits and now - hits[0] > PER_IP_WINDOW_S:
        hits.popleft()
    if len(hits) >= PER_IP_MAX:
        raise HTTPException(status_code=429, detail="You've reached the hourly limit for this demo. Try again a little later.")
    return ip


def record(ip: str) -> None:
    """Count a run that's actually starting (called after a slot is acquired)."""
    _ip_hits[ip].append(time.monotonic())
    _global["count"] += 1


async def acquire_slot() -> None:
    """Take a concurrency slot, or 429 if Atlas is already at capacity."""
    try:
        await asyncio.wait_for(_sem.acquire(), timeout=0.05)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=429, detail="Atlas is planning other trips right now. Try again in a moment.")


def release_slot() -> None:
    _sem.release()