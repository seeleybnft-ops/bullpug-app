"""
Custodial Wallet Management for Auto-Trading
Provides secure, encrypted hot wallet functionality for automated trade execution.
"""

import os
import base64
import logging
from datetime import datetime, timezone
from typing import Optional
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
SOLANA_RPC_URL = os.environ.get("ALCHEMY_RPC_URL", "https://api.mainnet-beta.solana.com")

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
            except:
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
    """
    
    wallet_doc = await db.custodial_wallets.find_one({"user_wallet": user_wallet})
    if not wallet_doc:
        raise HTTPException(status_code=404, detail="Custodial wallet not found")
    
    # Check balance
    custodial_address = wallet_doc["custodial_address"]
    balance = await get_wallet_balance(custodial_address)
    
    if balance < amount_lamports + 50000:  # Need some extra for fees
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient custodial balance. Have: {balance/LAMPORTS_PER_SOL:.4f} SOL, Need: {amount_lamports/LAMPORTS_PER_SOL:.4f} SOL"
        )
    
    # Get keypair
    keypair = await get_custodial_keypair(user_wallet)
    
    try:
        # Get quote from Jupiter lite API
        async with httpx.AsyncClient(timeout=30.0) as client:
            quote_url = "https://lite-api.jup.ag/swap/v1/quote"
            quote_params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount_lamports),
                "slippageBps": "100"  # 1% slippage
            }
            
            quote_response = await client.get(quote_url, params=quote_params)
            if quote_response.status_code != 200:
                raise Exception(f"Failed to get quote: {quote_response.text}")
            
            quote_data = quote_response.json()
            
            # Get swap transaction with priority fees for faster confirmation
            # Lite API supports priorityFee parameter
            swap_url = "https://lite-api.jup.ag/swap/v1/swap"
            swap_payload = {
                "quoteResponse": quote_data,
                "userPublicKey": custodial_address,
                "wrapAndUnwrapSol": True,
                "computeUnitPriceMicroLamports": 100000,  # 0.0001 SOL per CU - high priority
                "dynamicComputeUnitLimit": True  # Let Jupiter optimize compute units
            }
            
            swap_response = await client.post(swap_url, json=swap_payload)
            if swap_response.status_code != 200:
                raise Exception(f"Failed to get swap transaction: {swap_response.text}")
            
            swap_data = swap_response.json()
            swap_transaction = swap_data.get("swapTransaction")
            
            if not swap_transaction:
                raise Exception("No swap transaction returned")
            
            # Decode the transaction
            tx_bytes = base64.b64decode(swap_transaction)
            
            # Sign and send to Solana
            async with AsyncClient(SOLANA_RPC_URL) as solana_client:
                # Jupiter returns a versioned transaction that needs our signature
                from solders.transaction import VersionedTransaction
                from solders.signature import Signature
                
                # Deserialize the versioned transaction
                unsigned_tx = VersionedTransaction.from_bytes(tx_bytes)
                
                # Log transaction details for debugging
                logger.info(f"Transaction has {len(unsigned_tx.signatures)} signature slots")
                logger.info(f"Our pubkey: {keypair.pubkey()}")
                
                # Sign the message with our keypair
                message_bytes = bytes(unsigned_tx.message)
                signature = keypair.sign_message(message_bytes)
                
                # Create signed versioned transaction using populate
                signed_tx = VersionedTransaction.populate(unsigned_tx.message, [signature])
                
                # Serialize to bytes and send via send_raw_transaction
                signed_tx_bytes = bytes(signed_tx)
                
                logger.info(f"Sending transaction ({len(signed_tx_bytes)} bytes)...")
                
                # First simulate to check for errors
                try:
                    sim_result = await solana_client.simulate_transaction(signed_tx)
                    if sim_result.value.err:
                        logger.error(f"Transaction simulation failed: {sim_result.value.err}")
                        if sim_result.value.logs:
                            logger.error(f"Simulation logs: {sim_result.value.logs[-5:]}")
                        raise Exception(f"Transaction simulation failed: {sim_result.value.err}")
                    logger.info("Transaction simulation passed")
                except Exception as sim_error:
                    if "simulation failed" not in str(sim_error).lower():
                        logger.warning(f"Could not simulate transaction: {sim_error}")
                    else:
                        raise
                
                # Send with skip_confirmation=True for faster response
                try:
                    result = await solana_client.send_raw_transaction(
                        signed_tx_bytes,
                        opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed)
                    )
                    tx_signature = str(result.value)
                except Exception as send_error:
                    # If send fails, log the error
                    error_str = str(send_error)
                    logger.error(f"Send transaction error: {error_str}")
                    raise Exception(f"Transaction send failed: {error_str}")
                
                if not tx_signature or tx_signature == "1111111111111111111111111111111111111111111111111111111111111111":
                    raise Exception("Invalid transaction signature returned")
                
                logger.info(f"Auto-trade submitted: {tx_signature} (wallet: {str(keypair.pubkey())[:8]}...)")
                
                # Wait for confirmation with retries (Solana can be slow)
                import asyncio
                confirmed = False
                max_retries = 6  # Increased to 18 seconds total
                
                for attempt in range(max_retries):
                    await asyncio.sleep(3)  # Wait 3s between checks
                    
                    try:
                        sig_obj = Signature.from_string(tx_signature)
                        tx_info = await solana_client.get_transaction(
                            sig_obj,
                            max_supported_transaction_version=0
                        )
                        if tx_info.value is not None:
                            if tx_info.value.transaction.meta and tx_info.value.transaction.meta.err:
                                raise Exception(f"Transaction failed on-chain: {tx_info.value.transaction.meta.err}")
                            else:
                                logger.info(f"Auto-trade CONFIRMED on-chain (attempt {attempt + 1}): {tx_signature[:20]}...")
                                confirmed = True
                                break
                        else:
                            logger.info(f"Transaction not found yet (attempt {attempt + 1}/{max_retries})")
                    except Exception as verify_error:
                        if "failed" in str(verify_error).lower():
                            raise  # Transaction explicitly failed
                        logger.debug(f"Verification attempt {attempt + 1} error: {verify_error}")
                
                if not confirmed:
                    # Transaction did not land - this is a FAILURE, not success
                    logger.error(f"Transaction {tx_signature[:20]}... NOT confirmed after {max_retries * 3}s - marking as FAILED")
                    raise Exception(f"Transaction not confirmed on-chain after {max_retries * 3}s: {tx_signature}")
                
                # Update balance only if confirmed
                await update_wallet_balance(user_wallet)
                
                return {
                    "success": True,
                    "tx_signature": tx_signature,
                    "input_amount": amount_lamports,
                    "output_amount": quote_data.get("outAmount"),
                    "price_impact": quote_data.get("priceImpactPct"),
                    "confirmed": True
                }
                
    except Exception as e:
        logger.error(f"Auto-trade execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")
