"""
Real Price Data Collector

Builds actual OHLCV candle data by periodically polling DexScreener prices
and storing them in MongoDB. Replaces synthetic price history with real data
when sufficient candles are available.

This removes the -10% synthetic data confidence penalty for tokens with real data.
"""
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from utils.database import db

logger = logging.getLogger(__name__)

# Candle interval in minutes
CANDLE_INTERVAL_MINUTES = 5

# Minimum candles needed to use real data (50 candles = ~4 hours at 5min intervals)
MIN_CANDLES_FOR_REAL_DATA = 20

# Token mints we actively collect for
TRACKED_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "RNDR": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
}


async def collect_price_snapshot():
    """
    Collect current prices for all tracked tokens and store as candle data.
    Called every CANDLE_INTERVAL_MINUTES by the scheduler.
    """
    now = datetime.now(timezone.utc)
    # Round down to nearest interval
    interval_start = now.replace(
        minute=(now.minute // CANDLE_INTERVAL_MINUTES) * CANDLE_INTERVAL_MINUTES,
        second=0, microsecond=0
    )
    interval_key = interval_start.isoformat()

    collected = 0
    async with httpx.AsyncClient(timeout=15.0) as client:
        for symbol, mint in TRACKED_TOKENS.items():
            try:
                response = await client.get(
                    f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
                )
                if response.status_code != 200:
                    continue

                pairs = response.json().get("pairs", [])
                if not pairs:
                    continue

                best_pair = max(
                    pairs,
                    key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0)
                )
                price = float(best_pair.get("priceUsd", 0) or 0)
                volume_h1 = float(best_pair.get("volume", {}).get("h1", 0) or 0)

                if price <= 0:
                    continue

                # Upsert candle: update high/low/close, keep open from first insert
                existing = await db.price_candles.find_one({
                    "token_mint": mint,
                    "interval_key": interval_key
                })

                if existing:
                    await db.price_candles.update_one(
                        {"token_mint": mint, "interval_key": interval_key},
                        {"$set": {
                            "close": price,
                            "high": max(existing.get("high", price), price),
                            "low": min(existing.get("low", price), price),
                            "volume": volume_h1,
                            "updated_at": now.isoformat()
                        }}
                    )
                else:
                    await db.price_candles.insert_one({
                        "token_symbol": symbol,
                        "token_mint": mint,
                        "interval_key": interval_key,
                        "interval_minutes": CANDLE_INTERVAL_MINUTES,
                        "open": price,
                        "high": price,
                        "low": price,
                        "close": price,
                        "volume": volume_h1,
                        "timestamp": interval_start.isoformat(),
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat()
                    })
                collected += 1

            except Exception as e:
                logger.warning(f"Price collection error for {symbol}: {e}")

    if collected > 0:
        logger.info(f"Price collector: stored {collected} candle snapshots")
    return collected


async def get_real_price_history(token_mint: str, periods: int = 50) -> Tuple[List[float], bool]:
    """
    Get real OHLCV-based price history for a token.

    Returns:
        Tuple of (close_prices, is_synthetic)
        - is_synthetic=False if we have enough real candles
        - is_synthetic=True if we had to fall back to synthetic data
    """
    candles = await db.price_candles.find(
        {"token_mint": token_mint},
        {"_id": 0, "close": 1, "timestamp": 1}
    ).sort("timestamp", -1).to_list(periods)

    if len(candles) >= MIN_CANDLES_FOR_REAL_DATA:
        # Reverse to chronological order (oldest first)
        prices = [c["close"] for c in reversed(candles)]
        logger.info(f"Using REAL price data for {token_mint[:8]}... ({len(prices)} candles)")
        return prices, False

    # Not enough real data - return empty to signal fallback needed
    return [], True


async def get_real_ohlcv(token_mint: str, periods: int = 50) -> Optional[List[Dict]]:
    """
    Get full OHLCV candle data for a token.
    Returns None if insufficient data.
    """
    candles = await db.price_candles.find(
        {"token_mint": token_mint},
        {"_id": 0, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1, "timestamp": 1}
    ).sort("timestamp", -1).to_list(periods)

    if len(candles) >= MIN_CANDLES_FOR_REAL_DATA:
        return list(reversed(candles))
    return None


async def add_runner_to_tracking(symbol: str, token_mint: str):
    """Dynamically add a runner token to tracking when discovered."""
    if token_mint not in TRACKED_TOKENS.values():
        TRACKED_TOKENS[symbol] = token_mint
        logger.info(f"Added runner {symbol} ({token_mint[:8]}...) to price tracking")


async def cleanup_old_candles(max_age_hours: int = 48):
    """Remove candle data older than max_age_hours to save space."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    result = await db.price_candles.delete_many({"timestamp": {"$lt": cutoff}})
    if result.deleted_count > 0:
        logger.info(f"Cleaned up {result.deleted_count} old candle records")


async def get_data_quality_status() -> Dict:
    """Get status of price data collection for all tracked tokens."""
    status = {}
    for symbol, mint in TRACKED_TOKENS.items():
        count = await db.price_candles.count_documents({"token_mint": mint})
        latest = await db.price_candles.find_one(
            {"token_mint": mint},
            {"_id": 0, "close": 1, "timestamp": 1},
            sort=[("timestamp", -1)]
        )
        status[symbol] = {
            "candles": count,
            "has_real_data": count >= MIN_CANDLES_FOR_REAL_DATA,
            "latest_price": latest.get("close") if latest else None,
            "latest_time": latest.get("timestamp") if latest else None
        }
    return status
