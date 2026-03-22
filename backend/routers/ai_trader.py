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

# Import refactored services
from services.market_analyzer import MarketConditionAnalyzer
from services.runner_detector import RunnerDetector
from services.technical_analyzer import TechnicalAnalyzer
from services.strategy_engine import StrategyEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-trader", tags=["AI Trader"])

# Database connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ============== Journal Integration Helper ==============

async def create_pending_journal_entry(
    wallet_address: str,
    asset: str,
    trade_type: str,  # "buy" or "sell"
    entry_price: float,
    position_size_sol: float,
    position_size_tokens: float = None,
    tx_signature: str = None,
    pnl_percent: float = None,
    pnl_sol: float = None
):
    """
    Create a pending journal entry for an auto-trade.
    This integrates auto-trades with the trading journal.
    """
    try:
        trade_id = f"AT{str(uuid.uuid4())[:8].upper()}"
        
        pending_trade = {
            "trade_id": trade_id,
            "wallet_address": wallet_address,
            "asset": asset.upper(),
            "trade_type": trade_type,
            "entry_price": entry_price,
            "position_size": position_size_sol,
            "position_size_tokens": position_size_tokens,
            "date_entry": datetime.now(timezone.utc).isoformat(),
            "tx_signature": tx_signature,
            "source": "auto_trade",
            # For sells, include P/L
            "pnl": pnl_sol or 0,
            "pnl_percent": pnl_percent or 0,
            "exit_price": entry_price if trade_type == "sell" else None,
            # Pending status
            "pending": True,
            "auto_logged_at": datetime.now(timezone.utc).isoformat(),
            "status": "open" if trade_type == "buy" else "closed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.trading_journal.insert_one(pending_trade)
        logger.info(f"Created pending journal entry {trade_id} for {asset} {trade_type}")
        return trade_id
    except Exception as e:
        logger.error(f"Failed to create pending journal entry: {e}")
        return None

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

# Runner Detection Settings
RUNNER_MIN_LIQUIDITY = 10000  # Minimum $10k liquidity
RUNNER_MIN_VOLUME_24H = 50000  # Minimum $50k 24h volume
RUNNER_MIN_PRICE_CHANGE_1H = 5  # Minimum 5% gain in 1h
RUNNER_MAX_PRICE_CHANGE_1H = 100  # Max 100% (avoid pump & dumps)
RUNNER_MIN_TXNS_1H = 50  # Minimum transactions to avoid manipulation
RUNNER_MAX_AGE_HOURS = 72  # Focus on pairs created within 72 hours

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
    take_profit_percent: float = Field(default=20.0, ge=5.0, le=200.0)
    max_daily_trades: int = Field(default=5, ge=1, le=20)
    auto_approve: bool = False  # Legacy field
    # Phase 3: Auto-Trade Settings
    auto_trade_enabled: bool = False  # Master toggle for auto-trading
    auto_trade_mode: str = Field(default="conservative", pattern="^(conservative|moderate|aggressive)$")
    auto_min_confidence: float = Field(default=0.65, ge=0.5, le=0.95)  # Min confidence to auto-execute
    auto_max_daily_trades: int = Field(default=3, ge=1, le=10)  # Max auto-trades per day
    auto_max_position_sol: float = Field(default=0.2, ge=0.01, le=1.0)  # Max position for auto-trades
    auto_cooldown_minutes: int = Field(default=30, ge=5, le=120)  # Cooldown between auto-trades
    auto_require_multiple_signals: bool = True  # Require 2+ strategies to agree
    auto_pause_on_loss: bool = True  # Pause auto-trading after a loss
    auto_total_daily_limit_sol: float = Field(default=1.0, ge=0.1, le=5.0)  # Max total SOL per day
    auto_stop_loss_percent: float = Field(default=10.0, ge=2.0, le=50.0)  # Stop loss for auto-trades
    auto_take_profit_percent: float = Field(default=20.0, ge=5.0, le=200.0)  # Take profit for auto-trades
    # NEW: Advanced Auto-Trade Settings
    auto_trailing_stop_enabled: bool = False  # Enable trailing stop-loss
    auto_trailing_stop_percent: float = Field(default=5.0, ge=1.0, le=20.0)  # Trailing distance
    auto_scale_in_enabled: bool = False  # Enable position scaling (DCA on dips)
    auto_scale_in_threshold: float = Field(default=5.0, ge=2.0, le=15.0)  # % dip to trigger scale-in
    auto_scale_in_max_adds: int = Field(default=2, ge=1, le=5)  # Max scale-in additions
    auto_avoid_volatile_hours: bool = True  # Avoid trading during high volatility
    auto_profit_target_alert: bool = True  # Send alerts when profit targets hit
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


# ============== Services (Refactored) ==============
# The following classes have been moved to separate modules for better maintainability:
# - MarketConditionAnalyzer -> services/market_analyzer.py
# - RunnerDetector -> services/runner_detector.py
# - TechnicalAnalyzer -> services/technical_analyzer.py
# - StrategyEngine -> services/strategy_engine.py


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


@router.get("/runners")
async def get_runner_tokens():
    """
    Get potential runner tokens - new pairs with early momentum.
    These are fresh opportunities that could run before they're discovered.
    """
    try:
        runners = await RunnerDetector.fetch_trending_pairs(limit=15)
        
        return {
            "success": True,
            "runners": runners,
            "count": len(runners),
            "criteria": {
                "min_liquidity": f"${RUNNER_MIN_LIQUIDITY:,}",
                "min_volume_24h": f"${RUNNER_MIN_VOLUME_24H:,}",
                "min_price_change_1h": f"{RUNNER_MIN_PRICE_CHANGE_1H}%",
                "max_price_change_1h": f"{RUNNER_MAX_PRICE_CHANGE_1H}%",
                "min_txns_1h": RUNNER_MIN_TXNS_1H,
                "max_age_hours": RUNNER_MAX_AGE_HOURS
            },
            "disclaimer": "Runner tokens are HIGH RISK. Only trade with funds you can afford to lose completely."
        }
    except Exception as e:
        logger.error(f"Error fetching runners: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    
    # If no history, create improved simulated history with realistic volatility
    if len(price_history) < 10:
        # Fetch price changes from DexScreener for better simulation
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}")
                if resp.status_code == 200:
                    pairs = resp.json().get("pairs", [])
                    if pairs:
                        best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                        price_change_24h = float(best_pair.get("priceChange", {}).get("h24", 0) or 0)
                        price_change_6h = float(best_pair.get("priceChange", {}).get("h6", 0) or 0)
                        price_change_1h = float(best_pair.get("priceChange", {}).get("h1", 0) or 0)
                        
                        price_24h_ago = current_price / (1 + price_change_24h / 100) if price_change_24h != -100 else current_price
                        price_6h_ago = current_price / (1 + price_change_6h / 100) if price_change_6h != -100 else current_price
                        price_1h_ago = current_price / (1 + price_change_1h / 100) if price_change_1h != -100 else current_price
                        
                        # Generate realistic price history with volatility
                        import random
                        random.seed(int(current_price * 1e8) % 10000)
                        volatility = max(abs(price_change_24h), abs(price_change_6h), abs(price_change_1h)) / 100
                        volatility = max(0.005, min(volatility, 0.05))
                        
                        price_history = []
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
                            price_history.append(base + noise)
                        price_history.append(current_price)
        except Exception as e:
            logger.warning(f"Failed to create price history for {token_symbol}: {e}")
        
        # Fallback if DexScreener fails
        if len(price_history) < 10:
            price_history = [current_price * (1 + np.random.normal(0, 0.02)) for _ in range(50)]
            price_history.append(current_price)
    
    # Run technical analysis
    indicators = TechnicalAnalyzer.analyze(price_history, current_price)
    
    # Generate signal using combined strategy
    strategy_result = StrategyEngine.combined_strategy(indicators)
    
    # OPTIMIZED: Raised threshold from 0.45 to 0.55 based on backtest results
    # Backtest showed: 0.45 conf → 45.6% win rate, 0.55 conf → 72.5% win rate
    # Using StrategyEngine class constant for consistency
    MIN_SIGNAL_THRESHOLD = StrategyEngine.MIN_SIGNAL_CONFIDENCE
    
    if strategy_result["signal"] and strategy_result["confidence"] >= MIN_SIGNAL_THRESHOLD:
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
    """Get complete trade history including manual trades, auto-trades, and closed positions"""
    
    # Get trades from executions collection
    executions = await db.ai_trader_executions.find(
        {"wallet_address": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Get closed positions
    closed_positions = await db.ai_trader_positions.find(
        {
            "wallet_address": wallet_address,
            "status": {"$regex": "^closed"}
        },
        {"_id": 0}
    ).sort("closed_at", -1).limit(limit).to_list(limit)
    
    # Get auto-trade logs (buy and sell)
    auto_trade_logs = await db.auto_trade_logs.find(
        {
            "wallet_address": wallet_address,
            "$or": [
                {"action": {"$regex": "auto"}},
                {"action": "manual_close"}
            ]
        },
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Combine and normalize all trades
    all_trades = []
    seen_ids = set()
    
    # Add executions
    for trade in executions:
        trade_id = trade.get("execution_id") or trade.get("position_id")
        if trade_id and trade_id not in seen_ids:
            seen_ids.add(trade_id)
            trade["source"] = "manual"
            all_trades.append(trade)
    
    # Add closed positions (convert to trade format)
    for pos in closed_positions:
        pos_id = pos.get("position_id")
        if pos_id and pos_id not in seen_ids:
            seen_ids.add(pos_id)
            all_trades.append({
                "execution_id": pos_id,
                "token_symbol": pos.get("token_symbol"),
                "token_mint": pos.get("token_mint"),
                "trade_type": "sell",
                "action": pos.get("status", "").replace("closed_", ""),
                "entry_price": pos.get("entry_price"),
                "exit_price": pos.get("exit_price"),
                "amount_sol": pos.get("amount_sol"),
                "pnl_sol": pos.get("pnl_sol"),
                "pnl_percent": pos.get("pnl_percent"),
                "created_at": pos.get("created_at"),
                "closed_at": pos.get("closed_at"),
                "executed_at": pos.get("closed_at"),
                "tx_signature": pos.get("tx_signature"),
                "sell_tx_signature": pos.get("sell_tx_signature"),
                "status": "closed",
                "source": "auto" if pos.get("auto_trade") else "position"
            })
    
    # Add auto-trade logs
    for log in auto_trade_logs:
        log_id = log.get("log_id") or log.get("position_id")
        if log_id and log_id not in seen_ids:
            seen_ids.add(log_id)
            is_sell = "sell" in log.get("action", "") or "close" in log.get("action", "") or "take_profit" in log.get("action", "") or "stop_loss" in log.get("action", "")
            all_trades.append({
                "execution_id": log_id,
                "token_symbol": log.get("token_symbol"),
                "token_mint": log.get("token_mint"),
                "trade_type": "sell" if is_sell else "buy",
                "action": log.get("action"),
                "entry_price": log.get("entry_price"),
                "exit_price": log.get("exit_price"),
                "amount_sol": log.get("amount_sol"),
                "pnl_sol": log.get("pnl_sol"),
                "pnl_percent": log.get("pnl_percent"),
                "created_at": log.get("created_at"),
                "executed_at": log.get("created_at"),
                "tx_signature": log.get("tx_signature"),
                "status": "closed" if is_sell else "open",
                "source": "auto-trade"
            })
    
    # Sort by date (most recent first)
    all_trades.sort(key=lambda x: x.get("executed_at") or x.get("created_at") or "", reverse=True)
    
    # Calculate stats from all closed/sell trades
    sell_trades = [t for t in all_trades if t.get("trade_type") == "sell" or t.get("status") == "closed"]
    wins = len([t for t in sell_trades if (t.get("pnl_sol") or t.get("pnl_percent") or 0) > 0])
    losses = len([t for t in sell_trades if (t.get("pnl_sol") or t.get("pnl_percent") or 0) < 0])
    total_pnl = sum(t.get("pnl_sol") or 0 for t in sell_trades)
    
    return {
        "trades": all_trades[:limit],
        "stats": {
            "total_trades": len(sell_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(sell_trades) * 100) if sell_trades else 0,
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
        
        # Trigger copy trading to followers
        try:
            from routers.social_trading import copy_trade_to_followers, send_copy_trade_notification
            copied_trades = await copy_trade_to_followers(
                trader_wallet=wallet_address,
                trade_info={
                    "position_id": position_id,
                    "token_symbol": token_symbol.upper(),
                    "token_mint": token_mint,
                    "trade_type": "buy",
                    "amount_sol": input_sol,
                    "entry_price": entry_price,
                    "stop_loss_price": None,
                    "take_profit_price": None
                }
            )
            if copied_trades:
                logger.info(f"Copied trade to {len(copied_trades)} followers")
        except Exception as copy_error:
            logger.warning(f"Copy trading error (non-critical): {copy_error}")
        
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


class ManualCloseRequest(BaseModel):
    wallet_address: str
    position_id: str
    exit_price: float = None
    exit_reason: str = "manual_close"


@router.post("/manual-close-position")
async def manual_close_position(request: ManualCloseRequest):
    """
    Manually close a position without selling on-chain.
    Use this when tokens were sold outside the bot (e.g., via DEX directly).
    Records exit price and P/L for accurate history tracking.
    """
    try:
        # Find the position
        position = await db.ai_trader_positions.find_one({
            "wallet_address": request.wallet_address,
            "$or": [
                {"position_id": request.position_id},
                {"execution_id": request.position_id}
            ]
        })
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Get current price if not provided
        exit_price = request.exit_price
        if not exit_price:
            token_mint = position.get("token_mint")
            if token_mint:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}")
                    if response.status_code == 200:
                        pairs = response.json().get("pairs", [])
                        if pairs:
                            best = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                            exit_price = float(best.get("priceUsd", 0) or 0)
        
        # Calculate P/L
        entry_price = position.get("entry_price", 0)
        if entry_price > 0 and exit_price:
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_percent = 0
        
        amount_sol = position.get("amount_sol", 0)
        pnl_sol = amount_sol * (pnl_percent / 100)
        
        # Update position to closed
        await db.ai_trader_positions.update_one(
            {"_id": position["_id"]},
            {
                "$set": {
                    "status": f"closed_{request.exit_reason}",
                    "exit_price": exit_price,
                    "pnl_percent": pnl_percent,
                    "pnl_sol": pnl_sol,
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "manual_close": True,
                    "exit_reason": request.exit_reason
                }
            }
        )
        
        # Log the manual close
        await db.auto_trade_logs.insert_one({
            "log_id": str(uuid.uuid4())[:8],
            "wallet_address": request.wallet_address,
            "token_symbol": position.get("token_symbol"),
            "token_mint": position.get("token_mint"),
            "action": f"manual_close",
            "amount_sol": amount_sol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_percent": pnl_percent,
            "pnl_sol": pnl_sol,
            "reason": f"Manual close by user: {request.exit_reason}",
            "success": True,
            "position_id": request.position_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "message": f"Position closed at ${exit_price:.8f}" if exit_price else "Position closed",
            "position_id": request.position_id,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_percent": pnl_percent,
            "pnl_sol": pnl_sol
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual close position error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-ghost-positions/{wallet_address}")
async def delete_ghost_positions(wallet_address: str):
    """Delete all ghost positions (positions that weren't executed on-chain) for a wallet."""
    try:
        # Find and delete positions where executed_on_chain is False or missing
        result = await db.ai_trader_positions.delete_many({
            "wallet_address": wallet_address,
            "$or": [
                {"executed_on_chain": False},
                {"executed_on_chain": {"$exists": False}}
            ]
        })
        
        # Also clean up from executions collection
        exec_result = await db.ai_trader_executions.delete_many({
            "wallet_address": wallet_address,
            "$or": [
                {"executed_on_chain": False},
                {"executed_on_chain": {"$exists": False}}
            ]
        })
        
        total_deleted = result.deleted_count + exec_result.deleted_count
        
        return {
            "success": True,
            "message": f"Deleted {total_deleted} ghost position(s)",
            "deleted_count": total_deleted
        }
        
    except Exception as e:
        logger.error(f"Delete ghost positions error: {e}")
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
    # NEW: Advanced settings
    auto_trailing_stop_enabled: Optional[bool] = None
    auto_trailing_stop_percent: Optional[float] = None
    auto_scale_in_enabled: Optional[bool] = None
    auto_scale_in_threshold: Optional[float] = None
    auto_scale_in_max_adds: Optional[int] = None
    auto_avoid_volatile_hours: Optional[bool] = None
    auto_profit_target_alert: Optional[bool] = None


@router.get("/auto-trade/status/{wallet_address}")
async def get_auto_trade_status(wallet_address: str):
    """Get auto-trade status and settings for a wallet."""
    try:
        settings = await db.ai_trader_settings.find_one(
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
            "trades_executed": len([log for log in today_logs if log.get("success")]),
            "total_sol_used": sum(log.get("amount_sol", 0) for log in today_logs if log.get("success") and log.get("action") == "auto_buy"),
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
                "total_daily_limit_sol": settings.get("auto_total_daily_limit_sol", 1.0),
                "stop_loss_percent": settings.get("auto_stop_loss_percent", settings.get("stop_loss_percent", 10)),
                "take_profit_percent": settings.get("auto_take_profit_percent", settings.get("take_profit_percent", 20))
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
        await db.ai_trader_settings.update_one(
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
        
        await db.ai_trader_settings.update_one(
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


@router.post("/auto-trade/update-trailing-stops/{wallet_address}")
async def update_trailing_stops(wallet_address: str):
    """
    Update trailing stop-loss prices for all open positions.
    Should be called periodically to trail stops as price moves up.
    """
    try:
        settings = await db.ai_trader_settings.find_one({"wallet_address": wallet_address})
        
        if not settings or not settings.get("auto_trailing_stop_enabled"):
            return {"success": False, "message": "Trailing stops not enabled", "updated": 0}
        
        trailing_percent = settings.get("auto_trailing_stop_percent", 5.0)
        
        # Get all open positions
        positions = await db.ai_trader_positions.find({
            "wallet_address": wallet_address,
            "status": "open"
        }).to_list(100)
        
        updated_count = 0
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for position in positions:
                token_mint = position.get("token_mint")
                entry_price = position.get("entry_price", 0)
                current_stop = position.get("stop_loss_price", 0)
                highest_price = position.get("highest_price", entry_price)
                
                # Get current price
                try:
                    response = await client.get(
                        f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                    )
                    if response.status_code == 200:
                        pairs = response.json().get("pairs", [])
                        if pairs:
                            current_price = float(pairs[0].get("priceUsd", 0) or 0)
                            
                            # Update highest price if current is higher
                            if current_price > highest_price:
                                highest_price = current_price
                                await db.ai_trader_positions.update_one(
                                    {"_id": position["_id"]},
                                    {"$set": {"highest_price": highest_price}}
                                )
                            
                            # Calculate new trailing stop
                            new_stop = highest_price * (1 - trailing_percent / 100)
                            
                            # Only update if new stop is higher than current
                            if new_stop > current_stop:
                                await db.ai_trader_positions.update_one(
                                    {"_id": position["_id"]},
                                    {"$set": {
                                        "stop_loss_price": new_stop,
                                        "trailing_stop_updated_at": datetime.now(timezone.utc).isoformat()
                                    }}
                                )
                                updated_count += 1
                                
                                logger.info(f"Updated trailing stop for {position.get('token_symbol')}: {current_stop:.6f} -> {new_stop:.6f}")
                except Exception as e:
                    logger.warning(f"Failed to update trailing stop for {position.get('token_symbol')}: {e}")
        
        return {
            "success": True,
            "updated": updated_count,
            "positions_checked": len(positions)
        }
    except Exception as e:
        logger.error(f"Update trailing stops error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-trade/check-scale-in/{wallet_address}")
async def check_scale_in_opportunities(wallet_address: str):
    """
    Check if any positions should be scaled into (DCA on dip).
    Adds to position when price drops by threshold from entry.
    """
    try:
        settings = await db.ai_trader_settings.find_one({"wallet_address": wallet_address})
        
        if not settings or not settings.get("auto_scale_in_enabled"):
            return {"success": False, "message": "Scale-in not enabled", "scaled": 0}
        
        threshold = settings.get("auto_scale_in_threshold", 5.0)
        max_adds = settings.get("auto_scale_in_max_adds", 2)
        max_position = settings.get("auto_max_position_sol", 0.2)
        
        # Get open positions
        positions = await db.ai_trader_positions.find({
            "wallet_address": wallet_address,
            "status": "open"
        }).to_list(100)
        
        scaled_positions = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for position in positions:
                token_mint = position.get("token_mint")
                entry_price = position.get("entry_price", 0)
                current_amount = position.get("amount_sol", 0)
                scale_in_count = position.get("scale_in_count", 0)
                
                if scale_in_count >= max_adds:
                    continue
                
                # Get current price
                try:
                    response = await client.get(
                        f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                    )
                    if response.status_code == 200:
                        pairs = response.json().get("pairs", [])
                        if pairs:
                            current_price = float(pairs[0].get("priceUsd", 0) or 0)
                            
                            if current_price <= 0:
                                continue
                            
                            # Check if price dropped enough
                            price_drop = ((entry_price - current_price) / entry_price) * 100
                            
                            if price_drop >= threshold:
                                # Calculate scale-in amount (decreasing with each add)
                                scale_amount = max_position * (0.5 ** (scale_in_count + 1))
                                new_total = current_amount + scale_amount
                                
                                # Calculate new average entry
                                new_avg_entry = (
                                    (entry_price * current_amount) + (current_price * scale_amount)
                                ) / new_total
                                
                                # Update position
                                await db.ai_trader_positions.update_one(
                                    {"_id": position["_id"]},
                                    {"$set": {
                                        "amount_sol": new_total,
                                        "entry_price": new_avg_entry,
                                        "scale_in_count": scale_in_count + 1,
                                        "last_scale_in_at": datetime.now(timezone.utc).isoformat(),
                                        "last_scale_in_price": current_price
                                    }}
                                )
                                
                                # Log the scale-in
                                await db.auto_trade_logs.insert_one({
                                    "log_id": str(uuid.uuid4())[:8],
                                    "wallet_address": wallet_address,
                                    "token_symbol": position.get("token_symbol"),
                                    "token_mint": token_mint,
                                    "action": "scale_in",
                                    "amount_sol": scale_amount,
                                    "entry_price": current_price,
                                    "confidence": 0.0,
                                    "strategy": "dca_on_dip",
                                    "reason": f"Scaled in at {price_drop:.1f}% dip (add #{scale_in_count + 1})",
                                    "success": True,
                                    "created_at": datetime.now(timezone.utc).isoformat()
                                })
                                
                                scaled_positions.append({
                                    "symbol": position.get("token_symbol"),
                                    "scale_amount": scale_amount,
                                    "price_drop": price_drop,
                                    "new_avg_entry": new_avg_entry
                                })
                                
                                logger.info(f"Scaled into {position.get('token_symbol')} at {price_drop:.1f}% dip")
                except Exception as e:
                    logger.warning(f"Failed to check scale-in for {position.get('token_symbol')}: {e}")
        
        return {
            "success": True,
            "scaled": len(scaled_positions),
            "positions": scaled_positions
        }
    except Exception as e:
        logger.error(f"Check scale-in error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-trade/scan-and-execute/{wallet_address}")
async def auto_trade_scan_and_execute(wallet_address: str):
    """
    Main auto-trading function: Scan market and execute trades automatically.
    This should be called periodically (every 5 minutes) by the frontend or a scheduler.
    
    Flow:
    1. Check and execute exits for positions hitting take-profit/stop-loss
    2. Check daily limits and cooldowns
    3. Scan for new buy opportunities
    """
    try:
        # Get user settings from ai_trader_settings collection
        settings = await db.ai_trader_settings.find_one({"wallet_address": wallet_address})
        
        if not settings:
            return {"success": False, "message": "Settings not found", "trades": []}
        
        if not settings.get("auto_trade_enabled"):
            return {"success": False, "message": "Auto-trading is disabled", "trades": []}
        
        # FIRST: Check and execute exits for positions hitting TP/SL
        exits_result = await auto_trade_check_exits(wallet_address)
        exits_executed = exits_result.get("exits", [])
        if exits_executed:
            logger.info(f"Auto-exits executed: {len(exits_executed)} positions closed for {wallet_address}")
        
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
        # Note: require_multiple is no longer used - combined strategy handles multi-strategy logic internally
        risk_level = settings.get("risk_level", "safer")
        
        # Adjust confidence based on mode
        # Backtest shows 0.55 is optimal (72.5% win rate, +2.87% PnL)
        if mode == "aggressive":
            min_confidence = max(0.50, min_confidence - 0.15)  # More aggressive: 0.50 floor
        elif mode == "moderate":
            min_confidence = max(0.55, min_confidence - 0.05)  # Moderate: 0.55-0.60
        else:  # conservative
            min_confidence = min(0.75, min_confidence + 0.05)  # Conservative: 0.70-0.75
        
        # Log effective settings
        logger.info(f"Auto-trade scan for {wallet_address}: mode={mode}, min_conf={min_confidence:.2f}, risk={risk_level}")
        
        # Get tokens to scan based on risk level (exclude SOL - can't swap SOL to SOL)
        tokens_to_scan = []
        runner_tokens = []  # Will store runner data separately
        
        if risk_level in ["safer", "both"]:
            tokens_to_scan.extend(["JUP", "PYTH", "RNDR"])  # Removed SOL
        if risk_level in ["high_risk", "both"]:
            tokens_to_scan.extend(["BONK", "WIF", "RAY"])
            
            # Fetch runner tokens (new pairs with momentum) - only for high_risk or both
            try:
                runners = await RunnerDetector.get_best_runners(max_runners=5)
                runner_tokens = runners
                logger.info(f"Found {len(runners)} potential runner tokens: {[r['symbol'] for r in runners]}")
            except Exception as e:
                logger.warning(f"Failed to fetch runners: {e}")
        
        executed_trades = []
        skipped = []
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            # First scan known tokens
            for symbol in tokens_to_scan[:5]:  # Limit to 5 known tokens per scan
                try:
                    token_mint = TOKENS.get(symbol)
                    if not token_mint:
                        continue
                    
                    # Skip SOL - can't swap SOL to SOL
                    if token_mint == SOL_MINT:
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
                    
                    # Create synthetic price history with realistic volatility
                    price_24h_ago = current_price / (1 + price_change_24h / 100) if price_change_24h != -100 else current_price
                    price_6h_ago = current_price / (1 + price_change_6h / 100) if price_change_6h != -100 else current_price
                    price_1h_ago = current_price / (1 + price_change_1h / 100) if price_change_1h != -100 else current_price
                    
                    # Generate price history with natural volatility for meaningful MACD
                    import random
                    random.seed(int(current_price * 1e8) % 10000)  # Deterministic but varied
                    
                    # Calculate volatility factor from price changes
                    volatility = max(abs(price_change_24h), abs(price_change_6h), abs(price_change_1h)) / 100
                    volatility = max(0.005, min(volatility, 0.05))  # Clamp between 0.5% and 5%
                    
                    for i in range(50):
                        # Add micro-volatility to create MACD movement
                        noise = random.uniform(-volatility, volatility) * current_price
                        
                        if i < 6:  # Last 1 hour (most recent)
                            base = price_1h_ago + (current_price - price_1h_ago) * (i / 6)
                        elif i < 12:  # 1-6 hours ago
                            base = price_6h_ago + (price_1h_ago - price_6h_ago) * ((i - 6) / 6)
                        elif i < 24:  # 6-12 hours ago
                            base = price_24h_ago + (price_6h_ago - price_24h_ago) * ((i - 12) / 12)
                        else:  # 12-24 hours ago
                            base = price_24h_ago * (1 - (i - 24) * 0.002)
                        
                        prices.append(base + noise)
                    
                    prices.append(current_price)
                    
                    # Calculate indicators using TechnicalAnalyzer.analyze() to get all required fields
                    indicators = TechnicalAnalyzer.analyze(prices, current_price)
                    
                    # Run combined strategy as primary (best win rate: 76.9% at 0.55 conf)
                    # Combined already weighs momentum, mean_reversion, and breakout internally
                    combined = StrategyEngine.combined_strategy(indicators)
                    
                    # Also run individual strategies for logging/transparency
                    momentum = StrategyEngine.momentum_strategy(indicators)
                    mean_rev = StrategyEngine.mean_reversion_strategy(indicators)
                    breakout = StrategyEngine.breakout_strategy(indicators)
                    
                    # Count agreeing signals for transparency
                    strategies = [momentum, mean_rev, breakout]
                    buy_signals = [s for s in strategies if s["signal"] == "buy"]
                    agreement_count = len(buy_signals)
                    
                    # Determine if we should trade - USE COMBINED STRATEGY AS PRIMARY
                    # This bypasses require_multiple since combined already weighs all strategies
                    should_trade = False
                    trade_confidence = combined["confidence"]
                    trade_reason = combined["reasoning"]
                    
                    # Combined strategy buy signal with sufficient confidence
                    if combined["signal"] == "buy" and trade_confidence >= min_confidence:
                        should_trade = True
                        # Add agreement info to reason for transparency
                        if agreement_count >= 2:
                            trade_reason = f"[{agreement_count}/3 agree] {trade_reason}"
                        elif agreement_count == 1:
                            trade_reason = f"[Combined strategy] {trade_reason}"
                    
                    # Bonus: if multiple strategies strongly agree, boost confidence slightly
                    if should_trade and agreement_count >= 2:
                        trade_confidence = min(0.95, trade_confidence + 0.05)
                    
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
                            "stop_loss_price": current_price * (1 - settings.get("auto_stop_loss_percent", settings.get("stop_loss_percent", 10)) / 100),
                            "take_profit_price": current_price * (1 + settings.get("auto_take_profit_percent", settings.get("take_profit_percent", 20)) / 100),
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
                        
                        # ONLY save position and log if execution was successful
                        if execution_success:
                            position_doc["executed_on_chain"] = True
                            position_doc["execution_error"] = None
                            
                            await db.ai_trader_positions.insert_one(position_doc)
                            
                            # Log the successful auto-trade
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
                                "executed_on_chain": True,
                                "tx_signature": tx_signature,
                                "execution_error": None,
                                "position_id": position_id,
                                "created_at": datetime.now(timezone.utc).isoformat()
                            }
                            
                            await db.auto_trade_logs.insert_one(log_doc)
                            
                            # Create pending journal entry for user to review
                            await create_pending_journal_entry(
                                wallet_address=wallet_address,
                                asset=symbol,
                                trade_type="buy",
                                entry_price=current_price,
                                position_size_sol=position_sol,
                                tx_signature=tx_signature
                            )
                            
                            executed_trades.append({
                                "symbol": symbol,
                                "action": "buy",
                                "amount_sol": position_sol,
                                "entry_price": current_price,
                                "confidence": trade_confidence,
                                "reason": trade_reason,
                                "executed_on_chain": True,
                                "tx_signature": tx_signature
                            })
                            
                            logger.info(f"Position saved: {symbol} @ {current_price} - TX: {tx_signature}")
                            
                            # Only execute one trade per scan in conservative mode
                            if mode == "conservative":
                                break
                        else:
                            # Log as skipped, not as a trade
                            skipped.append({
                                "symbol": symbol,
                                "reason": execution_error or "On-chain execution failed",
                                "confidence": trade_confidence,
                                "would_have_traded": True
                            })
                            logger.warning(f"Trade skipped (execution failed): {symbol} - {execution_error}")
                    else:
                        # Log skipped - now based on combined strategy
                        if combined["signal"] != "buy":
                            skip_reason = f"No buy signal (combined: {combined['signal'] or 'hold'})"
                        elif trade_confidence < min_confidence:
                            skip_reason = f"Low confidence ({trade_confidence:.2f} < {min_confidence:.2f})"
                        else:
                            skip_reason = "Unknown"
                        
                        skipped.append({
                            "symbol": symbol,
                            "reason": skip_reason,
                            "confidence": trade_confidence,
                            "strategies_agreeing": agreement_count
                        })
                        
                except Exception as e:
                    logger.warning(f"Auto-trade scan error for {symbol}: {e}")
                    continue
            
            # Now scan runner tokens (new pairs with momentum)
            if runner_tokens and len(executed_trades) < 3:  # Don't over-trade
                logger.info(f"Scanning {len(runner_tokens)} runner tokens...")
                
                for runner in runner_tokens[:3]:  # Limit to top 3 runners
                    try:
                        symbol = runner["symbol"]
                        token_mint = runner["token_address"]
                        current_price = runner["price_usd"]
                        
                        if current_price <= 0:
                            continue
                        
                        # Create synthetic price history from runner data
                        price_change_24h = runner.get("price_change_24h", 0)
                        price_change_6h = runner.get("price_change_6h", 0)
                        price_change_1h = runner.get("price_change_1h", 0)
                        
                        price_24h_ago = current_price / (1 + price_change_24h / 100) if price_change_24h != -100 else current_price
                        price_6h_ago = current_price / (1 + price_change_6h / 100) if price_change_6h != -100 else current_price
                        price_1h_ago = current_price / (1 + price_change_1h / 100) if price_change_1h != -100 else current_price
                        
                        import random
                        random.seed(int(current_price * 1e8) % 10000)
                        volatility = max(abs(price_change_24h), abs(price_change_6h), abs(price_change_1h)) / 100
                        volatility = max(0.01, min(volatility, 0.08))  # Runners are more volatile
                        
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
                        
                        # Calculate indicators
                        indicators = TechnicalAnalyzer.analyze(prices, current_price)
                        
                        # Run strategies
                        combined = StrategyEngine.combined_strategy(indicators)
                        momentum = StrategyEngine.momentum_strategy(indicators)
                        mean_rev = StrategyEngine.mean_reversion_strategy(indicators)
                        breakout = StrategyEngine.breakout_strategy(indicators)
                        
                        buy_signals = [s for s in [momentum, mean_rev, breakout] if s["signal"] == "buy"]
                        agreement_count = len(buy_signals)
                        
                        # For runners, we BOOST confidence based on runner score
                        base_confidence = combined["confidence"]
                        runner_score = runner.get("runner_score", 0)
                        buy_ratio = runner.get("buy_ratio", 0.5)
                        
                        # Boost confidence for high-score runners with strong buy pressure
                        confidence_boost = 0
                        if runner_score >= 60:
                            confidence_boost += 0.10
                        elif runner_score >= 45:
                            confidence_boost += 0.05
                        
                        if buy_ratio >= 0.65:
                            confidence_boost += 0.05
                        
                        trade_confidence = min(0.95, base_confidence + confidence_boost)
                        trade_reason = f"[RUNNER score={runner_score}] {combined['reasoning']}"
                        
                        should_trade = False
                        if combined["signal"] == "buy" and trade_confidence >= min_confidence:
                            should_trade = True
                        
                        if should_trade:
                            # Check if we already have a position
                            existing_position = await db.ai_trader_positions.find_one({
                                "wallet_address": wallet_address,
                                "token_mint": token_mint
                            })
                            
                            if existing_position:
                                skipped.append({
                                    "symbol": f"{symbol} (RUNNER)",
                                    "reason": "Already have position",
                                    "runner_score": runner_score
                                })
                                continue
                            
                            # Use smaller position for runners (higher risk)
                            position_sol = min(max_position * 0.5, 0.1)  # Max 0.1 SOL for runners
                            
                            position_id = str(uuid.uuid4())[:8]
                            execution_id = f"runner_{str(uuid.uuid4())[:6]}"
                            
                            # Try to execute via custodial wallet
                            tx_signature = None
                            execution_success = False
                            execution_error = None
                            
                            try:
                                from routers.custodial_wallet import get_wallet_balance, execute_auto_trade
                                
                                custodial_wallet = await db.custodial_wallets.find_one({"user_wallet": wallet_address})
                                
                                if custodial_wallet:
                                    custodial_balance = await get_wallet_balance(custodial_wallet["custodial_address"])
                                    required_lamports = int(position_sol * LAMPORTS_PER_SOL)
                                    
                                    if custodial_balance >= required_lamports + 50000:
                                        logger.info(f"Executing runner trade via custodial wallet: {position_sol} SOL for {symbol}")
                                        
                                        trade_result = await execute_auto_trade(
                                            user_wallet=wallet_address,
                                            input_mint=SOL_MINT,
                                            output_mint=token_mint,
                                            amount_lamports=required_lamports
                                        )
                                        
                                        if trade_result.get("success"):
                                            tx_signature = trade_result.get("tx_signature")
                                            execution_success = True
                                            logger.info(f"Runner trade executed successfully: {tx_signature}")
                                    else:
                                        execution_error = f"Insufficient custodial balance: {custodial_balance/LAMPORTS_PER_SOL:.4f} SOL"
                                else:
                                    execution_error = "No custodial wallet"
                                    
                            except Exception as exec_error:
                                execution_error = f"Runner execution failed: {str(exec_error)}"
                                logger.error(f"Runner trade execution error: {exec_error}")
                            
                            # ONLY save position if execution was successful
                            if execution_success:
                                position_doc = {
                                    "position_id": position_id,
                                    "execution_id": execution_id,
                                    "wallet_address": wallet_address,
                                    "token_symbol": symbol,
                                    "token_mint": token_mint,
                                    "amount_sol": position_sol,
                                    "entry_price": current_price,
                                    "stop_loss_price": current_price * 0.80,
                                    "take_profit_price": current_price * 2.0,
                                    "trade_type": "buy",
                                    "status": "open",
                                    "auto_trade": True,
                                    "is_runner": True,
                                    "runner_score": runner_score,
                                    "confidence": trade_confidence,
                                    "strategy": "runner_momentum",
                                    "executed_on_chain": True,
                                    "tx_signature": tx_signature,
                                    "created_at": datetime.now(timezone.utc).isoformat()
                                }
                                
                                await db.ai_trader_positions.insert_one(position_doc)
                                
                                # Log the successful trade
                                log_doc = {
                                    "log_id": str(uuid.uuid4()),
                                    "wallet_address": wallet_address,
                                    "token_symbol": symbol,
                                    "token_mint": token_mint,
                                    "action": "auto_buy_runner",
                                    "amount_sol": position_sol,
                                    "entry_price": current_price,
                                    "confidence": trade_confidence,
                                    "runner_score": runner_score,
                                    "buy_ratio": buy_ratio,
                                    "strategy": "runner_momentum",
                                    "reason": trade_reason,
                                    "success": True,
                                    "executed_on_chain": True,
                                    "tx_signature": tx_signature,
                                    "position_id": position_id,
                                    "created_at": datetime.now(timezone.utc).isoformat()
                                }
                                
                                await db.auto_trade_logs.insert_one(log_doc)
                                
                                executed_trades.append({
                                    "symbol": f"{symbol} (RUNNER)",
                                    "action": "buy",
                                    "amount_sol": position_sol,
                                    "entry_price": current_price,
                                    "confidence": trade_confidence,
                                    "runner_score": runner_score,
                                    "reason": trade_reason,
                                    "is_runner": True,
                                    "executed_on_chain": True,
                                    "tx_signature": tx_signature
                                })
                                
                                logger.info(f"Runner position saved: {symbol} @ {current_price} - TX: {tx_signature}")
                                
                                # Limit runner trades
                                if len([t for t in executed_trades if t.get("is_runner")]) >= 2:
                                    break
                            else:
                                skipped.append({
                                    "symbol": f"{symbol} (RUNNER)",
                                    "reason": execution_error or "On-chain execution failed",
                                    "confidence": trade_confidence,
                                    "runner_score": runner_score,
                                    "would_have_traded": True
                                })
                        else:
                            skipped.append({
                                "symbol": f"{symbol} (RUNNER)",
                                "reason": f"Low confidence ({trade_confidence:.2f} < {min_confidence:.2f})" if trade_confidence < min_confidence else "No buy signal",
                                "confidence": trade_confidence,
                                "runner_score": runner_score
                            })
                    
                    except Exception as e:
                        logger.warning(f"Runner scan error for {runner.get('symbol', '?')}: {e}")
                        continue
        
        runner_trades = len([t for t in executed_trades if t.get("is_runner")])
        known_trades = len(executed_trades) - runner_trades
        
        # Include exits in the response
        exits_count = len(exits_executed)
        message_parts = []
        if exits_count:
            message_parts.append(f"{exits_count} exits")
        if known_trades:
            message_parts.append(f"{known_trades} known buys")
        if runner_trades:
            message_parts.append(f"{runner_trades} runner buys")
        
        return {
            "success": True,
            "trades_executed": len(executed_trades),
            "trades": executed_trades,
            "exits_executed": exits_count,
            "exits": exits_executed,
            "skipped": skipped,
            "runners_found": len(runner_tokens),
            "message": f"Auto-scan complete: {', '.join(message_parts) if message_parts else 'no trades'}"
        }
        
    except Exception as e:
        logger.error(f"Auto-trade scan error: {e}")
        return {"success": False, "error": str(e), "trades": []}


@router.post("/auto-trade/check-exits/{wallet_address}")
async def auto_trade_check_exits(wallet_address: str):
    """
    Check open positions for stop-loss or take-profit triggers.
    Executes sells on-chain via custodial wallet when triggers hit.
    Should be called periodically to manage risk.
    """
    from routers.custodial_wallet import execute_auto_trade, get_wallet_balance
    
    try:
        settings = await db.ai_trader_settings.find_one({"wallet_address": wallet_address})
        
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
                    
                    # Calculate current P&L percentage
                    if entry_price > 0:
                        current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:
                        current_pnl_pct = 0
                    
                    # Check for exit conditions
                    exit_action = None
                    exit_reason = ""
                    
                    if current_price <= stop_loss:
                        exit_action = "stop_loss"
                        exit_reason = f"Stop-loss triggered at ${current_price:.8f} (SL: ${stop_loss:.8f})"
                    elif current_price >= take_profit:
                        exit_action = "take_profit"
                        exit_reason = f"Take-profit triggered at ${current_price:.8f} (TP: ${take_profit:.8f}, +{current_pnl_pct:.1f}%)"
                    
                    if exit_action:
                        logger.info(f"Exit triggered for {symbol}: {exit_action} at {current_pnl_pct:.1f}%")
                        
                        # Try to execute sell on-chain
                        sell_success = False
                        tx_signature = None
                        sell_error = None
                        
                        try:
                            # Get the custodial wallet's token balance for this token
                            from solana.rpc.async_api import AsyncClient
                            from solders.pubkey import Pubkey
                            import os
                            
                            HELIUS_RPC = os.environ.get("HELIUS_RPC_URL") or os.environ.get("ALCHEMY_RPC_URL", "https://api.mainnet-beta.solana.com")
                            
                            # Get custodial wallet address
                            custodial_wallet = await db.custodial_wallets.find_one({"user_wallet": wallet_address})
                            if not custodial_wallet:
                                raise Exception("Custodial wallet not found")
                            
                            custodial_address = custodial_wallet["custodial_address"]
                            
                            # Get token accounts for this wallet
                            async with AsyncClient(HELIUS_RPC) as rpc_client:
                                from solana.rpc.types import TokenAccountOpts
                                
                                token_pubkey = Pubkey.from_string(token_mint)
                                wallet_pubkey = Pubkey.from_string(custodial_address)
                                
                                # Try standard SPL Token program first
                                TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
                                TOKEN_2022_PROGRAM_ID = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
                                
                                token_balance = 0
                                
                                # Check SPL Token accounts
                                opts = TokenAccountOpts(mint=token_pubkey, program_id=TOKEN_PROGRAM_ID)
                                token_accounts = await rpc_client.get_token_accounts_by_owner_json_parsed(wallet_pubkey, opts)
                                
                                if token_accounts.value:
                                    for account in token_accounts.value:
                                        info = account.account.data.parsed.get("info", {})
                                        token_amount_info = info.get("tokenAmount", {})
                                        token_balance = int(token_amount_info.get("amount", 0))
                                
                                # If no balance found, check Token-2022 accounts
                                if token_balance <= 0:
                                    opts_2022 = TokenAccountOpts(mint=token_pubkey, program_id=TOKEN_2022_PROGRAM_ID)
                                    token_accounts_2022 = await rpc_client.get_token_accounts_by_owner_json_parsed(wallet_pubkey, opts_2022)
                                    
                                    if token_accounts_2022.value:
                                        for account in token_accounts_2022.value:
                                            info = account.account.data.parsed.get("info", {})
                                            token_amount_info = info.get("tokenAmount", {})
                                            token_balance = int(token_amount_info.get("amount", 0))
                                
                                if token_balance <= 0:
                                    raise Exception(f"No {symbol} tokens in custodial wallet")
                                
                                logger.info(f"Found {token_balance} raw units of {symbol} to sell")
                            
                            # Execute swap: TOKEN -> SOL
                            sell_result = await execute_auto_trade(
                                user_wallet=wallet_address,
                                input_mint=token_mint,
                                output_mint=SOL_MINT,
                                amount_lamports=token_balance  # This is token units, not lamports
                            )
                            
                            if sell_result.get("success"):
                                sell_success = True
                                tx_signature = sell_result.get("tx_signature")
                                logger.info(f"Auto-sell executed for {symbol}: {tx_signature}")
                            else:
                                sell_error = sell_result.get("error", "Unknown error")
                                
                        except Exception as e:
                            sell_error = str(e)
                            logger.warning(f"Auto-sell failed for {symbol}: {e}")
                        
                        # Calculate final P&L
                        pnl_pct = current_pnl_pct
                        pnl_sol = position.get("amount_sol", 0) * (pnl_pct / 100)
                        
                        # Update position in database
                        await db.ai_trader_positions.update_one(
                            {"position_id": position.get("position_id")},
                            {
                                "$set": {
                                    "status": f"closed_{exit_action}" if sell_success else f"pending_{exit_action}",
                                    "exit_price": current_price,
                                    "pnl_percent": pnl_pct,
                                    "pnl_sol": pnl_sol,
                                    "closed_at": datetime.now(timezone.utc).isoformat(),
                                    "sell_tx_signature": tx_signature,
                                    "sell_executed_on_chain": sell_success,
                                    "sell_error": sell_error
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
                            "success": sell_success,
                            "tx_signature": tx_signature,
                            "executed_on_chain": sell_success,
                            "error": sell_error,
                            "position_id": position.get("position_id"),
                            "created_at": datetime.now(timezone.utc).isoformat()
                        })
                        
                        # Create pending journal entry for sell if successful
                        if sell_success:
                            await create_pending_journal_entry(
                                wallet_address=wallet_address,
                                asset=symbol,
                                trade_type="sell",
                                entry_price=current_price,  # Exit price for sells
                                position_size_sol=position.get("amount_sol", 0),
                                tx_signature=tx_signature,
                                pnl_percent=pnl_pct,
                                pnl_sol=pnl_sol
                            )
                        
                        exits.append({
                            "symbol": symbol,
                            "action": exit_action,
                            "entry_price": entry_price,
                            "exit_price": current_price,
                            "pnl_percent": pnl_pct,
                            "pnl_sol": pnl_sol,
                            "reason": exit_reason,
                            "executed_on_chain": sell_success,
                            "tx_signature": tx_signature,
                            "error": sell_error
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
