"""
Custodial Wallet Management for Auto-Trading
Provides secure, encrypted hot wallet functionality for automated trade execution.
Uses Jito bundles for reliable transaction landing during network congestion.
"""

import os
import base64
import logging
import random
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from cryptography.fernet import Fernet
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.message import Message
from solders.hash import Hash
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/custodial-wallet", tags=["custodial-wallet"])

# Database connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
from motor.motor_asyncio import AsyncIOMotorClient
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]

# Configuration
MAX_DEPOSIT_SOL = 0.5  # Maximum deposit limit
LAMPORTS_PER_SOL = 1_000_000_000

# RPC Configuration - Helius for tx submission (staked connections), Alchemy for reads
HELIUS_RPC_URL = os.environ.get("HELIUS_RPC_URL")
ALCHEMY_RPC_URL = os.environ.get("ALCHEMY_RPC_URL", "https://api.mainnet-beta.solana.com")

# Use Helius for transaction submission if available (better landing rates)
SOLANA_RPC_URL = HELIUS_RPC_URL or ALCHEMY_RPC_URL

# Jito Configuration - Multiple regional endpoints for redundancy
JITO_BUNDLE_ENDPOINTS = [
    "https://mainnet.block-engine.jito.wtf/api/v1/bundles",
    "https://amsterdam.mainnet.block-engine.jito.wtf/api/v1/bundles",
    "https://frankfurt.mainnet.block-engine.jito.wtf/api/v1/bundles",
    "https://ny.mainnet.block-engine.jito.wtf/api/v1/bundles",
    "https://tokyo.mainnet.block-engine.jito.wtf/api/v1/bundles",
]
JITO_TIP_ACCOUNTS = [
    "96gYZGCg6ZBH8UqPJgKWqWbToVCfUcmRRPP2SJHBFdLq",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"
]
JITO_TIP_LAMPORTS = 10000  # 0.00001 SOL tip for priority (can increase for higher priority)

# Encryption key - generate once and store in .env
# If not set, generate a new one (for development only)
ENCRYPTION_KEY = os.environ.get("CUSTODIAL_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # CRITICAL: Must be set in .env for production!
    # A generated key means wallet private keys will be lost on restart
    logger.error("CRITICAL: CUSTODIAL_ENCRYPTION_KEY not set in .env!")
    logger.error("Any custodial wallets created without this key will be UNRECOVERABLE")
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    logger.warning(f"Generated temporary key: {ENCRYPTION_KEY}")
    logger.warning("Add this to .env IMMEDIATELY: CUSTODIAL_ENCRYPTION_KEY={ENCRYPTION_KEY}")

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


# ============== Jito Bundle Helper ==============

async def send_transaction_via_jito(
    signed_tx_bytes: bytes,
    keypair: Keypair = None,  # Not needed when tip is in tx
    tip_lamports: int = JITO_TIP_LAMPORTS
) -> dict:
    """
    Send a transaction via Jito bundles for reliable landing.
    
    When using Jupiter's jitoTipLamports parameter, the tip is already included
    in the swap transaction, so we just need to send a single-tx bundle.
    
    Args:
        signed_tx_bytes: The signed swap transaction bytes (with Jito tip included)
        keypair: Not used when tip is already in transaction
        tip_lamports: For logging only
    
    Returns:
        dict with bundle_id on success
    """
    import asyncio
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Encode transaction as base64
        swap_tx_b64 = base64.b64encode(signed_tx_bytes).decode('utf-8')
        
        # Send single-tx bundle (tip is already in the swap tx)
        bundle_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendBundle",
            "params": [
                [swap_tx_b64],  # Single transaction with tip included
                {"encoding": "base64"}
            ]
        }
        
        logger.info(f"Sending Jito bundle (tip: {tip_lamports} lamports included in swap)...")
        
        # Try multiple endpoints with retry
        last_error = None
        shuffled_endpoints = random.sample(JITO_BUNDLE_ENDPOINTS, len(JITO_BUNDLE_ENDPOINTS))
        
        for endpoint in shuffled_endpoints:
            try:
                response = await client.post(endpoint, json=bundle_payload)
                result = response.json()
                
                if "error" in result:
                    error_msg = result.get("error", {}).get("message", str(result))
                    logger.warning(f"Jito {endpoint}: {error_msg}")
                    
                    # If rate limited, try next endpoint
                    if "rate limit" in error_msg.lower() or "congested" in error_msg.lower():
                        last_error = error_msg
                        await asyncio.sleep(0.5)
                        continue
                    # If invalid transaction, this is a real error
                    if "invalid" in error_msg.lower():
                        last_error = error_msg
                        continue
                    raise Exception(f"Jito bundle failed: {error_msg}")
                
                bundle_id = result.get("result")
                if bundle_id:
                    logger.info(f"Jito bundle submitted via {endpoint}: {bundle_id}")
                    return {
                        "bundle_id": bundle_id,
                        "tip_lamports": tip_lamports,
                        "endpoint": endpoint
                    }
                    
            except httpx.TimeoutException:
                logger.warning(f"Jito {endpoint} timeout, trying next...")
                last_error = "timeout"
                continue
            except Exception as e:
                if "rate limit" not in str(e).lower() and "congested" not in str(e).lower():
                    raise
                last_error = str(e)
                continue
        
        raise Exception(f"All Jito endpoints failed: {last_error}")


