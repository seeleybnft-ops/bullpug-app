from fastapi import FastAPI, APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging
import hashlib
import secrets
import httpx
import asyncio
import numpy as np
import json as jsonlib
import csv
import io
import base64
import base58
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest
)
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Import routers - using sys.path hack for development
import sys
from pathlib import Path
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
    showcase_router
)
from utils.websocket_managers import dm_manager, notification_manager, pot_ws_manager, ConnectionManager, BroadcastManager

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ['DB_NAME']]

stripe_api_key = os.environ.get('STRIPE_API_KEY')

# SendGrid Configuration
sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
sender_email = os.environ.get('SENDER_EMAIL', 'noreply@bullpug.com')

# P2P Betting Configuration
RAKE_PERCENT = 2.5
DISTRIBUTION_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"

# Admin wallets
ADMIN_WALLETS = [
    "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT",  # Fee wallet
    "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"   # Personal wallet
]

# Escrow wallet (for holding bets)
ESCROW_WALLET = DISTRIBUTION_WALLET  # Using distribution wallet as escrow for simplicity

app = FastAPI()

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# WebSocket managers imported from utils.websocket_managers


# ========== Models ==========
class NewsletterSubscribe(BaseModel):
    email: str

class CheckoutRequest(BaseModel):
    product_id: str
    quantity: int = 1
    origin_url: str

class CoinTossFlip(BaseModel):
    client_seed: str
    bet_amount: float
    choice: str
    wallet_address: Optional[str] = None

# P2P Coin Flip Challenge Models
class CreateChallengeRequest(BaseModel):
    bet_amount_sol: float
    choice: str  # heads or tails
    wallet_address: str
    display_name: str = "Anonymous Guardian"
    signature: Optional[str] = None  # Optional wallet signature for verification
    message: Optional[str] = None  # Message that was signed

class AcceptChallengeRequest(BaseModel):
    challenge_id: str
    wallet_address: str
    display_name: str = "Anonymous Guardian"
    client_seed: str
    signature: Optional[str] = None
    message: Optional[str] = None

# P2P Pot Models
class P2PPotJoinRequest(BaseModel):
    bet_amount_sol: float
    wallet_address: str
    display_name: str = "Anonymous Guardian"
    tx_signature: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None

# Forum Models
class CreatePostRequest(BaseModel):
    title: str
    content: str
    author_wallet: str
    author_name: str = "Anonymous"
    category: str = "general"

class CreateReplyRequest(BaseModel):
    post_id: str
    content: str
    author_wallet: str
    author_name: str = "Anonymous"

# Direct Messaging Models
class SendMessageRequest(BaseModel):
    to_wallet: str
    content: str
    from_wallet: str
    from_name: str = "Anonymous"

class ConversationRequest(BaseModel):
    wallet1: str
    wallet2: str

# Notification Models
class PushSubscription(BaseModel):
    wallet_address: str
    subscription: dict  # Push subscription object from browser

class NotificationRequest(BaseModel):
    to_wallet: str
    title: str
    body: str
    type: str = "general"  # general, challenge, message, pot

# Escrow Transaction Models
class EscrowDepositRequest(BaseModel):
    wallet_address: str
    amount_sol: float
    tx_signature: str
    purpose: str  # challenge, pot
    reference_id: str  # challenge_id or pot_id

class EscrowWithdrawRequest(BaseModel):
    wallet_address: str
    amount_sol: float

# Admin Models
class AdminDrawPotRequest(BaseModel):
    admin_wallet: str
    pot_id: Optional[str] = None

class AdminManageChallengeRequest(BaseModel):
    admin_wallet: str
    challenge_id: str
    action: str  # cancel, refund

# Journal Backup Models
class JournalBackupRequest(BaseModel):
    wallet_address: str

class JournalRestoreRequest(BaseModel):
    wallet_address: str
    backup_data: dict

class PotJoinRequest(BaseModel):
    bet_amount: float
    wallet_address: Optional[str] = None
    display_name: str = "Anonymous Guardian"

class VoteRequest(BaseModel):
    proposal_id: str
    vote: str
    wallet_address: Optional[str] = None

class StakingSimRequest(BaseModel):
    amount: float
    duration_days: int
    apy: float = 12.0

class ExitSimRequest(BaseModel):
    token_amount: float
    entry_price: float
    exit_prices: List[float]
    tax_rate: float = 15.0

class MonteCarloRequest(BaseModel):
    token_amount: float
    entry_price: float
    volatility: float = 0.8
    drift: float = 0.1
    days: int = 180
    simulations: int = 1000
    tax_rate: float = 15.0


# ========== Helper Functions ==========
def is_admin(wallet_address: str) -> bool:
    return wallet_address in ADMIN_WALLETS

async def send_notification(to_wallet: str, title: str, body: str, notif_type: str = "general"):
    """Store notification and send via WebSocket if user is connected"""
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
    # Send via WebSocket
    await notification_manager.send_personal_message({
        "type": "notification",
        "data": {k: v for k, v in notification.items() if k != "_id"}
    }, to_wallet)
    return notification


