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
from utils.solana_payout import send_sol_payout
from state.pot_state import get_pot, reset_pot
from routers.prize_pool import add_to_prize_pool

router = APIRouter(prefix="/betting/pot", tags=["pot"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


async def get_pot_data():
    """Get pot data for broadcasts and API responses (aggregated per player)."""
    pot = get_pot()
    # Aggregate stakes by wallet so stacked entries show as one player card
    aggregated = {}
    order = []
    for e in pot["entries"]:
        key = e.get("wallet_address") or f"anon-{e['id']}"
        if key not in aggregated:
            aggregated[key] = {
                "display_name": e["display_name"],
                "wallet_address": e["wallet_address"],
                "amount_sol": 0.0,
                "entry_count": 0
            }
            order.append(key)
        aggregated[key]["amount_sol"] += e["amount_sol"]
        aggregated[key]["entry_count"] += 1

    entries_display = []
    for key in order:
        agg = aggregated[key]
        prob = round(agg["amount_sol"] / pot["total_amount_sol"] * 100, 1) if pot["total_amount_sol"] > 0 else 0
        entries_display.append({
            "display_name": agg["display_name"],
            "wallet_address": agg["wallet_address"][:8] + "..." if agg.get("wallet_address") else "???",
            "amount_sol": round(agg["amount_sol"], 6),
            "entry_count": agg["entry_count"],
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
    """Join the P2P pot with SOL. Stacking allowed (cumulative ≤ 10 SOL per player per round)."""
    pot = get_pot()
    if pot["status"] != "open":
        raise HTTPException(status_code=400, detail="Pot is closed")
    if data.bet_amount_sol <= 0:
        raise HTTPException(status_code=400, detail="Bet must be positive")
    if data.bet_amount_sol < 0.005:
        raise HTTPException(status_code=400, detail="Minimum bet is 0.005 SOL")
    if data.bet_amount_sol > 10.0:
        raise HTTPException(status_code=400, detail="Maximum single entry is 10 SOL")
    if not data.wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address required")

    # Enforce cumulative 10 SOL cap per player per round
    existing_total = sum(
        e["amount_sol"] for e in pot["entries"]
        if e.get("wallet_address") == data.wallet_address
    )
    if existing_total + data.bet_amount_sol > 10.0:
        remaining = max(0, round(10.0 - existing_total, 6))
        raise HTTPException(
            status_code=400,
            detail=f"Per-player cap is 10 SOL per round. You can add at most {remaining} SOL more."
        )

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

    # Countdown starts as soon as there are 2+ unique players
    unique_players = len({e["wallet_address"] for e in pot["entries"] if e.get("wallet_address")})
    countdown_just_started = False
    if unique_players >= 2 and not pot["countdown_started"]:
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
async def draw_pot_winner(request: Request):
    """Draw pot winner - winner takes all minus rake.

    Gated: either the countdown must have expired (draw_at <= now) OR the caller
    is the DISTRIBUTION_WALLET admin (via X-Admin-Wallet header).
    """
    pot = get_pot()
    if len(pot["entries"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries")

    # Authorization: draw can only fire after the 60s countdown expires,
    # unless an admin (distribution wallet) manually triggers it.
    admin_header = request.headers.get("X-Admin-Wallet", "")
    is_admin = admin_header == DISTRIBUTION_WALLET
    if not is_admin:
        if not pot.get("draw_at"):
            raise HTTPException(status_code=403, detail="Countdown has not started")
        draw_time = datetime.fromisoformat(pot["draw_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < draw_time:
            raise HTTPException(status_code=403, detail="Countdown has not finished")

    total = pot["total_amount_sol"]
    if total <= 0:
        raise HTTPException(status_code=400, detail="Pot total is zero")
    # Guard randbelow(0) which would raise ValueError
    range_units = max(1, int(total * 1_000_000))
    rand_value = secrets.randbelow(range_units) / 1_000_000
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
    
    # === CONTRIBUTE TO PRIZE POOL (25% of rake) ===
    try:
        await add_to_prize_pool(
            amount_sol=rake,
            source="pot_rake",
            details={"pot_id": pot["id"], "total_pot": total, "entries": len(pot["entries"])}
        )
    except Exception as e:
        logger.error(f"Failed to add pot rake to prize pool: {e}")
    
    # === AUTOMATIC PAYOUT ===
    payout_success = False
    payout_tx = None
    payout_error = None
    
    try:
        winner_wallet = winner["wallet_address"]
        logger.info(f"Initiating pot payout: {payout} SOL to {winner_wallet}")
        
        success, tx_result = await send_sol_payout(
            recipient_wallet=winner_wallet,
            amount_sol=payout,
            memo=f"Bullpug Pot Win - {pot['id'][:8]}"
        )
        
        if success:
            payout_success = True
            payout_tx = tx_result
            logger.info(f"Pot payout successful! TX: {payout_tx}")
        else:
            payout_error = tx_result
            logger.error(f"Pot payout failed: {payout_error}")
            
    except Exception as e:
        payout_error = str(e)
        logger.error(f"Pot payout exception: {payout_error}")
    
    result = {
        "winner_name": winner["display_name"],
        "winner_wallet": winner["wallet_address"],
        "payout_sol": payout,
        "total_pot_sol": total,
        "rake_sol": rake,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(pot["entries"]),
        "payout_sent": payout_success,
        "payout_tx": payout_tx,
        "payout_error": payout_error
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
