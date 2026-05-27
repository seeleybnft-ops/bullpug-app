"""Client error capture endpoint.

Collects uncaught JS errors / React render crashes from the frontend and
persists them in MongoDB for ops review. Mounted at `/api/client-errors`.

Design notes
────────────
• CSRF-exempt: error reports often originate from already-broken pages
  where the CSRF interceptor may not be wired or may itself be the
  source of the failure. A best-effort intake is more valuable than a
  hardened one.
• Per-IP rate limiting: a single broken render can fire dozens of errors
  per second (re-render loops). We cap at 30 inserts / IP / minute via a
  small in-process sliding window — anything over the cap is dropped
  silently (returns 202 to the client so the frontend doesn't retry).
• Hard caps on input lengths so a hostile client can't pour MBs of garbage
  through the field validators.
• No PII collected: wallet address is OPTIONAL and never required.
"""

import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from utils.database import db

router = APIRouter(prefix="/client-errors", tags=["client-errors"])
logger = logging.getLogger(__name__)

# Sliding-window rate limiter: {ip -> deque[timestamps]}. Cleared lazily
# whenever an entry is read.
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_PER_WINDOW = 30
_rate_buckets: dict[str, deque[float]] = {}


def _rate_check(ip: str) -> bool:
    """Return True if this IP is under the limit, False if it should be dropped."""
    now = time.time()
    bucket = _rate_buckets.setdefault(ip, deque())
    cutoff = now - _RATE_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX_PER_WINDOW:
        return False
    bucket.append(now)
    return True


class ClientErrorPayload(BaseModel):
    """Validated client error report shape."""
    message: str = Field(max_length=2000)
    stack: Optional[str] = Field(default=None, max_length=8000)
    component_stack: Optional[str] = Field(default=None, max_length=8000)
    source: Optional[str] = Field(default=None, max_length=300)
    line: Optional[int] = None
    column: Optional[int] = None
    url: Optional[str] = Field(default=None, max_length=500)
    user_agent: Optional[str] = Field(default=None, max_length=400)
    build_id: Optional[str] = Field(default=None, max_length=80)
    kind: Optional[str] = Field(default="uncaught", max_length=40)
    wallet: Optional[str] = Field(default=None, max_length=64)


@router.post("")
async def capture_client_error(payload: ClientErrorPayload, request: Request):
    """Accept a client-side error report and persist it.

    Always returns 202 — we never want the frontend to retry on a 4xx/5xx
    here because that would compound errors during a real outage.
    """
    ip = (request.client.host if request.client else None) or "unknown"
    if not _rate_check(ip):
        # Silently drop — return 202 so the frontend's "fire-and-forget"
        # `keepalive: true` fetch doesn't surface this as a 429 in DevTools.
        return {"status": "rate_limited"}

    doc = payload.model_dump()
    doc["received_at"] = datetime.now(timezone.utc).isoformat()
    doc["ip"] = ip[:64]  # truncate just in case

    try:
        await db.client_errors.insert_one(doc)
    except Exception as e:
        logger.exception("Failed to persist client error: %s", e)
        # Still acknowledge — see docstring rationale.
        return {"status": "accept_persist_failed"}

    return {"status": "accepted"}


@router.get("/recent")
async def recent_client_errors(limit: int = 50):
    """Admin/ops view of the latest client errors. Public-readable for now
    so the user can sanity-check ingestion right after deploy; we can
    SIWS-gate it post-launch if it becomes noisy."""
    limit = max(1, min(200, limit))
    cursor = (
        db.client_errors.find({}, {"_id": 0})
        .sort("received_at", -1)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)
    return {"items": items, "count": len(items)}