# ========== Email Service ==========
async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send email via SendGrid"""
    if not sendgrid_api_key:
        logger.warning("SendGrid API key not configured - email not sent")
        return False
    
    try:
        message = Mail(
            from_email=sender_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}, status: {response.status_code}")
        return response.status_code == 202
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


async def send_welcome_email(email: str, wallet_address: str):
    """Send welcome email to new users"""
    html_content = f"""
    <html>
    <body style="font-family: 'Space Grotesk', Arial, sans-serif; background-color: #0A0A12; color: #fff; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 100%); border-radius: 16px; padding: 40px; border: 1px solid rgba(0,255,163,0.2);">
            <img src="https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png" alt="Bullpug" style="width: 80px; height: 80px; border-radius: 50%; margin-bottom: 20px;">
            <h1 style="color: #00FFA3; font-size: 28px; margin-bottom: 10px;">Welcome to Bullpug!</h1>
            <p style="color: #94a3b8; font-size: 16px; line-height: 1.6;">
                Your wallet <strong style="color: #fff;">{wallet_address[:8]}...{wallet_address[-4:]}</strong> has joined the Bullpug community!
            </p>
            <div style="background: rgba(0,255,163,0.1); border: 1px solid rgba(0,255,163,0.3); border-radius: 12px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #00FFA3; margin-bottom: 10px;">What you can do:</h3>
                <ul style="color: #94a3b8; padding-left: 20px;">
                    <li>Play P2P betting games with real SOL</li>
                    <li>Compete in the Speed Run game leaderboard</li>
                    <li>Track your trades with the Trading Journal</li>
                    <li>Join the community forum discussions</li>
                </ul>
            </div>
            <a href="https://bullpug.com" style="display: inline-block; background: #00FFA3; color: #000; font-weight: bold; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin-top: 20px;">
                Start Exploring
            </a>
            <p style="color: #64748b; font-size: 12px; margin-top: 30px;">
                Follow us: <a href="https://x.com/Bullpugcoin" style="color: #00FFA3;">@Bullpugcoin</a> | <a href="https://t.me/bullpugcoinchat" style="color: #00FFA3;">Telegram</a>
            </p>
        </div>
    </body>
    </html>
    """
    return await send_email(email, "Welcome to Bullpug - Guardian of the Memecoin Universe!", html_content)


async def send_weekly_summary_email(email: str, wallet_address: str, summary: dict):
    """Send weekly performance summary email"""
    pnl_color = "#00FFA3" if summary.get('total_pnl', 0) >= 0 else "#FF4444"
    pnl_sign = "+" if summary.get('total_pnl', 0) >= 0 else ""
    
    html_content = f"""
    <html>
    <body style="font-family: 'Space Grotesk', Arial, sans-serif; background-color: #0A0A12; color: #fff; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 100%); border-radius: 16px; padding: 40px; border: 1px solid rgba(0,255,163,0.2);">
            <img src="https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png" alt="Bullpug" style="width: 60px; height: 60px; border-radius: 50%; margin-bottom: 20px;">
            <h1 style="color: #00FFA3; font-size: 24px; margin-bottom: 10px;">Your Weekly Summary</h1>
            <p style="color: #94a3b8; font-size: 14px;">Week ending {datetime.now(timezone.utc).strftime('%B %d, %Y')}</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 25px 0;">
                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">TOTAL P&L</p>
                    <p style="color: {pnl_color}; font-size: 24px; font-weight: bold;">{pnl_sign}${summary.get('total_pnl', 0):.2f}</p>
                </div>
                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">WIN RATE</p>
                    <p style="color: #00FFA3; font-size: 24px; font-weight: bold;">{summary.get('win_rate', 0):.1f}%</p>
                </div>
                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">TOTAL TRADES</p>
                    <p style="color: #fff; font-size: 24px; font-weight: bold;">{summary.get('total_trades', 0)}</p>
                </div>
                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">BETS PLACED</p>
                    <p style="color: #D946EF; font-size: 24px; font-weight: bold;">{summary.get('bets_placed', 0)}</p>
                </div>
            </div>
            
            <a href="https://bullpug.com/journal" style="display: inline-block; background: #00FFA3; color: #000; font-weight: bold; padding: 12px 24px; border-radius: 8px; text-decoration: none;">
                View Full Journal
            </a>
            <p style="color: #64748b; font-size: 11px; margin-top: 30px;">
                To unsubscribe from weekly summaries, update your preferences in the app settings.
            </p>
        </div>
    </body>
    </html>
    """
    return await send_email(email, f"Bullpug Weekly Summary - {pnl_sign}${summary.get('total_pnl', 0):.2f}", html_content)


# ========== Wallet Signature Verification ==========
def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    """
    Verify a Solana wallet signature to ensure the user owns the wallet.
    This prevents impersonation attacks where someone uses another user's wallet address.
    """
    try:
        # Decode the wallet public key
        public_key_bytes = base58.b58decode(wallet_address)
        verify_key = VerifyKey(public_key_bytes)
        
        # Decode the signature
        signature_bytes = base58.b58decode(signature)
        
        # Encode the message
        message_bytes = message.encode('utf-8')
        
        # Verify the signature
        verify_key.verify(message_bytes, signature_bytes)
        return True
    except BadSignatureError:
        logger.warning(f"Invalid signature for wallet {wallet_address[:8]}...")
        return False
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def verify_request_signature(wallet_address: str, signature: Optional[str], message: Optional[str], strict: bool = False) -> bool:
    """
    Helper to verify request signature. If strict=True, reject if signature is missing.
    If strict=False, allow requests without signature (backward compatible).
    """
    if not signature or not message:
        if strict:
            return False
        return True  # Allow unsigned requests in non-strict mode
    
    return verify_wallet_signature(wallet_address, message, signature)


# PotWSManager imported from utils.websocket_managers


# ========== Products ==========
PRODUCTS = {
    "guardian-plush": {
        "id": "guardian-plush",
        "name": "Bullpug Guardian Plushie",
        "description": "The ultimate cosmic guardian in plush form! Cape, bull horns, and glow-in-the-dark eyes.",
        "price": 29.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/7x0weeyi_download%20-%202026-02-17T063439.078.png",
        "category": "plushie"
    },
    "space-pug-plush": {
        "id": "space-pug-plush",
        "name": "Cyber Bullpug Plushie",
        "description": "Bullpug in full cyber armor! LED visor included. Ready to patrol the blockchain.",
        "price": 34.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/kynwxxke_image%20-%202026-02-17T063523.593.jpg",
        "category": "plushie"
    },
    "mini-pug-pack": {
        "id": "mini-pug-pack",
        "name": "Mini Bullpug Pack (Set of 3)",
        "description": "Three adorable mini Bullpugs: Guardian, Cosmic, and Golden Bull variants.",
        "price": 19.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/5w17pptk__eda5997e-289f-4f2c-916b-329017a171d6.jfif",
        "category": "plushie"
    },
    "cape-edition": {
        "id": "cape-edition",
        "name": "Bullpug Maid Edition (XL)",
        "description": "Deluxe oversized Bullpug in maid outfit. The ultimate collector's item with real fabric accessories.",
        "price": 49.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/2sae826h_25.10.2024_17.06.12_REC.png",
        "category": "plushie"
    }
}

PROPOSALS = [
    {"id": "prop-1", "title": "Increase Burn Rate to 3%", "description": "Increase the burn rate from 2% to 3% per transaction to accelerate deflation.", "status": "active", "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()},
    {"id": "prop-2", "title": "Launch Bullpug Game Season 2", "description": "Allocate 2% of ecosystem reserve for Game Season 2 with new cosmic levels.", "status": "active", "end_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()},
    {"id": "prop-3", "title": "Partner with CosmicDogs DAO", "description": "Cross-promote with CosmicDogs DAO for joint NFT drops and shared liquidity.", "status": "active", "end_date": (datetime.now(timezone.utc) + timedelta(days=21)).isoformat()},
]


# ========== Routes ==========
@api_router.get("/")
async def root():
    return {"message": "Bullpug API - Guardian of the Memecoin Universe"}


@api_router.post("/newsletter/subscribe")
async def subscribe_newsletter(data: NewsletterSubscribe):
    existing = await db.newsletter_subscribers.find_one({"email": data.email}, {"_id": 0})
    if existing:
        return {"message": "Already subscribed!", "status": "existing"}
    doc = {"id": str(uuid.uuid4()), "email": data.email, "subscribed_at": datetime.now(timezone.utc).isoformat(), "active": True}
    await db.newsletter_subscribers.insert_one(doc)
    return {"message": "Welcome to the Guardian newsletter!", "status": "success"}


@api_router.get("/products")
async def get_products():
    return {"products": list(PRODUCTS.values())}


@api_router.post("/checkout/session")
async def create_checkout_session(request: Request, data: CheckoutRequest):
    if data.product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    product = PRODUCTS[data.product_id]
    amount = product["price"] * data.quantity

    success_url = f"{data.origin_url}/shop?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/shop"

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)

    checkout_req = CheckoutSessionRequest(
        amount=float(amount), currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"product_id": data.product_id, "product_name": product["name"], "quantity": str(data.quantity)}
    )
    session = await stripe_checkout.create_checkout_session(checkout_req)

    tx = {"id": str(uuid.uuid4()), "session_id": session.session_id, "amount": float(amount), "currency": "usd",
          "product_id": data.product_id, "quantity": data.quantity, "payment_status": "initiated", "status": "pending",
          "created_at": datetime.now(timezone.utc).isoformat()}
    await db.payment_transactions.insert_one(tx)
    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/checkout/status/{session_id}")
async def get_checkout_status(request: Request, session_id: str):
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    status = await stripe_checkout.get_checkout_status(session_id)
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status.payment_status,
                  "status": "completed" if status.payment_status == "paid" else status.status,
                  "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"status": status.status, "payment_status": status.payment_status,
            "amount_total": status.amount_total, "currency": status.currency}


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        if webhook_response and webhook_response.session_id:
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {"payment_status": webhook_response.payment_status,
                          "status": "completed" if webhook_response.payment_status == "paid" else "failed",
                          "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error"}


# ========== P2P COIN FLIP (Challenge System) ==========
@api_router.get("/betting/config")
async def get_betting_config():
    """Get betting configuration including rake and distribution wallet"""
    return {
        "rake_percent": RAKE_PERCENT,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "currency": "SOL",
        "min_bet_sol": 0.01,
        "max_bet_sol": 10.0
    }


@api_router.get("/auth/sign-message/{wallet_address}")
async def get_sign_message(wallet_address: str, action: str = "general"):
    """Generate a message for wallet signature verification"""
    nonce = secrets.token_hex(16)
    timestamp = datetime.now(timezone.utc).isoformat()
    message = f"Bullpug Action: {action}\nWallet: {wallet_address}\nNonce: {nonce}\nTimestamp: {timestamp}"
    
    # Store nonce for verification (expires in 5 minutes)
    await db.auth_nonces.insert_one({
        "nonce": nonce,
        "wallet_address": wallet_address,
        "action": action,
        "created_at": timestamp,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    })
    
    return {"message": message, "nonce": nonce}


@api_router.post("/auth/verify-signature")
async def verify_signature(wallet_address: str, message: str, signature: str):
    """Verify a wallet signature"""
    is_valid = verify_wallet_signature(wallet_address, message, signature)
    return {"valid": is_valid, "wallet": wallet_address}


@api_router.post("/betting/challenge/create")
@limiter.limit("10/minute")
async def create_challenge(request: Request, data: CreateChallengeRequest):
    """Create a P2P coin flip challenge"""
    if data.bet_amount_sol <= 0:
        raise HTTPException(status_code=400, detail="Bet must be positive")
    if data.bet_amount_sol < 0.01:
        raise HTTPException(status_code=400, detail="Minimum bet is 0.01 SOL")
    if data.bet_amount_sol > 10.0:
        raise HTTPException(status_code=400, detail="Maximum bet is 10 SOL")
    if data.choice.lower() not in ["heads", "tails"]:
        raise HTTPException(status_code=400, detail="Choice must be heads or tails")
    
    challenge = {
        "id": str(uuid.uuid4()),
        "creator_wallet": data.wallet_address,
        "creator_name": data.display_name,
        "creator_choice": data.choice.lower(),
        "bet_amount_sol": data.bet_amount_sol,
        "status": "open",  # open, matched, completed, cancelled
        "opponent_wallet": None,
        "opponent_name": None,
        "winner_wallet": None,
        "result": None,
        "rake_sol": round(data.bet_amount_sol * 2 * RAKE_PERCENT / 100, 6),
        "payout_sol": round(data.bet_amount_sol * 2 * (1 - RAKE_PERCENT / 100), 6),
        "server_seed_hash": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "matched_at": None,
        "completed_at": None
    }
    
    # Generate server seed hash (seed revealed after match)
    server_seed = secrets.token_hex(32)
    challenge["server_seed"] = server_seed
    challenge["server_seed_hash"] = hashlib.sha256(server_seed.encode()).hexdigest()
    
    await db.p2p_challenges.insert_one(challenge)
    
    # Don't expose server_seed yet
    return {
        "challenge_id": challenge["id"],
        "bet_amount_sol": challenge["bet_amount_sol"],
        "creator_choice": challenge["creator_choice"],
        "server_seed_hash": challenge["server_seed_hash"],
        "status": "open",
        "message": f"Challenge created! Waiting for opponent to bet {data.bet_amount_sol} SOL on {('tails' if data.choice.lower() == 'heads' else 'heads')}"
    }


@api_router.get("/betting/challenges")
async def get_open_challenges(limit: int = 20):
    """Get all open P2P challenges"""
    challenges = await db.p2p_challenges.find(
        {"status": "open"},
        {"_id": 0, "server_seed": 0}
    ).sort("created_at", -1).to_list(limit)
    return {"challenges": challenges}


@api_router.get("/betting/challenge/{challenge_id}")
async def get_challenge(challenge_id: str):
    """Get a specific challenge"""
    challenge = await db.p2p_challenges.find_one({"id": challenge_id}, {"_id": 0})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    # Only expose server_seed if completed
    if challenge["status"] != "completed":
        challenge.pop("server_seed", None)
    return challenge


@api_router.post("/betting/challenge/accept")
@limiter.limit("20/minute")
async def accept_challenge(request: Request, data: AcceptChallengeRequest):
    """Accept a P2P coin flip challenge and execute the flip"""
    challenge = await db.p2p_challenges.find_one({"id": data.challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge["status"] != "open":
        raise HTTPException(status_code=400, detail="Challenge is not open")
    if challenge["creator_wallet"] == data.wallet_address:
        raise HTTPException(status_code=400, detail="Cannot accept your own challenge")
    
    # Execute the flip
    server_seed = challenge["server_seed"]
    combined = f"{server_seed}{data.client_seed}"
    result_hash = hashlib.sha256(combined.encode()).hexdigest()
    last_digit = int(result_hash[-1], 16)
    outcome = "heads" if last_digit % 2 == 0 else "tails"
    
    # Determine winner
    creator_won = outcome == challenge["creator_choice"]
    winner_wallet = challenge["creator_wallet"] if creator_won else data.wallet_address
    winner_name = challenge["creator_name"] if creator_won else data.display_name
    loser_wallet = data.wallet_address if creator_won else challenge["creator_wallet"]
    
    # Calculate payouts
    total_pot = challenge["bet_amount_sol"] * 2
    rake = round(total_pot * RAKE_PERCENT / 100, 6)
    payout = round(total_pot - rake, 6)
    
    # Update challenge
    update_data = {
        "status": "completed",
        "opponent_wallet": data.wallet_address,
        "opponent_name": data.display_name,
        "opponent_choice": "tails" if challenge["creator_choice"] == "heads" else "heads",
        "client_seed": data.client_seed,
        "result_hash": result_hash,
        "outcome": outcome,
        "winner_wallet": winner_wallet,
        "winner_name": winner_name,
        "loser_wallet": loser_wallet,
        "rake_sol": rake,
        "payout_sol": payout,
        "matched_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.p2p_challenges.update_one({"id": data.challenge_id}, {"$set": update_data})
    
    # Log rake for distribution wallet
    logger.info(f"P2P Flip Rake: {rake} SOL to {DISTRIBUTION_WALLET}")
    
    # Record in bets collection
    bet_record = {
        "id": str(uuid.uuid4()),
        "type": "p2p_coin_flip",
        "challenge_id": data.challenge_id,
        "creator_wallet": challenge["creator_wallet"],
        "opponent_wallet": data.wallet_address,
        "bet_amount_sol": challenge["bet_amount_sol"],
        "total_pot_sol": total_pot,
        "rake_sol": rake,
        "payout_sol": payout,
        "outcome": outcome,
        "winner_wallet": winner_wallet,
        "server_seed": server_seed,
        "server_seed_hash": challenge["server_seed_hash"],
        "client_seed": data.client_seed,
        "result_hash": result_hash,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.bets.insert_one(bet_record)
    
    return {
        "challenge_id": data.challenge_id,
        "outcome": outcome,
        "winner_wallet": winner_wallet,
        "winner_name": winner_name,
        "payout_sol": payout,
        "rake_sol": rake,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "server_seed": server_seed,
        "client_seed": data.client_seed,
        "result_hash": result_hash,
        "verification": f"SHA256({server_seed} + {data.client_seed}) = {result_hash}"
    }


@api_router.post("/betting/challenge/cancel/{challenge_id}")
async def cancel_challenge(challenge_id: str, wallet_address: str):
    """Cancel an open challenge (only creator can cancel)"""
    challenge = await db.p2p_challenges.find_one({"id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge["status"] != "open":
        raise HTTPException(status_code=400, detail="Can only cancel open challenges")
    if challenge["creator_wallet"] != wallet_address:
        raise HTTPException(status_code=403, detail="Only creator can cancel")
    
    await db.p2p_challenges.update_one(
        {"id": challenge_id},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Challenge cancelled", "challenge_id": challenge_id}


@api_router.get("/betting/history")
async def get_bet_history(limit: int = 20, wallet_address: Optional[str] = None):
    """Get betting history, optionally filtered by wallet"""
    query = {}
    if wallet_address:
        query["$or"] = [
            {"creator_wallet": wallet_address},
            {"opponent_wallet": wallet_address},
            {"wallet_address": wallet_address}
        ]
    history = await db.bets.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"history": history}


# ========== P2P POT SYSTEM ==========
# Active pot stored in memory (resets on server restart)
active_pot = {
    "id": str(uuid.uuid4()),
    "total_amount_sol": 0,
    "entries": [],
    "status": "open",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "draw_at": None,  # Will be set when 2 participants join
    "countdown_started": False,
    "countdown_seconds": 60,
    "rake_percent": RAKE_PERCENT,
    "winner": None
}


async def _get_pot_data():
    """Get pot data for broadcasts"""
    entries_display = []
    for e in active_pot["entries"]:
        prob = round(e["amount_sol"] / active_pot["total_amount_sol"] * 100, 1) if active_pot["total_amount_sol"] > 0 else 0
        entries_display.append({
            "display_name": e["display_name"],
            "wallet_address": e["wallet_address"][:8] + "..." if e.get("wallet_address") else "???",
            "amount_sol": e["amount_sol"],
            "probability": prob
        })
    
    # Calculate remaining seconds if countdown started
    remaining_seconds = None
    if active_pot["countdown_started"] and active_pot["draw_at"]:
        draw_time = datetime.fromisoformat(active_pot["draw_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        remaining = (draw_time - now).total_seconds()
        remaining_seconds = max(0, int(remaining))
    
    return {
        "id": active_pot["id"],
        "total_amount_sol": active_pot["total_amount_sol"],
        "entry_count": len(active_pot["entries"]),
        "entries": entries_display,
        "status": active_pot["status"],
        "draw_at": active_pot["draw_at"],
        "countdown_started": active_pot["countdown_started"],
        "countdown_seconds": active_pot["countdown_seconds"],
        "remaining_seconds": remaining_seconds,
        "rake_percent": active_pot["rake_percent"],
        "distribution_wallet": DISTRIBUTION_WALLET,
        "winner": active_pot["winner"]
    }


@api_router.get("/betting/pot")
async def get_pot_status():
    """Get current P2P pot status"""
    return await _get_pot_data()


@api_router.post("/betting/pot/join")
@limiter.limit("10/minute")
async def join_pot(request: Request, data: P2PPotJoinRequest):
    """Join the P2P pot with SOL"""
    global active_pot
    if active_pot["status"] != "open":
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
    active_pot["entries"].append(entry)
    active_pot["total_amount_sol"] += data.bet_amount_sol
    
    # Start 60-second countdown when 2nd participant joins
    countdown_just_started = False
    if len(active_pot["entries"]) == 2 and not active_pot["countdown_started"]:
        active_pot["countdown_started"] = True
        active_pot["draw_at"] = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        countdown_just_started = True
        logger.info(f"Pot countdown started! Draw at: {active_pot['draw_at']}")
    
    resp = {
        "message": f"Joined pot with {data.bet_amount_sol} SOL!",
        "probability": round(data.bet_amount_sol / active_pot["total_amount_sol"] * 100, 1),
        "total_pot_sol": active_pot["total_amount_sol"],
        "entry_count": len(active_pot["entries"]),
        "countdown_started": active_pot["countdown_started"],
        "countdown_just_started": countdown_just_started,
        "draw_at": active_pot["draw_at"]
    }
    await pot_ws_manager.broadcast({"type": "pot_update", "data": await _get_pot_data()})
    return resp


@api_router.post("/betting/pot/draw")
async def draw_pot_winner():
    """Draw pot winner - winner takes all minus rake"""
    global active_pot
    if len(active_pot["entries"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries")
    
    total = active_pot["total_amount_sol"]
    rand_value = secrets.randbelow(int(total * 1000000)) / 1000000
    cumulative = 0
    winner = None
    
    for entry in active_pot["entries"]:
        cumulative += entry["amount_sol"]
        if rand_value <= cumulative:
            winner = entry
            break
    if not winner:
        winner = active_pot["entries"][-1]
    
    rake = round(total * active_pot["rake_percent"] / 100, 6)
    payout = round(total - rake, 6)
    
    logger.info(f"Pot Rake: {rake} SOL to {DISTRIBUTION_WALLET}")
    
    result = {
        "winner_name": winner["display_name"],
        "winner_wallet": winner["wallet_address"],
        "payout_sol": payout,
        "total_pot_sol": total,
        "rake_sol": rake,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(active_pot["entries"])
    }
    
    active_pot["winner"] = result
    active_pot["status"] = "completed"
    
    # Save to DB
    await db.pot_results.insert_one({
        **result,
        "pot_id": active_pot["id"],
        "entries": active_pot["entries"],
        "drawn_at": datetime.now(timezone.utc).isoformat()
    })
    
    await pot_ws_manager.broadcast({"type": "pot_winner", "data": result})
    
    # Reset pot
    active_pot = {
        "id": str(uuid.uuid4()),
        "total_amount_sol": 0,
        "entries": [],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "draw_at": None,
        "countdown_started": False,
        "countdown_seconds": 60,
        "rake_percent": RAKE_PERCENT,
        "winner": None
    }
    
    await pot_ws_manager.broadcast({"type": "pot_update", "data": await _get_pot_data()})
    return result


# _get_pot_data defined earlier in this file (line ~781)


@api_router.get("/governance/proposals")
async def get_proposals():
    enriched = []
    for p in PROPOSALS:
        yes_count = await db.votes.count_documents({"proposal_id": p["id"], "vote": "yes"})
        no_count = await db.votes.count_documents({"proposal_id": p["id"], "vote": "no"})
        enriched.append({**p, "yes_votes": yes_count, "no_votes": no_count})
    return {"proposals": enriched}


@api_router.post("/governance/vote")
async def cast_vote(data: VoteRequest):
    existing = await db.votes.find_one({"proposal_id": data.proposal_id, "wallet_address": data.wallet_address}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Already voted")
    doc = {"id": str(uuid.uuid4()), "proposal_id": data.proposal_id, "vote": data.vote,
           "wallet_address": data.wallet_address, "voted_at": datetime.now(timezone.utc).isoformat()}
    await db.votes.insert_one(doc)
    return {"message": "Vote cast!", "vote": data.vote}


@api_router.post("/staking/simulate")
async def simulate_staking(data: StakingSimRequest):
    daily_rate = data.apy / 100 / 365
    balance = data.amount
    total_rewards = 0
    chart_data = []
    for day in range(1, data.duration_days + 1):
        reward = balance * daily_rate
        total_rewards += reward
        balance += reward
        if day % max(1, data.duration_days // 30) == 0 or day == data.duration_days:
            chart_data.append({"day": day, "balance": round(balance, 2), "rewards": round(total_rewards, 2)})
    return {"initial": data.amount, "final_balance": round(balance, 2), "total_rewards": round(total_rewards, 2),
            "apy": data.apy, "duration_days": data.duration_days,
            "guardian_points": int(data.amount * data.duration_days / 100), "chart_data": chart_data}


@api_router.post("/exit-simulator")
async def simulate_exit(data: ExitSimRequest):
    results = []
    for exit_price in data.exit_prices:
        investment = data.token_amount * data.entry_price
        value = data.token_amount * exit_price
        pnl = value - investment
        pnl_pct = ((exit_price - data.entry_price) / data.entry_price) * 100 if data.entry_price > 0 else 0
        tax = max(0, pnl * data.tax_rate / 100)
        net_pnl = pnl - tax
        results.append({"exit_price": exit_price, "value": round(value, 2), "pnl": round(pnl, 2),
                         "pnl_percent": round(pnl_pct, 2), "tax": round(tax, 2), "net_pnl": round(net_pnl, 2)})
    best = max(results, key=lambda r: r["net_pnl"])
    return {"investment": round(data.token_amount * data.entry_price, 2), "results": results,
            "optimal_exit": best, "token_amount": data.token_amount, "entry_price": data.entry_price}


@api_router.post("/exit-simulator/monte-carlo")
async def monte_carlo_simulation(data: MonteCarloRequest):
    """Monte Carlo simulation using Geometric Brownian Motion"""
    S0 = data.entry_price
    mu = data.drift
    sigma = data.volatility
    T = data.days / 365.0
    N = data.days
    M = min(data.simulations, 5000)
    dt = T / N

    np.random.seed(None)
    Z = np.random.standard_normal((M, N))
    S = np.zeros((M, N + 1))
    S[:, 0] = S0

    for t in range(1, N + 1):
        S[:, t] = S[:, t - 1] * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * Z[:, t - 1])

    final_prices = S[:, -1]
    investment = data.token_amount * S0
    final_values = data.token_amount * final_prices
    pnl = final_values - investment
    taxes = np.maximum(0, pnl * data.tax_rate / 100)
    net_pnl = pnl - taxes

    percentiles = [5, 10, 25, 50, 75, 90, 95]
    price_pcts = {f"p{p}": float(round(np.percentile(final_prices, p), 6)) for p in percentiles}
    pnl_pcts = {f"p{p}": float(round(np.percentile(net_pnl, p), 2)) for p in percentiles}

    # Sample paths for chart (10 paths + percentile bands)
    sample_idx = np.random.choice(M, min(10, M), replace=False)
    sample_days = list(range(0, N + 1, max(1, N // 60)))
    if N not in sample_days:
        sample_days.append(N)

    sample_paths = []
    for idx in sample_idx:
        sample_paths.append([float(round(S[idx, d], 6)) for d in sample_days])

    band_p5 = [float(round(np.percentile(S[:, d], 5), 6)) for d in sample_days]
    band_p25 = [float(round(np.percentile(S[:, d], 25), 6)) for d in sample_days]
    band_p50 = [float(round(np.percentile(S[:, d], 50), 6)) for d in sample_days]
    band_p75 = [float(round(np.percentile(S[:, d], 75), 6)) for d in sample_days]
    band_p95 = [float(round(np.percentile(S[:, d], 95), 6)) for d in sample_days]

    # Distribution histogram
    hist_counts, hist_edges = np.histogram(final_prices, bins=30)
    histogram = [{"min": float(round(hist_edges[i], 6)), "max": float(round(hist_edges[i + 1], 6)),
                  "count": int(hist_counts[i])} for i in range(len(hist_counts))]

    prob_profit = float(round(np.mean(net_pnl > 0) * 100, 1))
    prob_2x = float(round(np.mean(final_prices >= S0 * 2) * 100, 1))
    prob_5x = float(round(np.mean(final_prices >= S0 * 5) * 100, 1))
    prob_10x = float(round(np.mean(final_prices >= S0 * 10) * 100, 1))
    prob_loss50 = float(round(np.mean(final_prices <= S0 * 0.5) * 100, 1))

    return {
        "investment": round(investment, 2),
        "token_amount": data.token_amount,
        "entry_price": data.entry_price,
        "simulations": M,
        "days": data.days,
        "volatility": data.volatility,
        "drift": data.drift,
        "price_percentiles": price_pcts,
        "pnl_percentiles": pnl_pcts,
        "mean_final_price": float(round(np.mean(final_prices), 6)),
        "mean_pnl": float(round(np.mean(net_pnl), 2)),
        "median_pnl": float(round(np.median(net_pnl), 2)),
        "max_pnl": float(round(np.max(net_pnl), 2)),
        "min_pnl": float(round(np.min(net_pnl), 2)),
        "prob_profit": prob_profit,
        "prob_2x": prob_2x,
        "prob_5x": prob_5x,
        "prob_10x": prob_10x,
        "prob_loss50": prob_loss50,
        "chart": {
            "days": sample_days,
            "sample_paths": sample_paths,
            "bands": {"p5": band_p5, "p25": band_p25, "p50": band_p50, "p75": band_p75, "p95": band_p95},
        },
        "histogram": histogram,
        "tax_rate": data.tax_rate,
    }


# ========== Leaderboard Models ==========
class LeaderboardEntry(BaseModel):
    player_name: str
    score: int
    mooncakes: int = 0
    wallet_address: Optional[str] = None

class ReflectionsCalcRequest(BaseModel):
    token_holdings: float
    volume_24h: float = 89000
    reflection_rate: float = 2.0

# ========== Trading Journal Models ==========
class TradeEntry(BaseModel):
    trade_id: Optional[str] = None
    date_entry: str
    date_exit: Optional[str] = None
    asset: str
    trade_type: str
    leverage: Optional[float] = 1.0
    entry_price: float
    position_size: float
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    fees: float = 0
    slippage: float = 0
    chart_link: Optional[str] = None
    entry_reason: Optional[str] = None
    strategy: Optional[str] = None
    market_conditions: Optional[str] = None
    expected_rr: Optional[float] = None
    emotion_entry: Optional[str] = None
    emotion_exit: Optional[str] = None
    confidence_level: Optional[int] = None
    mindset_notes: Optional[str] = None
    what_went_well: Optional[str] = None
    what_went_wrong: Optional[str] = None
    lessons: Optional[str] = None
    trade_grade: Optional[str] = None
    tags: Optional[List[str]] = []
    external_influences: Optional[str] = None
    health_notes: Optional[str] = None
    status: str = "open"



# ========== Reflections Calculator Route ==========
@api_router.post("/reflections/calculate")
async def calculate_reflections(data: ReflectionsCalcRequest):
    # Tokenomics constants
    total_supply = 1_000_000_000
    circulating_supply = 800_000_000
    
    # Calculate holder's share of circulating supply
    holder_share = data.token_holdings / circulating_supply
    
    # Reflections are 2% of all transactions, distributed to holders
    daily_volume = data.volume_24h
    daily_reflections_pool = daily_volume * (data.reflection_rate / 100)
    
    # Holder's daily reflections based on their share
    daily_reflections_usd = daily_reflections_pool * holder_share
    weekly_reflections_usd = daily_reflections_usd * 7
    monthly_reflections_usd = daily_reflections_usd * 30
    yearly_reflections_usd = daily_reflections_usd * 365
    
    # Calculate in tokens (assuming current price)
    price_usd = 0.00042
    daily_reflections_tokens = daily_reflections_usd / price_usd if price_usd > 0 else 0
    weekly_reflections_tokens = weekly_reflections_usd / price_usd if price_usd > 0 else 0
    monthly_reflections_tokens = monthly_reflections_usd / price_usd if price_usd > 0 else 0
    yearly_reflections_tokens = yearly_reflections_usd / price_usd if price_usd > 0 else 0
    
    # APY calculation
    initial_value = data.token_holdings * price_usd
    apy = (yearly_reflections_usd / initial_value * 100) if initial_value > 0 else 0
    
    return {
        "holdings": data.token_holdings,
        "holder_share_percent": round(holder_share * 100, 6),
        "volume_24h": data.volume_24h,
        "reflection_rate": data.reflection_rate,
        "daily": {"usd": round(daily_reflections_usd, 4), "tokens": round(daily_reflections_tokens, 2)},
        "weekly": {"usd": round(weekly_reflections_usd, 4), "tokens": round(weekly_reflections_tokens, 2)},
        "monthly": {"usd": round(monthly_reflections_usd, 4), "tokens": round(monthly_reflections_tokens, 2)},
        "yearly": {"usd": round(yearly_reflections_usd, 2), "tokens": round(yearly_reflections_tokens, 2)},
        "estimated_apy": round(apy, 2),
        "price_usd": price_usd
    }


# ========== Trading Journal Routes ==========
@api_router.get("/journal/trades")
async def get_trades(limit: int = 100, status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    trades = await db.trading_journal.find(query, {"_id": 0}).sort("date_entry", -1).to_list(limit)
    return {"trades": trades, "count": len(trades)}


@api_router.get("/journal/trade/{trade_id}")
async def get_trade(trade_id: str):
    trade = await db.trading_journal.find_one({"trade_id": trade_id}, {"_id": 0})
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@api_router.post("/journal/trade")
async def create_trade(data: TradeEntry):
    trade_id = data.trade_id or f"T{str(uuid.uuid4())[:8].upper()}"
    
    # Calculate P&L if exit price provided
    pnl = 0
    pnl_percent = 0
    if data.exit_price and data.entry_price:
        if data.trade_type.lower() in ["long", "spot"]:
            pnl = (data.exit_price - data.entry_price) * data.position_size
        else:  # short
            pnl = (data.entry_price - data.exit_price) * data.position_size
        pnl -= data.fees + data.slippage
        pnl_percent = ((data.exit_price - data.entry_price) / data.entry_price * 100) if data.entry_price > 0 else 0
        if data.trade_type.lower() == "short":
            pnl_percent = -pnl_percent
    
    trade = {
        "trade_id": trade_id,
        "date_entry": data.date_entry,
        "date_exit": data.date_exit,
        "asset": data.asset.upper(),
        "trade_type": data.trade_type,
        "leverage": data.leverage,
        "entry_price": data.entry_price,
        "position_size": data.position_size,
        "exit_price": data.exit_price,
        "exit_reason": data.exit_reason,
        "stop_loss": data.stop_loss,
        "take_profit": data.take_profit,
        "fees": data.fees,
        "slippage": data.slippage,
        "chart_link": data.chart_link,
        "entry_reason": data.entry_reason,
        "strategy": data.strategy,
        "market_conditions": data.market_conditions,
        "expected_rr": data.expected_rr,
        "emotion_entry": data.emotion_entry,
        "emotion_exit": data.emotion_exit,
        "confidence_level": data.confidence_level,
        "mindset_notes": data.mindset_notes,
        "what_went_well": data.what_went_well,
        "what_went_wrong": data.what_went_wrong,
        "lessons": data.lessons,
        "trade_grade": data.trade_grade,
        "tags": data.tags or [],
        "external_influences": data.external_influences,
        "health_notes": data.health_notes,
        "status": data.status,
        "pnl": round(pnl, 2),
        "pnl_percent": round(pnl_percent, 2),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trading_journal.insert_one(trade)
    return {"message": "Trade logged!", "trade_id": trade_id, "pnl": trade["pnl"]}


@api_router.put("/journal/trade/{trade_id}")
async def update_trade(trade_id: str, data: TradeEntry):
    existing = await db.trading_journal.find_one({"trade_id": trade_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    # Recalculate P&L
    pnl = 0
    pnl_percent = 0
    if data.exit_price and data.entry_price:
        if data.trade_type.lower() in ["long", "spot"]:
            pnl = (data.exit_price - data.entry_price) * data.position_size
        else:
            pnl = (data.entry_price - data.exit_price) * data.position_size
        pnl -= data.fees + data.slippage
        pnl_percent = ((data.exit_price - data.entry_price) / data.entry_price * 100) if data.entry_price > 0 else 0
        if data.trade_type.lower() == "short":
            pnl_percent = -pnl_percent
    
    update_data = {
        "date_entry": data.date_entry,
        "date_exit": data.date_exit,
        "asset": data.asset.upper(),
        "trade_type": data.trade_type,
        "leverage": data.leverage,
        "entry_price": data.entry_price,
        "position_size": data.position_size,
        "exit_price": data.exit_price,
        "exit_reason": data.exit_reason,
        "stop_loss": data.stop_loss,
        "take_profit": data.take_profit,
        "fees": data.fees,
        "slippage": data.slippage,
        "chart_link": data.chart_link,
        "entry_reason": data.entry_reason,
        "strategy": data.strategy,
        "market_conditions": data.market_conditions,
        "expected_rr": data.expected_rr,
        "emotion_entry": data.emotion_entry,
        "emotion_exit": data.emotion_exit,
        "confidence_level": data.confidence_level,
        "mindset_notes": data.mindset_notes,
        "what_went_well": data.what_went_well,
        "what_went_wrong": data.what_went_wrong,
        "lessons": data.lessons,
        "trade_grade": data.trade_grade,
        "tags": data.tags or [],
        "external_influences": data.external_influences,
        "health_notes": data.health_notes,
        "status": data.status,
        "pnl": round(pnl, 2),
        "pnl_percent": round(pnl_percent, 2),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trading_journal.update_one({"trade_id": trade_id}, {"$set": update_data})
    return {"message": "Trade updated!", "trade_id": trade_id, "pnl": pnl}


@api_router.delete("/journal/trade/{trade_id}")
async def delete_trade(trade_id: str):
    result = await db.trading_journal.delete_one({"trade_id": trade_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"message": "Trade deleted!", "trade_id": trade_id}


@api_router.get("/journal/dashboard")
async def get_journal_dashboard():
    trades = await db.trading_journal.find({}, {"_id": 0}).to_list(1000)
    
    if not trades:
        return {
            "total_trades": 0,
            "open_trades": 0,
            "closed_trades": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "avg_pnl": 0,
            "biggest_win": None,
            "biggest_loss": None,
            "most_traded_asset": None,
            "avg_confidence": 0,
            "recent_emotions": [],
            "pnl_by_asset": {},
            "win_streak": 0,
            "loss_streak": 0,
            "avg_rr": 0,
            "sharpe_ratio": 0
        }
    
    closed_trades = [t for t in trades if t.get("status") == "closed" and t.get("pnl") is not None]
    open_trades = [t for t in trades if t.get("status") == "open"]
    
    total_pnl = sum(t.get("pnl", 0) for t in closed_trades)
    wins = [t for t in closed_trades if t.get("pnl", 0) > 0]
    losses = [t for t in closed_trades if t.get("pnl", 0) < 0]
    
    win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0
    avg_pnl = total_pnl / len(closed_trades) if closed_trades else 0
    
    biggest_win = max(closed_trades, key=lambda t: t.get("pnl", 0)) if wins else None
    biggest_loss = min(closed_trades, key=lambda t: t.get("pnl", 0)) if losses else None
    
    # Most traded asset
    asset_counts = {}
    for t in trades:
        asset = t.get("asset", "Unknown")
        asset_counts[asset] = asset_counts.get(asset, 0) + 1
    most_traded = max(asset_counts.items(), key=lambda x: x[1]) if asset_counts else (None, 0)
    
    # P&L by asset
    pnl_by_asset = {}
    for t in closed_trades:
        asset = t.get("asset", "Unknown")
        pnl_by_asset[asset] = pnl_by_asset.get(asset, 0) + t.get("pnl", 0)
    
    # Average confidence
    confidence_vals = [t.get("confidence_level") for t in trades if t.get("confidence_level")]
    avg_confidence = sum(confidence_vals) / len(confidence_vals) if confidence_vals else 0
    
    # Recent emotions
    recent_emotions = [{"entry": t.get("emotion_entry"), "exit": t.get("emotion_exit"), "asset": t.get("asset")} 
                       for t in sorted(trades, key=lambda x: x.get("date_entry", ""), reverse=True)[:5]]
    
    # Win/Loss streaks
    sorted_closed = sorted(closed_trades, key=lambda x: x.get("date_entry", ""))
    win_streak = loss_streak = current_win = current_loss = 0
    for t in sorted_closed:
        if t.get("pnl", 0) > 0:
            current_win += 1
            current_loss = 0
            win_streak = max(win_streak, current_win)
        elif t.get("pnl", 0) < 0:
            current_loss += 1
            current_win = 0
            loss_streak = max(loss_streak, current_loss)
    
    # Average R:R
    rr_vals = [t.get("expected_rr") for t in trades if t.get("expected_rr")]
    avg_rr = sum(rr_vals) / len(rr_vals) if rr_vals else 0
    
    # Simple Sharpe-like ratio (avg return / std dev)
    pnl_vals = [t.get("pnl", 0) for t in closed_trades]
    if len(pnl_vals) > 1:
        import statistics
        std_dev = statistics.stdev(pnl_vals)
        sharpe = (avg_pnl / std_dev) if std_dev > 0 else 0
    else:
        sharpe = 0
    
    return {
        "total_trades": len(trades),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 1),
        "avg_pnl": round(avg_pnl, 2),
        "biggest_win": {"trade_id": biggest_win.get("trade_id"), "asset": biggest_win.get("asset"), "pnl": biggest_win.get("pnl")} if biggest_win else None,
        "biggest_loss": {"trade_id": biggest_loss.get("trade_id"), "asset": biggest_loss.get("asset"), "pnl": biggest_loss.get("pnl")} if biggest_loss else None,
        "most_traded_asset": {"asset": most_traded[0], "count": most_traded[1]} if most_traded[0] else None,
        "avg_confidence": round(avg_confidence, 1),
        "recent_emotions": recent_emotions,
        "pnl_by_asset": {k: round(v, 2) for k, v in pnl_by_asset.items()},
        "win_streak": win_streak,
        "loss_streak": loss_streak,
        "avg_rr": round(avg_rr, 2),
        "sharpe_ratio": round(sharpe, 3),
        "total_wins": len(wins),
        "total_losses": len(losses)
    }


@api_router.get("/tokenomics/stats")
async def get_tokenomics():
    total_bets = await db.bets.count_documents({})
    total_subs = await db.newsletter_subscribers.count_documents({})
    return {"total_supply": 1000000000, "circulating_supply": 800000000, "burned": 12500000,
            "burn_rate": "2%", "reflection_rate": "2%", "liquidity_rate": "1%",
            "distribution": {"community_liquidity": 80, "marketing_partnerships": 10, "developer_team": 5, "ecosystem_reserve": 5},
            "holders": 1247 + total_subs, "total_bets": total_bets,
            "price_usd": 0.00042, "market_cap": 420000, "volume_24h": 89000}


@api_router.get("/wallet/balance/{address}")
async def get_wallet_balance(address: str):
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                "https://api.mainnet-beta.solana.com",
                json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]},
                timeout=10.0
            )
            data = resp.json()
            if "result" in data:
                lamports = data["result"]["value"]
                return {"address": address, "balance_lamports": lamports, "balance_sol": lamports / 1e9}
    except Exception as e:
        logger.error(f"Balance error: {e}")
    return {"address": address, "balance_lamports": 0, "balance_sol": 0}


# ========== TRADING JOURNAL EXPORT ==========
@api_router.get("/journal/export/csv")
async def export_trades_csv():
    """Export all trades to CSV"""
    trades = await db.trading_journal.find({}, {"_id": 0}).sort("date_entry", -1).to_list(10000)
    
    if not trades:
        raise HTTPException(status_code=404, detail="No trades to export")
    
    output = io.StringIO()
    fieldnames = [
        "trade_id", "date_entry", "date_exit", "asset", "trade_type", "leverage",
        "entry_price", "position_size", "exit_price", "exit_reason", "stop_loss",
        "take_profit", "fees", "slippage", "pnl", "pnl_percent", "strategy",
        "entry_reason", "market_conditions", "expected_rr", "emotion_entry",
        "emotion_exit", "confidence_level", "trade_grade", "what_went_well",
        "what_went_wrong", "lessons", "tags", "status"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for trade in trades:
        trade["tags"] = ",".join(trade.get("tags", []))
        writer.writerow(trade)
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bullpug_trading_journal.csv"}
    )


@api_router.get("/journal/export/json")
async def export_trades_json():
    """Export all trades to JSON"""
    trades = await db.trading_journal.find({}, {"_id": 0}).sort("date_entry", -1).to_list(10000)
    dashboard = await get_journal_dashboard()
    
    export_data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "summary": dashboard,
        "trades": trades
    }
    
    return StreamingResponse(
        io.BytesIO(jsonlib.dumps(export_data, indent=2).encode()),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=bullpug_trading_journal.json"}
    )


# ========== ESCROW SYSTEM ==========
@api_router.post("/escrow/deposit")
async def escrow_deposit(data: EscrowDepositRequest):
    """Record an escrow deposit (after user sends SOL to escrow wallet)"""
    # Verify the transaction on Solana blockchain
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                "https://api.mainnet-beta.solana.com",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [data.tx_signature, {"encoding": "jsonParsed"}]
                },
                timeout=15.0
            )
            tx_data = resp.json()
            
            # Basic validation - in production, verify amount and destination
            if "error" in tx_data or tx_data.get("result") is None:
                logger.warning(f"Transaction not found or error: {data.tx_signature}")
                # For development, allow deposits without full verification
    except Exception as e:
        logger.error(f"Failed to verify transaction: {e}")
    
    deposit = {
        "id": str(uuid.uuid4()),
        "wallet_address": data.wallet_address,
        "amount_sol": data.amount_sol,
        "tx_signature": data.tx_signature,
        "purpose": data.purpose,
        "reference_id": data.reference_id,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.escrow_deposits.insert_one(deposit)
    
    # Update the challenge or pot with the deposit
    if data.purpose == "challenge":
        await db.p2p_challenges.update_one(
            {"id": data.reference_id},
            {"$set": {"creator_deposit_confirmed": True, "creator_tx": data.tx_signature}}
        )
    
    return {"message": "Deposit recorded", "deposit_id": deposit["id"]}


@api_router.get("/escrow/balance/{wallet_address}")
async def get_escrow_balance(wallet_address: str):
    """Get user's escrow balance"""
    deposits = await db.escrow_deposits.find(
        {"wallet_address": wallet_address, "status": "confirmed"}
    ).to_list(1000)
    
    withdrawals = await db.escrow_withdrawals.find(
        {"wallet_address": wallet_address, "status": "completed"}
    ).to_list(1000)
    
    total_deposited = sum(d.get("amount_sol", 0) for d in deposits)
    total_withdrawn = sum(w.get("amount_sol", 0) for w in withdrawals)
    
    return {
        "wallet_address": wallet_address,
        "balance_sol": round(total_deposited - total_withdrawn, 6),
        "total_deposited": round(total_deposited, 6),
        "total_withdrawn": round(total_withdrawn, 6)
    }


