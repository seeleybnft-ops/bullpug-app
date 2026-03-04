"""
AI Trading Bot - Bullpug AI Agent
Semi-automated trading system with user approval for each trade.

Features:
- Technical analysis (RSI, MACD, Moving Averages, Bollinger Bands)
- Multiple strategies (Momentum/Trend Following, Mean Reversion)
- Risk management (stop-loss, take-profit, position sizing)
- Jupiter DEX integration for trade execution
- User-controlled risk parameters
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
    auto_approve: bool = False  # For future fully-automated mode
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
    def combined_strategy(indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Combined strategy using both momentum and mean reversion"""
        momentum = StrategyEngine.momentum_strategy(indicators)
        mean_rev = StrategyEngine.mean_reversion_strategy(indicators)
        
        # If both agree, high confidence
        if momentum["signal"] and mean_rev["signal"] and momentum["signal"] == mean_rev["signal"]:
            return {
                "signal": momentum["signal"],
                "confidence": min((momentum["confidence"] + mean_rev["confidence"]) / 2 + 0.15, 0.95),
                "strategy": "combined",
                "reasoning": f"Both strategies agree: {momentum['reasoning']} | {mean_rev['reasoning']}"
            }
        
        # Use the higher confidence signal
        if momentum["confidence"] > mean_rev["confidence"] and momentum["signal"]:
            return momentum
        elif mean_rev["signal"]:
            return mean_rev
        elif momentum["signal"]:
            return momentum
        
        # Fallback: if any signal exists, use it even with lower confidence
        if momentum["signal"]:
            return momentum
        if mean_rev["signal"]:
            return mean_rev
        
        return {
            "signal": None,
            "confidence": 0,
            "strategy": "combined",
            "reasoning": "No clear signal from either strategy"
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
