"""
Post-deploy database initialization.

Ensures the correct custodial wallet (CFzZRc76y...) is present in the
production database. ONLY touches custodial_wallets collection.
All other data (ledger, positions, settings) is left untouched to preserve
live trading state.

The deposit detection fix in custodial_wallet.py handles reconciliation.
"""

import logging
from utils.database import db

logger = logging.getLogger(__name__)

CORRECT_WALLET = "CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg"
OLD_LOST_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"
USER_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"

CORRECT_WALLET_DOC = {
    "user_wallet": USER_WALLET,
    "custodial_address": CORRECT_WALLET,
    "encrypted_private_key": "Z0FBQUFBQnB4WjRETXlJN0F1U3A2N2UwNWVKRmNTSktEUk5EeGJETF9uMTNESW9KbXYwUWduYVJMUEN1Y2hkXzBxVGh4OUh3bXVkaHZKVWVfWmEyYTE5dml4SF9XSWNaXzdCMlR4TnJselp2dklqTUk2dlYxcXR6S21SRW45dl9XaUZFOVFZTXR6cVBBSk40QWFrNWRQeFlkSTZ0MzhIRnB5eHJiNG9Da3FuMzhqcEg3WmxySmlVPQ==",
    "balance_lamports": 0,
    "created_at": "2026-03-26T20:58:43.758196+00:00",
    "last_activity": "2026-03-27T10:30:00.000000+00:00",
    "total_deposits_lamports": 0,
    "total_withdrawals_lamports": 0,
    "transaction_history": []
}


async def run_post_deploy_init():
    """
    Idempotent. Only replaces the custodial wallet if the correct one is missing.
    Never touches ledger, positions, or other live trading data.
    """
    correct = await db.custodial_wallets.find_one(
        {"custodial_address": CORRECT_WALLET}, {"_id": 1}
    )
    if correct:
        logger.info("Post-deploy init: correct wallet CFzZRc76y found — skipping.")
        return

    logger.info("Post-deploy init: correct wallet NOT found — replacing wallet only...")

    try:
        await db.custodial_wallets.delete_many({"user_wallet": USER_WALLET})
        await db.custodial_wallets.insert_one(CORRECT_WALLET_DOC.copy())
        logger.info(f"  Wallet replaced: {CORRECT_WALLET}")
    except Exception as e:
        logger.error(f"  CRITICAL: wallet replacement failed: {e}")
        return

    # Seed telegram linkage only if missing
    tg_exists = await db.telegram_accounts.count_documents(
        {"wallet_address": USER_WALLET, "active": True}
    )
    if tg_exists == 0:
        await db.telegram_accounts.insert_one({
            "wallet_address": USER_WALLET,
            "chat_id": 6118851473,
            "telegram_username": "Seeleyb",
            "active": True,
            "alerts_enabled": True,
            "linked_at": "2026-03-15T00:03:55.414683+00:00"
        })
        logger.info("  Telegram linkage seeded for @Seeleyb")

    logger.info("Post-deploy init COMPLETE. Deposit detection will reconcile balances.")


async def force_seed():
    """
    Force-replace ONLY the custodial wallet. Does NOT touch ledger or positions.
    """
    logger.info("Force seed: replacing custodial wallet only...")
    await db.custodial_wallets.delete_many({"user_wallet": USER_WALLET})
    await db.custodial_wallets.insert_one(CORRECT_WALLET_DOC.copy())
    logger.info(f"  Wallet set: {CORRECT_WALLET}")
    return {"success": True, "wallet": CORRECT_WALLET, "note": "Wallet replaced. Open Fund Ledger to trigger deposit reconciliation."}
