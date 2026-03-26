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
import numpy as np

# Import refactored services
from services.market_analyzer import MarketConditionAnalyzer
from services.runner_detector import RunnerDetector
from services.technical_analyzer import TechnicalAnalyzer
from services.strategy_engine import StrategyEngine

# Import extracted models and utilities
from models.ai_trader_models import (
    TraderSettings, AutoTradeLog, TradeSignal, TradeExecution,
    ApproveSignalRequest, MIN_POSITION_SOL, MAX_POSITION_SOL
)
from services.token_price import (
    SOL_MINT, LAMPORTS_PER_SOL, JUPITER_QUOTE_URL, JUPITER_SWAP_URL,
    TOKENS, SAFER_TOKENS, HIGH_RISK_TOKENS,
    RUNNER_MIN_LIQUIDITY, RUNNER_MIN_VOLUME_24H, RUNNER_MIN_PRICE_CHANGE_1H,
    RUNNER_MAX_PRICE_CHANGE_1H, RUNNER_MIN_TXNS_1H, RUNNER_MAX_AGE_HOURS,
    get_jupiter_quote, get_token_price, get_token_price_by_mint, get_price_history
)
from utils.database import db
from services.ledger import record_entry as ledger_record, get_available_balance as ledger_balance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-trader", tags=["AI Trader"])

RAKE_PERCENT = 2.5  # Platform rake on profitable trades (% of profit only)


# Helper functions are in services/auto_trader_engine.py
from services.auto_trader_engine import apply_rake, ensure_sufficient_sol_for_trade, create_pending_journal_entry


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


@router.get("/intelligence/{token_mint}")
async def get_token_intelligence(token_mint: str):
    """Get combined intelligence data for a token (smart money, sentiment, price quality)."""
    try:
        from services.smart_money_tracker import get_smart_money_signal
        from services.social_sentiment import analyze_token_sentiment
        from services.price_collector import get_data_quality_status

        smart_money = await get_smart_money_signal(token_mint)
        sentiment = await analyze_token_sentiment(token_mint)
        data_quality = await get_data_quality_status()

        # Find the matching token in data quality
        token_quality = None
        for sym, quality in data_quality.items():
            if TOKENS.get(sym) == token_mint:
                token_quality = quality
                break

        return {
            "token_mint": token_mint,
            "smart_money": smart_money,
            "sentiment": sentiment,
            "data_quality": token_quality or {"candles": 0, "has_real_data": False},
            "combined_confidence_adj": round(
                smart_money.get("strength", 0) * 0.15 * (1 if smart_money.get("action") == "buy" else -1 if smart_money.get("action") == "sell" else 0)
                + sentiment.get("confidence_adjustment", 0),
                3
            )
        }
    except Exception as e:
        logger.error(f"Intelligence fetch error: {e}")
        return {"token_mint": token_mint, "smart_money": {}, "sentiment": {}, "data_quality": {}, "combined_confidence_adj": 0}


@router.get("/intelligence-dashboard")
async def get_intelligence_dashboard():
    """Get overview of all intelligence systems status."""
    try:
        from services.price_collector import get_data_quality_status
        from services.smart_money_tracker import SMART_MONEY_WALLETS

        data_quality = await get_data_quality_status()

        # Count recent smart money signals
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        recent_signals = await db.smart_money_signals.count_documents({"detected_at": {"$gte": cutoff}})

        # Count sentiment entries
        sentiment_entries = await db.sentiment_cache.count_documents({})

        tokens_with_real_data = sum(1 for v in data_quality.values() if v.get("has_real_data"))

        return {
            "price_collector": {
                "status": "active",
                "tokens_tracked": len(data_quality),
                "tokens_with_real_data": tokens_with_real_data,
                "details": data_quality
            },
            "smart_money": {
                "status": "active",
                "wallets_tracked": len(SMART_MONEY_WALLETS),
                "recent_signals": recent_signals
            },
            "sentiment": {
                "status": "active",
                "cached_entries": sentiment_entries
            },
            "jito": {
                "status": "active",
                "description": "MEV-protected execution via Jito bundles with RPC fallback"
            }
        }
    except Exception as e:
        logger.error(f"Intelligence dashboard error: {e}")
        return {"error": str(e)}



