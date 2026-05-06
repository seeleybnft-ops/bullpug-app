"""Background scheduler for automatic prize pool payouts and signal tracking."""

import asyncio
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_and_execute_payout():
    """Check if payout is due and execute if so."""
    from utils.database import db
    from routers.prize_pool import execute_prize_payout, get_or_create_prize_pool
    
    try:
        pool = await get_or_create_prize_pool()
        next_payout = datetime.fromisoformat(pool["next_payout_at"].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if now >= next_payout:
            logger.info("Prize pool payout timer expired - executing automatic payout")
            result = await execute_prize_payout()
            logger.info(f"Automatic payout result: {result}")
        else:
            remaining = (next_payout - now).total_seconds()
            logger.debug(f"Prize pool payout in {remaining:.0f} seconds")
            
    except Exception as e:
        logger.error(f"Error in prize pool scheduler: {e}")


async def run_signal_tracking():
    """
    Periodic job to track signal outcomes.
    Runs every hour to capture 1h, 4h, and 24h price changes.
    """
    from utils.database import db
    
    try:
        # Check if tracking is enabled
        config = await db.auto_tracking_config.find_one(
            {"config_type": "signal_tracking"},
            {"_id": 0}
        )
        
        if not config or not config.get("enabled", True):
            logger.debug("Signal tracking is disabled")
            return
        
        now = datetime.now(timezone.utc)
        run_id = now.strftime("%Y%m%d_%H%M%S")
        
        results = {
            "run_id": run_id,
            "run_at": now.isoformat(),
            "signals_processed": 0,
            "outcomes_1h": 0,
            "outcomes_4h": 0,
            "outcomes_24h": 0,
            "errors": [],
            "source": "scheduler"
        }
        
        # Get signals from the last 25 hours
        from datetime import timedelta
        cutoff = (now - timedelta(hours=25)).isoformat()
        
        signals = await db.ai_trader_signals.find({
            "created_at": {"$gte": cutoff},
            "entry_price": {"$exists": True, "$ne": None}
        }, {"_id": 0}).to_list(500)
        
        results["signals_processed"] = len(signals)
        
        for signal in signals:
            try:
                signal_id = signal.get("signal_id")
                token_mint = signal.get("token_mint")
                entry_price = signal.get("entry_price", 0)
                signal_type = signal.get("signal_type", "buy")
                created_at = signal.get("created_at", "")
                
                if not signal_id or not entry_price:
                    continue
                
                try:
                    signal_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    continue
                
                hours_elapsed = (now - signal_time).total_seconds() / 3600
                
                # Get current price (simulated for now)
                current_price = await _get_simulated_price(entry_price)
                
                if not current_price or current_price <= 0:
                    continue
                
                # Calculate PnL
                if signal_type == "buy":
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl_percent = ((entry_price - current_price) / entry_price) * 100
                
                # Determine outcome
                if pnl_percent >= 2:
                    outcome = "win"
                elif pnl_percent <= -2:
                    outcome = "loss"
                else:
                    outcome = "neutral"
                
                # Update appropriate time bucket
                update_fields = {}
                
                if config.get("track_1h", True) and 1 <= hours_elapsed < 2:
                    update_fields = {
                        "price_after_1h": current_price,
                        "pnl_1h_percent": round(pnl_percent, 2),
                        "outcome_1h": outcome
                    }
                    results["outcomes_1h"] += 1
                elif config.get("track_4h", True) and 4 <= hours_elapsed < 5:
                    update_fields = {
                        "price_after_4h": current_price,
                        "pnl_4h_percent": round(pnl_percent, 2),
                        "outcome_4h": outcome
                    }
                    results["outcomes_4h"] += 1
                elif config.get("track_24h", True) and 24 <= hours_elapsed < 25:
                    update_fields = {
                        "price_after_24h": current_price,
                        "pnl_24h_percent": round(pnl_percent, 2),
                        "outcome_24h": outcome
                    }
                    results["outcomes_24h"] += 1
                
                if update_fields:
                    update_fields["last_tracked_at"] = now.isoformat()
                    
                    indicators = signal.get("technical_indicators", {})
                    
                    await db.signal_outcomes.update_one(
                        {"signal_id": signal_id},
                        {
                            "$set": update_fields,
                            "$setOnInsert": {
                                "signal_id": signal_id,
                                "token_symbol": signal.get("token_symbol"),
                                "token_mint": token_mint,
                                "signal_type": signal_type,
                                "strategy": signal.get("strategy"),
                                "entry_price": entry_price,
                                "confidence": signal.get("confidence", 0),
                                "rsi": indicators.get("rsi"),
                                "macd_histogram": indicators.get("macd", {}).get("histogram"),
                                "bollinger_position": indicators.get("bollinger", {}).get("position"),
                                "short_trend": indicators.get("short_trend"),
                                "long_trend": indicators.get("long_trend"),
                                "created_at": created_at
                            }
                        },
                        upsert=True
                    )
                    
            except Exception as e:
                results["errors"].append(f"{signal.get('signal_id', 'unknown')}: {str(e)}")
        
        # Store run record
        run_record = results.copy()
        await db.tracking_runs.insert_one(run_record)
        
        # Update config stats
        await db.auto_tracking_config.update_one(
            {"config_type": "signal_tracking"},
            {
                "$set": {"last_run": now.isoformat()},
                "$inc": {
                    "total_runs": 1,
                    "total_outcomes_tracked": results["outcomes_1h"] + results["outcomes_4h"] + results["outcomes_24h"]
                }
            }
        )
        
        total_tracked = results["outcomes_1h"] + results["outcomes_4h"] + results["outcomes_24h"]
        if total_tracked > 0:
            logger.info(f"Signal tracking completed: {total_tracked} outcomes from {len(signals)} signals")
        else:
            logger.debug(f"Signal tracking: no outcomes to update from {len(signals)} signals")
            
    except Exception as e:
        logger.error(f"Error in signal tracking scheduler: {e}")


async def _get_simulated_price(entry_price: float) -> float:
    """Get simulated price for tracking (realistic random walk)."""
    import random
    
    # Simulate realistic price movement
    volatility = 0.05  # 5% volatility
    drift = -0.002  # Slight negative drift (realistic for memecoins)
    random_factor = random.gauss(0, volatility) + drift
    simulated_price = entry_price * (1 + random_factor)
    
    return max(simulated_price, entry_price * 0.5)  # Floor at 50% of entry


async def auto_complete_pending_journal_entries():
    """
    Auto-complete pending journal entries older than 24 hours.
    Runs every hour to check for expired pending entries.
    """
    from utils.database import db
    from datetime import timedelta
    
    try:
        now = datetime.now(timezone.utc)
        cutoff_time = (now - timedelta(hours=24)).isoformat()
        
        # Find expired pending entries
        expired = await db.trading_journal.find(
            {
                "pending": True,
                "auto_logged_at": {"$lt": cutoff_time}
            }
        ).to_list(100)
        
        updated_count = 0
        for entry in expired:
            try:
                await db.trading_journal.update_one(
                    {"trade_id": entry["trade_id"]},
                    {
                        "$set": {
                            "pending": False,
                            "completed_at": now.isoformat(),
                            "auto_completed": True,
                            "tags": (entry.get("tags") or []) + ["incomplete"],
                            "updated_at": now.isoformat()
                        }
                    }
                )
                updated_count += 1
            except Exception as e:
                logger.error(f"Error auto-completing entry {entry.get('trade_id')}: {e}")
        
        if updated_count > 0:
            logger.info(f"Journal auto-complete: marked {updated_count} pending entries as incomplete")
        else:
            logger.debug("Journal auto-complete: no expired pending entries found")
            
    except Exception as e:
        logger.error(f"Error in journal auto-complete scheduler: {e}")


async def scan_runner_alerts():
    """
    Scan for new runner tokens and send alerts to subscribed users.
    Runs every 5 minutes.
    """
    try:
        from services.runner_alerts import RunnerAlertService
        
        result = await RunnerAlertService.scan_and_alert()
        
        if result.get("alerts_sent", 0) > 0:
            logger.info(f"Runner alerts: sent {result['alerts_sent']} alerts to users")
        else:
            logger.debug(f"Runner alerts scan: {result.get('runners_found', 0)} runners, no alerts sent")
            
    except Exception as e:
        logger.error(f"Error in runner alerts scheduler: {e}")


async def auto_trade_scan_cycle():
    """
    Periodic scan: find all wallets with auto-trading enabled and run
    auto_trade_scan_and_execute for each one.
    """
    try:
        from utils.database import db

        enabled_settings = await db.ai_trader_settings.find({
            "auto_trade_enabled": True
        }).to_list(100)

        if not enabled_settings:
            logger.debug("Auto-trade scan: No wallets with auto-trading enabled")
            return

        for settings in enabled_settings:
            wallet_address = settings.get("wallet_address")
            if not wallet_address:
                continue
            try:
                from routers.ai_trader import auto_trade_scan_and_execute
                result = await auto_trade_scan_and_execute(wallet_address)
                trades = result.get("trades", [])
                if trades:
                    logger.info(f"Auto-trade scan for {wallet_address[:8]}…: {len(trades)} trades executed")
                else:
                    msg = result.get("message", "no opportunities")
                    logger.debug(f"Auto-trade scan for {wallet_address[:8]}…: {msg}")
            except Exception as e:
                logger.error(f"Auto-trade scan error for {wallet_address[:8]}…: {e}")

    except Exception as e:
        logger.error(f"Error in auto-trade scan cycle: {e}")


async def check_auto_trade_exits():
    """
    CRITICAL: Check all open positions for take-profit and stop-loss triggers.
    This runs every minute to ensure timely exit execution.
    """
    try:
        from utils.database import db
        import httpx
        
        # Find all wallets with auto-trading enabled
        enabled_settings = await db.ai_trader_settings.find({
            "auto_trade_enabled": True
        }).to_list(100)
        
        if not enabled_settings:
            logger.debug("Auto-trade exit check: No wallets with auto-trading enabled")
            return
        
        total_exits = 0
        total_positions = 0
        
        for settings in enabled_settings:
            wallet_address = settings.get("wallet_address")
            if not wallet_address:
                continue
                
            try:
                # Import the check_exits function from ai_trader router
                from routers.ai_trader import auto_trade_check_exits
                
                result = await auto_trade_check_exits(wallet_address)
                
                exits_count = len(result.get("exits", []))
                positions_count = result.get("positions_checked", 0)
                
                total_exits += exits_count
                total_positions += positions_count
                
                if exits_count > 0:
                    logger.info(f"Auto-trade exits for {wallet_address[:8]}...: {exits_count} positions closed")
                    
            except Exception as e:
                logger.error(f"Error checking exits for {wallet_address[:8]}...: {e}")
        
        if total_exits > 0:
            logger.info(f"Auto-trade exit check complete: {total_exits} exits across {total_positions} positions")
        else:
            logger.debug(f"Auto-trade exit check: {total_positions} positions checked, no exits triggered")
            
    except Exception as e:
        logger.error(f"Error in auto-trade exit scheduler: {e}")


async def collect_real_prices():
    """Collect real OHLCV price data for tracked tokens."""
    try:
        from services.price_collector import collect_price_snapshot, cleanup_old_candles
        await collect_price_snapshot()
        # Cleanup old data every run (cheap operation)
        await cleanup_old_candles(max_age_hours=48)
    except Exception as e:
        logger.error(f"Error in price collector: {e}")


async def scan_smart_money():
    """Scan smart money activity using DexScreener flow + Helius whale discovery."""
    try:
        from services.smart_money_tracker import scan_smart_money as run_scan, cleanup_expired_signals
        await run_scan()
        await cleanup_expired_signals()
    except Exception as e:
        logger.error(f"Error in smart money scanner: {e}")


async def send_daily_trading_digest():
    """Send the daily P&L digest to all linked Telegram users. Runs once at 20:00 UTC."""
    try:
        from routers.telegram import run_daily_digest_all
        result = await run_daily_digest_all()
        sent = result.get("sent", 0)
        if sent > 0:
            logger.info(f"Daily trading digest sent to {sent} users")
        else:
            logger.debug("Daily trading digest: no messages sent")
    except Exception as e:
        logger.error(f"Error in daily trading digest: {e}")


async def auto_draw_pot_check():
    """Auto-draw the P2P pot when its 60s countdown expires."""
    try:
        from state.pot_state import get_pot
        from routers.pot import draw_pot_winner
        from fastapi import Request
        from utils.config import DISTRIBUTION_WALLET

        pot = get_pot()
        if pot["status"] != "open" or not pot.get("draw_at") or len(pot["entries"]) < 2:
            return
        draw_time = datetime.fromisoformat(pot["draw_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < draw_time:
            return

        logger.info("Pot countdown expired — auto-drawing winner")

        # Build a minimal Request-like stub that carries the admin header so
        # the authorization gate in draw_pot_winner lets us through.
        class _Stub:
            headers = {"X-Admin-Wallet": DISTRIBUTION_WALLET}
        await draw_pot_winner(_Stub())
    except Exception as e:
        logger.error(f"Error in auto_draw_pot_check: {e}")


def start_scheduler():
    """Start the background scheduler."""
    # Check every 5 minutes if payout is due
    scheduler.add_job(
        check_and_execute_payout,
        trigger=IntervalTrigger(minutes=5),
        id="prize_pool_check",
        replace_existing=True,
        max_instances=1
    )
    
    # Signal tracking - run every hour
    scheduler.add_job(
        run_signal_tracking,
        trigger=IntervalTrigger(hours=1),
        id="signal_tracking",
        replace_existing=True,
        max_instances=1
    )
    
    # Journal pending entries auto-complete - run every hour
    scheduler.add_job(
        auto_complete_pending_journal_entries,
        trigger=IntervalTrigger(hours=1),
        id="journal_auto_complete",
        replace_existing=True,
        max_instances=1
    )
    
    # Runner alerts - scan every 5 minutes
    scheduler.add_job(
        scan_runner_alerts,
        trigger=IntervalTrigger(minutes=5),
        id="runner_alerts_scan",
        replace_existing=True,
        max_instances=1
    )
    
    # === TRADING BOT HIBERNATED ===
    # Auto-trade exit monitoring — DISABLED (bot hibernated)
    # scheduler.add_job(
    #     check_auto_trade_exits,
    #     trigger=IntervalTrigger(minutes=1),
    #     id="auto_trade_exit_check",
    #     replace_existing=True,
    #     max_instances=1
    # )
    
    # Auto-trade scan & execute — DISABLED (bot hibernated)
    # scheduler.add_job(
    #     auto_trade_scan_cycle,
    #     trigger=IntervalTrigger(minutes=5),
    #     id="auto_trade_scan",
    #     replace_existing=True,
    #     max_instances=1
    # )
    
    # CRITICAL: Real OHLCV price data collection - every 1 minute
    scheduler.add_job(
        collect_real_prices,
        trigger=IntervalTrigger(minutes=1),
        id="price_collector",
        replace_existing=True,
        max_instances=1
    )
    
    # NEW: Smart money wallet tracking - every 10 minutes
    scheduler.add_job(
        scan_smart_money,
        trigger=IntervalTrigger(minutes=10),
        id="smart_money_scanner",
        replace_existing=True,
        max_instances=1
    )
    
    # NEW: Daily trading digest via Telegram - 20:00 UTC daily
    scheduler.add_job(
        send_daily_trading_digest,
        trigger=CronTrigger(hour=20, minute=0, timezone="UTC"),
        id="daily_trading_digest",
        replace_existing=True,
        max_instances=1
    )

    # P2P pot auto-draw — check every 5 seconds for expired countdown
    scheduler.add_job(
        auto_draw_pot_check,
        trigger=IntervalTrigger(seconds=5),
        id="pot_auto_draw",
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.start()
    logger.info(
        "Background scheduler started - prize pool (5 min), signal tracking (1 hour), "
        "journal auto-complete (1 hour), runner alerts (5 min), "
        "PRICE COLLECTOR (1 min), SMART MONEY v2 (10 min), "
        "DAILY DIGEST (20:00 UTC), POT AUTO-DRAW (5 sec). "
        "[HIBERNATED: auto-trade exit check, auto-trade scan]"
    )


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
