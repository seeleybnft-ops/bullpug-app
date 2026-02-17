"""Leaderboard routes for the Speed Run game."""

from fastapi import APIRouter
import uuid
from datetime import datetime, timezone, timedelta

from ..models.schemas import LeaderboardSubmitRequest
from ..utils.database import db

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def get_week_start():
    """Get the start of the current week (Monday 00:00 UTC)."""
    now = datetime.now(timezone.utc)
    days_since_monday = now.weekday()
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
    return week_start


@router.get("")
async def get_leaderboard(limit: int = 10):
    """Get weekly leaderboard."""
    week_start = get_week_start()
    next_reset = week_start + timedelta(days=7)
    days_until_reset = (next_reset - datetime.now(timezone.utc)).days
    
    leaderboard = await db.leaderboard.find(
        {"week_start": week_start.isoformat()},
        {"_id": 0}
    ).sort("score", -1).to_list(limit)
    
    return {
        "leaderboard": leaderboard,
        "week_start": week_start.isoformat(),
        "next_reset": next_reset.isoformat(),
        "days_until_reset": max(0, days_until_reset)
    }


@router.post("/submit")
async def submit_score(data: LeaderboardSubmitRequest):
    """Submit a score to the leaderboard."""
    week_start = get_week_start()
    
    existing = await db.leaderboard.find_one({
        "player_name": data.player_name,
        "week_start": week_start.isoformat()
    })
    
    if existing:
        if data.score > existing.get("score", 0):
            await db.leaderboard.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "score": data.score,
                    "mooncakes": data.mooncakes,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    else:
        entry = {
            "id": str(uuid.uuid4()),
            "player_name": data.player_name,
            "score": data.score,
            "mooncakes": data.mooncakes,
            "week_start": week_start.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.leaderboard.insert_one(entry)
    
    # Get rank
    higher_scores = await db.leaderboard.count_documents({
        "week_start": week_start.isoformat(),
        "score": {"$gt": data.score}
    })
    rank = higher_scores + 1
    
    return {"rank": rank, "score": data.score, "mooncakes": data.mooncakes}
