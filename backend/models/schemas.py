"""Pydantic models for the Bullpug application."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


# ========== Betting Models ==========
class CreateChallengeRequest(BaseModel):
    bet_amount_sol: float
    choice: str  # heads or tails
    wallet_address: str
    display_name: str = "Anonymous Guardian"
    signature: Optional[str] = None
    message: Optional[str] = None


class AcceptChallengeRequest(BaseModel):
    challenge_id: str
    wallet_address: str
    display_name: str = "Anonymous Guardian"
    client_seed: str
    signature: Optional[str] = None
    message: Optional[str] = None


class P2PPotJoinRequest(BaseModel):
    bet_amount_sol: float
    wallet_address: str
    display_name: str = "Anonymous Guardian"
    tx_signature: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None


# ========== Forum Models ==========
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


# ========== Messaging Models ==========
class SendMessageRequest(BaseModel):
    recipient_wallet: str
    content: str
    sender_wallet: str
    sender_name: str = "Anonymous"


# ========== Notification Models ==========
class NotificationSubscribeRequest(BaseModel):
    wallet_address: str
    endpoint: str
    p256dh: str
    auth: str


# ========== Email Models ==========
class EmailSubscribeRequest(BaseModel):
    email: str
    wallet_address: str
    subscribe_weekly: bool = True


class SendWelcomeEmailRequest(BaseModel):
    email: str
    wallet_address: str


# ========== Trading Journal Models ==========
class JournalBackupRequest(BaseModel):
    wallet_address: str
    trades: List[Dict]
    backup_name: str = "Backup"


# ========== Simulation Models ==========
class SimulationRequest(BaseModel):
    initialInvestment: float = 1000
    volatility: float = 0.5
    drift: float = 0.1
    days: int = 180


# ========== Leaderboard Models ==========
class LeaderboardSubmitRequest(BaseModel):
    player_name: str
    score: int
    moonCheese: int = 0


# ========== Shop Models ==========
class ShopOrderRequest(BaseModel):
    item_id: str
    quantity: int = 1
    wallet_address: Optional[str] = None
