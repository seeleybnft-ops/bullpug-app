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
    except (ValueError, TypeError):
        days_until_reset = CYCLE_DAYS
    
    # Get scores from the current cycle
    leaderboard_entries = await db.leaderboard.find(
        {"cycle_start": cycle_start},
        {"_id": 0}
    ).sort("score", -1).to_list(limit)
    
    # Enrich with wallet info from game_leaderboard
    enriched_leaderboard = []
    for entry in leaderboard_entries:
        player_info = await db.game_leaderboard.find_one(
            {"display_name": entry.get("player_name")},
            {"_id": 0, "wallet_address": 1}
        )
        enriched_entry = {
            **entry,
            "wallet_address": player_info.get("wallet_address") if player_info else None
        }
        enriched_leaderboard.append(enriched_entry)
    
    return {
        "leaderboard": enriched_leaderboard,
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
            "mooncakes": data.moonCheese,  # Store as mooncakes for backward compatibility
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


@router.get("/wallet-link/{player_name}")
async def get_wallet_link(player_name: str):
    """Check if a player has linked a wallet for prize payouts."""
    player = await db.game_leaderboard.find_one(
        {"display_name": player_name},
        {"_id": 0, "wallet_address": 1, "display_name": 1}
    )
    
    if not player:
        return {"player_name": player_name, "wallet_address": None, "linked": False}
    
    return {
        "player_name": player_name,
        "wallet_address": player.get("wallet_address"),
        "linked": bool(player.get("wallet_address"))
    }


@router.post("/link-wallet")
async def link_wallet_to_player(data: dict):
    """Link a wallet address to a player name for prize payouts."""
    player_name = data.get("player_name")
    wallet_address = data.get("wallet_address")
    
    if not player_name or not wallet_address:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="player_name and wallet_address required")
    
    # Check if wallet is already linked to another player
    existing_wallet = await db.game_leaderboard.find_one({
        "wallet_address": wallet_address,
        "display_name": {"$ne": player_name}
    })
    
    if existing_wallet:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400, 
            detail=f"Wallet already linked to player: {existing_wallet.get('display_name')}"
        )
    
    # Update or create player entry
    await db.game_leaderboard.update_one(
        {"display_name": player_name},
        {
            "$set": {
                "wallet_address": wallet_address,
                "wallet_linked_at": datetime.now(timezone.utc).isoformat()
            },
            "$setOnInsert": {
                "display_name": player_name,
                "high_score": 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "player_name": player_name,
        "wallet_address": wallet_address,
        "message": "Wallet linked successfully! You're now eligible for prize payouts."
    }


@router.post("/unlink-wallet")
async def unlink_wallet_from_player(data: dict):
    """Remove wallet link from a player."""
    player_name = data.get("player_name")
    
    if not player_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="player_name required")
    
    await db.game_leaderboard.update_one(
        {"display_name": player_name},
        {"$set": {"wallet_address": None, "wallet_linked_at": None}}
    )
    
    return {"success": True, "message": "Wallet unlinked"}
