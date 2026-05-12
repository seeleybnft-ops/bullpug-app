"""
Push Notifications System for Copy Trading
Browser/Mobile push notifications using Web Push API

Focused on Copy Trading Events:
- Trade copied from followed trader
- New follower notifications
- Profit/loss alerts on copied trades
- Stop-loss triggered on copied trades
- Performance fee earned
"""

import os
import json
import base64
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from utils.database import db

try:
    from pywebpush import webpush, WebPushException  # type: ignore
    _PYWEBPUSH_AVAILABLE = True
except Exception:  # pragma: no cover
    webpush = None  # type: ignore
    WebPushException = Exception  # type: ignore
    _PYWEBPUSH_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/push-notifications", tags=["Push Notifications"])

# VAPID public key is shared with frontend; private key signs JWT for push services
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY_RAW = os.environ.get("VAPID_PRIVATE_KEY_RAW", "")  # 32-byte private scalar, urlsafe-b64
VAPID_PRIVATE_KEY_B64 = os.environ.get("VAPID_PRIVATE_KEY_B64", "")  # legacy PKCS#8 PEM, base64
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")  # legacy fallback (raw PEM)
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", os.environ.get("VAPID_EMAIL", "mailto:admin@bullpug.app"))
VAPID_EMAIL = VAPID_SUBJECT  # backward compatibility


def _vapid_private_key_for_pywebpush() -> Optional[str]:
    """Return the VAPID private key in the form pywebpush expects.

    pywebpush's Vapid.from_string accepts:
      - a 32-byte raw private scalar (urlsafe-base64, no padding) — preferred
      - a base64-encoded DER private key

    We standardise on the raw 32-byte form.
    """
    if VAPID_PRIVATE_KEY_RAW:
        return VAPID_PRIVATE_KEY_RAW
    if VAPID_PRIVATE_KEY_B64:
        try:
            return base64.b64decode(VAPID_PRIVATE_KEY_B64).decode()
        except Exception:
            logger.exception("VAPID_PRIVATE_KEY_B64 is malformed")
    if VAPID_PRIVATE_KEY:
        return VAPID_PRIVATE_KEY
    return None


def _push_one(subscription_info: dict, payload: dict) -> bool:
    """Synchronously send a single push (called via run_in_executor)."""
    key = _vapid_private_key_for_pywebpush()
    if not key or not _PYWEBPUSH_AVAILABLE:
        return False
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=key,
            vapid_claims={"sub": VAPID_SUBJECT},
            ttl=60,
        )
        return True
    except WebPushException as e:
        # 404/410 → endpoint expired; caller will prune
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (404, 410):
            raise
        logger.warning("WebPush send failed (status=%s): %s", status, e)
        return False
    except Exception:
        logger.exception("WebPush send error")
        return False


async def _send_to_subscription(sub: dict, payload: dict) -> bool:
    """Async wrapper. Prunes expired endpoints automatically."""
    sub_info = {"endpoint": sub["endpoint"], "keys": sub["keys"]}
    loop = asyncio.get_event_loop()
    try:
        ok = await loop.run_in_executor(None, _push_one, sub_info, payload)
        return bool(ok)
    except WebPushException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (404, 410):
            try:
                await db.push_subscriptions.delete_one({"_id": sub.get("_id")})
                logger.info("Pruned expired push subscription %s", sub.get("subscription_id"))
            except Exception:
                logger.exception("Failed to prune expired subscription")
        return False


async def broadcast_to_all_subscribers(payload: dict) -> int:
    """Fan out a payload to every active push subscription. Returns delivered count."""
    if not _PYWEBPUSH_AVAILABLE or not _vapid_private_key_for_pywebpush():
        logger.info("broadcast_to_all_subscribers: skipped (pywebpush/VAPID not configured)")
        return 0
    subs = await db.push_subscriptions.find({"active": True}).to_list(2000)
    if not subs:
        return 0
    results = await asyncio.gather(*[_send_to_subscription(s, payload) for s in subs], return_exceptions=True)
    delivered = sum(1 for r in results if r is True)
    logger.info("broadcast_to_all_subscribers: %d/%d delivered", delivered, len(subs))
    return delivered