async def check_jito_bundle_status(bundle_id: str, endpoint: str = None) -> dict:
    """
    Check the status of a Jito bundle.
    
    Returns status info including whether the bundle landed.
    """
    # Use provided endpoint or default to first one
    check_endpoint = endpoint or JITO_BUNDLE_ENDPOINTS[0]
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBundleStatuses",
            "params": [[bundle_id]]
        }
        
        response = await client.post(check_endpoint, json=payload)
        result = response.json()
        
        if "error" in result:
            return {"status": "error", "error": result.get("error")}
        
        statuses = result.get("result", {}).get("value", [])
        if statuses and len(statuses) > 0:
            return statuses[0]
        
        return {"status": "pending"}


# ============== Models ==============

class CustodialWalletResponse(BaseModel):
    """Response model for custodial wallet info"""
    wallet_address: str
    balance_sol: float
    balance_lamports: int
    max_deposit_sol: float = MAX_DEPOSIT_SOL
    available_deposit_sol: float
    created_at: str
    last_activity: Optional[str] = None
    total_deposits: float = 0
    total_withdrawals: float = 0


class DepositRequest(BaseModel):
    """Request to deposit SOL into custodial wallet"""
    user_wallet: str
    amount_sol: float = Field(gt=0, le=MAX_DEPOSIT_SOL)


class WithdrawRequest(BaseModel):
    """Request to withdraw SOL from custodial wallet"""
    user_wallet: str
    amount_sol: float = Field(gt=0)
    destination_wallet: Optional[str] = None  # If not provided, use user_wallet


class TransactionRecord(BaseModel):
    """Record of deposit/withdrawal transaction"""
    tx_type: str  # "deposit" or "withdrawal"
    amount_sol: float
    amount_lamports: int
    tx_signature: Optional[str] = None
    status: str  # "pending", "confirmed", "failed"
    created_at: str
    confirmed_at: Optional[str] = None


# ============== Encryption Utilities ==============

def encrypt_private_key(private_key_bytes: bytes) -> str:
    """Encrypt private key for secure storage"""
    encrypted = fernet.encrypt(private_key_bytes)
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_private_key(encrypted_key: str) -> bytes:
    """Decrypt private key for transaction signing"""
    encrypted_bytes = base64.b64decode(encrypted_key.encode('utf-8'))
    return fernet.decrypt(encrypted_bytes)


# ============== Wallet Management ==============

