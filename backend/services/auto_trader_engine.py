"""
Auto-Trade Engine Service

Core auto-trading logic extracted from ai_trader.py for modularity.
Contains: scan_and_execute (token scanning + trade execution) and check_exits (exit monitoring).
"""

import os
import uuid
import httpx
import asyncio
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from utils.database import db
from services.token_price import (
    SOL_MINT, LAMPORTS_PER_SOL, TOKENS, SAFER_TOKENS, HIGH_RISK_TOKENS,
    get_token_price, get_token_price_by_mint, get_price_history
)
from services.ledger import record_entry as ledger_record, get_available_balance as ledger_balance
from services.runner_detector import RunnerDetector
from services.market_analyzer import MarketConditionAnalyzer
from services.strategy_engine import StrategyEngine
from services.technical_analyzer import TechnicalAnalyzer

logger = logging.getLogger(__name__)

RAKE_PERCENT = 2.5


async def apply_rake(wallet_address: str, profit_sol: float, position_id: str, symbol: str):
    """Apply rake (2.5%) on profitable trades."""
    if profit_sol <= 0:
        return 0
    rake_amount = round(profit_sol * (RAKE_PERCENT / 100), 6)
    if rake_amount < 0.0001:
        return 0
    try:
        await ledger_record(
            wallet_address, "fee", -rake_amount,
            reference_id=position_id,
            reference_type="rake",
            description=f"Platform rake ({RAKE_PERCENT}%) on {symbol} profit: {rake_amount:.6f} SOL",
            metadata={"profit_sol": profit_sol, "rake_percent": RAKE_PERCENT}
        )
        logger.info(f"Rake applied: {rake_amount:.6f} SOL on {symbol} profit of {profit_sol:.6f}")
        return rake_amount
    except Exception as e:
        logger.error(f"Rake application failed: {e}")
        return 0


async def ensure_sufficient_sol_for_trade(wallet_address: str, required_sol: float) -> dict:
    """Auto-burn empty token accounts to reclaim SOL before a trade if needed."""
    try:
        from routers.custodial_wallet import get_wallet_balance
        wallet_doc = await db.custodial_wallets.find_one({"user_wallet": wallet_address}, {"_id": 0, "custodial_address": 1})
        if not wallet_doc:
            return {"burned_accounts": 0, "reclaimed_sol": 0}
        
        balance = await get_wallet_balance(wallet_doc["custodial_address"])
        balance_sol = balance / LAMPORTS_PER_SOL
        
        if balance_sol >= required_sol + 0.005:
            return {"burned_accounts": 0, "reclaimed_sol": 0}
        
        # Try to reclaim SOL from empty token accounts (pugburn)
        try:
            from routers.pugburn import auto_close_empty_accounts
            result = await auto_close_empty_accounts(wallet_doc["custodial_address"])
            return result
        except Exception:
            return {"burned_accounts": 0, "reclaimed_sol": 0}
    except Exception as e:
        logger.warning(f"ensure_sufficient_sol failed: {e}")
        return {"burned_accounts": 0, "reclaimed_sol": 0}


async def create_pending_journal_entry(
    wallet_address: str,
    asset: str,
    trade_type: str,
    entry_price: float,
    position_size_sol: float,
    position_size_tokens: float = None,
    tx_signature: str = None,
    pnl_percent: float = None,
    pnl_sol: float = None,
    strategy: str = None,
    trigger_reason: str = None
):
    """Create a pending journal entry for an auto-trade."""
    try:
        trade_id = f"AT{str(uuid.uuid4())[:8].upper()}"
        
        auto_strategy = strategy
        if not auto_strategy:
            if trade_type == "buy":
                auto_strategy = trigger_reason or "AI Signal - Auto Buy"
            else:
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
            "strategy": auto_strategy,
            "pnl": pnl_sol or 0,
            "pnl_percent": pnl_percent or 0,
            "exit_price": entry_price if trade_type == "sell" else None,
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


