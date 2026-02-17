"""Notification utilities for sending alerts to users."""

import uuid
from datetime import datetime, timezone

from .database import db


# WebSocket notification manager (will be set by server.py)
notification_manager = None


def set_notification_manager(manager):
    """Set the notification manager from server.py."""
    global notification_manager
    notification_manager = manager


async def send_notification(to_wallet: str, title: str, body: str, notif_type: str = "general"):
    """Store notification and send via WebSocket if user is connected."""
    notification = {
        "id": str(uuid.uuid4()),
        "to_wallet": to_wallet,
        "title": title,
        "body": body,
        "type": notif_type,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    # Send via WebSocket if manager is set and user is connected
    if notification_manager:
        await notification_manager.send_personal_message({
            "type": "notification",
            "data": {k: v for k, v in notification.items() if k != "_id"}
        }, to_wallet)
    
    return notification
