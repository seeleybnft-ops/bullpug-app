"""Background scheduler for automatic prize pool payouts."""

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
    
    scheduler.start()
    logger.info("Prize pool scheduler started - checking every 5 minutes")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Prize pool scheduler stopped")
