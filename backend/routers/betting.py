"""Betting routes for P2P coin flip and pot games."""

from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
import hashlib
import secrets
import uuid
import logging
from datetime import datetime, timezone

from models.schemas import CreateChallengeRequest, AcceptChallengeRequest
from utils.database import db
from utils.config import RAKE_PERCENT, DISTRIBUTION_WALLET
from utils.solana_payout import send_sol_payout, get_escrow_balance
from routers.prize_pool import add_to_prize_pool

router = APIRouter(prefix="/betting", tags=["betting"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.get("/config")
async def get_betting_config():
    """Get betting configuration including rake and distribution wallet."""
    return {
        "rake_percent": RAKE_PERCENT,
        "distribution_wallet": DISTRIBUTION_WALLET,
        "currency": "SOL",
        "min_bet_sol": 0.005,
        "max_bet_sol": 10.0
    }


@router.post("/challenge/create")
@limiter.limit("10/minute")
async def create_challenge(request: Request, data: CreateChallengeRequest):
    """Create a P2P coin flip challenge."""
    if data.bet_amount_sol <= 0:
        raise HTTPException(status_code=400, detail="Bet must be positive")
    if data.bet_amount_sol < 0.005:
        raise HTTPException(status_code=400, detail="Minimum bet is 0.005 SOL")
    if data.bet_amount_sol > 10.0:
        raise HTTPException(status_code=400, detail="Maximum bet is 10 SOL")
    if data.choice.lower() not in ["heads", "tails"]:
        raise HTTPException(status_code=400, detail="Choice must be heads or tails")
    
    server_seed = secrets.token_hex(32)
    challenge = {
        "id": str(uuid.uuid4()),
        "creator_wallet": data.wallet_address,
        "creator_name": data.display_name,
        "creator_choice": data.choice.lower(),
        "bet_amount_sol": data.bet_amount_sol,
        "status": "open",
        "opponent_wallet": None,
        "opponent_name": None,
        "winner_wallet": None,
        "result": None,
        "rake_sol": round(data.bet_amount_sol * 2 * RAKE_PERCENT / 100, 6),
        "payout_sol": round(data.bet_amount_sol * 2 * (1 - RAKE_PERCENT / 100), 6),
        "server_seed": server_seed,
        "server_seed_hash": hashlib.sha256(server_seed.encode()).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "matched_at": None,
        "completed_at": None
    }
    
    await db.p2p_challenges.insert_one(challenge)
    
    return {
        "challenge_id": challenge["id"],
        "bet_amount_sol": challenge["bet_amount_sol"],
        "creator_choice": challenge["creator_choice"],
        "server_seed_hash": challenge["server_seed_hash"],
        "status": "open",
        "message": "Challenge created! Waiting for opponent."
    }


@router.get("/challenges")
async def get_open_challenges(limit: int = 20):
    """Get all open P2P challenges."""
    challenges = await db.p2p_challenges.find(
        {"status": "open"},
        {"_id": 0, "server_seed": 0}
    ).sort("created_at", -1).to_list(limit)
    return {"challenges": challenges}


@router.get("/challenge/{challenge_id}")
async def get_challenge(challenge_id: str):
    """Get a specific challenge."""
    challenge = await db.p2p_challenges.find_one({"id": challenge_id}, {"_id": 0})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge["status"] != "completed":
        challenge.pop("server_seed", None)
    return challenge


@router.post("/challenge/accept")
@limiter.limit("20/minute")
async def accept_challenge(request: Request, data: AcceptChallengeRequest):
    """Accept a P2P coin flip challenge and execute the flip."""
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
    
    creator_won = outcome == challenge["creator_choice"]
    winner_wallet = challenge["creator_wallet"] if creator_won else data.wallet_address
    winner_name = challenge["creator_name"] if creator_won else data.display_name
    
    # Update challenge
    await db.p2p_challenges.update_one(
        {"id": data.challenge_id},
        {"$set": {
            "status": "completed",
            "opponent_wallet": data.wallet_address,
            "opponent_name": data.display_name,
            "winner_wallet": winner_wallet,
            "result": outcome,
            "client_seed": data.client_seed,
            "result_hash": result_hash,
            "matched_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # === CONTRIBUTE TO PRIZE POOL (25% of rake) ===
    try:
        rake_amount = challenge["rake_sol"]
        await add_to_prize_pool(
            amount_sol=rake_amount,
            source="coinflip_rake",
            details={"challenge_id": data.challenge_id, "total_pot": challenge["bet_amount_sol"] * 2}
        )
    except Exception as e:
        logger.error(f"Failed to add to prize pool: {e}")
    
    # === AUTOMATIC PAYOUT ===
    payout_success = False
    payout_tx = None
    payout_error = None
    
    try:
        payout_amount = challenge["payout_sol"]
        logger.info(f"Initiating automatic payout: {payout_amount} SOL to {winner_wallet}")
        
        success, result = await send_sol_payout(
            recipient_wallet=winner_wallet,
            amount_sol=payout_amount,
            memo=f"Bullpug CoinFlip Win - Challenge {data.challenge_id[:8]}"
        )
        
        if success:
            payout_success = True
            payout_tx = result
            logger.info(f"Payout successful! TX: {payout_tx}")
        else:
            payout_error = result
            logger.error(f"Payout failed: {payout_error}")
            
    except Exception as e:
        payout_error = str(e)
        logger.error(f"Payout exception: {payout_error}")
    
    # Update challenge with payout status
    await db.p2p_challenges.update_one(
        {"id": data.challenge_id},
        {"$set": {
            "payout_sent": payout_success,
            "payout_tx": payout_tx,
            "payout_error": payout_error
        }}
    )
    
    # Record in history
    history_entry = {
        "id": str(uuid.uuid4()),
        "type": "coinflip",
        "bet_amount_sol": challenge["bet_amount_sol"],
        "outcome": outcome,
        "winner_wallet": winner_wallet,
        "winner_name": winner_name,
        "payout_sol": challenge["payout_sol"],
        "rake_sol": challenge["rake_sol"],
        "payout_sent": payout_success,
        "payout_tx": payout_tx,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.betting_history.insert_one(history_entry)
    
    return {
        "outcome": outcome,
        "winner_wallet": winner_wallet,
        "winner_name": winner_name,
        "payout_sol": challenge["payout_sol"],
        "rake_sol": challenge["rake_sol"],
        "server_seed": server_seed,
        "client_seed": data.client_seed,
        "result_hash": result_hash,
        "payout_sent": payout_success,
        "payout_tx": payout_tx,
        "payout_error": payout_error
    }


@router.post("/challenge/cancel/{challenge_id}")
async def cancel_challenge(challenge_id: str, wallet_address: str):
    """Cancel an open challenge (creator only)."""
    challenge = await db.p2p_challenges.find_one({"id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge["status"] != "open":
        raise HTTPException(status_code=400, detail="Cannot cancel - challenge not open")
    if challenge["creator_wallet"] != wallet_address:
        raise HTTPException(status_code=403, detail="Only creator can cancel")
    
    await db.p2p_challenges.update_one(
        {"id": challenge_id},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Challenge cancelled", "challenge_id": challenge_id}


@router.get("/history")
async def get_betting_history(limit: int = 20):
    """Get recent betting history."""
    history = await db.betting_history.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    return {"history": history}
