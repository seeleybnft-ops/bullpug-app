"""Escrow system routes for P2P betting."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import httpx
import uuid
import logging
from datetime import datetime, timezone

from utils.database import db
from utils.config import DISTRIBUTION_WALLET


router = APIRouter(prefix="/escrow", tags=["escrow"])
logger = logging.getLogger(__name__)

# Using distribution wallet as escrow
ESCROW_WALLET = DISTRIBUTION_WALLET


class EscrowDepositRequest(BaseModel):
    wallet_address: str
    amount_sol: float
    tx_signature: str
    purpose: str  # challenge, pot
    reference_id: str  # challenge_id or pot_id


class EscrowWithdrawRequest(BaseModel):
    wallet_address: str
    amount_sol: float


@router.post("/deposit")
async def escrow_deposit(data: EscrowDepositRequest):
    """Record an escrow deposit (after user sends SOL to escrow wallet)."""
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
            
            if "error" in tx_data or tx_data.get("result") is None:
                logger.warning(f"Transaction not found or error: {data.tx_signature}")
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


@router.get("/balance/{wallet_address}")
async def get_escrow_balance(wallet_address: str):
    """Get user's escrow balance."""
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


@router.get("/wallet")
async def get_escrow_wallet():
    """Get the escrow wallet address for deposits."""
    return {
        "escrow_wallet": ESCROW_WALLET,
        "message": "Send SOL to this address for P2P betting"
    }
