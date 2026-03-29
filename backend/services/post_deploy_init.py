"""
Post-deploy database initialization.

Ensures the correct custodial wallet (CFzZRc76y...) is present in the
production database. Also seeds position records from known on-chain
token holdings when RPC-based sync is unavailable.

The deposit detection fix in custodial_wallet.py handles reconciliation.
"""

import logging
import uuid
import os
import httpx
from datetime import datetime, timezone
from utils.database import db

logger = logging.getLogger(__name__)

CORRECT_WALLET = "CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg"
OLD_LOST_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"
USER_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"

CORRECT_WALLET_DOC = {
    "user_wallet": USER_WALLET,
    "custodial_address": CORRECT_WALLET,
    "encrypted_private_key": "Z0FBQUFBQnB4WjRETXlJN0F1U3A2N2UwNWVKRmNTSktEUk5EeGJETF9uMTNESW9KbXYwUWduYVJMUEN1Y2hkXzBxVGh4OUh3bXVkaHZKVWVfWmEyYTE5dml4SF9XSWNaXzdCMlR4TnJselp2dklqTUk2dlYxcXR6S21SRW45dl9XaUZFOVFZTXR6cVBBSk40QWFrNWRQeFlkSTZ0MzhIRnB5eHJiNG9Da3FuMzhqcEg3WmxySmlVPQ==",
    "balance_lamports": 0,
    "created_at": "2026-03-26T20:58:43.758196+00:00",
    "last_activity": "2026-03-27T10:30:00.000000+00:00",
    "total_deposits_lamports": 0,
    "total_withdrawals_lamports": 0,
    "transaction_history": []
}

# Known token symbols for mints the bot has traded
KNOWN_MINTS = {
    "hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux": "HNT",
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL": "JTO",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "JUP",
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": "PYTH",
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": "WIF",
    "34q2KmCvapecJgR6ZrtbCTrzZVtkt3a5mHEA3TuEsWYb": "LOL",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
    "H43xqMLiFLNLLGRhXKxJUVXdEe8uVdXs93Emo5Wzpump": "PIXEL",
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof": "RNDR",
    "DriFtupJYLTosbwoN8koMbEYSx54aFAVLddWsbksjwg7": "DRIFT",
}


async def _fetch_onchain_tokens():
    """Query both Token programs via RPC to discover all on-chain holdings."""
    # Try Alchemy first (more reliable on production), then Helius
    rpc_urls = [
        os.environ.get("ALCHEMY_RPC_URL", ""),
        os.environ.get("HELIUS_RPC_URL", ""),
    ]
    rpc_urls = [u for u in rpc_urls if u]

    TOKEN_PROGRAMS = [
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
    ]

    tokens = {}
    for rpc_url in rpc_urls:
        if tokens:
            break
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for pid in TOKEN_PROGRAMS:
                    resp = await client.post(rpc_url, json={
                        "jsonrpc": "2.0", "id": 1,
                        "method": "getTokenAccountsByOwner",
                        "params": [
                            CORRECT_WALLET,
                            {"programId": pid},
                            {"encoding": "jsonParsed"}
                        ]
                    })
                    data = resp.json()
                    if "error" in data:
                        logger.warning(f"RPC error ({rpc_url[:30]}): {data['error']}")
                        continue
                    for acc in data.get("result", {}).get("value", []):
                        info = acc["account"]["data"]["parsed"]["info"]
                        mint = info["mint"]
                        ui_amount = info["tokenAmount"].get("uiAmount", 0)
                        if ui_amount and ui_amount > 0:
                            tokens[mint] = ui_amount
        except Exception as e:
            logger.warning(f"RPC exception ({rpc_url[:30]}): {e}")
    return tokens


