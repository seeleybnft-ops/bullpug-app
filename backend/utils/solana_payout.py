"""Solana transaction utilities for automatic payouts."""

import os
import logging
from typing import Optional, Tuple

import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
from solders.message import Message
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed

logger = logging.getLogger(__name__)

# Solana RPC endpoints
MAINNET_RPC = "https://api.mainnet-beta.solana.com"
DEVNET_RPC = "https://api.devnet.solana.com"

# Use mainnet for production
SOLANA_RPC_URL = MAINNET_RPC

# Lamports per SOL
LAMPORTS_PER_SOL = 1_000_000_000

# Solana transaction fee (base fee is 5000 lamports = 0.000005 SOL)
# Adding buffer for priority fees and potential increases
BASE_TX_FEE_LAMPORTS = 5000
TX_FEE_BUFFER_LAMPORTS = 5000  # Extra buffer for safety
TOTAL_TX_FEE_LAMPORTS = BASE_TX_FEE_LAMPORTS + TX_FEE_BUFFER_LAMPORTS  # 10000 lamports = 0.00001 SOL


def get_escrow_keypair() -> Optional[Keypair]:
    """Load the escrow wallet keypair from environment."""
    private_key_b58 = os.environ.get("ESCROW_PRIVATE_KEY")
    if not private_key_b58:
        logger.error("ESCROW_PRIVATE_KEY not set in environment")
        return None
    
    try:
        # Decode base58 private key
        secret_key = base58.b58decode(private_key_b58)
        keypair = Keypair.from_bytes(secret_key)
        logger.info(f"Escrow wallet loaded: {keypair.pubkey()}")
        return keypair
    except Exception as e:
        logger.error(f"Failed to load escrow keypair: {e}")
        return None


def get_escrow_pubkey() -> Optional[str]:
    """Get the escrow wallet public key."""
    keypair = get_escrow_keypair()
    if keypair:
        return str(keypair.pubkey())
    return None


async def send_sol_payout(
    recipient_wallet: str,
    amount_sol: float,
    memo: str = "Bullpug P2P Payout"
) -> Tuple[bool, str]:
    """
    Send SOL from escrow wallet to recipient.
    
    Args:
        recipient_wallet: Recipient's Solana wallet address (base58)
        amount_sol: Amount in SOL to send
        memo: Transaction memo/description
        
    Returns:
        Tuple of (success: bool, message: str with tx signature or error)
    """
    try:
        # Load escrow keypair
        escrow_keypair = get_escrow_keypair()
        if not escrow_keypair:
            return False, "Escrow wallet not configured"
        
        # Parse recipient address
        try:
            recipient_pubkey = Pubkey.from_string(recipient_wallet)
        except Exception as e:
            return False, f"Invalid recipient wallet address: {e}"
        
        # Convert SOL to lamports
        lamports = int(amount_sol * LAMPORTS_PER_SOL)
        if lamports <= 0:
            return False, "Amount must be positive"
        
        # Create Solana client
        client = Client(SOLANA_RPC_URL)
        
        # Check escrow balance first
        balance_resp = client.get_balance(escrow_keypair.pubkey())
        if balance_resp.value is None:
            return False, "Could not fetch escrow balance"
        
        escrow_balance = balance_resp.value
        # Need lamports + fee buffer (5000 lamports for transaction fee)
        required = lamports + 5000
        
        if escrow_balance < required:
            return False, f"Insufficient escrow balance. Have: {escrow_balance/LAMPORTS_PER_SOL:.6f} SOL, Need: {required/LAMPORTS_PER_SOL:.6f} SOL"
        
        # Get recent blockhash
        blockhash_resp = client.get_latest_blockhash()
        if blockhash_resp.value is None:
            return False, "Could not fetch recent blockhash"
        
        recent_blockhash = blockhash_resp.value.blockhash
        
        # Create transfer instruction
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=escrow_keypair.pubkey(),
                to_pubkey=recipient_pubkey,
                lamports=lamports
            )
        )
        
        # Build and sign transaction
        message = Message.new_with_blockhash(
            [transfer_ix],
            escrow_keypair.pubkey(),
            recent_blockhash
        )
        tx = Transaction.new_unsigned(message)
        tx.sign([escrow_keypair], recent_blockhash)
        
        # Send transaction
        tx_resp = client.send_transaction(tx)
        
        if tx_resp.value:
            tx_signature = str(tx_resp.value)
            logger.info(f"Payout sent! {amount_sol} SOL to {recipient_wallet}. TX: {tx_signature}")
            return True, tx_signature
        else:
            return False, "Transaction failed - no signature returned"
            
    except Exception as e:
        error_msg = f"Payout failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def get_escrow_balance() -> Optional[float]:
    """Get current escrow wallet balance in SOL."""
    try:
        keypair = get_escrow_keypair()
        if not keypair:
            return None
        
        client = Client(SOLANA_RPC_URL)
        balance_resp = client.get_balance(keypair.pubkey())
        
        if balance_resp.value is not None:
            return balance_resp.value / LAMPORTS_PER_SOL
        return None
    except Exception as e:
        logger.error(f"Failed to get escrow balance: {e}")
        return None
