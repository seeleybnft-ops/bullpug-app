"""Operator Telegram alerts.

Currently fires a single alert: when the P2P arena escrow's free capital
dips below ALERT_THRESHOLD_SOL, send the operator a Telegram nudge so
they can top up before player payouts fail.

Setup:
  1. Open Telegram, message @userinfobot, copy your numeric chat id.
  2. Paste it into `backend/.env` as ADMIN_TELEGRAM_CHAT_ID=<id>.
  3. Restart backend. The scheduler will then check every 10 minutes.
"""

import logging
import os
from datetime import datetime, timezone, timedelta

from utils.database import db
from utils.config import DISTRIBUTION_WALLET
from utils.solana_payout import get_escrow_balance

logger = logging.getLogger(__name__)

ALERT_THRESHOLD_SOL = 0.05
ALERT_COOLDOWN_HOURS = 6  # only re-alert every 6h while still low
ALERT_STATE_KEY = "escrow_alert_state"


async def _get_pending_obligations_sol() -> float:
    """Sum open pot + open/matched coinflip obligations to compute free capital."""
    from routers.pot import get_pot
    pot = get_pot()
    pot_obligation = float(pot.get("total_amount_sol") or 0.0)

    coinflip_obligation = 0.0
    async for c in db.betting_challenges.find(
        {"status": {"$in": ["open", "matched", "active", "pending"]}}
    ):
        amount = float(c.get("bet_amount_sol") or 0.0)
        coinflip_obligation += amount * (2.0 if c.get("status") in ("matched", "active") else 1.0)

    pool = await db.prize_pool.find_one({"active": True})
    jackpot_owed = float(pool.get("total_sol") or 0.0) if pool else 0.0

    return pot_obligation + coinflip_obligation + jackpot_owed


async def check_escrow_and_alert() -> dict:
    """Run an escrow health check and emit a Telegram alert if needed.

    Returns a dict describing what happened (useful for scheduler logs).
    """
    chat_id_str = os.environ.get("ADMIN_TELEGRAM_CHAT_ID", "").strip()
    if not chat_id_str:
        return {"status": "skipped", "reason": "ADMIN_TELEGRAM_CHAT_ID not set"}
    try:
        chat_id = int(chat_id_str)
    except ValueError:
        logger.warning("ADMIN_TELEGRAM_CHAT_ID is not numeric: %s", chat_id_str)
        return {"status": "error", "reason": "invalid chat id"}

    balance = get_escrow_balance()
    if balance is None:
        return {"status": "error", "reason": "could not read on-chain balance"}

    obligations = await _get_pending_obligations_sol()
    free_capital = max(0.0, balance - obligations)

    now = datetime.now(timezone.utc)
    state_doc = await db.system_state.find_one({"_id": ALERT_STATE_KEY}) or {}
    last_alert_at = state_doc.get("last_alert_at")
    last_alert_dt = None
    if last_alert_at:
        try:
            last_alert_dt = datetime.fromisoformat(last_alert_at.replace("Z", "+00:00"))
        except Exception:
            last_alert_dt = None

    # Healthy → reset the recent-alert flag so we re-alert on the next dip
    if free_capital >= ALERT_THRESHOLD_SOL:
        if state_doc.get("currently_alerted"):
            await db.system_state.update_one(
                {"_id": ALERT_STATE_KEY},
                {"$set": {"currently_alerted": False, "recovered_at": now.isoformat()}},
                upsert=True,
            )
        return {"status": "ok", "balance_sol": balance, "free_capital_sol": free_capital}

    # Below threshold — check cooldown
    if last_alert_dt and (now - last_alert_dt) < timedelta(hours=ALERT_COOLDOWN_HOURS):
        return {
            "status": "throttled",
            "free_capital_sol": free_capital,
            "next_alert_after": (last_alert_dt + timedelta(hours=ALERT_COOLDOWN_HOURS)).isoformat(),
        }

    # Fire the alert
    from routers.telegram import send_telegram_message
    message = (
        "🚨 <b>Bullpug Escrow LOW</b>\n\n"
        f"Free capital: <b>{free_capital:.6f} SOL</b>\n"
        f"On-chain balance: {balance:.6f} SOL\n"
        f"Pending obligations: {obligations:.6f} SOL\n\n"
        f"Threshold: {ALERT_THRESHOLD_SOL} SOL. Player payouts may fail if balance "
        f"runs out.\n\n"
        f"Top up the escrow wallet:\n<code>{DISTRIBUTION_WALLET}</code>\n\n"
        f"Recommended top-up: <b>{max(0.5 - free_capital, 0):.4f} SOL</b> to reach the 0.5 SOL buffer."
    )
    sent = await send_telegram_message(chat_id, message)
    if sent:
        await db.system_state.update_one(
            {"_id": ALERT_STATE_KEY},
            {"$set": {"last_alert_at": now.isoformat(), "currently_alerted": True}},
            upsert=True,
        )
        logger.warning(
            "Escrow LOW alert sent to admin (free_capital=%.6f SOL)", free_capital
        )
        return {"status": "alerted", "free_capital_sol": free_capital}
    return {"status": "telegram_send_failed", "free_capital_sol": free_capital}
