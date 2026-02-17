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
    """Get notifications for a wallet."""
    notifications = await db.notifications.find(
        {"wallet_address": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return {
        "notifications": notifications,
        "unread_count": sum(1 for n in notifications if not n.get("read"))
    }


@router.post("/read/{notification_id}")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    result = await db.notifications.update_one(
        {"id": notification_id},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": result.modified_count > 0}


@router.post("/read-all/{wallet_address}")
async def mark_all_notifications_read(wallet_address: str):
    """Mark all notifications as read for a wallet."""
    result = await db.notifications.update_many(
        {"wallet_address": wallet_address, "read": False},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"marked_read": result.modified_count}


@router.post("/subscribe")
async def subscribe_push_notifications(data: PushSubscription):
    """Subscribe to push notifications."""
    existing = await db.push_subscriptions.find_one({"wallet_address": data.wallet_address})
    
    if existing:
        await db.push_subscriptions.update_one(
            {"wallet_address": data.wallet_address},
            {"$set": {"subscription": data.subscription, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    else:
        await db.push_subscriptions.insert_one({
            "id": str(uuid.uuid4()),
            "wallet_address": data.wallet_address,
            "subscription": data.subscription,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"message": "Subscribed to push notifications"}


async def create_notification(wallet_address: str, notification_type: str, title: str, message: str, data: dict = None):
    """Helper function to create a notification."""
    notification = {
        "id": str(uuid.uuid4()),
        "wallet_address": wallet_address,
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    return notification
