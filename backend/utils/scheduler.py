"""Background scheduler for automatic prize pool payouts and signal tracking."""

import asyncio
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

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
    
    scheduler.start()
    logger.info("Background scheduler started - prize pool (5 min), signal tracking (1 hour), journal auto-complete (1 hour), runner alerts (5 min)")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
