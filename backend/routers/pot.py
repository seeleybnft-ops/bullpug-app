"""Pot game routes for P2P winner-takes-all betting.

All math is done in lamports (integers) for accounting safety. Floats are only
used at API boundaries / UI surfaces.
"""

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
from state.pot_state import (
    get_pot,
    reset_pot,
    persist_pot,
    sol_to_lamports,
    lamports_to_sol,
    LAMPORTS_PER_SOL,
)
from routers.prize_pool import add_to_prize_pool
from routers.big_wins import record_big_win

router = APIRouter(prefix="/betting/pot", tags=["pot"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

MIN_BET_LAMPORTS = sol_to_lamports(0.005)   # 5_000_000
MAX_BET_LAMPORTS = sol_to_lamports(10.0)    # 10_000_000_000
MAX_PLAYER_LAMPORTS_PER_ROUND = MAX_BET_LAMPORTS  # 10 SOL cumulative


async def get_pot_data():
    """Get pot data for broadcasts and API responses (aggregated per player)."""
    pot = get_pot()
    aggregated = {}
    order = []
    for e in pot["entries"]:
        key = e.get("wallet_address") or f"anon-{e['id']}"
        if key not in aggregated:
            aggregated[key] = {
                "display_name": e["display_name"],
                "wallet_address": e["wallet_address"],
                "amount_lamports": 0,
                "entry_count": 0
            }
            order.append(key)
        aggregated[key]["amount_lamports"] += int(e.get("amount_lamports", 0))
        aggregated[key]["entry_count"] += 1

    total_lamports = int(pot.get("total_lamports", 0))
    entries_display = []
    for key in order:
        agg = aggregated[key]
        prob = round(agg["amount_lamports"] / total_lamports * 100, 1) if total_lamports > 0 else 0
        entries_display.append({
            "display_name": agg["display_name"],
            "wallet_address": agg["wallet_address"][:8] + "..." if agg.get("wallet_address") else "???",
            "amount_sol": lamports_to_sol(agg["amount_lamports"]),
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
        "total_amount_sol": lamports_to_sol(total_lamports),
        "total_lamports": total_lamports,
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
    if not data.wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address required")

    bet_lamports = sol_to_lamports(data.bet_amount_sol)
    if bet_lamports < MIN_BET_LAMPORTS:
        raise HTTPException(status_code=400, detail="Minimum bet is 0.005 SOL")
    if bet_lamports > MAX_BET_LAMPORTS:
        raise HTTPException(status_code=400, detail="Maximum single entry is 10 SOL")

    # Enforce cumulative 10 SOL cap per player per round (lamport math)
    existing_lamports = sum(
        int(e.get("amount_lamports", 0)) for e in pot["entries"]
        if e.get("wallet_address") == data.wallet_address
    )
    if existing_lamports + bet_lamports > MAX_PLAYER_LAMPORTS_PER_ROUND:
        remaining_lamports = max(0, MAX_PLAYER_LAMPORTS_PER_ROUND - existing_lamports)
        raise HTTPException(
            status_code=400,
            detail=f"Per-player cap is 10 SOL per round. You can add at most "
                   f"{lamports_to_sol(remaining_lamports)} SOL more."
        )

    entry = {
        "id": str(uuid.uuid4()),
        "display_name": data.display_name,
        "wallet_address": data.wallet_address,
        "amount_lamports": bet_lamports,
        "amount_sol": lamports_to_sol(bet_lamports),
        "tx_signature": data.tx_signature,
        "joined_at": datetime.now(timezone.utc).isoformat()
    }
    pot["entries"].append(entry)
    pot["total_lamports"] = int(pot.get("total_lamports", 0)) + bet_lamports
    pot["total_amount_sol"] = lamports_to_sol(pot["total_lamports"])

    # Countdown starts as soon as there are 2+ unique players
    unique_players = len({e["wallet_address"] for e in pot["entries"] if e.get("wallet_address")})
    countdown_just_started = False
    if unique_players >= 2 and not pot["countdown_started"]:
        pot["countdown_started"] = True
        pot["draw_at"] = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        countdown_just_started = True
        logger.info(f"Pot countdown started! Draw at: {pot['draw_at']}")

    # Persist to MongoDB BEFORE responding so a crash here doesn't lose the entry
    await persist_pot()

    # Fire a web-push to all subscribers when the 60s countdown starts. One per round.
    if countdown_just_started:
        try:
            from routers.push_notifications import broadcast_to_all_subscribers
            await broadcast_to_all_subscribers({
                "title": "⏱ 60s to win — Bullpug Pot is LIVE",
                "body": f"Pot is {pot['total_amount_sol']:.3f} SOL with {unique_players} players. Tap to jump in before draw.",
                "icon": "/bullpug-icon.png",
                "badge": "/bullpug-badge.png",
                "tag": f"pot-countdown-{pot['draw_at']}",
                "url": "/betting",
                "data": {
                    "type": "pot_countdown",
                    "total_sol": pot["total_amount_sol"],
                    "players": unique_players,
                    "draw_at": pot["draw_at"],
                    "url": "/betting",
                },
            })
        except Exception:
            logger.exception("Failed to send pot countdown web push")

        # Drop a system chat message into the arena chat for everyone watching
        try:
            from routers.arena_chat import post_system_message
            await post_system_message(
                f"⏱ 60-second countdown started · {unique_players} players · pot at {pot['total_amount_sol']:.3f} SOL — last chance to jump in!"
            )
        except Exception:
            logger.exception("Failed to post countdown system chat")

    resp = {
        "message": f"Joined pot with {data.bet_amount_sol} SOL!",
        "probability": round(bet_lamports / pot["total_lamports"] * 100, 1),
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

    admin_header = request.headers.get("X-Admin-Wallet", "")
    is_admin = admin_header == DISTRIBUTION_WALLET
    if not is_admin:
        if not pot.get("draw_at"):
            raise HTTPException(status_code=403, detail="Countdown has not started")
        draw_time = datetime.fromisoformat(pot["draw_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < draw_time:
            raise HTTPException(status_code=403, detail="Countdown has not finished")

    total_lamports = int(pot.get("total_lamports", 0))
    if total_lamports <= 0:
        raise HTTPException(status_code=400, detail="Pot total is zero")

    # Weighted random in lamport space (uniform integer 0..total_lamports-1)
    rand_lamports = secrets.randbelow(total_lamports)
    cumulative = 0
    winner = None
    for entry in pot["entries"]:
        cumulative += int(entry.get("amount_lamports", 0))
        if rand_lamports < cumulative:
            winner = entry
            break
    if not winner:
        winner = pot["entries"][-1]

    # Integer math: rake = floor(total * rake_percent / 100), payout = total - rake
    # rake_percent is 2.5 → multiply by 25, divide by 1000 to keep integers
    rake_basis_points = int(round(pot["rake_percent"] * 100))  # 2.5% → 250 bps
    rake_lamports = (total_lamports * rake_basis_points) // 10000
    payout_lamports = total_lamports - rake_lamports

    rake = lamports_to_sol(rake_lamports)
    payout = lamports_to_sol(payout_lamports)
    total = lamports_to_sol(total_lamports)

    logger.info(f"Pot Rake: {rake} SOL ({rake_lamports} lamports) to {DISTRIBUTION_WALLET}")

    # === CONTRIBUTE 25% OF RAKE TO PRIZE POOL (Cosmic Runner Jackpot) ===
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
        "payout_lamports": payout_lamports,
        "total_pot_sol": total,
        "total_lamports": total_lamports,
        "rake_sol": rake,
        "rake_lamports": rake_lamports,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(pot["entries"]),
        "payout_sent": payout_success,
        "payout_tx": payout_tx,
        "payout_error": payout_error
    }

    pot["winner"] = result
    pot["status"] = "completed"
    await persist_pot()

    await db.pot_results.insert_one({
        **result,
        "pot_id": pot["id"],
        "entries": pot["entries"],
        "drawn_at": datetime.now(timezone.utc).isoformat()
    })

    await pot_ws_manager.broadcast({"type": "pot_winner", "data": result})

    # Cross-page big-win toast (≥ 1 SOL)
    try:
        await record_big_win(
            game="pot",
            winner_name=winner.get("display_name"),
            winner_wallet=winner.get("wallet_address"),
            payout_sol=payout,
            rake_sol=rake,
            extra={"pot_id": pot["id"], "total_pot_sol": total, "entry_count": len(pot["entries"])},
        )
    except Exception:
        logger.exception("record_big_win (pot) failed")

    await reset_pot()

    return result
