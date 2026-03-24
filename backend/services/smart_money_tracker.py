"""
Smart Money Tracker

Monitors known profitable Solana wallets (whales, smart traders) for their
trading activity. When smart money is detected buying or selling a token,
it provides a signal boost or reduction to the trading bot's confidence.

Uses Helius API for transaction parsing.
"""
import os
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from utils.database import db

logger = logging.getLogger(__name__)

# Extract Helius API key from RPC URL
HELIUS_RPC_URL = os.environ.get("HELIUS_RPC_URL", "")
HELIUS_API_KEY = ""
if "api-key=" in HELIUS_RPC_URL:
    HELIUS_API_KEY = HELIUS_RPC_URL.split("api-key=")[-1]

# Known smart money wallets on Solana (curated list of profitable traders)
# These are well-known whale/fund wallets tracked by the community
SMART_MONEY_WALLETS = [
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",  # Raydium Authority
    "HWHvQhFmJB3NUcu1aihKmrKegfVxBEHzwVX6yZCKEsi1",  # Known whale
    "CuieVDEDtLo7FypA9SbLM9saXFdb1dsshEkyErMqkRQq",  # DeFi whale
    "7Ppgch9d4nQi5rzrLHnoi5cLJhGSEsFEWkTitimkAfAQ",  # Memecoin whale
    "FGJMvEsmBFAhh5Rpr3ZWF6SKYPLDvXcH6YDYv6GEsRwt",  # Smart trader
]

# Jupiter program IDs for swap detection
JUPITER_PROGRAM_IDS = [
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",  # Jupiter v6
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",  # Jupiter v4
]

# SOL mint for reference
SOL_MINT = "So11111111111111111111111111111111111111112"

# Cache duration for smart money signals (minutes)
SIGNAL_CACHE_MINUTES = 30