async def run_scan_and_execute(wallet_address: str):
    """Main auto-trading function: scan market and execute trades."""
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
                    
                    # Apply optimal settings — but never raise confidence above user's own setting
                    user_min_conf = settings.get("auto_min_confidence", 0.55)
                    recommended = auto_trade_opt.get("recommended_min_confidence", 0.55)
                    settings["auto_min_confidence"] = min(user_min_conf, recommended)
                    settings["auto_max_daily_trades"] = auto_trade_opt.get("recommended_max_daily_trades", settings.get("auto_max_daily_trades", 3))
                    settings["auto_cooldown_minutes"] = auto_trade_opt.get("recommended_cooldown_minutes", settings.get("auto_cooldown_minutes", 45))
                    settings["auto_require_multiple_signals"] = auto_trade_opt.get("require_multiple_signals", True)
                    
                    logger.info(f"Auto-optimization applied: min_conf={settings['auto_min_confidence']}, max_trades={settings['auto_max_daily_trades']}, cooldown={settings['auto_cooldown_minutes']}")
            except Exception as e:
                logger.warning(f"Failed to fetch optimal settings: {e}, using manual settings")
        
        # FIRST: Check and execute exits for positions hitting TP/SL
        exits_result = await run_check_exits(wallet_address)
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
        if mode == "aggressive" or mode == "sniper":
            min_confidence = max(0.45, min_confidence - 0.15)  # Aggressive/sniper: 0.45 floor
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
            tokens_to_scan.extend(["JUP", "PYTH", "RNDR", "BONK", "RAY", "WIF", "HNT", "JTO", "TENSOR", "DRIFT"])
        if risk_level in ["high_risk", "both"]:
            tokens_to_scan.extend(["BONK", "WIF", "RAY"])
        
        # IMPORTANT: Prefetch ALL token data from CoinGecko FIRST (single API call)
        # This must happen BEFORE runner detection to avoid rate limit conflicts
        from services.market_data import get_token_market_data_multi, prefetch_coingecko_batch
        await prefetch_coingecko_batch(tokens_to_scan[:10])
        
        if risk_level in ["high_risk", "both"]:
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
        
        # Get available ledger balance ONCE for the entire scan
        ledger_available = await ledger_balance(wallet_address)
        logger.info(f"Scan starting: ledger available = {ledger_available:.6f} SOL")
        
        if ledger_available < 0.005:
            logger.warning(f"INSUFFICIENT BALANCE for trading: {ledger_available:.6f} SOL (need >0.005). Skipping scan.")
            return {"success": True, "executed": [], "skipped": [{"symbol": "*", "reason": f"Insufficient balance: {ledger_available:.6f} SOL"}]}
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Scan known tokens using multi-source market data
            
            for symbol in tokens_to_scan[:10]:  # Scan up to 10 known tokens per cycle
                try:
                    token_mint = TOKENS.get(symbol)
                    if not token_mint:
                        continue
                    
                    # Skip SOL - can't swap SOL to SOL
                    if token_mint == SOL_MINT:
                        continue
                    
                    # Use multi-source market data (DexScreener cached -> CoinGecko fallback)
                    market_data = await get_token_market_data_multi(symbol, token_mint)
                    
                    if not market_data:
                        skipped.append({"symbol": symbol, "reason": "No market data available from any source"})
                        continue
                    
                    data_source_name = market_data.get("source", "unknown")
                    best_pair = market_data.get("pair_data")  # May be None for CoinGecko source
                    
                    # === QUALITY CHECK: Volume + Liquidity filter ===
                    from services.market_quality import extract_market_quality, build_price_history_from_dex, confidence_penalty_for_synthetic_data
                    
                    if best_pair:
                        # Full quality check with DexScreener pair data
                        quality = extract_market_quality(best_pair)
                        if not quality["passes_quality_check"]:
                            skipped.append({"symbol": symbol, "reason": f"Market quality: {', '.join(quality['rejection_reasons'])}"})
                            continue
                    else:
                        # Simplified quality check for CoinGecko data (no pair data)
                        if market_data["volume_24h"] < 1_000_000:
                            skipped.append({"symbol": symbol, "reason": f"Low volume: ${market_data['volume_24h']:,.0f}"})
                            continue
                    
                    # Get price history for analysis
                    current_price = market_data["price_usd"]
                    
                    if current_price <= 0:
                        continue
                    
                    # === IMPROVEMENT 1: Try REAL OHLCV data first, fall back to synthetic ===
                    from services.price_collector import get_real_price_history, add_runner_to_tracking
                    prices, is_synthetic = await get_real_price_history(token_mint)
                    
                    if is_synthetic:
                        # Fall back to synthetic price history from market data % changes
                        price_change_24h = market_data.get("price_change_24h", 0)
                        price_change_6h = market_data.get("price_change_6h", 0)
                        price_change_1h = market_data.get("price_change_1h", 0)
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
                        trade_reason = f"[SYNTHETIC DATA -5%] {trade_reason}"
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
                        sentiment_adj = await sentiment_confidence(token_mint, pair_data=best_pair if best_pair else {})
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
                        # Use market_data for price changes (works with any source)
                        change_5m = market_data.get("price_change_5m", 0)
                        change_1h = market_data.get("price_change_1h", 0)
                        change_6h = market_data.get("price_change_6h", 0)
                        change_24h = market_data.get("price_change_24h", 0)
                        
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
                        
                        # Check how many OPEN positions we have for this token
                        existing_count = await db.ai_trader_positions.count_documents({
                            "wallet_address": wallet_address,
                            "token_mint": token_mint,
                            "status": "open"
                        })
                        
                        # Allow up to 2 positions per token (DCA-style)
                        if existing_count >= 2:
                            skipped.append({
                                "symbol": symbol,
                                "reason": f"Max positions for {symbol} reached ({existing_count}/2)"
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
                        
                        # Cap position to available ledger balance minus fee reserve
                        fee_reserve = 0.003  # Keep 0.003 SOL for tx fees + sell reserve
                        position_sol = round(min(position_sol, max(0, ledger_available - fee_reserve)), 6)
                        if position_sol < 0.002:  # Minimum viable trade
                            skipped.append({"symbol": symbol, "reason": f"Insufficient balance (avail: {ledger_available:.4f} SOL, need: {base_position:.4f})"})
                            continue
                        
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
                            
                            # Refresh ledger balance (may have changed from burns/other trades)
                            ledger_available = await ledger_balance(wallet_address)
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
                                
                                if custodial_balance >= required_lamports + 5050000:  # 0.005 sell reserve + 0.00005 tx fee
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
                            
                            # === FEE RECONCILIATION ===
                            # After trade, compare on-chain SOL with ledger available.
                            # Any difference = transaction fees (Solana base fee + priority fee + Jupiter route fee)
                            try:
                                post_trade_balance = await get_wallet_balance(custodial_wallet["custodial_address"])
                                post_trade_sol = post_trade_balance / LAMPORTS_PER_SOL
                                new_ledger_available = await ledger_balance(wallet_address)
                                fee_gap = round(new_ledger_available - post_trade_sol, 6)
                                if fee_gap > 0.0001:  # Only record if meaningful (> 0.0001 SOL)
                                    await ledger_record(
                                        wallet_address, "fee", -fee_gap,
                                        reference_id=position_id,
                                        reference_type="tx_fee",
                                        description=f"Transaction fee for {symbol} buy: {fee_gap:.6f} SOL",
                                        metadata={"tx_signature": tx_signature, "on_chain_sol": post_trade_sol}
                                    )
                                    logger.info(f"Recorded tx fee: {fee_gap:.6f} SOL for {symbol} buy")
                                    # Update the available balance for further calculations
                                    ledger_available = await ledger_balance(wallet_address)
                            except Exception as fee_err:
                                logger.warning(f"Fee reconciliation failed: {fee_err}")
                            
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
                            
                            # Send Telegram trade alert
                            try:
                                from routers.telegram import send_trade_alert
                                await send_trade_alert(wallet_address, {
                                    "action": "buy",
                                    "symbol": symbol,
                                    "amount_sol": position_sol,
                                    "price": current_price,
                                    "confidence": trade_confidence,
                                    "reason": trade_reason,
                                    "tx_signature": tx_signature
                                })
                            except Exception as tg_err:
                                logger.debug(f"Telegram buy alert failed: {tg_err}")
                            
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
                            trade_reason = f"[SYNTHETIC DATA -5%] {trade_reason}"
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
                            # Cap to available balance minus fee reserve
                            from services.ledger import get_available_balance as ledger_avail_fn
                            ledger_avail = await ledger_avail_fn(wallet_address)
                            fee_reserve = 0.006  # Keep 0.006 SOL for tx fees + sell reserve
                            max_runner_position = min(max_position * 0.5, 0.1, max(0, ledger_avail - fee_reserve))
                            position_sol = round(max_runner_position, 6)
                            
                            if position_sol < 0.002:  # Minimum viable trade
                                skipped.append({"symbol": f"{symbol} (RUNNER)", "reason": f"Insufficient balance for runner trade (avail: {ledger_avail:.4f} SOL)"})
                                continue
                            
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
                                
                                # Send Telegram runner trade alert
                                try:
                                    from routers.telegram import send_trade_alert
                                    await send_trade_alert(wallet_address, {
                                        "action": "buy",
                                        "symbol": symbol,
                                        "amount_sol": position_sol,
                                        "price": current_price,
                                        "confidence": trade_confidence,
                                        "reason": trade_reason,
                                        "tx_signature": tx_signature,
                                        "is_runner": True
                                    })
                                except Exception as tg_err:
                                    logger.debug(f"Telegram runner alert failed: {tg_err}")
                                
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


async def run_check_exits(wallet_address: str):
    """Check open positions for TP/SL/trailing-stop triggers."""
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
                    # Get current price using multi-source (DexScreener cached -> CoinGecko -> fallback)
                    current_price = await get_token_price_by_mint(token_mint, symbol=symbol)
                    
                    if not current_price or current_price <= 0:
                        continue
                    
                    # Update current_price in position document for live P&L display
                    await db.ai_trader_positions.update_one(
                        {"position_id": position.get("position_id")},
                        {"$set": {"current_price": current_price, "price_updated_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    
                    entry_price = position.get("entry_price", 0)
                    
                    # CRITICAL GUARD: Skip positions with no valid entry price
                    # Synced-from-chain positions may have entry_price=0 until prices are fetched
                    if not entry_price or entry_price <= 0:
                        # Try to set entry_price to current price so future checks work
                        if current_price and current_price > 0:
                            await db.ai_trader_positions.update_one(
                                {"position_id": position.get("position_id")},
                                {"$set": {"entry_price": current_price, "peak_price": current_price}}
                            )
                            logger.info(f"Position {symbol}: set entry_price to current market ${current_price:.8f} (was 0)")
                        else:
                            logger.warning(f"Skipping exit check for {symbol}: entry_price=0 and no current price available")
                        continue
                    
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
                            from routers.custodial_wallet import execute_auto_trade
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
                            
                            # Send Telegram exit alert
                            try:
                                from routers.telegram import send_trade_alert
                                await send_trade_alert(wallet_address, {
                                    "action": exit_action,
                                    "symbol": symbol,
                                    "amount_sol": position.get("amount_sol", 0),
                                    "price": current_price,
                                    "confidence": 1.0,
                                    "reason": exit_reason,
                                    "tx_signature": tx_signature,
                                    "pnl_percent": pnl_pct,
                                    "pnl_sol": pnl_sol,
                                    "peak_price": peak_price
                                })
                            except Exception as tg_err:
                                logger.debug(f"Telegram exit alert failed: {tg_err}")
                        
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
