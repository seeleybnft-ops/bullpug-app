"""
Post-deploy database initialization.

Ensures the correct custodial wallet (CFzZRc76y...) is present in the
production database. Replaces the old lost wallet (B2ykf4...) if found.

The critical wallet data is embedded directly in code to avoid any
file-not-found issues during deployment.
"""

import json
import logging
from pathlib import Path
from utils.database import db

logger = logging.getLogger(__name__)

CORRECT_WALLET = "CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg"
OLD_LOST_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"
USER_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"

# The correct custodial wallet — embedded directly so it never gets lost
CORRECT_WALLET_DOC = {
    "user_wallet": USER_WALLET,
    "custodial_address": CORRECT_WALLET,
    "encrypted_private_key": "Z0FBQUFBQnB4WjRETXlJN0F1U3A2N2UwNWVKRmNTSktEUk5EeGJETF9uMTNESW9KbXYwUWduYVJMUEN1Y2hkXzBxVGh4OUh3bXVkaHZKVWVfWmEyYTE5dml4SF9XSWNaXzdCMlR4TnJselp2dklqTUk2dlYxcXR6S21SRW45dl9XaUZFOVFZTXR6cVBBSk40QWFrNWRQeFlkSTZ0MzhIRnB5eHJiNG9Da3FuMzhqcEg3WmxySmlVPQ==",
    "balance_lamports": 3955720,
    "created_at": "2026-03-26T20:58:43.758196+00:00",
    "last_activity": "2026-03-26T21:43:38.915771+00:00",
    "total_deposits_lamports": 50000000,
    "total_withdrawals_lamports": 0,
    "transaction_history": [
        {
            "tx_type": "deposit",
            "amount_lamports": 50000000,
            "amount_sol": 0.05,
            "tx_signature": "auto_detected",
            "status": "confirmed",
            "created_at": "2026-03-26T21:32:17.027617+00:00"
        }
    ]
}

SEED_FILE = Path(__file__).parent.parent / "seed_data.json"

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


def _load_seed_data():
    """Load seed data from file, falling back to wallet-only if file missing."""
    if SEED_FILE.exists():
        try:
            with open(SEED_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read seed file: {e}")

    # Fallback: at minimum seed the wallet
    return {"custodial_wallets": [CORRECT_WALLET_DOC]}


async def run_post_deploy_init():
    """
    Idempotent initializer. Runs on every startup.
    - If correct wallet (CFzZRc76y) exists → skip.
    - If old lost wallet (B2ykf4) or no wallet → replace/seed.
    """
    correct = await db.custodial_wallets.find_one(
        {"custodial_address": CORRECT_WALLET}, {"_id": 1}
    )
    if correct:
        logger.info("Post-deploy init: correct wallet CFzZRc76y found — skipping.")
        return

    logger.info("Post-deploy init: correct wallet NOT found — seeding now...")
    await _do_seed()


async def force_seed():
    """
    Force re-seed. Called from the manual admin endpoint.
    Always runs regardless of current DB state.
    """
    logger.info("Force seed triggered — replacing all seeded collections...")
    await _do_seed()
    return {"success": True, "wallet": CORRECT_WALLET}


async def _do_seed():
    """Core seeding logic. Clears and re-inserts all critical collections."""
    data = _load_seed_data()

    # Step 1: ALWAYS ensure correct wallet (even if seed file is partial)
    try:
        await db.custodial_wallets.delete_many({})
        await db.custodial_wallets.insert_one(CORRECT_WALLET_DOC.copy())
        logger.info(f"  custodial_wallets: seeded wallet {CORRECT_WALLET}")
    except Exception as e:
        logger.error(f"  CRITICAL: failed to seed custodial wallet: {e}")
        return

    # Step 2: Seed remaining collections from file
    total = 1
    for col_name in SEEDED_COLLECTIONS:
        if col_name == "custodial_wallets":
            continue  # Already handled above
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

    logger.info(f"Seed COMPLETE: {total} documents. Wallet: {CORRECT_WALLET}")
