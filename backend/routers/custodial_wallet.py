"""
Custodial Wallet Management for Auto-Trading
Provides secure, encrypted hot wallet functionality for automated trade execution.
Uses Jito bundles for reliable transaction landing during network congestion.
"""

import os
import base64
import logging
import random
import uuid
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

# Use shared database connection
from utils.database import db
from services.ledger import record_entry as ledger_record, get_available_balance as ledger_balance

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
# NOTE: Primary Jito execution now in services/jito_executor.py
# These legacy functions are kept for potential direct bundle usage

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
    # Try Helius first (valid API key), fallback to public RPC
    rpcs = [
        SOLANA_RPC_URL,
        os.environ.get("ALCHEMY_SOLANA_RPC", "https://api.mainnet-beta.solana.com"),
    ]
    for rpc_url in rpcs:
        try:
            async with AsyncClient(rpc_url) as client:
                response = await client.get_balance(Pubkey.from_string(address))
                return response.value
        except Exception:
            continue
    
    logger.warning(f"All RPCs failed for balance of {address}")
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
    
    # NOTE: Do NOT update balance_lamports here — that's the job of detect_deposit.
    # Updating it here defeats deposit detection (which compares on-chain vs stored).
    
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
    
    amount_sol = amount_lamports / LAMPORTS_PER_SOL
    
    # Record the transaction
    tx_record = {
        "tx_type": "deposit",
        "amount_lamports": amount_lamports,
        "amount_sol": amount_sol,
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
    
    # Record in internal ledger (credit)
    await ledger_record(
        user_wallet, "deposit", amount_sol,
        reference_id=tx_signature,
        reference_type="deposit_tx",
        description=f"Deposit {amount_sol:.6f} SOL",
        metadata={"tx_signature": tx_signature, "amount_lamports": amount_lamports}
    )
    
    logger.info(f"Deposit confirmed: {amount_lamports} lamports to custodial wallet for {user_wallet[:8]}...")
    
    return {
        "success": True,
        "tx_signature": tx_signature,
        "new_balance_sol": new_balance / LAMPORTS_PER_SOL,
        "message": "Deposit confirmed successfully"
    }


@router.post("/detect-deposit/{user_wallet}")
async def detect_deposit(user_wallet: str):
    """
    Auto-detect new deposits by comparing on-chain balance with tracked deposits.
    If new SOL is found, record it as a deposit in the ledger.
    """
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")

    custodial_address = wallet_doc["custodial_address"]

    # Get current on-chain balance
    on_chain_lamports = await get_wallet_balance(custodial_address)
    on_chain_sol = on_chain_lamports / LAMPORTS_PER_SOL

    # The ledger available balance = sum of all entries (deposits - trades - fees).
    # Any SOL on-chain that exceeds this is a new unrecorded deposit.
    from services.ledger import get_available_balance
    ledger_balance_sol = await get_available_balance(user_wallet)

    diff_sol = on_chain_sol - ledger_balance_sol
    diff_lamports = int(diff_sol * LAMPORTS_PER_SOL)

    # Minimum detection threshold: 0.001 SOL (1M lamports) to avoid rounding noise
    if diff_lamports < 1_000_000:
        return {
            "success": True,
            "detected": False,
            "on_chain_sol": round(on_chain_sol, 6),
            "ledger_sol": round(ledger_balance_sol, 6),
            "message": "No new deposit detected"
        }

    # New SOL detected! Record it
    deposit_sol = round(diff_sol, 6)
    deposit_lamports = int(deposit_sol * LAMPORTS_PER_SOL)
    
    await db.custodial_wallets.update_one(
        {"user_wallet": user_wallet},
        {
            "$set": {
                "balance_lamports": on_chain_lamports,
                "last_activity": datetime.now(timezone.utc).isoformat(),
            },
            "$inc": {"total_deposits_lamports": deposit_lamports},
            "$push": {
                "transaction_history": {
                    "tx_type": "deposit",
                    "amount_lamports": deposit_lamports,
                    "amount_sol": deposit_sol,
                    "tx_signature": "auto_detected",
                    "status": "confirmed",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        },
    )

    # Record in internal ledger
    await ledger_record(
        user_wallet,
        "deposit",
        deposit_sol,
        reference_type="auto_detected_deposit",
        description=f"Deposit detected: {deposit_sol:.6f} SOL",
        metadata={"on_chain_lamports": on_chain_lamports, "ledger_available_sol": ledger_balance_sol},
    )

    logger.info(f"Auto-detected deposit of {deposit_sol:.6f} SOL for {user_wallet[:8]}…")

    return {
        "success": True,
        "detected": True,
        "deposit_sol": deposit_sol,
        "new_balance_sol": round(on_chain_sol, 6),
        "message": f"Deposit of {deposit_sol:.6f} SOL detected and recorded",
    }


@router.api_route("/reconcile/{user_wallet}", methods=["GET", "POST"])
async def reconcile_ledger(user_wallet: str):
    """
    One-time reconciliation: ensures ledger deposits + debits match on-chain state.
    Calculates: expected_deposits = on_chain_sol + abs(all debits from ledger)
    If ledger deposits are short, adds a correction entry.
    """
    wallet_doc = await db.custodial_wallets.find_one(
        {"user_wallet": user_wallet}, {"_id": 0}
    )
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Wallet not found")

    custodial_address = wallet_doc["custodial_address"]
    on_chain_lamports = await get_wallet_balance(custodial_address)
    on_chain_sol = on_chain_lamports / LAMPORTS_PER_SOL

    # Get all ledger entries
    entries = await db.user_ledger.find(
        {"user_wallet": user_wallet}, {"_id": 0}
    ).to_list(1000)

    total_deposits = sum(e["amount_sol"] for e in entries if e.get("entry_type") == "deposit")
    total_debits = sum(abs(e["amount_sol"]) for e in entries if e.get("amount_sol", 0) < 0)

    # Expected deposits = what's on-chain + what was spent
    expected_deposits = on_chain_sol + total_debits
    gap = round(expected_deposits - total_deposits, 6)

    if gap < 0.0005:
        return {
            "success": True, "reconciled": False,
            "message": "Ledger is already balanced",
            "total_deposits": round(total_deposits, 6),
            "expected_deposits": round(expected_deposits, 6),
        }

    # Add correction entry
    await ledger_record(
        user_wallet, "deposit", gap,
        reference_type="reconciliation",
        description=f"Ledger reconciliation: +{gap:.6f} SOL (correcting prior detection gap)",
        metadata={"on_chain_sol": on_chain_sol, "total_debits": total_debits}
    )

    return {
        "success": True, "reconciled": True,
        "correction_sol": gap,
        "new_total_deposits": round(total_deposits + gap, 6),
        "on_chain_sol": round(on_chain_sol, 6),
        "message": f"Added {gap:.6f} SOL correction. Deposits now balanced."
    }


@router.api_route("/sync-positions/{user_wallet}", methods=["GET", "POST"])
async def sync_positions(user_wallet: str):
    """
    Sync on-chain token holdings with the positions database.
    - Queries BOTH legacy Token program AND Token-2022 program
    - Creates position records for tokens held on-chain but missing from DB
    - Auto-closes DB positions whose on-chain balance is zero
    """
    wallet_doc = await db.custodial_wallets.find_one(
        {"user_wallet": user_wallet}, {"_id": 0}
    )
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Wallet not found")

    custodial_address = wallet_doc["custodial_address"]

    # 1. Get all on-chain token holdings (both Token programs)
    import os
    import httpx

    rpc_url = os.environ.get("HELIUS_RPC_URL", "")
    TOKEN_PROGRAM_LEGACY = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    TOKEN_PROGRAM_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

    onchain_tokens = {}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for program_id in [TOKEN_PROGRAM_LEGACY, TOKEN_PROGRAM_2022]:
                resp = await client.post(rpc_url, json={
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        custodial_address,
                        {"programId": program_id},
                        {"encoding": "jsonParsed"}
                    ]
                })
                data = resp.json()
                if "error" in data:
                    logger.warning(f"Sync RPC error for {program_id[:12]}: {data['error']}")
                    continue
                for acc in data.get("result", {}).get("value", []):
                    info = acc["account"]["data"]["parsed"]["info"]
                    mint = info["mint"]
                    ui_amount = info["tokenAmount"].get("uiAmount", 0)
                    if ui_amount and ui_amount > 0:
                        onchain_tokens[mint] = ui_amount
    except Exception as e:
        logger.error(f"Sync: failed to fetch on-chain tokens: {e}")
        raise HTTPException(status_code=500, detail=f"RPC error: {e}")

    # 2. Get existing DB positions (open or pending)
    db_positions = await db.ai_trader_positions.find(
        {"wallet_address": user_wallet, "status": {"$in": ["open", "take_profit_pending", "pending_stop_loss", "pending_take_profit"]}},
        {"_id": 0, "token_mint": 1, "position_id": 1}
    ).to_list(100)
    db_mints = set(p.get("token_mint") for p in db_positions)

    # 3. Auto-close DB positions with zero on-chain balance
    #    AND update token amounts for positions that exist on-chain
    from datetime import datetime, timezone
    import uuid
    closed_stale = []
    updated_amounts = []
    for pos in db_positions:
        mint = pos.get("token_mint")
        if not mint:
            continue
        if mint not in onchain_tokens:
            # Zero balance on-chain — close the position
            await db.ai_trader_positions.update_one(
                {"position_id": pos["position_id"]},
                {"$set": {
                    "status": "closed_sync",
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "close_reason": "Zero balance on-chain (auto-sync)"
                }}
            )
            closed_stale.append(mint[:12] + "...")
        else:
            # Update token amount to match on-chain reality
            onchain_amount = onchain_tokens[mint]
            await db.ai_trader_positions.update_one(
                {"position_id": pos["position_id"]},
                {"$set": {
                    "token_amount": onchain_amount,
                    "amount_tokens": onchain_amount,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            updated_amounts.append(mint[:12] + "...")

    # 4. Find missing positions (on-chain but not in DB)
    missing_mints = set(onchain_tokens.keys()) - db_mints

    # 5. Get prices and create missing positions
    from services.market_data import get_dexscreener_pair_data
    known_mints = {
        "hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux": "HNT",
        "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL": "JTO",
        "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "JUP",
        "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": "PYTH",
        "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": "WIF",
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
        "H43xqMLiFLNLLGRhXKxJUVXdEe8uVdXs93Emo5Wzpump": "PIXEL",
        "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof": "RNDR",
        "DriFtupJYLTosbwoN8koMbEYSx54aFAVLddWsbksjwg7": "DRIFT",
        "34q2KmCvapecJgR6ZrtbCTrzZVtkt3a5mHEA3TuEsWYb": "LOL",
    }
    synced = []

    for mint in missing_mints:
        token_amount = onchain_tokens[mint]
        price = 0
        symbol = "UNKNOWN"

        try:
            pair_data = await get_dexscreener_pair_data(mint)
            if pair_data:
                price = pair_data.get("priceUsd", 0)
                if isinstance(price, str):
                    price = float(price)
                symbol = pair_data.get("baseToken", {}).get("symbol", mint[:8])
        except Exception:
            pass

        if symbol == "UNKNOWN" and mint in known_mints:
            symbol = known_mints[mint]

        position_doc = {
            "position_id": str(uuid.uuid4()),
            "wallet_address": user_wallet,
            "token_symbol": symbol,
            "token_mint": mint,
            "entry_price": price if price > 0 else 0,
            "current_price": price if price > 0 else 0,
            "amount_sol": 0,
            "token_amount": token_amount,
            "status": "open",
            "auto_trade": True,
            "synced_from_chain": True,
            "take_profit_pct": 20.0,
            "stop_loss_pct": -10.0,
            "trailing_stop_enabled": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        await db.ai_trader_positions.insert_one(position_doc)
        synced.append({"symbol": symbol, "mint": mint[:12] + "...", "token_amount": token_amount})

    return {
        "success": True,
        "synced": len(synced),
        "closed_stale": len(closed_stale),
        "updated_amounts": len(updated_amounts),
        "positions_synced": synced,
        "stale_closed": closed_stale,
        "message": f"Synced {len(synced)} new, closed {len(closed_stale)} stale, updated {len(updated_amounts)} amounts",
        "onchain_count": len(onchain_tokens),
        "db_count": len(db_mints) - len(closed_stale) + len(synced),
    }


@router.post("/withdraw")
async def withdraw_funds(request: WithdrawRequest):
    """Withdraw SOL from custodial wallet back to user's wallet"""
    
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": request.user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    # Validate against internal ledger balance first
    virtual_balance = await ledger_balance(request.user_wallet)
    if request.amount_sol > virtual_balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient ledger balance. Available: {virtual_balance:.6f} SOL"
        )
    
    # Get current on-chain balance
    custodial_address = wallet_doc["custodial_address"]
    balance_lamports = await get_wallet_balance(custodial_address)
    
    # Validate withdrawal amount (leave some for transaction fee)
    withdraw_lamports = int(request.amount_sol * LAMPORTS_PER_SOL)
    fee_buffer = 10000  # 0.00001 SOL for tx fee
    
    if withdraw_lamports + fee_buffer > balance_lamports:
        max_withdraw = (balance_lamports - fee_buffer) / LAMPORTS_PER_SOL
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient on-chain balance. Max withdrawal: {max_withdraw:.6f} SOL"
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
            
            # Record in internal ledger (debit)
            await ledger_record(
                request.user_wallet, "withdrawal", -request.amount_sol,
                reference_id=tx_signature,
                reference_type="withdrawal_tx",
                description=f"Withdraw {request.amount_sol:.6f} SOL to {destination[:12]}…",
                metadata={"tx_signature": tx_signature, "destination": destination}
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
            
    except HTTPException:
        raise
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


@router.get("/token-balance/{wallet_address}/{token_mint}")
async def get_token_balance(wallet_address: str, token_mint: str):
    """
    Get token balance for a specific wallet and token mint.
    Works with both SPL Token and Token-2022 programs.
    """
    from solana.rpc.types import TokenAccountOpts
    
    try:
        TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        TOKEN_2022_PROGRAM_ID = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
        
        wallet_pubkey = Pubkey.from_string(wallet_address)
        mint_pubkey = Pubkey.from_string(token_mint)
        
        token_balance = 0
        ui_amount = 0.0
        decimals = 9
        
        # Try multiple RPC endpoints for reliability
        rpc_endpoints = [
            os.environ.get("HELIUS_RPC_URL"),
            os.environ.get("ALCHEMY_SOLANA_RPC"),
            SOLANA_RPC_URL,
            "https://api.mainnet-beta.solana.com"
        ]
        rpc_endpoints = [r for r in rpc_endpoints if r]
        
        for rpc_url in rpc_endpoints:
            try:
                async with AsyncClient(rpc_url) as client:
                    # Try SPL Token program first
                    opts = TokenAccountOpts(mint=mint_pubkey, program_id=TOKEN_PROGRAM_ID)
                    accounts = await client.get_token_accounts_by_owner_json_parsed(wallet_pubkey, opts)
                    
                    if accounts.value:
                        for account in accounts.value:
                            info = account.account.data.parsed.get("info", {})
                            token_amount = info.get("tokenAmount", {})
                            token_balance = int(token_amount.get("amount", 0))
                            ui_amount = float(token_amount.get("uiAmount", 0) or 0)
                            decimals = int(token_amount.get("decimals", 9))
                    
                    # If no balance found, try Token-2022 program
                    if token_balance <= 0:
                        opts_2022 = TokenAccountOpts(mint=mint_pubkey, program_id=TOKEN_2022_PROGRAM_ID)
                        accounts_2022 = await client.get_token_accounts_by_owner_json_parsed(wallet_pubkey, opts_2022)
                        
                        if accounts_2022.value:
                            for account in accounts_2022.value:
                                info = account.account.data.parsed.get("info", {})
                                token_amount = info.get("tokenAmount", {})
                                token_balance = int(token_amount.get("amount", 0))
                                ui_amount = float(token_amount.get("uiAmount", 0) or 0)
                                decimals = int(token_amount.get("decimals", 9))
                    
                    # If we got a result, return it
                    if token_balance > 0 or accounts.value or accounts_2022.value:
                        break
                        
            except Exception as e:
                logger.warning(f"RPC {rpc_url[:30]}... failed for token balance: {e}")
                continue
        
        return {
            "wallet_address": wallet_address,
            "token_mint": token_mint,
            "raw_amount": token_balance,
            "amount": ui_amount,
            "decimals": decimals,
            "has_tokens": token_balance > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting token balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExecuteSellRequest(BaseModel):
    """Request to sell tokens from custodial wallet"""
    user_wallet: str
    token_mint: str
    token_amount: int  # Raw token amount (smallest units)
    position_id: Optional[str] = None


@router.get("/all-tokens/{user_wallet}")
async def get_all_token_holdings(user_wallet: str):
    """
    Get ALL token holdings in the custodial wallet.
    Fetches on-chain data and returns token balances with current prices.
    """
    from solana.rpc.types import TokenAccountOpts
    
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    custodial_address = wallet_doc["custodial_address"]
    
    try:
        TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        TOKEN_2022_PROGRAM_ID = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
        wallet_pubkey = Pubkey.from_string(custodial_address)
        
        holdings = []
        
        # Try multiple RPC endpoints for reliability
        rpc_endpoints = [
            os.environ.get("HELIUS_RPC_URL"),
            os.environ.get("ALCHEMY_RPC_URL"),
            os.environ.get("ALCHEMY_SOLANA_RPC"),
            "https://api.mainnet-beta.solana.com"
        ]
        rpc_endpoints = [r for r in rpc_endpoints if r]  # Filter None values
        
        last_error = None
        accounts_fetched = False
        
        for rpc_url in rpc_endpoints:
            try:
                async with AsyncClient(rpc_url) as client:
                    # Get all SPL token accounts
                    opts = TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
                    accounts = await client.get_token_accounts_by_owner_json_parsed(wallet_pubkey, opts)
                    
                    if accounts.value:
                        for account in accounts.value:
                            info = account.account.data.parsed.get("info", {})
                            mint = info.get("mint", "")
                            token_amount = info.get("tokenAmount", {})
                            raw_amount = int(token_amount.get("amount", 0))
                            ui_amount = float(token_amount.get("uiAmount", 0) or 0)
                            decimals = int(token_amount.get("decimals", 9))
                            
                            if raw_amount > 0:
                                holdings.append({
                                    "mint": mint,
                                    "raw_amount": raw_amount,
                                    "amount": ui_amount,
                                    "decimals": decimals,
                                    "program": "spl-token"
                                })
                    
                    # Get Token-2022 accounts
                    opts_2022 = TokenAccountOpts(program_id=TOKEN_2022_PROGRAM_ID)
                    accounts_2022 = await client.get_token_accounts_by_owner_json_parsed(wallet_pubkey, opts_2022)
                    
                    if accounts_2022.value:
                        for account in accounts_2022.value:
                            info = account.account.data.parsed.get("info", {})
                            mint = info.get("mint", "")
                            token_amount = info.get("tokenAmount", {})
                            raw_amount = int(token_amount.get("amount", 0))
                            ui_amount = float(token_amount.get("uiAmount", 0) or 0)
                            decimals = int(token_amount.get("decimals", 9))
                            
                            if raw_amount > 0:
                                holdings.append({
                                    "mint": mint,
                                    "raw_amount": raw_amount,
                                    "amount": ui_amount,
                                    "decimals": decimals,
                                    "program": "token-2022"
                                })
                    
                    accounts_fetched = True
                    break  # Success, exit loop
                    
            except Exception as e:
                last_error = e
                logger.warning(f"RPC {rpc_url[:30]}... failed: {e}")
                continue
        
        if not accounts_fetched:
            raise Exception(f"All RPC endpoints failed. Last error: {last_error}")
        
        # Fetch token info and prices from DexScreener
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            for holding in holdings:
                try:
                    response = await http_client.get(
                        f"https://api.dexscreener.com/latest/dex/tokens/{holding['mint']}"
                    )
                    if response.status_code == 200:
                        pairs = response.json().get("pairs", [])
                        if pairs:
                            # Get best liquidity pair
                            best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                            holding["symbol"] = best_pair.get("baseToken", {}).get("symbol", "UNKNOWN")
                            holding["name"] = best_pair.get("baseToken", {}).get("name", "Unknown Token")
                            holding["price_usd"] = float(best_pair.get("priceUsd", 0) or 0)
                            holding["liquidity_usd"] = float(best_pair.get("liquidity", {}).get("usd", 0) or 0)
                            holding["value_usd"] = holding["amount"] * holding["price_usd"]
                            holding["dex"] = best_pair.get("dexId", "unknown")
                except Exception as e:
                    logger.warning(f"Failed to get price for {holding['mint']}: {e}")
                    holding["symbol"] = "UNKNOWN"
                    holding["price_usd"] = 0
                    holding["value_usd"] = 0
        
        return {
            "custodial_address": custodial_address,
            "holdings": holdings,
            "count": len(holdings),
            "total_value_usd": sum(h.get("value_usd", 0) for h in holdings)
        }
        
    except Exception as e:
        logger.error(f"Error fetching all token holdings: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-positions/{user_wallet}")
async def sync_positions_from_chain(user_wallet: str):
    """
    Sync positions with actual on-chain token holdings.
    Creates new positions for tokens found on-chain that don't have positions.
    Marks positions as closed if tokens are no longer held.
    """
    from routers.ai_trader import db as ai_db
    
    try:
        # Get all on-chain holdings
        holdings_response = await get_all_token_holdings(user_wallet)
        holdings = holdings_response["holdings"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync positions failed to get holdings: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch on-chain holdings: {str(e)}")
    
    # Get existing positions (include pending states - they're still valid positions)
    existing_positions = await ai_db.ai_trader_positions.find({
        "wallet_address": user_wallet,
        "status": {"$in": ["open", "pending_stop_loss", "pending_take_profit"]}
    }).to_list(100)
    
    existing_mints = {p.get("token_mint") for p in existing_positions}
    on_chain_mints = {h["mint"] for h in holdings}
    
    synced = []
    created = []
    closed = []
    
    # Create positions for tokens found on-chain but not in database
    for holding in holdings:
        mint = holding["mint"]
        if mint not in existing_mints and holding.get("price_usd", 0) > 0:
            # Get SOL price using Jupiter API (more reliable)
            sol_price = 140  # Fallback
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Try Jupiter price API first
                    response = await client.get(
                        "https://price.jup.ag/v6/price?ids=SOL"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        sol_price = float(data.get("data", {}).get("SOL", {}).get("price", 140) or 140)
                    
                    if sol_price < 50 or sol_price > 500:  # Sanity check
                        # Fallback to CoinGecko
                        response = await client.get(
                            "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
                        )
                        if response.status_code == 200:
                            sol_price = float(response.json().get("solana", {}).get("usd", 140) or 140)
            except Exception as e:
                logger.warning(f"Failed to get SOL price: {e}, using fallback")
            
            logger.info(f"Using SOL price: ${sol_price}")
            
            position_value_usd = holding.get("value_usd", 0)
            amount_sol = position_value_usd / sol_price if sol_price > 0 else 0
            
            new_position = {
                "position_id": f"SYNC{uuid.uuid4().hex[:8].upper()}",
                "wallet_address": user_wallet,
                "token_symbol": holding.get("symbol", "UNKNOWN"),
                "token_name": holding.get("name", "Unknown Token"),
                "token_mint": mint,
                "amount_sol": round(amount_sol, 6),
                "amount_tokens": holding["amount"],
                "raw_amount_tokens": holding["raw_amount"],
                "entry_price": holding.get("price_usd", 0),  # Current price as entry (we don't have historical)
                "current_price": holding.get("price_usd", 0),
                "status": "open",
                "trade_type": "buy",
                "executed_on_chain": True,
                "synced_from_chain": True,
                "custodial": True,  # Mark as custodial wallet position
                "auto_trade": True,  # Enable auto-trade features
                "source": "custodial",  # Explicit source marking
                "decimals": holding["decimals"],
                "dex": holding.get("dex", "unknown"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "opened_at": datetime.now(timezone.utc).isoformat()
            }
            
            await ai_db.ai_trader_positions.insert_one(new_position)
            created.append({
                "symbol": holding.get("symbol"),
                "mint": mint,
                "amount": holding["amount"],
                "value_usd": position_value_usd
            })
    
    # Mark positions as closed if tokens no longer on-chain
    for position in existing_positions:
        mint = position.get("token_mint")
        if mint and mint not in on_chain_mints:
            await ai_db.ai_trader_positions.update_one(
                {"position_id": position.get("position_id")},
                {
                    "$set": {
                        "status": "closed_synced",
                        "closed_at": datetime.now(timezone.utc).isoformat(),
                        "close_reason": "Token no longer in wallet"
                    }
                }
            )
            closed.append({
                "symbol": position.get("token_symbol"),
                "position_id": position.get("position_id")
            })
    
    # Update existing positions with current on-chain amounts
    for position in existing_positions:
        mint = position.get("token_mint")
        if mint in on_chain_mints:
            holding = next((h for h in holdings if h["mint"] == mint), None)
            if holding:
                await ai_db.ai_trader_positions.update_one(
                    {"position_id": position.get("position_id")},
                    {
                        "$set": {
                            "amount_tokens": holding["amount"],
                            "raw_amount_tokens": holding["raw_amount"],
                            "current_price": holding.get("price_usd", 0),
                            "last_synced": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                synced.append({
                    "symbol": position.get("token_symbol"),
                    "position_id": position.get("position_id")
                })
    
    return {
        "success": True,
        "holdings_on_chain": len(holdings),
        "positions_created": len(created),
        "positions_synced": len(synced),
        "positions_closed": len(closed),
        "created": created,
        "synced": synced,
        "closed": closed
    }


@router.post("/execute-sell")
async def execute_sell(request: ExecuteSellRequest):
    """
    Execute a token sell from the custodial wallet.
    Swaps the specified token amount back to SOL.
    """
    SOL_MINT = "So11111111111111111111111111111111111111112"
    
    try:
        wallet_doc = await db.custodial_wallets.find_one({"user_wallet": request.user_wallet})
        if not wallet_doc:
            raise HTTPException(status_code=404, detail="Custodial wallet not found")
        
        custodial_address = wallet_doc["custodial_address"]
        
        # Check SOL balance for fees
        balance = await get_wallet_balance(custodial_address)
        min_fee_buffer = 3000000  # 0.003 SOL for fees
        if balance < min_fee_buffer:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient SOL for fees. Have: {balance/LAMPORTS_PER_SOL:.4f} SOL, Need: ~0.003 SOL"
            )
        
        # Get keypair
        keypair = await get_custodial_keypair(request.user_wallet)
        
        # Execute the swap: Token -> SOL
        result = await _execute_swap_with_retry(
            keypair=keypair,
            custodial_address=custodial_address,
            input_mint=request.token_mint,
            output_mint=SOL_MINT,
            amount_lamports=request.token_amount,
            user_wallet=request.user_wallet,
            max_retries=3
        )
        
        if result.get("success"):
            # Update position if provided
            if request.position_id:
                await db.ai_trader_positions.update_one(
                    {
                        "wallet_address": request.user_wallet,
                        "$or": [
                            {"position_id": request.position_id},
                            {"execution_id": request.position_id}
                        ]
                    },
                    {
                        "$set": {
                            "status": "closed_manual_sell",
                            "sell_tx_signature": result.get("tx_signature"),
                            "sell_executed_on_chain": True,
                            "closed_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
            
            return {
                "success": True,
                "tx_signature": result.get("tx_signature"),
                "received_sol": int(result.get("output_amount", 0) or 0) / LAMPORTS_PER_SOL
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Swap failed")
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute sell failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

async def execute_auto_trade(user_wallet: str, input_mint: str, output_mint: str, amount_lamports: int, is_stop_loss: bool = False) -> dict:
    """
    Execute a swap using the custodial wallet (called by auto-trade system).
    This function handles the actual trade execution for automated trading.
    
    For BUYS (SOL -> Token): amount_lamports is SOL amount to spend
    For SELLS (Token -> SOL): amount_lamports is the token amount in smallest units
    
    Args:
        is_stop_loss: If True, use higher slippage to ensure execution
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
        # For sells, only need SOL for transaction fees
        # Priority fees can be 0.0005-0.002 SOL, regular fee ~0.000005
        # Use 0.002 SOL as minimum - should cover most cases
        min_fee_buffer = 2000000  # 0.002 SOL for fees
        if balance < min_fee_buffer:
            # If we have SOME SOL, try anyway - Jupiter might succeed with lower fees
            if balance >= 500000:  # At least 0.0005 SOL
                logger.warning(f"Low SOL balance for fees ({balance/LAMPORTS_PER_SOL:.4f}), attempting anyway...")
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient SOL for fees. Have: {balance/LAMPORTS_PER_SOL:.4f} SOL, Need: ~0.002 SOL. Please deposit SOL to custodial wallet."
                )
    else:
        # For buys, check SOL balance covers the swap amount + fees + reserve for selling later
        # IMPORTANT: Always keep at least 0.005 SOL reserved for future sell transactions
        sell_fee_reserve = 5000000  # 0.005 SOL reserved for future sells
        min_required = amount_lamports + 50000 + sell_fee_reserve
        
        if balance < min_required:
            available_for_trade = max(0, balance - sell_fee_reserve - 50000)
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Have: {balance/LAMPORTS_PER_SOL:.4f} SOL, Available for trade: {available_for_trade/LAMPORTS_PER_SOL:.4f} SOL (keeping 0.005 SOL reserved for fees)"
            )
    
    # Get keypair
    keypair = await get_custodial_keypair(user_wallet)
    
    try:
        # Use regular swap with high priority fees and retry logic
        # For stop-loss/take-profit exits, use higher slippage to ensure execution
        return await _execute_swap_with_retry(
            keypair, custodial_address, input_mint, output_mint,
            amount_lamports, user_wallet, max_retries=3, is_stop_loss=is_stop_loss or is_sell
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
    max_retries: int = 3,
    is_stop_loss: bool = False
) -> dict:
    """
    Execute swap with retry logic using fresh blockhash each attempt.
    Uses progressive slippage on retries for better fill rates.
    Stop-loss trades use higher initial slippage to ensure execution.
    """
    import asyncio
    from solders.transaction import VersionedTransaction
    from solders.signature import Signature
    
    # Log which RPC we're using
    rpc_name = "Helius" if HELIUS_RPC_URL and HELIUS_RPC_URL in SOLANA_RPC_URL else "Alchemy"
    logger.info(f"Using {rpc_name} RPC for transaction submission")
    
    # Progressive slippage: increase with each retry
    # Stop-loss trades start with higher slippage to ensure execution
    base_slippage = 500 if is_stop_loss else 200  # 5% for SL, 2% for normal
    slippage_values = [base_slippage, base_slippage + 300, base_slippage + 700]  # Progressive increase
    
    last_error = None
    
    for retry in range(max_retries):
        try:
            current_slippage = slippage_values[min(retry, len(slippage_values) - 1)]
            logger.info(f"Swap attempt {retry + 1}/{max_retries} with slippage {current_slippage} bps ({current_slippage/100}%)")
            
            async with httpx.AsyncClient(timeout=45.0) as client:
                # Get fresh quote with progressive slippage
                quote_response = await client.get(
                    "https://lite-api.jup.ag/swap/v1/quote",
                    params={
                        "inputMint": input_mint,
                        "outputMint": output_mint,
                        "amount": str(amount_lamports),
                        "slippageBps": str(current_slippage)
                    }
                )
                
                if quote_response.status_code != 200:
                    raise Exception(f"Failed to get quote: {quote_response.text}")
                
                quote_data = quote_response.json()
                
                # Get swap transaction with auto priority fee for landing
                swap_response = await client.post(
                    "https://lite-api.jup.ag/swap/v1/swap",
                    json={
                        "quoteResponse": quote_data,
                        "userPublicKey": custodial_address,
                        "wrapAndUnwrapSol": True,
                        "dynamicComputeUnitLimit": True,
                        "prioritizationFeeLamports": "auto"  # Let Jupiter auto-optimize priority
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
                
                # === IMPROVEMENT 4: Try Jito bundle execution first for MEV protection ===
                jito_success = False
                try:
                    from services.jito_executor import send_transaction_with_jito
                    jito_result = await send_transaction_with_jito(
                        signed_tx_bytes,
                        is_stop_loss=is_stop_loss
                    )
                    if jito_result.get("success"):
                        tx_signature = jito_result["signature"]
                        jito_success = True
                        logger.info(f"Transaction sent via Jito: {tx_signature[:20]}...")
                except Exception as jito_err:
                    logger.warning(f"Jito execution failed, falling back to RPC: {jito_err}")
                
                if jito_success:
                    # Wait for confirmation (reduced timeout: 5 attempts × 2s = 10s max)
                    rpc_url = os.environ.get("HELIUS_RPC_URL") or "https://api.mainnet-beta.solana.com"
                    async with AsyncClient(rpc_url) as solana_client:
                        for attempt in range(5):
                            await asyncio.sleep(2)
                            try:
                                sig_obj = Signature.from_string(tx_signature)
                                tx_info = await solana_client.get_transaction(
                                    sig_obj,
                                    max_supported_transaction_version=0
                                )
                                if tx_info.value is not None:
                                    if tx_info.value.transaction.meta and tx_info.value.transaction.meta.err:
                                        raise Exception(f"Transaction failed: {tx_info.value.transaction.meta.err}")
                                    
                                    logger.info(f"Jito transaction CONFIRMED: {tx_signature}")
                                    await update_wallet_balance(user_wallet)
                                    return {
                                        "success": True,
                                        "tx_signature": tx_signature,
                                        "input_amount": amount_lamports,
                                        "output_amount": quote_data.get("outAmount"),
                                        "confirmed": True,
                                        "method": "jito_bundle",
                                        "retry_count": retry
                                    }
                            except Exception as e:
                                if "failed" in str(e).lower():
                                    raise
                                logger.debug(f"Jito confirmation check {attempt + 1}: {e}")
                        
                        logger.warning("Jito transaction not confirmed, falling back to standard RPC")
                
                # Fallback: Send via standard RPC endpoints
                rpc_endpoints_for_submit = [
                    os.environ.get("HELIUS_RPC_URL"),
                    os.environ.get("ALCHEMY_SOLANA_RPC"),
                    "https://api.mainnet-beta.solana.com"
                ]
                rpc_endpoints_for_submit = [r for r in rpc_endpoints_for_submit if r]
                
                tx_sent = False
                rpc_error = None
                
                for rpc_url in rpc_endpoints_for_submit:
                    try:
                        logger.info(f"Trying RPC: {rpc_url[:40]}...")
                        async with AsyncClient(rpc_url) as solana_client:
                            # Simulate first
                            try:
                                sim_result = await solana_client.simulate_transaction(signed_tx)
                                if sim_result.value.err:
                                    error_detail = str(sim_result.value.err)
                                    logger.error(f"Simulation failed on {rpc_url[:30]}: {error_detail}")
                                    rpc_error = error_detail
                                    continue  # Try next RPC
                            except Exception as sim_error:
                                logger.warning(f"Simulation exception on {rpc_url[:30]}: {sim_error}")
                                rpc_error = str(sim_error)
                                continue  # Try next RPC
                            
                            logger.info(f"Simulation passed (units: {sim_result.value.units_consumed})")
                            
                            # Send transaction
                            result = await solana_client.send_raw_transaction(
                                signed_tx_bytes,
                                opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed)
                            )
                            tx_signature = str(result.value)
                            tx_sent = True
                            
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
                            break  # Exit RPC loop, retry outer loop
                            
                    except Exception as rpc_e:
                        logger.warning(f"RPC {rpc_url[:30]} failed: {rpc_e}")
                        rpc_error = str(rpc_e)
                        continue
                
                if not tx_sent and rpc_error:
                    raise Exception(f"All RPCs failed. Last error: {rpc_error}")
        
        except Exception as e:
            last_error = str(e)
            if "simulation failed" in str(e).lower() or "transaction failed" in str(e).lower():
                # Don't retry on simulation/transaction failures
                raise
            logger.warning(f"Attempt {retry + 1} failed: {e}")
            
            if retry < max_retries - 1:
                await asyncio.sleep(2)  # Brief pause before retry
    
    raise Exception(f"All {max_retries} swap attempts failed. Last error: {last_error}")
