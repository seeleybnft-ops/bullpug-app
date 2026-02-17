"""Prize pool management for leaderboard rewards."""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional

from utils.database import db
from utils.config import DISTRIBUTION_WALLET
from utils.solana_payout import send_sol_payout, get_escrow_balance

router = APIRouter(prefix="/prize-pool", tags=["prize-pool"])
logger = logging.getLogger(__name__)

# Prize distribution percentages for top 10
PRIZE_DISTRIBUTION = {
    1: 0.25,   # 25%
    2: 0.15,   # 15%
    3: 0.12,   # 12%
    4: 0.10,   # 10%
    5: 0.09,   # 9%
    6: 0.08,   # 8%
    7: 0.07,   # 7%
    8: 0.06,   # 6%
    9: 0.05,   # 5%
    10: 0.03,  # 3%
}

# Prize pool contribution rate (25% of revenue)
PRIZE_POOL_RATE = 0.25

# Payout interval in days
PAYOUT_INTERVAL_DAYS = 3


async def get_or_create_prize_pool():
    """Get current prize pool or create if doesn't exist."""
    pool = await db.prize_pool.find_one({"active": True})
    
    if not pool:
        # Create new prize pool with next payout in 3 days
        next_payout = datetime.now(timezone.utc) + timedelta(days=PAYOUT_INTERVAL_DAYS)
        pool = {
            "active": True,
            "total_sol": 0.0,
            "contributions": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "next_payout_at": next_payout.isoformat(),
            "payout_interval_days": PAYOUT_INTERVAL_DAYS
        }
        await db.prize_pool.insert_one(pool)
        pool = await db.prize_pool.find_one({"active": True})
    
    return pool


async def add_to_prize_pool(amount_sol: float, source: str, details: dict = None):
    """Add funds to the prize pool (25% of revenue)."""
    contribution = amount_sol * PRIZE_POOL_RATE
    
    if contribution <= 0:
        return
    
    pool = await get_or_create_prize_pool()
    
    contribution_record = {
        "amount_sol": round(contribution, 6),
        "source": source,  # "rake" or "skin_purchase"
        "original_amount": amount_sol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details or {}
    }
    
    await db.prize_pool.update_one(
        {"_id": pool["_id"]},
        {
            "$inc": {"total_sol": contribution},
            "$push": {"contributions": contribution_record}
        }
    )
    
    logger.info(f"Added {contribution:.6f} SOL to prize pool from {source} (25% of {amount_sol:.6f})")
    return contribution


