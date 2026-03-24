"""
Social Sentiment Analyzer

Analyzes social/market sentiment for tokens using:
1. DexScreener on-chain metrics (buy/sell ratio, transaction volume)
2. Market momentum indicators (price changes, volume trends)
3. AI-powered sentiment analysis via GPT (Emergent LLM Key)

Provides a sentiment score that adjusts trading confidence.
"""
import os
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from utils.database import db

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# Sentiment cache duration
SENTIMENT_CACHE_MINUTES = 15


async def analyze_token_sentiment(
    token_mint: str,
    pair_data: Optional[Dict] = None
) -> Dict:
    """
    Analyze sentiment for a token using multiple data sources.

    Args:
        token_mint: Token mint address
        pair_data: Optional DexScreener pair data (avoids extra API call)

    Returns:
        Dict with 'score' (-1 to 1), 'label', 'factors', 'confidence_adjustment'
    """
    # Check cache first
    cached = await db.sentiment_cache.find_one({
        "token_mint": token_mint,
        "expires_at": {"$gte": datetime.now(timezone.utc).isoformat()}
    }, {"_id": 0})

    if cached:
        return cached.get("sentiment", _neutral_sentiment())

    # Fetch pair data if not provided
    if not pair_data:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                )
                if response.status_code == 200:
                    pairs = response.json().get("pairs", [])
                    if pairs:
                        pair_data = max(
                            pairs,
                            key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0)
                        )
        except Exception as e:
            logger.warning(f"Failed to fetch pair data for sentiment: {e}")

    if not pair_data:
        return _neutral_sentiment()

    # Analyze multiple sentiment factors
    factors = []
    total_score = 0.0
    total_weight = 0.0

    # 1. Buy/Sell Ratio Analysis (weight: 0.25)
    txns = pair_data.get("txns", {})
    buys_24h = int(txns.get("h24", {}).get("buys", 0) or 0)
    sells_24h = int(txns.get("h24", {}).get("sells", 0) or 0)
    buys_1h = int(txns.get("h1", {}).get("buys", 0) or 0)
    sells_1h = int(txns.get("h1", {}).get("sells", 0) or 0)

    if buys_24h + sells_24h > 0:
        buy_ratio_24h = buys_24h / (buys_24h + sells_24h)
        buy_ratio_1h = buys_1h / (buys_1h + sells_1h) if (buys_1h + sells_1h) > 0 else 0.5

        # Score: >0.6 buy ratio = bullish, <0.4 = bearish
        ratio_score = (buy_ratio_24h - 0.5) * 2  # Maps 0.4-0.6 to -0.2 to 0.2
        ratio_score_1h = (buy_ratio_1h - 0.5) * 2

        # 1h ratio weighted more heavily (more recent = more relevant)
        combined_ratio = ratio_score * 0.4 + ratio_score_1h * 0.6

        factors.append({
            "factor": "buy_sell_ratio",
            "score": round(combined_ratio, 3),
            "detail": f"24h: {buy_ratio_24h:.1%} buys, 1h: {buy_ratio_1h:.1%} buys"
        })
        total_score += combined_ratio * 0.25
        total_weight += 0.25

    # 2. Price Momentum Analysis (weight: 0.30)
    price_changes = pair_data.get("priceChange", {})
    change_5m = float(price_changes.get("m5", 0) or 0)
    change_1h = float(price_changes.get("h1", 0) or 0)
    change_24h = float(price_changes.get("h24", 0) or 0)

    # Short-term momentum (5m + 1h) weighted more
    momentum_score = 0
    if abs(change_1h) > 0.5:  # Meaningful change
        # Normalize: +10% = +0.5 score, -10% = -0.5 score
        short_momentum = max(-1, min(1, change_1h / 20))
        long_momentum = max(-1, min(1, change_24h / 40))

        momentum_score = short_momentum * 0.7 + long_momentum * 0.3

        # Detect momentum acceleration (1h change faster than 24h trend)
        if change_1h > 0 and change_24h > 0 and abs(change_1h) > abs(change_24h / 24):
            momentum_score = min(1.0, momentum_score + 0.1)
            factors.append({
                "factor": "momentum_acceleration",
                "score": 0.1,
                "detail": "Short-term momentum accelerating"
            })

    factors.append({
        "factor": "price_momentum",
        "score": round(momentum_score, 3),
        "detail": f"5m: {change_5m:+.1f}%, 1h: {change_1h:+.1f}%, 24h: {change_24h:+.1f}%"
    })
    total_score += momentum_score * 0.30
    total_weight += 0.30

    # 3. Volume Trend Analysis (weight: 0.20)
    volume_24h = float(pair_data.get("volume", {}).get("h24", 0) or 0)
    volume_1h = float(pair_data.get("volume", {}).get("h1", 0) or 0)

    volume_score = 0
    if volume_24h > 0:
        # Expected 1h volume = 24h / 24
        expected_1h = volume_24h / 24
        if expected_1h > 0:
            volume_ratio = volume_1h / expected_1h
            # Volume ratio > 2x = bullish, < 0.5x = bearish
            volume_score = max(-0.5, min(0.5, (volume_ratio - 1) * 0.5))

            factors.append({
                "factor": "volume_trend",
                "score": round(volume_score, 3),
                "detail": f"1h vol {volume_ratio:.1f}x average (${volume_1h:,.0f})"
            })
            total_score += volume_score * 0.20
            total_weight += 0.20

    # 4. Liquidity Health (weight: 0.10)
    liquidity_usd = float(pair_data.get("liquidity", {}).get("usd", 0) or 0)
    if liquidity_usd > 0 and volume_24h > 0:
        # Volume to liquidity ratio - healthy is 1-5x
        vol_liq_ratio = volume_24h / liquidity_usd
        if vol_liq_ratio > 5:
            liq_score = -0.2  # Too much volume relative to liquidity = risky
        elif vol_liq_ratio > 1:
            liq_score = 0.2   # Healthy trading activity
        elif vol_liq_ratio > 0.3:
            liq_score = 0.1   # Moderate activity
        else:
            liq_score = -0.1  # Low activity

        factors.append({
            "factor": "liquidity_health",
            "score": round(liq_score, 3),
            "detail": f"Vol/Liq ratio: {vol_liq_ratio:.1f}x (${liquidity_usd:,.0f} liq)"
        })
        total_score += liq_score * 0.10
        total_weight += 0.10

    # 5. Pair Age Factor (weight: 0.15)
    pair_created = pair_data.get("pairCreatedAt")
    if pair_created:
        try:
            created_dt = datetime.fromtimestamp(pair_created / 1000, tz=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600

            if age_hours < 1:
                age_score = -0.3  # Very new = high risk
                age_label = "Very new pair (<1h)"
            elif age_hours < 24:
                age_score = -0.1  # New = moderate risk
                age_label = f"New pair ({age_hours:.0f}h)"
            elif age_hours < 168:  # 1 week
                age_score = 0.1   # Established
                age_label = f"Established ({age_hours/24:.0f}d)"
            else:
                age_score = 0.2   # Mature
                age_label = f"Mature ({age_hours/24:.0f}d)"

            factors.append({
                "factor": "pair_age",
                "score": round(age_score, 3),
                "detail": age_label
            })
            total_score += age_score * 0.15
            total_weight += 0.15
        except Exception:
            pass

    # Calculate final normalized score
    final_score = total_score / total_weight if total_weight > 0 else 0
    final_score = max(-1.0, min(1.0, final_score))

    # 6. AI-powered GPT Sentiment Analysis (weight: 0.20)
    ai_analysis = None
    token_symbol = pair_data.get("baseToken", {}).get("symbol", "UNKNOWN")
    try:
        ai_analysis = await _gpt_sentiment_analysis(token_symbol, pair_data, factors)
        if ai_analysis and abs(ai_analysis.get("ai_score", 0)) > 0.01:
            ai_score = ai_analysis["ai_score"]
            # Blend AI score with on-chain score (20% weight for AI)
            final_score = final_score * 0.80 + ai_score * 0.20
            final_score = max(-1.0, min(1.0, final_score))

            factors.append({
                "factor": "ai_analysis",
                "score": round(ai_score, 3),
                "detail": f"GPT: {ai_analysis.get('reasoning', 'N/A')[:60]}"
            })
    except Exception as e:
        logger.debug(f"AI sentiment skipped: {e}")

    # Determine label
    if final_score > 0.3:
        label = "very_bullish"
    elif final_score > 0.1:
        label = "bullish"
    elif final_score > -0.1:
        label = "neutral"
    elif final_score > -0.3:
        label = "bearish"
    else:
        label = "very_bearish"

    # Calculate confidence adjustment (-0.10 to +0.10)
    confidence_adj = round(final_score * 0.10, 3)

    sentiment = {
        "score": round(final_score, 3),
        "label": label,
        "confidence_adjustment": confidence_adj,
        "factors": factors,
        "data_points": len(factors),
        "ai_analysis": ai_analysis,
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }

    # Cache the result
    await db.sentiment_cache.update_one(
        {"token_mint": token_mint},
        {"$set": {
            "token_mint": token_mint,
            "sentiment": sentiment,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=SENTIMENT_CACHE_MINUTES)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )

    return sentiment


def _neutral_sentiment() -> Dict:
    """Return neutral sentiment when data is unavailable."""
    return {
        "score": 0.0,
        "label": "neutral",
        "confidence_adjustment": 0.0,
        "factors": [],
        "data_points": 0,
        "ai_analysis": None,
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }


async def _gpt_sentiment_analysis(
    token_symbol: str,
    pair_data: Dict,
    on_chain_factors: list
) -> Optional[Dict]:
    """
    Use GPT to analyze token sentiment from aggregated market data.
    Provides a professional trader's perspective on the token.
    """
    if not EMERGENT_LLM_KEY:
        return None

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        # Build concise market context for GPT
        price_changes = pair_data.get("priceChange", {})
        txns = pair_data.get("txns", {})
        volume = pair_data.get("volume", {})
        liquidity = pair_data.get("liquidity", {})

        buys_24h = txns.get("h24", {}).get("buys", 0)
        sells_24h = txns.get("h24", {}).get("sells", 0)
        buys_1h = txns.get("h1", {}).get("buys", 0)
        sells_1h = txns.get("h1", {}).get("sells", 0)

        market_context = f"""Token: {token_symbol}
Price: ${pair_data.get('priceUsd', 'N/A')}
Market Cap: ${pair_data.get('marketCap', 'N/A')}
Liquidity: ${liquidity.get('usd', 'N/A')}
Volume 24h: ${volume.get('h24', 0)}, 1h: ${volume.get('h1', 0)}
Price Change: 5m {price_changes.get('m5', 0)}%, 1h {price_changes.get('h1', 0)}%, 6h {price_changes.get('h6', 0)}%, 24h {price_changes.get('h24', 0)}%
Transactions 24h: {buys_24h} buys / {sells_24h} sells
Transactions 1h: {buys_1h} buys / {sells_1h} sells
On-chain factors: {'; '.join(f['detail'] for f in on_chain_factors[:4])}"""

        prompt = f"""You are a professional Solana crypto trader. Analyze this token's market data and provide a brief trading sentiment assessment.

{market_context}

Respond in EXACTLY this JSON format, nothing else:
{{"sentiment": "bullish" or "bearish" or "neutral", "confidence": 0.0 to 1.0, "reasoning": "one sentence max", "key_signal": "the single most important signal"}}"""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"sentiment-{token_symbol}",
            system_message="You are a professional crypto market analyst. Provide concise JSON sentiment analysis."
        ).with_model("openai", "gpt-4o")

        response = await chat.send_message(UserMessage(text=prompt))
        response_text = str(response).strip()

        # Parse JSON response
        import json
        # Handle markdown code blocks
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        ai_result = json.loads(response_text)

        sentiment_map = {"bullish": 0.3, "neutral": 0.0, "bearish": -0.3}
        ai_score = sentiment_map.get(ai_result.get("sentiment", "neutral"), 0.0)
        ai_confidence = float(ai_result.get("confidence", 0.5))

        return {
            "ai_sentiment": ai_result.get("sentiment", "neutral"),
            "ai_confidence": ai_confidence,
            "ai_score": round(ai_score * ai_confidence, 3),
            "reasoning": ai_result.get("reasoning", ""),
            "key_signal": ai_result.get("key_signal", "")
        }

    except Exception as e:
        logger.warning(f"GPT sentiment analysis failed for {token_symbol}: {e}")
        return None


async def get_confidence_adjustment(token_mint: str, pair_data: Optional[Dict] = None) -> float:
    """
    Get sentiment-based confidence adjustment for a token.

    Returns:
        Float between -0.10 and +0.10
    """
    sentiment = await analyze_token_sentiment(token_mint, pair_data)
    return sentiment.get("confidence_adjustment", 0.0)


async def cleanup_expired_cache():
    """Remove expired sentiment cache entries."""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.sentiment_cache.delete_many({"expires_at": {"$lt": now}})
    if result.deleted_count > 0:
        logger.info(f"Cleaned up {result.deleted_count} expired sentiment entries")
