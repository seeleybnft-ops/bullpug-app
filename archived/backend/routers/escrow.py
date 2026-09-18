"""Escrow system routes for P2P betting."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import logging
from datetime import datetime, timezone

from utils.database import db
from utils.config import DISTRIBUTION_WALLET
from utils.tx_verify import verify_sol_transfer


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
    """Record an escrow deposit after verifying the SOL transfer on-chain.

    Rejects the deposit if the tx signature is missing, unconfirmed, paid to
    the wrong wallet, or short on amount. Idempotent on ``tx_signature``.
    """
    # Idempotency — never double-credit a single tx.
    existing = await db.escrow_deposits.find_one(
        {"tx_signature": data.tx_signature},
        {"_id": 0, "id": 1, "amount_sol": 1, "status": 1},
    )
    if existing:
        return {
            "message": "Deposit already recorded",
            "deposit_id": existing.get("id"),
            "duplicate": True,
        }

    ok, reason = await verify_sol_transfer(
        tx_signature=data.tx_signature,
        expected_recipient=ESCROW_WALLET,
        expected_amount_sol=data.amount_sol,
        expected_sender=data.wallet_address,
    )
    if not ok:
        logger.warning(
            "Escrow deposit rejected: %s for %s (%.6f SOL): %s",
            data.tx_signature, data.wallet_address, data.amount_sol, reason,
        )
        raise HTTPException(status_code=400, detail=f"Deposit verification failed: {reason}")

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
    """Get the escrow wallet address, balance, and fee info."""
    from utils.solana_payout import get_escrow_balance, get_escrow_pubkey, get_tx_fee_sol, TOTAL_TX_FEE_LAMPORTS, LAMPORTS_PER_SOL
    
    balance = get_escrow_balance()
    pubkey = get_escrow_pubkey()
    tx_fee = get_tx_fee_sol()
    
    # Calculate how many payouts can be made with current balance
    if balance and balance > tx_fee:
        max_single_payout = balance - tx_fee
    else:
        max_single_payout = 0
    
    return {
        "escrow_wallet": pubkey or ESCROW_WALLET,
        "balance_sol": balance,
        "balance_lamports": int(balance * LAMPORTS_PER_SOL) if balance else 0,
        "tx_fee_sol": tx_fee,
        "tx_fee_lamports": TOTAL_TX_FEE_LAMPORTS,
        "max_single_payout_sol": round(max_single_payout, 6) if max_single_payout > 0 else 0,
        "message": "Send SOL to this address for P2P betting"
    }


@router.post("/manual-payout")
async def manual_payout(wallet_address: str, amount_sol: float, admin_key: str):
    """Manually trigger a payout (admin only)."""
    from utils.solana_payout import send_sol_payout
    from utils.config import ADMIN_WALLETS
    
    # Simple admin check - in production use proper auth
    if admin_key not in ADMIN_WALLETS:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    if amount_sol <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    success, result = await send_sol_payout(
        recipient_wallet=wallet_address,
        amount_sol=amount_sol,
        memo="Bullpug Manual Payout"
    )
    
    if success:
        return {"success": True, "tx_signature": result, "amount_sol": amount_sol}
    else:
        raise HTTPException(status_code=500, detail=result)
