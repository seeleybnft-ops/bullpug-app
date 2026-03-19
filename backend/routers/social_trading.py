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
    performance_fee_percent: float = Field(default=0, ge=0, le=30)  # Future: fee on profits
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
            {"_id": 0, "display_name": 1, "copy_trading_enabled": 1, "profile_visible": 1}
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