async def get_or_create_custodial_wallet(user_wallet: str) -> dict:
    """Get existing custodial wallet or create a new one for user"""
    
    # Check if wallet exists
    existing = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    
    if existing:
        return existing
    
    # Create new keypair
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    private_key_bytes = bytes(keypair)
    
    # Encrypt private key
    encrypted_private_key = encrypt_private_key(private_key_bytes)
    
    # Store in database
    wallet_doc = {
        "user_wallet": user_wallet,
        "custodial_address": public_key,
        "encrypted_private_key": encrypted_private_key,
        "balance_lamports": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": None,
        "total_deposits_lamports": 0,
        "total_withdrawals_lamports": 0,
        "transaction_history": []
    }
    
    await db.custodial_wallets.insert_one(wallet_doc)
    logger.info(f"Created custodial wallet {public_key[:8]}... for user {user_wallet[:8]}...")
    
    return wallet_doc


async def get_custodial_keypair(user_wallet: str) -> Keypair:
    """Get the keypair for a user's custodial wallet (for signing transactions)"""
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    try:
        private_key_bytes = decrypt_private_key(wallet_doc["encrypted_private_key"])
        return Keypair.from_bytes(private_key_bytes)
    except Exception as e:
        logger.error(f"Failed to decrypt private key: {e}")
        raise HTTPException(status_code=500, detail="Failed to access custodial wallet")


async def get_wallet_balance(address: str) -> int:
    """Get SOL balance of a wallet in lamports"""
    try:
        async with AsyncClient(SOLANA_RPC_URL) as client:
            response = await client.get_balance(Pubkey.from_string(address))
            return response.value
    except Exception as e:
        logger.error(f"Failed to get balance for {address}: {e}")
        return 0


async def update_wallet_balance(user_wallet: str):
    """Update the stored balance from on-chain data"""
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    if wallet_doc:
        balance = await get_wallet_balance(wallet_doc["custodial_address"])
        await db.custodial_wallets.update_one(
            {"user_wallet": user_wallet},
            {"$set": {"balance_lamports": balance, "last_activity": datetime.now(timezone.utc).isoformat()}}
        )
        return balance
    return 0


# ============== API Endpoints ==============

@router.post("/regenerate/{user_wallet}")
async def regenerate_custodial_wallet(user_wallet: str):
    """
    Regenerate a custodial wallet with new keys.
    Use this when the encryption key was lost and the wallet is unrecoverable.
    WARNING: Any SOL in the old wallet will be LOST!
    """
    try:
        # Check if old wallet exists
        old_wallet = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
        old_address = old_wallet.get("custodial_address") if old_wallet else None
        old_balance = 0
        
        if old_wallet:
            try:
                old_balance = await get_wallet_balance(old_wallet["custodial_address"])
            except Exception:
                pass
        
        # Generate new keypair
        new_keypair = Keypair()
        new_address = str(new_keypair.pubkey())
        private_key_bytes = bytes(new_keypair)
        encrypted_private_key = encrypt_private_key(private_key_bytes)
        
        # Delete old wallet if exists
        if old_wallet:
            await db.custodial_wallets.delete_one({"user_wallet": user_wallet})
        
        # Create new wallet document
        wallet_doc = {
            "user_wallet": user_wallet,
            "custodial_address": new_address,
            "encrypted_private_key": encrypted_private_key,
            "balance_lamports": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": None,
            "total_deposits_lamports": 0,
            "total_withdrawals_lamports": 0,
            "transaction_history": [],
            "regenerated_from": old_address,
            "lost_balance_lamports": old_balance
        }
        
        await db.custodial_wallets.insert_one(wallet_doc)
        
        logger.info(f"Regenerated custodial wallet for {user_wallet[:12]}... New address: {new_address}")
        if old_balance > 0:
            logger.warning(f"LOST {old_balance / LAMPORTS_PER_SOL:.6f} SOL in old wallet {old_address}")
        
        return {
            "success": True,
            "new_address": new_address,
            "old_address": old_address,
            "lost_balance_sol": old_balance / LAMPORTS_PER_SOL if old_balance else 0,
            "message": f"New custodial wallet created. Old wallet had {old_balance / LAMPORTS_PER_SOL:.6f} SOL that is now inaccessible."
        }
        
    except Exception as e:
        logger.error(f"Regenerate wallet error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{user_wallet}")
