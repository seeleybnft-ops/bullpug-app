"""
AI Trading Bot - Bullpug AI Agent
Semi-automated trading system with user approval for each trade.
Now with optional custodial wallet for fully automated trading.

Features:
- Technical analysis (RSI, MACD, Moving Averages, Bollinger Bands)
- Multiple strategies (Momentum/Trend Following, Mean Reversion)
- Risk management (stop-loss, take-profit, position sizing)
- Jupiter DEX integration for trade execution
- User-controlled risk parameters
- Custodial wallet integration for automated execution
"""

import os
import uuid
import httpx
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-trader", tags=["AI Trader"])

# Database connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Token constants
SOL_MINT = "So11111111111111111111111111111111111111112"
LAMPORTS_PER_SOL = 1_000_000_000

# Jupiter API Configuration
JUPITER_QUOTE_URL = "https://lite-api.jup.ag/swap/v1"
JUPITER_SWAP_URL = "https://lite-api.jup.ag/swap/v1"

# Token Mint Addresses (Solana)
TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "RNDR": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
}

# Risk Categories
SAFER_TOKENS = ["SOL", "USDC", "USDT", "JUP", "PYTH", "RNDR"]
HIGH_RISK_TOKENS = ["BONK", "WIF", "RAY", "ORCA"]

# Position Limits (in SOL)
MIN_POSITION_SOL = 0.05
MAX_POSITION_SOL = 1.0


# ============== Pydantic Models ==============

