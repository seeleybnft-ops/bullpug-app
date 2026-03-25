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
    """Get the user's available balance and full breakdown."""
    breakdown = await get_balance_breakdown(user_wallet)
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
