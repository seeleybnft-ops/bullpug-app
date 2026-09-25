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



# ─── Pug Pit admin endpoints — archived 18 Sep 2026 ─────────────────
# The following endpoints were moved out of the live admin surface
# alongside the Pug Pit stack. They lived here previously:
#   GET  /admin/challenges          — list P2P coin-flip challenges
#   POST /admin/challenge/cancel    — cancel a challenge and refund
#   POST /admin/pot/draw            — force a jackpot draw
#   GET  /admin/bets                — recent betting activity
#   GET  /admin/escrow              — escrow stats summary
# To restore: `git log --diff-filter=D -p -- backend/routers/admin.py`
# and copy the deleted blocks back in.




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



# ─── Pug Pit rake / escrow endpoints — archived 18 Sep 2026 ─────────
# Removed alongside the Pug Pit stack:
#   POST /admin/escrow-alert-test   — trigger a test Telegram escrow alert
#   GET  /admin/escrow-status       — on-chain escrow balance + headroom
#   GET  /admin/rake-summary        — SIWS-gated lifetime rake & jackpot rollup
# To restore: `git log --diff-filter=D -p -- backend/routers/admin.py`




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



# ─── Auth breakdown (Phase C — spec Part 7) ─────────────────────────
# Read-only snapshot of the users collection + 24h signup deltas +
# email OTP conversion rate. Powers the admin auth breakdown card.

@router.get("/auth/breakdown")
async def get_auth_breakdown(wallet: str = Depends(require_admin_jwt)):
    """Return { totals, last_24h, email_verification_rate }.

    Test-user fixtures (mailinator emails, `test_*` / `phaseb-*` /
    `siwsprobe*` wallets from automated agents) are filtered so the
    admin sees real-user counts only. See `utils.test_wallet_filter`
    for the canonical patterns.
    """
    from datetime import datetime, timezone, timedelta
    from utils.test_wallet_filter import TEST_WALLET_REGEX, TEST_EMAIL_REGEX

    _not_test_email = {"$not": {"$regex": TEST_EMAIL_REGEX, "$options": "i"}}
    _not_test_wallet = {"$not": {"$regex": TEST_WALLET_REGEX}}

    async def _count(auth_type: str, since_iso: Optional[str] = None) -> int:
        q: dict = {"auth_type": auth_type, "merged_into": {"$exists": False}}
        # Filter test rows on the field appropriate to the auth_type.
        # Email + linked rows carry an `email`; wallet rows carry
        # `wallet_address`. Passing `$not $regex` on a null/missing
        # field trivially matches, so this is safe to apply either way.
        if auth_type == "wallet":
            q["wallet_address"] = _not_test_wallet
        else:
            q["email"] = _not_test_email
        if since_iso:
            q["created_at"] = {"$gte": since_iso}
        return await db.users.count_documents(q)

    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=24)).isoformat()

    totals = {
        "email": await _count("email"),
        "wallet": await _count("wallet"),
        "linked": await _count("linked"),
    }
    last_24h = {
        "email": await _count("email", since),
        "wallet": await _count("wallet", since),
        "linked": await _count("linked", since),
    }
    otp_requested = await db.auth_otps.count_documents({
        "created_at": {"$gte": since},
        "email": _not_test_email,
    })
    otp_verified = await db.auth_otps.count_documents({
        "created_at": {"$gte": since},
        "email": _not_test_email,
        "verified_at": {"$exists": True},
    })
    rate = round(otp_verified / otp_requested, 3) if otp_requested else 0.0

    return {
        "totals": totals,
        "totals_grand": sum(totals.values()),
        "last_24h": last_24h,
        "email_verification_rate_24h": rate,
        "otp_requested_24h": otp_requested,
        "otp_verified_24h": otp_verified,
        "_authenticated_as": wallet,
    }


@router.get("/auth/lookup")
async def lookup_user(
    q: str,
    wallet: str = Depends(require_admin_jwt),
):
    """Fuzzy-search users by email or wallet_address. Case-insensitive.

    Returns up to 20 matches. Sanitises the query so shell metacharacters
    aren't interpreted as regex. Test-user fixtures are excluded so the
    admin doesn't see mailinator + phaseb-* pollution when searching.
    An admin can force-include them by prefixing the query with `test:`.
    """
    import re as _re
    from utils.test_wallet_filter import TEST_WALLET_REGEX, TEST_EMAIL_REGEX

    raw = (q or "").strip()
    include_test = False
    if raw.lower().startswith("test:"):
        include_test = True
        raw = raw[5:].strip()
    if not raw or len(raw) < 3:
        raise HTTPException(status_code=400, detail="Search must be at least 3 characters")
    pattern = _re.escape(raw)

    or_clause = {"$or": [
        {"email": {"$regex": pattern, "$options": "i"}},
        {"wallet_address": {"$regex": pattern, "$options": "i"}},
        {"user_id": {"$regex": pattern, "$options": "i"}},
    ]}
    and_clauses = [{"merged_into": {"$exists": False}}, or_clause]
    if not include_test:
        and_clauses.append({"email": {"$not": {"$regex": TEST_EMAIL_REGEX, "$options": "i"}}})
        and_clauses.append({"wallet_address": {"$not": {"$regex": TEST_WALLET_REGEX}}})

    rows = await db.users.find(
        {"$and": and_clauses},
        {"_id": 0, "user_id": 1, "email": 1, "wallet_address": 1, "auth_type": 1, "created_at": 1},
    ).limit(20).to_list(20)

    for r in rows:
        r["unlocked_count"] = await db.archive_unlocks.count_documents({
            "$or": [
                {"user_id": r["user_id"]},
                {"wallet_address": r.get("wallet_address")},
            ]
        })

    return {"matches": rows, "count": len(rows), "test_included": include_test}


# ─── Archive lore-card image sweep ──────────────────────────────────
# One-click regeneration of every lore-card thumbnail. Useful after a
# prompt-tuning change (like the mandatory Bullpughan style suffix) so
# admins don't have to click-regen 72 entries individually.

@router.post("/archive/regenerate-all-images")
async def admin_regenerate_all_lore_images(wallet: str = Depends(require_admin_jwt)):
    """Kick off a background sweep that regenerates every non-special
    lore-card image using the current prompt. Returns immediately with
    the job envelope; poll `GET /archive/regenerate-all-images/status`
    for progress. If a sweep is already running, returns that job's
    state instead of starting a second one.
    """
    from services.archive_achievements import start_regen_all_entry_images
    envelope = await start_regen_all_entry_images()
    logger.info("admin regen-all-images kicked off by %s: job=%s", wallet, envelope.get("job_id"))
    return envelope


@router.get("/archive/regenerate-all-images/status")
async def admin_regen_all_lore_images_status(wallet: str = Depends(require_admin_jwt)):
    """Return the current or most-recent sweep job's progress."""
    from services.archive_achievements import get_regen_status
    return await get_regen_status()

