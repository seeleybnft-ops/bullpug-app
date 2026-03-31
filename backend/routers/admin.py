"""Admin routes for dashboard and management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import secrets
import logging

from utils.database import db
from utils.config import DISTRIBUTION_WALLET, is_admin
from utils.websocket_managers import pot_ws_manager
from state.pot_state import get_pot, reset_pot

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
    
    # Draw winner
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
    
    result = {
        "winner_name": winner["display_name"],
        "winner_wallet": winner["winner_wallet"] if "winner_wallet" in winner else winner["wallet_address"],
        "payout_sol": payout,
        "total_pot_sol": total,
        "rake_sol": rake,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(pot["entries"])
    }
    
    pot["winner"] = result
    pot["status"] = "completed"
    
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
    reset_pot()
    
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
    }
