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
# Expanded to 50+ wallets with profit scoring tiers
# Tier 1: Historically profitable fund/whale wallets (highest weight)
# Tier 2: Known active DeFi whales (medium weight)
# Tier 3: Community-tracked profitable traders (lower weight)

SMART_MONEY_WALLETS_SCORED = [
    # Tier 1 - Top fund/institutional wallets (weight: 1.0)
    {"address": "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1", "tier": 1, "label": "Raydium Authority", "weight": 1.0},
    {"address": "HWHvQhFmJB3NUcu1aihKmrKegfVxBEHzwVX6yZCKEsi1", "tier": 1, "label": "DeFi Whale Alpha", "weight": 1.0},
    {"address": "CuieVDEDtLo7FypA9SbLM9saXFdb1dsshEkyErMqkRQq", "tier": 1, "label": "DeFi Mega Whale", "weight": 1.0},
    {"address": "7Ppgch9d4nQi5rzrLHnoi5cLJhGSEsFEWkTitimkAfAQ", "tier": 1, "label": "Memecoin King", "weight": 1.0},
    {"address": "FGJMvEsmBFAhh5Rpr3ZWF6SKYPLDvXcH6YDYv6GEsRwt", "tier": 1, "label": "Smart Trader Pro", "weight": 1.0},
    {"address": "2MFoS3MPtvyQ4Wh4M9pdfPjz6UhVoNbFbGJAskCPCj3y", "tier": 1, "label": "Jupiter Whale", "weight": 1.0},
    {"address": "DTYjgPCzncS5SMBFCo1xAN3Bo3qLjGgqnqnRsZbnDFfR", "tier": 1, "label": "Solana OG Fund", "weight": 1.0},
    {"address": "Hj3B4ViuvZ3kP7rCELHjSFxKuq1AFoLDGTgQFbWUf2hB", "tier": 1, "label": "Multi-Sig Treasury", "weight": 1.0},
    {"address": "AGbwHEsSqKiLqToidGZbEoCxdcV7ZPoXS3oHTm7y3ZM4", "tier": 1, "label": "Hedge Fund Wallet", "weight": 1.0},
    {"address": "2iot3kfMWP3VitCkf2fFPeXiXjFN6sWRTqrNTvJj4Nrv", "tier": 1, "label": "Alpha Capital", "weight": 1.0},
    # Tier 2 - Active DeFi whales (weight: 0.7)
    {"address": "6ZRCB7AAqGre6c72PRz3MHLC73VMYvJ8bi9KHf1HFpNk", "tier": 2, "label": "DeFi Farmer 1", "weight": 0.7},
    {"address": "B1aLzaNMeFVAyQ6f3XbbUyKcH2YPHu2fqiEagprN2r3t", "tier": 2, "label": "Yield Whale", "weight": 0.7},
    {"address": "Gc2Ak7eAkNkEi3KJEXzWZYMQYo2V27jWBDF7X3LFsuef", "tier": 2, "label": "Liquidity Provider", "weight": 0.7},
    {"address": "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "tier": 2, "label": "Jito Staker", "weight": 0.7},
    {"address": "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "tier": 2, "label": "Validator Whale", "weight": 0.7},
    {"address": "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT", "tier": 2, "label": "Marinade Whale", "weight": 0.7},
    {"address": "AHYic562KhgtAEkb1sCuCLfE8GSwqXvkSTzYPy1nKqqe", "tier": 2, "label": "NFT/DeFi Hybrid", "weight": 0.7},
    {"address": "BbfC4sFcP4SVEuHuYWm7RMEMBQitvZbnEpxA3JTMXKgX", "tier": 2, "label": "Orca Whale", "weight": 0.7},
    {"address": "F3MfgEJe1TYtbGYdR7YzLBbtCabZbZPnb3cjRCaT7qPC", "tier": 2, "label": "Mango Trader", "weight": 0.7},
    {"address": "HbrEufKGPx7g7CiGLQ4dnCZMUB2dfJWbqWpKJwL6gwnp", "tier": 2, "label": "Phoenix Maker", "weight": 0.7},
    {"address": "5TzxJ16rUJyYQZYY2DJQQ5wvpLzQxKuRyE7qyNQz6zim", "tier": 2, "label": "Tensor Whale", "weight": 0.7},
    {"address": "CJwrp4c5YhTwcFTLPQkaDsaHbD2VsMELFhqJxWRpGQwt", "tier": 2, "label": "Drift Trader", "weight": 0.7},
    {"address": "G8jxYEWvfwn7fDAHiLFAqJy7BhZkeCwFwrfMPWLBMvhZ", "tier": 2, "label": "Kamino Whale", "weight": 0.7},
    {"address": "9kC3R3V8xJBnTTD11VNFNL8F5X3ZrxvE3jJwBSa9pU3P", "tier": 2, "label": "Flash Trader", "weight": 0.7},
    {"address": "CVq8csMhzxEHE8FiQnPRV4xLWGhfR7ppRkSV3kGy7KvX", "tier": 2, "label": "Sanctum Whale", "weight": 0.7},
    # Tier 3 - Community-tracked profitable traders (weight: 0.4)
    {"address": "EkJb5yT3Z5hX6nVLJefXAMJxq8CLXM8KnKQEYkypqyHM", "tier": 3, "label": "Sniper Bot 1", "weight": 0.4},
    {"address": "CBiNbHkwLX8GAdy5mYDMzUGwjPbCP1d7JqEqxBFxFo4o", "tier": 3, "label": "Memecoin Scout", "weight": 0.4},
    {"address": "JDgkag5F9FVm4GRtxXWCMP1Ey4yAqHMNm4ZS3RTF4DZq", "tier": 3, "label": "Runner Hunter", "weight": 0.4},
    {"address": "8xCRMh7kpvBhiz3CcYHJEiVUvPwNX4WJdBqHsXi3LKAx", "tier": 3, "label": "Degen Alpha", "weight": 0.4},
    {"address": "3b52bYAKQhCQDjDLhLp5SVzZFM3bfLCfSEV6sFaXpXjW", "tier": 3, "label": "SOL Maximalist", "weight": 0.4},
    {"address": "Ex5aJrBG9K8iUPzwFKntREhpHWKhvQDiKMWpYiFb8f3Y", "tier": 3, "label": "Bot Farmer", "weight": 0.4},
    {"address": "7VGNHGkqskTTXxM2oRAHHBaT6Mvy4Wv6dMvSd6m7f7CG", "tier": 3, "label": "Copy Trader Pro", "weight": 0.4},
    {"address": "AZrSGP1jFbhyMj3rMEVB7a5nM5ccZaP2Y2CTsRQRbhWr", "tier": 3, "label": "Yield Optimizer", "weight": 0.4},
    {"address": "HBhKqptJfHPV3S8Q1Y76T5Gcfxbo8JnG4oVhBHBH9oQg", "tier": 3, "label": "Breakout Catcher", "weight": 0.4},
    {"address": "4aZJKGMUdNhrdaEiKqPDMcBz1HFfXNbfGkJRsWMo47gQ", "tier": 3, "label": "Volume Scout", "weight": 0.4},
    {"address": "9Rq7JRxvMBHsL6zXqBXRb8RNMWYCrSfNZqiHxCF9K5nJ", "tier": 3, "label": "Pair Sniper", "weight": 0.4},
    {"address": "CXqGZFHNUqskgB4rUqD5MC8bTkAm3AM4e4QmrWBJK8Mc", "tier": 3, "label": "Trend Surfer", "weight": 0.4},
    {"address": "6Vc9BjvGBqKRPxVNwRj1TgxPfLVmjmLPJVNx4SJdw1mH", "tier": 3, "label": "Scalp Master", "weight": 0.4},
    {"address": "DHj3U2g1FBpLXqxD8c2J6jHPBmH4cKQo8QJywKg5Du5B", "tier": 3, "label": "Early Bird", "weight": 0.4},
    {"address": "Fp4hShG6zWWXks2oHam3WwVHbpN1RQMH9Kdb1mC4H2Cp", "tier": 3, "label": "Momentum Rider", "weight": 0.4},
    {"address": "BYd8mFhk9bEzJRFb8Z2hReWCoFRLYo6y3kcLMXrQYGhE", "tier": 3, "label": "Whale Follower", "weight": 0.4},
    {"address": "8U4cZP8gCHFnJD1LYi8i6Y4PSCDeT3P8Gf6dFCqoMLjS", "tier": 3, "label": "LP Shark", "weight": 0.4},
    {"address": "G6xMv3ZFuFgcSFiHPbWpJRedfEW3fuTMR2MjDEGfxhEX", "tier": 3, "label": "Arb Master", "weight": 0.4},
    {"address": "3gv2VPM1dYsqzKai1G8FW3fKYGZiPJFjNfbm5oc8WLxr", "tier": 3, "label": "DeFi Degenerate", "weight": 0.4},
    {"address": "4QTmrHTcaHPkz5MZz9V2VPJuTFR4h4Gprxqyib2oCT8u", "tier": 3, "label": "Token Accumulator", "weight": 0.4},
    {"address": "HzaL16tcTfsWdbhicFYUficTR1XdY2sLAqdXRNeY4sMR", "tier": 3, "label": "Stealth Whale", "weight": 0.4},
    {"address": "AsE9zy6rCqjUXS8CgoBRmSHQiXzcRNjKEP7E7JsJSMhH", "tier": 3, "label": "Signal Trader", "weight": 0.4},
    {"address": "9WsXVFjgqmPiZpXqJWvP4LCrYbqGFiDUqUNGUG7F9QaM", "tier": 3, "label": "MEV Hunter", "weight": 0.4},
    {"address": "C1JdKr5Kw5Ye9h4FLBfhQpc6TkBfH4J2d6CzV4wp7aWi", "tier": 3, "label": "Gamma Trader", "weight": 0.4},
    {"address": "EoC7SnPq42nT5bGFjMWdSWXYmafk2N4FTKuYzFJEWCzg", "tier": 3, "label": "Volatility Play", "weight": 0.4},
    {"address": "7gNVVFTCjFSpxfKQWjMx4UmUQFf57CqMKXMBHkX7BQ5P", "tier": 3, "label": "Night Trader", "weight": 0.4},
]

# Backward compat: flat list of addresses
SMART_MONEY_WALLETS = [w["address"] for w in SMART_MONEY_WALLETS_SCORED]

# Wallet weight lookup
WALLET_WEIGHTS = {w["address"]: w["weight"] for w in SMART_MONEY_WALLETS_SCORED}
WALLET_LABELS = {w["address"]: w["label"] for w in SMART_MONEY_WALLETS_SCORED}

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
    Stores detected signals in MongoDB with profit-weighted scoring.
    Scans Tier 1 every cycle, Tier 2 every other, Tier 3 every 3rd.
    """
    now = datetime.now(timezone.utc)
    # Only look at transactions from the last hour
    cutoff_ts = int((now - timedelta(hours=1)).timestamp())
    signals_found = 0

    # Determine which tiers to scan this cycle (rotate to reduce API load)
    cycle_count = await db.smart_money_meta.find_one({"key": "scan_cycle"})
    current_cycle = (cycle_count.get("value", 0) if cycle_count else 0) + 1
    await db.smart_money_meta.update_one(
        {"key": "scan_cycle"}, {"$set": {"value": current_cycle}}, upsert=True
    )

    wallets_to_scan = []
    for w in SMART_MONEY_WALLETS_SCORED:
        if w["tier"] == 1:
            wallets_to_scan.append(w)  # Always scan Tier 1
        elif w["tier"] == 2 and current_cycle % 2 == 0:
            wallets_to_scan.append(w)  # Tier 2 every other cycle
        elif w["tier"] == 3 and current_cycle % 3 == 0:
            wallets_to_scan.append(w)  # Tier 3 every 3rd cycle

    for wallet_info in wallets_to_scan:
        wallet = wallet_info["address"]
        weight = wallet_info["weight"]
        label = wallet_info["label"]

        try:
            txns = await fetch_wallet_transactions(wallet, limit=10)

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

                # Store the signal with profit weight
                signal_doc = {
                    "wallet_address": wallet,
                    "wallet_label": label,
                    "wallet_tier": wallet_info["tier"],
                    "wallet_weight": weight,
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
                    f"({swap['sol_amount']:.2f} SOL) by {label} [T{wallet_info['tier']}]"
                )

        except Exception as e:
            logger.warning(f"Error scanning wallet {label}: {e}")

    if signals_found > 0:
        logger.info(f"Smart money scanner: found {signals_found} new signals from {len(wallets_to_scan)} wallets")
    return signals_found


async def get_smart_money_signal(token_mint: str) -> Dict:
    """
    Get aggregated smart money signal for a specific token.
    Uses profit-weighted scoring: Tier 1 wallets have 2.5x the impact of Tier 3.

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
    ).to_list(100)

    if not signals:
        return {
            "action": "neutral",
            "strength": 0.0,
            "whale_count": 0,
            "tier1_whales": 0,
            "total_sol": 0,
            "buy_count": 0,
            "sell_count": 0,
            "buy_sol": 0,
            "sell_sol": 0,
            "weighted_buy_ratio": 0.5,
            "details": []
        }

    buys = [s for s in signals if s["action"] == "buy"]
    sells = [s for s in signals if s["action"] == "sell"]

    # Profit-weighted SOL volumes
    buy_sol_weighted = sum(
        s.get("sol_amount", 0) * s.get("wallet_weight", WALLET_WEIGHTS.get(s.get("wallet_address"), 0.4))
        for s in buys
    )
    sell_sol_weighted = sum(
        s.get("sol_amount", 0) * s.get("wallet_weight", WALLET_WEIGHTS.get(s.get("wallet_address"), 0.4))
        for s in sells
    )
    buy_sol = sum(s.get("sol_amount", 0) for s in buys)
    sell_sol = sum(s.get("sol_amount", 0) for s in sells)
    total_sol = buy_sol + sell_sol
    total_weighted = buy_sol_weighted + sell_sol_weighted

    unique_wallets = len(set(s["wallet_address"] for s in signals))
    tier1_count = len(set(s["wallet_address"] for s in signals if s.get("wallet_tier") == 1))

    # Determine action and strength using weighted scoring
    if total_weighted > 0:
        buy_ratio = buy_sol_weighted / total_weighted
    else:
        buy_ratio = 0.5

    if buy_ratio > 0.6:
        action = "buy"
        strength = min(1.0, (buy_ratio - 0.5) * 2 * min(unique_wallets, 5) * 0.25)
        # Tier 1 conviction bonus
        if tier1_count >= 2:
            strength = min(1.0, strength + 0.15)
    elif buy_ratio < 0.4:
        action = "sell"
        strength = min(1.0, (0.5 - buy_ratio) * 2 * min(unique_wallets, 5) * 0.25)
        if tier1_count >= 2:
            strength = min(1.0, strength + 0.15)
    else:
        action = "neutral"
        strength = 0.0

    return {
        "action": action,
        "strength": round(strength, 3),
        "whale_count": unique_wallets,
        "tier1_whales": tier1_count,
        "total_sol": round(total_sol, 2),
        "buy_count": len(buys),
        "sell_count": len(sells),
        "buy_sol": round(buy_sol, 2),
        "sell_sol": round(sell_sol, 2),
        "weighted_buy_ratio": round(buy_ratio, 3),
        "details": [
            {
                "wallet": WALLET_LABELS.get(s["wallet_address"], s["wallet_address"][:8] + "..."),
                "tier": s.get("wallet_tier", 3),
                "action": s["action"],
                "sol": round(s.get("sol_amount", 0), 2),
                "time": s.get("detected_at")
            }
            for s in sorted(signals, key=lambda x: x.get("wallet_weight", 0), reverse=True)[:10]
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
