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


async def apply_rake(wallet_address: str, pnl_sol: float, position_id: str, token_symbol: str) -> float:
    """
    Apply a rake (platform fee) on profitable trades.
    Takes RAKE_PERCENT of the PROFIT ONLY — never touches the original investment.
    Returns the rake amount deducted (0 if trade was not profitable).
    """
    if pnl_sol <= 0:
        return 0.0

    rake_amount = round(pnl_sol * (RAKE_PERCENT / 100), 9)

    try:
        await ledger_record(
            wallet_address, "fee", -rake_amount,
            reference_id=position_id,
            reference_type="rake",
            description=f"Rake {RAKE_PERCENT}% on {token_symbol} profit ({pnl_sol:+.6f} SOL)",
            metadata={
                "token_symbol": token_symbol,
                "gross_pnl_sol": pnl_sol,
                "rake_percent": RAKE_PERCENT,
                "rake_sol": rake_amount,
            }
        )
        logger.info(f"Rake applied: {rake_amount:.6f} SOL ({RAKE_PERCENT}% of {pnl_sol:.6f} profit) for {token_symbol} position {position_id}")
    except Exception as e:
        logger.warning(f"Rake ledger record failed: {e}")

    return rake_amount


async def ensure_sufficient_sol_for_trade(wallet_address: str, required_sol: float) -> dict:
    """
    Ensure the custodial wallet has sufficient SOL for a trade.
    If balance is low, automatically burn empty token accounts to reclaim rent.
    
    Returns:
        dict with 'success', 'balance', 'burned_accounts', 'reclaimed_sol'
    """
    from routers.custodial_wallet import get_wallet_balance
    
    try:
        custodial_wallet = await db.custodial_wallets.find_one({"user_wallet": wallet_address})
        if not custodial_wallet:
            return {"success": False, "error": "No custodial wallet found"}
        
        custodial_address = custodial_wallet["custodial_address"]
        current_balance = await get_wallet_balance(custodial_address)
        current_balance_sol = current_balance / 1_000_000_000  # Convert lamports to SOL
        
        # Calculate required (trade amount + fees + reserve)
        required_total = required_sol + 0.005  # Keep 0.005 SOL reserve for fees
        
        # If we have enough, no burn needed
        if current_balance_sol >= required_total:
            return {
                "success": True,
                "balance": current_balance_sol,
                "burned_accounts": 0,
                "reclaimed_sol": 0
            }
        
        # If balance is low, try to burn empty accounts
        logger.info(f"Low balance ({current_balance_sol:.4f} SOL) - attempting auto-burn before trade")
        
        try:
            from routers.pugburn import scan_vacant_accounts, burn_custodial_accounts
            
            # Scan for empty accounts
            scan_result = await scan_vacant_accounts(custodial_address)
            
            if scan_result.vacant_accounts:
                # Burn up to 15 accounts at a time
                burn_result = await burn_custodial_accounts(wallet_address, max_accounts=15)
                
                if burn_result.get("success"):
                    # Re-check balance after burn
                    new_balance = await get_wallet_balance(custodial_address)
                    new_balance_sol = new_balance / 1_000_000_000
                    
                    logger.info(f"Auto-burn complete: reclaimed {burn_result.get('sol_reclaimed', 0):.4f} SOL, new balance: {new_balance_sol:.4f} SOL")
                    
                    return {
                        "success": new_balance_sol >= required_total,
                        "balance": new_balance_sol,
                        "burned_accounts": burn_result.get("accounts_closed", 0),
                        "reclaimed_sol": burn_result.get("sol_reclaimed", 0)
                    }
            
            # No accounts to burn or burn failed
            return {
                "success": current_balance_sol >= required_total,
                "balance": current_balance_sol,
                "burned_accounts": 0,
                "reclaimed_sol": 0,
                "warning": "No empty accounts to reclaim" if not scan_result.vacant_accounts else "Burn failed"
            }
            
        except Exception as burn_error:
            logger.warning(f"Auto-burn failed: {burn_error}")
            # Continue with current balance even if burn fails
            return {
                "success": current_balance_sol >= required_total,
                "balance": current_balance_sol,
                "burned_accounts": 0,
                "reclaimed_sol": 0,
                "warning": f"Auto-burn failed: {str(burn_error)}"
            }
            
    except Exception as e:
        logger.error(f"Error checking SOL balance: {e}")
        return {"success": False, "error": str(e)}

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
    pnl_sol: float = None,
    strategy: str = None,  # Auto-filled from trade trigger/reason
    trigger_reason: str = None  # The reason that triggered the trade
):
    """
    Create a pending journal entry for an auto-trade.
    This integrates auto-trades with the trading journal.
    """
    try:
        trade_id = f"AT{str(uuid.uuid4())[:8].upper()}"
        
        # Determine strategy from trade type and trigger
        auto_strategy = strategy
        if not auto_strategy:
            if trade_type == "buy":
                auto_strategy = trigger_reason or "AI Signal - Auto Buy"
            else:
                # For sells, determine if it was TP, SL, or manual
                if trigger_reason:
                    if "take_profit" in trigger_reason.lower() or "take-profit" in trigger_reason.lower():
                        auto_strategy = "Take-Profit Triggered"
                    elif "stop_loss" in trigger_reason.lower() or "stop-loss" in trigger_reason.lower():
                        auto_strategy = "Stop-Loss Triggered"
                    else:
                        auto_strategy = trigger_reason
                else:
                    auto_strategy = "Auto-Sell"
        
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
            "strategy": auto_strategy,  # Auto-filled strategy
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
        logger.info(f"Created pending journal entry {trade_id} for {asset} {trade_type} with strategy: {auto_strategy}")
        return trade_id
    except Exception as e:
        logger.error(f"Failed to create pending journal entry: {e}")
        return None


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
        
        # If auto_optimization_enabled, fetch and apply optimal settings
        if settings.get("auto_optimization_enabled"):
            try:
                from routers.signal_analytics import get_optimal_settings
                optimal = await get_optimal_settings()
                if optimal.get("sufficient_data") and optimal.get("settings"):
                    opt_settings = optimal["settings"]
                    auto_trade_opt = opt_settings.get("auto_trade", {})
                    
                    # Apply optimal settings to current settings
                    settings["auto_min_confidence"] = auto_trade_opt.get("recommended_min_confidence", settings.get("auto_min_confidence", 0.6))
                    settings["auto_max_daily_trades"] = auto_trade_opt.get("recommended_max_daily_trades", settings.get("auto_max_daily_trades", 3))
                    settings["auto_cooldown_minutes"] = auto_trade_opt.get("recommended_cooldown_minutes", settings.get("auto_cooldown_minutes", 45))
                    settings["auto_require_multiple_signals"] = auto_trade_opt.get("require_multiple_signals", True)
                    
                    logger.info(f"Auto-optimization applied: min_conf={settings['auto_min_confidence']}, max_trades={settings['auto_max_daily_trades']}, cooldown={settings['auto_cooldown_minutes']}")
            except Exception as e:
                logger.warning(f"Failed to fetch optimal settings: {e}, using manual settings")
        
        # FIRST: Check and execute exits for positions hitting TP/SL
        exits_result = await auto_trade_check_exits(wallet_address)
        exits_executed = exits_result.get("exits", [])
        if exits_executed:
            logger.info(f"Auto-exits executed: {len(exits_executed)} positions closed for {wallet_address}")
        
        # Check daily limits
        # A "trade" = a completed round-trip (buy + sell). 
        # We count closed positions today, NOT buys. Sells (TP/SL) must never be blocked.
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        today_completed_trades = await db.ai_trader_positions.count_documents({
            "wallet_address": wallet_address,
            "closed_at": {"$gte": today_start},
            "status": {"$regex": "^closed"}
        })
        
        max_daily = settings.get("auto_max_daily_trades", 3)
        if today_completed_trades >= max_daily:
            return {
                "success": False,
                "message": f"Daily trade limit reached ({today_completed_trades}/{max_daily} completed trades)",
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
        elif mode in ("moderate", "normal"):
            pass  # Use the user's stored auto_min_confidence as-is
        else:  # conservative
            min_confidence = min(0.75, min_confidence + 0.05)  # Conservative: 0.70-0.75
        
        # Log effective settings
        trading_mode = settings.get("trading_mode", "normal")
        logger.info(f"Auto-trade scan for {wallet_address}: mode={mode}, trading_mode={trading_mode}, min_conf={min_confidence:.2f}, risk={risk_level}")
        
        # === SNIPER MODE: Scan for brand new tokens ===
        sniper_targets = []
        if trading_mode == "sniper":
            try:
                from services.token_sniper import scan_new_pairs
                sniper_targets = await scan_new_pairs()
                if sniper_targets:
                    logger.info(f"Sniper mode: found {len(sniper_targets)} new pair targets")
            except Exception as e:
                logger.warning(f"Sniper scan error: {e}")
        
        # Get tokens to scan based on risk level (exclude SOL - can't swap SOL to SOL)
        tokens_to_scan = []
        runner_tokens = []  # Will store runner data separately
        
        if risk_level in ["safer", "both"]:
            tokens_to_scan.extend(["JUP", "PYTH", "RNDR", "BONK", "RAY", "WIF", "HNT", "JITO"])
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
        remaining_daily_trades = max_daily - today_completed_trades  # Track how many trades we can still do
        
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
                    
                    # === QUALITY CHECK: Volume + Liquidity filter ===
                    from services.market_quality import extract_market_quality, build_price_history_from_dex, confidence_penalty_for_synthetic_data
                    quality = extract_market_quality(best_pair)
                    if not quality["passes_quality_check"]:
                        skipped.append({"symbol": symbol, "reason": f"Market quality: {', '.join(quality['rejection_reasons'])}"})
                        continue
                    
                    # Get price history for analysis
                    current_price = float(best_pair.get("priceUsd", 0) or 0)
                    
                    if current_price <= 0:
                        continue
                    
                    # === IMPROVEMENT 1: Try REAL OHLCV data first, fall back to synthetic ===
                    from services.price_collector import get_real_price_history, add_runner_to_tracking
                    prices, is_synthetic = await get_real_price_history(token_mint)
                    
                    if is_synthetic:
                        # Fall back to synthetic price history from DexScreener % changes
                        price_change_24h = float(best_pair.get("priceChange", {}).get("h24", 0) or 0)
                        price_change_6h = float(best_pair.get("priceChange", {}).get("h6", 0) or 0)
                        price_change_1h = float(best_pair.get("priceChange", {}).get("h1", 0) or 0)
                        prices, is_synthetic = build_price_history_from_dex(current_price, price_change_24h, price_change_6h, price_change_1h)
                        # Ensure this token is tracked for future real data
                        await add_runner_to_tracking(symbol, token_mint)
                    else:
                        logger.info(f"Using REAL price data for {symbol} ({len(prices)} candles)")
                    
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
                    
                    # Apply synthetic data penalty
                    if should_trade and is_synthetic:
                        trade_confidence = confidence_penalty_for_synthetic_data(trade_confidence)
                        trade_reason = f"[SYNTHETIC DATA -10%] {trade_reason}"
                        if trade_confidence < min_confidence:
                            should_trade = False
                            skipped.append({"symbol": symbol, "reason": f"Confidence {trade_confidence:.2f} below threshold after synthetic penalty"})
                            continue
                    
                    # Bonus: if multiple strategies strongly agree, boost confidence slightly
                    if should_trade and agreement_count >= 2:
                        trade_confidence = min(0.95, trade_confidence + 0.05)
                    
                    # === IMPROVEMENT 2: Smart Money confidence adjustment ===
                    smart_money_adj = 0.0
                    try:
                        from services.smart_money_tracker import get_confidence_adjustment as smart_money_confidence
                        smart_money_adj = await smart_money_confidence(token_mint)
                        if abs(smart_money_adj) > 0.01:
                            trade_confidence = max(0.0, min(0.95, trade_confidence + smart_money_adj))
                            trade_reason = f"[SM {'+'  if smart_money_adj > 0 else ''}{smart_money_adj:.0%}] {trade_reason}"
                            logger.info(f"Smart money adjustment for {symbol}: {smart_money_adj:+.2f}")
                    except Exception as e:
                        logger.debug(f"Smart money check skipped for {symbol}: {e}")
                    
                    # === IMPROVEMENT 3: Social Sentiment confidence adjustment ===
                    sentiment_adj = 0.0
                    try:
                        from services.social_sentiment import get_confidence_adjustment as sentiment_confidence
                        sentiment_adj = await sentiment_confidence(token_mint, pair_data=best_pair)
                        if abs(sentiment_adj) > 0.01:
                            trade_confidence = max(0.0, min(0.95, trade_confidence + sentiment_adj))
                            trade_reason = f"[SENT {'+'  if sentiment_adj > 0 else ''}{sentiment_adj:.0%}] {trade_reason}"
                    except Exception as e:
                        logger.debug(f"Sentiment check skipped for {symbol}: {e}")
                    
                    # Re-check confidence after all adjustments
                    if should_trade and trade_confidence < min_confidence:
                        should_trade = False
                        skipped.append({"symbol": symbol, "reason": f"Confidence {trade_confidence:.2f} below threshold after adjustments (SM:{smart_money_adj:+.2f}, SENT:{sentiment_adj:+.2f})"})
                        continue
                    
                    # === MULTI-TIMEFRAME CONFIRMATION ===
                    if should_trade and settings.get("multi_timeframe_enabled", True):
                        price_changes = best_pair.get("priceChange", {})
                        change_5m = float(price_changes.get("m5", 0) or 0)
                        change_1h = float(price_changes.get("h1", 0) or 0)
                        change_6h = float(price_changes.get("h6", 0) or 0)
                        change_24h = float(price_changes.get("h24", 0) or 0)
                        
                        # Count how many timeframes agree with the signal direction
                        tf_bullish = sum(1 for c in [change_5m, change_1h, change_6h, change_24h] if c > 0)
                        tf_bearish = sum(1 for c in [change_5m, change_1h, change_6h, change_24h] if c < 0)
                        
                        # For a BUY signal, we want mostly bullish timeframes
                        if combined.get("action") == "buy":
                            if tf_bearish >= 3:
                                # 3+ timeframes bearish = strong contradiction
                                trade_confidence = max(0.0, trade_confidence - 0.15)
                                trade_reason = f"[MTF CONFLICT -{tf_bearish}/4 bearish] {trade_reason}"
                                if trade_confidence < min_confidence:
                                    should_trade = False
                                    skipped.append({"symbol": symbol, "reason": f"Multi-TF conflict: {tf_bearish}/4 timeframes bearish"})
                                    continue
                            elif tf_bullish >= 3:
                                # 3+ timeframes agree = bonus
                                trade_confidence = min(0.95, trade_confidence + 0.05)
                                trade_reason = f"[MTF ALIGNED {tf_bullish}/4] {trade_reason}"
                    
                    if should_trade:
                        # Check daily limit hasn't been reached during this scan
                        if remaining_daily_trades <= 0:
                            skipped.append({"symbol": symbol, "reason": f"Daily trade limit reached ({max_daily}/{max_daily})"})
                            continue
                        
                        # Check if we already have an OPEN position
                        existing_position = await db.ai_trader_positions.find_one({
                            "wallet_address": wallet_address,
                            "token_mint": token_mint,
                            "status": "open"
                        })
                        
                        if existing_position:
                            skipped.append({
                                "symbol": symbol,
                                "reason": "Already have open position"
                            })
                            continue
                        
                        # CRITICAL: Check if we recently hit stop-loss on this token
                        # Don't re-buy a token within 60 minutes of a stop-loss
                        stop_loss_cooldown_minutes = 60
                        stop_loss_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=stop_loss_cooldown_minutes)).isoformat()
                        
                        recent_stop_loss = await db.ai_trader_positions.find_one({
                            "wallet_address": wallet_address,
                            "token_mint": token_mint,
                            "status": {"$regex": "stop_loss|closed_stop"},
                            "closed_at": {"$gte": stop_loss_cutoff}
                        })
                        
                        if recent_stop_loss:
                            logger.warning(f"Skipping {symbol}: Recent stop-loss triggered within {stop_loss_cooldown_minutes} minutes")
                            skipped.append({
                                "symbol": symbol,
                                "reason": f"Recent stop-loss (cooldown {stop_loss_cooldown_minutes}m)"
                            })
                            continue
                        
                        # Also check for any recent loss on this token (including pending exits)
                        recent_loss = await db.ai_trader_positions.find_one({
                            "wallet_address": wallet_address,
                            "token_mint": token_mint,
                            "status": {"$in": ["closed_stop_loss", "closed_manual_sell", "pending_stop_loss"]},
                            "created_at": {"$gte": stop_loss_cutoff}
                        })
                        
                        if recent_loss:
                            logger.warning(f"Skipping {symbol}: Recent losing position within {stop_loss_cooldown_minutes} minutes")
                            skipped.append({
                                "symbol": symbol,
                                "reason": f"Recent losing trade (cooldown {stop_loss_cooldown_minutes}m)"
                            })
                            continue
                        
                        # Calculate position size with CONVICTION-BASED SIZING
                        base_position = min(max_position, settings.get("max_position_sol", 0.5))
                        
                        if settings.get("conviction_sizing_enabled", True):
                            # Scale position by confidence:
                            # 90%+ = 1.5x, 80-90% = 1.2x, 70-80% = 1.0x, 60-70% = 0.7x, <60% = 0.5x
                            if trade_confidence >= 0.90:
                                sizing_mult = 1.5
                            elif trade_confidence >= 0.80:
                                sizing_mult = 1.2
                            elif trade_confidence >= 0.70:
                                sizing_mult = 1.0
                            elif trade_confidence >= 0.60:
                                sizing_mult = 0.7
                            else:
                                sizing_mult = 0.5
                            position_sol = round(min(base_position * sizing_mult, max_position), 4)
                            trade_reason = f"[SIZE {sizing_mult}x] {trade_reason}"
                        else:
                            position_sol = base_position
                        
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
                            "data_source": "synthetic" if is_synthetic else "real_ohlcv",
                            "smart_money_adj": smart_money_adj,
                            "sentiment_adj": sentiment_adj,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Try to execute via custodial wallet
                        tx_signature = None
                        execution_success = False
                        execution_error = None
                        
                        try:
                            # Auto-burn empty accounts to reclaim SOL before buying
                            burn_result = await ensure_sufficient_sol_for_trade(wallet_address, position_sol)
                            if burn_result.get("burned_accounts", 0) > 0:
                                logger.info(f"Auto-burn before signal buy: reclaimed {burn_result.get('reclaimed_sol', 0):.4f} SOL from {burn_result['burned_accounts']} accounts")
                            
                            # CRITICAL: Check ledger available balance FIRST
                            from services.ledger import get_available_balance
                            ledger_available = await get_available_balance(wallet_address)
                            if ledger_available < position_sol:
                                execution_error = f"Insufficient ledger balance: {ledger_available:.6f} SOL available, need {position_sol:.4f} SOL"
                                logger.warning(execution_error)
                                skipped.append({"symbol": symbol, "reason": execution_error})
                                continue
                            
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
                            
                            # Atomic duplicate guard — prevent race condition double-inserts
                            existing_check = await db.ai_trader_positions.find_one({
                                "wallet_address": wallet_address,
                                "token_mint": token_mint,
                                "status": "open"
                            })
                            if existing_check:
                                logger.warning(f"Duplicate position prevented for {symbol} — already open")
                                skipped.append({"symbol": symbol, "reason": "Duplicate position race condition prevented"})
                            else:
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
                                tx_signature=tx_signature,
                                strategy=combined.get("strategy"),
                                trigger_reason=trade_reason
                            )
                            
                            # Record in internal ledger (debit — lock funds)
                            try:
                                await ledger_record(
                                    wallet_address, "trade_open", -position_sol,
                                    reference_id=position_id,
                                    reference_type="auto_buy",
                                    description=f"Auto-buy {symbol} — {position_sol:.6f} SOL",
                                    metadata={"token_symbol": symbol, "token_mint": token_mint, "confidence": trade_confidence}
                                )
                            except Exception as le:
                                logger.warning(f"Ledger record failed for auto_buy: {le}")
                            
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
                            remaining_daily_trades -= 1
                            
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
                        
                        # === QUALITY CHECK: Volume + Liquidity filter for runners ===
                        from services.market_quality import extract_market_quality, build_price_history_from_dex, confidence_penalty_for_synthetic_data
                        runner_volume_24h = runner.get("volume_24h", 0)
                        runner_liquidity = runner.get("liquidity_usd", 0)
                        # Build a minimal pair_data dict for quality check
                        runner_pair_data = {
                            "volume": {"h24": runner_volume_24h},
                            "liquidity": {"usd": runner_liquidity}
                        }
                        quality = extract_market_quality(runner_pair_data)
                        if not quality["passes_quality_check"]:
                            skipped.append({"symbol": f"{symbol} (RUNNER)", "reason": f"Market quality: {', '.join(quality['rejection_reasons'])}"})
                            continue
                        
                        # Build price history from runner data
                        price_change_24h = runner.get("price_change_24h", 0)
                        price_change_6h = runner.get("price_change_6h", 0)
                        price_change_1h = runner.get("price_change_1h", 0)
                        
                        prices, is_synthetic = build_price_history_from_dex(current_price, price_change_24h, price_change_6h, price_change_1h)
                        
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
                        
                        # Apply synthetic data penalty for runners too
                        if should_trade and is_synthetic:
                            trade_confidence = confidence_penalty_for_synthetic_data(trade_confidence)
                            trade_reason = f"[SYNTHETIC DATA -10%] {trade_reason}"
                            if trade_confidence < min_confidence:
                                should_trade = False
                                skipped.append({"symbol": f"{symbol} (RUNNER)", "reason": f"Confidence {trade_confidence:.2f} below threshold after synthetic penalty"})
                                continue
                        
                        if should_trade:
                            # Check daily limit hasn't been reached during this scan
                            if remaining_daily_trades <= 0:
                                skipped.append({"symbol": f"{symbol} (RUNNER)", "reason": f"Daily trade limit reached ({max_daily}/{max_daily})"})
                                continue
                            
                            # Check if we already have an OPEN position
                            existing_position = await db.ai_trader_positions.find_one({
                                "wallet_address": wallet_address,
                                "token_mint": token_mint,
                                "status": "open"
                            })
                            
                            if existing_position:
                                skipped.append({
                                    "symbol": f"{symbol} (RUNNER)",
                                    "reason": "Already have open position",
                                    "runner_score": runner_score
                                })
                                continue
                            
                            # CRITICAL: Check if we recently hit stop-loss on this token
                            stop_loss_cooldown_minutes = 60
                            stop_loss_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=stop_loss_cooldown_minutes)).isoformat()
                            
                            recent_stop_loss = await db.ai_trader_positions.find_one({
                                "wallet_address": wallet_address,
                                "token_mint": token_mint,
                                "status": {"$in": ["closed_stop_loss", "closed_manual_sell", "pending_stop_loss"]},
                                "created_at": {"$gte": stop_loss_cutoff}
                            })
                            
                            if recent_stop_loss:
                                logger.warning(f"Skipping runner {symbol}: Recent stop-loss within {stop_loss_cooldown_minutes}m")
                                skipped.append({
                                    "symbol": f"{symbol} (RUNNER)",
                                    "reason": f"Recent stop-loss (cooldown {stop_loss_cooldown_minutes}m)",
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
                                # Auto-burn empty accounts to reclaim SOL before runner buy
                                burn_result = await ensure_sufficient_sol_for_trade(wallet_address, position_sol)
                                if burn_result.get("burned_accounts", 0) > 0:
                                    logger.info(f"Auto-burn before runner buy: reclaimed {burn_result.get('reclaimed_sol', 0):.4f} SOL from {burn_result['burned_accounts']} accounts")
                                
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
                                
                                # Atomic duplicate guard for runners
                                runner_dup = await db.ai_trader_positions.find_one({
                                    "wallet_address": wallet_address,
                                    "token_mint": token_mint,
                                    "status": "open",
                                    "execution_id": {"$ne": position_doc.get("execution_id")}
                                })
                                if runner_dup:
                                    logger.warning(f"Duplicate runner position prevented for {symbol}")
                                    skipped.append({"symbol": f"{symbol} (RUNNER)", "reason": "Duplicate position race condition"})
                                    continue
                                
                                await db.ai_trader_positions.insert_one(position_doc)
                                
                                # Record in internal ledger (debit — lock funds for runner trade)
                                try:
                                    await ledger_record(
                                        wallet_address, "trade_open", -position_sol,
                                        reference_id=position_id,
                                        reference_type="auto_buy_runner",
                                        description=f"Auto-buy runner {symbol} — {position_sol:.6f} SOL",
                                        metadata={"token_symbol": symbol, "runner_score": runner_score}
                                    )
                                except Exception as le:
                                    logger.warning(f"Ledger record failed for runner buy: {le}")
                                
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
                                remaining_daily_trades -= 1
                                
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
        
        # Include exits in the response
        exits_count = len(exits_executed)
        
        # === SNIPER MODE EXECUTION ===
        SNIPER_MAX_POSITION_MULT = 0.3
        sniper_trades = 0
        if sniper_targets and today_completed_trades < max_daily:
            for target in sniper_targets[:2]:  # Max 2 sniper trades per scan
                try:
                    if today_completed_trades >= max_daily:
                        break
                    
                    sniper_conf = target["confidence"]
                    if sniper_conf < min_confidence:
                        skipped.append({"symbol": target["token_symbol"], "reason": f"Sniper conf {sniper_conf:.2f} < {min_confidence:.2f}"})
                        continue
                    
                    # Sniper uses smaller positions (30% of normal)
                    sniper_position = round(max_position * SNIPER_MAX_POSITION_MULT, 4)
                    
                    # Apply conviction sizing to sniper positions too
                    if settings.get("conviction_sizing_enabled", True):
                        if sniper_conf >= 0.80:
                            sniper_position = round(sniper_position * 1.2, 4)
                        elif sniper_conf < 0.65:
                            sniper_position = round(sniper_position * 0.5, 4)
                    
                    if sniper_position < MIN_POSITION_SOL:
                        continue
                    
                    # Check duplicate position
                    existing_pos = await db.ai_trader_positions.find_one({
                        "wallet_address": wallet_address,
                        "token_mint": target["token_mint"],
                        "status": {"$in": ["open", "pending_stop_loss", "pending_take_profit"]}
                    })
                    if existing_pos:
                        skipped.append({"symbol": target["token_symbol"], "reason": "Already have open position"})
                        continue
                    
                    logger.info(f"SNIPER: Executing buy for {target['token_symbol']} (conf: {sniper_conf:.2f}, pos: {sniper_position} SOL, age: {target['pair_age_minutes']}min)")
                    
                    from services.token_sniper import record_snipe
                    await record_snipe(target["token_mint"], target["token_symbol"], sniper_conf, wallet_address)
                    
                    sniper_position_id = f"snipe_{target['token_symbol']}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                    sniper_execution_id = f"exec_snipe_{datetime.now(timezone.utc).timestamp()}"
                    
                    position_doc = {
                        "position_id": sniper_position_id,
                        "execution_id": sniper_execution_id,
                        "wallet_address": wallet_address,
                        "token_symbol": target["token_symbol"],
                        "token_mint": target["token_mint"],
                        "amount_sol": sniper_position,
                        "entry_price": target["price_usd"],
                        "stop_loss_price": target["price_usd"] * (1 - settings.get("auto_stop_loss_percent", 10) / 100),
                        "take_profit_price": target["price_usd"] * (1 + settings.get("auto_take_profit_percent", 20) / 100),
                        "trade_type": "buy",
                        "status": "open",
                        "auto_trade": True,
                        "is_snipe": True,
                        "confidence": sniper_conf,
                        "strategy": "sniper",
                        "data_source": "dexscreener_new_pair",
                        "pair_age_minutes": target["pair_age_minutes"],
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await db.ai_trader_positions.insert_one(position_doc)
                    
                    # Record in internal ledger (debit — lock funds for sniper trade)
                    try:
                        await ledger_record(
                            wallet_address, "trade_open", -sniper_position,
                            reference_id=position_doc.get("position_id", ""),
                            reference_type="sniper_buy",
                            description=f"Sniper buy {target['token_symbol']} — {sniper_position:.6f} SOL",
                            metadata={"token_symbol": target["token_symbol"], "pair_age_minutes": target["pair_age_minutes"]}
                        )
                    except Exception as le:
                        logger.warning(f"Ledger record failed for sniper buy: {le}")
                    
                    executed_trades.append({
                        "symbol": target["token_symbol"],
                        "action": "sniper_buy",
                        "amount_sol": sniper_position,
                        "confidence": sniper_conf,
                        "reason": f"Sniper: new pair ({target['pair_age_minutes']}min old), liq ${target['liquidity_usd']:,.0f}"
                    })
                    sniper_trades += 1
                    today_completed_trades += 1
                    
                except Exception as e:
                    logger.warning(f"Sniper execution error for {target.get('token_symbol')}: {e}")
        
        # Summarize results

        known_trades = len([t for t in executed_trades if t.get("action") != "sniper_buy" and t.get("action") != "runner_buy"])
        runner_trades_count = len([t for t in executed_trades if t.get("action") == "runner_buy"])
        
        message_parts = []
        if exits_count:
            message_parts.append(f"{exits_count} exits")
        if known_trades:
            message_parts.append(f"{known_trades} known buys")
        if runner_trades_count:
            message_parts.append(f"{runner_trades_count} runner buys")
        if sniper_trades:
            message_parts.append(f"{sniper_trades} sniper buys")
        
        return {
            "success": True,
            "trades_executed": len(executed_trades),
            "trades": executed_trades,
            "exits_executed": exits_count,
            "exits": exits_executed,
            "skipped": skipped,
            "runners_found": len(runner_tokens),
            "sniper_targets_found": len(sniper_targets),
            "trading_mode": trading_mode,
            "message": f"Auto-scan complete: {', '.join(message_parts) if message_parts else 'no trades'}"
        }
        
    except Exception as e:
        logger.error(f"Auto-trade scan error: {e}")
        return {"success": False, "error": str(e), "trades": []}


@router.post("/auto-trade/check-exits/{wallet_address}")
async def auto_trade_check_exits(wallet_address: str):
    """
    Check open positions for stop-loss or take-profit triggers.
    Implements TRAILING STOP-LOSS: when price rises, stop-loss moves up to lock in gains.
    Executes sells on-chain via custodial wallet when triggers hit.
    Should be called periodically to manage risk.
    """
    from routers.custodial_wallet import execute_auto_trade, get_wallet_balance
    
    try:
        settings = await db.ai_trader_settings.find_one({"wallet_address": wallet_address})
        
        if not settings or not settings.get("auto_trade_enabled"):
            return {"success": False, "message": "Auto-trading not enabled", "exits": []}
        
        # Get TP/SL percentages from settings
        stop_loss_pct = settings.get("auto_stop_loss_percent", settings.get("stop_loss_percent", 10)) / 100
        take_profit_pct = settings.get("auto_take_profit_percent", settings.get("take_profit_percent", 20)) / 100
        
        # Trailing stop configuration
        trailing_enabled = settings.get("trailing_stop_enabled", settings.get("auto_trailing_stop_enabled", True))
        # Trail activation: trailing stop kicks in after price rises this % above entry
        trail_activation_pct = settings.get("trailing_activation_pct", 5) / 100  # Default 5%
        # Trail distance: how far below the peak price the stop-loss trails
        trail_distance_pct = settings.get("trailing_distance_pct", settings.get("auto_trailing_stop_percent", 0)) / 100
        # If trail distance is 0 or not set, use the original stop loss % as trail distance
        if trail_distance_pct <= 0:
            trail_distance_pct = stop_loss_pct
        
        logger.info(f"Checking exits with SL: {stop_loss_pct*100}%, TP: {take_profit_pct*100}%, Trailing: {'ON' if trailing_enabled else 'OFF'}")
        
        # Get all open positions AND positions with pending exit status (for retry)
        positions = await db.ai_trader_positions.find({
            "wallet_address": wallet_address,
            "status": {"$in": ["open", "pending_stop_loss", "pending_take_profit"]}
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
                    
                    # === TRAILING STOP-LOSS LOGIC ===
                    # Track the highest price seen since entry
                    peak_price = position.get("peak_price", entry_price)
                    trailing_stop_active = position.get("trailing_stop_active", False)
                    
                    # Update peak price if current price is higher
                    if current_price > peak_price:
                        peak_price = current_price
                        await db.ai_trader_positions.update_one(
                            {"position_id": position.get("position_id")},
                            {"$set": {"peak_price": peak_price}}
                        )
                    
                    # Calculate base stop-loss and take-profit
                    base_stop_loss = entry_price * (1 - stop_loss_pct)
                    take_profit = entry_price * (1 + take_profit_pct)
                    
                    # Determine effective stop-loss (base or trailing)
                    if trailing_enabled and entry_price > 0:
                        peak_gain_pct = (peak_price - entry_price) / entry_price
                        
                        # Activate trailing stop when price has risen above activation threshold
                        if peak_gain_pct >= trail_activation_pct:
                            trailing_stop_active = True
                            # Trailing stop = peak price - trail distance
                            trailing_stop = peak_price * (1 - trail_distance_pct)
                            # Trailing stop should never be lower than entry price (lock in at least breakeven)
                            trailing_stop = max(trailing_stop, entry_price * 1.001)
                            # Use trailing stop if it's higher than base stop-loss
                            stop_loss = max(base_stop_loss, trailing_stop)
                            
                            # Update trailing stop state
                            if not position.get("trailing_stop_active"):
                                await db.ai_trader_positions.update_one(
                                    {"position_id": position.get("position_id")},
                                    {"$set": {
                                        "trailing_stop_active": True,
                                        "trailing_stop_price": trailing_stop,
                                        "trail_activated_at": datetime.now(timezone.utc).isoformat()
                                    }}
                                )
                                logger.info(f"Trailing stop ACTIVATED for {symbol}: trail @ ${trailing_stop:.8f} (peak: ${peak_price:.8f})")
                            else:
                                await db.ai_trader_positions.update_one(
                                    {"position_id": position.get("position_id")},
                                    {"$set": {"trailing_stop_price": trailing_stop}}
                                )
                        else:
                            stop_loss = base_stop_loss
                    else:
                        stop_loss = base_stop_loss
                    
                    # Calculate current P&L percentage
                    if entry_price > 0:
                        current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:
                        current_pnl_pct = 0
                    
                    trail_info = f", TRAIL={'ACTIVE' if trailing_stop_active else 'OFF'}" if trailing_enabled else ""
                    logger.info(f"Position {symbol}: entry={entry_price:.8f}, current={current_price:.8f}, peak={peak_price:.8f}, SL={stop_loss:.8f}, TP={take_profit:.8f}, P/L={current_pnl_pct:.2f}%{trail_info}")
                    
                    # Check for exit conditions
                    exit_action = None
                    exit_reason = ""
                    position_status = position.get("status", "open")
                    
                    # If position is in pending state, retry the sell
                    if position_status == "pending_stop_loss":
                        exit_action = "stop_loss"
                        exit_reason = f"RETRY: Stop-loss pending, retrying sell at ${current_price:.8f}"
                        logger.info(f"Retrying failed stop-loss sell for {symbol}")
                    elif position_status == "pending_take_profit":
                        exit_action = "take_profit"
                        exit_reason = f"RETRY: Take-profit pending, retrying sell at ${current_price:.8f}"
                        logger.info(f"Retrying failed take-profit sell for {symbol}")
                    # Otherwise check if exit conditions are met
                    elif current_price <= stop_loss:
                        if trailing_stop_active:
                            exit_action = "trailing_stop"
                            exit_reason = f"Trailing stop triggered at ${current_price:.8f} (trail SL: ${stop_loss:.8f}, peak: ${peak_price:.8f}, locked +{((stop_loss - entry_price) / entry_price * 100):.1f}%)"
                        else:
                            exit_action = "stop_loss"
                            exit_reason = f"Stop-loss triggered at ${current_price:.8f} (SL: ${stop_loss:.8f})"
                    elif current_price >= take_profit:
                        # === DCA EXIT STRATEGY ===
                        dca_enabled = settings.get("dca_exit_enabled", False)
                        dca_stage = position.get("dca_exit_stage", 0)  # 0=none, 1=TP1 done, 2=TP2 done
                        
                        if dca_enabled and dca_stage < 2:
                            dca_tp1_pct = settings.get("dca_tp1_percent", 15) / 100
                            dca_tp2_pct = settings.get("dca_tp2_percent", 30) / 100
                            tp1_price = entry_price * (1 + dca_tp1_pct)
                            tp2_price = entry_price * (1 + dca_tp2_pct)
                            
                            if dca_stage == 0 and current_price >= tp1_price:
                                exit_action = "dca_tp1"
                                exit_reason = f"DCA TP1 triggered: sell 50% at ${current_price:.8f} (+{current_pnl_pct:.1f}%)"
                            elif dca_stage == 1 and current_price >= tp2_price:
                                exit_action = "dca_tp2"
                                exit_reason = f"DCA TP2 triggered: sell 25% at ${current_price:.8f} (+{current_pnl_pct:.1f}%)"
                            else:
                                # Between TP1 and TP2, or not yet at TP1 — skip
                                pass
                        else:
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
                            
                            # RPC fallback list for reliability
                            RPC_ENDPOINTS = [
                                os.environ.get("HELIUS_RPC_URL"),
                                os.environ.get("ALCHEMY_RPC_URL"),
                                "https://api.mainnet-beta.solana.com"
                            ]
                            RPC_ENDPOINTS = [rpc for rpc in RPC_ENDPOINTS if rpc]  # Filter out None
                            
                            # Get custodial wallet address
                            custodial_wallet = await db.custodial_wallets.find_one({"user_wallet": wallet_address})
                            if not custodial_wallet:
                                raise Exception("Custodial wallet not found")
                            
                            custodial_address = custodial_wallet["custodial_address"]
                            
                            token_balance = 0
                            rpc_success = False
                            rpc_error = None
                            
                            # Try each RPC endpoint until one works
                            for rpc_url in RPC_ENDPOINTS:
                                try:
                                    async with AsyncClient(rpc_url) as rpc_client:
                                        from solana.rpc.types import TokenAccountOpts
                                        
                                        token_pubkey = Pubkey.from_string(token_mint)
                                        wallet_pubkey = Pubkey.from_string(custodial_address)
                                        
                                        # Try standard SPL Token program first
                                        TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
                                        TOKEN_2022_PROGRAM_ID = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
                                        
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
                                        
                                        rpc_success = True
                                        break  # Got a response, stop trying other RPCs
                                        
                                except Exception as rpc_e:
                                    rpc_error = str(rpc_e)
                                    logger.warning(f"RPC {rpc_url[:30]}... failed: {rpc_e}")
                                    continue
                            
                            if not rpc_success:
                                raise Exception(f"All RPC endpoints failed. Last error: {rpc_error}")
                            
                            if token_balance <= 0:
                                raise Exception(f"No {symbol} tokens in custodial wallet")
                            
                            logger.info(f"Found {token_balance} raw units of {symbol} to sell")
                            
                            # DCA partial sell: adjust sell amount for staged exits
                            sell_amount = token_balance
                            if exit_action == "dca_tp1":
                                sell_amount = int(token_balance * 0.50)  # Sell 50%
                                logger.info(f"DCA TP1: selling 50% = {sell_amount} of {token_balance}")
                            elif exit_action == "dca_tp2":
                                sell_amount = int(token_balance * 0.50)  # Sell 50% of remaining (= 25% of original)
                                logger.info(f"DCA TP2: selling 50% of remaining = {sell_amount}")
                            
                            if sell_amount <= 0:
                                raise Exception(f"Calculated sell amount is 0 for {symbol}")
                            
                            # Execute swap: TOKEN -> SOL
                            # Pass is_stop_loss=True for exit trades to use higher slippage
                            sell_result = await execute_auto_trade(
                                user_wallet=wallet_address,
                                input_mint=token_mint,
                                output_mint=SOL_MINT,
                                amount_lamports=sell_amount,  # This is token units, not lamports
                                is_stop_loss=(exit_action in ("stop_loss", "trailing_stop"))
                            )
                            
                            if sell_result.get("success"):
                                sell_success = True
                                tx_signature = sell_result.get("tx_signature")
                                logger.info(f"Auto-sell executed for {symbol}: {tx_signature}")
                            else:
                                sell_error = sell_result.get("error", "Unknown error")
                                
                        except Exception as e:
                            sell_error = f"{type(e).__name__}: {str(e)}"
                            logger.warning(f"Auto-sell failed for {symbol}: {sell_error}")
                            
                            # CRITICAL: Notify user of failed stop-loss immediately
                            if exit_action == "stop_loss":
                                logger.error(f"CRITICAL: Stop-loss sell FAILED for {symbol} at {current_pnl_pct:.1f}% loss!")
                                # Try to send Telegram alert about failed stop-loss
                                try:
                                    from routers.telegram import send_telegram_message
                                    account = await db.telegram_accounts.find_one({
                                        "wallet_address": wallet_address,
                                        "active": True
                                    })
                                    if account and account.get("chat_id"):
                                        await send_telegram_message(
                                            account["chat_id"],
                                            f"🚨 <b>STOP-LOSS FAILED</b>\n\n"
                                            f"<b>{symbol}</b> sell failed!\n"
                                            f"Current P/L: <code>{current_pnl_pct:.1f}%</code>\n"
                                            f"Error: {sell_error[:100]}\n\n"
                                            f"⚠️ Manual intervention may be required.\n"
                                            f"Will retry on next check (1 min)"
                                        )
                                except Exception as notify_e:
                                    logger.error(f"Failed to send stop-loss failure notification: {notify_e}")
                        
                        # Calculate final P&L
                        pnl_pct = current_pnl_pct
                        pnl_sol = position.get("amount_sol", 0) * (pnl_pct / 100)
                        
                        # Update position in database
                        # For DCA exits, keep position open and track stage
                        if exit_action in ("dca_tp1", "dca_tp2") and sell_success:
                            new_stage = 1 if exit_action == "dca_tp1" else 2
                            remaining_pct = 50 if new_stage == 1 else 25
                            await db.ai_trader_positions.update_one(
                                {"position_id": position.get("position_id")},
                                {"$set": {
                                    "status": "open",  # Keep open for remaining position
                                    "dca_exit_stage": new_stage,
                                    "dca_last_exit_price": current_price,
                                    "dca_last_exit_at": datetime.now(timezone.utc).isoformat(),
                                    "remaining_percent": remaining_pct,
                                    "peak_price": peak_price,
                                    "trailing_stop_active": trailing_stop_active,
                                }}
                            )
                            logger.info(f"DCA stage {new_stage} complete for {symbol}: {remaining_pct}% remaining")
                        else:
                            await db.ai_trader_positions.update_one(
                                {"position_id": position.get("position_id")},
                                {
                                    "$set": {
                                        "status": f"closed_{exit_action}" if sell_success else f"pending_{exit_action}",
                                        "exit_price": current_price,
                                        "pnl_percent": pnl_pct,
                                        "pnl_sol": pnl_sol,
                                        "peak_price": peak_price,
                                        "trailing_stop_active": trailing_stop_active,
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
                                pnl_sol=pnl_sol,
                                trigger_reason=exit_action  # "take_profit" or "stop_loss"
                            )
                            
                            # Record in internal ledger (credit — return funds + P&L)
                            try:
                                amount_sol = position.get("amount_sol", 0)
                                received = amount_sol + pnl_sol
                                # For DCA partial sells, only credit the partial amount
                                if exit_action in ("dca_tp1", "dca_tp2"):
                                    sell_frac = 0.50 if exit_action == "dca_tp1" else 0.25
                                    received = amount_sol * sell_frac * (1 + pnl_pct / 100)
                                await ledger_record(
                                    wallet_address, "trade_close", received,
                                    reference_id=position.get("position_id", ""),
                                    reference_type=f"auto_{exit_action}",
                                    description=f"Auto {exit_action} {symbol} — {received:.6f} SOL (PnL: {pnl_sol:+.6f})",
                                    metadata={"token_symbol": symbol, "pnl_sol": pnl_sol, "pnl_pct": pnl_pct, "exit_action": exit_action}
                                )
                            except Exception as le:
                                logger.warning(f"Ledger record failed for auto exit: {le}")
                            
                            # Apply rake on profit (2.5% of profit only)
                            actual_pnl = pnl_sol
                            # For DCA partial exits, scale the P&L to the sold fraction
                            if exit_action in ("dca_tp1", "dca_tp2"):
                                sell_frac = 0.50 if exit_action == "dca_tp1" else 0.25
                                actual_pnl = position.get("amount_sol", 0) * sell_frac * (pnl_pct / 100)
                            await apply_rake(wallet_address, actual_pnl, position.get("position_id", ""), symbol)
                        
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
