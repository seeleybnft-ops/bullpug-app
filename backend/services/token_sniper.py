"""
Token Sniper Scanner

Monitors DexScreener for brand new token pairs and applies rapid analysis.
Used when Trading Mode is set to "sniper".

Characteristics:
- Targets pairs < 30 minutes old
- Lower confidence thresholds (but smaller positions)
- Requires minimum liquidity for safety
- Rapid volume/momentum analysis instead of full technical indicators
"""
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from utils.database import db

logger = logging.getLogger(__name__)

# Sniper criteria
SNIPER_MAX_PAIR_AGE_MINUTES = 30
SNIPER_MIN_LIQUIDITY_USD = 10000    # Minimum $10k liquidity
SNIPER_MIN_VOLUME_5M = 5000         # Minimum $5k 5-min volume
SNIPER_MIN_BUYS_5M = 10             # At least 10 buys in 5 minutes
SNIPER_MAX_POSITION_MULTIPLIER = 0.3  # Sniper uses 30% of normal position

# Known rug indicators
RUG_INDICATORS = [
    "honeypot", "mint_authority", "freeze_authority",
    "blacklist", "hidden_owner", "external_call"
]


async def scan_new_pairs() -> List[Dict]:
    """
    Scan DexScreener for brand-new Solana token pairs.
    Uses a 2-step approach:
      1. Fetch latest token profiles + boosts on Solana
      2. Batch-lookup pair data for those tokens
      3. Apply sniper criteria (age, liquidity, volume, buys)
    Returns list of potential snipe targets.
    """
    targets = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: Get fresh token addresses from profiles AND boosts
            solana_addresses = set()

            # Source 1: Latest token profiles
            try:
                profiles_resp = await client.get("https://api.dexscreener.com/token-profiles/latest/v1")
                if profiles_resp.status_code == 200:
                    profiles = profiles_resp.json()
                    for t in profiles:
                        if t.get("chainId") == "solana" and t.get("tokenAddress"):
                            solana_addresses.add(t["tokenAddress"])
            except Exception as e:
                logger.debug(f"Token profiles fetch failed: {e}")

            # Source 2: Latest token boosts
            try:
                boosts_resp = await client.get("https://api.dexscreener.com/token-boosts/latest/v1")
                if boosts_resp.status_code == 200:
                    boosts = boosts_resp.json()
                    for t in boosts:
                        if t.get("chainId") == "solana" and t.get("tokenAddress"):
                            solana_addresses.add(t["tokenAddress"])
            except Exception as e:
                logger.debug(f"Token boosts fetch failed: {e}")

            if not solana_addresses:
                logger.warning("Sniper: No Solana token addresses found from profiles/boosts")
                return []

            logger.info(f"Sniper: Fetched {len(solana_addresses)} Solana token addresses from profiles+boosts")

            # Step 2: Batch lookup pair data (DexScreener supports comma-separated, max ~30)
            addr_list = list(solana_addresses)[:30]
            batch_query = ",".join(addr_list)

            response = await client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{batch_query}"
            )

            if response.status_code != 200:
                logger.warning(f"DexScreener batch lookup returned {response.status_code}")
                return []

            pairs = response.json().get("pairs", [])
            now = datetime.now(timezone.utc)

            # Step 3: Apply sniper criteria
            seen_mints = set()  # Dedupe by token mint
            for pair in pairs:
                try:
                    if pair.get("chainId") != "solana":
                        continue

                    created_at = pair.get("pairCreatedAt")
                    if not created_at:
                        continue

                    pair_age_minutes = (now - datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)).total_seconds() / 60

                    if pair_age_minutes > SNIPER_MAX_PAIR_AGE_MINUTES:
                        continue

                    # Basic safety checks
                    liquidity_usd = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                    if liquidity_usd < SNIPER_MIN_LIQUIDITY_USD:
                        continue

                    volume_5m = float(pair.get("volume", {}).get("m5", 0) or 0)
                    buys_5m = int(pair.get("txns", {}).get("m5", {}).get("buys", 0) or 0)
                    sells_5m = int(pair.get("txns", {}).get("m5", {}).get("sells", 0) or 0)

                    if volume_5m < SNIPER_MIN_VOLUME_5M:
                        continue

                    if buys_5m < SNIPER_MIN_BUYS_5M:
                        continue

                    token_mint = pair.get("baseToken", {}).get("address", "")
                    if not token_mint or token_mint in seen_mints:
                        continue
                    seen_mints.add(token_mint)

                    # Calculate sniper confidence
                    confidence = _calculate_sniper_confidence(pair, pair_age_minutes, buys_5m, sells_5m, liquidity_usd, volume_5m)

                    token_symbol = pair.get("baseToken", {}).get("symbol", "???")
                    price_usd = float(pair.get("priceUsd", 0) or 0)

                    # Check if we already sniped this token recently
                    existing = await db.sniper_history.find_one({
                        "token_mint": token_mint,
                        "created_at": {"$gte": (now - timedelta(hours=1)).isoformat()}
                    })
                    if existing:
                        continue

                    target = {
                        "token_symbol": token_symbol,
                        "token_mint": token_mint,
                        "pair_address": pair.get("pairAddress"),
                        "price_usd": price_usd,
                        "liquidity_usd": liquidity_usd,
                        "volume_5m": volume_5m,
                        "buys_5m": buys_5m,
                        "sells_5m": sells_5m,
                        "pair_age_minutes": round(pair_age_minutes, 1),
                        "confidence": round(confidence, 3),
                        "dex": pair.get("dexId", "unknown"),
                        "price_change_5m": float(pair.get("priceChange", {}).get("m5", 0) or 0)
                    }
                    targets.append(target)

                except Exception as e:
                    logger.debug(f"Error processing pair: {e}")
                    continue

        # Sort by confidence
        targets.sort(key=lambda x: x["confidence"], reverse=True)

        if targets:
            logger.info(f"Sniper scanner found {len(targets)} targets (top: {targets[0]['token_symbol']} @ {targets[0]['confidence']:.0%})")

    except Exception as e:
        logger.warning(f"Sniper scan error: {e}")

    return targets[:5]  # Top 5 targets


