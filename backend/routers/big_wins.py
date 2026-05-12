"""Big Win cross-page broadcaster.

Persists every arena win over a configurable threshold (default 1 SOL) and
broadcasts it on a WebSocket so any page can show a real-time toast.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Header, HTTPException

from utils.database import db
from utils.websocket_managers import big_wins_manager

router = APIRouter(prefix="/big-wins", tags=["big-wins"])
logger = logging.getLogger(__name__)

BIG_WIN_THRESHOLD_SOL = 1.0
_ADMIN_WALLETS = {
    "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT",
    "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs",
}


def _truncate_wallet(addr: Optional[str]) -> Optional[str]:
    if not addr:
        return None
    if len(addr) <= 10:
        return addr
    return f"{addr[:4]}…{addr[-4:]}"


async def record_big_win(
    game: str,
    winner_name: Optional[str],
    winner_wallet: Optional[str],
    payout_sol: float,
    rake_sol: float = 0.0,
    extra: Optional[dict] = None,
) -> None:
    """Persist a win to MongoDB and broadcast it. No-op if payout is below threshold."""
    try:
        amount = float(payout_sol or 0)
    except (TypeError, ValueError):
        return
    if amount < BIG_WIN_THRESHOLD_SOL:
        return

    doc = {
        "game": game,                       # "pot" | "coinflip"
        "winner_name": winner_name or "Anonymous",
        "winner_wallet": winner_wallet,
        "winner_wallet_short": _truncate_wallet(winner_wallet),
        "payout_sol": round(amount, 6),
        "rake_sol": round(float(rake_sol or 0), 6),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        doc["extra"] = extra
    try:
        await db.big_wins.insert_one(doc)
    except Exception:
        logger.exception("Failed to persist big win")
    doc.pop("_id", None)
    try:
        await big_wins_manager.broadcast({"type": "big_win", "data": doc})
    except Exception:
        logger.exception("Failed to broadcast big win")

    # Web Push to all subscribers (true background notifications via Service Worker)
    try:
        from routers.push_notifications import broadcast_to_all_subscribers
        game_label = "Winner Pot" if doc.get("game") == "pot" else "Coin Flip"
        await broadcast_to_all_subscribers({
            "title": f"🏆 {doc['winner_name']} won {doc['payout_sol']} SOL",
            "body": f"Bullpug {game_label} just resolved. Tap to enter the arena.",
            "icon": "/bullpug-icon.png",
            "badge": "/bullpug-badge.png",
            "tag": f"bigwin-{doc['game']}-{doc['occurred_at']}",
            "url": "/betting",
            "data": {
                "type": "big_win",
                "game": doc.get("game"),
                "payout_sol": doc.get("payout_sol"),
                "url": "/betting",
            },
        })
    except Exception:
        logger.exception("Failed to send big-win web push")


@router.get("/recent")
async def get_recent_big_wins(limit: int = 5, since: Optional[str] = None):
    """Recent big wins. Pass `since=<ISO timestamp>` to get only newer wins."""
    if limit > 25:
        limit = 25
    query: dict = {}
    if since:
        query["occurred_at"] = {"$gt": since}
    rows = await db.big_wins.find(query, {"_id": 0}).sort("occurred_at", -1).limit(limit).to_list(limit)
    return {"big_wins": rows, "threshold_sol": BIG_WIN_THRESHOLD_SOL}



@router.post("/debug-inject")
async def debug_inject_big_win(
    payout_sol: float = 1.5,
    game: str = "coinflip",
    winner_name: str = "QA Tester",
    winner_wallet: str = "DebugWalletQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    x_admin_wallet: Optional[str] = Header(None),
):
    """Admin-only synthetic big win injector for QA testing (toast verification)."""
    if x_admin_wallet not in _ADMIN_WALLETS:
        raise HTTPException(status_code=403, detail="Admin wallet required")
    await record_big_win(
        game=game,
        winner_name=winner_name,
        winner_wallet=winner_wallet,
        payout_sol=payout_sol,
        rake_sol=round(payout_sol * 0.025, 6),
    )
    return {"status": "ok", "injected": True, "payout_sol": payout_sol}