@router.get("/sniper-targets")
async def get_sniper_targets():
    """Get current sniper targets (new pairs detected)."""
    try:
        from services.token_sniper import scan_new_pairs
        targets = await scan_new_pairs()
        return {"targets": targets, "count": len(targets)}
    except Exception as e:
        logger.error(f"Sniper targets error: {e}")
        return {"targets": [], "count": 0, "error": str(e)}


@router.get("/platform-stats")
async def get_platform_stats():
    """Get aggregate trading stats across all users for the homepage widget."""
    try:
        # Count all closed positions with on-chain sell execution
        pipeline = [
            {"$match": {
                "status": {"$regex": "^closed"},
                "sell_executed_on_chain": True,
                "sell_tx_signature": {"$exists": True, "$ne": None}
            }},
            {"$group": {
                "_id": None,
                "total_trades": {"$sum": 1},
                "total_pnl_sol": {"$sum": {"$ifNull": ["$pnl_sol", 0]}},
                "wins": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$pnl_sol", 0]}, 0]}, 1, 0]}},
                "unique_traders": {"$addToSet": "$wallet_address"}
            }}
        ]
        result = await db.ai_trader_positions.aggregate(pipeline).to_list(1)

        # Count active positions
        active_count = await db.ai_trader_positions.count_documents({
            "status": {"$in": ["open", "pending_stop_loss", "pending_take_profit"]}
        })

        # Find best trade (highest PnL %)
        best_trade_pipeline = [
            {"$match": {
                "status": {"$regex": "^closed"},
                "sell_executed_on_chain": True,
                "pnl_pct": {"$exists": True, "$gt": 0}
            }},
            {"$sort": {"pnl_pct": -1}},
            {"$limit": 1},
            {"$project": {"_id": 0, "token_symbol": 1, "pnl_pct": 1, "pnl_sol": 1}}
        ]
        best_trade_result = await db.ai_trader_positions.aggregate(best_trade_pipeline).to_list(1)
        best_trade = best_trade_result[0] if best_trade_result else None

        if result and len(result) > 0:
            r = result[0]
            total = r["total_trades"]
            wins = r["wins"]
            return {
                "total_trades": total,
                "win_rate": round((wins / total * 100) if total > 0 else 0, 1),
                "total_pnl_sol": round(r["total_pnl_sol"], 4),
                "active_positions": active_count,
                "active_traders": len(r.get("unique_traders", [])),
                "best_trade": best_trade
            }
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl_sol": 0,
            "active_positions": active_count,
            "active_traders": 0,
            "best_trade": best_trade
        }
    except Exception as e:
        logger.error(f"Platform stats error: {e}")
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl_sol": 0,
            "active_positions": 0,
            "active_traders": 0
        }