@api_router.get("/escrow/wallet")
async def get_escrow_wallet():
    """Get the escrow wallet address for deposits"""
    return {
        "escrow_wallet": ESCROW_WALLET,
        "message": "Send SOL to this address for P2P betting"
    }


# ========== NOTIFICATIONS ==========
@api_router.get("/notifications/{wallet_address}")
async def get_notifications(wallet_address: str, limit: int = 50):
    """Get notifications for a user"""
    notifications = await db.notifications.find(
        {"to_wallet": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    unread = sum(1 for n in notifications if not n.get("read"))
    
    return {"notifications": notifications, "unread_count": unread}


@api_router.post("/notifications/read/{notification_id}")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read"""
    await db.notifications.update_one(
        {"id": notification_id},
        {"$set": {"read": True}}
    )
    return {"message": "Marked as read"}


@api_router.post("/notifications/read-all/{wallet_address}")
async def mark_all_notifications_read(wallet_address: str):
    """Mark all notifications as read"""
    await db.notifications.update_many(
        {"to_wallet": wallet_address, "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "All notifications marked as read"}


@api_router.post("/notifications/subscribe")
async def subscribe_push(data: PushSubscription):
    """Subscribe to push notifications"""
    subscription = {
        "wallet_address": data.wallet_address,
        "subscription": data.subscription,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert - update if exists, insert if not
    await db.push_subscriptions.update_one(
        {"wallet_address": data.wallet_address},
        {"$set": subscription},
        upsert=True
    )
    
    return {"message": "Subscribed to push notifications"}


# ========== ADMIN PANEL ==========
@api_router.get("/admin/check/{wallet_address}")
async def check_admin(wallet_address: str):
    """Check if wallet is admin"""
    return {"is_admin": is_admin(wallet_address)}


@api_router.get("/admin/dashboard")
async def admin_dashboard(admin_wallet: str):
    """Get admin dashboard data"""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
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
            "total_amount_sol": active_pot["total_amount_sol"],
            "entry_count": len(active_pot["entries"]),
            "status": active_pot["status"]
        },
        "distribution_wallet": DISTRIBUTION_WALLET
    }


@api_router.get("/admin/challenges")
async def admin_get_challenges(admin_wallet: str, status: Optional[str] = None, limit: int = 50):
    """Get all challenges (admin only)"""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {}
    if status:
        query["status"] = status
    
    challenges = await db.p2p_challenges.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"challenges": challenges}


@api_router.post("/admin/challenge/cancel")
async def admin_cancel_challenge(data: AdminManageChallengeRequest):
    """Cancel a challenge and refund (admin only)"""
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


@api_router.post("/admin/pot/draw")
async def admin_draw_pot(data: AdminDrawPotRequest):
    """Force draw the current pot (admin only)"""
    if not is_admin(data.admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    global active_pot
    if len(active_pot["entries"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries to draw")
    
    # Draw winner
    total = active_pot["total_amount_sol"]
    rand_value = secrets.randbelow(int(total * 1000000)) / 1000000
    cumulative = 0
    winner = None
    
    for entry in active_pot["entries"]:
        cumulative += entry["amount_sol"]
        if rand_value <= cumulative:
            winner = entry
            break
    if not winner:
        winner = active_pot["entries"][-1]
    
    rake = round(total * active_pot["rake_percent"] / 100, 6)
    payout = round(total - rake, 6)
    
    result = {
        "winner_name": winner["display_name"],
        "winner_wallet": winner["wallet_address"],
        "payout_sol": payout,
        "total_pot_sol": total,
        "rake_sol": rake,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "entry_count": len(active_pot["entries"]),
        "drawn_by": data.admin_wallet
    }
    
    active_pot["winner"] = result
    active_pot["status"] = "completed"
    
    # Save to DB
    await db.pot_results.insert_one({
        **result,
        "pot_id": active_pot["id"],
        "entries": active_pot["entries"],
        "drawn_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Notify winner
    await send_notification(
        winner["wallet_address"],
        "You Won the Pot!",
        f"Congratulations! You won {payout} SOL in the pot!",
        "pot"
    )
    
    # Notify all participants
    for entry in active_pot["entries"]:
        if entry["wallet_address"] != winner["wallet_address"]:
            await send_notification(
                entry["wallet_address"],
                "Pot Drawn",
                f"{winner['display_name']} won the pot of {total} SOL",
                "pot"
            )
    
    await pot_ws_manager.broadcast({"type": "pot_winner", "data": result})
    
    # Reset pot
    active_pot = {
        "id": str(uuid.uuid4()),
        "total_amount_sol": 0,
        "entries": [],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "draw_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "rake_percent": RAKE_PERCENT,
        "winner": None
    }
    
    await pot_ws_manager.broadcast({"type": "pot_update", "data": await _get_pot_data()})
    
    return result


@api_router.get("/admin/bets")
async def admin_get_bets(admin_wallet: str, limit: int = 100):
    """Get all bets (admin only)"""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    bets = await db.bets.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"bets": bets}


@api_router.get("/admin/escrow")
async def admin_get_escrow(admin_wallet: str):
    """Get escrow statistics (admin only)"""
    if not is_admin(admin_wallet):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    deposits = await db.escrow_deposits.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    withdrawals = await db.escrow_withdrawals.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    total_deposited = sum(d.get("amount_sol", 0) for d in deposits)
    total_withdrawn = sum(w.get("amount_sol", 0) for w in withdrawals)
    
    return {
        "total_deposited_sol": round(total_deposited, 6),
        "total_withdrawn_sol": round(total_withdrawn, 6),
        "escrow_balance_sol": round(total_deposited - total_withdrawn, 6),
        "recent_deposits": deposits[:20],
        "recent_withdrawals": withdrawals[:20]
    }


# ========== TRADING JOURNAL CLOUD BACKUP ==========
@api_router.post("/journal/backup")
async def create_journal_backup(data: JournalBackupRequest):
    """Create a cloud backup of user's trading journal"""
    if not data.wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address required")
    
    # Get all trades for this wallet
    trades = await db.trading_journal.find(
        {"wallet_address": data.wallet_address},
        {"_id": 0}
    ).to_list(10000)
    
    # Create backup
    backup = {
        "id": str(uuid.uuid4()),
        "wallet_address": data.wallet_address,
        "trades": trades,
        "trade_count": len(trades),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Store backup
    await db.journal_backups.insert_one(backup)
    
    return {
        "message": "Backup created!",
        "backup_id": backup["id"],
        "trade_count": len(trades),
        "created_at": backup["created_at"]
    }


@api_router.get("/journal/backups/{wallet_address}")
async def get_journal_backups(wallet_address: str):
    """Get list of backups for a wallet"""
    backups = await db.journal_backups.find(
        {"wallet_address": wallet_address},
        {"_id": 0, "trades": 0}  # Don't include full trade data in list
    ).sort("created_at", -1).to_list(50)
    
    return {"backups": backups}


@api_router.get("/journal/backup/{backup_id}")
async def get_journal_backup(backup_id: str, wallet_address: str):
    """Get a specific backup"""
    backup = await db.journal_backups.find_one(
        {"id": backup_id, "wallet_address": wallet_address},
        {"_id": 0}
    )
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return backup


@api_router.post("/journal/restore/{backup_id}")
async def restore_journal_backup(backup_id: str, wallet_address: str):
    """Restore trades from a backup"""
    backup = await db.journal_backups.find_one(
        {"id": backup_id, "wallet_address": wallet_address}
    )
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    # Option: Clear existing trades or merge
    # For now, we'll merge (skip duplicates based on trade_id)
    trades = backup.get("trades", [])
    restored_count = 0
    
    for trade in trades:
        existing = await db.trading_journal.find_one({"trade_id": trade.get("trade_id")})
        if not existing:
            trade["wallet_address"] = wallet_address
            trade["restored_from_backup"] = backup_id
            trade["restored_at"] = datetime.now(timezone.utc).isoformat()
            await db.trading_journal.insert_one(trade)
            restored_count += 1
    
    return {
        "message": f"Restored {restored_count} trades",
        "restored_count": restored_count,
        "total_in_backup": len(trades)
    }


@api_router.delete("/journal/backup/{backup_id}")
async def delete_journal_backup(backup_id: str, wallet_address: str):
    """Delete a backup"""
    result = await db.journal_backups.delete_one({
        "id": backup_id,
        "wallet_address": wallet_address
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return {"message": "Backup deleted"}


# ========== EMAIL ENDPOINTS ==========
class EmailSubscribeRequest(BaseModel):
    email: str
    wallet_address: str
    subscribe_weekly: bool = True

class SendWelcomeEmailRequest(BaseModel):
    email: str
    wallet_address: str

@api_router.post("/email/subscribe")
async def subscribe_to_emails(data: EmailSubscribeRequest):
    """Subscribe to email notifications"""
    subscription = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "wallet_address": data.wallet_address,
        "subscribe_weekly": data.subscribe_weekly,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True
    }
    
    existing = await db.email_subscriptions.find_one({
        "wallet_address": data.wallet_address
    })
    
    if existing:
        await db.email_subscriptions.update_one(
            {"wallet_address": data.wallet_address},
            {"$set": {
                "email": data.email,
                "subscribe_weekly": data.subscribe_weekly,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return {"message": "Email preferences updated", "status": "updated"}
    
    await db.email_subscriptions.insert_one(subscription)
    await send_welcome_email(data.email, data.wallet_address)
    
    return {"message": "Subscribed successfully!", "status": "subscribed"}


@api_router.post("/email/welcome")
async def send_welcome(data: SendWelcomeEmailRequest):
    """Send welcome email to a user"""
    success = await send_welcome_email(data.email, data.wallet_address)
    if success:
        return {"message": "Welcome email sent", "status": "sent"}
    return {"message": "Email service not configured", "status": "not_configured"}


@api_router.get("/email/subscription/{wallet_address}")
async def get_email_subscription(wallet_address: str):
    """Get email subscription status for a wallet"""
    subscription = await db.email_subscriptions.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    if subscription:
        return subscription
    return {"subscribed": False}


@api_router.delete("/email/unsubscribe/{wallet_address}")
async def unsubscribe_from_emails(wallet_address: str):
    """Unsubscribe from email notifications"""
    result = await db.email_subscriptions.update_one(
        {"wallet_address": wallet_address},
        {"$set": {"active": False, "unsubscribed_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count > 0:
        return {"message": "Unsubscribed successfully"}
    return {"message": "No subscription found"}


@api_router.post("/email/test")
async def test_email_config():
    """Test if email is configured"""
    if sendgrid_api_key:
        return {"configured": True, "sender": sender_email}
    return {"configured": False, "message": "SENDGRID_API_KEY not set"}


# Include modular routers BEFORE registering api_router with app
api_router.include_router(betting_router)
api_router.include_router(auth_router)
api_router.include_router(email_router)
api_router.include_router(leaderboard_router)
api_router.include_router(skins_router)
api_router.include_router(forum_router)
api_router.include_router(messages_router)
api_router.include_router(journal_router)
api_router.include_router(showcase_router)

# Now register the complete api_router with the app
app.include_router(api_router)


# WebSocket for pot real-time updates
@app.websocket("/ws/pot")
async def pot_websocket(ws: WebSocket):
    await pot_ws_manager.connect(ws)
    try:
        await ws.send_json({"type": "pot_update", "data": await _get_pot_data()})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pot_ws_manager.disconnect(ws)
    except Exception:
        pot_ws_manager.disconnect(ws)


# WebSocket for direct messages
@app.websocket("/ws/dm/{wallet_address}")
async def dm_websocket(ws: WebSocket, wallet_address: str):
    await dm_manager.connect(ws, wallet_address)
    try:
        while True:
            data = await ws.receive_json()
            # Handle incoming messages via WebSocket
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


# WebSocket for notifications
@app.websocket("/ws/notifications/{wallet_address}")
async def notification_websocket(ws: WebSocket, wallet_address: str):
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
            await ws.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        notification_manager.disconnect(wallet_address)
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")
        notification_manager.disconnect(wallet_address)


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    mongo_client.close()
