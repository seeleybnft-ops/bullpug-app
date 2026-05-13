"""Prize pool management for leaderboard rewards."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
import logging
import uuid
from typing import Optional

from utils.database import db
from utils.config import DISTRIBUTION_WALLET
from utils.solana_payout import send_sol_payout, get_escrow_balance
from utils.tx_verify import verify_sol_transfer

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

# Standard Solana network fee for a single signed transfer.
# All transfer fees (pot payouts, coinflip payouts, leaderboard prize payouts)
# are absorbed by the jackpot share so the operator's 75% rake remains clean.
SOL_TX_FEE = 0.000005


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


async def add_to_prize_pool(amount_sol: float, source: str, details: dict = None, fee_offset_sol: float = 0.0):
    """Add 25% of revenue (rake/skin) to the prize pool.

    `fee_offset_sol` is subtracted from the jackpot contribution to absorb
    transaction fees incurred when this rake event was paid out (e.g. the pot
    winner's transfer fee). This keeps the operator's 75% rake share clean —
    the jackpot covers all on-chain transfer costs.
    """
    contribution = amount_sol * PRIZE_POOL_RATE - max(fee_offset_sol, 0.0)

    if contribution <= 0:
        return

    pool = await get_or_create_prize_pool()

    contribution_record = {
        "amount_sol": round(contribution, 9),
        "source": source,
        "original_amount": amount_sol,
        "fee_offset_sol": round(max(fee_offset_sol, 0.0), 9),
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

    logger.info(
        f"Added {contribution:.9f} SOL to prize pool from {source} "
        f"(25% of {amount_sol:.6f} minus {max(fee_offset_sol, 0.0):.9f} fee)"
    )
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
    gross_prize = pool.get("total_sol", 0)
    # Estimate fee cost for up to 10 winner transfers — absorbed by the jackpot
    # so the operator's 75% rake share never subsidises payout fees.
    estimated_fees = SOL_TX_FEE * 10
    total_prize = max(0.0, gross_prize - estimated_fees)
    
    # Helper function to reset timer and leaderboard
    async def reset_cycle():
        next_payout = datetime.now(timezone.utc) + timedelta(days=PAYOUT_INTERVAL_DAYS)
        
        # Mark old pool as inactive
        await db.prize_pool.update_one(
            {"_id": pool["_id"]},
            {"$set": {
                "active": False,
                "paid_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Create new pool with fresh timer
        new_pool = {
            "active": True,
            "total_sol": 0.0,
            "contributions": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "next_payout_at": next_payout.isoformat(),
            "payout_interval_days": PAYOUT_INTERVAL_DAYS
        }
        await db.prize_pool.insert_one(new_pool)
        
        # Reset BOTH leaderboard collections
        await db.game_leaderboard.update_many({}, {"$set": {"high_score": 0}})
        # Clear the main leaderboard scores for old cycles (new cycle_start means fresh start)
        # Scores from previous cycles remain for history but won't show in current leaderboard
        
        logger.info(f"Prize cycle reset - next payout at {next_payout.isoformat()}, leaderboards cleared")
        return next_payout
    
    # If prize pool too small, still reset the cycle
    if total_prize < 0.001:
        next_payout = await reset_cycle()
        return {
            "success": True, 
            "message": "No prize to distribute - cycle reset, leaderboard cleared",
            "total_sol": total_prize,
            "next_payout_at": next_payout.isoformat(),
            "leaderboard_reset": True
        }
    
    # Get top 10 players
    leaderboard = await db.game_leaderboard.find(
        {},
        {"_id": 0, "wallet_address": 1, "display_name": 1, "high_score": 1}
    ).sort("high_score", -1).limit(10).to_list(10)
    
    if not leaderboard:
        next_payout = await reset_cycle()
        return {
            "success": True, 
            "message": "No players on leaderboard - cycle reset",
            "next_payout_at": next_payout.isoformat(),
            "leaderboard_reset": True
        }
    
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
    
    # Reset cycle (timer + leaderboard)
    next_payout = await reset_cycle()
    
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


# ─────────────────────────────────────────── Tip the Pot

class TipPotRequest(BaseModel):
    wallet_address: str = Field(..., min_length=20, max_length=64)
    amount_sol: float = Field(..., gt=0)
    tx_signature: str = Field(..., min_length=10, max_length=200)
    display_name: Optional[str] = None


@router.post("/tip")
async def tip_the_pot(req: TipPotRequest):
    """Record a community tip to the jackpot.

    The client transfers SOL directly to ``DISTRIBUTION_WALLET`` via Phantom
    and then calls this endpoint with the resulting tx signature. **All of
    the tipped amount goes to the prize pool** (the operator does not take a
    rake on tips) so the gesture is fully credited to the runners.
    """
    if req.amount_sol < 0.001:
        raise HTTPException(status_code=400, detail="Minimum tip is 0.001 SOL")
    if req.amount_sol > 100:
        raise HTTPException(status_code=400, detail="Maximum tip is 100 SOL — split it if needed")

    # Idempotent on tx_signature so retries don't double-credit.
    existing = await db.pot_tips.find_one(
        {"tx_signature": req.tx_signature},
        {"_id": 0, "id": 1, "amount_sol": 1}
    )
    if existing:
        return {
            "success": True,
            "duplicate": True,
            "tip_id": existing.get("id"),
            "amount_sol": existing.get("amount_sol"),
        }

    # On-chain verification — make sure the user actually paid the escrow.
    ok, reason = await verify_sol_transfer(
        tx_signature=req.tx_signature,
        expected_recipient=DISTRIBUTION_WALLET,
        expected_amount_sol=req.amount_sol,
        expected_sender=req.wallet_address,
    )
    if not ok:
        logger.warning(
            "Tip verification failed: %s for %s (%.6f SOL): %s",
            req.tx_signature, req.wallet_address, req.amount_sol, reason,
        )
        raise HTTPException(status_code=400, detail=f"Tip verification failed: {reason}")

    # Append to the active pool (100% of the tip — no rake split).
    pool = await get_or_create_prize_pool()
    contribution_record = {
        "amount_sol": round(req.amount_sol, 9),
        "source": "community_tip",
        "original_amount": req.amount_sol,
        "fee_offset_sol": 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {
            "wallet": req.wallet_address,
            "tx_signature": req.tx_signature,
            "display_name": req.display_name or "",
        },
    }
    await db.prize_pool.update_one(
        {"_id": pool["_id"]},
        {
            "$inc": {"total_sol": req.amount_sol},
            "$push": {"contributions": contribution_record},
        },
    )

    # Independent tip ledger for the public leaderboard / Top Tippers panel.
    tip_doc = {
        "id": str(uuid.uuid4()),
        "wallet_address": req.wallet_address,
        "display_name": (req.display_name or "")[:24],
        "amount_sol": round(req.amount_sol, 9),
        "tx_signature": req.tx_signature,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.pot_tips.insert_one(tip_doc)

    # Refresh pool total for the response.
    refreshed = await db.prize_pool.find_one(
        {"_id": pool["_id"]}, {"_id": 0, "total_sol": 1}
    )
    new_total = round(refreshed.get("total_sol", 0), 6) if refreshed else 0

    logger.info(
        "Community tip recorded: %.6f SOL from %s (tx %s) — new pool total %.6f SOL",
        req.amount_sol, req.wallet_address, req.tx_signature, new_total
    )

    return {
        "success": True,
        "duplicate": False,
        "tip_id": tip_doc["id"],
        "amount_sol": tip_doc["amount_sol"],
        "new_pool_total_sol": new_total,
    }


@router.get("/top-tippers")
async def get_top_tippers(limit: int = 10):
    """Aggregate the top community tippers for the current pool cycle."""
    pool = await get_or_create_prize_pool()
    cycle_start = pool.get("created_at")
    match_stage = {}
    if cycle_start:
        match_stage["created_at"] = {"$gte": cycle_start}

    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
        {"$group": {
            "_id": "$wallet_address",
            "total_sol": {"$sum": "$amount_sol"},
            "display_name": {"$last": "$display_name"},
            "tip_count": {"$sum": 1},
            "last_tip_at": {"$max": "$created_at"},
        }},
        {"$sort": {"total_sol": -1}},
        {"$limit": int(limit)},
    ]
    rows = await db.pot_tips.aggregate(pipeline).to_list(int(limit))
    tippers = [{
        "wallet_address": r["_id"],
        "display_name": (r.get("display_name") or "")[:24],
        "total_sol": round(r.get("total_sol", 0), 6),
        "tip_count": r.get("tip_count", 0),
        "last_tip_at": r.get("last_tip_at"),
    } for r in rows]

    return {"tippers": tippers, "cycle_start": cycle_start}
