"""Newsletter subscription routes."""

from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone

from utils.database import db


router = APIRouter(prefix="/newsletter", tags=["newsletter"])


class NewsletterSubscribe(BaseModel):
    email: str


@router.post("/subscribe")
async def subscribe_newsletter(data: NewsletterSubscribe):
    """Subscribe to the newsletter."""
    existing = await db.newsletter_subscribers.find_one({"email": data.email}, {"_id": 0})
    if existing:
        return {"message": "Already subscribed!", "status": "existing"}
    doc = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "active": True
    }
    await db.newsletter_subscribers.insert_one(doc)
    return {"message": "Welcome to the Guardian newsletter!", "status": "success"}