@router.get("/performance-scorecard/{wallet_address}")
async def get_performance_scorecard(wallet_address: str):
    """Generate a weekly performance scorecard for sharing on X."""
    try:
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        # All-time stats
        all_pipeline = [
            {"$match": {
                "wallet_address": wallet_address,
                "status": {"$regex": "^closed"},
                "sell_executed_on_chain": True
            }},
            {"$group": {
                "_id": None,
                "total_trades": {"$sum": 1},
                "total_pnl_sol": {"$sum": {"$ifNull": ["$pnl_sol", 0]}},
                "wins": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$pnl_sol", 0]}, 0]}, 1, 0]}},
                "losses": {"$sum": {"$cond": [{"$lte": [{"$ifNull": ["$pnl_sol", 0]}, 0]}, 1, 0]}}
            }}
        ]
        all_result = await db.ai_trader_positions.aggregate(all_pipeline).to_list(1)

        # Weekly stats
        week_pipeline = [
            {"$match": {
                "wallet_address": wallet_address,
                "status": {"$regex": "^closed"},
                "sell_executed_on_chain": True,
                "closed_at": {"$gte": week_ago}
            }},
            {"$group": {
                "_id": None,
                "trades": {"$sum": 1},
                "pnl_sol": {"$sum": {"$ifNull": ["$pnl_sol", 0]}},
                "wins": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$pnl_sol", 0]}, 0]}, 1, 0]}}
            }}
        ]
        week_result = await db.ai_trader_positions.aggregate(week_pipeline).to_list(1)

        # Best trade this week
        best_pipeline = [
            {"$match": {
                "wallet_address": wallet_address,
                "status": {"$regex": "^closed"},
                "sell_executed_on_chain": True,
                "closed_at": {"$gte": week_ago},
                "pnl_pct": {"$exists": True, "$gt": 0}
            }},
            {"$sort": {"pnl_pct": -1}},
            {"$limit": 1},
            {"$project": {"_id": 0, "token_symbol": 1, "pnl_pct": 1, "pnl_sol": 1}}
        ]
        best_result = await db.ai_trader_positions.aggregate(best_pipeline).to_list(1)

        # Active positions count
        active_count = await db.ai_trader_positions.count_documents({
            "wallet_address": wallet_address,
            "status": {"$in": ["open", "pending_stop_loss", "pending_take_profit"]}
        })

        # Win streak calculation
        recent_trades = await db.ai_trader_positions.find(
            {"wallet_address": wallet_address, "status": {"$regex": "^closed"}, "sell_executed_on_chain": True},
            {"_id": 0, "pnl_sol": 1}
        ).sort("closed_at", -1).to_list(50)

        streak = 0
        for t in recent_trades:
            if (t.get("pnl_sol") or 0) > 0:
                streak += 1
            else:
                break

        all_stats = all_result[0] if all_result else {}
        week_stats = week_result[0] if week_result else {}
        best_trade = best_result[0] if best_result else None
        total_all = all_stats.get("total_trades", 0)
        wins_all = all_stats.get("wins", 0)

        return {
            "wallet_address": wallet_address[:6] + "..." + wallet_address[-4:],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "all_time": {
                "total_trades": total_all,
                "win_rate": round((wins_all / total_all * 100) if total_all > 0 else 0, 1),
                "total_pnl_sol": round(all_stats.get("total_pnl_sol", 0), 4),
                "wins": wins_all,
                "losses": all_stats.get("losses", 0)
            },
            "this_week": {
                "trades": week_stats.get("trades", 0),
                "pnl_sol": round(week_stats.get("pnl_sol", 0), 4),
                "wins": week_stats.get("wins", 0),
                "win_rate": round((week_stats.get("wins", 0) / week_stats.get("trades", 1) * 100) if week_stats.get("trades", 0) > 0 else 0, 1)
            },
            "best_trade_this_week": best_trade,
            "current_streak": streak,
            "active_positions": active_count
        }
    except Exception as e:
        logger.error(f"Performance scorecard error: {e}")
        return {
            "wallet_address": wallet_address[:6] + "..." + wallet_address[-4:],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "all_time": {"total_trades": 0, "win_rate": 0, "total_pnl_sol": 0, "wins": 0, "losses": 0},
            "this_week": {"trades": 0, "pnl_sol": 0, "wins": 0, "win_rate": 0},
            "best_trade_this_week": None,
            "current_streak": 0,
            "active_positions": 0
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
        
        # Keep auto_trade_mode in sync with trading_mode
        if "trading_mode" in settings_dict:
            settings_dict["auto_trade_mode"] = settings_dict["trading_mode"]
        
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
    is_synthetic = False
    
    # If no history, reconstruct from DexScreener price changes (directionally accurate)
    if len(price_history) < 10:
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
                        
                        from services.market_quality import build_price_history_from_dex
                        price_history, is_synthetic = build_price_history_from_dex(
                            current_price, price_change_24h, price_change_6h, price_change_1h
                        )
        except Exception as e:
            logger.warning(f"Failed to create price history for {token_symbol}: {e}")
        
        # If still no data, refuse to generate signal rather than trading on pure noise
        if len(price_history) < 10:
            logger.warning(f"Insufficient price data for {token_symbol} — cannot generate reliable signal")
            return {
                "signal": None,
                "message": f"Insufficient price data for {token_symbol}. Need real market data to generate signals.",
                "current_price": current_price
            }
    
    # Run technical analysis
    indicators = TechnicalAnalyzer.analyze(price_history, current_price)
    
    # Generate signal using combined strategy
    strategy_result = StrategyEngine.combined_strategy(indicators)
    
    # OPTIMIZED: Raised threshold from 0.45 to 0.55 based on backtest results
    # Backtest showed: 0.45 conf → 45.6% win rate, 0.55 conf → 72.5% win rate
    # Using StrategyEngine class constant for consistency
    MIN_SIGNAL_THRESHOLD = StrategyEngine.MIN_SIGNAL_CONFIDENCE
    
    if strategy_result["signal"] and strategy_result["confidence"] >= MIN_SIGNAL_THRESHOLD:
        # Apply synthetic data penalty when trading on reconstructed price history
        final_confidence = strategy_result["confidence"]
        reasoning_prefix = ""
        if is_synthetic:
            from services.market_quality import confidence_penalty_for_synthetic_data
            final_confidence = confidence_penalty_for_synthetic_data(final_confidence)
            reasoning_prefix = "[Synthetic price data -10%] "
            if final_confidence < MIN_SIGNAL_THRESHOLD:
                return {
                    "signal": None,
                    "message": f"Signal confidence {final_confidence:.2f} below threshold after synthetic data penalty.",
                    "current_price": current_price,
                    "raw_confidence": strategy_result["confidence"]
                }
        
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
        suggested_position = base_position * final_confidence
        suggested_position = max(MIN_POSITION_SOL, min(suggested_position, MAX_POSITION_SOL))
        
        signal = TradeSignal(
            wallet_address=wallet_address,
            token_symbol=token_symbol,
            token_mint=token_mint,
            signal_type=strategy_result["signal"],
            entry_price=current_price,
            suggested_position_sol=round(suggested_position, 4),
            stop_loss_price=round(stop_loss_price, 8),
            take_profit_price=round(take_profit_price, 8),
            confidence=final_confidence,
            strategy=strategy_result["strategy"],
            risk_category=risk_category,
            reasoning=f"{reasoning_prefix}{strategy_result['reasoning']}",
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
    """Get all active positions for a user - positions that haven't been sold yet"""
    positions = []
    
    # Simple logic: show positions that are actively held (not closed/sold)
    # A position is active if:
    # 1. Status is "open" OR starts with "pending_" (awaiting sell)
    # 2. Has NOT been sold on-chain yet
    pos_from_positions = await db.ai_trader_positions.find({
        "wallet_address": wallet_address,
        "status": {"$in": ["open", "pending_stop_loss", "pending_take_profit"]},
        "sell_executed_on_chain": {"$ne": True}  # Not yet sold
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    positions.extend(pos_from_positions)
    
    # Get SOL price for USD conversions
    sol_price = await get_token_price("SOL") or 0
    
    # Update positions with current prices and calculate P/L
    for pos in positions:
        token_symbol = pos.get("token_symbol", "")
        token_mint = pos.get("token_mint", TOKENS.get(token_symbol))
        
        # Try to get price - first by symbol (multi-source), then by mint
        current_price = await get_token_price(token_symbol)
        if not current_price and token_mint:
            current_price = await get_token_price_by_mint(token_mint, symbol=token_symbol)
        
        entry_price = pos.get("entry_price", 0)
        amount_sol = pos.get("amount_sol", pos.get("input_sol", 0))
        
        pos["current_price"] = current_price
        pos["sol_price_usd"] = sol_price
        
        # Persist current_price to DB so ledger balance breakdown can use it
        if current_price and current_price > 0:
            await db.ai_trader_positions.update_one(
                {"position_id": pos.get("position_id")},
                {"$set": {"current_price": current_price, "price_updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        
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
async def get_trade_history(wallet_address: str, limit: int = 50, on_chain_only: bool = True):
    """Get trade history showing only successfully executed on-chain trades.
    
    Returns 1 BUY and 1 SELL per position (max), with accurate P/L calculations.
    
    Args:
        wallet_address: User's wallet address
        limit: Maximum number of trades to return
        on_chain_only: If True (default), only include trades with tx_signature
    """
    
    all_trades = []
    seen_position_buys = set()
    seen_position_sells = set()
    
    # Primary source: ai_trader_positions - get closed positions with successful sells
    closed_positions = await db.ai_trader_positions.find({
        "wallet_address": wallet_address,
        "status": {"$regex": "^closed"},
        "sell_executed_on_chain": True,  # Must have successful on-chain sell
        "sell_tx_signature": {"$exists": True, "$ne": None}
    }, {"_id": 0}).sort("closed_at", -1).limit(limit).to_list(limit)
    
    for pos in closed_positions:
        pos_id = pos.get("position_id")
        symbol = pos.get("token_symbol")
        
        # Add SELL trade for this position
        if pos_id not in seen_position_sells:
            seen_position_sells.add(pos_id)
            all_trades.append({
                "execution_id": f"{pos_id}_SELL",
                "position_id": pos_id,
                "token_symbol": symbol,
                "token_mint": pos.get("token_mint"),
                "trade_type": "sell",
                "action": pos.get("status", "").replace("closed_", ""),
                "entry_price": pos.get("entry_price"),
                "exit_price": pos.get("exit_price"),
                "amount_sol": pos.get("amount_sol"),
                "pnl_sol": pos.get("pnl_sol"),
                "pnl_percent": pos.get("pnl_percent"),
                "created_at": pos.get("closed_at"),
                "executed_at": pos.get("closed_at"),
                "tx_signature": pos.get("sell_tx_signature"),
                "status": "closed",
                "source": "auto" if pos.get("auto_trade") or pos.get("custodial") else "position",
                "time_held_minutes": _calculate_time_held(pos.get("created_at"), pos.get("closed_at"))
            })
        
        # Add BUY trade for this position (if it was executed on-chain)
        if pos_id not in seen_position_buys and pos.get("executed_on_chain") and pos.get("tx_signature"):
            seen_position_buys.add(pos_id)
            all_trades.append({
                "execution_id": f"{pos_id}_BUY",
                "position_id": pos_id,
                "token_symbol": symbol,
                "token_mint": pos.get("token_mint"),
                "trade_type": "buy",
                "action": "auto_buy" if pos.get("auto_trade") or pos.get("custodial") else "buy",
                "entry_price": pos.get("entry_price"),
                "amount_sol": pos.get("amount_sol"),
                "created_at": pos.get("created_at"),
                "executed_at": pos.get("created_at"),
                "tx_signature": pos.get("tx_signature"),
                "status": "closed",  # Position is closed now
                "source": "auto" if pos.get("auto_trade") or pos.get("custodial") else "position"
            })
    
    # Secondary source: Open positions with successful buys (not yet sold)
    open_positions = await db.ai_trader_positions.find({
        "wallet_address": wallet_address,
        "status": "open",
        "executed_on_chain": True,
        "tx_signature": {"$exists": True, "$ne": None}
    }, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    for pos in open_positions:
        pos_id = pos.get("position_id")
        if pos_id not in seen_position_buys:
            seen_position_buys.add(pos_id)
            all_trades.append({
                "execution_id": f"{pos_id}_BUY",
                "position_id": pos_id,
                "token_symbol": pos.get("token_symbol"),
                "token_mint": pos.get("token_mint"),
                "trade_type": "buy",
                "action": "auto_buy" if pos.get("auto_trade") or pos.get("custodial") else "buy",
                "entry_price": pos.get("entry_price"),
                "amount_sol": pos.get("amount_sol"),
                "created_at": pos.get("created_at"),
                "executed_at": pos.get("created_at"),
                "tx_signature": pos.get("tx_signature"),
                "status": "open",
                "source": "auto" if pos.get("auto_trade") or pos.get("custodial") else "position"
            })
    
    # Sort by executed_at (most recent first)
    all_trades.sort(key=lambda x: x.get("executed_at") or x.get("created_at") or "", reverse=True)
    
    # Calculate stats from SELL trades only (completed round-trips)
    # Only count trades with actual P/L data (not None)
    sell_trades = [t for t in all_trades if t.get("trade_type") == "sell"]
    trades_with_pnl = [t for t in sell_trades if t.get("pnl_percent") is not None or t.get("pnl_sol") is not None]
    
    wins = len([t for t in trades_with_pnl if (t.get("pnl_sol") or t.get("pnl_percent") or 0) > 0])
    losses = len([t for t in trades_with_pnl if (t.get("pnl_sol") or t.get("pnl_percent") or 0) < 0])
    total_pnl = sum(t.get("pnl_sol") or 0 for t in trades_with_pnl)
    
    # Count trades without P/L data separately
    trades_no_pnl = len(sell_trades) - len(trades_with_pnl)
    
    return {
        "trades": all_trades[:limit],
        "stats": {
            "total_trades": len(trades_with_pnl),  # Only count trades with actual P/L
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(trades_with_pnl) * 100) if trades_with_pnl else 0,
            "total_pnl_sol": round(total_pnl, 4),
            "trades_missing_pnl": trades_no_pnl  # Inform about incomplete data
        }
    }


def _calculate_time_held(start_time: str, end_time: str) -> int:
    """Calculate time held in minutes between two ISO timestamps."""
    try:
        if not start_time or not end_time:
            return 0
        from datetime import datetime
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        return int((end - start).total_seconds() / 60)
    except Exception:
        return 0


@router.post("/reset-statistics/{wallet_address}")
async def reset_statistics(wallet_address: str, full_reset: bool = False):
    """
    Reset trading statistics.
    
    If full_reset=False (default): Removes only non-on-chain trades, keeps successful on-chain history.
    If full_reset=True: Archives ALL trading history for learning, then resets stats to zero.
    """
    from datetime import datetime, timezone
    
    try:
        # Count records before cleanup
        before_counts = {
            "executions": await db.ai_trader_executions.count_documents({"wallet_address": wallet_address}),
            "positions": await db.ai_trader_positions.count_documents({"wallet_address": wallet_address}),
            "auto_logs": await db.auto_trade_logs.count_documents({"wallet_address": wallet_address})
        }
        
        if full_reset:
            # FULL RESET: Archive data for learning purposes, then clear stats
            archive_timestamp = datetime.now(timezone.utc).isoformat()
            
            # Archive positions before deleting
            positions_to_archive = await db.ai_trader_positions.find({
                "wallet_address": wallet_address,
                "status": {"$regex": "^closed|no_tokens"}
            }).to_list(1000)
            
            if positions_to_archive:
                for pos in positions_to_archive:
                    pos["archived_at"] = archive_timestamp
                    pos["archive_reason"] = "stats_reset"
                    if "_id" in pos:
                        del pos["_id"]
                await db.ai_trader_positions_archive.insert_many(positions_to_archive)
                logger.info(f"Archived {len(positions_to_archive)} positions for learning")
            
            # Archive auto-trade logs before deleting
            logs_to_archive = await db.auto_trade_logs.find({
                "wallet_address": wallet_address
            }).to_list(5000)
            
            if logs_to_archive:
                for log in logs_to_archive:
                    log["archived_at"] = archive_timestamp
                    log["archive_reason"] = "stats_reset"
                    if "_id" in log:
                        del log["_id"]
                await db.auto_trade_logs_archive.insert_many(logs_to_archive)
                logger.info(f"Archived {len(logs_to_archive)} auto-trade logs for learning")
            
            # Now delete from main collections
            exec_result = await db.ai_trader_executions.delete_many({
                "wallet_address": wallet_address
            })
            
            pos_result = await db.ai_trader_positions.delete_many({
                "wallet_address": wallet_address,
                "status": {"$regex": "^closed|no_tokens"}
            })
            
            log_result = await db.auto_trade_logs.delete_many({
                "wallet_address": wallet_address
            })
            
            stale_result_count = 0
        else:
            # PARTIAL RESET: Only remove non-on-chain records
            exec_result = await db.ai_trader_executions.delete_many({
                "wallet_address": wallet_address,
                "$or": [
                    {"tx_signature": {"$exists": False}},
                    {"tx_signature": None},
                    {"tx_signature": ""}
                ]
            })
            
            pos_result = await db.ai_trader_positions.delete_many({
                "wallet_address": wallet_address,
                "status": {"$ne": "open"},
                "executed_on_chain": {"$ne": True},
                "sell_executed_on_chain": {"$ne": True},
                "$and": [
                    {"$or": [{"tx_signature": {"$exists": False}}, {"tx_signature": None}]},
                    {"$or": [{"sell_tx_signature": {"$exists": False}}, {"sell_tx_signature": None}]}
                ]
            })
            
            log_result = await db.auto_trade_logs.delete_many({
                "wallet_address": wallet_address,
                "$or": [
                    {"success": {"$ne": True}},
                    {"tx_signature": {"$exists": False}},
                    {"tx_signature": None}
                ],
                "action": {"$nin": ["auto_skip", "auto_pause"]}
            })
            
            # Clean up stale positions
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            stale_result = await db.ai_trader_positions.delete_many({
                "wallet_address": wallet_address,
                "status": {"$in": ["pending_stop_loss", "pending_take_profit"]},
                "sell_executed_on_chain": {"$ne": True},
                "created_at": {"$lt": cutoff}
            })
            stale_result_count = stale_result.deleted_count
        
        # Count records after cleanup
        after_counts = {
            "executions": await db.ai_trader_executions.count_documents({"wallet_address": wallet_address}),
            "positions": await db.ai_trader_positions.count_documents({"wallet_address": wallet_address}),
            "auto_logs": await db.auto_trade_logs.count_documents({"wallet_address": wallet_address})
        }
        
        # Get fresh statistics after cleanup
        fresh_history = await get_trade_history(wallet_address, limit=100, on_chain_only=True)
        
        return {
            "success": True,
            "message": "All trading history cleared - fresh start!" if full_reset else "Statistics reset - now showing only on-chain executed trades",
            "removed": {
                "executions": exec_result.deleted_count,
                "positions": pos_result.deleted_count,
                "auto_logs": log_result.deleted_count,
                "stale_positions": stale_result_count if not full_reset else 0
            },
            "before": before_counts,
            "after": after_counts,
            "new_stats": fresh_history["stats"]
        }
        
    except Exception as e:
        logger.error(f"Reset statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        
        # Record in internal ledger (debit — lock funds for this trade)
        try:
            await ledger_record(
                wallet_address, "trade_open", -input_sol,
                reference_id=position_id,
                reference_type="position",
                description=f"Buy {token_symbol.upper()} — {input_sol:.6f} SOL",
                metadata={"token_symbol": token_symbol.upper(), "token_mint": token_mint, "entry_price": entry_price}
            )
        except Exception as le:
            logger.warning(f"Ledger record failed for trade_open: {le}")
        
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
        
        # Record in internal ledger (credit — return funds + P&L)
        try:
            await ledger_record(
                wallet_address, "trade_close", received_sol,
                reference_id=position_id,
                reference_type="position",
                description=f"Sell {position.get('token_symbol', '?')} — {received_sol:.6f} SOL (PnL: {pnl_sol:+.6f})",
                metadata={"token_symbol": position.get("token_symbol"), "pnl_sol": pnl_sol, "pnl_pct": pnl_pct}
            )
        except Exception as le:
            logger.warning(f"Ledger record failed for trade_close: {le}")
        
        # Apply rake on profit
        rake_amount = await apply_rake(wallet_address, pnl_sol, position_id, position.get("token_symbol", "?"))
        
        return {
            "success": True,
            "message": "Position closed",
            "position_id": position_id,
            "pnl": {
                "sol": pnl_sol,
                "percent": pnl_pct
            },
            "rake": {
                "applied": rake_amount > 0,
                "amount_sol": rake_amount,
                "percent": RAKE_PERCENT
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
            "action": "manual_close",
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
        
        # Record in internal ledger (credit — return original + P&L)
        try:
            received = amount_sol + pnl_sol
            await ledger_record(
                request.wallet_address, "trade_close", received,
                reference_id=request.position_id,
                reference_type="position_manual_close",
                description=f"Manual close {position.get('token_symbol', '?')} — {received:.6f} SOL (PnL: {pnl_sol:+.6f})",
                metadata={"token_symbol": position.get("token_symbol"), "pnl_sol": pnl_sol, "pnl_pct": pnl_percent, "exit_reason": request.exit_reason}
            )
        except Exception as le:
            logger.warning(f"Ledger record failed for manual_close: {le}")
        
        # Apply rake on profit
        rake_amount = await apply_rake(request.wallet_address, pnl_sol, request.position_id, position.get("token_symbol", "?"))
        
        return {
            "success": True,
            "message": f"Position closed at ${exit_price:.8f}" if exit_price else "Position closed",
            "position_id": request.position_id,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_percent": pnl_percent,
            "pnl_sol": pnl_sol,
            "rake": {
                "applied": rake_amount > 0,
                "amount_sol": rake_amount,
                "percent": RAKE_PERCENT
            }
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
# Price Alerts are now in routers/price_alerts.py
# ============================================================================



# ============================================================================
# PHASE 3: AUTO-TRADING SYSTEM
# ============================================================================

class AutoTradeSettingsUpdate(BaseModel):
    """Update auto-trade settings"""
    auto_trade_enabled: Optional[bool] = None
    auto_optimization_enabled: Optional[bool] = None  # NEW: Auto-apply optimal settings
    auto_trade_mode: Optional[str] = None
    auto_min_confidence: Optional[float] = None
    auto_max_daily_trades: Optional[int] = None
    auto_max_position_sol: Optional[float] = None
    auto_cooldown_minutes: Optional[int] = None
    auto_require_multiple_signals: Optional[bool] = None
    auto_pause_on_loss: Optional[bool] = None
    auto_total_daily_limit_sol: Optional[float] = None
    # Stop-loss and take-profit settings
    auto_stop_loss_percent: Optional[float] = None
    auto_take_profit_percent: Optional[float] = None
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
            "action": {"$in": ["auto_buy", "auto_sell", "auto_take_profit", "auto_stop_loss"]}
        }).to_list(100)
        
        # Also count from ALL open positions (represents active capital at risk)
        open_positions = await db.ai_trader_positions.find({
            "wallet_address": wallet_address,
            "status": "open"
        }).to_list(100)
        
        # Calculate stats from both logs and positions
        successful_logs = [log for log in today_logs if log.get("success")]
        buy_logs = [log for log in successful_logs if log.get("action") in ["auto_buy"]]
        sol_from_logs = sum(log.get("amount_sol", 0) for log in buy_logs)
        
        # All open positions represent SOL currently in trades
        position_sol = sum(p.get("amount_sol", 0) for p in open_positions)
        
        # Count completed round-trips today (1 trade = buy + sell)
        today_completed = await db.ai_trader_positions.count_documents({
            "wallet_address": wallet_address,
            "closed_at": {"$gte": today_start},
            "status": {"$regex": "^closed"}
        })
        
        today_stats = {
            "trades_executed": today_completed,  # Completed round-trips only
            "total_sol_used": sol_from_logs + position_sol,  # Total capital at risk
            "wins": len([log for log in successful_logs if log.get("pnl_sol", 0) > 0]),
            "losses": len([log for log in successful_logs if log.get("pnl_sol", 0) < 0]),
            "pnl_sol": sum(log.get("pnl_sol", 0) for log in successful_logs),
            "open_positions": len(open_positions)
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
        
        # Check daily limits (based on completed round-trips)
        if today_stats["trades_executed"] >= settings.get("auto_max_daily_trades", 3):
            auto_paused = True
            pause_reason = "Daily trade limit reached"
        
        if today_stats["total_sol_used"] >= settings.get("auto_total_daily_limit_sol", 1.0):
            auto_paused = True
            pause_reason = "Daily SOL limit reached"
        
        return {
            "auto_trade_enabled": settings.get("auto_trade_enabled", False),
            "auto_optimization_enabled": settings.get("auto_optimization_enabled", False),
            "auto_paused": auto_paused,
            "pause_reason": pause_reason,
            "settings": {
                "mode": settings.get("trading_mode", settings.get("auto_trade_mode", "conservative")),
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
    """Update auto-trade settings and check for exit triggers if TP/SL changed."""
    try:
        update_data = {k: v for k, v in settings.dict().items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.ai_trader_settings.update_one(
            {"wallet_address": wallet_address},
            {"$set": update_data},
            upsert=True
        )
        
        # If TP or SL settings changed, check for exit triggers
        exits_triggered = []
        if "auto_take_profit_percent" in update_data or "auto_stop_loss_percent" in update_data:
            try:
                logger.info(f"TP/SL settings changed for {wallet_address}, checking for exit triggers...")
                exit_result = await auto_trade_check_exits(wallet_address)
                if exit_result.get("success") and exit_result.get("exits"):
                    exits_triggered = exit_result.get("exits", [])
                    logger.info(f"Settings change triggered {len(exits_triggered)} exit(s)")
            except Exception as e:
                logger.warning(f"Failed to check exits after settings update: {e}")
        
        return {
            "success": True,
            "updated_fields": list(update_data.keys()),
            "message": "Auto-trade settings updated",
            "exits_triggered": exits_triggered,
            "exits_count": len(exits_triggered)
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
    Delegated to services/auto_trader_engine.py for modularity.
    """
    from services.auto_trader_engine import run_scan_and_execute
    return await run_scan_and_execute(wallet_address)


@router.post("/auto-trade/check-exits/{wallet_address}")
async def auto_trade_check_exits(wallet_address: str):
    """
    Check open positions for stop-loss or take-profit triggers.
    Delegated to services/auto_trader_engine.py for modularity.
    """
    from services.auto_trader_engine import run_check_exits
    return await run_check_exits(wallet_address)
