"""Pot game routes for P2P winner-takes-all betting."""

from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
import secrets
import uuid
import logging
from datetime import datetime, timezone, timedelta

from models.schemas import P2PPotJoinRequest
from utils.database import db
from utils.config import RAKE_PERCENT, DISTRIBUTION_WALLET
from utils.websocket_managers import pot_ws_manager

router = APIRouter(prefix="/betting/pot", tags=["pot"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

# Active pot stored in memory (resets on server restart)
active_pot = {
    "id": str(uuid.uuid4()),
    "total_amount_sol": 0,
    "entries": [],
    "status": "open",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "draw_at": None,
    "countdown_started": False,
    "countdown_seconds": 60,
    "rake_percent": RAKE_PERCENT,
    "winner": None
}


async def _get_pot_data():
    """Get pot data for broadcasts."""
    entries_display = []
    for e in active_pot["entries"]:
        prob = round(e["amount_sol"] / active_pot["total_amount_sol"] * 100, 1) if active_pot["total_amount_sol"] > 0 else 0
        entries_display.append({
            "display_name": e["display_name"],
            "wallet_address": e["wallet_address"][:8] + "..." if e.get("wallet_address") else "???",
            "amount_sol": e["amount_sol"],
            "probability": prob
        })
    
    remaining_seconds = None
    if active_pot["countdown_started"] and active_pot["draw_at"]:
        draw_time = datetime.fromisoformat(active_pot["draw_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        remaining = (draw_time - now).total_seconds()
        remaining_seconds = max(0, int(remaining))
    
    return {
        "id": active_pot["id"],
        "total_amount_sol": active_pot["total_amount_sol"],
        "entry_count": len(active_pot["entries"]),
        "entries": entries_display,
        "status": active_pot["status"],
        "draw_at": active_pot["draw_at"],
        "countdown_started": active_pot["countdown_started"],
        "countdown_seconds": active_pot["countdown_seconds"],
        "remaining_seconds": remaining_seconds,
        "rake_percent": active_pot["rake_percent"],
        "distribution_wallet": DISTRIBUTION_WALLET,
        "winner": active_pot["winner"]
    }


def reset_pot():
    """Reset the pot to initial state."""
    global active_pot
    active_pot = {
        "id": str(uuid.uuid4()),
        "total_amount_sol": 0,
        "entries": [],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "draw_at": None,
        "countdown_started": False,
        "countdown_seconds": 60,
        "rake_percent": RAKE_PERCENT,
        "winner": None
    }


@router.get("")
async def get_pot_status():
    """Get current P2P pot status."""
    return await _get_pot_data()


@router.post("/join")
@limiter.limit("10/minute")
async def join_pot(request: Request, data: P2PPotJoinRequest):
    """Join the P2P pot with SOL."""
    global active_pot
    if active_pot["status"] != "open":
        raise HTTPException(status_code=400, detail="Pot is closed")
    if data.bet_amount_sol <= 0:
        raise HTTPException(status_code=400, detail="Bet must be positive")
    if data.bet_amount_sol < 0.01:
        raise HTTPException(status_code=400, detail="Minimum bet is 0.01 SOL")
    if not data.wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address required")
    
    entry = {
        "id": str(uuid.uuid4()),
        "display_name": data.display_name,
        "wallet_address": data.wallet_address,
        "amount_sol": data.bet_amount_sol,
        "tx_signature": data.tx_signature,
        "joined_at": datetime.now(timezone.utc).isoformat()
    }
    active_pot["entries"].append(entry)
    active_pot["total_amount_sol"] += data.bet_amount_sol
    
    countdown_just_started = False
    if len(active_pot["entries"]) == 2 and not active_pot["countdown_started"]:
        active_pot["countdown_started"] = True
        active_pot["draw_at"] = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        countdown_just_started = True
        logger.info(f"Pot countdown started! Draw at: {active_pot['draw_at']}")
    
    resp = {
        "message": f"Joined pot with {data.bet_amount_sol} SOL!",
        "probability": round(data.bet_amount_sol / active_pot["total_amount_sol"] * 100, 1),
        "total_pot_sol": active_pot["total_amount_sol"],
        "entry_count": len(active_pot["entries"]),
        "countdown_started": active_pot["countdown_started"],
        "countdown_just_started": countdown_just_started,
        "draw_at": active_pot["draw_at"]
    }
    await pot_ws_manager.broadcast({"type": "pot_update", "data": await _get_pot_data()})
    return resp


@router.post("/draw")
async def draw_pot_winner():
    """Draw pot winner - winner takes all minus rake."""
    global active_pot
    if len(active_pot["entries"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries")
    
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
    
    logger.info(f"Pot Rake: {rake} SOL to {DISTRIBUTION_WALLET}")
    
    result = {
        "winner_name": winner["display_name"],
        "winner_wallet": winner["wallet_address"],
        "payout_sol": payout,
        "total_pot_sol": total,
        "rake_sol": rake,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(active_pot["entries"])
    }
    
    active_pot["winner"] = result
    active_pot["status"] = "completed"
    
    await db.pot_results.insert_one({
        **result,
        "pot_id": active_pot["id"],
        "entries": active_pot["entries"],
        "drawn_at": datetime.now(timezone.utc).isoformat()
    })
    
    await pot_ws_manager.broadcast({"type": "pot_winner", "data": result})
    
    reset_pot()
    
    return result