async def fetch_wallet_transactions(wallet_address: str, limit: int = 20) -> List[Dict]:
    """
    Fetch recent transactions for a wallet using Helius enhanced RPC.
    Uses the RPC URL directly (not REST API) for compatibility.
    """
    rpc_url = os.environ.get("HELIUS_RPC_URL", "")
    if not rpc_url:
        logger.warning("No Helius RPC URL available for smart money tracking")
        return []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: Get recent signatures
            sig_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [wallet_address, {"limit": limit}]
            }
            sig_response = await client.post(rpc_url, json=sig_payload)
            if sig_response.status_code != 200:
                return []

            sigs_data = sig_response.json().get("result", [])
            if not sigs_data:
                return []

            # Step 2: Fetch parsed transactions for recent signatures
            transactions = []
            for sig_info in sigs_data[:10]:  # Limit to 10 most recent
                sig = sig_info.get("signature")
                if not sig:
                    continue

                tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
                }

                tx_response = await client.post(rpc_url, json=tx_payload)
                if tx_response.status_code != 200:
                    continue

                tx_data = tx_response.json().get("result")
                if not tx_data:
                    continue

                # Parse the transaction into our expected format
                block_time = tx_data.get("blockTime", 0)
                meta = tx_data.get("meta", {})

                # Detect swaps by looking at token balance changes
                pre_token_balances = meta.get("preTokenBalances", [])
                post_token_balances = meta.get("postTokenBalances", [])

                # Simple swap detection: look for SOL + token balance changes
                pre_sol = meta.get("preBalances", [0])[0] if meta.get("preBalances") else 0
                post_sol = meta.get("postBalances", [0])[0] if meta.get("postBalances") else 0
                sol_change = (post_sol - pre_sol) / 1e9

                token_changes = {}
                for post_bal in post_token_balances:
                    mint = post_bal.get("mint", "")
                    if mint == SOL_MINT:
                        continue
                    owner = post_bal.get("owner", "")
                    post_amount = float(post_bal.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)

                    pre_amount = 0
                    for pre_bal in pre_token_balances:
                        if pre_bal.get("mint") == mint and pre_bal.get("owner") == owner:
                            pre_amount = float(pre_bal.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
                            break

                    change = post_amount - pre_amount
                    if abs(change) > 0:
                        token_changes[mint] = {"amount": change, "owner": owner}

                if not token_changes:
                    continue

                # Build a simplified transaction object
                parsed_tx = {
                    "signature": sig,
                    "timestamp": block_time,
                    "type": "SWAP" if token_changes and abs(sol_change) > 0.01 else "TRANSFER",
                    "source": "UNKNOWN",
                    "sol_change": sol_change,
                    "token_changes": token_changes,
                    "nativeTransfers": [],
                    "tokenTransfers": []
                }

                # Build tokenTransfers
                for mint, data in token_changes.items():
                    if data["amount"] > 0:
                        parsed_tx["tokenTransfers"].append({
                            "mint": mint,
                            "tokenAmount": data["amount"],
                            "toUserAccount": wallet_address
                        })
                    else:
                        parsed_tx["tokenTransfers"].append({
                            "mint": mint,
                            "tokenAmount": abs(data["amount"]),
                            "fromUserAccount": wallet_address
                        })

                # Build nativeTransfers
                if sol_change < -0.01:
                    parsed_tx["nativeTransfers"].append({
                        "fromUserAccount": wallet_address,
                        "amount": abs(sol_change) * 1e9
                    })
                elif sol_change > 0.01:
                    parsed_tx["nativeTransfers"].append({
                        "toUserAccount": wallet_address,
                        "amount": sol_change * 1e9
                    })

                transactions.append(parsed_tx)

            return transactions

    except Exception as e:
        logger.warning(f"Failed to fetch transactions for {wallet_address[:8]}...: {e}")
        return []


def parse_swap_from_transaction(tx: Dict) -> Optional[Dict]:
    """
    Parse a Helius transaction to detect token swaps.
    Returns swap details if detected, None otherwise.
    """
    tx_type = tx.get("type", "")
    source = tx.get("source", "")

    # Check if it's a swap transaction
    if tx_type != "SWAP" and source not in ["JUPITER", "RAYDIUM", "ORCA"]:
        return None

    # Extract token transfers
    token_transfers = tx.get("tokenTransfers", [])
    native_transfers = tx.get("nativeTransfers", [])

    if not token_transfers and not native_transfers:
        return None

    # Determine buy/sell direction
    # If SOL goes out and tokens come in = BUY
    # If tokens go out and SOL comes in = SELL
    sol_out = 0
    sol_in = 0
    token_in = None
    token_out = None

    for nt in native_transfers:
        if nt.get("fromUserAccount") in SMART_MONEY_WALLETS:
            sol_out += nt.get("amount", 0) / 1e9  # lamports to SOL
        if nt.get("toUserAccount") in SMART_MONEY_WALLETS:
            sol_in += nt.get("amount", 0) / 1e9

    for tt in token_transfers:
        mint = tt.get("mint", "")
        if mint == SOL_MINT:
            continue
        amount = tt.get("tokenAmount", 0)
        if tt.get("toUserAccount") in SMART_MONEY_WALLETS or \
           tx.get("feePayer") in SMART_MONEY_WALLETS:
            if amount > 0:
                token_in = {"mint": mint, "amount": amount}
        if tt.get("fromUserAccount") in SMART_MONEY_WALLETS:
            if amount > 0:
                token_out = {"mint": mint, "amount": amount}

    # Determine action
    if sol_out > 0.01 and token_in:
        return {
            "action": "buy",
            "token_mint": token_in["mint"],
            "token_amount": token_in["amount"],
            "sol_amount": sol_out,
            "source": source,
            "signature": tx.get("signature"),
            "timestamp": tx.get("timestamp"),
            "block_time": tx.get("timestamp")
        }
    elif token_out and sol_in > 0.01:
        return {
            "action": "sell",
            "token_mint": token_out["mint"],
            "token_amount": token_out["amount"],
            "sol_amount": sol_in,
            "source": source,
            "signature": tx.get("signature"),
            "timestamp": tx.get("timestamp"),
            "block_time": tx.get("timestamp")
        }

    return None


async def scan_smart_money_activity():
    """
    Scan all tracked smart money wallets for recent trading activity.
    Stores detected signals in MongoDB.
    """
    now = datetime.now(timezone.utc)
    # Only look at transactions from the last hour
    cutoff_ts = int((now - timedelta(hours=1)).timestamp())
    signals_found = 0

    for wallet in SMART_MONEY_WALLETS:
        try:
            txns = await fetch_wallet_transactions(wallet, limit=15)

            for tx in txns:
                tx_time = tx.get("timestamp", 0)
                if tx_time < cutoff_ts:
                    continue

                swap = parse_swap_from_transaction(tx)
                if not swap:
                    continue

                # Check if we already logged this signal
                existing = await db.smart_money_signals.find_one({
                    "signature": swap["signature"]
                })
                if existing:
                    continue

                # Store the signal
                signal_doc = {
                    "wallet_address": wallet,
                    "wallet_label": f"whale_{wallet[:6]}",
                    "action": swap["action"],
                    "token_mint": swap["token_mint"],
                    "token_amount": swap["token_amount"],
                    "sol_amount": swap["sol_amount"],
                    "source": swap["source"],
                    "signature": swap["signature"],
                    "block_time": swap.get("block_time"),
                    "detected_at": now.isoformat(),
                    "expires_at": (now + timedelta(minutes=SIGNAL_CACHE_MINUTES)).isoformat()
                }

                await db.smart_money_signals.insert_one(signal_doc)
                signals_found += 1
                logger.info(
                    f"Smart money signal: {swap['action'].upper()} {swap['token_mint'][:8]}... "
                    f"({swap['sol_amount']:.2f} SOL) by whale {wallet[:8]}..."
                )

        except Exception as e:
            logger.warning(f"Error scanning wallet {wallet[:8]}...: {e}")

    if signals_found > 0:
        logger.info(f"Smart money scanner: found {signals_found} new signals")
    return signals_found


async def get_smart_money_signal(token_mint: str) -> Dict:
    """
    Get aggregated smart money signal for a specific token.

    Returns:
        Dict with 'action' (buy/sell/neutral), 'strength' (0-1),
        'whale_count', 'total_sol', and 'details'.
    """
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=SIGNAL_CACHE_MINUTES)).isoformat()

    # Get recent signals for this token
    signals = await db.smart_money_signals.find(
        {
            "token_mint": token_mint,
            "detected_at": {"$gte": cutoff}
        },
        {"_id": 0}
    ).to_list(50)

    if not signals:
        return {
            "action": "neutral",
            "strength": 0.0,
            "whale_count": 0,
            "total_sol": 0,
            "buy_count": 0,
            "sell_count": 0,
            "details": []
        }

    buys = [s for s in signals if s["action"] == "buy"]
    sells = [s for s in signals if s["action"] == "sell"]

    buy_sol = sum(s.get("sol_amount", 0) for s in buys)
    sell_sol = sum(s.get("sol_amount", 0) for s in sells)
    total_sol = buy_sol + sell_sol

    unique_wallets = len(set(s["wallet_address"] for s in signals))

    # Determine action and strength
    if buy_sol > sell_sol * 1.5:
        action = "buy"
        strength = min(1.0, (buy_sol - sell_sol) / max(total_sol, 1) * unique_wallets * 0.3)
    elif sell_sol > buy_sol * 1.5:
        action = "sell"
        strength = min(1.0, (sell_sol - buy_sol) / max(total_sol, 1) * unique_wallets * 0.3)
    else:
        action = "neutral"
        strength = 0.0

    return {
        "action": action,
        "strength": round(strength, 3),
        "whale_count": unique_wallets,
        "total_sol": round(total_sol, 2),
        "buy_count": len(buys),
        "sell_count": len(sells),
        "buy_sol": round(buy_sol, 2),
        "sell_sol": round(sell_sol, 2),
        "details": [
            {
                "wallet": s["wallet_address"][:8] + "...",
                "action": s["action"],
                "sol": round(s.get("sol_amount", 0), 2),
                "time": s.get("detected_at")
            }
            for s in signals[:5]
        ]
    }


async def get_confidence_adjustment(token_mint: str) -> float:
    """
    Get a confidence adjustment based on smart money activity.

    Returns:
        Float between -0.15 and +0.15
        Positive = smart money is buying (confidence boost)
        Negative = smart money is selling (confidence reduction)
    """
    signal = await get_smart_money_signal(token_mint)

    if signal["action"] == "buy":
        # Max +15% boost for strong buy signal from multiple whales
        return min(0.15, signal["strength"] * 0.15)
    elif signal["action"] == "sell":
        # Max -15% reduction for strong sell signal
        return max(-0.15, -signal["strength"] * 0.15)

    return 0.0


async def cleanup_expired_signals():
    """Remove expired smart money signals."""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.smart_money_signals.delete_many({"expires_at": {"$lt": now}})
    if result.deleted_count > 0:
        logger.info(f"Cleaned up {result.deleted_count} expired smart money signals")
