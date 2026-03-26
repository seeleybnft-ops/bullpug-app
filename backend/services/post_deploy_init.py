"""
Post-deploy ledger initialization.

Runs once on first startup with a fresh database to restore the known-good
ledger state and open positions that existed before the deploy.

This is idempotent — if the ledger already has entries, it skips entirely.
"""

import logging
from datetime import datetime, timezone
from utils.database import db

logger = logging.getLogger(__name__)

USER_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
# NOTE: Custodial wallet is NOT created by this script. It is created by
# get_or_create_custodial_wallet() on first access, which generates a proper
# keypair. NEVER manually insert custodial wallet records without a keypair.

# Platform rake (pre-existing on-chain balance before any user deposits)
PLATFORM_RAKE_SOL = 0.008767

# No pre-existing deposits or positions for fresh deploy
# User will deposit to the new custodial wallet after deploy


async def run_post_deploy_init():
    """
    Idempotent initializer. Only runs if the database is empty (fresh deploy).
    Records platform rake. User deposits and positions start fresh.
    """
    # Guard: skip if ledger already has entries
    existing = await db.user_ledger.count_documents({})
    if existing > 0:
        logger.info(f"Post-deploy init: ledger already has {existing} entries — skipping.")
        return

    logger.info("Post-deploy init: fresh database detected — recording platform rake...")

    now = datetime.now(timezone.utc).isoformat()

    # 1. Platform rake entry
    await db.user_ledger.insert_one({
        "entry_id": "init_platform_rake",
        "user_wallet": "__platform__",
        "entry_type": "adjustment",
        "amount_sol": PLATFORM_RAKE_SOL,
        "balance_after": PLATFORM_RAKE_SOL,
        "reference_id": "",
        "reference_type": "platform_rake",
        "description": "Pre-existing on-chain balance attributed to platform rake (deploy init)",
        "metadata": {"reason": "deploy_init", "original_balance_sol": PLATFORM_RAKE_SOL},
        "created_at": now,
    })
    logger.info(f"  Recorded platform rake: {PLATFORM_RAKE_SOL} SOL")

    logger.info(
        "Post-deploy init COMPLETE: Platform rake recorded. "
        "Custodial wallet will be created on first user access with proper keypair. "
        "User deposits and trades start fresh."
    )
