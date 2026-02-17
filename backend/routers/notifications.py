"""Notifications routes for push notifications and alerts."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from utils.database import db

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PushSubscription(BaseModel):
    wallet_address: str
    subscription: dict


@router.get("/{wallet_address}")
async def get_notifications(wallet_address: str, limit: int = 50):
    """Get notifications for a user."""
    notifications = await db.notifications.find(
        {"to_wallet": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    unread = sum(1 for n in notifications if not n.get("read"))
    
    return {"notifications": notifications, "unread_count": unread}


@router.post("/read/{notification_id}")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    await db.notifications.update_one(
        {"id": notification_id},
        {"$set": {"read": True}}
    )
    return {"message": "Marked as read"}


@router.post("/read-all/{wallet_address}")
async def mark_all_notifications_read(wallet_address: str):
    """Mark all notifications as read."""
    await db.notifications.update_many(
        {"to_wallet": wallet_address, "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "All notifications marked as read"}


@router.post("/subscribe")
async def subscribe_push(data: PushSubscription):
    """Subscribe to push notifications."""
    subscription = {
        "wallet_address": data.wallet_address,
        "subscription": data.subscription,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.push_subscriptions.update_one(
        {"wallet_address": data.wallet_address},
        {"$set": subscription},
        upsert=True
    )
    
    return {"message": "Subscribed to push notifications"}


async def create_notification(to_wallet: str, notification_type: str, title: str, body: str, data: dict = None):
    """Helper function to create a notification."""
    notification = {
        "id": str(uuid.uuid4()),
        "to_wallet": to_wallet,
        "type": notification_type,
        "title": title,
        "body": body,
        "data": data or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    return notification
