"""Leaderboard routes for the Speed Run game."""

from fastapi import APIRouter
import uuid
from datetime import datetime, timezone, timedelta

from models.schemas import LeaderboardSubmitRequest
from utils.database import db

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

# Use 3-day cycle synced with prize pool
CYCLE_DAYS = 3


async def get_current_cycle_start():
    """Get the start of the current 3-day cycle from the prize pool."""
    pool = await db.prize_pool.find_one({"active": True}, sort=[("created_at", -1)])
    if pool and pool.get("created_at"):
        return pool["created_at"]
    # Fallback to current time if no pool
    return datetime.now(timezone.utc).isoformat()


async def get_next_payout_time():
    """Get the next payout time from the prize pool."""
    pool = await db.prize_pool.find_one({"active": True}, sort=[("created_at", -1)])
    if pool and pool.get("next_payout_at"):
        return pool["next_payout_at"]
    # Fallback: 3 days from now
    return (datetime.now(timezone.utc) + timedelta(days=CYCLE_DAYS)).isoformat()


@router.get("")
async def get_leaderboard(limit: int = 10):
    """Get leaderboard for current 3-day prize cycle."""
    cycle_start = await get_current_cycle_start()
    next_payout = await get_next_payout_time()
    
    # Parse the next payout time
    try:
        next_payout_dt = datetime.fromisoformat(next_payout.replace('Z', '+00:00'))
        seconds_remaining = max(0, (next_payout_dt - datetime.now(timezone.utc)).total_seconds())
        days_until_reset = int(seconds_remaining // 86400)
    except:
        days_until_reset = CYCLE_DAYS
    
    # Get scores from the current cycle
    leaderboard = await db.leaderboard.find(
        {"cycle_start": cycle_start},
        {"_id": 0}
    ).sort("score", -1).to_list(limit)
    
    return {
        "leaderboard": leaderboard,
        "cycle_start": cycle_start,
        "next_payout": next_payout,
        "days_until_reset": days_until_reset
    }


@router.post("/submit")
async def submit_score(data: LeaderboardSubmitRequest):
    """Submit a score to the leaderboard."""
    cycle_start = await get_current_cycle_start()
    
    existing = await db.leaderboard.find_one({
        "player_name": data.player_name,
        "cycle_start": cycle_start
    })
    
    if existing:
        if data.score > existing.get("score", 0):
            await db.leaderboard.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "score": data.score,
                    "moonCheese": data.moonCheese,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    else:
        entry = {
            "id": str(uuid.uuid4()),
            "player_name": data.player_name,
            "score": data.score,
            "mooncakes": data.mooncakes,
            "cycle_start": cycle_start,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.leaderboard.insert_one(entry)
    
    # Also update the game_leaderboard collection (used by prize pool)
    existing_pool = await db.game_leaderboard.find_one({
        "display_name": data.player_name
    })
    
    if existing_pool:
        if data.score > existing_pool.get("high_score", 0):
            await db.game_leaderboard.update_one(
                {"display_name": data.player_name},
                {"$set": {
                    "high_score": data.score,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    else:
        await db.game_leaderboard.insert_one({
            "display_name": data.player_name,
            "high_score": data.score,
            "wallet_address": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Get rank
    higher_scores = await db.leaderboard.count_documents({
        "cycle_start": cycle_start,
        "score": {"$gt": data.score}
    })
    rank = higher_scores + 1
    
    return {"rank": rank, "score": data.score, "moonCheese": data.moonCheese}
