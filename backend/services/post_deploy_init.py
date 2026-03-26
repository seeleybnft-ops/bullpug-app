"""
Post-deploy database initialization.

Runs once on first startup with a fresh database to restore the critical
wallet, ledger, positions, settings, and Telegram linkages from the
preview environment.

This is idempotent — if the custodial_wallets collection already has entries,
it skips entirely to avoid overwriting a live database.
"""

import json
import logging
from pathlib import Path
from utils.database import db

logger = logging.getLogger(__name__)

SEED_FILE = Path(__file__).parent.parent / "seed_data.json"


async def run_post_deploy_init():
    """
    Idempotent initializer. Only runs if the database has no custodial wallet
    (fresh deploy). Seeds all critical data from seed_data.json.
    """
    # Guard: skip if custodial wallets already exist (not a fresh deploy)
    existing_wallets = await db.custodial_wallets.count_documents({})
    if existing_wallets > 0:
        logger.info(f"Post-deploy init: {existing_wallets} custodial wallet(s) found — skipping seed.")
        return

    if not SEED_FILE.exists():
        logger.warning("Post-deploy init: seed_data.json not found — skipping.")
        return

    logger.info("Post-deploy init: fresh database detected — seeding critical data...")

    try:
        with open(SEED_FILE) as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Post-deploy init: failed to read seed_data.json: {e}")
        return

    collections = [
        "custodial_wallets",
        "user_ledger",
        "ai_trader_positions",
        "ai_trader_settings",
        "trader_settings",
        "telegram_accounts",
        "auto_trade_logs",
        "trading_journal",
    ]

    total_seeded = 0
    for col_name in collections:
        docs = data.get(col_name, [])
        if not docs:
            continue

        collection = db[col_name]
        existing = await collection.count_documents({})
        if existing > 0:
            logger.info(f"  {col_name}: already has {existing} docs — skipping.")
            continue

        try:
            await collection.insert_many(docs)
            total_seeded += len(docs)
            logger.info(f"  {col_name}: seeded {len(docs)} docs")
        except Exception as e:
            logger.error(f"  {col_name}: seed failed: {e}")

    logger.info(f"Post-deploy init COMPLETE: seeded {total_seeded} documents across {len(collections)} collections.")
