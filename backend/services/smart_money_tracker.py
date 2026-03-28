"""
Smart Money Tracker v2 — Dynamic Whale Discovery

Replaces the hardcoded wallet list with live data sources:
1. DexScreener: Aggregate buy/sell flow, volume, and transaction counts
2. Helius Enhanced API: Parsed swap transactions to identify large traders

Signals feed into the auto-trader engine as confidence adjustments.
"""

import os
import logging
import httpx
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from utils.database import db

logger = logging.getLogger(__name__)

HELIUS_RPC_URL = os.environ.get("HELIUS_RPC_URL", "")
HELIUS_API_KEY = ""
if "api-key=" in HELIUS_RPC_URL:
    HELIUS_API_KEY = HELIUS_RPC_URL.split("api-key=")[-1]

HELIUS_ENHANCED_URL = "https://api.helius.xyz/v0"

# Known token mints for tracked tokens
TOKEN_MINTS = {
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "RNDR": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "DRIFT": "DriFtupJYLTosbwoN8koMbEYSx54aFAVLddWsbksjwg7",
    "TRUMP": "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
    "PENGU": "2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv",
    "POPCAT": "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    "FARTCOIN": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
}

# Reverse lookup: mint -> symbol
MINT_TO_SYMBOL = {v: k for k, v in TOKEN_MINTS.items()}

# In-memory caches
_dexscreener_flow_cache: Dict[str, tuple] = {}  # symbol -> (timestamp, data)
_large_trader_cache: Dict[str, tuple] = {}  # pair_address -> (timestamp, traders)
FLOW_CACHE_TTL = 300  # 5 min
TRADER_CACHE_TTL = 600  # 10 min

# Minimum SOL swap size to qualify as "whale" activity
MIN_WHALE_SWAP_SOL = 0.5


async def get_dexscreener_flow(symbol: str) -> Optional[dict]:
    """
    Fetch aggregate buy/sell flow data for a token from DexScreener.
    Returns buy/sell counts, volumes, and the buy ratio.
    """
    now = time.time()
    cached = _dexscreener_flow_cache.get(symbol)
    if cached and now - cached[0] < FLOW_CACHE_TTL:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.dexscreener.com/latest/dex/search?q={symbol}%20SOL"
            )
            if resp.status_code != 200:
                return None

            pairs = resp.json().get("pairs", [])
            # Find the best SOL pair (highest liquidity)
            sol_pairs = [
                p for p in pairs
                if p.get("quoteToken", {}).get("symbol") == "SOL"
                and p.get("chainId") == "solana"
            ]
            if not sol_pairs:
                return None

            pair = max(sol_pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0))
            txns = pair.get("txns", {})

            result = {
                "pair_address": pair.get("pairAddress"),
                "dex": pair.get("dexId"),
                "liquidity_usd": pair.get("liquidity", {}).get("usd", 0),
                "volume_1h": pair.get("volume", {}).get("h1", 0),
                "volume_6h": pair.get("volume", {}).get("h6", 0),
                "volume_24h": pair.get("volume", {}).get("h24", 0),
                "buys_1h": txns.get("h1", {}).get("buys", 0),
                "sells_1h": txns.get("h1", {}).get("sells", 0),
                "buys_6h": txns.get("h6", {}).get("buys", 0),
                "sells_6h": txns.get("h6", {}).get("sells", 0),
                "buys_24h": txns.get("h24", {}).get("buys", 0),
                "sells_24h": txns.get("h24", {}).get("sells", 0),
                "price_change_1h": pair.get("priceChange", {}).get("h1", 0),
                "price_change_6h": pair.get("priceChange", {}).get("h6", 0),
                "price_change_24h": pair.get("priceChange", {}).get("h24", 0),
            }

            # Calculate buy ratios
            total_1h = result["buys_1h"] + result["sells_1h"]
            total_6h = result["buys_6h"] + result["sells_6h"]
            total_24h = result["buys_24h"] + result["sells_24h"]
            result["buy_ratio_1h"] = result["buys_1h"] / total_1h if total_1h > 0 else 0.5
            result["buy_ratio_6h"] = result["buys_6h"] / total_6h if total_6h > 0 else 0.5
            result["buy_ratio_24h"] = result["buys_24h"] / total_24h if total_24h > 0 else 0.5

            _dexscreener_flow_cache[symbol] = (now, result)
            return result

    except Exception as e:
        logger.debug(f"DexScreener flow error for {symbol}: {e}")
        return None


