"""Newsletter subscription routes."""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone

from services.email_service import send_email
from utils.database import db


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/newsletter", tags=["newsletter"])

# Confirmation copy for the Act I placeholder signup — Tinkerpug voice,
# plain-text-feel. Wrapped in a <pre> tag so gmail/apple mail preserve
# the newlines without an HTML template. Sender + API key come from
# the existing SendGrid setup in `services/email_service.py`.
_ACT1_CONFIRMATION_SUBJECT = "the signal is logged."
_ACT1_CONFIRMATION_TEXT = (
    "keeper's log — signal received.\n"
    "\n"
    "You'll be the first to know when Act I arrives.\n"
    "\n"
    "In the meantime, the Archive is open.\n"
    "Ask Tinkerpug anything.\n"
    "\n"
    "bullpug.com/archive\n"
    "\n"
    "keeper's note: the deeper you dig, the more it gives back."
)


def _act1_html_body() -> str:
    """Plain-text-feel body wrapped in <pre> so newlines survive."""
    return (
        "<pre style=\"font-family: ui-monospace, SFMono-Regular, Menlo, monospace; "
        "background: #0a0a12; color: #dce2f0; padding: 24px; border-radius: 12px; "
        "line-height: 1.6; margin: 0; white-space: pre-wrap; font-size: 14px;\">"
        f"{_ACT1_CONFIRMATION_TEXT}"
        "</pre>"
    )


class NewsletterSubscribe(BaseModel):
    email: str
    # Optional identifier for where the signup came from (e.g.
    # "act1-placeholder", "footer", "modal"). Stored on the doc so
    # marketing can segment on it later. Keep it short.
    source: Optional[str] = None


@router.post("/subscribe")
async def subscribe_newsletter(data: NewsletterSubscribe):
    """Subscribe to the newsletter."""
    src = (data.source or "").strip()[:64] or None
    existing = await db.newsletter_subscribers.find_one({"email": data.email}, {"_id": 0})
    if existing:
        # Backfill `source` on legacy rows the first time they resurface —
        # never overwrite an existing source (first-touch wins).
        if src and not existing.get("source"):
            try:
                await db.newsletter_subscribers.update_one(
                    {"email": data.email},
                    {"$set": {"source": src}},
                )
            except Exception:
                pass
        return {"message": "Already subscribed!", "status": "existing"}
    doc = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "source": src,
    }
    await db.newsletter_subscribers.insert_one(doc)

    # Fire the confirmation email — non-blocking so a slow/failing
    # transactional provider never stalls the HTTP response. Only
    # act1-placeholder signups get this specific keeper's-log copy;
    # other sources are silent for now (footer signups had no email
    # historically and we don't want to break that expectation).
    if src == "act1-placeholder":
        async def _send_conf():
            try:
                ok = await send_email(
                    to_email=data.email,
                    subject=_ACT1_CONFIRMATION_SUBJECT,
                    html_content=_act1_html_body(),
                )
                if not ok:
                    logger.warning("act1 confirmation not sent for %s", data.email)
            except Exception:
                logger.exception("act1 confirmation crash for %s", data.email)
        try:
            asyncio.create_task(_send_conf())
        except RuntimeError:
            # No running loop (shouldn't happen inside FastAPI) — send inline.
            await _send_conf()

    return {"message": "Welcome to the Guardian newsletter!", "status": "success"}
