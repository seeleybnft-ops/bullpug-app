"""
Market Data Quality Checks

Provides volume/liquidity filtering and price history quality assessment
for the AI trading bot. Prevents trades on unreliable data.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum thresholds for auto-trading
MIN_VOLUME_24H = 10_000      # $10K minimum 24h volume (established tokens have reliable data above this)
MIN_LIQUIDITY_USD = 5_000    # $5K minimum liquidity (lowered from $10K — data showed $10K too restrictive)
MIN_PRICE_HISTORY_POINTS = 10  # Minimum real data points for reliable indicators
MIN_SELL_TXNS_24H = 5        # Minimum sell transactions in 24h (liquidity exit filter)
MIN_BUY_SELL_RATIO = 0.1     # Minimum sells/buys ratio (filters honeypots where sells are near zero)


def extract_market_quality(pair_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract volume, liquidity, and data quality metrics from a DexScreener pair.
    Returns a dict with quality metrics and pass/fail flags.
    """
    volume_24h = float(pair_data.get("volume", {}).get("h24", 0) or 0)
    liquidity_usd = float(pair_data.get("liquidity", {}).get("usd", 0) or 0)
    txns = pair_data.get("txns", {})
    buys_24h = int(txns.get("h24", {}).get("buys", 0) or 0)
    sells_24h = int(txns.get("h24", {}).get("sells", 0) or 0)
    total_txns_24h = buys_24h + sells_24h
    pair_age_hours = 0
    if pair_data.get("pairCreatedAt"):
        try:
            from datetime import datetime, timezone
            created = datetime.fromtimestamp(pair_data["pairCreatedAt"] / 1000, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            pair_age_hours = (now - created).total_seconds() / 3600
        except Exception:
            pass

    volume_ok = volume_24h >= MIN_VOLUME_24H
    liquidity_ok = liquidity_usd >= MIN_LIQUIDITY_USD
    sells_ok = sells_24h >= MIN_SELL_TXNS_24H
    ratio_ok = (sells_24h / max(buys_24h, 1)) >= MIN_BUY_SELL_RATIO if buys_24h > 0 else sells_24h > 0
    passes_all = volume_ok and liquidity_ok and sells_ok and ratio_ok

    return {
        "volume_24h": volume_24h,
        "liquidity_usd": liquidity_usd,
        "buys_24h": buys_24h,
        "sells_24h": sells_24h,
        "total_txns_24h": total_txns_24h,
        "pair_age_hours": pair_age_hours,
        "volume_ok": volume_ok,
        "liquidity_ok": liquidity_ok,
        "sells_ok": sells_ok,
        "ratio_ok": ratio_ok,
        "passes_quality_check": passes_all,
        "rejection_reasons": [
            r for r in [
                f"Volume ${volume_24h:,.0f} < ${MIN_VOLUME_24H:,.0f}" if not volume_ok else None,
                f"Liquidity ${liquidity_usd:,.0f} < ${MIN_LIQUIDITY_USD:,.0f}" if not liquidity_ok else None,
                f"Only {sells_24h} sells in 24h (need {MIN_SELL_TXNS_24H}+) — possible honeypot" if not sells_ok else None,
                f"Sell/buy ratio {sells_24h}/{buys_24h} too low — possible honeypot" if not ratio_ok else None,
            ] if r
        ]
    }


def build_price_history_from_dex(
    current_price: float,
    price_change_24h: float,
    price_change_6h: float,
    price_change_1h: float,
) -> Tuple[List[float], bool]:
    """
    Build price history from DexScreener price change data.
    
    Returns:
        Tuple of (price_list, is_synthetic)
        - is_synthetic is always True since this is reconstructed from % changes
        - The data is directionally accurate (based on real % changes) but
          the intermediate points are interpolated with noise
    """
    import random
    
    # Calculate historical prices from percentage changes
    price_24h_ago = current_price / (1 + price_change_24h / 100) if price_change_24h != -100 else current_price
    price_6h_ago = current_price / (1 + price_change_6h / 100) if price_change_6h != -100 else current_price
    price_1h_ago = current_price / (1 + price_change_1h / 100) if price_change_1h != -100 else current_price
    
    # Use deterministic seed for consistency within the same scan
    random.seed(int(current_price * 1e8) % 10000)
    
    # Calculate volatility from real price changes
    volatility = max(abs(price_change_24h), abs(price_change_6h), abs(price_change_1h)) / 100
    volatility = max(0.005, min(volatility, 0.05))
    
    prices = []
    for i in range(50):
        noise = random.uniform(-volatility, volatility) * current_price
        if i < 6:
            base = price_1h_ago + (current_price - price_1h_ago) * (i / 6)
        elif i < 12:
            base = price_6h_ago + (price_1h_ago - price_6h_ago) * ((i - 6) / 6)
        elif i < 24:
            base = price_24h_ago + (price_6h_ago - price_24h_ago) * ((i - 12) / 12)
        else:
            base = price_24h_ago * (1 - (i - 24) * 0.002)
        prices.append(base + noise)
    prices.append(current_price)
    
    return prices, True


def confidence_penalty_for_synthetic_data(confidence: float) -> float:
    """
    Apply a confidence penalty when trading on synthetic/reconstructed price data.
    Synthetic data means RSI/MACD/BB are approximations, not exact.
    """
    SYNTHETIC_PENALTY = 0.05  # Reduce confidence by 5% for synthetic data
    return max(0.0, confidence - SYNTHETIC_PENALTY)
