"""Background scheduler for automatic prize pool payouts and arena ops."""

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

    # Escrow health check + Telegram alert to operator when free capital is low
    async def _run_escrow_alert():
        try:
            from services.escrow_alerts import check_escrow_and_alert
            result = await check_escrow_and_alert()
            if result.get("status") not in ("ok", "skipped", "throttled"):
                logger.info("Escrow alert task: %s", result)
        except Exception:
            logger.exception("Escrow alert task crashed")

    scheduler.add_job(
        _run_escrow_alert,
        trigger=IntervalTrigger(minutes=10),
        id="escrow_health_alert",
        replace_existing=True,
        max_instances=1,
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

    # Archive test-wallet cleanup — runs once a day at 03:15 UTC (off-peak,
    # after the daily-digest window). Removes any rows matching the
    # TEST_WALLET_REGEX so QA smoke-testing never accumulates in prod.
    async def _run_archive_test_cleanup():
        try:
            from services.archive_test_cleanup import purge_test_wallet_data
            result = await purge_test_wallet_data()
            total = sum(result.values())
            if total > 0:
                logger.info(
                    "Archive test-wallet cleanup: purged %s rows — %s",
                    total, result,
                )
            else:
                logger.debug("Archive test-wallet cleanup: 0 rows to purge")
        except Exception:
            logger.exception("Archive test-wallet cleanup crashed")

    scheduler.add_job(
        _run_archive_test_cleanup,
        trigger=CronTrigger(hour=3, minute=15, timezone="UTC"),
        id="archive_test_cleanup",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info(
        "Background scheduler started - prize pool (5 min), "
        "journal auto-complete (1 hour), runner alerts (5 min), "
        "PRICE COLLECTOR (1 min), SMART MONEY v2 (10 min), "
        "DAILY DIGEST (20:00 UTC), POT AUTO-DRAW (5 sec), "
        "ESCROW ALERT (10 min), ARCHIVE TEST CLEANUP (03:15 UTC daily)."
    )


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