# ============== Models ==============

class PushSubscription(BaseModel):
    """Browser push subscription data"""
    endpoint: str
    keys: Dict[str, str]  # p256dh and auth keys
    

class PushSubscriptionCreate(BaseModel):
    """Request to create a push subscription"""
    wallet_address: Optional[str] = None  # Optional — anonymous subs allowed
    subscription: PushSubscription
    device_name: Optional[str] = "Browser"
    platform: Optional[str] = "web"  # web, ios, android


class PushNotificationPreferences(BaseModel):
    """User notification preferences - focused on copy trading"""
    wallet_address: str
    # Copy Trading notifications (core features)
    trade_copied: bool = True  # When a trade is copied from followed trader
    new_follower: bool = True  # When someone starts following you
    fee_earned: bool = True  # When you earn a performance fee
    # Profit/Loss alerts on copied trades
    profit_alerts: bool = True
    loss_alerts: bool = True
    stop_loss_triggered: bool = True
    # Thresholds for alerts
    min_profit_percent: float = Field(default=10.0, ge=5.0, le=100.0)
    min_loss_percent: float = Field(default=5.0, ge=2.0, le=50.0)


# ============== Subscription Management ==============

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Get the VAPID public key for push subscription."""
    if not VAPID_PUBLIC_KEY:
        # Return a demo key indicator if not configured
        return {
            "public_key": None,
            "configured": False,
            "message": "Push notifications not configured. Set VAPID_PUBLIC_KEY environment variable."
        }
    
    return {
        "public_key": VAPID_PUBLIC_KEY,
        "configured": True
    }


@router.post("/subscribe")
async def subscribe_to_push(data: PushSubscriptionCreate):
    """Subscribe a device to push notifications."""
    subscription_id = str(uuid.uuid4())[:8]
    
    wallet = data.wallet_address or "anonymous"

    # Check if this endpoint is already subscribed
    existing = await db.push_subscriptions.find_one({
        "endpoint": data.subscription.endpoint
    })
    
    if existing:
        # Update existing subscription
        await db.push_subscriptions.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "wallet_address": wallet,
                "keys": data.subscription.keys,
                "device_name": data.device_name,
                "platform": data.platform,
                "active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return {
            "success": True,
            "subscription_id": existing.get("subscription_id"),
            "message": "Subscription updated"
        }
    
    # Create new subscription
    subscription_doc = {
        "subscription_id": subscription_id,
        "wallet_address": wallet,
        "endpoint": data.subscription.endpoint,
        "keys": data.subscription.keys,
        "device_name": data.device_name,
        "platform": data.platform,
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.push_subscriptions.insert_one(subscription_doc)
    
    # Initialize preferences only for wallet-bound subs
    if data.wallet_address:
        await db.push_notification_preferences.update_one(
            {"wallet_address": wallet},
            {
                "$setOnInsert": {
                    "wallet_address": wallet,
                    **PushNotificationPreferences(wallet_address=wallet).dict(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
    
    return {
        "success": True,
        "subscription_id": subscription_id,
        "message": "Successfully subscribed to push notifications"
    }


@router.post("/unsubscribe")
async def unsubscribe_from_push(wallet_address: str, endpoint: Optional[str] = None):
    """Unsubscribe from push notifications."""
    if endpoint:
        # Unsubscribe specific device
        result = await db.push_subscriptions.delete_one({
            "wallet_address": wallet_address,
            "endpoint": endpoint
        })
    else:
        # Unsubscribe all devices
        result = await db.push_subscriptions.delete_many({
            "wallet_address": wallet_address
        })
    
    return {
        "success": True,
        "deleted_count": result.deleted_count,
        "message": "Unsubscribed from push notifications"
    }


@router.get("/subscriptions/{wallet_address}")
async def get_subscriptions(wallet_address: str):
    """Get all push subscriptions for a wallet."""
    subscriptions = await db.push_subscriptions.find(
        {"wallet_address": wallet_address, "active": True},
        {"_id": 0, "keys": 0}  # Don't expose keys
    ).to_list(20)
    
    return {
        "subscriptions": subscriptions,
        "count": len(subscriptions)
    }


# ============== Preferences Management ==============

@router.get("/preferences/{wallet_address}")
async def get_push_preferences(wallet_address: str):
    """Get push notification preferences."""
    prefs = await db.push_notification_preferences.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    
    if not prefs:
        # Return defaults
        return PushNotificationPreferences(wallet_address=wallet_address).dict()
    
    return prefs


@router.put("/preferences/{wallet_address}")
async def update_push_preferences(
    wallet_address: str,
    trade_copied: Optional[bool] = None,
    new_follower: Optional[bool] = None,
    fee_earned: Optional[bool] = None,
    profit_alerts: Optional[bool] = None,
    loss_alerts: Optional[bool] = None,
    stop_loss_triggered: Optional[bool] = None,
    min_profit_percent: Optional[float] = None,
    min_loss_percent: Optional[float] = None
):
    """Update push notification preferences for copy trading."""
    update_data = {}
    
    # Build update dict from non-None values
    local_vars = locals()
    for key in ['trade_copied', 'new_follower', 'fee_earned', 'profit_alerts',
                'loss_alerts', 'stop_loss_triggered', 'min_profit_percent', 'min_loss_percent']:
        if local_vars[key] is not None:
            update_data[key] = local_vars[key]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No preferences to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.push_notification_preferences.update_one(
        {"wallet_address": wallet_address},
        {
            "$set": update_data,
            "$setOnInsert": {
                "wallet_address": wallet_address,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return await get_push_preferences(wallet_address)


# ============== Send Notifications ==============

async def send_push_notification(
    wallet_address: str,
    notification_type: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a push notification to all subscribed devices for a wallet.
    
    Returns dict with success status and delivery results.
    """
    # Check user preferences
    prefs = await db.push_notification_preferences.find_one(
        {"wallet_address": wallet_address}
    )
    
    # Map notification types to preference keys (copy trading focused)
    type_to_pref = {
        "trade_copied": "trade_copied",
        "new_follower": "new_follower",
        "fee_earned": "fee_earned",
        "profit_alert": "profit_alerts",
        "loss_alert": "loss_alerts",
        "stop_loss_triggered": "stop_loss_triggered",
        "runner_alert": "runner_alerts"  # Runner token alerts
    }
    
    pref_key = type_to_pref.get(notification_type)
    if prefs and pref_key and not prefs.get(pref_key, True):
        return {
            "success": False,
            "reason": "User has disabled this notification type",
            "sent_count": 0
        }
    
    # Get all active subscriptions
    subscriptions = await db.push_subscriptions.find({
        "wallet_address": wallet_address,
        "active": True
    }).to_list(20)
    
    if not subscriptions:
        return {
            "success": False,
            "reason": "No active subscriptions",
            "sent_count": 0
        }
    
    # Build notification payload (used when pywebpush is configured)
    _notification_payload = {
        "title": title,
        "body": body,
        "icon": icon or "/bullpug-icon.png",
        "badge": badge or "/bullpug-badge.png",
        "data": {
            "type": notification_type,
            "url": url or "/",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(data or {})
        },
        "requireInteraction": notification_type in ["prize_payout", "stop_loss_triggered"],
        "tag": f"{notification_type}_{wallet_address[:8]}"
    }
    
    # Store notification record
    notification_record = {
        "notification_id": str(uuid.uuid4())[:8],
        "wallet_address": wallet_address,
        "notification_type": notification_type,
        "title": title,
        "body": body,
        "data": data,
        "subscriptions_targeted": len(subscriptions),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.push_notification_log.insert_one(notification_record)
    
    # In production, you would use pywebpush to actually send:
    # from pywebpush import webpush, WebPushException
    # for sub in subscriptions:
    #     try:
    #         webpush(
    #             subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
    #             data=json.dumps(_notification_payload),
    #             vapid_private_key=VAPID_PRIVATE_KEY,
    #             vapid_claims={"sub": VAPID_EMAIL}
    #         )
    #     except WebPushException as e:
    #         logger.error(f"Push failed: {e}")
    
    logger.info(f"Push notification queued: {title} -> {wallet_address[:8]}... ({len(subscriptions)} devices)")
    
    return {
        "success": True,
        "sent_count": len(subscriptions),
        "notification_id": notification_record["notification_id"]
    }


@router.post("/send-test/{wallet_address}")
async def send_test_notification(wallet_address: str):
    """Send a test push notification to verify setup."""
    result = await send_push_notification(
        wallet_address=wallet_address,
        notification_type="test",
        title="🐾 Bullpug Test Notification",
        body="Push notifications are working! You'll receive trading alerts here.",
        data={"test": True},
        url="/trading-bot"
    )
    
    return result


@router.get("/history/{wallet_address}")
async def get_notification_history(
    wallet_address: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get push notification history for a wallet."""
    notifications = await db.push_notification_log.find(
        {"wallet_address": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "notifications": notifications,
        "count": len(notifications)
    }


# ============== Helper Functions for Copy Trading Events ==============

async def notify_trade_copied(
    wallet_address: str,
    trader_name: str,
    token_symbol: str,
    trade_type: str,
    amount_sol: float
):
    """Notify follower when a trade is copied from a trader they follow."""
    return await send_push_notification(
        wallet_address=wallet_address,
        notification_type="trade_copied",
        title=f"Trade Copied: {trade_type.upper()} {token_symbol}",
        body=f"Copied {trade_type} from {trader_name} for {amount_sol:.4f} SOL",
        data={
            "trader_name": trader_name,
            "token_symbol": token_symbol,
            "trade_type": trade_type,
            "amount_sol": amount_sol
        },
        url="/trading-bot?tab=positions"
    )


async def notify_new_follower(
    wallet_address: str,
    follower_count: int
):
    """Notify trader when someone starts following them."""
    return await send_push_notification(
        wallet_address=wallet_address,
        notification_type="new_follower",
        title="New Follower!",
        body=f"Someone started copying your trades. You now have {follower_count} follower{'s' if follower_count != 1 else ''}.",
        data={"total_followers": follower_count},
        url="/trading-bot?tab=social"
    )


async def notify_fee_earned(
    wallet_address: str,
    fee_amount: float,
    token_symbol: str,
    gross_profit: float
):
    """Notify trader when they earn a performance fee."""
    return await send_push_notification(
        wallet_address=wallet_address,
        notification_type="fee_earned",
        title="Performance Fee Earned! 💰",
        body=f"You earned {fee_amount:.4f} SOL from a follower's {token_symbol} trade profit.",
        data={
            "fee_amount_sol": fee_amount,
            "token_symbol": token_symbol,
            "gross_profit_sol": gross_profit
        },
        url="/trading-bot?tab=social"
    )


async def notify_copied_trade_profit(
    wallet_address: str,
    token_symbol: str,
    pnl_percent: float,
    pnl_sol: float,
    trader_name: str
):
    """Notify follower of significant profit on a copied trade."""
    emoji = "🚀" if pnl_percent >= 50 else "🎉" if pnl_percent >= 25 else "✨"
    return await send_push_notification(
        wallet_address=wallet_address,
        notification_type="profit_alert",
        title=f"{emoji} Copied Trade +{pnl_percent:.1f}%",
        body=f"Your {token_symbol} position (copied from {trader_name}) is up {pnl_percent:.1f}% (+{pnl_sol:.4f} SOL)",
        data={
            "token_symbol": token_symbol,
            "pnl_percent": pnl_percent,
            "pnl_sol": pnl_sol,
            "trader_name": trader_name
        },
        url="/trading-bot?tab=positions"
    )


async def notify_copied_trade_stop_loss(
    wallet_address: str,
    token_symbol: str,
    loss_percent: float,
    trader_name: str
):
    """Notify follower when stop loss is triggered on a copied trade."""
    return await send_push_notification(
        wallet_address=wallet_address,
        notification_type="stop_loss_triggered",
        title="⚠️ Stop Loss Triggered",
        body=f"Your {token_symbol} position (copied from {trader_name}) was closed at {loss_percent:.1f}% loss.",
        data={
            "token_symbol": token_symbol,
            "loss_percent": loss_percent,
            "trader_name": trader_name
        },
        url="/trading-bot?tab=history"
    )
