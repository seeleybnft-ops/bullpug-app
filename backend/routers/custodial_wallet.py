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
            logger.info(f"Balance for {address}: {response.value} lamports")
            return response.value
    except Exception as e:
        logger.error(f"Failed to get balance for {address}: {type(e).__name__}: {e}")
        # Try fallback RPC
        try:
            fallback_rpc = os.environ.get("ALCHEMY_SOLANA_RPC", "https://api.mainnet-beta.solana.com")
            async with AsyncClient(fallback_rpc) as fallback_client:
                response = await fallback_client.get_balance(Pubkey.from_string(address))
                logger.info(f"Fallback balance for {address}: {response.value} lamports")
                return response.value
        except Exception as fallback_e:
            logger.error(f"Fallback balance also failed for {address}: {type(fallback_e).__name__}: {fallback_e}")
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
    
    # Get existing positions
    existing_positions = await ai_db.ai_trader_positions.find({
        "wallet_address": user_wallet,
        "status": "open"
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
                
                # Send via RPC - try multiple endpoints
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
