"""Email routes for subscriptions and notifications."""

from fastapi import APIRouter
import uuid
from datetime import datetime, timezone

from models.schemas import EmailSubscribeRequest, SendWelcomeEmailRequest
from utils.database import db
from utils.config import SENDGRID_API_KEY, SENDER_EMAIL
from services.email_service import send_welcome_email

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/subscribe")
async def subscribe_to_emails(data: EmailSubscribeRequest):
    """Subscribe to email notifications."""
    subscription = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "wallet_address": data.wallet_address,
        "subscribe_weekly": data.subscribe_weekly,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True
    }
    
    existing = await db.email_subscriptions.find_one({
        "wallet_address": data.wallet_address
    })
    
    if existing:
        await db.email_subscriptions.update_one(
            {"wallet_address": data.wallet_address},
            {"$set": {
                "email": data.email,
                "subscribe_weekly": data.subscribe_weekly,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return {"message": "Email preferences updated", "status": "updated"}
    
    await db.email_subscriptions.insert_one(subscription)
    await send_welcome_email(data.email, data.wallet_address)
    
    return {"message": "Subscribed successfully!", "status": "subscribed"}


@router.post("/welcome")
async def send_welcome(data: SendWelcomeEmailRequest):
    """Send welcome email to a user."""
    success = await send_welcome_email(data.email, data.wallet_address)
    if success:
        return {"message": "Welcome email sent", "status": "sent"}
    return {"message": "Email service not configured", "status": "not_configured"}


@router.get("/subscription/{wallet_address}")
async def get_email_subscription(wallet_address: str):
    """Get email subscription status for a wallet."""
    subscription = await db.email_subscriptions.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    if subscription:
        return subscription
    return {"subscribed": False}


@router.delete("/unsubscribe/{wallet_address}")
async def unsubscribe_from_emails(wallet_address: str):
    """Unsubscribe from email notifications."""
    result = await db.email_subscriptions.update_one(
        {"wallet_address": wallet_address},
        {"$set": {"active": False, "unsubscribed_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count > 0:
        return {"message": "Unsubscribed successfully"}
    return {"message": "No subscription found"}


@router.post("/test")
async def test_email_config():
    """Test if email is configured."""
    if SENDGRID_API_KEY:
        return {"configured": True, "sender": SENDER_EMAIL}
    return {"configured": False, "message": "SENDGRID_API_KEY not set"}
