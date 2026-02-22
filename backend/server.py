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

# Import routers
import sys
sys.path.insert(0, str(Path(__file__).parent))

from routers import (
    betting_router,
    auth_router,
    email_router,
    leaderboard_router,
    skins_router,
    forum_router,
    messages_router,
    journal_router,
    showcase_router,
    notifications_router,
    reflections_router,
    pot_router,
    admin_router,
    newsletter_router,
    checkout_router,
    governance_router,
    staking_router,
    wallet_router,
    escrow_router,
    tokenomics_router
)
from routers.prize_pool import router as prize_pool_router
from routers.profile import router as profile_router
from routers.ai_suggestions import router as ai_suggestions_router
from routers.badges import router as badges_router
from routers.wallet_trades import router as wallet_trades_router
from routers.portfolio import router as portfolio_router
from routers.achievements import router as achievements_router
from routers.ai_chat import router as ai_chat_router
from routers.pot import get_pot_data
from utils.websocket_managers import dm_manager, notification_manager, pot_ws_manager
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


# ========== Register All Routers ==========
api_router.include_router(betting_router)
api_router.include_router(auth_router)
api_router.include_router(email_router)
api_router.include_router(leaderboard_router)
api_router.include_router(skins_router)
api_router.include_router(forum_router)
api_router.include_router(messages_router)
api_router.include_router(journal_router)
api_router.include_router(showcase_router)
api_router.include_router(notifications_router)
api_router.include_router(reflections_router)
api_router.include_router(pot_router)
api_router.include_router(admin_router)
api_router.include_router(newsletter_router)
api_router.include_router(checkout_router)
api_router.include_router(governance_router)
api_router.include_router(staking_router)
api_router.include_router(wallet_router)
api_router.include_router(escrow_router)
api_router.include_router(tokenomics_router)
api_router.include_router(prize_pool_router)
api_router.include_router(profile_router)
api_router.include_router(ai_suggestions_router)
api_router.include_router(badges_router)
api_router.include_router(wallet_trades_router)
api_router.include_router(portfolio_router)
api_router.include_router(achievements_router)

# Register the complete api_router with the app
app.include_router(api_router)


# ========== Startup/Shutdown Events ==========
@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    start_scheduler()
    logger.info("Prize pool scheduler started")


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


# ========== CORS Middleware ==========
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Shutdown Handler ==========
@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection and scheduler on shutdown."""
    stop_scheduler()
    mongo_client.close()
    logger.info("Shutdown complete")