async def _sync_positions_from_chain():
    """
    Ensure open positions in DB match on-chain token holdings.
    Runs on startup: creates missing positions, closes stale ones, updates amounts.
    """
    # Check if there are already correct positions
    existing = await db.ai_trader_positions.find(
        {"wallet_address": USER_WALLET, "status": {"$in": ["open", "pending_stop_loss", "pending_take_profit"]}},
        {"_id": 0, "token_mint": 1, "position_id": 1}
    ).to_list(100)

    onchain = await _fetch_onchain_tokens()
    if not onchain:
        logger.warning("Position sync: could not fetch on-chain tokens (RPC unavailable)")
        if not existing:
            logger.warning("Position sync: no positions in DB and no RPC. Positions will be missing until sync works.")
        return

    existing_mints = set(p.get("token_mint") for p in existing)
    now = datetime.now(timezone.utc).isoformat()

    # Close stale positions (in DB but 0 on-chain)
    for pos in existing:
        mint = pos.get("token_mint")
        if mint and mint not in onchain:
            await db.ai_trader_positions.update_one(
                {"position_id": pos["position_id"]},
                {"$set": {"status": "closed_sync", "closed_at": now, "close_reason": "Zero balance on-chain (startup sync)"}}
            )
            logger.info(f"  Closed stale position: {mint[:16]}...")

    # Update amounts for existing positions
    for pos in existing:
        mint = pos.get("token_mint")
        if mint and mint in onchain:
            await db.ai_trader_positions.update_one(
                {"position_id": pos["position_id"]},
                {"$set": {"token_amount": onchain[mint], "amount_tokens": onchain[mint], "updated_at": now}}
            )

    # Create missing positions — fetch prices from DexScreener
    missing = set(onchain.keys()) - existing_mints
    for mint in missing:
        symbol = KNOWN_MINTS.get(mint, mint[:8])
        price = 0
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{mint}")
                pairs = resp.json().get("pairs", [])
                if pairs:
                    price = float(pairs[0].get("priceUsd", 0) or 0)
                    if symbol == mint[:8]:
                        symbol = pairs[0].get("baseToken", {}).get("symbol", symbol)
        except Exception:
            pass

        # CRITICAL: entry_price MUST be > 0 to prevent auto-TP at $0
        entry_price = price if price > 0 else 0
        auto_trade_flag = price > 0

        doc = {
            "position_id": str(uuid.uuid4()),
            "wallet_address": USER_WALLET,
            "token_symbol": symbol,
            "token_mint": mint,
            "entry_price": entry_price,
            "current_price": entry_price,
            "amount_sol": 0,
            "token_amount": onchain[mint],
            "amount_tokens": onchain[mint],
            "status": "open",
            "auto_trade": auto_trade_flag,
            "synced_from_chain": True,
            "take_profit_pct": 20.0,
            "stop_loss_pct": -10.0,
            "trailing_stop_enabled": False,
            "created_at": now,
            "updated_at": now,
        }
        await db.ai_trader_positions.insert_one(doc)
        logger.info(f"  Created position: {symbol} ({onchain[mint]} tokens, entry=${entry_price:.8f})")

    total = len(onchain)
    logger.info(f"Position sync complete: {total} on-chain, {len(missing)} created, {len(existing_mints) - len(existing_mints & set(onchain.keys()))} closed")


async def run_post_deploy_init():
    """
    Idempotent. Ensures wallet, telegram, and positions are correctly set up.
    """
    correct = await db.custodial_wallets.find_one(
        {"custodial_address": CORRECT_WALLET}, {"_id": 1}
    )
    if not correct:
        logger.info("Post-deploy init: correct wallet NOT found — replacing wallet only...")
        try:
            await db.custodial_wallets.delete_many({"user_wallet": USER_WALLET})
            await db.custodial_wallets.insert_one(CORRECT_WALLET_DOC.copy())
            logger.info(f"  Wallet replaced: {CORRECT_WALLET}")
        except Exception as e:
            logger.error(f"  CRITICAL: wallet replacement failed: {e}")
            return

        # Seed telegram linkage only if missing
        tg_exists = await db.telegram_accounts.count_documents(
            {"wallet_address": USER_WALLET, "active": True}
        )
        if tg_exists == 0:
            await db.telegram_accounts.insert_one({
                "wallet_address": USER_WALLET,
                "chat_id": 6118851473,
                "telegram_username": "Seeleyb",
                "active": True,
                "alerts_enabled": True,
                "linked_at": "2026-03-15T00:03:55.414683+00:00"
            })
            logger.info("  Telegram linkage seeded for @Seeleyb")
    else:
        logger.info("Post-deploy init: correct wallet CFzZRc76y found — skipping wallet seed.")

    # Always sync positions on startup
    try:
        await _sync_positions_from_chain()
    except Exception as e:
        logger.warning(f"Position sync failed (non-fatal): {e}")

    logger.info("Post-deploy init COMPLETE.")


async def force_seed():
    """
    Force-replace ONLY the custodial wallet. Does NOT touch ledger or positions.
    """
    logger.info("Force seed: replacing custodial wallet only...")
    await db.custodial_wallets.delete_many({"user_wallet": USER_WALLET})
    await db.custodial_wallets.insert_one(CORRECT_WALLET_DOC.copy())
    logger.info(f"  Wallet set: {CORRECT_WALLET}")
    return {"success": True, "wallet": CORRECT_WALLET, "note": "Wallet replaced. Open Fund Ledger to trigger deposit reconciliation."}
