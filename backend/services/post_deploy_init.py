"""
Post-deploy database initialization.

Runs once on first startup to ensure the correct custodial wallet (CFzZRc76y...)
is present. If the old lost wallet (B2ykf4...) is found, it replaces all stale
data with the correct seed data.

This is idempotent — if the correct wallet already exists, it skips entirely.
"""

import json
import logging
from pathlib import Path
from utils.database import db

logger = logging.getLogger(__name__)

SEED_FILE = Path(__file__).parent.parent / "seed_data.json"
CORRECT_WALLET = "CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg"
OLD_LOST_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"

SEEDED_COLLECTIONS = [
    "custodial_wallets",
    "user_ledger",
    "ai_trader_positions",
    "ai_trader_settings",
    "trader_settings",
    "telegram_accounts",
    "auto_trade_logs",
    "trading_journal",
]


async def run_post_deploy_init():
    """
    Idempotent initializer.
    - If correct wallet exists → skip (nothing to do).
    - If old lost wallet exists → replace with seed data.
    - If no wallet exists → seed fresh.
    """
    correct = await db.custodial_wallets.find_one(
        {"custodial_address": CORRECT_WALLET}, {"_id": 1}
    )
    if correct:
        logger.info("Post-deploy init: correct wallet found — skipping.")
        return

    old = await db.custodial_wallets.find_one(
        {"custodial_address": OLD_LOST_WALLET}, {"_id": 1}
    )
    if old:
        logger.info("Post-deploy init: old lost wallet detected — replacing with correct data...")
    else:
        logger.info("Post-deploy init: fresh database — seeding...")

    if not SEED_FILE.exists():
        logger.warning("Post-deploy init: seed_data.json not found — cannot seed.")
        return

    try:
        with open(SEED_FILE) as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Post-deploy init: failed to read seed file: {e}")
        return

    total = 0
    for col_name in SEEDED_COLLECTIONS:
        docs = data.get(col_name, [])
        if not docs:
            continue
        collection = db[col_name]
        try:
            await collection.delete_many({})
            await collection.insert_many(docs)
            total += len(docs)
            logger.info(f"  {col_name}: seeded {len(docs)} docs")
        except Exception as e:
            logger.error(f"  {col_name}: seed failed: {e}")

    logger.info(f"Post-deploy init COMPLETE: seeded {total} documents. Wallet: {CORRECT_WALLET}")