async def get_wallet_info(user_wallet: str) -> CustodialWalletResponse:
    """Get custodial wallet information for a user"""
    
    wallet_doc = await get_or_create_custodial_wallet(user_wallet)
    
    # Get current on-chain balance
    balance_lamports = await get_wallet_balance(wallet_doc["custodial_address"])
    
    # Update stored balance
    await db.custodial_wallets.update_one(
        {"user_wallet": user_wallet},
        {"$set": {"balance_lamports": balance_lamports}}
    )
    
    balance_sol = balance_lamports / LAMPORTS_PER_SOL
    available_deposit = max(0, MAX_DEPOSIT_SOL - balance_sol)
    
    return CustodialWalletResponse(
        wallet_address=wallet_doc["custodial_address"],
        balance_sol=round(balance_sol, 6),
        balance_lamports=balance_lamports,
        max_deposit_sol=MAX_DEPOSIT_SOL,
        available_deposit_sol=round(available_deposit, 6),
        created_at=wallet_doc["created_at"],
        last_activity=wallet_doc.get("last_activity"),
        total_deposits=wallet_doc.get("total_deposits_lamports", 0) / LAMPORTS_PER_SOL,
        total_withdrawals=wallet_doc.get("total_withdrawals_lamports", 0) / LAMPORTS_PER_SOL
    )


@router.get("/address/{user_wallet}")
async def get_deposit_address(user_wallet: str):
    """Get the custodial wallet address for deposits"""
    wallet_doc = await get_or_create_custodial_wallet(user_wallet)
    
    return {
        "custodial_address": wallet_doc["custodial_address"],
        "max_deposit_sol": MAX_DEPOSIT_SOL,
        "instructions": f"Send up to {MAX_DEPOSIT_SOL} SOL to this address for auto-trading"
    }


@router.post("/prepare-deposit")
async def prepare_deposit(request: DepositRequest):
    """Prepare a deposit transaction (returns transaction for user to sign)"""
    
    # Get or create custodial wallet
    wallet_doc = await get_or_create_custodial_wallet(request.user_wallet)
    custodial_address = wallet_doc["custodial_address"]
    
    # Check current balance
    current_balance = await get_wallet_balance(custodial_address)
    current_sol = current_balance / LAMPORTS_PER_SOL
    
    # Validate deposit amount
    if current_sol + request.amount_sol > MAX_DEPOSIT_SOL:
        available = MAX_DEPOSIT_SOL - current_sol
        raise HTTPException(
            status_code=400, 
            detail=f"Deposit would exceed max limit. Available: {available:.4f} SOL"
        )
    
    amount_lamports = int(request.amount_sol * LAMPORTS_PER_SOL)
    
    return {
        "success": True,
        "deposit_address": custodial_address,
        "amount_sol": request.amount_sol,
        "amount_lamports": amount_lamports,
        "current_balance_sol": round(current_sol, 6),
        "after_deposit_sol": round(current_sol + request.amount_sol, 6),
        "message": f"Send {request.amount_sol} SOL to {custodial_address}"
    }


