"""Bullpug API Server - Guardian of the Memecoin Universe.

This is the main FastAPI application. All route logic has been modularized into
separate router files under /routers. This file handles app initialization,
middleware setup, and router registration.
"""

from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent))

from routers import ALL_ROUTERS
from routers.pot import get_pot_data
from utils.websocket_managers import dm_manager, notification_manager, pot_ws_manager, big_wins_manager
from utils.database import db
from utils.scheduler import start_scheduler, stop_scheduler

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)

# Create FastAPI app
app = FastAPI(
    title="Bullpug API",
    description="Guardian of the Memecoin Universe",
    version="2.0.0"
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========== Root Route ==========
@api_router.get("/")
async def root():
    """API root endpoint."""
    return {"message": "Bullpug API - Guardian of the Memecoin Universe"}


@api_router.get("/admin/force-seed")
async def admin_force_seed():
    """Force re-seed the database with correct wallet data. Hit this URL after deploy."""
    from services.post_deploy_init import force_seed
    result = await force_seed()
    return result


@api_router.get("/admin/rpc-diagnostic")
async def rpc_diagnostic():
    """Diagnostic: test RPC connectivity and env vars for debugging sync issues."""
    import os
    import httpx
    helius = os.environ.get("HELIUS_RPC_URL", "")
    alchemy = os.environ.get("ALCHEMY_RPC_URL", "")
    custodial = "CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg"

    results = {}
    for label, url in [("helius", helius), ("alchemy", alchemy)]:
        if not url:
            results[label] = {"status": "NOT_SET", "url_preview": ""}
            continue
        results[label] = {"url_preview": url[:50] + "..."}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json={
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        custodial,
                        {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                        {"encoding": "jsonParsed"}
                    ]
                })
                data = resp.json()
                if "error" in data:
                    results[label]["status"] = "RPC_ERROR"
                    results[label]["error"] = str(data["error"])
                else:
                    accounts = data.get("result", {}).get("value", [])
                    nonzero = [a for a in accounts if a["account"]["data"]["parsed"]["info"]["tokenAmount"].get("uiAmount", 0) > 0]
                    results[label]["status"] = "OK"
                    results[label]["total_accounts"] = len(accounts)
                    results[label]["nonzero_accounts"] = len(nonzero)
                    results[label]["tokens"] = [
                        {"mint": a["account"]["data"]["parsed"]["info"]["mint"][:16] + "...",
                         "amount": a["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]}
                        for a in nonzero
                    ]
        except Exception as e:
            results[label]["status"] = "EXCEPTION"
            results[label]["error"] = str(e)

    return {"diagnostic": results, "custodial_wallet": custodial}


@api_router.post("/admin/force-sync-positions")
async def force_sync_positions(payload: dict):
    """
    Force-create position records from externally-provided on-chain data.
    Accepts: {"user_wallet": "...", "tokens": [{"mint": "...", "symbol": "...", "amount": 0.0, "price_usd": 0.0}]}
    """
    from datetime import datetime, timezone
    import uuid

    user_wallet = payload.get("user_wallet")
    tokens = payload.get("tokens", [])
    if not user_wallet or not tokens:
        return {"success": False, "error": "user_wallet and tokens[] required"}

    # Clear any existing open/pending positions for this wallet first
    cleared = await db.ai_trader_positions.update_many(
        {"wallet_address": user_wallet, "status": {"$in": ["open", "pending_stop_loss", "pending_take_profit"]}},
        {"$set": {"status": "closed_force_sync", "closed_at": datetime.now(timezone.utc).isoformat()}}
    )

    created = []
    for t in tokens:
        mint = t.get("mint", "")
        symbol = t.get("symbol", mint[:8])
        amount = t.get("amount", 0)
        price = t.get("price_usd", 0)
        if not mint or not amount:
            continue

        # CRITICAL: entry_price MUST be > 0 to prevent auto-TP at $0
        entry_price = price if price > 0 else 0
        auto_trade_flag = price > 0

        doc = {
            "position_id": str(uuid.uuid4()),
            "wallet_address": user_wallet,
            "token_symbol": symbol,
            "token_mint": mint,
            "entry_price": entry_price,
            "current_price": entry_price,
            "amount_sol": 0,
            "token_amount": amount,
            "amount_tokens": amount,
            "status": "open",
            "auto_trade": auto_trade_flag,
            "synced_from_chain": True,
            "take_profit_pct": 20.0,
            "stop_loss_pct": -10.0,
            "trailing_stop_enabled": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.ai_trader_positions.insert_one(doc)
        created.append({"symbol": symbol, "amount": amount})

    return {
        "success": True,
        "cleared_old": cleared.modified_count,
        "created": len(created),
        "positions": created
    }


# ========== Register All Routers ==========
for r in ALL_ROUTERS:
    api_router.include_router(r)

# Register the complete api_router with the app
app.include_router(api_router)


# ========== Startup/Shutdown Events ==========
@app.on_event("startup")
async def startup_event():
    """Start background tasks and create indexes on app startup."""
    # Restore in-flight pot from MongoDB before starting the scheduler so
    # the auto-draw job sees the persisted state if the server crashed mid-round.
    try:
        from state.pot_state import load_pot
        await load_pot()
    except Exception as e:
        logger.warning(f"Pot state restore (non-fatal): {e}")

    start_scheduler()
    logger.info("Prize pool scheduler started")

    # Create indexes for new intelligence collections
    try:
        await db.price_candles.create_index([("token_mint", 1), ("interval_key", 1)], unique=True)
        await db.price_candles.create_index([("token_mint", 1), ("timestamp", -1)])
        await db.smart_money_signals.create_index("signature", unique=True)
        await db.smart_money_signals.create_index([("token_mint", 1), ("detected_at", -1)])
        await db.smart_money_signals.create_index("expires_at")
        await db.sentiment_cache.create_index("token_mint", unique=True)
        await db.sentiment_cache.create_index("expires_at")
        await db.ai_trader_positions.create_index([("wallet_address", 1), ("status", 1)])
        await db.user_ledger.create_index([("user_wallet", 1), ("created_at", -1)])
        await db.user_ledger.create_index([("user_wallet", 1), ("entry_type", 1)])
        # Daily drop cache — unique per (user, day), indexed for admin gallery pagination
        await db.daily_drops.create_index([("user_key", 1), ("date_utc", 1)], unique=True)
        await db.daily_drops.create_index([("created_at", -1)])
        # Clean up legacy smart_money_signals (v1 had signature_1 unique index)
        try:
            indexes = await db.smart_money_signals.index_information()
            if "signature_1" in indexes:
                await db.smart_money_signals.drop()
                await db.smart_money_signals.create_index("token_mint", unique=True)
                logger.info("Rebuilt smart_money_signals with v2 schema")
        except Exception:
            pass
        logger.info("MongoDB indexes created for intelligence collections")
    except Exception as e:
        logger.warning(f"Index creation (non-fatal): {e}")

    # Restore ledger state if deploying with a fresh database
    try:
        from services.post_deploy_init import run_post_deploy_init
        await run_post_deploy_init()
    except Exception as e:
        logger.warning(f"Post-deploy init (non-fatal): {e}")


# ========== WebSocket Endpoints ==========
@app.websocket("/ws/pot")
async def pot_websocket(ws: WebSocket):
    """WebSocket for pot real-time updates."""
    await pot_ws_manager.connect(ws)
    try:
        await ws.send_json({"type": "pot_update", "data": await get_pot_data()})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pot_ws_manager.disconnect(ws)
    except Exception:
        pot_ws_manager.disconnect(ws)


@app.websocket("/ws/big-wins")
async def big_wins_websocket(ws: WebSocket):
    """WebSocket for cross-page big-win broadcasts (arena wins ≥ 1 SOL)."""
    await big_wins_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        big_wins_manager.disconnect(ws)
    except Exception:
        big_wins_manager.disconnect(ws)


@app.websocket("/ws/dm/{wallet_address}")
async def dm_websocket(ws: WebSocket, wallet_address: str):
    """WebSocket for direct messages."""
    await dm_manager.connect(ws, wallet_address)
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "send_message":
                to_wallet = data.get("to_wallet")
                content = data.get("content", "")
                from_name = data.get("from_name", "Anonymous")
                
                if to_wallet and content:
                    wallets = sorted([wallet_address, to_wallet])
                    conversation_id = f"{wallets[0]}_{wallets[1]}"
                    
                    message = {
                        "id": str(uuid.uuid4()),
                        "conversation_id": conversation_id,
                        "from_wallet": wallet_address,
                        "from_name": from_name,
                        "to_wallet": to_wallet,
                        "content": content[:2000],
                        "read": False,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    await db.messages.insert_one(message)
                    
                    # Send to recipient
                    await dm_manager.send_personal_message({
                        "type": "new_message",
                        "data": {k: v for k, v in message.items() if k != "_id"}
                    }, to_wallet)
                    
                    # Confirm to sender
                    await ws.send_json({
                        "type": "message_sent",
                        "data": {k: v for k, v in message.items() if k != "_id"}
                    })
    except WebSocketDisconnect:
        dm_manager.disconnect(wallet_address)
    except Exception as e:
        logger.error(f"DM WebSocket error: {e}")
        dm_manager.disconnect(wallet_address)


@app.websocket("/ws/notifications/{wallet_address}")
async def notification_websocket(ws: WebSocket, wallet_address: str):
    """WebSocket for notifications."""
    await notification_manager.connect(ws, wallet_address)
    try:
        # Send unread notifications on connect
        notifications = await db.notifications.find(
            {"to_wallet": wallet_address, "read": False},
            {"_id": 0}
        ).sort("created_at", -1).to_list(20)
        
        await ws.send_json({
            "type": "initial_notifications",
            "data": notifications
        })
        
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(wallet_address)
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")
        notification_manager.disconnect(wallet_address)


# ========== CSRF Protection Middleware ==========
# Stateless API hardening — defence-in-depth on every state-changing request.
#
# **Threat model & defence layers** (in order of importance):
#
# 1. **Custom header check** (`X-Bullpug-CSRF: 1`)
#    This is the actual CSRF defence. A cross-origin attacker site CANNOT
#    add a custom header to a fetch() call without a successful CORS
#    preflight, and our CORS allowlist only grants preflight to known
#    origins. This is the OWASP-recommended "custom request header"
#    pattern. (Browsers in 2026 still enforce this.)
#
# 2. **Referer allowlist** (when present)
#    The Cloudflare Worker that fronts both the preview env and
#    bullpug.com REWRITES the `Origin` header to an internal cluster
#    URL, so Origin can't be trusted. The `Referer` header is passed
#    through verbatim. When present, we require it to start with an
#    allowlisted origin. If absent (some privacy modes strip it), we
#    fall through to the custom-header check alone.
#
# 3. **X-Forwarded-Host fallback**
#    Set by the ingress. Useful as a tertiary signal when Referer is
#    stripped — must match the user-facing host of an allowlisted entry.
#
# Exemptions: GET/HEAD/OPTIONS (read-only), Stripe webhook (signature
# auth), RPC diagnostics, WebSocket upgrades.
from urllib.parse import urlparse
from fastapi import Request
from fastapi.responses import JSONResponse

_CSRF_EXEMPT_METHODS = {"GET", "HEAD", "OPTIONS"}
_CSRF_EXEMPT_PATHS = {
    "/api/webhook/stripe",       # Stripe verifies via signature header
    "/api/admin/force-seed",     # Server-to-server diagnostic
    "/api/admin/rpc-diagnostic", # Server-to-server diagnostic
    "/api/client-errors",        # Client crash reporter — best-effort intake
                                  # from possibly-broken pages where the
                                  # CSRF header may itself be the failure.
    "/api/analytics/track",      # Pageview tracker — best-effort, no PII,
                                  # rate-limited at the router. Exempt so a
                                  # broken CSRF interceptor on a crashing
                                  # page can't poison the traffic data.
}
_CSRF_EXEMPT_PREFIXES = (
    "/api/ws/",
)


def _parse_origin(value: str) -> tuple[str, str]:
    """Return (scheme+host[:port], host) from a URL or origin string."""
    if not value:
        return "", ""
    try:
        p = urlparse(value)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}", p.netloc
        # Fallback: treat as a bare host
        return "", value.strip()
    except Exception:
        return "", ""


def _csrf_allowed_origins() -> set[str]:
    """Parse the CORS_ORIGINS env into a set of exact scheme+host[:port]."""
    raw = os.environ.get("CORS_ORIGINS", "*")
    return {o.strip() for o in raw.split(",") if o.strip()}


@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    method = request.method.upper()
    path = request.url.path
    if (
        method in _CSRF_EXEMPT_METHODS
        or path in _CSRF_EXEMPT_PATHS
        or any(path.startswith(p) for p in _CSRF_EXEMPT_PREFIXES)
        or not path.startswith("/api/")
    ):
        return await call_next(request)

    allowed_origins = _csrf_allowed_origins()
    wildcard = "*" in allowed_origins

    # LAYER 1 — Custom header is the actual CSRF defence. Required always.
    if not request.headers.get("x-bullpug-csrf"):
        logger.warning("CSRF reject: missing X-Bullpug-CSRF path=%s", path)
        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF check failed: missing X-Bullpug-CSRF header."},
        )

    # LAYER 2 — Referer allowlist (best available origin signal behind the
    # Cloudflare worker). Origin is intentionally NOT checked because the
    # ingress rewrites it to an internal cluster URL. X-Forwarded-Host is
    # also NOT used because the ingress sets it to OUR hostname regardless
    # of who the actual requester is, so it's a useless CSRF signal here.
    if not wildcard:
        referer = request.headers.get("referer") or ""
        if referer:
            referer_origin, _ = _parse_origin(referer)
            referer_ok = bool(referer_origin) and any(
                referer_origin == a or referer_origin.startswith(a)
                for a in allowed_origins
            )
            if not referer_ok:
                logger.warning(
                    "CSRF reject: bad referer path=%s referer=%s",
                    path, referer[:80]
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF check failed: referer not allowed."},
                )
        # If Referer is absent (privacy-mode browser strips it), the
        # custom-header check above is the sole defence. That alone is
        # the OWASP-blessed minimum for CSRF protection on a custom-header-
        # required stateless API, so we let it through.

    return await call_next(request)


# ========== CORS Middleware ==========
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*", "X-Bullpug-CSRF"],
)


# ========== Shutdown Handler ==========
@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection and scheduler on shutdown."""
    stop_scheduler()
    mongo_client.close()
    logger.info("Shutdown complete")