async def discover_large_traders(pair_address: str) -> List[dict]:
    """
    Use Helius Enhanced API to find wallets making large swaps on a pair.
    Returns list of {wallet, action, sol_amount, timestamp}.
    """
    if not HELIUS_API_KEY:
        return []

    now = time.time()
    cached = _large_trader_cache.get(pair_address)
    if cached and now - cached[0] < TRADER_CACHE_TTL:
        return cached[1]

    traders = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{HELIUS_ENHANCED_URL}/addresses/{pair_address}/transactions",
                params={"api-key": HELIUS_API_KEY, "limit": 20, "type": "SWAP"}
            )
            if resp.status_code != 200:
                logger.debug(f"Helius enhanced API returned {resp.status_code}")
                return []

            txns = resp.json()
            if not isinstance(txns, list):
                return []

            for tx in txns:
                fee_payer = tx.get("feePayer", "")
                if not fee_payer:
                    continue

                # Calculate SOL volume from native transfers
                sol_volume = 0
                for nt in tx.get("nativeTransfers", []):
                    sol_volume += abs(nt.get("amount", 0)) / 1e9

                if sol_volume < MIN_WHALE_SWAP_SOL:
                    continue

                # Determine buy or sell from token transfers
                action = "unknown"
                token_mint = ""
                for tt in tx.get("tokenTransfers", []):
                    mint = tt.get("mint", "")
                    if mint in MINT_TO_SYMBOL:
                        token_mint = mint
                        if tt.get("toUserAccount") == fee_payer:
                            action = "buy"
                        elif tt.get("fromUserAccount") == fee_payer:
                            action = "sell"
                        break

                if action in ("buy", "sell"):
                    traders.append({
                        "wallet": fee_payer,
                        "action": action,
                        "sol_amount": round(sol_volume, 4),
                        "token_mint": token_mint,
                        "token_symbol": MINT_TO_SYMBOL.get(token_mint, "?"),
                        "timestamp": tx.get("timestamp", 0),
                        "source": tx.get("source", "UNKNOWN"),
                        "signature": tx.get("signature", ""),
                    })

        _large_trader_cache[pair_address] = (now, traders)
        return traders

    except Exception as e:
        logger.debug(f"Helius large trader discovery error: {e}")
        return []


