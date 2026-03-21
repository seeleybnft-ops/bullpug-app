"""
Market Condition Analysis Service

Analyzes market conditions to dynamically tune signal confidence.
Considers volatility, trend strength, volume, and overall market sentiment.
"""

import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MarketConditionAnalyzer:
    """
    Analyzes market conditions to dynamically tune signal confidence.
    Considers volatility, trend strength, volume, and overall market sentiment.
    """
    
    @staticmethod
    async def get_market_conditions() -> Dict[str, Any]:
        """
        Fetch and analyze overall market conditions.
        Returns a market condition assessment with confidence adjustments.
        """
        conditions = {
            "volatility": "normal",  # low, normal, high, extreme
            "trend": "neutral",  # strong_bull, bull, neutral, bear, strong_bear
            "fear_greed": 50,  # 0-100 scale
            "btc_dominance_trend": "stable",  # rising, stable, falling
            "confidence_multiplier": 1.0,  # 0.5 to 1.5
            "trading_recommended": True,
            "reason": ""
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get Bitcoin data as market proxy
                btc_response = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana&vs_currencies=usd&include_24hr_change=true"
                )
                
                if btc_response.status_code == 200:
                    data = btc_response.json()
                    btc_change = data.get("bitcoin", {}).get("usd_24h_change", 0)
                    sol_change = data.get("solana", {}).get("usd_24h_change", 0)
                    
                    # Determine overall market trend
                    avg_change = (btc_change + sol_change) / 2
                    
                    if avg_change > 5:
                        conditions["trend"] = "strong_bull"
                        conditions["confidence_multiplier"] = 1.2
                    elif avg_change > 2:
                        conditions["trend"] = "bull"
                        conditions["confidence_multiplier"] = 1.1
                    elif avg_change < -5:
                        conditions["trend"] = "strong_bear"
                        conditions["confidence_multiplier"] = 0.7
                        conditions["trading_recommended"] = False
                        conditions["reason"] = "Strong bearish market - reduced confidence"
                    elif avg_change < -2:
                        conditions["trend"] = "bear"
                        conditions["confidence_multiplier"] = 0.85
                    
                    # Analyze volatility
                    abs_change = abs(avg_change)
                    if abs_change > 10:
                        conditions["volatility"] = "extreme"
                        conditions["confidence_multiplier"] *= 0.6
                        conditions["trading_recommended"] = False
                        conditions["reason"] = "Extreme volatility detected - trading paused"
                    elif abs_change > 7:
                        conditions["volatility"] = "high"
                        conditions["confidence_multiplier"] *= 0.8
                    elif abs_change < 1:
                        conditions["volatility"] = "low"
                        conditions["confidence_multiplier"] *= 1.05
                    
                    # Estimate fear/greed from price action
                    conditions["fear_greed"] = min(100, max(0, 50 + avg_change * 5))
                    
        except Exception as e:
            logger.warning(f"Failed to fetch market conditions: {e}")
            conditions["reason"] = "Unable to fetch market data - using defaults"
        
        return conditions
    
    @staticmethod
    def adjust_confidence(base_confidence: float, market_conditions: Dict[str, Any]) -> float:
        """
        Adjust signal confidence based on market conditions.
        """
        multiplier = market_conditions.get("confidence_multiplier", 1.0)
        adjusted = base_confidence * multiplier
        
        # Additional adjustments based on fear/greed
        fear_greed = market_conditions.get("fear_greed", 50)
        
        # Extreme fear (< 20) - slightly boost buy signals
        if fear_greed < 20:
            adjusted *= 1.05  # Potential bounce opportunity
        # Extreme greed (> 80) - reduce buy confidence
        elif fear_greed > 80:
            adjusted *= 0.9  # Risk of correction
        
        # Clamp confidence to valid range
        return min(0.95, max(0.1, adjusted))
    
    @staticmethod
    def get_confidence_reason(base_confidence: float, adjusted_confidence: float, market_conditions: Dict[str, Any]) -> str:
        """
        Generate a human-readable explanation for confidence adjustment.
        """
        diff = adjusted_confidence - base_confidence
        reasons = []
        
        if market_conditions.get("volatility") == "extreme":
            reasons.append("Extreme volatility (-40%)")
        elif market_conditions.get("volatility") == "high":
            reasons.append("High volatility (-20%)")
        elif market_conditions.get("volatility") == "low":
            reasons.append("Low volatility (+5%)")
        
        trend = market_conditions.get("trend", "neutral")
        if trend == "strong_bull":
            reasons.append("Strong bull market (+20%)")
        elif trend == "strong_bear":
            reasons.append("Strong bear market (-30%)")
        elif trend == "bull":
            reasons.append("Bull market (+10%)")
        elif trend == "bear":
            reasons.append("Bear market (-15%)")
        
        fear_greed = market_conditions.get("fear_greed", 50)
        if fear_greed < 20:
            reasons.append("Extreme fear (+5% opportunity)")
        elif fear_greed > 80:
            reasons.append("Extreme greed (-10% caution)")
        
        if not reasons:
            return "Normal market conditions"
        
        return f"Adjusted {diff:+.1%}: " + ", ".join(reasons)
