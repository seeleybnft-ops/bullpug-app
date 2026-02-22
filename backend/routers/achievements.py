"""Achievements & Community Benchmarks Router

Provides endpoints for:
- Achievement badges tracking (soulbound-style, DB-tracked)
- Win/loss streak milestones
- Share card generation
- Community benchmarks with opt-in anonymized stats
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from utils.database import db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/achievements", tags=["achievements"])

# Achievement Badge Definitions
BADGES = {
    # Streak Badges
    "streak_3": {
        "id": "streak_3",
        "name": "Hot Start",
        "description": "3-day winning streak",
        "icon": "🔥",
        "category": "streak",
        "requirement": {"type": "win_streak", "value": 3},
        "rarity": "common",
        "color": "#FF6B35"
    },
    "streak_7": {
        "id": "streak_7",
        "name": "On Fire",
        "description": "7-day winning streak",
        "icon": "💎",
        "category": "streak",
        "requirement": {"type": "win_streak", "value": 7},
        "rarity": "rare",
        "color": "#00C2FF"
    },
    "streak_14": {
        "id": "streak_14",
        "name": "Unstoppable",
        "description": "14-day winning streak",
        "icon": "👑",
        "category": "streak",
        "requirement": {"type": "win_streak", "value": 14},
        "rarity": "epic",
        "color": "#D946EF"
    },
    "streak_30": {
        "id": "streak_30",
        "name": "Legend",
        "description": "30-day winning streak",
        "icon": "🏆",
        "category": "streak",
        "requirement": {"type": "win_streak", "value": 30},
        "rarity": "legendary",
        "color": "#F5D300"
    },
    
    # Trade Count Badges
    "trades_10": {
        "id": "trades_10",
        "name": "Getting Started",
        "description": "10 trades logged",
        "icon": "📝",
        "category": "volume",
        "requirement": {"type": "trade_count", "value": 10},
        "rarity": "common",
        "color": "#00FFA3"
    },
    "trades_30": {
        "id": "trades_30",
        "name": "Active Trader",
        "description": "30 trades logged",
        "icon": "📊",
        "category": "volume",
        "requirement": {"type": "trade_count", "value": 30},
        "rarity": "rare",
        "color": "#00C2FF"
    },
    "trades_100": {
        "id": "trades_100",
        "name": "Veteran",
        "description": "100 trades logged",
        "icon": "🎖️",
        "category": "volume",
        "requirement": {"type": "trade_count", "value": 100},
        "rarity": "epic",
        "color": "#D946EF"
    },
    "trades_500": {
        "id": "trades_500",
        "name": "Trading Machine",
        "description": "500 trades logged",
        "icon": "🤖",
        "category": "volume",
        "requirement": {"type": "trade_count", "value": 500},
        "rarity": "legendary",
        "color": "#F5D300"
    },
    
    # Win Rate Badges
    "winrate_60": {
        "id": "winrate_60",
        "name": "Consistent",
        "description": "60%+ win rate (min 20 trades)",
        "icon": "✅",
        "category": "performance",
        "requirement": {"type": "win_rate", "value": 60, "min_trades": 20},
        "rarity": "common",
        "color": "#00FFA3"
    },
    "winrate_70": {
        "id": "winrate_70",
        "name": "Sharp Trader",
        "description": "70%+ win rate (min 20 trades)",
        "icon": "🎯",
        "category": "performance",
        "requirement": {"type": "win_rate", "value": 70, "min_trades": 20},
        "rarity": "rare",
        "color": "#00C2FF"
    },
    "winrate_80": {
        "id": "winrate_80",
        "name": "Elite",
        "description": "80%+ win rate (min 30 trades)",
        "icon": "⭐",
        "category": "performance",
        "requirement": {"type": "win_rate", "value": 80, "min_trades": 30},
        "rarity": "epic",
        "color": "#D946EF"
    },
    "winrate_90": {
        "id": "winrate_90",
        "name": "Master Trader",
        "description": "90%+ win rate (min 50 trades)",
        "icon": "🌟",
        "category": "performance",
        "requirement": {"type": "win_rate", "value": 90, "min_trades": 50},
        "rarity": "legendary",
        "color": "#F5D300"
    },
    
    # PnL Badges
    "pnl_1k": {
        "id": "pnl_1k",
        "name": "First Grand",
        "description": "$1,000+ total profit",
        "icon": "💰",
        "category": "profit",
        "requirement": {"type": "total_pnl", "value": 1000},
        "rarity": "common",
        "color": "#00FFA3"
    },
    "pnl_10k": {
        "id": "pnl_10k",
        "name": "Five Figures",
        "description": "$10,000+ total profit",
        "icon": "💎",
        "category": "profit",
        "requirement": {"type": "total_pnl", "value": 10000},
        "rarity": "rare",
        "color": "#00C2FF"
    },
    "pnl_100k": {
        "id": "pnl_100k",
        "name": "Six Figures",
        "description": "$100,000+ total profit",
        "icon": "🏦",
        "category": "profit",
        "requirement": {"type": "total_pnl", "value": 100000},
        "rarity": "epic",
        "color": "#D946EF"
    },
    
    # Special Badges
    "first_trade": {
        "id": "first_trade",
        "name": "Genesis",
        "description": "Logged your first trade",
        "icon": "🌱",
        "category": "milestone",
        "requirement": {"type": "trade_count", "value": 1},
        "rarity": "common",
        "color": "#00FFA3"
    },
    "multi_chain": {
        "id": "multi_chain",
        "name": "Chain Hopper",
        "description": "Traded on 3+ chains",
        "icon": "🔗",
        "category": "milestone",
        "requirement": {"type": "chain_count", "value": 3},
        "rarity": "rare",
        "color": "#00C2FF"
    },
}


class UserStats(BaseModel):
    """User trading statistics."""
    wallet_address: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    current_win_streak: int
    current_loss_streak: int
    best_win_streak: int
    total_pnl: float
    chains_traded: List[str]
    badges_earned: List[str]
    community_opt_in: bool = False


class BadgeEarned(BaseModel):
    """Badge earned by user."""
    badge_id: str
    earned_at: str
    share_url: Optional[str] = None


class CommunityBenchmarks(BaseModel):
    """Aggregated community statistics."""
    total_users: int
    total_trades: int
    average_win_rate: float
    average_streak: float
    percentile_win_rate: Optional[float] = None
    percentile_streak: Optional[float] = None
    top_streaks: List[Dict[str, Any]]
    common_assets: List[Dict[str, Any]]


async def get_user_stats(wallet_address: str) -> Dict[str, Any]:
    """Calculate user statistics from their trades."""
    trades = await db.journal_trades.find(
        {"wallet_address": wallet_address, "status": {"$ne": "draft"}}
    ).sort("date_entry", 1).to_list(1000)
    
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "current_win_streak": 0,
            "current_loss_streak": 0,
            "best_win_streak": 0,
            "total_pnl": 0,
            "chains_traded": [],
            "badges_earned": []
        }
    
    winning = 0
    losing = 0
    total_pnl = 0
    chains = set()
    
    current_win_streak = 0
    current_loss_streak = 0
    best_win_streak = 0
    temp_streak = 0
    last_was_win = None
    
    for trade in trades:
        pnl = trade.get("pnl", 0) or 0
        total_pnl += pnl
        
        chain = trade.get("chain", "unknown")
        chains.add(chain)
        
        is_win = pnl > 0
        if is_win:
            winning += 1
            if last_was_win == True or last_was_win is None:
                temp_streak += 1
            else:
                temp_streak = 1
            best_win_streak = max(best_win_streak, temp_streak)
        else:
            losing += 1
            temp_streak = 0
        
        last_was_win = is_win
    
    # Calculate current streaks from most recent trades
    current_win_streak = 0
    current_loss_streak = 0
    for trade in reversed(trades):
        pnl = trade.get("pnl", 0) or 0
        if pnl > 0:
            if current_loss_streak == 0:
                current_win_streak += 1
            else:
                break
        else:
            if current_win_streak == 0:
                current_loss_streak += 1
            else:
                break
    
    total = winning + losing
    win_rate = (winning / total * 100) if total > 0 else 0
    
    return {
        "total_trades": total,
        "winning_trades": winning,
        "losing_trades": losing,
        "win_rate": round(win_rate, 1),
        "current_win_streak": current_win_streak,
        "current_loss_streak": current_loss_streak,
        "best_win_streak": best_win_streak,
        "total_pnl": round(total_pnl, 2),
        "chains_traded": list(chains)
    }


async def check_badge_eligibility(stats: Dict[str, Any]) -> List[str]:
    """Check which badges a user is eligible for."""
    eligible = []
    
    for badge_id, badge in BADGES.items():
        req = badge["requirement"]
        req_type = req["type"]
        
        if req_type == "win_streak":
            if stats["best_win_streak"] >= req["value"]:
                eligible.append(badge_id)
        
        elif req_type == "trade_count":
            if stats["total_trades"] >= req["value"]:
                eligible.append(badge_id)
        
        elif req_type == "win_rate":
            min_trades = req.get("min_trades", 0)
            if stats["total_trades"] >= min_trades and stats["win_rate"] >= req["value"]:
                eligible.append(badge_id)
        
        elif req_type == "total_pnl":
            if stats["total_pnl"] >= req["value"]:
                eligible.append(badge_id)
        
        elif req_type == "chain_count":
            if len(stats["chains_traded"]) >= req["value"]:
                eligible.append(badge_id)
    
    return eligible


@router.get("/badges")
async def get_all_badges():
    """Get all available badges and their requirements."""
    return {
        "badges": list(BADGES.values()),
        "categories": ["streak", "volume", "performance", "profit", "milestone"]
    }


@router.get("/user/{wallet_address}")
async def get_user_achievements(wallet_address: str):
    """Get user's stats and earned badges."""
    stats = await get_user_stats(wallet_address)
    eligible_badges = await check_badge_eligibility(stats)
    
    # Get already earned badges
    user_badges = await db.user_badges.find(
        {"wallet_address": wallet_address}
    ).to_list(100)
    earned_ids = [b["badge_id"] for b in user_badges]
    
    # Award new badges
    new_badges = []
    for badge_id in eligible_badges:
        if badge_id not in earned_ids:
            badge_record = {
                "wallet_address": wallet_address,
                "badge_id": badge_id,
                "earned_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.user_badges.insert_one(badge_record)
            new_badges.append(badge_id)
            earned_ids.append(badge_id)
    
    # Build badge details
    badges_detail = []
    for badge_id in earned_ids:
        if badge_id in BADGES:
            badge = BADGES[badge_id].copy()
            user_badge = next((b for b in user_badges if b["badge_id"] == badge_id), None)
            badge["earned_at"] = user_badge["earned_at"] if user_badge else datetime.now(timezone.utc).isoformat()
            badges_detail.append(badge)
    
    return {
        "wallet_address": wallet_address,
        "stats": stats,
        "badges": badges_detail,
        "new_badges": [BADGES[b] for b in new_badges if b in BADGES],
        "total_badges": len(earned_ids),
        "available_badges": len(BADGES)
    }


@router.get("/share-data/{wallet_address}")
async def get_share_data(wallet_address: str):
    """Get data for generating shareable card."""
    stats = await get_user_stats(wallet_address)
    eligible_badges = await check_badge_eligibility(stats)
    
    # Get user's display name if set
    profile = await db.profiles.find_one({"wallet_address": wallet_address})
    display_name = profile.get("display_name") if profile else None
    
    # Get most impressive badge
    best_badge = None
    rarity_order = ["legendary", "epic", "rare", "common"]
    for rarity in rarity_order:
        for badge_id in eligible_badges:
            if BADGES.get(badge_id, {}).get("rarity") == rarity:
                best_badge = BADGES[badge_id]
                break
        if best_badge:
            break
    
    return {
        "wallet_address": wallet_address,
        "display_name": display_name,
        "stats": {
            "win_streak": stats["current_win_streak"],
            "best_streak": stats["best_win_streak"],
            "win_rate": stats["win_rate"],
            "total_pnl": stats["total_pnl"],
            "total_trades": stats["total_trades"],
        },
        "best_badge": best_badge,
        "share_text": f"My {stats['best_win_streak']}-day win streak on BullPug Journal! +${stats['total_pnl']:,.0f} PnL | {stats['win_rate']}% win rate | Check yours: https://bullpug.com/journal #BullPug #CryptoJournal"
    }


@router.post("/opt-in")
async def toggle_community_opt_in(
    wallet_address: str = Body(..., embed=True),
    opt_in: bool = Body(..., embed=True)
):
    """Toggle community benchmark opt-in status."""
    await db.community_opt_in.update_one(
        {"wallet_address": wallet_address},
        {
            "$set": {
                "wallet_address": wallet_address,
                "opt_in": opt_in,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"success": True, "opt_in": opt_in}


@router.get("/opt-in/{wallet_address}")
async def get_opt_in_status(wallet_address: str):
    """Get user's opt-in status."""
    record = await db.community_opt_in.find_one({"wallet_address": wallet_address})
    return {"opt_in": record.get("opt_in", False) if record else False}


@router.get("/community/benchmarks")
async def get_community_benchmarks(
    wallet_address: Optional[str] = Query(None, description="User wallet for percentile calculation")
):
    """Get aggregated community statistics from opted-in users."""
    # Get all opted-in users
    opted_in = await db.community_opt_in.find({"opt_in": True}).to_list(10000)
    opted_in_wallets = [u["wallet_address"] for u in opted_in]
    
    if not opted_in_wallets:
        return CommunityBenchmarks(
            total_users=0,
            total_trades=0,
            average_win_rate=0,
            average_streak=0,
            top_streaks=[],
            common_assets=[]
        )
    
    # Calculate stats for all opted-in users
    all_stats = []
    all_win_rates = []
    all_streaks = []
    total_trades = 0
    asset_counts = {}
    
    for wallet in opted_in_wallets[:100]:  # Limit to 100 for performance
        stats = await get_user_stats(wallet)
        if stats["total_trades"] > 0:
            all_stats.append(stats)
            all_win_rates.append(stats["win_rate"])
            all_streaks.append(stats["best_win_streak"])
            total_trades += stats["total_trades"]
    
    if not all_stats:
        return CommunityBenchmarks(
            total_users=0,
            total_trades=0,
            average_win_rate=0,
            average_streak=0,
            top_streaks=[],
            common_assets=[]
        )
    
    avg_win_rate = sum(all_win_rates) / len(all_win_rates)
    avg_streak = sum(all_streaks) / len(all_streaks)
    
    # Calculate percentiles for requesting user
    percentile_win_rate = None
    percentile_streak = None
    
    if wallet_address:
        user_stats = await get_user_stats(wallet_address)
        if user_stats["total_trades"] > 0:
            # Calculate percentile (what % of users you beat)
            below_wr = sum(1 for wr in all_win_rates if wr < user_stats["win_rate"])
            percentile_win_rate = round((below_wr / len(all_win_rates)) * 100, 1)
            
            below_streak = sum(1 for s in all_streaks if s < user_stats["best_win_streak"])
            percentile_streak = round((below_streak / len(all_streaks)) * 100, 1)
    
    # Top streaks (anonymized)
    sorted_stats = sorted(all_stats, key=lambda x: x["best_win_streak"], reverse=True)
    top_streaks = [
        {
            "rank": i + 1,
            "streak": s["best_win_streak"],
            "win_rate": s["win_rate"],
            "trades": s["total_trades"]
        }
        for i, s in enumerate(sorted_stats[:10])
    ]
    
    # Get common assets from trades
    trades = await db.journal_trades.find(
        {"wallet_address": {"$in": opted_in_wallets}}
    ).to_list(1000)
    
    for trade in trades:
        asset = trade.get("asset", "Unknown")
        asset_counts[asset] = asset_counts.get(asset, 0) + 1
    
    common_assets = sorted(
        [{"asset": k, "count": v} for k, v in asset_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:10]
    
    return CommunityBenchmarks(
        total_users=len(all_stats),
        total_trades=total_trades,
        average_win_rate=round(avg_win_rate, 1),
        average_streak=round(avg_streak, 1),
        percentile_win_rate=percentile_win_rate,
        percentile_streak=percentile_streak,
        top_streaks=top_streaks,
        common_assets=common_assets
    )


@router.get("/leaderboard")
async def get_leaderboard(
    sort_by: str = Query("streak", description="Sort by: streak, win_rate, pnl, trades"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get public leaderboard of opted-in users."""
    # Get all opted-in users
    opted_in = await db.community_opt_in.find({"opt_in": True}).to_list(10000)
    opted_in_wallets = [u["wallet_address"] for u in opted_in]
    
    if not opted_in_wallets:
        return {"leaderboard": [], "total_participants": 0}
    
    # Calculate stats for all
    user_stats = []
    for wallet in opted_in_wallets[:100]:
        stats = await get_user_stats(wallet)
        if stats["total_trades"] >= 5:  # Min 5 trades to appear
            # Get display name
            profile = await db.profiles.find_one({"wallet_address": wallet})
            display_name = profile.get("display_name") if profile else None
            
            user_stats.append({
                "wallet": f"{wallet[:4]}...{wallet[-4:]}",
                "display_name": display_name,
                "streak": stats["best_win_streak"],
                "current_streak": stats["current_win_streak"],
                "win_rate": stats["win_rate"],
                "pnl": stats["total_pnl"],
                "trades": stats["total_trades"],
            })
    
    # Sort
    sort_key = {
        "streak": lambda x: x["streak"],
        "win_rate": lambda x: x["win_rate"],
        "pnl": lambda x: x["pnl"],
        "trades": lambda x: x["trades"],
    }.get(sort_by, lambda x: x["streak"])
    
    sorted_stats = sorted(user_stats, key=sort_key, reverse=True)[:limit]
    
    # Add ranks
    for i, stat in enumerate(sorted_stats):
        stat["rank"] = i + 1
    
    return {
        "leaderboard": sorted_stats,
        "total_participants": len(user_stats),
        "sort_by": sort_by
    }
