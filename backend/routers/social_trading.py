"""
Social Trading - Copy Trades Feature
Allows users to follow successful traders and automatically copy their trades.

Features:
- Top trader leaderboard based on PnL
- Follow/unfollow traders
- Automatic trade copying with customizable position sizing
- Performance analytics for followed traders
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from utils.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/social-trading", tags=["Social Trading"])


# ============== Models ==============

class TraderProfile(BaseModel):
    """Public trader profile for social trading"""
    wallet_address: str
    display_name: str = "Anonymous Trader"
    bio: Optional[str] = None
    profile_visible: bool = True  # Can be found in leaderboard
    copy_trading_enabled: bool = False  # Allow others to copy
    min_copy_amount_sol: float = Field(default=0.05, ge=0.01, le=1.0)
    max_copiers: int = Field(default=100, ge=1, le=1000)
    performance_fee_percent: float = Field(default=10.0, ge=5.0, le=15.0)  # 5-15% fee on follower profits
    total_fees_earned_sol: float = 0.0  # Track total fees earned
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PerformanceFeeRecord(BaseModel):
    """Record of a performance fee payment"""
    fee_id: str
    trader_wallet: str
    follower_wallet: str
    copy_trade_id: str
    token_symbol: str
    gross_profit_sol: float
    fee_percent: float
    fee_amount_sol: float
    net_profit_sol: float  # Follower's profit after fee
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FollowRequest(BaseModel):
    """Request to follow a trader"""
    follower_wallet: str
    trader_wallet: str
    copy_percentage: float = Field(default=100, ge=10, le=100)  # % of trader's position to copy
    max_position_sol: float = Field(default=0.1, ge=0.01, le=1.0)  # Max per trade
    auto_copy_enabled: bool = True


class TraderStats(BaseModel):
    """Trader performance statistics"""
    wallet_address: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl_sol: float = 0.0
    total_pnl_percent: float = 0.0
    avg_trade_duration_hours: float = 0.0
    best_trade_pnl_percent: float = 0.0
    worst_trade_pnl_percent: float = 0.0
    followers_count: int = 0
    rank: int = 0
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============== Trader Profile Endpoints ==============

@router.get("/profile/{wallet_address}")
async def get_trader_profile(wallet_address: str):
    """Get a trader's public profile and stats."""
    profile = await db.trader_profiles.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    
    if not profile:
        # Return default profile
        return {
            "wallet_address": wallet_address,
            "display_name": f"Trader_{wallet_address[:6]}",
            "profile_visible": False,
            "copy_trading_enabled": False,
            "stats": None
        }
    
    # Get performance stats
    stats = await calculate_trader_stats(wallet_address)
    
    return {
        **profile,
        "stats": stats
    }


@router.post("/profile/update")
async def update_trader_profile(profile: TraderProfile):
    """Update trader profile settings."""
    await db.trader_profiles.update_one(
        {"wallet_address": profile.wallet_address},
        {"$set": profile.dict()},
        upsert=True
    )
    
    return {
        "success": True,
        "message": "Profile updated",
        "profile": profile.dict()
    }