def _calculate_sniper_confidence(pair: Dict, age_min: float, buys: int, sells: int, liquidity: float, volume: float) -> float:
    """
    Calculate sniper confidence for a new pair.
    Different from normal analysis — focuses on early momentum indicators.
    """
    confidence = 0.50  # Base

    # 1. Buy/Sell ratio (heavy weight for new tokens)
    total_txns = buys + sells
    if total_txns > 0:
        buy_ratio = buys / total_txns
        if buy_ratio >= 0.7:
            confidence += 0.15  # Strong buying pressure
        elif buy_ratio >= 0.6:
            confidence += 0.08
        elif buy_ratio < 0.4:
            confidence -= 0.15  # More sellers = danger

    # 2. Volume to liquidity ratio (healthy is 0.5-3x)
    if liquidity > 0:
        vol_liq = volume / liquidity
        if 0.5 <= vol_liq <= 3:
            confidence += 0.10  # Healthy ratio
        elif vol_liq > 5:
            confidence -= 0.05  # Suspicious (possible wash trading)

    # 3. Liquidity strength
    if liquidity >= 100000:
        confidence += 0.10  # Strong liquidity
    elif liquidity >= 50000:
        confidence += 0.05

    # 4. Age factor (newer = riskier but higher potential)
    if age_min < 5:
        confidence += 0.05  # Very fresh — potential for early pump
    elif age_min < 15:
        confidence += 0.08  # Sweet spot — some validation
    else:
        confidence += 0.03  # Older but still new

    # 5. Price change (positive 5m change = momentum)
    price_change = float(pair.get("priceChange", {}).get("m5", 0) or 0)
    if 5 <= price_change <= 50:
        confidence += 0.08  # Healthy upward momentum
    elif price_change > 100:
        confidence -= 0.10  # Too much too fast = likely dump

    # 6. Transaction velocity (more txns = more interest)
    if total_txns >= 50:
        confidence += 0.05
    elif total_txns >= 20:
        confidence += 0.03

    return max(0.0, min(0.95, confidence))


async def record_snipe(token_mint: str, token_symbol: str, confidence: float, wallet_address: str):
    """Record a snipe attempt for tracking and cooldown."""
    await db.sniper_history.insert_one({
        "token_mint": token_mint,
        "token_symbol": token_symbol,
        "confidence": confidence,
        "wallet_address": wallet_address,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
