"""Admin routes for dashboard and management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from utils.database import db
from utils.config import ADMIN_WALLETS, RAKE_PERCENT, DISTRIBUTION_WALLET, is_admin
from utils.websocket_managers import pot_ws_manager
from routers.pot import active_pot, reset_pot, _get_pot_data
import secrets
import logging

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


class AdminCancelRequest(BaseModel):
    challenge_id: str
    admin_wallet: str


class AdminPotDrawRequest(BaseModel):
    admin_wallet: str


@router.get("/check/{wallet_address}")
async def check_admin_status(wallet_address: str):
    """Check if wallet is an admin."""
    return {"is_admin": is_admin(wallet_address)}


@router.get("/dashboard")
async def get_admin_dashboard():
    """Get admin dashboard statistics."""
    # Total stats
    total_challenges = await db.p2p_challenges.count_documents({})
    completed_challenges = await db.p2p_challenges.count_documents({"status": "completed"})
    open_challenges = await db.p2p_challenges.count_documents({"status": "open"})
    
    # Calculate total rake collected
    completed = await db.p2p_challenges.find({"status": "completed"}, {"rake_sol": 1}).to_list(10000)
    total_rake = sum(c.get("rake_sol", 0) for c in completed)
    
    # Pot stats
    pot_results = await db.pot_results.find({}, {"rake_sol": 1, "total_pot_sol": 1}).to_list(1000)
    pot_rake = sum(p.get("rake_sol", 0) for p in pot_results)
    total_pot_volume = sum(p.get("total_pot_sol", 0) for p in pot_results)
    
    # Volume stats
    total_volume = sum(c.get("bet_amount_sol", 0) * 2 for c in completed)
    
    # Recent activity
    recent_challenges = await db.p2p_challenges.find(
        {"status": "completed"},
        {"_id": 0, "server_seed": 0}
    ).sort("completed_at", -1).to_list(10)
    
    # User stats
    unique_wallets = await db.p2p_challenges.distinct("creator_wallet")
    unique_opponents = await db.p2p_challenges.distinct("opponent_wallet")
    all_wallets = set(unique_wallets + [w for w in unique_opponents if w])
    
    return {
        "betting_stats": {
            "total_challenges": total_challenges,
            "completed_challenges": completed_challenges,
            "open_challenges": open_challenges,
            "total_volume_sol": round(total_volume, 4),
            "total_rake_collected_sol": round(total_rake, 4),
            "rake_percent": RAKE_PERCENT
        },
        "pot_stats": {
            "total_pots_drawn": len(pot_results),
            "total_pot_volume_sol": round(total_pot_volume, 4),
            "total_pot_rake_sol": round(pot_rake, 4),
            "current_pot": {
                "total_sol": active_pot["total_amount_sol"],
                "entries": len(active_pot["entries"]),
                "status": active_pot["status"],
                "countdown_started": active_pot["countdown_started"]
            }
        },
        "user_stats": {
            "unique_players": len(all_wallets),
            "unique_creators": len(unique_wallets),
            "unique_acceptors": len([w for w in unique_opponents if w])
        },
        "distribution_wallet": DISTRIBUTION_WALLET,
        "total_revenue_sol": round(total_rake + pot_rake, 4),
        "recent_challenges": recent_challenges
    }


@router.get("/challenges")
async def get_all_challenges(limit: int = 50, status: Optional[str] = None):
    """Get all challenges (admin view)."""
    query = {}
    if status:
        query["status"] = status
    
    challenges = await db.p2p_challenges.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return {"challenges": challenges, "count": len(challenges)}


@router.post("/challenge/cancel")
async def admin_cancel_challenge(data: AdminCancelRequest):
    """Admin force-cancel a challenge."""
    if not is_admin(data.admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    challenge = await db.p2p_challenges.find_one({"id": data.challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if challenge["status"] != "open":
        raise HTTPException(status_code=400, detail="Challenge is not open")
    
    await db.p2p_challenges.update_one(
        {"id": data.challenge_id},
        {"$set": {
            "status": "admin_cancelled",
            "cancelled_by": data.admin_wallet,
            "cancelled_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    logger.info(f"Admin {data.admin_wallet} cancelled challenge {data.challenge_id}")
    
    return {
        "message": "Challenge cancelled by admin",
        "challenge_id": data.challenge_id,
        "refund_amount_sol": challenge["bet_amount_sol"]
    }


@router.post("/pot/draw")
async def admin_force_draw_pot(data: AdminPotDrawRequest):
    """Admin force draw the pot."""
    global active_pot
    
    if not is_admin(data.admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if len(active_pot["entries"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries")
    
    # Draw winner
    total = active_pot["total_amount_sol"]
    rand_value = secrets.randbelow(int(total * 1000000)) / 1000000
    cumulative = 0
    winner = None
    
    for entry in active_pot["entries"]:
        cumulative += entry["amount_sol"]
        if rand_value <= cumulative:
            winner = entry
            break
    if not winner:
        winner = active_pot["entries"][-1]
    
    rake = round(total * active_pot["rake_percent"] / 100, 6)
    payout = round(total - rake, 6)
    
    result = {
        "winner_name": winner["display_name"],
        "winner_wallet": winner["wallet_address"],
        "payout_sol": payout,
        "total_pot_sol": total,
        "rake_sol": rake,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(active_pot["entries"]),
        "admin_forced": True,
        "forced_by": data.admin_wallet
    }
    
    active_pot["winner"] = result
    active_pot["status"] = "completed"
    
    # Save to DB
    await db.pot_results.insert_one({
        **result,
        "pot_id": active_pot["id"],
        "entries": active_pot["entries"],
        "drawn_at": datetime.now(timezone.utc).isoformat()
    })
    
    await pot_ws_manager.broadcast({"type": "pot_winner", "data": result})
    
    logger.info(f"Admin {data.admin_wallet} force-drew pot. Winner: {winner['display_name']}")
    
    # Reset pot
    reset_pot()
    
    return result


@router.get("/bets")
async def get_recent_bets(limit: int = 50):
    """Get recent betting activity."""
    history = await db.betting_history.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    
    return {"bets": history, "count": len(history)}


@router.get("/escrow")
async def get_escrow_stats():
    """Get escrow statistics."""
    escrow_deposits = await db.escrow_deposits.find({}, {"_id": 0}).to_list(1000)
    
    total_deposited = sum(d.get("amount_sol", 0) for d in escrow_deposits)
    active_deposits = [d for d in escrow_deposits if d.get("status") == "active"]
    
    return {
        "total_deposits": len(escrow_deposits),
        "active_deposits": len(active_deposits),
        "total_volume_sol": round(total_deposited, 4),
        "escrow_wallet": DISTRIBUTION_WALLET
    }