@router.get("/status")
async def get_prize_pool_status():
    """Get current prize pool status with countdown and breakdown."""
    pool = await get_or_create_prize_pool()
    
    # Calculate time remaining
    next_payout = datetime.fromisoformat(pool["next_payout_at"].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    time_remaining = next_payout - now
    
    # If timer expired, it will be handled by the scheduler
    seconds_remaining = max(0, int(time_remaining.total_seconds()))
    
    # Calculate prize breakdown
    total = pool.get("total_sol", 0)
    breakdown = []
    for rank, percentage in PRIZE_DISTRIBUTION.items():
        breakdown.append({
            "rank": rank,
            "percentage": int(percentage * 100),
            "amount_sol": round(total * percentage, 6)
        })
    
    return {
        "total_sol": round(total, 6),
        "next_payout_at": pool["next_payout_at"],
        "seconds_remaining": seconds_remaining,
        "payout_interval_days": PAYOUT_INTERVAL_DAYS,
        "prize_breakdown": breakdown,
        "escrow_wallet": DISTRIBUTION_WALLET
    }


@router.get("/leaderboard")
async def get_leaderboard_for_prizes():
    """Get current leaderboard for prize distribution."""
    # Get top 10 players from game leaderboard
    leaderboard = await db.game_leaderboard.find(
        {},
        {"_id": 0, "wallet_address": 1, "display_name": 1, "high_score": 1, "rank": 1}
    ).sort("high_score", -1).limit(10).to_list(10)
    
    # Add rank if not present
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
        entry["prize_percentage"] = int(PRIZE_DISTRIBUTION.get(i + 1, 0) * 100)
    
    return {"leaderboard": leaderboard}


@router.post("/execute-payout")
async def execute_prize_payout(admin_key: str = None):
    """Execute prize pool payout to top 10 players."""
    from utils.config import ADMIN_WALLETS
    
    # Admin check (can be triggered manually or by scheduler)
    if admin_key and admin_key not in ADMIN_WALLETS:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    pool = await get_or_create_prize_pool()
    total_prize = pool.get("total_sol", 0)
    
    if total_prize < 0.001:
        return {"success": False, "message": "Prize pool too small to distribute", "total_sol": total_prize}
    
    # Get top 10 players
    leaderboard = await db.game_leaderboard.find(
        {},
        {"_id": 0, "wallet_address": 1, "display_name": 1, "high_score": 1}
    ).sort("high_score", -1).limit(10).to_list(10)
    
    if not leaderboard:
        return {"success": False, "message": "No players on leaderboard"}
    
    # Execute payouts
    winners = []
    total_paid = 0
    
    for i, player in enumerate(leaderboard):
        rank = i + 1
        percentage = PRIZE_DISTRIBUTION.get(rank, 0)
        prize_amount = round(total_prize * percentage, 6)
        
        if prize_amount < 0.000001:
            continue
        
        wallet = player.get("wallet_address")
        if not wallet:
            continue
        
        # Send payout
        success, result = await send_sol_payout(
            recipient_wallet=wallet,
            amount_sol=prize_amount,
            memo=f"Bullpug Leaderboard #{rank} Prize"
        )
        
        winner_entry = {
            "rank": rank,
            "wallet_address": wallet,
            "display_name": player.get("display_name", "Unknown"),
            "high_score": player.get("high_score", 0),
            "prize_sol": prize_amount,
            "percentage": int(percentage * 100),
            "payout_success": success,
            "tx_signature": result if success else None,
            "error": result if not success else None
        }
        winners.append(winner_entry)
        
        if success:
            total_paid += prize_amount
            logger.info(f"Paid #{rank} {player.get('display_name')}: {prize_amount} SOL - TX: {result}")
        else:
            logger.error(f"Failed to pay #{rank} {player.get('display_name')}: {result}")
    
    # Record payout history
    payout_record = {
        "payout_at": datetime.now(timezone.utc).isoformat(),
        "total_pool_sol": total_prize,
        "total_paid_sol": total_paid,
        "winners": winners,
        "pool_id": str(pool["_id"])
    }
    await db.prize_payouts.insert_one(payout_record)
    
    # Reset prize pool and set next payout time
    next_payout = datetime.now(timezone.utc) + timedelta(days=PAYOUT_INTERVAL_DAYS)
    await db.prize_pool.update_one(
        {"_id": pool["_id"]},
        {"$set": {
            "active": False,
            "paid_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Create new pool
    new_pool = {
        "active": True,
        "total_sol": 0.0,
        "contributions": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "next_payout_at": next_payout.isoformat(),
        "payout_interval_days": PAYOUT_INTERVAL_DAYS
    }
    await db.prize_pool.insert_one(new_pool)
    
    # Reset weekly leaderboard scores
    await db.game_leaderboard.update_many({}, {"$set": {"high_score": 0}})
    
    logger.info(f"Prize payout complete: {total_paid:.6f} SOL distributed to {len([w for w in winners if w['payout_success']])} winners")
    
    return {
        "success": True,
        "total_pool_sol": total_prize,
        "total_paid_sol": total_paid,
        "winners": winners,
        "next_payout_at": next_payout.isoformat()
    }


@router.get("/recent-winners")
async def get_recent_winners():
    """Get recent prize payout winners for display on home page."""
    # Get the most recent payout
    recent_payout = await db.prize_payouts.find_one(
        {},
        sort=[("payout_at", -1)]
    )
    
    if not recent_payout:
        return {
            "has_winners": False,
            "winners": [],
            "payout_at": None,
            "total_pool_sol": 0
        }
    
    # Get successful winners only
    winners = [w for w in recent_payout.get("winners", []) if w.get("payout_success")]
    
    return {
        "has_winners": len(winners) > 0,
        "winners": winners[:10],  # Top 10
        "payout_at": recent_payout.get("payout_at"),
        "total_pool_sol": recent_payout.get("total_pool_sol", 0),
        "total_paid_sol": recent_payout.get("total_paid_sol", 0)
    }


@router.get("/history")
async def get_payout_history(limit: int = 10):
    """Get prize payout history."""
    payouts = await db.prize_payouts.find(
        {},
        {"_id": 0}
    ).sort("payout_at", -1).limit(limit).to_list(limit)
    
    return {"payouts": payouts}