@router.post("/confirm-deposit")
async def confirm_deposit(user_wallet: str, tx_signature: str, amount_lamports: int):
    """Confirm a deposit after user signs and submits the transaction"""
    
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    # Record the transaction
    tx_record = {
        "tx_type": "deposit",
        "amount_lamports": amount_lamports,
        "amount_sol": amount_lamports / LAMPORTS_PER_SOL,
        "tx_signature": tx_signature,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Update wallet
    new_balance = await update_wallet_balance(user_wallet)
    
    await db.custodial_wallets.update_one(
        {"user_wallet": user_wallet},
        {
            "$push": {"transaction_history": tx_record},
            "$inc": {"total_deposits_lamports": amount_lamports}
        }
    )
    
    logger.info(f"Deposit confirmed: {amount_lamports} lamports to custodial wallet for {user_wallet[:8]}...")
    
    return {
        "success": True,
        "tx_signature": tx_signature,
        "new_balance_sol": new_balance / LAMPORTS_PER_SOL,
        "message": "Deposit confirmed successfully"
    }


@router.post("/withdraw")
async def withdraw_funds(request: WithdrawRequest):
    """Withdraw SOL from custodial wallet back to user's wallet"""
    
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": request.user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    # Get current balance
    custodial_address = wallet_doc["custodial_address"]
    balance_lamports = await get_wallet_balance(custodial_address)
    
    # Validate withdrawal amount (leave some for transaction fee)
    withdraw_lamports = int(request.amount_sol * LAMPORTS_PER_SOL)
    fee_buffer = 10000  # 0.00001 SOL for tx fee
    
    if withdraw_lamports + fee_buffer > balance_lamports:
        max_withdraw = (balance_lamports - fee_buffer) / LAMPORTS_PER_SOL
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Max withdrawal: {max_withdraw:.6f} SOL"
        )
    
    # Get keypair for signing
    keypair = await get_custodial_keypair(request.user_wallet)
    
    destination = request.destination_wallet or request.user_wallet
    
    try:
        async with AsyncClient(SOLANA_RPC_URL) as client:
            # Get recent blockhash
            blockhash_resp = await client.get_latest_blockhash()
            recent_blockhash = blockhash_resp.value.blockhash
            
            # Create transfer instruction
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=keypair.pubkey(),
                    to_pubkey=Pubkey.from_string(destination),
                    lamports=withdraw_lamports
                )
            )
            
            # Create and sign transaction
            msg = Message.new_with_blockhash(
                [transfer_ix],
                keypair.pubkey(),
                recent_blockhash
            )
            tx = Transaction.new_unsigned(msg)
            tx.sign([keypair], recent_blockhash)
            
            # Send transaction
            result = await client.send_transaction(tx)
            tx_signature = str(result.value)
            
            # Record transaction
            tx_record = {
                "tx_type": "withdrawal",
                "amount_lamports": withdraw_lamports,
                "amount_sol": request.amount_sol,
                "destination": destination,
                "tx_signature": tx_signature,
                "status": "confirmed",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update database
            new_balance = await update_wallet_balance(request.user_wallet)
            
            await db.custodial_wallets.update_one(
                {"user_wallet": request.user_wallet},
                {
                    "$push": {"transaction_history": tx_record},
                    "$inc": {"total_withdrawals_lamports": withdraw_lamports}
                }
            )
            
            logger.info(f"Withdrawal successful: {request.amount_sol} SOL from custodial wallet to {destination[:8]}...")
            
            return {
                "success": True,
                "tx_signature": tx_signature,
                "amount_sol": request.amount_sol,
                "destination": destination,
                "new_balance_sol": new_balance / LAMPORTS_PER_SOL,
                "message": f"Successfully withdrew {request.amount_sol} SOL"
            }
            
    except Exception as e:
        logger.error(f"Withdrawal failed: {e}")
        raise HTTPException(status_code=500, detail=f"Withdrawal failed: {str(e)}")


@router.get("/transactions/{user_wallet}")
async def get_transaction_history(user_wallet: str, limit: int = 20):
    """Get transaction history for custodial wallet"""
    
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    transactions = wallet_doc.get("transaction_history", [])
    
    # Return most recent first
    transactions = sorted(transactions, key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "transactions": transactions[:limit],
        "total_count": len(transactions)
    }


@router.delete("/close/{user_wallet}")
async def close_custodial_wallet(user_wallet: str):
    """Close custodial wallet and withdraw all remaining funds"""
    
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    # Check balance
    balance = await get_wallet_balance(wallet_doc["custodial_address"])
    
    if balance > 10000:  # More than just dust
        # Withdraw remaining balance first
        balance_sol = (balance - 5000) / LAMPORTS_PER_SOL  # Leave tiny amount for fee
        withdraw_request = WithdrawRequest(
            user_wallet=user_wallet,
            amount_sol=balance_sol
        )
        await withdraw_funds(withdraw_request)
    
    # Mark wallet as closed (don't delete for audit trail)
    await db.custodial_wallets.update_one(
        {"user_wallet": user_wallet},
        {
            "$set": {
                "status": "closed",
                "closed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Custodial wallet closed. Any remaining funds have been returned."
    }


# ============== Auto-Trade Execution Helper ==============

async def execute_auto_trade(user_wallet: str, input_mint: str, output_mint: str, amount_lamports: int) -> dict:
    """
    Execute a swap using the custodial wallet (called by auto-trade system).
    This function handles the actual trade execution for automated trading.
    
    For BUYS (SOL -> Token): amount_lamports is SOL amount to spend
    For SELLS (Token -> SOL): amount_lamports is the token amount in smallest units
    """
    
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    custodial_address = wallet_doc["custodial_address"]
    balance = await get_wallet_balance(custodial_address)
    
    # For buys (SOL -> Token): check SOL balance
    # For sells (Token -> SOL): just need enough SOL for fees
    is_sell = output_mint == "So11111111111111111111111111111111111111112"
    
    if is_sell:
        # For sells, only need SOL for transaction fees (~0.003 SOL should be enough)
        min_fee_buffer = 3000000  # 0.003 SOL for fees
        if balance < min_fee_buffer:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient SOL for fees. Have: {balance/LAMPORTS_PER_SOL:.4f} SOL, Need: ~0.003 SOL for fees"
            )
    else:
        # For buys, check SOL balance covers the swap amount + fees
        if balance < amount_lamports + 50000:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient custodial balance. Have: {balance/LAMPORTS_PER_SOL:.4f} SOL, Need: {amount_lamports/LAMPORTS_PER_SOL:.4f} SOL"
            )
    
    # Get keypair
    keypair = await get_custodial_keypair(user_wallet)
    
    try:
        # Use regular swap with high priority fees and retry logic
        return await _execute_swap_with_retry(
            keypair, custodial_address, input_mint, output_mint,
            amount_lamports, user_wallet, max_retries=3
        )
                
    except Exception as e:
        logger.error(f"Auto-trade execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")


async def _execute_swap_with_retry(
    keypair: Keypair,
    custodial_address: str,
    input_mint: str,
    output_mint: str,
    amount_lamports: int,
    user_wallet: str,
    max_retries: int = 3
) -> dict:
    """
    Execute swap with retry logic using fresh blockhash each attempt.
    Uses Helius RPC with staked connections for better transaction landing.
    """
    import asyncio
    from solders.transaction import VersionedTransaction
    from solders.signature import Signature
    
    # Log which RPC we're using
    rpc_name = "Helius" if HELIUS_RPC_URL and HELIUS_RPC_URL in SOLANA_RPC_URL else "Alchemy"
    logger.info(f"Using {rpc_name} RPC for transaction submission")
    
    last_error = None
    
    for retry in range(max_retries):
        try:
            logger.info(f"Swap attempt {retry + 1}/{max_retries}")
            
            async with httpx.AsyncClient(timeout=45.0) as client:
                # Get fresh quote
                quote_response = await client.get(
                    "https://lite-api.jup.ag/swap/v1/quote",
                    params={
                        "inputMint": input_mint,
                        "outputMint": output_mint,
                        "amount": str(amount_lamports),
                        "slippageBps": "150"  # 1.5% slippage for better fill
                    }
                )
                
                if quote_response.status_code != 200:
                    raise Exception(f"Failed to get quote: {quote_response.text}")
                
                quote_data = quote_response.json()
                
                # Get swap transaction with high priority
                swap_response = await client.post(
                    "https://lite-api.jup.ag/swap/v1/swap",
                    json={
                        "quoteResponse": quote_data,
                        "userPublicKey": custodial_address,
                        "wrapAndUnwrapSol": True,
                        "computeUnitPriceMicroLamports": 1000000,  # 1M microlamports = high priority
                        "dynamicComputeUnitLimit": True
                    }
                )
                
                if swap_response.status_code != 200:
                    raise Exception(f"Failed to get swap: {swap_response.text}")
                
                swap_data = swap_response.json()
                swap_transaction = swap_data.get("swapTransaction")
                
                if not swap_transaction:
                    raise Exception("No swap transaction returned")
                
                # Sign transaction using the correct method
                # IMPORTANT: VersionedTransaction(message, [keypair]) is the correct way
                # sign_message() + populate() causes SignatureFailure on Jupiter swaps
                tx_bytes = base64.b64decode(swap_transaction)
                unsigned_tx = VersionedTransaction.from_bytes(tx_bytes)
                
                # Use constructor with keypair - this properly signs the transaction
                signed_tx = VersionedTransaction(unsigned_tx.message, [keypair])
                signed_tx_bytes = bytes(signed_tx)
                
                logger.info(f"Transaction signed ({len(signed_tx_bytes)} bytes)")
                
                # Send via RPC
                async with AsyncClient(SOLANA_RPC_URL) as solana_client:
                    # Simulate first
                    sim_result = await solana_client.simulate_transaction(signed_tx)
                    if sim_result.value.err:
                        raise Exception(f"Simulation failed: {sim_result.value.err}")
                    
                    logger.info(f"Simulation passed (units: {sim_result.value.units_consumed})")
                    
                    # Send transaction
                    result = await solana_client.send_raw_transaction(
                        signed_tx_bytes,
                        opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed)
                    )
                    tx_signature = str(result.value)
                    
                    logger.info(f"Transaction sent: {tx_signature[:20]}...")
                    
                    # Wait for confirmation with extended timeout
                    for attempt in range(12):  # Up to 36 seconds
                        await asyncio.sleep(3)
                        try:
                            sig_obj = Signature.from_string(tx_signature)
                            tx_info = await solana_client.get_transaction(
                                sig_obj,
                                max_supported_transaction_version=0
                            )
                            if tx_info.value is not None:
                                if tx_info.value.transaction.meta and tx_info.value.transaction.meta.err:
                                    raise Exception(f"Transaction failed: {tx_info.value.transaction.meta.err}")
                                
                                logger.info(f"Transaction CONFIRMED: {tx_signature}")
                                
                                await update_wallet_balance(user_wallet)
                                
                                return {
                                    "success": True,
                                    "tx_signature": tx_signature,
                                    "input_amount": amount_lamports,
                                    "output_amount": quote_data.get("outAmount"),
                                    "confirmed": True,
                                    "method": "rpc_with_priority",
                                    "retry_count": retry
                                }
                        except Exception as e:
                            if "failed" in str(e).lower():
                                raise
                            logger.debug(f"Confirmation check {attempt + 1}: {e}")
                    
                    # Transaction not confirmed - will retry with fresh blockhash
                    last_error = f"Transaction {tx_signature[:20]}... not confirmed after 36s"
                    logger.warning(f"{last_error}, retrying with fresh blockhash...")
        
        except Exception as e:
            last_error = str(e)
            if "simulation failed" in str(e).lower() or "failed" in str(e).lower():
                # Don't retry on simulation failures or explicit failures
                raise
            logger.warning(f"Attempt {retry + 1} failed: {e}")
            
            if retry < max_retries - 1:
                await asyncio.sleep(2)  # Brief pause before retry
    
    raise Exception(f"All {max_retries} swap attempts failed. Last error: {last_error}")
