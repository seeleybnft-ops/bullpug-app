"""
Rake withdrawal service — auto-transfers accumulated rake to community wallet.
Triggers when accumulated rake reaches 0.01 SOL threshold.
"""

import logging
import os
from datetime import datetime, timezone

from solders.pubkey import Pubkey
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
from solders.message import Message
from solana.rpc.async_api import AsyncClient

from utils.database import db

logger = logging.getLogger(__name__)

COMMUNITY_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"
RAKE_WITHDRAW_THRESHOLD = 0.01  # SOL
LAMPORTS_PER_SOL = 1_000_000_000


async def track_rake(wallet_address: str, rake_amount: float, position_id: str, symbol: str):
    """
    Record rake and trigger withdrawal if threshold is met.
    Called after every successful apply_rake().
    """
    if rake_amount <= 0:
        return

    # Upsert the tracker: increment pending_sol
    await db.rake_tracker.update_one(
        {"wallet_address": wallet_address},
        {
            "$inc": {"pending_sol": rake_amount, "total_collected_sol": rake_amount},
            "$setOnInsert": {"wallet_address": wallet_address, "created_at": datetime.now(timezone.utc).isoformat()},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
        upsert=True,
    )

    # Log individual rake event
    await db.rake_events.insert_one({
        "wallet_address": wallet_address,
        "amount_sol": rake_amount,
        "position_id": position_id,
        "symbol": symbol,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Check threshold
    tracker = await db.rake_tracker.find_one({"wallet_address": wallet_address}, {"_id": 0})
    pending = tracker.get("pending_sol", 0) if tracker else 0

    if pending >= RAKE_WITHDRAW_THRESHOLD:
        await _execute_rake_withdrawal(wallet_address, pending)


async def _execute_rake_withdrawal(wallet_address: str, amount_sol: float):
    """Transfer accumulated rake from custodial wallet to community wallet."""
    from routers.custodial_wallet import get_custodial_keypair

    try:
        keypair = await get_custodial_keypair(wallet_address)
        custodial_address = str(keypair.pubkey())

        amount_lamports = int(amount_sol * LAMPORTS_PER_SOL)

        # Leave 5000 lamports for tx fee
        send_lamports = amount_lamports - 5000
        if send_lamports <= 0:
            logger.warning(f"Rake withdrawal too small after fee: {amount_sol} SOL")
            return

        rpc_urls = [
            os.environ.get("HELIUS_RPC_URL"),
            os.environ.get("ALCHEMY_SOLANA_RPC", "https://api.mainnet-beta.solana.com"),
        ]
        rpc_urls = [r for r in rpc_urls if r]

        tx_signature = None
        for rpc_url in rpc_urls:
            try:
                async with AsyncClient(rpc_url) as client:
                    # Get recent blockhash
                    blockhash_resp = await client.get_latest_blockhash()
                    blockhash = blockhash_resp.value.blockhash

                    # Build transfer instruction
                    ix = transfer(TransferParams(
                        from_pubkey=keypair.pubkey(),
                        to_pubkey=Pubkey.from_string(COMMUNITY_WALLET),
                        lamports=send_lamports,
                    ))

                    msg = Message.new_with_blockhash([ix], keypair.pubkey(), blockhash)
                    tx = Transaction.new_unsigned(msg)
                    tx.sign([keypair], blockhash)

                    result = await client.send_transaction(tx)
                    tx_signature = str(result.value)
                    logger.info(f"Rake withdrawal TX: {tx_signature} ({amount_sol:.6f} SOL → {COMMUNITY_WALLET})")
                    break

            except Exception as rpc_err:
                logger.warning(f"Rake withdrawal RPC error ({rpc_url[:30]}...): {rpc_err}")
                continue

        if tx_signature:
            # Reset pending, log the withdrawal
            await db.rake_tracker.update_one(
                {"wallet_address": wallet_address},
                {"$set": {
                    "pending_sol": 0,
                    "last_withdrawal_at": datetime.now(timezone.utc).isoformat(),
                    "last_withdrawal_tx": tx_signature,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "$inc": {"total_withdrawn_sol": amount_sol, "withdrawal_count": 1}}
            )

            await db.rake_withdrawals.insert_one({
                "wallet_address": wallet_address,
                "amount_sol": round(amount_sol, 6),
                "send_lamports": send_lamports,
                "community_wallet": COMMUNITY_WALLET,
                "tx_signature": tx_signature,
                "custodial_address": custodial_address,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            logger.info(f"Rake withdrawal complete: {amount_sol:.6f} SOL → community wallet. TX: {tx_signature}")
        else:
            logger.error(f"Rake withdrawal failed: all RPCs failed for {amount_sol:.6f} SOL")

    except Exception as e:
        logger.error(f"Rake withdrawal error: {e}")


async def get_rake_stats(wallet_address: str) -> dict:
    """Get rake tracking stats for admin dashboard."""
    tracker = await db.rake_tracker.find_one({"wallet_address": wallet_address}, {"_id": 0})
    if not tracker:
        return {
            "total_collected_sol": 0,
            "total_withdrawn_sol": 0,
            "pending_sol": 0,
            "withdrawal_count": 0,
            "community_wallet": COMMUNITY_WALLET,
            "threshold_sol": RAKE_WITHDRAW_THRESHOLD,
        }

    recent_withdrawals = await db.rake_withdrawals.find(
        {"wallet_address": wallet_address}, {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)

    return {
        "total_collected_sol": round(tracker.get("total_collected_sol", 0), 6),
        "total_withdrawn_sol": round(tracker.get("total_withdrawn_sol", 0), 6),
        "pending_sol": round(tracker.get("pending_sol", 0), 6),
        "withdrawal_count": tracker.get("withdrawal_count", 0),
        "last_withdrawal_at": tracker.get("last_withdrawal_at"),
        "last_withdrawal_tx": tracker.get("last_withdrawal_tx"),
        "community_wallet": COMMUNITY_WALLET,
        "threshold_sol": RAKE_WITHDRAW_THRESHOLD,
        "recent_withdrawals": recent_withdrawals,
    }