async def scan_smart_money():
    """
    Main scanner — runs every 10 minutes via scheduler.
    Fetches live flow data from DexScreener + large trader activity from Helius.
    Stores signals in MongoDB.
    """
    try:
        signals_found = 0
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=2)).isoformat()

        for symbol, mint in TOKEN_MINTS.items():
            # 1. Get aggregate flow from DexScreener
            flow = await get_dexscreener_flow(symbol)
            if not flow:
                continue

            # 2. Discover large traders on this pair
            pair_address = flow.get("pair_address", "")
            large_traders = []
            if pair_address:
                large_traders = await discover_large_traders(pair_address)

            # 3. Determine signal from flow + large traders
            buy_ratio_1h = flow.get("buy_ratio_1h", 0.5)
            buy_ratio_6h = flow.get("buy_ratio_6h", 0.5)
            volume_1h = flow.get("volume_1h", 0)

            # Weight recent flow more heavily
            weighted_ratio = buy_ratio_1h * 0.6 + buy_ratio_6h * 0.4

            # Large trader signal
            whale_buys = len([t for t in large_traders if t["action"] == "buy"])
            whale_sells = len([t for t in large_traders if t["action"] == "sell"])
            whale_buy_sol = sum(t["sol_amount"] for t in large_traders if t["action"] == "buy")
            whale_sell_sol = sum(t["sol_amount"] for t in large_traders if t["action"] == "sell")

            if weighted_ratio > 0.55 or whale_buys > whale_sells:
                action = "buy"
            elif weighted_ratio < 0.45 or whale_sells > whale_buys:
                action = "sell"
            else:
                action = "neutral"

            # Calculate signal strength (0 to 1)
            flow_strength = abs(weighted_ratio - 0.5) * 4  # 0.5 = 0, 0.75 = 1.0
            whale_strength = min(1.0, (whale_buys + whale_sells) * 0.2) if large_traders else 0
            strength = min(1.0, flow_strength * 0.7 + whale_strength * 0.3)

            if action == "neutral" and strength < 0.1:
                continue

            # Store signal
            signal_doc = {
                "token_mint": mint,
                "token_symbol": symbol,
                "action": action,
                "strength": round(strength, 3),
                "buy_ratio_1h": round(buy_ratio_1h, 3),
                "buy_ratio_6h": round(buy_ratio_6h, 3),
                "volume_1h": volume_1h,
                "whale_buys": whale_buys,
                "whale_sells": whale_sells,
                "whale_buy_sol": round(whale_buy_sol, 2),
                "whale_sell_sol": round(whale_sell_sol, 2),
                "large_traders": [
                    {"wallet": t["wallet"][:12] + "...", "action": t["action"], "sol": t["sol_amount"]}
                    for t in large_traders[:5]
                ],
                "detected_at": now.isoformat(),
                "expires_at": expires_at,
                "source": "dexscreener+helius",
            }

            await db.smart_money_signals.update_one(
                {"token_mint": mint},
                {"$set": signal_doc},
                upsert=True,
            )
            signals_found += 1

            logger.info(
                f"SM signal: {symbol} {action} (str={strength:.2f}, "
                f"flow={weighted_ratio:.2f}, whales={whale_buys}B/{whale_sells}S)"
            )

        logger.info(f"Smart money scanner: {signals_found} signals from {len(TOKEN_MINTS)} tokens")
        return {"success": True, "signals": signals_found}

    except Exception as e:
        logger.error(f"Smart money scan error: {e}")
        return {"success": False, "error": str(e)}


async def get_smart_money_signal(token_mint: str) -> dict:
    """
    Get aggregated smart money signal for a specific token.
    Returns signal data used by the auto-trade engine.
    """
    signal = await db.smart_money_signals.find_one(
        {"token_mint": token_mint},
        {"_id": 0}
    )

    if not signal:
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
            "details": [],
        }

    return {
        "action": signal.get("action", "neutral"),
        "strength": signal.get("strength", 0),
        "whale_count": signal.get("whale_buys", 0) + signal.get("whale_sells", 0),
        "tier1_whales": 0,
        "total_sol": signal.get("whale_buy_sol", 0) + signal.get("whale_sell_sol", 0),
        "buy_count": signal.get("whale_buys", 0),
        "sell_count": signal.get("whale_sells", 0),
        "buy_sol": signal.get("whale_buy_sol", 0),
        "sell_sol": signal.get("whale_sell_sol", 0),
        "weighted_buy_ratio": signal.get("buy_ratio_1h", 0.5),
        "details": signal.get("large_traders", []),
    }


async def get_confidence_adjustment(token_mint: str) -> float:
    """
    Get a confidence adjustment based on smart money activity.
    Returns float between -0.15 and +0.15.
    """
    signal = await get_smart_money_signal(token_mint)

    if signal["action"] == "buy":
        return min(0.15, signal["strength"] * 0.15)
    elif signal["action"] == "sell":
        return max(-0.15, -signal["strength"] * 0.15)

    return 0.0


async def cleanup_expired_signals():
    """Remove expired smart money signals."""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.smart_money_signals.delete_many({"expires_at": {"$lt": now}})
    if result.deleted_count > 0:
        logger.info(f"Cleaned up {result.deleted_count} expired smart money signals")
