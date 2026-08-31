"""Newsletter subscription routes."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone

from utils.database import db


router = APIRouter(prefix="/newsletter", tags=["newsletter"])


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
    return {"message": "Welcome to the Guardian newsletter!", "status": "success"}
