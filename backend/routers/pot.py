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
from utils.config import DISTRIBUTION_WALLET
from utils.websocket_managers import pot_ws_manager
from state.pot_state import get_pot, reset_pot

router = APIRouter(prefix="/betting/pot", tags=["pot"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


async def get_pot_data():
    """Get pot data for broadcasts and API responses."""
    pot = get_pot()
    entries_display = []
    for e in pot["entries"]:
        prob = round(e["amount_sol"] / pot["total_amount_sol"] * 100, 1) if pot["total_amount_sol"] > 0 else 0
        entries_display.append({
            "display_name": e["display_name"],
            "wallet_address": e["wallet_address"][:8] + "..." if e.get("wallet_address") else "???",
            "amount_sol": e["amount_sol"],
            "probability": prob
        })
    
    remaining_seconds = None
    if pot["countdown_started"] and pot["draw_at"]:
        draw_time = datetime.fromisoformat(pot["draw_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        remaining = (draw_time - now).total_seconds()
        remaining_seconds = max(0, int(remaining))
    
    return {
        "id": pot["id"],
        "total_amount_sol": pot["total_amount_sol"],
        "entry_count": len(pot["entries"]),
        "entries": entries_display,
        "status": pot["status"],
        "draw_at": pot["draw_at"],
        "countdown_started": pot["countdown_started"],
        "countdown_seconds": pot["countdown_seconds"],
        "remaining_seconds": remaining_seconds,
        "rake_percent": pot["rake_percent"],
        "distribution_wallet": DISTRIBUTION_WALLET,
        "winner": pot["winner"]
    }


@router.get("")
async def get_pot_status():
    """Get current P2P pot status."""
    return await get_pot_data()


@router.post("/join")
@limiter.limit("10/minute")
async def join_pot(request: Request, data: P2PPotJoinRequest):
    """Join the P2P pot with SOL."""
    pot = get_pot()
    if pot["status"] != "open":
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
    pot["entries"].append(entry)
    pot["total_amount_sol"] += data.bet_amount_sol
    
    countdown_just_started = False
    if len(pot["entries"]) == 2 and not pot["countdown_started"]:
        pot["countdown_started"] = True
        pot["draw_at"] = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        countdown_just_started = True
        logger.info(f"Pot countdown started! Draw at: {pot['draw_at']}")
    
    resp = {
        "message": f"Joined pot with {data.bet_amount_sol} SOL!",
        "probability": round(data.bet_amount_sol / pot["total_amount_sol"] * 100, 1),
        "total_pot_sol": pot["total_amount_sol"],
        "entry_count": len(pot["entries"]),
        "countdown_started": pot["countdown_started"],
        "countdown_just_started": countdown_just_started,
        "draw_at": pot["draw_at"]
    }
    await pot_ws_manager.broadcast({"type": "pot_update", "data": await get_pot_data()})
    return resp


@router.post("/draw")
async def draw_pot_winner():
    """Draw pot winner - winner takes all minus rake."""
    pot = get_pot()
    if len(pot["entries"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries")
    
    total = pot["total_amount_sol"]
    rand_value = secrets.randbelow(int(total * 1000000)) / 1000000
    cumulative = 0
    winner = None
    
    for entry in pot["entries"]:
        cumulative += entry["amount_sol"]
        if rand_value <= cumulative:
            winner = entry
            break
    if not winner:
        winner = pot["entries"][-1]
    
    rake = round(total * pot["rake_percent"] / 100, 6)
    payout = round(total - rake, 6)
    
    logger.info(f"Pot Rake: {rake} SOL to {DISTRIBUTION_WALLET}")
    
    result = {
        "winner_name": winner["display_name"],
        "winner_wallet": winner["wallet_address"],
        "payout_sol": payout,
        "total_pot_sol": total,
        "rake_sol": rake,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(pot["entries"])
    }
    
    pot["winner"] = result
    pot["status"] = "completed"
    
    await db.pot_results.insert_one({
        **result,
        "pot_id": pot["id"],
        "entries": pot["entries"],
        "drawn_at": datetime.now(timezone.utc).isoformat()
    })
    
    await pot_ws_manager.broadcast({"type": "pot_winner", "data": result})
    
    reset_pot()
    
    return result
