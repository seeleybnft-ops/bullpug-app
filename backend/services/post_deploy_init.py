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
CUSTODIAL_ADDRESS = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"

# Platform rake (pre-existing on-chain balance before any user deposits)
PLATFORM_RAKE_SOL = 0.008767

# User's known deposits
USER_DEPOSIT_SOL = 0.05          # Direct deposit made by user
PRE_TRADE_FUNDS_SOL = 0.033049   # Funds already in trades before ledger existed

# The 4 open positions at time of deploy
OPEN_POSITIONS = [
    {
        "position_id": "SYNCEEBC65A3",
        "token_symbol": "RENDER",
        "token_name": "Render Token",
        "token_mint": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
        "amount_sol": 0.006528,
        "entry_price": 1.68,
        "amount_tokens": 0.54396511,
        "raw_amount_tokens": 54396511,
        "decimals": 8,
        "trade_type": "buy",
        "dex": "raydium",
        "created_at": "2026-03-23T23:51:13.537446+00:00",
    },
    {
        "position_id": "b5cc699f",
        "execution_id": "auto_c78410",
        "token_symbol": "PYTH",
        "token_mint": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
        "amount_sol": 0.01,
        "entry_price": 0.0399,
        "amount_tokens": 22.858233,
        "raw_amount_tokens": 22858233,
        "trade_type": "buy",
        "confidence": 0.95,
        "strategy": "combined",
        "created_at": "2026-03-23T23:31:23.794321+00:00",
        "tx_signature": "5JV82NaDq58FTgxZp6679rKga2mQduuPYTWpUQrFteZC744QhZQcmsZQGSVZyAhVB35gsUgLVAUHcxN1355iEc9s",
    },
    {
        "position_id": "SYNC1EFB2328",
        "token_symbol": "JUP",
        "token_name": "Jupiter",
        "token_mint": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        "amount_sol": 0.006521,
        "entry_price": 0.1535,
        "amount_tokens": 11.893906,
        "raw_amount_tokens": 11893906,
        "decimals": 6,
        "trade_type": "buy",
        "dex": "meteora",
        "created_at": "2026-03-23T23:30:49.604634+00:00",
    },
    {
        "position_id": "1ba25310",
        "execution_id": "auto_db8d55",
        "token_symbol": "JUP",
        "token_mint": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        "amount_sol": 0.01,
        "entry_price": 0.1535,
        "amount_tokens": 11.893906,
        "raw_amount_tokens": 11893906,
        "decimals": 6,
        "trade_type": "buy",
        "created_at": "2026-03-23T23:30:26.241927+00:00",
    },
]


async def run_post_deploy_init():
    """
    Idempotent initializer. Only runs if the database is empty (fresh deploy).
    Restores: platform rake, user deposits, open positions, custodial wallet, and ledger entries.
    """
    # Guard: skip if ledger already has entries
    existing = await db.user_ledger.count_documents({})
    if existing > 0:
        logger.info(f"Post-deploy init: ledger already has {existing} entries — skipping.")
        return

    logger.info("Post-deploy init: fresh database detected — restoring ledger state...")

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

    # 2. User deposit (0.05 SOL direct deposit)
    await db.user_ledger.insert_one({
        "entry_id": "init_deposit_01",
        "user_wallet": USER_WALLET,
        "entry_type": "deposit",
        "amount_sol": USER_DEPOSIT_SOL,
        "balance_after": USER_DEPOSIT_SOL,
        "reference_id": "manual_retroactive",
        "reference_type": "deposit_tx",
        "description": f"Deposit {USER_DEPOSIT_SOL} SOL (restored after deploy)",
        "metadata": {"deploy_init": True},
        "created_at": now,
    })
    logger.info(f"  Recorded user deposit: {USER_DEPOSIT_SOL} SOL")

    # 3. Pre-existing trade funds deposit (0.033049 SOL)
    running_balance = USER_DEPOSIT_SOL + PRE_TRADE_FUNDS_SOL
    await db.user_ledger.insert_one({
        "entry_id": "init_deposit_02",
        "user_wallet": USER_WALLET,
        "entry_type": "deposit",
        "amount_sol": PRE_TRADE_FUNDS_SOL,
        "balance_after": running_balance,
        "reference_id": "pre_existing_trade_funds",
        "reference_type": "deposit_tx",
        "description": f"Deposit {PRE_TRADE_FUNDS_SOL} SOL — funds already in open trades (restored after deploy)",
        "metadata": {"deploy_init": True},
        "created_at": now,
    })
    logger.info(f"  Recorded pre-trade deposit: {PRE_TRADE_FUNDS_SOL} SOL")

    # 4. Trade_open ledger entries for each open position
    for pos in OPEN_POSITIONS:
        amt = pos["amount_sol"]
        running_balance -= amt
        await db.user_ledger.insert_one({
            "entry_id": f"init_trade_{pos['position_id']}",
            "user_wallet": USER_WALLET,
            "entry_type": "trade_open",
            "amount_sol": -abs(amt),
            "balance_after": round(running_balance, 9),
            "reference_id": pos["position_id"],
            "reference_type": "position",
            "description": f"Trade open: {pos['token_symbol']} ({amt} SOL) [deploy init]",
            "metadata": {"position_id": pos["position_id"], "token_symbol": pos["token_symbol"], "deploy_init": True},
            "created_at": now,
        })
    logger.info(f"  Recorded {len(OPEN_POSITIONS)} trade_open entries")

    # 5. Custodial wallet is NOT created here — let get_or_create_custodial_wallet()
    # handle it on first access so it generates a proper keypair.
    # The user will get a new custodial address and must deposit to it.
    logger.info("  Custodial wallet will be created on first access with proper keypair")

    # 6. Restore open positions in ai_trader_positions
    for pos in OPEN_POSITIONS:
        existing_pos = await db.ai_trader_positions.find_one({"position_id": pos["position_id"]})
        if not existing_pos:
            doc = {
                "wallet_address": USER_WALLET,
                "status": "open",
                "auto_trade": True,
                "executed_on_chain": True,
                "custodial": True,
                "source": "custodial",
                "opened_at": pos["created_at"],
                "last_synced": now,
                **pos,
            }
            await db.ai_trader_positions.insert_one(doc)
    logger.info(f"  Restored {len(OPEN_POSITIONS)} open positions")

    # Final verification
    final_balance = await db.user_ledger.count_documents({"user_wallet": USER_WALLET})
    logger.info(
        f"Post-deploy init COMPLETE: {final_balance} ledger entries for user, "
        f"available={USER_DEPOSIT_SOL} SOL, locked={PRE_TRADE_FUNDS_SOL} SOL, "
        f"total={USER_DEPOSIT_SOL + PRE_TRADE_FUNDS_SOL} SOL"
    )
