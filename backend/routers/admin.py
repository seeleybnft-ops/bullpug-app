"""Admin routes for dashboard and management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import secrets
import logging

from utils.database import db
from utils.config import DISTRIBUTION_WALLET, is_admin
from utils.admin_auth import require_admin_jwt
from utils.websocket_managers import pot_ws_manager
from state.pot_state import get_pot, reset_pot, persist_pot, lamports_to_sol
from fastapi import Depends

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


class AdminManageChallengeRequest(BaseModel):
    challenge_id: str
    admin_wallet: str


class AdminDrawPotRequest(BaseModel):
    admin_wallet: str


async def send_notification(to_wallet: str, title: str, body: str, notif_type: str = "general"):
    """Store notification in database."""
    import uuid
    notification = {
        "id": str(uuid.uuid4()),
        "to_wallet": to_wallet,
        "title": title,
        "body": body,
        "type": notif_type,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    return notification


@router.get("/check/{wallet_address}")
async def check_admin_status(wallet_address: str):
    """Check if wallet is an admin."""
    return {"is_admin": is_admin(wallet_address)}


@router.get("/dashboard")
async def admin_dashboard(admin_wallet: str):
    """Get admin dashboard data."""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    pot = get_pot()
    
    # Get statistics
    total_bets = await db.bets.count_documents({})
    total_challenges = await db.p2p_challenges.count_documents({})
    open_challenges = await db.p2p_challenges.count_documents({"status": "open"})
    completed_challenges = await db.p2p_challenges.count_documents({"status": "completed"})
    
    total_deposits = await db.escrow_deposits.count_documents({})
    total_messages = await db.messages.count_documents({})
    total_forum_posts = await db.forum_posts.count_documents({})
    total_users = len(set(
        [d["wallet_address"] async for d in db.bets.find({}, {"wallet_address": 1})]
    ))
    
    # Calculate total rake collected
    completed_bets = await db.bets.find({"type": "p2p_coin_flip"}, {"rake_sol": 1}).to_list(10000)
    total_rake = sum(b.get("rake_sol", 0) for b in completed_bets)
    
    # Get pot statistics
    pot_results = await db.pot_results.find({}, {"rake_sol": 1}).to_list(1000)
    total_pot_rake = sum(p.get("rake_sol", 0) for p in pot_results)
    
    return {
        "total_bets": total_bets,
        "total_challenges": total_challenges,
        "open_challenges": open_challenges,
        "completed_challenges": completed_challenges,
        "total_deposits": total_deposits,
        "total_messages": total_messages,
        "total_forum_posts": total_forum_posts,
        "estimated_users": total_users,
        "total_rake_collected_sol": round(total_rake + total_pot_rake, 6),
        "current_pot": {
            "total_amount_sol": pot["total_amount_sol"],
            "entry_count": len(pot["entries"]),
            "status": pot["status"]
        },
        "distribution_wallet": DISTRIBUTION_WALLET
    }


@router.get("/challenges")
async def admin_get_challenges(admin_wallet: str, status: Optional[str] = None, limit: int = 50):
    """Get all challenges (admin only)."""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {}
    if status:
        query["status"] = status
    
    challenges = await db.p2p_challenges.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"challenges": challenges}


@router.post("/challenge/cancel")
async def admin_cancel_challenge(data: AdminManageChallengeRequest):
    """Cancel a challenge and refund (admin only)."""
    if not is_admin(data.admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    challenge = await db.p2p_challenges.find_one({"id": data.challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if challenge["status"] != "open":
        raise HTTPException(status_code=400, detail="Can only cancel open challenges")
    
    await db.p2p_challenges.update_one(
        {"id": data.challenge_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_by": data.admin_wallet,
            "cancelled_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify the creator
    await send_notification(
        challenge["creator_wallet"],
        "Challenge Cancelled",
        f"Your {challenge['bet_amount_sol']} SOL challenge has been cancelled by admin",
        "challenge"
    )
    
    return {"message": "Challenge cancelled", "challenge_id": data.challenge_id}


@router.post("/pot/draw")
async def admin_draw_pot(data: AdminDrawPotRequest):
    """Force draw the current pot (admin only)."""
    if not is_admin(data.admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    pot = get_pot()
    if len(pot["entries"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries to draw")

    # Lamport-safe weighted random draw
    total_lamports = int(pot.get("total_lamports", 0))
    if total_lamports <= 0:
        raise HTTPException(status_code=400, detail="Pot total is zero")

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

    rake_basis_points = int(round(pot["rake_percent"] * 100))
    rake_lamports = (total_lamports * rake_basis_points) // 10000
    payout_lamports = total_lamports - rake_lamports

    rake = lamports_to_sol(rake_lamports)
    payout = lamports_to_sol(payout_lamports)
    total = lamports_to_sol(total_lamports)

    result = {
        "winner_name": winner["display_name"],
        "winner_wallet": winner.get("wallet_address"),
        "payout_sol": payout,
        "payout_lamports": payout_lamports,
        "total_pot_sol": total,
        "total_lamports": total_lamports,
        "rake_sol": rake,
        "rake_lamports": rake_lamports,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(pot["entries"])
    }

    pot["winner"] = result
    pot["status"] = "completed"
    await persist_pot()
    
    # Save to DB
    await db.pot_results.insert_one({
        **result,
        "pot_id": pot["id"],
        "entries": pot["entries"],
        "admin_forced": True,
        "forced_by": data.admin_wallet,
        "drawn_at": datetime.now(timezone.utc).isoformat()
    })
    
    await pot_ws_manager.broadcast({"type": "pot_winner", "data": result})
    
    logger.info(f"Admin {data.admin_wallet} force-drew pot. Winner: {winner['display_name']}")
    
    # Reset pot
    await reset_pot()
    
    return result


@router.get("/bets")
async def admin_get_bets(admin_wallet: str, limit: int = 50):
    """Get recent betting activity (admin only)."""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    history = await db.betting_history.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    
    return {"bets": history, "count": len(history)}


@router.get("/escrow")
async def admin_get_escrow(admin_wallet: str):
    """Get escrow statistics (admin only)."""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    escrow_deposits = await db.escrow_deposits.find({}, {"_id": 0}).to_list(1000)
    
    total_deposited = sum(d.get("amount_sol", 0) for d in escrow_deposits)
    active_deposits = [d for d in escrow_deposits if d.get("status") == "active"]
    
    return {
        "total_deposits": len(escrow_deposits),
        "active_deposits": len(active_deposits),
        "total_volume_sol": round(total_deposited, 4),
        "escrow_wallet": DISTRIBUTION_WALLET
    }



@router.get("/bot-health")
async def admin_bot_health(admin_wallet: str):
    """Get bot health dashboard data (admin only)."""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")

    from datetime import timedelta
    from services.ledger import get_available_balance, get_balance_breakdown

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    last_7d = (now - timedelta(days=7)).isoformat()

    # --- Ledger & On-Chain balances ---
    wallets = await db.custodial_wallets.find({}, {"_id": 0, "user_wallet": 1, "custodial_address": 1}).to_list(100)
    wallet_health = []
    total_on_chain = 0
    total_available = 0

    for w in wallets:
        uw = w["user_wallet"]
        avail = await get_available_balance(uw)
        total_available += avail

        on_chain_sol = 0
        try:
            from routers.custodial_wallet import get_wallet_balance
            from services.token_price import LAMPORTS_PER_SOL
            bal = await get_wallet_balance(w["custodial_address"])
            on_chain_sol = bal / LAMPORTS_PER_SOL
            total_on_chain += on_chain_sol
        except Exception:
            pass

        open_pos = await db.ai_trader_positions.count_documents({"wallet_address": uw, "status": "open"})

        wallet_health.append({
            "user_wallet": f"{uw[:6]}...{uw[-4:]}",
            "custodial": f"{w['custodial_address'][:6]}...{w['custodial_address'][-4:]}",
            "on_chain_sol": round(on_chain_sol, 6),
            "available_sol": round(avail, 6),
            "open_positions": open_pos,
            "funding_status": "critical" if avail < 0.001 else "low" if avail < 0.01 else "ok",
        })

    # --- Recent auto-trade scan logs (last 20) ---
    recent_scans = await db.auto_trade_logs.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)

    # --- Today's trade counts ---
    today_buys = await db.auto_trade_logs.count_documents({
        "action": {"$in": ["auto_buy", "auto_buy_runner", "sniper_buy"]},
        "success": True,
        "created_at": {"$gte": today_start}
    })
    today_exits = await db.ai_trader_positions.count_documents({
        "closed_at": {"$gte": today_start},
        "status": {"$regex": "^closed"}
    })

    # --- 7-day trade counts ---
    week_buys = await db.auto_trade_logs.count_documents({
        "action": {"$in": ["auto_buy", "auto_buy_runner", "sniper_buy"]},
        "success": True,
        "created_at": {"$gte": last_7d}
    })
    week_exits = await db.ai_trader_positions.count_documents({
        "closed_at": {"$gte": last_7d},
        "status": {"$regex": "^closed"}
    })

    # --- Sniper history (last 10) ---
    sniper_hits = await db.sniper_history.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)

    # --- PugBurn reclaim logs (from auto_trade_logs or manual entries) ---
    # We look for trade logs mentioning "burn" or the pugburn collection
    burn_logs = await db.auto_trade_logs.find(
        {"reason": {"$regex": "burn|reclaim", "$options": "i"}},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)

    # --- Open positions summary ---
    open_positions = await db.ai_trader_positions.find(
        {"status": "open"},
        {"_id": 0, "token_symbol": 1, "amount_sol": 1, "entry_price": 1, "confidence": 1,
         "strategy": 1, "is_snipe": 1, "is_runner": 1, "created_at": 1, "wallet_address": 1}
    ).sort("created_at", -1).to_list(50)

    # --- Current bot settings (filter out test wallets) ---
    all_settings = await db.ai_trader_settings.find(
        {"wallet_address": {"$not": {"$regex": "^test_|^TEST_"}}},
        {"_id": 0}
    ).to_list(10)
    bot_configs = []
    for s in all_settings:
        bot_configs.append({
            "wallet": f"{s.get('wallet_address', '?')[:6]}...{s.get('wallet_address', '?')[-4:]}",
            "enabled": s.get("auto_trade_enabled", False),
            "mode": s.get("auto_trade_mode") or s.get("trading_mode", "unknown"),
            "min_conf": s.get("auto_min_confidence", 0.55),
            "max_pos": s.get("auto_max_position_sol", 0.2),
            "max_daily": s.get("auto_max_daily_trades", 10),
            "cooldown": s.get("auto_cooldown_minutes", 15),
            "stop_loss": s.get("auto_stop_loss_percent") or s.get("stop_loss_percent", 10),
            "take_profit": s.get("auto_take_profit_percent") or s.get("take_profit_percent", 20),
        })

    # --- Rake tracking stats ---
    from services.rake_withdrawal import get_rake_stats
    rake_stats = {}
    for w in wallets:
        rs = await get_rake_stats(w["user_wallet"])
        if rs.get("total_collected_sol", 0) > 0 or rs.get("pending_sol", 0) > 0:
            rake_stats[f"{w['user_wallet'][:6]}...{w['user_wallet'][-4:]}"] = rs

    return {
        "checked_at": now.isoformat(),
        "funding": {
            "total_on_chain_sol": round(total_on_chain, 6),
            "total_available_sol": round(total_available, 6),
            "wallets": wallet_health,
            "overall_status": "critical" if total_available < 0.001 else "low" if total_available < 0.01 else "ok",
        },
        "activity": {
            "today_buys": today_buys,
            "today_exits": today_exits,
            "week_buys": week_buys,
            "week_exits": week_exits,
        },
        "open_positions": open_positions,
        "recent_scans": recent_scans,
        "sniper_history": sniper_hits,
        "burn_logs": burn_logs,
        "bot_configs": bot_configs,
        "rake": rake_stats,
    }


# --- Escrow balance + headroom indicator (admin-only) ---

# Recommended buffer to keep on-hand for tx fees + timing-skew during payouts.
# Below this we render a warning in the UI so the operator knows to top up.
ESCROW_HEADROOM_TARGET_SOL = 0.5
ESCROW_HEADROOM_WARN_SOL = 0.1
ESCROW_HEADROOM_CRITICAL_SOL = 0.01


@router.post("/escrow-alert-test")
async def admin_escrow_alert_test(admin_wallet: str):
    """Run an escrow-health check and send a test Telegram alert if configured.

    Lets you confirm the ADMIN_TELEGRAM_CHAT_ID is set correctly without
    having to wait for free capital to actually drop below the threshold.
    """
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Admin only")
    from services.escrow_alerts import check_escrow_and_alert
    import os
    chat_id = os.environ.get("ADMIN_TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        return {
            "status": "skipped",
            "reason": "ADMIN_TELEGRAM_CHAT_ID is not set in backend/.env",
            "instructions": "Message @userinfobot on Telegram to get your numeric chat id, paste it into backend/.env as ADMIN_TELEGRAM_CHAT_ID=<id>, then restart backend.",
        }
    # Force-send by temporarily clearing the throttle state
    await db.system_state.update_one(
        {"_id": "escrow_alert_state"},
        {"$set": {"last_alert_at": None}},
        upsert=True,
    )
    result = await check_escrow_and_alert()
    return {"test": True, "chat_id_configured": bool(chat_id), **result}


@router.get("/escrow-status")
async def admin_escrow_status(admin_wallet: str):
    """Live on-chain escrow balance + headroom assessment for the AdminPanel.

    Gated to the wallets listed in `utils/config.py::ADMIN_WALLETS`
    (currently `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT` and
    `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`).
    """
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Admin only")

    from utils.solana_payout import get_escrow_balance, get_tx_fee_sol
    balance_sol = get_escrow_balance()

    # In-flight obligations: payouts queued but not yet on-chain (open pot/coinflip)
    pot = get_pot()
    pot_obligation_sol = float(pot.get("total_amount_sol") or 0.0)
    open_challenges = await db.betting_challenges.find(
        {"status": {"$in": ["open", "matched", "active", "pending"]}}
    ).to_list(500)
    coinflip_obligation_sol = 0.0
    for c in open_challenges:
        amount = float(c.get("bet_amount_sol") or 0.0)
        # Matched challenges hold 2x bet; open challenges hold 1x
        if c.get("status") in ("matched", "active"):
            coinflip_obligation_sol += amount * 2.0
        else:
            coinflip_obligation_sol += amount
    pending_obligations_sol = pot_obligation_sol + coinflip_obligation_sol

    # Jackpot share — money that's accounted to the prize pool but still sitting in escrow
    prize_pool = await db.prize_pool.find_one({"active": True})
    jackpot_owed_sol = float(prize_pool.get("total_sol") or 0.0) if prize_pool else 0.0

    tx_fee_sol = get_tx_fee_sol()
    if balance_sol is None:
        free_capital_sol: Optional[float] = None
        status = "unknown"
    else:
        free_capital_sol = max(0.0, balance_sol - pending_obligations_sol - jackpot_owed_sol)
        if free_capital_sol < ESCROW_HEADROOM_CRITICAL_SOL:
            status = "critical"
        elif free_capital_sol < ESCROW_HEADROOM_WARN_SOL:
            status = "low"
        elif free_capital_sol < ESCROW_HEADROOM_TARGET_SOL:
            status = "ok"
        else:
            status = "healthy"

    # Recent rake earnings (operator side) over the last 7 days
    from datetime import timedelta
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    pipeline = [
        {"$match": {"created_at": {"$gte": seven_days_ago}}},
        {"$group": {"_id": None, "total_rake_sol": {"$sum": "$rake_sol"}}},
    ]
    coinflip_rake_agg = await db.betting_history.aggregate(pipeline).to_list(1)
    pot_rake_agg = await db.pot_results.aggregate(pipeline).to_list(1)
    coinflip_rake_7d = float(coinflip_rake_agg[0]["total_rake_sol"]) if coinflip_rake_agg else 0.0
    pot_rake_7d = float(pot_rake_agg[0]["total_rake_sol"]) if pot_rake_agg else 0.0
    rake_total_7d = coinflip_rake_7d + pot_rake_7d
    operator_share_7d = rake_total_7d * 0.75  # 75% stays in escrow
    jackpot_share_7d = rake_total_7d * 0.25   # 25% flows to Cosmic Runner jackpot

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "escrow_wallet": DISTRIBUTION_WALLET,
        "balance_sol": round(balance_sol, 6) if balance_sol is not None else None,
        "tx_fee_sol": tx_fee_sol,
        "pending_obligations_sol": round(pending_obligations_sol, 6),
        "jackpot_owed_sol": round(jackpot_owed_sol, 6),
        "free_capital_sol": round(free_capital_sol, 6) if free_capital_sol is not None else None,
        "headroom": {
            "target_sol": ESCROW_HEADROOM_TARGET_SOL,
            "warn_sol": ESCROW_HEADROOM_WARN_SOL,
            "critical_sol": ESCROW_HEADROOM_CRITICAL_SOL,
            "status": status,
        },
        "rake_last_7d": {
            "total_sol": round(rake_total_7d, 6),
            "coinflip_sol": round(coinflip_rake_7d, 6),
            "pot_sol": round(pot_rake_7d, 6),
            "operator_share_sol": round(operator_share_7d, 6),
            "jackpot_share_sol": round(jackpot_share_7d, 6),
        },
    }


@router.get("/rake-summary")
async def rake_summary(wallet: str = Depends(require_admin_jwt)):
    """SIWS-protected lifetime rake & jackpot rollup.

    Single call returns:
      • Lifetime gross rake collected (split by source)
      • The 75 / 25 split (operator share vs jackpot contribution)
      • Lifetime skin revenue + community tips (separate from bet rake)
      • Current active jackpot balance & next payout countdown
      • Lifetime jackpot paid out to leaderboard winners
      • Last-payout details
      • Current operator escrow wallet balance (on-chain)

    All amounts in SOL. Source of truth is the prize_pool contribution log;
    bet-history collections are queried for cross-checking and per-source
    breakdown.
    """
    from datetime import timedelta
    from utils.solana_payout import get_escrow_balance

    now = datetime.now(timezone.utc)

    # ── Lifetime bet rake (coinflip + pot) — sum from history collections ──
    coinflip_agg = await db.betting_history.aggregate([
        {"$group": {"_id": None, "rake_sol": {"$sum": "$rake_sol"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    pot_agg = await db.pot_results.aggregate([
        {"$group": {"_id": None, "rake_sol": {"$sum": "$rake_sol"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    coinflip_rake_lifetime = float(coinflip_agg[0]["rake_sol"]) if coinflip_agg else 0.0
    pot_rake_lifetime = float(pot_agg[0]["rake_sol"]) if pot_agg else 0.0
    coinflip_count = int(coinflip_agg[0]["n"]) if coinflip_agg else 0
    pot_count = int(pot_agg[0]["n"]) if pot_agg else 0
    bet_rake_lifetime = coinflip_rake_lifetime + pot_rake_lifetime

    # ── Lifetime skin revenue — every paid skin purchase ──
    skin_agg = await db.skin_purchases.aggregate([
        {"$match": {
            "tx_signature": {"$ne": "ADMIN_UNLOCK_TESTING"},
            "amount_sol": {"$gt": 0},
        }},
        {"$group": {"_id": None, "revenue_sol": {"$sum": "$amount_sol"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    skin_revenue_lifetime = float(skin_agg[0]["revenue_sol"]) if skin_agg else 0.0
    skin_count = int(skin_agg[0]["n"]) if skin_agg else 0

    # ── Lifetime community tips ──
    tip_agg = await db.pot_tips.aggregate([
        {"$group": {"_id": None, "tip_sol": {"$sum": "$amount_sol"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    tips_lifetime = float(tip_agg[0]["tip_sol"]) if tip_agg else 0.0
    tip_count = int(tip_agg[0]["n"]) if tip_agg else 0

    # ── 75 / 25 split applies to BET rake only. Skin purchases are 100% to
    #    house but 25% of the skin price ALSO contributes to the jackpot
    #    (see add_to_prize_pool source="skin_purchase"). Tips are 100% to
    #    jackpot. We compute the operator/jackpot net flows below.
    operator_share_lifetime = bet_rake_lifetime * 0.75 + skin_revenue_lifetime * 0.75
    # jackpot share = 25% of bet rake + 25% of skin revenue + 100% of tips
    jackpot_contributed_lifetime = (
        bet_rake_lifetime * 0.25 + skin_revenue_lifetime * 0.25 + tips_lifetime
    )

    # ── Current active jackpot pool ──
    active_pool = await db.prize_pool.find_one({"active": True}, {"_id": 0})
    current_pool_sol = float(active_pool.get("total_sol") or 0.0) if active_pool else 0.0
    next_payout_iso = active_pool.get("next_payout_at") if active_pool else None
    time_until_payout_seconds = None
    if next_payout_iso:
        try:
            next_dt = datetime.fromisoformat(next_payout_iso.replace("Z", "+00:00"))
            time_until_payout_seconds = max(0, int((next_dt - now).total_seconds()))
        except Exception:
            pass

    # ── Lifetime jackpot paid out ──
    payouts_agg = await db.prize_payouts.aggregate([
        {"$group": {"_id": None, "paid_sol": {"$sum": "$total_paid_sol"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    jackpot_paid_lifetime = float(payouts_agg[0]["paid_sol"]) if payouts_agg else 0.0
    payout_cycles = int(payouts_agg[0]["n"]) if payouts_agg else 0

    # ── Last payout details ──
    last_payout_doc = await db.prize_payouts.find_one(
        {}, {"_id": 0, "payout_at": 1, "total_paid_sol": 1, "winners": 1},
        sort=[("payout_at", -1)],
    )
    last_payout = None
    if last_payout_doc:
        winners = last_payout_doc.get("winners") or []
        last_payout = {
            "payout_at": last_payout_doc.get("payout_at"),
            "total_paid_sol": round(float(last_payout_doc.get("total_paid_sol") or 0.0), 6),
            "winner_count": len(winners),
            "top_winner": (
                {
                    "display_name": winners[0].get("display_name"),
                    "wallet": winners[0].get("wallet_address"),
                    "prize_sol": round(float(winners[0].get("prize_sol") or 0.0), 6),
                }
                if winners else None
            ),
        }

    # ── Live escrow wallet balance ──
    on_chain_balance = get_escrow_balance()

    # ── 7-day & 24h rollups for the dashboard ──
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    one_day_ago = (now - timedelta(days=1)).isoformat()

    async def _rake_in_window(coll, since_iso: str, time_field: str) -> float:
        agg = await db[coll].aggregate([
            {"$match": {time_field: {"$gte": since_iso}}},
            {"$group": {"_id": None, "rake_sol": {"$sum": "$rake_sol"}}},
        ]).to_list(1)
        return float(agg[0]["rake_sol"]) if agg else 0.0

    coinflip_rake_7d = await _rake_in_window("betting_history", seven_days_ago, "timestamp")
    pot_rake_7d = await _rake_in_window("pot_results", seven_days_ago, "drawn_at")
    coinflip_rake_24h = await _rake_in_window("betting_history", one_day_ago, "timestamp")
    pot_rake_24h = await _rake_in_window("pot_results", one_day_ago, "drawn_at")

    return {
        "checked_at": now.isoformat(),
        "operator_wallet": DISTRIBUTION_WALLET,
        "on_chain_balance_sol": round(on_chain_balance, 6) if on_chain_balance is not None else None,
        "lifetime": {
            "bet_rake_sol": round(bet_rake_lifetime, 6),
            "coinflip_rake_sol": round(coinflip_rake_lifetime, 6),
            "coinflip_count": coinflip_count,
            "pot_rake_sol": round(pot_rake_lifetime, 6),
            "pot_count": pot_count,
            "skin_revenue_sol": round(skin_revenue_lifetime, 6),
            "skin_count": skin_count,
            "tips_sol": round(tips_lifetime, 6),
            "tip_count": tip_count,
            "operator_share_sol": round(operator_share_lifetime, 6),
            "jackpot_contributed_sol": round(jackpot_contributed_lifetime, 6),
            "jackpot_paid_sol": round(jackpot_paid_lifetime, 6),
            "payout_cycles": payout_cycles,
        },
        "current_cycle": {
            "pool_sol": round(current_pool_sol, 6),
            "next_payout_at": next_payout_iso,
            "time_until_payout_seconds": time_until_payout_seconds,
            "last_payout": last_payout,
        },
        "rake_24h": {
            "total_sol": round(coinflip_rake_24h + pot_rake_24h, 6),
            "coinflip_sol": round(coinflip_rake_24h, 6),
            "pot_sol": round(pot_rake_24h, 6),
            "operator_share_sol": round((coinflip_rake_24h + pot_rake_24h) * 0.75, 6),
            "jackpot_share_sol": round((coinflip_rake_24h + pot_rake_24h) * 0.25, 6),
        },
        "rake_7d": {
            "total_sol": round(coinflip_rake_7d + pot_rake_7d, 6),
            "coinflip_sol": round(coinflip_rake_7d, 6),
            "pot_sol": round(pot_rake_7d, 6),
            "operator_share_sol": round((coinflip_rake_7d + pot_rake_7d) * 0.75, 6),
            "jackpot_share_sol": round((coinflip_rake_7d + pot_rake_7d) * 0.25, 6),
        },
        "_authenticated_as": wallet,
    }



# ─── Forum tester cleanup ────────────────────────────────────────────
#
# Automated tests (see `backend/tests/test_p2p_betting_forum.py` and
# related modular-route suites) seed forum posts titled `TEST_...`. On a
# fresh test run those rows persist and end up looking like real user
# content in the /forum feed. This endpoint gives admins a one-click
# repeatable cleanup instead of needing raw DB access. Idempotent:
# running it again with no matches is a no-op.

_TESTER_TITLE_REGEX = "^TEST_"


@router.get("/forum/tester-preview")
async def preview_forum_testers(wallet: str = Depends(require_admin_jwt)):
    """Preview how many forum rows the tester cleanup would delete.

    Match rule: any `forum_posts` document whose `title` starts with
    `TEST_` (case-sensitive, matches the test-suite seed prefix). Also
    counts the replies + likes that would cascade with those posts.
    """
    posts_cursor = db.forum_posts.find(
        {"title": {"$regex": _TESTER_TITLE_REGEX}},
        {"_id": 0, "id": 1, "title": 1, "wallet_address": 1, "created_at": 1, "category": 1},
    ).sort("created_at", -1)
    posts = await posts_cursor.to_list(500)
    post_ids = [p["id"] for p in posts]

    replies_count = 0
    likes_count = 0
    if post_ids:
        replies_count = await db.forum_replies.count_documents({"post_id": {"$in": post_ids}})
        # forum_likes covers both post-likes and reply-likes; only count
        # the ones pointed at the tester posts so we don't over-report.
        likes_count = await db.forum_likes.count_documents({
            "item_id": {"$in": post_ids},
        })

    return {
        "posts": posts,
        "post_count": len(posts),
        "reply_count": replies_count,
        "like_count": likes_count,
        "_authenticated_as": wallet,
    }


@router.post("/forum/clear-testers")
async def clear_forum_testers(wallet: str = Depends(require_admin_jwt)):
    """Delete every `TEST_`-prefixed forum post and its cascade.

    Cascade rules:
      • forum_replies whose `post_id` is in the tester post set
      • forum_likes whose `item_id` is in the tester post OR the
        tester reply set (i.e. reply-likes on cascaded replies)

    Returns the deletion counts + a copy of what was removed so the
    admin has an audit trail in the response body.
    """
    # Snapshot the tester posts FIRST — after the delete_many() runs we
    # can't reconstruct what was removed, and we want to hand the caller
    # a receipt for their audit log.
    tester_posts = await db.forum_posts.find(
        {"title": {"$regex": _TESTER_TITLE_REGEX}},
        {"_id": 0, "id": 1, "title": 1, "wallet_address": 1, "created_at": 1, "category": 1},
    ).to_list(500)
    post_ids = [p["id"] for p in tester_posts]

    if not post_ids:
        return {
            "deleted_posts": 0,
            "deleted_replies": 0,
            "deleted_likes": 0,
            "removed_posts": [],
            "_authenticated_as": wallet,
        }

    # Collect reply ids up-front so we can wipe the likes tied to them.
    reply_ids = [
        r["id"] for r in
        await db.forum_replies.find({"post_id": {"$in": post_ids}}, {"_id": 0, "id": 1}).to_list(2000)
    ]

    likes_res = await db.forum_likes.delete_many({
        "item_id": {"$in": post_ids + reply_ids}
    })
    replies_res = await db.forum_replies.delete_many({"post_id": {"$in": post_ids}})
    posts_res = await db.forum_posts.delete_many({"id": {"$in": post_ids}})

    logger.info(
        "admin_forum_cleanup: wallet=%s posts=%d replies=%d likes=%d",
        wallet, posts_res.deleted_count, replies_res.deleted_count, likes_res.deleted_count,
    )

    return {
        "deleted_posts": posts_res.deleted_count,
        "deleted_replies": replies_res.deleted_count,
        "deleted_likes": likes_res.deleted_count,
        "removed_posts": tester_posts,
        "_authenticated_as": wallet,
    }


# ─── Phase A migration trigger ───────────────────────────────────────
# Runs `scripts/migrate_wallet_to_user_id.py` INSIDE the deployed
# backend so it hits whichever Mongo the container is wired to (i.e.
# production, when triggered from the production admin panel). The
# script itself is idempotent; `apply` also requires an explicit
# `confirm=YES` param so a stray click never mutates data.

from fastapi import Query


@router.post("/run-migration")
async def run_wallet_to_user_id_migration(
    mode: str = Query(..., pattern="^(dry_run|apply|verify)$"),
    confirm: Optional[str] = Query(None, description="Must be 'YES' when mode=apply"),
    wallet: str = Depends(require_admin_jwt),
):
    """Invoke the wallet→user_id hybrid backfill.

    Modes:
      • ``dry_run`` — count what would change, write nothing
      • ``apply``   — actually backfill (requires `confirm=YES`)
      • ``verify``  — read-only audit of current state

    Response is the same JSON shape for all three modes so the admin
    UI can render one component.
    """
    if mode == "apply" and confirm != "YES":
        raise HTTPException(
            status_code=400,
            detail="mode=apply requires ?confirm=YES to prevent accidental runs.",
        )

    # Import lazily so a broken migration module can never take down
    # the whole admin router at import time.
    from scripts.migrate_wallet_to_user_id import run_migration

    logger.info("admin migration triggered: mode=%s by wallet=%s", mode, wallet)
    try:
        report = await run_migration(db, mode)
    except Exception as e:
        logger.exception("migration crashed")
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")

    report["_authenticated_as"] = wallet
    return report