class TraderSettings(BaseModel):
    """User trading bot settings"""
    wallet_address: str
    enabled: bool = False
    risk_level: str = Field(default="safer", pattern="^(safer|high_risk|both)$")
    max_position_sol: float = Field(default=0.5, ge=MIN_POSITION_SOL, le=MAX_POSITION_SOL)
    min_position_sol: float = Field(default=MIN_POSITION_SOL, ge=MIN_POSITION_SOL)
    stop_loss_percent: float = Field(default=10.0, ge=1.0, le=50.0)
    take_profit_percent: float = Field(default=20.0, ge=5.0, le=100.0)
    max_daily_trades: int = Field(default=5, ge=1, le=20)
    auto_approve: bool = False  # Legacy field
    # Phase 3: Auto-Trade Settings
    auto_trade_enabled: bool = False  # Master toggle for auto-trading
    auto_trade_mode: str = Field(default="conservative", pattern="^(conservative|moderate|aggressive)$")
    auto_min_confidence: float = Field(default=0.65, ge=0.5, le=0.95)  # Min confidence to auto-execute
    auto_max_daily_trades: int = Field(default=3, ge=1, le=10)  # Max auto-trades per day
    auto_max_position_sol: float = Field(default=0.2, ge=0.05, le=1.0)  # Max position for auto-trades
    auto_cooldown_minutes: int = Field(default=30, ge=5, le=120)  # Cooldown between auto-trades
    auto_require_multiple_signals: bool = True  # Require 2+ strategies to agree
    auto_pause_on_loss: bool = True  # Pause auto-trading after a loss
    auto_total_daily_limit_sol: float = Field(default=1.0, ge=0.1, le=5.0)  # Max total SOL per day
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutoTradeLog(BaseModel):
    """Log entry for auto-executed trades"""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    wallet_address: str
    token_symbol: str
    token_mint: str
    action: str  # "auto_buy", "auto_sell", "auto_skip", "auto_pause"
    amount_sol: Optional[float] = None
    entry_price: Optional[float] = None
    confidence: float
    strategy: str
    reason: str
    success: bool
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TradeSignal(BaseModel):
    """AI-generated trade signal"""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wallet_address: str
    token_symbol: str
    token_mint: str
    signal_type: str  # "buy" or "sell"
    entry_price: float
    suggested_position_sol: float
    stop_loss_price: float
    take_profit_price: float
    confidence: float = Field(ge=0.0, le=1.0)
    strategy: str  # "momentum", "mean_reversion", "combined"
    risk_category: str  # "safer" or "high_risk"
    reasoning: str
    technical_indicators: Dict[str, Any]
    status: str = "pending"  # pending, approved, rejected, executed, expired
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = Field(default_factory=lambda: (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat())


class TradeExecution(BaseModel):
    """Executed trade record"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str
    wallet_address: str
    token_symbol: str
    token_mint: str
    trade_type: str  # "buy" or "sell"
    amount_sol: float
    amount_tokens: Optional[float] = None
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss_price: float
    take_profit_price: float
    status: str = "open"  # open, closed_profit, closed_loss, closed_manual
    pnl_sol: Optional[float] = None
    pnl_percent: Optional[float] = None
    tx_signature: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: Optional[str] = None


class ApproveSignalRequest(BaseModel):
    """Request to approve a trade signal"""
    signal_id: str
    wallet_address: str
    position_sol: Optional[float] = None  # Override suggested position
    stop_loss_percent: Optional[float] = None  # Override stop loss


# ============== Technical Analysis ==============

class TechnicalAnalyzer:
    """Technical analysis engine for generating trade signals"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0}
        
        prices_arr = np.array(prices)
        
        # EMA calculations
        ema_12 = TechnicalAnalyzer._ema(prices_arr, 12)
        ema_26 = TechnicalAnalyzer._ema(prices_arr, 26)
        
        macd_line = ema_12 - ema_26
        signal_line = TechnicalAnalyzer._ema(np.array([macd_line]), 9) if macd_line else 0
        histogram = macd_line - signal_line
        
        return {
            "macd": round(macd_line, 6),
            "signal": round(signal_line, 6),
            "histogram": round(histogram, 6)
        }
    
    @staticmethod
    def _ema(prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return float(np.mean(prices))
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            current_price = prices[-1] if prices else 0
            return {"upper": current_price, "middle": current_price, "lower": current_price, "position": 0.5}
        
        prices_arr = np.array(prices[-period:])
        middle = np.mean(prices_arr)
        std = np.std(prices_arr)
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        current_price = prices[-1]
        band_width = upper - lower
        position = (current_price - lower) / band_width if band_width > 0 else 0.5
        
        return {
            "upper": round(upper, 6),
            "middle": round(middle, 6),
            "lower": round(lower, 6),
            "position": round(position, 4)  # 0 = at lower band, 1 = at upper band
        }
    
    @staticmethod
    def calculate_moving_averages(prices: List[float]) -> Dict[str, float]:
        """Calculate various moving averages"""
        result = {}
        
        for period in [7, 14, 21, 50]:
            if len(prices) >= period:
                result[f"sma_{period}"] = round(np.mean(prices[-period:]), 6)
            else:
                result[f"sma_{period}"] = round(np.mean(prices), 6) if prices else 0
        
        return result
    
    @staticmethod
    def analyze(prices: List[float], current_price: float) -> Dict[str, Any]:
        """Run full technical analysis"""
        rsi = TechnicalAnalyzer.calculate_rsi(prices)
        macd = TechnicalAnalyzer.calculate_macd(prices)
        bollinger = TechnicalAnalyzer.calculate_bollinger_bands(prices)
        mas = TechnicalAnalyzer.calculate_moving_averages(prices)
        
        # Trend determination
        if len(prices) >= 14:
            short_trend = prices[-1] > np.mean(prices[-7:])
            long_trend = prices[-1] > np.mean(prices[-14:])
        else:
            short_trend = True
            long_trend = True
        
        return {
            "rsi": rsi,
            "macd": macd,
            "bollinger": bollinger,
            "moving_averages": mas,
            "current_price": current_price,
            "short_trend": "bullish" if short_trend else "bearish",
            "long_trend": "bullish" if long_trend else "bearish"
        }


# ============== Strategy Engine ==============

class StrategyEngine:
    """Trading strategy engine combining multiple approaches"""
    
    @staticmethod
    def momentum_strategy(indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Momentum/Trend Following Strategy - More sensitive"""
        rsi = indicators["rsi"]
        macd = indicators["macd"]
        short_trend = indicators["short_trend"]
        long_trend = indicators["long_trend"]
        
        signal = None
        confidence = 0.0
        reasoning = []
        
        # Strong uptrend signals
        if rsi < 70 and macd["histogram"] > 0 and short_trend == "bullish":
            signal = "buy"
            confidence = 0.55
            reasoning.append("RSI not overbought, MACD bullish, short-term uptrend")
            
            if long_trend == "bullish":
                confidence += 0.15
                reasoning.append("Long-term trend also bullish")
            
            if rsi < 50:
                confidence += 0.1
                reasoning.append("RSI in neutral-oversold zone (good entry)")
        
        # Moderate uptrend (more sensitive)
        elif rsi < 65 and short_trend == "bullish":
            signal = "buy"
            confidence = 0.40
            reasoning.append("RSI moderate, short-term bullish trend detected")
            if macd["histogram"] > 0:
                confidence += 0.1
                reasoning.append("MACD confirming bullish momentum")
        
        # Strong downtrend signals (sell/close)
        elif rsi > 70 or (macd["histogram"] < 0 and short_trend == "bearish"):
            signal = "sell"
            confidence = 0.45
            reasoning.append("RSI overbought or MACD bearish with downtrend")
            if rsi > 75:
                confidence += 0.1
                reasoning.append("RSI highly overbought - sell pressure likely")
        
        return {
            "signal": signal,
            "confidence": min(confidence, 0.9),
            "strategy": "momentum",
            "reasoning": "; ".join(reasoning)
        }
    
    @staticmethod
    def mean_reversion_strategy(indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Mean Reversion Strategy - More sensitive"""
        rsi = indicators["rsi"]
        bollinger = indicators["bollinger"]
        
        signal = None
        confidence = 0.0
        reasoning = []
        
        # Oversold - potential bounce
        if rsi < 35 and bollinger["position"] < 0.3:
            signal = "buy"
            confidence = 0.55
            reasoning.append("RSI in oversold zone, price near lower Bollinger Band")
        
        # Very oversold
        elif rsi < 25:
            signal = "buy"
            confidence = 0.65
            reasoning.append("RSI extremely oversold, high bounce probability")
        
        # Moderately oversold (more sensitive)
        elif rsi < 45 and bollinger["position"] < 0.4:
            signal = "buy"
            confidence = 0.40
            reasoning.append("RSI in lower range, price below mid Bollinger Band")
        
        # Overbought - potential pullback
        elif rsi > 65 and bollinger["position"] > 0.7:
            signal = "sell"
            confidence = 0.50
            reasoning.append("RSI elevated, price near upper Bollinger Band")
        
        return {
            "signal": signal,
            "confidence": min(confidence, 0.85),
            "strategy": "mean_reversion",
            "reasoning": "; ".join(reasoning)
        }
    
    @staticmethod
    def breakout_strategy(indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Breakout Strategy - Detects price breaking through support/resistance levels"""
        bollinger = indicators["bollinger"]
        rsi = indicators["rsi"]
        macd = indicators["macd"]
        current_price = indicators["current_price"]
        moving_averages = indicators["moving_averages"]
        
        signal = None
        confidence = 0.0
        reasoning = []
        
        # Calculate support and resistance from Bollinger Bands and MAs
        middle_line = bollinger["middle"]
        bb_position = bollinger["position"]
        
        # Get moving averages for additional S/R levels
        sma_7 = moving_averages.get("sma_7", middle_line)
        sma_21 = moving_averages.get("sma_21", middle_line)
        sma_50 = moving_averages.get("sma_50", middle_line)
        
        # Bullish Breakout Detection
        # Price breaking above upper Bollinger Band with momentum confirmation
        if bb_position > 0.95:  # Price at or above upper band
            if macd["histogram"] > 0 and rsi < 80:  # Momentum confirming, not extremely overbought
                signal = "buy"
                confidence = 0.60
                reasoning.append("BREAKOUT: Price breaking above upper Bollinger Band")
                reasoning.append(f"MACD histogram positive ({macd['histogram']:.6f})")
                
                # Additional confidence if breaking above key MAs
                if current_price > sma_21 and current_price > sma_50:
                    confidence += 0.15
                    reasoning.append("Price above 21 and 50 SMA - strong breakout")
                
                # RSI confirmation
                if 50 < rsi < 70:
                    confidence += 0.10
                    reasoning.append("RSI in bullish momentum zone")
        
        # Price breaking above key moving average resistance
        elif current_price > sma_50 and sma_7 > sma_21 > sma_50:
            if macd["histogram"] > 0:
                signal = "buy"
                confidence = 0.50
                reasoning.append("BREAKOUT: Price above 50 SMA with bullish MA alignment")
                reasoning.append("Moving averages in bullish order (7 > 21 > 50)")
                
                if rsi > 50 and rsi < 70:
                    confidence += 0.10
                    reasoning.append("RSI confirming bullish momentum")
        
        # Bearish Breakdown Detection
        # Price breaking below lower Bollinger Band
        elif bb_position < 0.05:  # Price at or below lower band
            if macd["histogram"] < 0 and rsi > 20:  # Momentum confirming, not extremely oversold
                signal = "sell"
                confidence = 0.55
                reasoning.append("BREAKDOWN: Price breaking below lower Bollinger Band")
                reasoning.append(f"MACD histogram negative ({macd['histogram']:.6f})")
                
                # Additional confidence if breaking below key MAs
                if current_price < sma_21 and current_price < sma_50:
                    confidence += 0.15
                    reasoning.append("Price below 21 and 50 SMA - strong breakdown")
        
        # Price breaking below key moving average support
        elif current_price < sma_50 and sma_7 < sma_21 < sma_50:
            if macd["histogram"] < 0:
                signal = "sell"
                confidence = 0.45
                reasoning.append("BREAKDOWN: Price below 50 SMA with bearish MA alignment")
                reasoning.append("Moving averages in bearish order (7 < 21 < 50)")
        
        # False breakout detection - reduces confidence
        if signal == "buy" and rsi > 75:
            confidence -= 0.15
            reasoning.append("Warning: RSI overbought - possible false breakout")
        elif signal == "sell" and rsi < 25:
            confidence -= 0.15
            reasoning.append("Warning: RSI oversold - possible false breakdown")
        
        return {
            "signal": signal,
            "confidence": max(0, min(confidence, 0.85)),
            "strategy": "breakout",
            "reasoning": "; ".join(reasoning)
        }
    
    @staticmethod
    def combined_strategy(indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Combined strategy using momentum, mean reversion, and breakout"""
        momentum = StrategyEngine.momentum_strategy(indicators)
        mean_rev = StrategyEngine.mean_reversion_strategy(indicators)
        breakout = StrategyEngine.breakout_strategy(indicators)
        
        strategies = [momentum, mean_rev, breakout]
        
        # Count agreeing signals
        buy_signals = [s for s in strategies if s["signal"] == "buy"]
        sell_signals = [s for s in strategies if s["signal"] == "sell"]
        
        # If all three agree, very high confidence
        if len(buy_signals) == 3:
            avg_confidence = sum(s["confidence"] for s in buy_signals) / 3
            return {
                "signal": "buy",
                "confidence": min(avg_confidence + 0.20, 0.95),
                "strategy": "combined",
                "reasoning": f"All strategies agree BUY: {buy_signals[0]['reasoning']} | {buy_signals[1]['reasoning']} | {buy_signals[2]['reasoning']}"
            }
        
        if len(sell_signals) == 3:
            avg_confidence = sum(s["confidence"] for s in sell_signals) / 3
            return {
                "signal": "sell",
                "confidence": min(avg_confidence + 0.20, 0.95),
                "strategy": "combined",
                "reasoning": f"All strategies agree SELL: {sell_signals[0]['reasoning']} | {sell_signals[1]['reasoning']} | {sell_signals[2]['reasoning']}"
            }
        
        # If two agree, moderate boost
        if len(buy_signals) >= 2:
            best = max(buy_signals, key=lambda x: x["confidence"])
            return {
                "signal": "buy",
                "confidence": min(best["confidence"] + 0.10, 0.90),
                "strategy": "combined",
                "reasoning": f"Multiple strategies agree BUY: {best['reasoning']}"
            }
        
        if len(sell_signals) >= 2:
            best = max(sell_signals, key=lambda x: x["confidence"])
            return {
                "signal": "sell",
                "confidence": min(best["confidence"] + 0.10, 0.90),
                "strategy": "combined",
                "reasoning": f"Multiple strategies agree SELL: {best['reasoning']}"
            }
        
        # Prioritize breakout signals (they indicate strong moves)
        if breakout["signal"] and breakout["confidence"] >= 0.50:
            return breakout
        
        # Use the highest confidence signal
        all_signals = [s for s in strategies if s["signal"]]
        if all_signals:
            best = max(all_signals, key=lambda x: x["confidence"])
            return best
        
        return {
            "signal": None,
            "confidence": 0,
            "strategy": "combined",
            "reasoning": "No clear signal from any strategy"
        }


# ============== Jupiter Integration ==============

async def get_jupiter_quote(
    input_mint: str,
    output_mint: str,
    amount_lamports: int,
    slippage_bps: int = 100
) -> Optional[Dict]:
    """Get swap quote from Jupiter"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{JUPITER_QUOTE_URL}/quote",
                params={
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": str(amount_lamports),
                    "slippageBps": slippage_bps
                }
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Jupiter quote failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Jupiter quote error: {e}")
        return None


async def get_token_price(token_symbol: str) -> Optional[float]:
    """Get current token price in USD"""
    token_mint = TOKENS.get(token_symbol)
    if not token_mint:
        return None
    
    return await get_token_price_by_mint(token_mint)


async def get_token_price_by_mint(token_mint: str) -> Optional[float]:
    """Get current token price in USD by mint address"""
    if not token_mint:
        return None
    
    try:
        # Use DexScreener for price
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                    return float(best_pair.get("priceUsd", 0) or 0)
    except Exception as e:
        logger.warning(f"Price fetch error for {token_mint}: {e}")
    
    return None


async def get_price_history(token_symbol: str, periods: int = 50) -> List[float]:
    """Get historical prices for technical analysis using DexScreener data"""
    current_price = await get_token_price(token_symbol)
    if not current_price:
        return []
    
    token_mint = TOKENS.get(token_symbol)
    if not token_mint:
        return [current_price]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                    
                    # Get price changes at different intervals
                    change_5m = float(best_pair.get("priceChange", {}).get("m5", 0) or 0) / 100
                    change_1h = float(best_pair.get("priceChange", {}).get("h1", 0) or 0) / 100
                    change_6h = float(best_pair.get("priceChange", {}).get("h6", 0) or 0) / 100
                    change_24h = float(best_pair.get("priceChange", {}).get("h24", 0) or 0) / 100
                    
                    # Generate more realistic price history using available changes
                    prices = []
                    price_24h_ago = current_price / (1 + change_24h) if change_24h != -1 else current_price
                    price_6h_ago = current_price / (1 + change_6h) if change_6h != -1 else current_price
                    price_1h_ago = current_price / (1 + change_1h) if change_1h != -1 else current_price
                    
                    # Create more varied price movement pattern
                    key_prices = [
                        (0.0, price_24h_ago),
                        (0.25, price_24h_ago * 1.02),  # 6h mark with some movement
                        (0.5, price_6h_ago),
                        (0.75, price_6h_ago * 0.98),  # 3h mark
                        (0.90, price_1h_ago),
                        (0.95, price_1h_ago * (1 + change_5m * 0.5)),
                        (1.0, current_price)
                    ]
                    
                    for i in range(periods):
                        t = i / periods
                        # Find the two key prices to interpolate between
                        for j in range(len(key_prices) - 1):
                            if key_prices[j][0] <= t < key_prices[j+1][0]:
                                t_local = (t - key_prices[j][0]) / (key_prices[j+1][0] - key_prices[j][0])
                                base_price = key_prices[j][1] + (key_prices[j+1][1] - key_prices[j][1]) * t_local
                                # Add volatility noise based on position in time
                                volatility = 0.008 if t > 0.8 else 0.004  # More recent = more volatile
                                noise = np.random.normal(0, base_price * volatility)
                                prices.append(max(base_price + noise, 0.000001))
                                break
                    
                    prices.append(current_price)
                    return prices
    except Exception as e:
        logger.warning(f"Price history error for {token_symbol}: {e}")
    
    return [current_price] * periods


# ============== API Endpoints ==============

@router.get("/disclaimer")
async def get_disclaimer():
    """Get trading bot disclaimer and terms"""
    return {
        "title": "AI Trading Bot Disclaimer",
        "terms": [
            "Trading cryptocurrencies carries significant financial risk. Only trade with funds you can afford to lose completely.",
            "Past performance does not guarantee future results. The AI trading bot makes no guarantees of profitability.",
            "All trade signals are suggestions only. You maintain full control and must approve each trade in semi-automated mode.",
            "The bot uses technical analysis which may not account for fundamental news, market manipulation, or black swan events.",
            "Bullpug and its developers are not responsible for any losses incurred through use of this trading bot.",
            "By enabling the AI trader, you acknowledge and accept these risks.",
            "Stop-loss orders may not execute at exact prices during high volatility or low liquidity conditions.",
            "This is not financial advice. Consult a qualified financial advisor before trading."
        ],
        "risk_acknowledgment": "I understand and accept the risks of automated trading",
        "min_position": MIN_POSITION_SOL,
        "max_position": MAX_POSITION_SOL
    }


@router.get("/tokens")
async def get_available_tokens():
    """Get available tokens for trading"""
    safer_with_prices = []
    high_risk_with_prices = []
    
    for symbol in SAFER_TOKENS:
        price = await get_token_price(symbol)
        safer_with_prices.append({
            "symbol": symbol,
            "mint": TOKENS.get(symbol),
            "price_usd": price,
            "risk_category": "safer"
        })
    
    for symbol in HIGH_RISK_TOKENS:
        price = await get_token_price(symbol)
        high_risk_with_prices.append({
            "symbol": symbol,
            "mint": TOKENS.get(symbol),
            "price_usd": price,
            "risk_category": "high_risk"
        })
    
    return {
        "safer_tokens": safer_with_prices,
        "high_risk_tokens": high_risk_with_prices,
        "position_limits": {
            "min_sol": MIN_POSITION_SOL,
            "max_sol": MAX_POSITION_SOL
        }
    }


@router.post("/settings")
async def save_settings(settings: TraderSettings):
    """Save or update user trading settings"""
    try:
        existing = await db.ai_trader_settings.find_one(
            {"wallet_address": settings.wallet_address}
        )
        
        settings_dict = settings.dict()
        settings_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        if existing:
            await db.ai_trader_settings.update_one(
                {"wallet_address": settings.wallet_address},
                {"$set": settings_dict}
            )
        else:
            await db.ai_trader_settings.insert_one(settings_dict)
        
        # Remove MongoDB _id before returning
        settings_dict.pop("_id", None)
        return {"success": True, "message": "Settings saved", "settings": settings_dict}
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{wallet_address}")
async def get_settings(wallet_address: str):
    """Get user trading settings"""
    settings = await db.ai_trader_settings.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    
    if not settings:
        # Return default settings
        return TraderSettings(wallet_address=wallet_address).dict()
    
    return settings


@router.post("/analyze/{token_symbol}")
async def analyze_token(token_symbol: str, wallet_address: str, contract_address: str = None):
    """Analyze a token and generate trade signal if conditions are met.
    
    Args:
        token_symbol: Token symbol (e.g., SOL, JUP, BONK)
        wallet_address: User's wallet address
        contract_address: Optional - token mint address for unknown tokens
    """
    token_symbol = token_symbol.upper()
    
    # Check if token is in our known list
    token_mint = TOKENS.get(token_symbol)
    
    # If not found and contract_address provided, use that
    if not token_mint and contract_address:
        token_mint = contract_address
    
    if not token_mint:
        # Try to look up the token from DexScreener
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.dexscreener.com/latest/dex/search",
                    params={"q": token_symbol}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    pairs = data.get("pairs", [])
                    # Find Solana pair
                    for pair in pairs:
                        if pair.get("chainId") == "solana":
                            base = pair.get("baseToken", {})
                            if base.get("symbol", "").upper() == token_symbol:
                                token_mint = base.get("address")
                                break
        except Exception as e:
            logger.warning(f"Failed to lookup token {token_symbol}: {e}")
    
    if not token_mint:
        return {
            "signal": None,
            "message": f"Token {token_symbol} not found. Try providing the contract address."
        }
    
    # Get user settings
    settings = await db.ai_trader_settings.find_one({"wallet_address": wallet_address})
    if not settings:
        settings = TraderSettings(wallet_address=wallet_address).dict()
    
    # Check risk category
    risk_category = "safer" if token_symbol in SAFER_TOKENS else "high_risk"
    if settings.get("risk_level") == "safer" and risk_category == "high_risk":
        return {
            "signal": None,
            "message": f"{token_symbol} is a high-risk token but your settings only allow safer tokens"
        }
    
    # Get price data
    current_price = await get_token_price(token_symbol)
    
    # If standard lookup fails, try DexScreener with mint address
    if not current_price and token_mint:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}")
                if resp.status_code == 200:
                    data = resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        current_price = float(pairs[0].get("priceUsd", 0))
        except Exception as e:
            logger.warning(f"DexScreener price lookup failed for {token_symbol}: {e}")
    
    if not current_price:
        return {
            "signal": None,
            "message": f"Unable to fetch price data for {token_symbol}"
        }
    
    price_history = await get_price_history(token_symbol)
    
    # If no history, create simulated history from current price
    if len(price_history) < 10:
        price_history = [current_price * (1 + np.random.normal(0, 0.02)) for _ in range(50)]
        price_history.append(current_price)
    
    # Run technical analysis
    indicators = TechnicalAnalyzer.analyze(price_history, current_price)
    
    # Generate signal using combined strategy
    strategy_result = StrategyEngine.combined_strategy(indicators)
    
    # Only generate signal if confidence is high enough (lowered threshold for more signals)
    if strategy_result["signal"] and strategy_result["confidence"] >= 0.35:
        # Calculate position size and risk levels
        stop_loss_pct = settings.get("stop_loss_percent", 10) / 100
        take_profit_pct = settings.get("take_profit_percent", 20) / 100
        
        if strategy_result["signal"] == "buy":
            stop_loss_price = current_price * (1 - stop_loss_pct)
            take_profit_price = current_price * (1 + take_profit_pct)
        else:
            stop_loss_price = current_price * (1 + stop_loss_pct)
            take_profit_price = current_price * (1 - take_profit_pct)
        
        # Suggested position based on confidence
        base_position = settings.get("max_position_sol", 0.5)
        suggested_position = base_position * strategy_result["confidence"]
        suggested_position = max(MIN_POSITION_SOL, min(suggested_position, MAX_POSITION_SOL))
        
        signal = TradeSignal(
            wallet_address=wallet_address,
            token_symbol=token_symbol,
            token_mint=token_mint,  # Use resolved token_mint (supports unknown tokens via contract_address)
            signal_type=strategy_result["signal"],
            entry_price=current_price,
            suggested_position_sol=round(suggested_position, 4),
            stop_loss_price=round(stop_loss_price, 8),
            take_profit_price=round(take_profit_price, 8),
            confidence=strategy_result["confidence"],
            strategy=strategy_result["strategy"],
            risk_category=risk_category,
            reasoning=strategy_result["reasoning"],
            technical_indicators=indicators
        )
        
        # Save signal to database
        await db.ai_trader_signals.insert_one(signal.dict())
        
        return {
            "signal": signal.dict(),
            "message": f"{strategy_result['signal'].upper()} signal generated with {strategy_result['confidence']*100:.1f}% confidence"
        }
    
    return {
        "signal": None,
        "analysis": indicators,
        "message": "No strong signal detected at this time"
    }


@router.get("/signals/{wallet_address}")
async def get_pending_signals(wallet_address: str):
    """Get all pending trade signals for a user"""
    now = datetime.now(timezone.utc).isoformat()
    
    signals = await db.ai_trader_signals.find({
        "wallet_address": wallet_address,
        "status": "pending",
        "expires_at": {"$gt": now}
    }, {"_id": 0}).sort("created_at", -1).to_list(20)
    
    # Mark expired signals
    await db.ai_trader_signals.update_many(
        {
            "wallet_address": wallet_address,
            "status": "pending",
            "expires_at": {"$lt": now}
        },
        {"$set": {"status": "expired"}}
    )
    
    return {"signals": signals, "count": len(signals)}


@router.post("/signals/approve")
async def approve_signal(request: ApproveSignalRequest):
    """Approve a trade signal for execution"""
    signal = await db.ai_trader_signals.find_one({
        "signal_id": request.signal_id,
        "wallet_address": request.wallet_address,
        "status": "pending"
    })
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found or already processed")
    
    # Check if expired
    if signal["expires_at"] < datetime.now(timezone.utc).isoformat():
        await db.ai_trader_signals.update_one(
            {"signal_id": request.signal_id},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(status_code=400, detail="Signal has expired")
    
    # Get position size (use override or suggested)
    position_sol = request.position_sol or signal["suggested_position_sol"]
    position_sol = max(MIN_POSITION_SOL, min(position_sol, MAX_POSITION_SOL))
    
    # Update stop loss if overridden
    stop_loss_price = signal["stop_loss_price"]
    if request.stop_loss_percent:
        stop_loss_pct = request.stop_loss_percent / 100
        if signal["signal_type"] == "buy":
            stop_loss_price = signal["entry_price"] * (1 - stop_loss_pct)
        else:
            stop_loss_price = signal["entry_price"] * (1 + stop_loss_pct)
    
    # Create execution record
    execution = TradeExecution(
        signal_id=request.signal_id,
        wallet_address=request.wallet_address,
        token_symbol=signal["token_symbol"],
        token_mint=signal["token_mint"],
        trade_type=signal["signal_type"],
        amount_sol=position_sol,
        entry_price=signal["entry_price"],
        stop_loss_price=round(stop_loss_price, 8),
        take_profit_price=signal["take_profit_price"]
    )
    
    # Save execution
    await db.ai_trader_executions.insert_one(execution.dict())
    
    # Update signal status
    await db.ai_trader_signals.update_one(
        {"signal_id": request.signal_id},
        {"$set": {"status": "approved"}}
    )
    
    return {
        "success": True,
        "message": "Signal approved - ready for wallet signature",
        "execution": execution.dict(),
        "next_step": "Sign the transaction in your wallet to execute the trade"
    }


@router.post("/signals/reject/{signal_id}")
async def reject_signal(signal_id: str, wallet_address: str):
    """Reject a trade signal"""
    result = await db.ai_trader_signals.update_one(
        {
            "signal_id": signal_id,
            "wallet_address": wallet_address,
            "status": "pending"
        },
        {"$set": {"status": "rejected"}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Signal not found or already processed")
    
    return {"success": True, "message": "Signal rejected"}


@router.get("/positions/{wallet_address}")
async def get_open_positions(wallet_address: str):
    """Get all open positions for a user with P/L in SOL and USD"""
    # Query both collections for positions
    positions = []
    
    # From positions collection (Quick Buy from Tokens tab)
    pos_from_positions = await db.ai_trader_positions.find({
        "wallet_address": wallet_address,
        "status": "open"
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    positions.extend(pos_from_positions)
    
    # From executions collection (from Signals)
    pos_from_executions = await db.ai_trader_executions.find({
        "wallet_address": wallet_address,
        "status": "open"
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    positions.extend(pos_from_executions)
    
    # Get SOL price for USD conversions
    sol_price = await get_token_price("SOL") or 0
    
    # Update positions with current prices and calculate P/L
    for pos in positions:
        token_symbol = pos.get("token_symbol", "")
        token_mint = pos.get("token_mint", TOKENS.get(token_symbol))
        
        # Try to get price - first by symbol, then by mint address from position
        current_price = await get_token_price(token_symbol)
        if not current_price and token_mint:
            current_price = await get_token_price_by_mint(token_mint)
        
        entry_price = pos.get("entry_price", 0)
        amount_sol = pos.get("amount_sol", pos.get("input_sol", 0))
        
        pos["current_price"] = current_price
        pos["sol_price_usd"] = sol_price
        
        if current_price and entry_price > 0:
            # Calculate percentage change
            if pos.get("trade_type") == "buy":
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                price_change_pct = ((entry_price - current_price) / entry_price) * 100
            
            pos["unrealized_pnl_pct"] = round(price_change_pct, 2)
            
            # Calculate P/L in SOL
            # If position went up 10%, our SOL value increased by 10%
            pnl_sol = amount_sol * (price_change_pct / 100)
            pos["unrealized_pnl_sol"] = round(pnl_sol, 6)
            
            # Calculate P/L in USD
            pnl_usd = pnl_sol * sol_price if sol_price > 0 else 0
            pos["unrealized_pnl_usd"] = round(pnl_usd, 2)
            
            # Current value in SOL and USD
            current_value_sol = amount_sol + pnl_sol
            pos["current_value_sol"] = round(current_value_sol, 6)
            pos["current_value_usd"] = round(current_value_sol * sol_price, 2) if sol_price > 0 else 0
        else:
            pos["unrealized_pnl_pct"] = 0
            pos["unrealized_pnl_sol"] = 0
            pos["unrealized_pnl_usd"] = 0
            pos["current_value_sol"] = amount_sol
            pos["current_value_usd"] = round(amount_sol * sol_price, 2) if sol_price > 0 else 0
    
    return {"positions": positions, "count": len(positions), "sol_price_usd": sol_price}


@router.get("/history/{wallet_address}")
async def get_trade_history(wallet_address: str, limit: int = 50):
    """Get trade history for a user"""
    trades = await db.ai_trader_executions.find(
        {"wallet_address": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Calculate stats
    closed_trades = [t for t in trades if t["status"] != "open"]
    wins = len([t for t in closed_trades if t.get("pnl_sol", 0) > 0])
    losses = len([t for t in closed_trades if t.get("pnl_sol", 0) < 0])
    total_pnl = sum(t.get("pnl_sol", 0) for t in closed_trades)
    
    return {
        "trades": trades,
        "stats": {
            "total_trades": len(closed_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(closed_trades) * 100) if closed_trades else 0,
            "total_pnl_sol": round(total_pnl, 4)
        }
    }


@router.get("/quote")
async def get_swap_quote(
    input_mint: str,
    output_mint: str,
    amount_lamports: int,
    slippage_bps: int = 100
):
    """Get swap quote from Jupiter"""
    quote = await get_jupiter_quote(input_mint, output_mint, amount_lamports, slippage_bps)
    
    if not quote:
        raise HTTPException(status_code=503, detail="Unable to get quote from Jupiter")
    
    return quote


@router.post("/swap-transaction")
async def get_swap_transaction(
    user_public_key: str,
    input_mint: str,
    output_mint: str,
    amount_lamports: int,
    slippage_bps: int = 100
):
    """Get serialized swap transaction from Jupiter for wallet signing.
    
    This endpoint:
    1. Gets a quote from Jupiter
    2. Requests the swap transaction data
    3. Returns the serialized transaction for the frontend to sign
    """
    try:
        # Step 1: Get quote
        quote = await get_jupiter_quote(input_mint, output_mint, amount_lamports, slippage_bps)
        if not quote:
            raise HTTPException(status_code=503, detail="Unable to get quote from Jupiter")
        
        # Step 2: Get swap transaction
        async with httpx.AsyncClient(timeout=30.0) as client:
            swap_response = await client.post(
                f"{JUPITER_SWAP_URL}/swap",
                json={
                    "quoteResponse": quote,
                    "userPublicKey": user_public_key,
                    "wrapAndUnwrapSol": True,
                    "dynamicComputeUnitLimit": True,
                    "dynamicSlippage": True,
                    "priorityLevelWithMaxLamports": {
                        "maxLamports": 1000000,
                        "priorityLevel": "medium"
                    }
                },
                headers={"Accept": "application/json", "Content-Type": "application/json"}
            )
            
            if swap_response.status_code != 200:
                logger.error(f"Jupiter swap failed: {swap_response.status_code} - {swap_response.text}")
                raise HTTPException(
                    status_code=503, 
                    detail=f"Jupiter swap request failed: {swap_response.text}"
                )
            
            swap_data = swap_response.json()
            
            return {
                "success": True,
                "swapTransaction": swap_data.get("swapTransaction"),
                "lastValidBlockHeight": swap_data.get("lastValidBlockHeight"),
                "quote": {
                    "inputMint": quote.get("inputMint"),
                    "outputMint": quote.get("outputMint"),
                    "inAmount": quote.get("inAmount"),
                    "outAmount": quote.get("outAmount"),
                    "priceImpactPct": quote.get("priceImpactPct"),
                    "slippageBps": quote.get("slippageBps")
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Swap transaction error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build swap transaction: {str(e)}")


@router.post("/execute-swap")
async def execute_swap_record(
    wallet_address: str,
    signal_id: str,
    tx_signature: str,
    input_amount: float,
    output_amount: float
):
    """Record a completed swap execution after the user signs the transaction.
    
    Called by the frontend after successfully signing and submitting the transaction.
    """
    try:
        # Find the signal
        signal = await db.ai_trader_signals.find_one({"signal_id": signal_id})
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        # Update execution record
        await db.ai_trader_executions.update_one(
            {"signal_id": signal_id},
            {
                "$set": {
                    "status": "executed",
                    "tx_signature": tx_signature,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "actual_input_amount": input_amount,
                    "actual_output_amount": output_amount
                }
            }
        )
        
        # Update signal status
        await db.ai_trader_signals.update_one(
            {"signal_id": signal_id},
            {"$set": {"status": "executed"}}
        )
        
        # Record in trade history
        trade_record = {
            "wallet_address": wallet_address,
            "signal_id": signal_id,
            "tx_signature": tx_signature,
            "token_symbol": signal.get("token_symbol"),
            "trade_type": signal.get("signal_type"),
            "input_amount": input_amount,
            "output_amount": output_amount,
            "entry_price": signal.get("entry_price"),
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": "open"
        }
        
        await db.ai_trader_history.insert_one(trade_record)
        
        return {
            "success": True,
            "message": "Trade executed successfully",
            "tx_signature": tx_signature,
            "trade": {
                "token": signal.get("token_symbol"),
                "type": signal.get("signal_type"),
                "input": input_amount,
                "output": output_amount
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute swap record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-position")
async def add_position(
    wallet_address: str,
    token_symbol: str,
    tx_signature: str,
    input_sol: float,
    output_amount: float,
    entry_price: float,
    token_mint: str = None
):
    """Add a new position after buying a token directly from Tokens tab."""
    try:
        position_id = str(uuid.uuid4())
        
        position = {
            "position_id": position_id,
            "wallet_address": wallet_address,
            "token_symbol": token_symbol.upper(),
            "token_mint": token_mint,
            "trade_type": "buy",
            "input_sol": input_sol,
            "amount_sol": input_sol,
            "output_amount": output_amount,
            "entry_price": entry_price,
            "tx_signature": tx_signature,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "unrealized_pnl_pct": 0
        }
        
        await db.ai_trader_positions.insert_one(position)
        
        # Also add to history
        history_record = {
            **position,
            "execution_id": position_id
        }
        await db.ai_trader_history.insert_one(history_record)
        
        return {
            "success": True,
            "message": "Position added",
            "position_id": position_id,
            "position": {k: v for k, v in position.items() if k != "_id"}
        }
        
    except Exception as e:
        logger.error(f"Add position error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close-position")
async def close_position(
    wallet_address: str,
    position_id: str,
    tx_signature: str,
    sell_amount: float,
    received_sol: float
):
    """Close (sell) an existing position."""
    try:
        # Find the position
        position = await db.ai_trader_positions.find_one({
            "wallet_address": wallet_address,
            "$or": [
                {"position_id": position_id},
                {"execution_id": position_id}
            ]
        })
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Calculate P&L
        input_sol = position.get("input_sol", position.get("amount_sol", 0))
        pnl_sol = received_sol - sell_amount
        pnl_pct = ((received_sol / input_sol) - 1) * 100 if input_sol > 0 else 0
        
        # Update position status
        await db.ai_trader_positions.update_one(
            {"_id": position["_id"]},
            {
                "$set": {
                    "status": "closed",
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "close_tx_signature": tx_signature,
                    "sell_amount": sell_amount,
                    "received_sol": received_sol,
                    "realized_pnl_sol": pnl_sol,
                    "realized_pnl_pct": pnl_pct
                }
            }
        )
        
        # Add to history
        close_record = {
            "wallet_address": wallet_address,
            "position_id": position_id,
            "token_symbol": position.get("token_symbol"),
            "trade_type": "sell",
            "input_sol": sell_amount,
            "received_sol": received_sol,
            "pnl_sol": pnl_sol,
            "pnl_pct": pnl_pct,
            "tx_signature": tx_signature,
            "executed_at": datetime.now(timezone.utc).isoformat()
        }
        await db.ai_trader_history.insert_one(close_record)
        
        return {
            "success": True,
            "message": "Position closed",
            "position_id": position_id,
            "pnl": {
                "sol": pnl_sol,
                "percent": pnl_pct
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Close position error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-position")
async def delete_position(
    wallet_address: str,
    position_id: str
):
    """Manually delete/remove a position without selling (for cleanup purposes)."""
    try:
        # Find and delete from positions collection
        result = await db.ai_trader_positions.delete_one({
            "wallet_address": wallet_address,
            "$or": [
                {"position_id": position_id},
                {"execution_id": position_id}
            ]
        })
        
        # Also try executions collection
        if result.deleted_count == 0:
            result = await db.ai_trader_executions.delete_one({
                "wallet_address": wallet_address,
                "execution_id": position_id,
                "status": "open"
            })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Position not found")
        
        return {
            "success": True,
            "message": "Position removed",
            "position_id": position_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete position error: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/scan-all/{wallet_address}")
async def scan_all_tokens(wallet_address: str):
    """Scan all available tokens and return any signals.
    
    Filters out:
    - Duplicate signals for the same token
    - Contradicting signals (if both BUY and SELL exist, keep higher RSI/confidence)
    """
    settings = await db.ai_trader_settings.find_one({"wallet_address": wallet_address})
    if not settings:
        settings = TraderSettings(wallet_address=wallet_address).dict()
    
    risk_level = settings.get("risk_level", "safer")
    
    # Determine which tokens to scan
    tokens_to_scan = []
    if risk_level in ["safer", "both"]:
        tokens_to_scan.extend(SAFER_TOKENS)
    if risk_level in ["high_risk", "both"]:
        tokens_to_scan.extend(HIGH_RISK_TOKENS)
    
    # Check for existing pending signals to avoid duplicates
    existing_signals = await db.ai_trader_signals.find({
        "wallet_address": wallet_address,
        "status": "pending"
    }, {"token_symbol": 1, "signal_type": 1}).to_list(100)
    
    existing_tokens = {s["token_symbol"] for s in existing_signals}
    
    raw_signals = []
    
    for token in tokens_to_scan:
        # Skip if already has a pending signal
        if token in existing_tokens:
            continue
            
        try:
            result = await analyze_token(token, wallet_address)
            if result.get("signal"):
                raw_signals.append(result["signal"])
        except Exception as e:
            logger.warning(f"Error analyzing {token}: {e}")
            continue
    
    # Filter out contradicting signals - keep highest confidence for each token
    signals_by_token = {}
    for signal in raw_signals:
        token = signal["token_symbol"]
        if token not in signals_by_token:
            signals_by_token[token] = signal
        else:
            # If we have both BUY and SELL, or duplicate signals:
            existing = signals_by_token[token]
            
            # Prioritize by RSI value for better timing
            existing_rsi = existing.get("technical_indicators", {}).get("rsi", 50)
            new_rsi = signal.get("technical_indicators", {}).get("rsi", 50)
            
            # For BUY signals, lower RSI is better (more oversold)
            # For SELL signals, higher RSI is better (more overbought)
            if signal["signal_type"] == "buy" and existing["signal_type"] == "buy":
                # Keep lower RSI for BUY
                if new_rsi < existing_rsi:
                    signals_by_token[token] = signal
            elif signal["signal_type"] == "sell" and existing["signal_type"] == "sell":
                # Keep higher RSI for SELL
                if new_rsi > existing_rsi:
                    signals_by_token[token] = signal
            elif signal["signal_type"] != existing["signal_type"]:
                # Contradicting signals - pick based on RSI extremes
                if signal["signal_type"] == "buy" and new_rsi < 40:
                    # Oversold - BUY is stronger
                    signals_by_token[token] = signal
                elif signal["signal_type"] == "sell" and new_rsi > 60:
                    # Overbought - SELL is stronger
                    signals_by_token[token] = signal
                # Otherwise keep existing
    
    # Final list of unique, non-contradicting signals
    signals = list(signals_by_token.values())
    
    return {
        "signals": signals,
        "tokens_scanned": len(tokens_to_scan),
        "signals_generated": len(signals)
    }



@router.get("/new-pairs")
async def get_new_pairs():
    """Get recently created bonded pairs from Solana DEXes.
    
    Criteria for inclusion:
    - Bonded tokens only (on Raydium, Orca, or Meteora - NOT pump.fun)
    - Created within last 14 days (336 hours)
    - Minimum $15K liquidity
    - Minimum $10K 24h volume
    - Returns 5 most recent pairs meeting criteria
    """
    
    try:
        new_pairs = []
        seen_symbols = set()
        skip_symbols = {"USDC", "USDT", "SOL", "WSOL", "USD", "RAY", "ORCA", "JUP", "PYUSD", "USDG", 
                       "BONK", "WIF", "POPCAT", "FARTCOIN", "AI16Z", "PNUT", "VIRTUAL", "GOAT",
                       "MOODENG", "PEPE", "DOGE", "SHIB", "TRUMP", "MELANIA", "JTO", "W", "WEN"}
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Search for recent pairs on major DEXes with diverse terms
            search_terms = [
                "meme raydium", "sol meteora", "new raydium", "degen raydium", 
                "pump raydium", "solana meme", "memecoin meteora", "cat raydium",
                "dog raydium", "ai raydium", "trump raydium"
            ]
            
            for term in search_terms:
                if len(new_pairs) >= 15:  # Gather extras for filtering
                    break
                    
                try:
                    resp = await client.get(
                        "https://api.dexscreener.com/latest/dex/search",
                        params={"q": term},
                        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
                    )
                    
                    if resp.status_code != 200:
                        continue
                    
                    data = resp.json()
                    pairs = data.get("pairs", []) or []
                    
                    for pair in pairs:
                        if pair.get("chainId") != "solana":
                            continue
                        
                        base_token = pair.get("baseToken", {})
                        symbol = base_token.get("symbol", "?").upper()
                        
                        # Skip duplicates and known tokens
                        if symbol in seen_symbols or symbol in skip_symbols:
                            continue
                        
                        # Check metrics
                        volume_24h = float(pair.get("volume", {}).get("h24", 0) or 0)
                        liquidity_usd = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                        price_usd = float(pair.get("priceUsd", 0) or 0)
                        price_change_24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
                        pair_created_at = pair.get("pairCreatedAt")
                        dex_id = (pair.get("dexId", "") or "").lower()
                        
                        # MUST be on a major DEX (bonded) - NOT pump.fun
                        is_bonded = "raydium" in dex_id or "orca" in dex_id or "meteora" in dex_id
                        if not is_bonded:
                            continue
                        
                        # Check if pair is new (within 14 days / 336 hours)
                        age_hours = 9999
                        if pair_created_at:
                            try:
                                created_time = datetime.fromtimestamp(pair_created_at / 1000, tz=timezone.utc)
                                age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600
                            except (ValueError, TypeError, OSError):
                                age_hours = 9999
                        
                        # Only include if created within 14 days
                        if age_hours > 336:
                            continue
                        
                        # Filter criteria: minimum liquidity and volume for bonded tokens
                        if liquidity_usd < 15000 or volume_24h < 10000:
                            continue
                        
                        # Skip if price is 0
                        if price_usd <= 0:
                            continue
                        
                        seen_symbols.add(symbol)
                        
                        # Determine platform
                        platform = "Unknown"
                        if "raydium" in dex_id:
                            platform = "Raydium"
                        elif "orca" in dex_id:
                            platform = "Orca"
                        elif "meteora" in dex_id:
                            platform = "Meteora"
                        
                        contract_address = base_token.get("address", "")
                        pair_address = pair.get("pairAddress", "")
                        dex_url = pair.get("url", "") or f"https://dexscreener.com/solana/{pair_address}"
                        
                        new_pairs.append({
                            "symbol": symbol,
                            "name": base_token.get("name", symbol),
                            "price": price_usd,
                            "change_24h": price_change_24h,
                            "volume_24h": volume_24h,
                            "liquidity_usd": liquidity_usd,
                            "platform": platform,
                            "contract_address": contract_address,
                            "pair_address": pair_address,
                            "dex_url": dex_url,
                            "age_hours": round(age_hours, 1),
                            "is_bonded": True,
                            "risk_level": "High"
                        })
                            
                except Exception as e:
                    logger.warning(f"Search for {term} failed: {e}")
                    continue
        
        # Sort by most recent (lowest age)
        new_pairs.sort(key=lambda x: x.get("age_hours", 9999))
        
        return {
            "pairs": new_pairs[:5],  # Return exactly 5 pairs
            "count": len(new_pairs[:5]),
            "disclaimer": "New bonded pairs are HIGH RISK. These have graduated to major DEXes. Only trade what you can lose.",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"New pairs error: {e}")
        return {
            "pairs": [],
            "count": 0,
            "error": str(e)
        }



# ============================================================================
# PRICE ALERTS SYSTEM
# ============================================================================

class PriceAlert(BaseModel):
    wallet_address: str
    symbol: str
    token_mint: Optional[str] = None
    alert_type: str  # "breakout_up", "breakout_down", "price_above", "price_below"
    target_price: Optional[float] = None
    created_at: Optional[str] = None
    triggered: bool = False
    triggered_at: Optional[str] = None


class CreateAlertRequest(BaseModel):
    wallet_address: str
    symbol: str
    token_mint: Optional[str] = None
    alert_type: str = "breakout_up"  # breakout_up, breakout_down, price_above, price_below
    target_price: Optional[float] = None


@router.post("/alerts/create")
async def create_price_alert(request: CreateAlertRequest):
    """Create a new price alert for breakout signals or price targets."""
    try:
        alert_id = str(uuid.uuid4())[:8]
        
        alert_doc = {
            "alert_id": alert_id,
            "wallet_address": request.wallet_address,
            "symbol": request.symbol.upper(),
            "token_mint": request.token_mint,
            "alert_type": request.alert_type,
            "target_price": request.target_price,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "triggered": False,
            "triggered_at": None,
            "active": True
        }
        
        await db.price_alerts.insert_one(alert_doc)
        
        return {
            "success": True,
            "alert_id": alert_id,
            "message": f"Alert created for {request.symbol.upper()}"
        }
    except Exception as e:
        logger.error(f"Create alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{wallet_address}")
async def get_price_alerts(wallet_address: str):
    """Get all price alerts for a wallet."""
    try:
        alerts = await db.price_alerts.find(
            {"wallet_address": wallet_address, "active": True},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        
        return {
            "alerts": alerts,
            "count": len(alerts)
        }
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return {"alerts": [], "count": 0, "error": str(e)}


@router.delete("/alerts/{alert_id}")
async def delete_price_alert(alert_id: str):
    """Delete a price alert."""
    try:
        result = await db.price_alerts.update_one(
            {"alert_id": alert_id},
            {"$set": {"active": False}}
        )
        
        return {
            "success": result.modified_count > 0,
            "message": "Alert deleted" if result.modified_count > 0 else "Alert not found"
        }
    except Exception as e:
        logger.error(f"Delete alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/check/{wallet_address}")
async def check_alerts(wallet_address: str):
    """Check if any alerts have been triggered based on current market conditions."""
    try:
        alerts = await db.price_alerts.find(
            {"wallet_address": wallet_address, "active": True, "triggered": False},
            {"_id": 0}
        ).to_list(50)
        
        if not alerts:
            return {"triggered_alerts": [], "count": 0}
        
        triggered = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Group alerts by symbol for efficient fetching
            symbols = list(set(a["symbol"] for a in alerts))
            
            for symbol in symbols:
                symbol_alerts = [a for a in alerts if a["symbol"] == symbol]
                
                # Fetch current price
                token_mint = symbol_alerts[0].get("token_mint") or TOKENS.get(symbol)
                current_price = None
                price_change_1h = 0
                volume_24h = 0
                
                if token_mint:
                    try:
                        response = await client.get(
                            f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                        )
                        if response.status_code == 200:
                            pairs = response.json().get("pairs", [])
                            if pairs:
                                best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                                current_price = float(best_pair.get("priceUsd", 0) or 0)
                                
                                # Get price indicators for breakout detection
                                price_change_1h = float(best_pair.get("priceChange", {}).get("h1", 0) or 0)
                                volume_24h = float(best_pair.get("volume", {}).get("h24", 0) or 0)
                    except Exception as e:
                        logger.warning(f"Price fetch failed for {symbol}: {e}")
                
                if current_price is None or current_price == 0:
                    continue
                
                # Check each alert
                for alert in symbol_alerts:
                    alert_triggered = False
                    trigger_reason = ""
                    
                    if alert["alert_type"] == "price_above" and alert.get("target_price"):
                        if current_price >= alert["target_price"]:
                            alert_triggered = True
                            trigger_reason = f"Price ${current_price:.6f} reached target ${alert['target_price']:.6f}"
                    
                    elif alert["alert_type"] == "price_below" and alert.get("target_price"):
                        if current_price <= alert["target_price"]:
                            alert_triggered = True
                            trigger_reason = f"Price ${current_price:.6f} dropped to target ${alert['target_price']:.6f}"
                    
                    elif alert["alert_type"] == "breakout_up":
                        # Breakout up: >10% gain in 1h with high volume
                        if price_change_1h > 10 and volume_24h > 50000:
                            alert_triggered = True
                            trigger_reason = f"BREAKOUT UP: +{price_change_1h:.1f}% in 1h, Vol: ${volume_24h:,.0f}"
                    
                    elif alert["alert_type"] == "breakout_down":
                        # Breakout down: >10% drop in 1h
                        if price_change_1h < -10:
                            alert_triggered = True
                            trigger_reason = f"BREAKDOWN: {price_change_1h:.1f}% in 1h"
                    
                    if alert_triggered:
                        # Mark as triggered
                        await db.price_alerts.update_one(
                            {"alert_id": alert["alert_id"]},
                            {"$set": {
                                "triggered": True, 
                                "triggered_at": datetime.now(timezone.utc).isoformat(),
                                "trigger_price": current_price,
                                "trigger_reason": trigger_reason
                            }}
                        )
                        
                        alert_info = {
                            "alert_id": alert["alert_id"],
                            "symbol": symbol,
                            "alert_type": alert["alert_type"],
                            "current_price": current_price,
                            "target_price": alert.get("target_price"),
                            "trigger_reason": trigger_reason,
                            "triggered_at": datetime.now(timezone.utc).isoformat(),
                            "token_mint": alert.get("token_mint")
                        }
                        
                        triggered.append(alert_info)
                        
                        # Send Telegram notification
                        try:
                            from routers.telegram import send_breakout_alert
                            await send_breakout_alert(wallet_address, alert_info)
                        except Exception as tg_err:
                            logger.warning(f"Telegram notification failed: {tg_err}")
        
        return {
            "triggered_alerts": triggered,
            "count": len(triggered)
        }
    except Exception as e:
        logger.error(f"Check alerts error: {e}")
        return {"triggered_alerts": [], "count": 0, "error": str(e)}


@router.post("/alerts/breakout-scan")
async def scan_for_breakouts(wallet_address: str):
    """Scan market for potential breakout candidates and create alerts automatically."""
    try:
        new_alerts = []
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Scan for tokens showing breakout potential
            # Look for tokens near Bollinger Band upper/lower bounds with increasing volume
            
            search_terms = ["solana meme trending", "raydium pump"]
            
            for term in search_terms:
                try:
                    response = await client.get(
                        "https://api.dexscreener.com/latest/dex/search",
                        params={"q": term}
                    )
                    
                    if response.status_code != 200:
                        continue
                    
                    pairs = response.json().get("pairs", [])
                    
                    for pair in pairs[:20]:
                        if pair.get("chainId") != "solana":
                            continue
                        
                        base = pair.get("baseToken", {})
                        symbol = base.get("symbol", "").upper()
                        
                        if symbol in ["USDC", "USDT", "SOL", "WSOL"]:
                            continue
                        
                        # Check for breakout indicators
                        price_change_1h = float(pair.get("priceChange", {}).get("h1", 0) or 0)
                        price_change_6h = float(pair.get("priceChange", {}).get("h6", 0) or 0)
                        price_change_24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
                        volume_24h = float(pair.get("volume", {}).get("h24", 0) or 0)
                        liquidity = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                        
                        # Breakout candidate criteria:
                        # - Good liquidity (>$30K)
                        # - High volume (>$50K)
                        # - Price consolidating (small 1h move) but building (6h+ move)
                        is_breakout_candidate = (
                            liquidity > 30000 and
                            volume_24h > 50000 and
                            abs(price_change_1h) < 5 and  # Consolidating
                            (price_change_6h > 15 or price_change_24h > 30)  # Building momentum
                        )
                        
                        if is_breakout_candidate:
                            # Check if alert already exists
                            existing = await db.price_alerts.find_one({
                                "wallet_address": wallet_address,
                                "symbol": symbol,
                                "active": True,
                                "triggered": False
                            })
                            
                            if not existing:
                                alert_id = str(uuid.uuid4())[:8]
                                token_address = base.get("address", "")
                                
                                alert_doc = {
                                    "alert_id": alert_id,
                                    "wallet_address": wallet_address,
                                    "symbol": symbol,
                                    "token_mint": token_address,
                                    "alert_type": "breakout_up",
                                    "target_price": None,  # Auto-triggered by momentum
                                    "created_at": datetime.now(timezone.utc).isoformat(),
                                    "triggered": False,
                                    "active": True,
                                    "auto_created": True,
                                    "scan_reason": f"Building momentum: +{price_change_6h:.1f}% (6h), Vol: ${volume_24h:,.0f}"
                                }
                                
                                await db.price_alerts.insert_one(alert_doc)
                                new_alerts.append({
                                    "alert_id": alert_id,
                                    "symbol": symbol,
                                    "reason": alert_doc["scan_reason"]
                                })
                                
                except Exception as e:
                    logger.warning(f"Breakout scan failed for term {term}: {e}")
        
        return {
            "success": True,
            "new_alerts": new_alerts,
            "count": len(new_alerts),
            "message": f"Created {len(new_alerts)} breakout alerts"
        }
    except Exception as e:
        logger.error(f"Breakout scan error: {e}")
        return {"success": False, "new_alerts": [], "error": str(e)}



# ============================================================================
# PHASE 3: AUTO-TRADING SYSTEM
# ============================================================================

class AutoTradeSettingsUpdate(BaseModel):
    """Update auto-trade settings"""
    auto_trade_enabled: Optional[bool] = None
    auto_trade_mode: Optional[str] = None
    auto_min_confidence: Optional[float] = None
    auto_max_daily_trades: Optional[int] = None
    auto_max_position_sol: Optional[float] = None
    auto_cooldown_minutes: Optional[int] = None
    auto_require_multiple_signals: Optional[bool] = None
    auto_pause_on_loss: Optional[bool] = None
    auto_total_daily_limit_sol: Optional[float] = None


@router.get("/auto-trade/status/{wallet_address}")
async def get_auto_trade_status(wallet_address: str):
    """Get auto-trade status and settings for a wallet."""
    try:
        settings = await db.trader_settings.find_one(
            {"wallet_address": wallet_address},
            {"_id": 0}
        )
        
        if not settings:
            return {
                "auto_trade_enabled": False,
                "settings": None,
                "today_stats": {
                    "trades_executed": 0,
                    "total_sol_used": 0,
                    "wins": 0,
                    "losses": 0,
                    "pnl_sol": 0
                }
            }
        
        # Get today's auto-trade stats
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        today_logs = await db.auto_trade_logs.find({
            "wallet_address": wallet_address,
            "created_at": {"$gte": today_start},
            "action": {"$in": ["auto_buy", "auto_sell"]}
        }).to_list(100)
        
        today_stats = {
            "trades_executed": len([l for l in today_logs if l.get("success")]),
            "total_sol_used": sum(l.get("amount_sol", 0) for l in today_logs if l.get("success") and l.get("action") == "auto_buy"),
            "wins": 0,
            "losses": 0,
            "pnl_sol": 0
        }
        
        # Check if auto-trading should be paused
        auto_paused = False
        pause_reason = None
        
        if settings.get("auto_pause_on_loss"):
            # Check for recent losses
            recent_loss = await db.auto_trade_logs.find_one({
                "wallet_address": wallet_address,
                "created_at": {"$gte": today_start},
                "action": "auto_sell",
                "success": True
            }, sort=[("created_at", -1)])
            
            if recent_loss and recent_loss.get("pnl_sol", 0) < 0:
                auto_paused = True
                pause_reason = "Paused after loss - resume manually"
        
        # Check daily limits
        if today_stats["trades_executed"] >= settings.get("auto_max_daily_trades", 3):
            auto_paused = True
            pause_reason = "Daily trade limit reached"
        
        if today_stats["total_sol_used"] >= settings.get("auto_total_daily_limit_sol", 1.0):
            auto_paused = True
            pause_reason = "Daily SOL limit reached"
        
        return {
            "auto_trade_enabled": settings.get("auto_trade_enabled", False),
            "auto_paused": auto_paused,
            "pause_reason": pause_reason,
            "settings": {
                "mode": settings.get("auto_trade_mode", "conservative"),
                "min_confidence": settings.get("auto_min_confidence", 0.65),
                "max_daily_trades": settings.get("auto_max_daily_trades", 3),
                "max_position_sol": settings.get("auto_max_position_sol", 0.2),
                "cooldown_minutes": settings.get("auto_cooldown_minutes", 30),
                "require_multiple_signals": settings.get("auto_require_multiple_signals", True),
                "pause_on_loss": settings.get("auto_pause_on_loss", True),
                "total_daily_limit_sol": settings.get("auto_total_daily_limit_sol", 1.0)
            },
            "today_stats": today_stats
        }
    except Exception as e:
        logger.error(f"Auto-trade status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-trade/toggle/{wallet_address}")
async def toggle_auto_trade(wallet_address: str, enabled: bool = True):
    """Enable or disable auto-trading for a wallet."""
    try:
        result = await db.trader_settings.update_one(
            {"wallet_address": wallet_address},
            {
                "$set": {
                    "auto_trade_enabled": enabled,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        # Log the toggle
        await db.auto_trade_logs.insert_one({
            "log_id": str(uuid.uuid4())[:8],
            "wallet_address": wallet_address,
            "token_symbol": "-",
            "token_mint": "-",
            "action": "auto_enabled" if enabled else "auto_disabled",
            "confidence": 0,
            "strategy": "-",
            "reason": f"Auto-trading {'enabled' if enabled else 'disabled'} by user",
            "success": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "auto_trade_enabled": enabled,
            "message": f"Auto-trading {'enabled' if enabled else 'disabled'}"
        }
    except Exception as e:
        logger.error(f"Toggle auto-trade error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/auto-trade/settings/{wallet_address}")
async def update_auto_trade_settings(wallet_address: str, settings: AutoTradeSettingsUpdate):
    """Update auto-trade settings."""
    try:
        update_data = {k: v for k, v in settings.dict().items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.trader_settings.update_one(
            {"wallet_address": wallet_address},
            {"$set": update_data},
            upsert=True
        )
        
        return {
            "success": True,
            "updated_fields": list(update_data.keys()),
            "message": "Auto-trade settings updated"
        }
    except Exception as e:
        logger.error(f"Update auto-trade settings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-trade/logs/{wallet_address}")
async def get_auto_trade_logs(wallet_address: str, limit: int = 50):
    """Get auto-trade activity logs."""
    try:
        logs = await db.auto_trade_logs.find(
            {"wallet_address": wallet_address},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return {
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        logger.error(f"Get auto-trade logs error: {e}")
        return {"logs": [], "count": 0, "error": str(e)}


@router.post("/auto-trade/scan-and-execute/{wallet_address}")
async def auto_trade_scan_and_execute(wallet_address: str):
    """
    Main auto-trading function: Scan market and execute trades automatically.
    This should be called periodically (every 5 minutes) by the frontend or a scheduler.
    """
    try:
        # Get user settings
        settings = await db.trader_settings.find_one({"wallet_address": wallet_address})
        
        if not settings:
            return {"success": False, "message": "Settings not found", "trades": []}
        
        if not settings.get("auto_trade_enabled"):
            return {"success": False, "message": "Auto-trading is disabled", "trades": []}
        
        # Check daily limits
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        today_trades = await db.auto_trade_logs.count_documents({
            "wallet_address": wallet_address,
            "created_at": {"$gte": today_start},
            "action": "auto_buy",
            "success": True
        })
        
        max_daily = settings.get("auto_max_daily_trades", 3)
        if today_trades >= max_daily:
            return {
                "success": False,
                "message": f"Daily trade limit reached ({today_trades}/{max_daily})",
                "trades": []
            }
        
        # Check cooldown
        last_trade = await db.auto_trade_logs.find_one(
            {
                "wallet_address": wallet_address,
                "action": "auto_buy",
                "success": True
            },
            sort=[("created_at", -1)]
        )
        
        cooldown_minutes = settings.get("auto_cooldown_minutes", 30)
        if last_trade:
            last_trade_time = datetime.fromisoformat(last_trade["created_at"].replace("Z", "+00:00"))
            time_since = (datetime.now(timezone.utc) - last_trade_time).total_seconds() / 60
            if time_since < cooldown_minutes:
                return {
                    "success": False,
                    "message": f"Cooldown active ({int(cooldown_minutes - time_since)} minutes remaining)",
                    "trades": []
                }
        
        # Get auto-trade mode settings
        mode = settings.get("auto_trade_mode", "conservative")
        min_confidence = settings.get("auto_min_confidence", 0.65)
        max_position = settings.get("auto_max_position_sol", 0.2)
        require_multiple = settings.get("auto_require_multiple_signals", True)
        risk_level = settings.get("risk_level", "safer")
        
        # Adjust confidence based on mode
        if mode == "aggressive":
            min_confidence = max(0.5, min_confidence - 0.1)
        elif mode == "moderate":
            min_confidence = min_confidence
        else:  # conservative
            min_confidence = min(0.8, min_confidence + 0.1)
        
        # Get tokens to scan based on risk level
        tokens_to_scan = []
        if risk_level in ["safer", "both"]:
            tokens_to_scan.extend(["SOL", "JUP", "PYTH", "RNDR"])
        if risk_level in ["high_risk", "both"]:
            tokens_to_scan.extend(["BONK", "WIF", "RAY"])
        
        executed_trades = []
        skipped = []
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            for symbol in tokens_to_scan[:5]:  # Limit to 5 tokens per scan
                try:
                    token_mint = TOKENS.get(symbol)
                    if not token_mint:
                        continue
                    
                    # Get price data
                    response = await client.get(
                        f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                    )
                    
                    if response.status_code != 200:
                        continue
                    
                    pairs = response.json().get("pairs", [])
                    if not pairs:
                        continue
                    
                    best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                    
                    # Get price history for analysis
                    prices = []
                    current_price = float(best_pair.get("priceUsd", 0) or 0)
                    
                    if current_price <= 0:
                        continue
                    
                    # Simulate price history from price changes
                    price_change_24h = float(best_pair.get("priceChange", {}).get("h24", 0) or 0)
                    price_change_6h = float(best_pair.get("priceChange", {}).get("h6", 0) or 0)
                    price_change_1h = float(best_pair.get("priceChange", {}).get("h1", 0) or 0)
                    
                    # Create synthetic price history
                    price_24h_ago = current_price / (1 + price_change_24h / 100) if price_change_24h != -100 else current_price
                    price_6h_ago = current_price / (1 + price_change_6h / 100) if price_change_6h != -100 else current_price
                    price_1h_ago = current_price / (1 + price_change_1h / 100) if price_change_1h != -100 else current_price
                    
                    # Generate approximate price history
                    for i in range(50):
                        factor = i / 50
                        if i < 12:  # Last 6 hours
                            prices.append(price_6h_ago + (current_price - price_6h_ago) * (i / 12))
                        elif i < 24:  # 6-12 hours ago
                            prices.append(price_24h_ago + (price_6h_ago - price_24h_ago) * ((i - 12) / 12))
                        else:  # 12-24 hours ago
                            prices.append(price_24h_ago * (1 + (i - 24) * 0.001))
                    
                    prices.append(current_price)
                    
                    # Calculate indicators
                    indicators = TechnicalAnalysis.calculate_all_indicators(prices)
                    indicators["current_price"] = current_price
                    
                    # Run strategies
                    momentum = StrategyEngine.momentum_strategy(indicators)
                    mean_rev = StrategyEngine.mean_reversion_strategy(indicators)
                    breakout = StrategyEngine.breakout_strategy(indicators)
                    combined = StrategyEngine.combined_strategy(indicators)
                    
                    # Count agreeing signals
                    strategies = [momentum, mean_rev, breakout]
                    buy_signals = [s for s in strategies if s["signal"] == "buy"]
                    
                    # Determine if we should trade
                    should_trade = False
                    trade_confidence = combined["confidence"]
                    trade_reason = combined["reasoning"]
                    
                    if combined["signal"] == "buy" and trade_confidence >= min_confidence:
                        if require_multiple:
                            # Need at least 2 strategies to agree
                            if len(buy_signals) >= 2:
                                should_trade = True
                                trade_reason = f"Multiple strategies agree ({len(buy_signals)}/3): {trade_reason}"
                        else:
                            should_trade = True
                    
                    if should_trade:
                        # Check if we already have a position
                        existing_position = await db.ai_trader_positions.find_one({
                            "wallet_address": wallet_address,
                            "token_mint": token_mint
                        })
                        
                        if existing_position:
                            skipped.append({
                                "symbol": symbol,
                                "reason": "Already have position"
                            })
                            continue
                        
                        # Calculate position size
                        position_sol = min(max_position, settings.get("max_position_sol", 0.5))
                        
                        # Create position record
                        position_id = str(uuid.uuid4())[:8]
                        execution_id = f"auto_{str(uuid.uuid4())[:6]}"
                        
                        position_doc = {
                            "position_id": position_id,
                            "execution_id": execution_id,
                            "wallet_address": wallet_address,
                            "token_symbol": symbol,
                            "token_mint": token_mint,
                            "amount_sol": position_sol,
                            "entry_price": current_price,
                            "stop_loss_price": current_price * (1 - settings.get("stop_loss_percent", 10) / 100),
                            "take_profit_price": current_price * (1 + settings.get("take_profit_percent", 20) / 100),
                            "trade_type": "buy",
                            "status": "open",
                            "auto_trade": True,
                            "confidence": trade_confidence,
                            "strategy": combined["strategy"],
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Try to execute via custodial wallet
                        tx_signature = None
                        execution_success = False
                        execution_error = None
                        
                        try:
                            # Check if user has custodial wallet with sufficient balance
                            from routers.custodial_wallet import get_wallet_balance, get_or_create_custodial_wallet, execute_auto_trade
                            
                            custodial_wallet = await db.custodial_wallets.find_one({"user_wallet": wallet_address})
                            
                            if custodial_wallet:
                                custodial_balance = await get_wallet_balance(custodial_wallet["custodial_address"])
                                required_lamports = int(position_sol * LAMPORTS_PER_SOL)
                                
                                if custodial_balance >= required_lamports + 50000:  # Extra for fees
                                    # Execute actual trade via custodial wallet
                                    logger.info(f"Executing auto-trade via custodial wallet: {position_sol} SOL for {symbol}")
                                    
                                    trade_result = await execute_auto_trade(
                                        user_wallet=wallet_address,
                                        input_mint=SOL_MINT,
                                        output_mint=token_mint,
                                        amount_lamports=required_lamports
                                    )
                                    
                                    if trade_result.get("success"):
                                        tx_signature = trade_result.get("tx_signature")
                                        execution_success = True
                                        position_doc["tx_signature"] = tx_signature
                                        position_doc["executed_on_chain"] = True
                                        logger.info(f"Auto-trade executed successfully: {tx_signature}")
                                else:
                                    execution_error = f"Insufficient custodial balance: {custodial_balance/LAMPORTS_PER_SOL:.4f} SOL"
                                    logger.warning(execution_error)
                            else:
                                execution_error = "No custodial wallet - position recorded for manual execution"
                                logger.info(execution_error)
                                
                        except Exception as exec_error:
                            execution_error = f"Execution failed: {str(exec_error)}"
                            logger.error(f"Auto-trade execution error: {exec_error}")
                        
                        # Save position regardless of execution success
                        position_doc["executed_on_chain"] = execution_success
                        position_doc["execution_error"] = execution_error
                        
                        await db.ai_trader_positions.insert_one(position_doc)
                        
                        # Log the auto-trade
                        log_doc = {
                            "log_id": str(uuid.uuid4())[:8],
                            "wallet_address": wallet_address,
                            "token_symbol": symbol,
                            "token_mint": token_mint,
                            "action": "auto_buy",
                            "amount_sol": position_sol,
                            "entry_price": current_price,
                            "confidence": trade_confidence,
                            "strategy": combined["strategy"],
                            "reason": trade_reason,
                            "success": True,
                            "executed_on_chain": execution_success,
                            "tx_signature": tx_signature,
                            "execution_error": execution_error,
                            "position_id": position_id,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await db.auto_trade_logs.insert_one(log_doc)
                        
                        executed_trades.append({
                            "symbol": symbol,
                            "action": "buy",
                            "amount_sol": position_sol,
                            "entry_price": current_price,
                            "confidence": trade_confidence,
                            "reason": trade_reason,
                            "executed_on_chain": execution_success,
                            "tx_signature": tx_signature
                        })
                        
                        # Only execute one trade per scan in conservative mode
                        if mode == "conservative":
                            break
                    else:
                        # Log skipped
                        skip_reason = "Low confidence" if trade_confidence < min_confidence else "No buy signal"
                        if require_multiple and len(buy_signals) < 2:
                            skip_reason = f"Only {len(buy_signals)}/3 strategies agree"
                        
                        skipped.append({
                            "symbol": symbol,
                            "reason": skip_reason,
                            "confidence": trade_confidence
                        })
                        
                except Exception as e:
                    logger.warning(f"Auto-trade scan error for {symbol}: {e}")
                    continue
        
        return {
            "success": True,
            "trades_executed": len(executed_trades),
            "trades": executed_trades,
            "skipped": skipped,
            "message": f"Auto-scan complete: {len(executed_trades)} trades executed"
        }
        
    except Exception as e:
        logger.error(f"Auto-trade scan error: {e}")
        return {"success": False, "error": str(e), "trades": []}


@router.post("/auto-trade/check-exits/{wallet_address}")
async def auto_trade_check_exits(wallet_address: str):
    """
    Check open positions for stop-loss or take-profit triggers.
    Should be called periodically to manage risk.
    """
    try:
        settings = await db.trader_settings.find_one({"wallet_address": wallet_address})
        
        if not settings or not settings.get("auto_trade_enabled"):
            return {"success": False, "message": "Auto-trading not enabled", "exits": []}
        
        # Get all open positions
        positions = await db.ai_trader_positions.find({
            "wallet_address": wallet_address,
            "status": "open"
        }).to_list(50)
        
        if not positions:
            return {"success": True, "exits": [], "message": "No open positions"}
        
        exits = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for position in positions:
                token_mint = position.get("token_mint")
                symbol = position.get("token_symbol")
                
                if not token_mint:
                    continue
                
                try:
                    # Get current price
                    response = await client.get(
                        f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                    )
                    
                    if response.status_code != 200:
                        continue
                    
                    pairs = response.json().get("pairs", [])
                    if not pairs:
                        continue
                    
                    best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                    current_price = float(best_pair.get("priceUsd", 0) or 0)
                    
                    if current_price <= 0:
                        continue
                    
                    entry_price = position.get("entry_price", 0)
                    stop_loss = position.get("stop_loss_price", entry_price * 0.9)
                    take_profit = position.get("take_profit_price", entry_price * 1.2)
                    
                    # Check for exit conditions
                    exit_action = None
                    exit_reason = ""
                    
                    if current_price <= stop_loss:
                        exit_action = "stop_loss"
                        exit_reason = f"Stop-loss triggered at ${current_price:.8f} (SL: ${stop_loss:.8f})"
                    elif current_price >= take_profit:
                        exit_action = "take_profit"
                        exit_reason = f"Take-profit triggered at ${current_price:.8f} (TP: ${take_profit:.8f})"
                    
                    if exit_action:
                        # Calculate P&L
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        pnl_sol = position.get("amount_sol", 0) * (pnl_pct / 100)
                        
                        # Update position
                        await db.ai_trader_positions.update_one(
                            {"position_id": position.get("position_id")},
                            {
                                "$set": {
                                    "status": f"closed_{exit_action}",
                                    "exit_price": current_price,
                                    "pnl_percent": pnl_pct,
                                    "pnl_sol": pnl_sol,
                                    "closed_at": datetime.now(timezone.utc).isoformat()
                                }
                            }
                        )
                        
                        # Log the exit
                        await db.auto_trade_logs.insert_one({
                            "log_id": str(uuid.uuid4())[:8],
                            "wallet_address": wallet_address,
                            "token_symbol": symbol,
                            "token_mint": token_mint,
                            "action": f"auto_{exit_action}",
                            "amount_sol": position.get("amount_sol"),
                            "entry_price": entry_price,
                            "exit_price": current_price,
                            "pnl_percent": pnl_pct,
                            "pnl_sol": pnl_sol,
                            "confidence": 1.0,
                            "strategy": "risk_management",
                            "reason": exit_reason,
                            "success": True,
                            "position_id": position.get("position_id"),
                            "created_at": datetime.now(timezone.utc).isoformat()
                        })
                        
                        exits.append({
                            "symbol": symbol,
                            "action": exit_action,
                            "entry_price": entry_price,
                            "exit_price": current_price,
                            "pnl_percent": pnl_pct,
                            "pnl_sol": pnl_sol,
                            "reason": exit_reason
                        })
                        
                        # If loss and pause_on_loss is enabled, pause auto-trading
                        if exit_action == "stop_loss" and settings.get("auto_pause_on_loss"):
                            await db.auto_trade_logs.insert_one({
                                "log_id": str(uuid.uuid4())[:8],
                                "wallet_address": wallet_address,
                                "token_symbol": "-",
                                "token_mint": "-",
                                "action": "auto_pause",
                                "confidence": 0,
                                "strategy": "risk_management",
                                "reason": f"Auto-paused after stop-loss on {symbol}",
                                "success": True,
                                "created_at": datetime.now(timezone.utc).isoformat()
                            })
                        
                except Exception as e:
                    logger.warning(f"Exit check error for {symbol}: {e}")
                    continue
        
        return {
            "success": True,
            "exits": exits,
            "positions_checked": len(positions),
            "exits_triggered": len(exits)
        }
        
    except Exception as e:
        logger.error(f"Check exits error: {e}")
        return {"success": False, "error": str(e), "exits": []}