@router.post("/profile/enable-copy-trading/{wallet_address}")
async def enable_copy_trading(wallet_address: str, enabled: bool = True):
    """Enable or disable copy trading for your profile."""
    await db.trader_profiles.update_one(
        {"wallet_address": wallet_address},
        {
            "$set": {
                "copy_trading_enabled": enabled,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$setOnInsert": {
                "wallet_address": wallet_address,
                "display_name": f"Trader_{wallet_address[:6]}",
                "profile_visible": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "copy_trading_enabled": enabled,
        "message": "Others can now copy your trades" if enabled else "Copy trading disabled"
    }


# ============== Leaderboard Endpoints ==============

@router.get("/leaderboard")
async def get_trader_leaderboard(
    period: str = Query("7d", regex="^(24h|7d|30d|all)$"),
    limit: int = Query(20, ge=1, le=100),
    min_trades: int = Query(5, ge=1)
):
    """Get top traders by performance."""
    # Calculate period start
    now = datetime.now(timezone.utc)
    if period == "24h":
        period_start = now - timedelta(hours=24)
    elif period == "7d":
        period_start = now - timedelta(days=7)
    elif period == "30d":
        period_start = now - timedelta(days=30)
    else:
        period_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    
    period_start_str = period_start.isoformat()
    
    # Aggregate trader performance from positions
    pipeline = [
        {
            "$match": {
                "status": {"$in": ["closed_profit", "closed_loss"]},
                "closed_at": {"$gte": period_start_str}
            }
        },
        {
            "$group": {
                "_id": "$wallet_address",
                "total_trades": {"$sum": 1},
                "winning_trades": {
                    "$sum": {"$cond": [{"$eq": ["$status", "closed_profit"]}, 1, 0]}
                },
                "total_pnl_sol": {"$sum": {"$ifNull": ["$pnl_sol", 0]}},
                "total_pnl_percent": {"$avg": {"$ifNull": ["$pnl_percent", 0]}},
                "best_trade": {"$max": {"$ifNull": ["$pnl_percent", 0]}},
                "worst_trade": {"$min": {"$ifNull": ["$pnl_percent", 0]}}
            }
        },
        {
            "$match": {
                "total_trades": {"$gte": min_trades}
            }
        },
        {
            "$addFields": {
                "win_rate": {
                    "$multiply": [
                        {"$divide": ["$winning_trades", "$total_trades"]},
                        100
                    ]
                }
            }
        },
        {
            "$sort": {"total_pnl_sol": -1}
        },
        {
            "$limit": limit
        }
    ]
    
    results = await db.ai_trader_positions.aggregate(pipeline).to_list(limit)
    
    leaderboard = []
    for i, trader in enumerate(results):
        # Get profile info
        profile = await db.trader_profiles.find_one(
            {"wallet_address": trader["_id"]},
            {"_id": 0, "display_name": 1, "copy_trading_enabled": 1, "profile_visible": 1, "performance_fee_percent": 1, "total_fees_earned_sol": 1}
        )
        
        # Skip if profile is not visible
        if profile and not profile.get("profile_visible", True):
            continue
        
        # Get followers count
        followers = await db.copy_trading_follows.count_documents({
            "trader_wallet": trader["_id"],
            "active": True
        })
        
        leaderboard.append({
            "rank": i + 1,
            "wallet_address": trader["_id"],
            "display_name": profile.get("display_name", f"Trader_{trader['_id'][:6]}") if profile else f"Trader_{trader['_id'][:6]}",
            "copy_trading_enabled": profile.get("copy_trading_enabled", False) if profile else False,
            "performance_fee_percent": profile.get("performance_fee_percent", 10.0) if profile else 10.0,
            "total_fees_earned_sol": round(profile.get("total_fees_earned_sol", 0), 4) if profile else 0,
            "total_trades": trader["total_trades"],
            "winning_trades": trader["winning_trades"],
            "win_rate": round(trader["win_rate"], 1),
            "total_pnl_sol": round(trader["total_pnl_sol"], 4),
            "avg_pnl_percent": round(trader["total_pnl_percent"], 2),
            "best_trade_percent": round(trader["best_trade"], 2),
            "worst_trade_percent": round(trader["worst_trade"], 2),
            "followers_count": followers
        })
    
    return {
        "period": period,
        "leaderboard": leaderboard,
        "total_traders": len(leaderboard)
    }


# ============== Follow/Copy Trading Endpoints ==============

@router.post("/follow")
async def follow_trader(request: FollowRequest):
    """Start following a trader to copy their trades."""
    # Check if trader has copy trading enabled
    trader_profile = await db.trader_profiles.find_one({
        "wallet_address": request.trader_wallet
    })
    
    if not trader_profile or not trader_profile.get("copy_trading_enabled"):
        raise HTTPException(
            status_code=400,
            detail="This trader has not enabled copy trading"
        )
    
    # Check max copiers limit
    current_followers = await db.copy_trading_follows.count_documents({
        "trader_wallet": request.trader_wallet,
        "active": True
    })
    
    max_copiers = trader_profile.get("max_copiers", 100)
    if current_followers >= max_copiers:
        raise HTTPException(
            status_code=400,
            detail=f"This trader has reached their max followers limit ({max_copiers})"
        )
    
    # Check if already following
    existing = await db.copy_trading_follows.find_one({
        "follower_wallet": request.follower_wallet,
        "trader_wallet": request.trader_wallet
    })
    
    if existing and existing.get("active"):
        raise HTTPException(
            status_code=400,
            detail="You are already following this trader"
        )
    
    # Create or update follow relationship
    follow_id = str(uuid.uuid4())[:8]
    follow_doc = {
        "follow_id": follow_id,
        "follower_wallet": request.follower_wallet,
        "trader_wallet": request.trader_wallet,
        "copy_percentage": request.copy_percentage,
        "max_position_sol": request.max_position_sol,
        "auto_copy_enabled": request.auto_copy_enabled,
        "active": True,
        "trades_copied": 0,
        "total_pnl_sol": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if existing:
        await db.copy_trading_follows.update_one(
            {"_id": existing["_id"]},
            {"$set": {**follow_doc, "reactivated_at": datetime.now(timezone.utc).isoformat()}}
        )
    else:
        await db.copy_trading_follows.insert_one(follow_doc)
    
    # Notify the trader about new follower
    try:
        await notify_trader_of_new_follower(request.trader_wallet, request.follower_wallet)
    except Exception as e:
        logger.warning(f"Failed to send new follower notification: {e}")
    
    return {
        "success": True,
        "follow_id": follow_id,
        "message": f"Now following {trader_profile.get('display_name', 'trader')}",
        "copy_percentage": request.copy_percentage,
        "max_position_sol": request.max_position_sol
    }


@router.post("/unfollow")
async def unfollow_trader(follower_wallet: str, trader_wallet: str):
    """Stop following a trader."""
    result = await db.copy_trading_follows.update_one(
        {
            "follower_wallet": follower_wallet,
            "trader_wallet": trader_wallet,
            "active": True
        },
        {
            "$set": {
                "active": False,
                "unfollowed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Follow relationship not found"
        )
    
    return {
        "success": True,
        "message": "Unfollowed trader"
    }


@router.get("/following/{wallet_address}")
async def get_following(wallet_address: str):
    """Get list of traders you're following."""
    follows = await db.copy_trading_follows.find(
        {"follower_wallet": wallet_address, "active": True},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with trader profiles and stats
    enriched = []
    for follow in follows:
        profile = await db.trader_profiles.find_one(
            {"wallet_address": follow["trader_wallet"]},
            {"_id": 0, "display_name": 1}
        )
        
        stats = await calculate_trader_stats(follow["trader_wallet"])
        
        enriched.append({
            **follow,
            "trader_display_name": profile.get("display_name", f"Trader_{follow['trader_wallet'][:6]}") if profile else f"Trader_{follow['trader_wallet'][:6]}",
            "trader_stats": stats
        })
    
    return {
        "following": enriched,
        "count": len(enriched)
    }


@router.get("/followers/{wallet_address}")
async def get_followers(wallet_address: str):
    """Get list of users following you (if you're a trader)."""
    followers = await db.copy_trading_follows.find(
        {"trader_wallet": wallet_address, "active": True},
        {"_id": 0, "follower_wallet": 1, "copy_percentage": 1, "created_at": 1, "trades_copied": 1}
    ).to_list(100)
    
    return {
        "followers": followers,
        "count": len(followers)
    }


@router.put("/follow/settings")
async def update_follow_settings(
    follower_wallet: str,
    trader_wallet: str,
    copy_percentage: Optional[float] = None,
    max_position_sol: Optional[float] = None,
    auto_copy_enabled: Optional[bool] = None
):
    """Update copy trading settings for a followed trader."""
    update_data = {}
    
    if copy_percentage is not None:
        update_data["copy_percentage"] = max(10, min(100, copy_percentage))
    if max_position_sol is not None:
        update_data["max_position_sol"] = max(0.01, min(1.0, max_position_sol))
    if auto_copy_enabled is not None:
        update_data["auto_copy_enabled"] = auto_copy_enabled
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No settings to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.copy_trading_follows.update_one(
        {
            "follower_wallet": follower_wallet,
            "trader_wallet": trader_wallet,
            "active": True
        },
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Follow relationship not found")
    
    return {
        "success": True,
        "updated_settings": update_data
    }


# ============== Copy Trade Execution ==============

async def copy_trade_to_followers(
    trader_wallet: str,
    trade_info: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Copy a trade to all followers of a trader.
    Called when a trader executes a trade.
    Returns list of copied trades.
    """
    # Get all active followers with auto-copy enabled
    followers = await db.copy_trading_follows.find({
        "trader_wallet": trader_wallet,
        "active": True,
        "auto_copy_enabled": True
    }).to_list(100)
    
    copied_trades = []
    
    for follow in followers:
        try:
            # Calculate position size based on follower settings
            trader_position = trade_info.get("amount_sol", 0)
            copy_percentage = follow.get("copy_percentage", 100) / 100
            max_position = follow.get("max_position_sol", 0.1)
            
            copied_position = min(
                trader_position * copy_percentage,
                max_position
            )
            
            # Skip if position too small
            if copied_position < 0.01:
                continue
            
            # Create copied trade record
            copy_trade_id = str(uuid.uuid4())[:8]
            copied_trade = {
                "copy_trade_id": copy_trade_id,
                "original_trade_id": trade_info.get("execution_id") or trade_info.get("position_id"),
                "follower_wallet": follow["follower_wallet"],
                "trader_wallet": trader_wallet,
                "token_symbol": trade_info.get("token_symbol"),
                "token_mint": trade_info.get("token_mint"),
                "trade_type": trade_info.get("trade_type", "buy"),
                "original_amount_sol": trader_position,
                "copied_amount_sol": copied_position,
                "entry_price": trade_info.get("entry_price"),
                "stop_loss_price": trade_info.get("stop_loss_price"),
                "take_profit_price": trade_info.get("take_profit_price"),
                "status": "pending",  # pending, executed, failed
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.copied_trades.insert_one(copied_trade)
            
            # Update follower's trades_copied count
            await db.copy_trading_follows.update_one(
                {"_id": follow["_id"]},
                {"$inc": {"trades_copied": 1}}
            )
            
            copied_trades.append(copied_trade)
            logger.info(f"Copied trade {copy_trade_id} to {follow['follower_wallet'][:8]}...")
            
        except Exception as e:
            logger.error(f"Failed to copy trade to {follow['follower_wallet']}: {e}")
    
    # Send notifications to all followers after copying
    if copied_trades:
        try:
            await notify_followers_of_trade(trader_wallet, trade_info, copied_trades)
        except Exception as e:
            logger.warning(f"Failed to send copy trade notifications: {e}")
    
    return copied_trades


@router.get("/copied-trades/{wallet_address}")
async def get_copied_trades(wallet_address: str, limit: int = 50):
    """Get trades that were copied to your account."""
    trades = await db.copied_trades.find(
        {"follower_wallet": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "copied_trades": trades,
        "count": len(trades)
    }


# ============== Helper Functions ==============

async def calculate_trader_stats(wallet_address: str) -> Optional[Dict[str, Any]]:
    """Calculate performance statistics for a trader."""
    # Get all closed positions
    positions = await db.ai_trader_positions.find({
        "wallet_address": wallet_address,
        "status": {"$in": ["closed_profit", "closed_loss"]}
    }).to_list(1000)
    
    if not positions:
        return None
    
    total_trades = len(positions)
    winning = [p for p in positions if p.get("status") == "closed_profit"]
    losing = [p for p in positions if p.get("status") == "closed_loss"]
    
    total_pnl = sum(p.get("pnl_sol", 0) for p in positions)
    pnl_percents = [p.get("pnl_percent", 0) for p in positions if p.get("pnl_percent")]
    
    # Get followers count
    followers = await db.copy_trading_follows.count_documents({
        "trader_wallet": wallet_address,
        "active": True
    })
    
    return {
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": round((len(winning) / total_trades) * 100, 1) if total_trades > 0 else 0,
        "total_pnl_sol": round(total_pnl, 4),
        "avg_pnl_percent": round(sum(pnl_percents) / len(pnl_percents), 2) if pnl_percents else 0,
        "best_trade_percent": round(max(pnl_percents), 2) if pnl_percents else 0,
        "worst_trade_percent": round(min(pnl_percents), 2) if pnl_percents else 0,
        "followers_count": followers
    }


# ============== Notification System ==============

class CopyTradeNotification(BaseModel):
    """Notification model for copy trading events"""
    notification_id: str
    wallet_address: str
    notification_type: str  # trade_copied, trader_followed, trade_executed, profit_alert, loss_alert
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


async def send_copy_trade_notification(
    wallet_address: str,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
):
    """
    Send a notification to a user about copy trading activity.
    Stores in database and can be fetched by frontend.
    """
    try:
        notification = {
            "notification_id": str(uuid.uuid4())[:8],
            "wallet_address": wallet_address,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.copy_trade_notifications.insert_one(notification)
        logger.info(f"Sent notification to {wallet_address[:8]}...: {title}")
        
        return notification
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return None


async def notify_followers_of_trade(
    trader_wallet: str,
    trade_info: Dict[str, Any],
    copied_trades: List[Dict[str, Any]]
):
    """
    Notify all followers that a trade was copied from a trader they follow.
    """
    # Get trader profile for display name
    trader_profile = await db.trader_profiles.find_one(
        {"wallet_address": trader_wallet},
        {"_id": 0, "display_name": 1}
    )
    trader_name = trader_profile.get("display_name", f"Trader_{trader_wallet[:6]}") if trader_profile else f"Trader_{trader_wallet[:6]}"
    
    token_symbol = trade_info.get("token_symbol", "Unknown")
    trade_type = trade_info.get("trade_type", "buy").upper()
    
    for copied in copied_trades:
        follower_wallet = copied.get("follower_wallet")
        copied_amount = copied.get("copied_amount_sol", 0)
        
        await send_copy_trade_notification(
            wallet_address=follower_wallet,
            notification_type="trade_copied",
            title=f"Trade Copied: {trade_type} {token_symbol}",
            message=f"Copied {trade_type} from {trader_name} for {copied_amount:.4f} SOL",
            data={
                "trader_wallet": trader_wallet,
                "trader_name": trader_name,
                "token_symbol": token_symbol,
                "trade_type": trade_type,
                "copied_amount_sol": copied_amount,
                "copy_trade_id": copied.get("copy_trade_id")
            }
        )


async def notify_trader_of_new_follower(
    trader_wallet: str,
    follower_wallet: str
):
    """
    Notify a trader when someone starts following them.
    """
    # Get follower count
    follower_count = await db.copy_trading_follows.count_documents({
        "trader_wallet": trader_wallet,
        "active": True
    })
    
    await send_copy_trade_notification(
        wallet_address=trader_wallet,
        notification_type="new_follower",
        title="New Follower!",
        message=f"Someone started copying your trades. You now have {follower_count} follower{'s' if follower_count != 1 else ''}.",
        data={
            "follower_wallet": follower_wallet,
            "total_followers": follower_count
        }
    )


async def notify_profit_milestone(
    wallet_address: str,
    pnl_sol: float,
    pnl_percent: float,
    token_symbol: str,
    is_from_copy: bool = False
):
    """
    Notify user of significant profit milestones.
    """
    if pnl_percent >= 50:
        milestone = "50%+ Profit!"
        emoji = "🚀"
    elif pnl_percent >= 25:
        milestone = "25%+ Profit!"
        emoji = "🎉"
    elif pnl_percent >= 10:
        milestone = "10%+ Profit"
        emoji = "✨"
    else:
        return  # No notification for small profits
    
    source = " (Copied Trade)" if is_from_copy else ""
    
    await send_copy_trade_notification(
        wallet_address=wallet_address,
        notification_type="profit_alert",
        title=f"{emoji} {milestone}",
        message=f"Your {token_symbol} position{source} is up {pnl_percent:.1f}% (+{pnl_sol:.4f} SOL)",
        data={
            "token_symbol": token_symbol,
            "pnl_sol": pnl_sol,
            "pnl_percent": pnl_percent,
            "is_from_copy": is_from_copy
        }
    )


async def notify_stop_loss_triggered(
    wallet_address: str,
    token_symbol: str,
    loss_percent: float,
    is_from_copy: bool = False
):
    """
    Notify user when stop loss is triggered.
    """
    source = " (Copied Trade)" if is_from_copy else ""
    
    await send_copy_trade_notification(
        wallet_address=wallet_address,
        notification_type="stop_loss_triggered",
        title="⚠️ Stop Loss Triggered",
        message=f"Your {token_symbol} position{source} was closed at {loss_percent:.1f}% loss to protect your capital.",
        data={
            "token_symbol": token_symbol,
            "loss_percent": loss_percent,
            "is_from_copy": is_from_copy
        }
    )


@router.get("/notifications/{wallet_address}")
async def get_notifications(
    wallet_address: str,
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False
):
    """Get copy trading notifications for a wallet."""
    query = {"wallet_address": wallet_address}
    if unread_only:
        query["read"] = False
    
    notifications = await db.copy_trade_notifications.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Count unread
    unread_count = await db.copy_trade_notifications.count_documents({
        "wallet_address": wallet_address,
        "read": False
    })
    
    return {
        "notifications": notifications,
        "count": len(notifications),
        "unread_count": unread_count
    }


@router.post("/notifications/mark-read/{wallet_address}")
async def mark_notifications_read(
    wallet_address: str,
    notification_ids: Optional[List[str]] = None
):
    """Mark notifications as read. If no IDs provided, marks all as read."""
    if notification_ids:
        # Mark specific notifications
        result = await db.copy_trade_notifications.update_many(
            {
                "wallet_address": wallet_address,
                "notification_id": {"$in": notification_ids}
            },
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
        )
    else:
        # Mark all as read
        result = await db.copy_trade_notifications.update_many(
            {"wallet_address": wallet_address, "read": False},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    return {
        "success": True,
        "marked_read": result.modified_count
    }


@router.delete("/notifications/{wallet_address}/{notification_id}")
async def delete_notification(wallet_address: str, notification_id: str):
    """Delete a specific notification."""
    result = await db.copy_trade_notifications.delete_one({
        "wallet_address": wallet_address,
        "notification_id": notification_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True, "message": "Notification deleted"}


@router.get("/notifications/settings/{wallet_address}")
async def get_notification_settings(wallet_address: str):
    """Get notification preferences for a wallet."""
    settings = await db.copy_trade_notification_settings.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    
    if not settings:
        # Return defaults
        return {
            "wallet_address": wallet_address,
            "trade_copied": True,
            "new_follower": True,
            "profit_alerts": True,
            "loss_alerts": True,
            "stop_loss_triggered": True,
            "trader_activity": True,
            "min_profit_alert_percent": 10,
            "min_loss_alert_percent": 5
        }
    
    return settings


@router.put("/notifications/settings/{wallet_address}")
async def update_notification_settings(
    wallet_address: str,
    trade_copied: Optional[bool] = None,
    new_follower: Optional[bool] = None,
    profit_alerts: Optional[bool] = None,
    loss_alerts: Optional[bool] = None,
    stop_loss_triggered: Optional[bool] = None,
    trader_activity: Optional[bool] = None,
    min_profit_alert_percent: Optional[float] = None,
    min_loss_alert_percent: Optional[float] = None
):
    """Update notification preferences."""
    update_data = {}
    
    if trade_copied is not None:
        update_data["trade_copied"] = trade_copied
    if new_follower is not None:
        update_data["new_follower"] = new_follower
    if profit_alerts is not None:
        update_data["profit_alerts"] = profit_alerts
    if loss_alerts is not None:
        update_data["loss_alerts"] = loss_alerts
    if stop_loss_triggered is not None:
        update_data["stop_loss_triggered"] = stop_loss_triggered
    if trader_activity is not None:
        update_data["trader_activity"] = trader_activity
    if min_profit_alert_percent is not None:
        update_data["min_profit_alert_percent"] = max(5, min(100, min_profit_alert_percent))
    if min_loss_alert_percent is not None:
        update_data["min_loss_alert_percent"] = max(2, min(50, min_loss_alert_percent))
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No settings to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.copy_trade_notification_settings.update_one(
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
    
    # Return updated settings
    return await get_notification_settings(wallet_address)


# ============== Performance Fee System ==============

async def calculate_and_collect_performance_fee(
    copy_trade_id: str,
    follower_wallet: str,
    trader_wallet: str,
    token_symbol: str,
    gross_profit_sol: float
) -> Optional[Dict[str, Any]]:
    """
    Calculate and record performance fee when a copied trade closes with profit.
    Returns fee record if fee was collected, None if no fee (loss or disabled).
    """
    # Only charge fee on profitable trades
    if gross_profit_sol <= 0:
        return None
    
    # Get trader's fee percentage
    trader_profile = await db.trader_profiles.find_one(
        {"wallet_address": trader_wallet},
        {"_id": 0, "performance_fee_percent": 1}
    )
    
    fee_percent = trader_profile.get("performance_fee_percent", 10.0) if trader_profile else 10.0
    
    # Ensure fee is within valid range (5-15%)
    fee_percent = max(5.0, min(15.0, fee_percent))
    
    # Calculate fee
    fee_amount = gross_profit_sol * (fee_percent / 100)
    net_profit = gross_profit_sol - fee_amount
    
    # Create fee record
    fee_id = str(uuid.uuid4())[:8]
    fee_record = {
        "fee_id": fee_id,
        "trader_wallet": trader_wallet,
        "follower_wallet": follower_wallet,
        "copy_trade_id": copy_trade_id,
        "token_symbol": token_symbol,
        "gross_profit_sol": round(gross_profit_sol, 6),
        "fee_percent": fee_percent,
        "fee_amount_sol": round(fee_amount, 6),
        "net_profit_sol": round(net_profit, 6),
        "status": "collected",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Store fee record
    await db.performance_fees.insert_one(fee_record)
    
    # Update trader's total fees earned
    await db.trader_profiles.update_one(
        {"wallet_address": trader_wallet},
        {
            "$inc": {"total_fees_earned_sol": fee_amount},
            "$set": {"last_fee_earned_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Update copy trading follow relationship with fee paid
    await db.copy_trading_follows.update_one(
        {
            "follower_wallet": follower_wallet,
            "trader_wallet": trader_wallet,
            "active": True
        },
        {"$inc": {"total_fees_paid_sol": fee_amount}}
    )
    
    # Send notification to trader about fee earned
    try:
        await send_copy_trade_notification(
            wallet_address=trader_wallet,
            notification_type="fee_earned",
            title="Performance Fee Earned! 💰",
            message=f"You earned {fee_amount:.4f} SOL ({fee_percent}% of {gross_profit_sol:.4f} SOL profit) from a follower's {token_symbol} trade.",
            data={
                "fee_id": fee_id,
                "fee_amount_sol": fee_amount,
                "gross_profit_sol": gross_profit_sol,
                "token_symbol": token_symbol
            }
        )
    except Exception as e:
        logger.warning(f"Failed to send fee notification: {e}")
    
    logger.info(f"Performance fee collected: {fee_amount:.6f} SOL ({fee_percent}%) from {follower_wallet[:8]}... to {trader_wallet[:8]}...")
    
    return fee_record


@router.get("/fees/earned/{wallet_address}")
async def get_fees_earned(
    wallet_address: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get performance fees earned by a trader from their followers' profits."""
    fees = await db.performance_fees.find(
        {"trader_wallet": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Calculate totals
    total_earned = sum(f.get("fee_amount_sol", 0) for f in fees)
    
    # Get all-time total from profile
    profile = await db.trader_profiles.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0, "total_fees_earned_sol": 1}
    )
    all_time_total = profile.get("total_fees_earned_sol", 0) if profile else 0
    
    return {
        "fees": fees,
        "count": len(fees),
        "total_in_period": round(total_earned, 6),
        "all_time_total": round(all_time_total, 6)
    }


@router.get("/fees/paid/{wallet_address}")
async def get_fees_paid(
    wallet_address: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get performance fees paid by a follower to traders they copy."""
    fees = await db.performance_fees.find(
        {"follower_wallet": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Calculate totals
    total_paid = sum(f.get("fee_amount_sol", 0) for f in fees)
    
    # Group by trader
    fees_by_trader = {}
    for fee in fees:
        trader = fee.get("trader_wallet", "unknown")
        if trader not in fees_by_trader:
            fees_by_trader[trader] = 0
        fees_by_trader[trader] += fee.get("fee_amount_sol", 0)
    
    return {
        "fees": fees,
        "count": len(fees),
        "total_paid": round(total_paid, 6),
        "fees_by_trader": {k: round(v, 6) for k, v in fees_by_trader.items()}
    }


@router.get("/fees/summary/{wallet_address}")
async def get_fee_summary(wallet_address: str):
    """Get combined fee summary for a wallet (both earned and paid)."""
    # Fees earned as a trader
    earned_pipeline = [
        {"$match": {"trader_wallet": wallet_address}},
        {"$group": {
            "_id": None,
            "total_earned": {"$sum": "$fee_amount_sol"},
            "total_trades": {"$sum": 1}
        }}
    ]
    earned_result = await db.performance_fees.aggregate(earned_pipeline).to_list(1)
    
    # Fees paid as a follower
    paid_pipeline = [
        {"$match": {"follower_wallet": wallet_address}},
        {"$group": {
            "_id": None,
            "total_paid": {"$sum": "$fee_amount_sol"},
            "total_trades": {"$sum": 1}
        }}
    ]
    paid_result = await db.performance_fees.aggregate(paid_pipeline).to_list(1)
    
    # Get profile fee percentage
    profile = await db.trader_profiles.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0, "performance_fee_percent": 1, "copy_trading_enabled": 1}
    )
    
    earned_data = earned_result[0] if earned_result else {"total_earned": 0, "total_trades": 0}
    paid_data = paid_result[0] if paid_result else {"total_paid": 0, "total_trades": 0}
    
    return {
        "wallet_address": wallet_address,
        "as_trader": {
            "total_fees_earned_sol": round(earned_data.get("total_earned", 0), 6),
            "trades_with_fees": earned_data.get("total_trades", 0),
            "current_fee_percent": profile.get("performance_fee_percent", 10.0) if profile else 10.0,
            "copy_trading_enabled": profile.get("copy_trading_enabled", False) if profile else False
        },
        "as_follower": {
            "total_fees_paid_sol": round(paid_data.get("total_paid", 0), 6),
            "trades_with_fees": paid_data.get("total_trades", 0)
        },
        "net_position_sol": round(earned_data.get("total_earned", 0) - paid_data.get("total_paid", 0), 6)
    }


@router.put("/fees/set-percentage/{wallet_address}")
async def set_performance_fee_percentage(
    wallet_address: str,
    fee_percent: float = Query(..., ge=5.0, le=15.0, description="Performance fee percentage (5-15%)")
):
    """Set the performance fee percentage for a trader (5-15% range)."""
    await db.trader_profiles.update_one(
        {"wallet_address": wallet_address},
        {
            "$set": {
                "performance_fee_percent": fee_percent,
                "fee_updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$setOnInsert": {
                "wallet_address": wallet_address,
                "display_name": f"Trader_{wallet_address[:6]}",
                "profile_visible": True,
                "copy_trading_enabled": False,
                "total_fees_earned_sol": 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "wallet_address": wallet_address,
        "performance_fee_percent": fee_percent,
        "message": f"Performance fee set to {fee_percent}%"
    }


@router.get("/fees/leaderboard")
async def get_top_fee_earners(
    period: str = Query("30d", regex="^(7d|30d|all)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """Get top traders by fees earned."""
    # Calculate period start
    now = datetime.now(timezone.utc)
    if period == "7d":
        period_start = now - timedelta(days=7)
    elif period == "30d":
        period_start = now - timedelta(days=30)
    else:
        period_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    
    period_start_str = period_start.isoformat()
    
    pipeline = [
        {"$match": {"created_at": {"$gte": period_start_str}}},
        {"$group": {
            "_id": "$trader_wallet",
            "total_earned": {"$sum": "$fee_amount_sol"},
            "total_trades": {"$sum": 1},
            "avg_fee_per_trade": {"$avg": "$fee_amount_sol"}
        }},
        {"$sort": {"total_earned": -1}},
        {"$limit": limit}
    ]
    
    results = await db.performance_fees.aggregate(pipeline).to_list(limit)
    
    leaderboard = []
    for i, trader in enumerate(results):
        # Get profile info
        profile = await db.trader_profiles.find_one(
            {"wallet_address": trader["_id"]},
            {"_id": 0, "display_name": 1, "performance_fee_percent": 1}
        )
        
        leaderboard.append({
            "rank": i + 1,
            "wallet_address": trader["_id"],
            "display_name": profile.get("display_name", f"Trader_{trader['_id'][:6]}") if profile else f"Trader_{trader['_id'][:6]}",
            "fee_percent": profile.get("performance_fee_percent", 10.0) if profile else 10.0,
            "total_earned_sol": round(trader["total_earned"], 4),
            "total_trades": trader["total_trades"],
            "avg_fee_per_trade": round(trader["avg_fee_per_trade"], 6)
        })
    
    return {
        "period": period,
        "leaderboard": leaderboard
    }
