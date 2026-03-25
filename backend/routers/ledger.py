"""
Ledger Router — API endpoints for per-user fund tracking.
"""

from fastapi import APIRouter, HTTPException, Query
from utils.database import db
from services.ledger import (
    get_available_balance,
    get_balance_breakdown,
    get_history,
    reconcile_all,
    migrate_existing_data,
)

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/balance/{user_wallet}")
async def api_get_balance(user_wallet: str):
    """Get the user's balance — on-chain balance is the source of truth."""
    breakdown = await get_balance_breakdown(user_wallet)

    # Get actual on-chain custodial wallet balance as the source of truth
    wallet_doc = await db.custodial_wallets.find_one(
        {"user_wallet": user_wallet}, {"_id": 0}
    )
    if wallet_doc:
        on_chain_sol = wallet_doc.get("balance_lamports", 0) / 1_000_000_000
        breakdown["on_chain_balance_sol"] = round(on_chain_sol, 6)
        breakdown["custodial_address"] = wallet_doc.get("custodial_address", "")
        # Total deposits/withdrawals from custodial wallet records (source of truth)
        breakdown["total_deposited_sol"] = round(
            wallet_doc.get("total_deposits_lamports", 0) / 1_000_000_000, 6
        )
        breakdown["total_withdrawn_sol"] = round(
            wallet_doc.get("total_withdrawals_lamports", 0) / 1_000_000_000, 6
        )

    return breakdown


@router.get("/history/{user_wallet}")
async def api_get_history(
    user_wallet: str,
    limit: int = Query(50, ge=1, le=200),
    entry_type: str = Query(None),
):
    """Get ledger transaction history for a user."""
    entries = await get_history(user_wallet, limit=limit, entry_type=entry_type)
    return {"entries": entries, "count": len(entries)}


@router.get("/reconciliation")
async def api_reconcile():
    """Compare total virtual balances against on-chain. Admin endpoint."""
    return await reconcile_all()


@router.post("/migrate")
async def api_migrate():
    """One-time migration from existing custodial wallet data into the ledger."""
    return await migrate_existing_data()


@router.get("/rake-stats/{user_wallet}")
async def api_rake_stats(user_wallet: str):
    """Get rake (platform fee) statistics for a user."""
    pipeline = [
        {"$match": {"user_wallet": user_wallet, "entry_type": "fee", "metadata.rake_percent": {"$exists": True}}},
        {"$group": {
            "_id": None,
            "total_rake_sol": {"$sum": {"$abs": "$amount_sol"}},
            "total_gross_profit_sol": {"$sum": "$metadata.gross_pnl_sol"},
            "rake_count": {"$sum": 1},
        }},
    ]
    result = await db.user_ledger.aggregate(pipeline).to_list(1)
    if result:
        r = result[0]
        return {
            "total_rake_sol": round(r["total_rake_sol"], 6),
            "total_gross_profit_sol": round(r["total_gross_profit_sol"], 6),
            "rake_count": r["rake_count"],
            "rake_percent": 2.5,
        }
    return {"total_rake_sol": 0, "total_gross_profit_sol": 0, "rake_count": 0, "rake_percent": 2.5}
