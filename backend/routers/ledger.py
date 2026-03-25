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
    """Get the user's virtual balance from the internal ledger (source of truth)."""
    breakdown = await get_balance_breakdown(user_wallet)

    # Attach custodial address for display purposes only
    wallet_doc = await db.custodial_wallets.find_one(
        {"user_wallet": user_wallet}, {"_id": 0}
    )
    if wallet_doc:
        breakdown["custodial_address"] = wallet_doc.get("custodial_address", "")

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


@router.post("/reset-fresh-start")
async def api_reset_fresh_start():
    """
    Clear all ledger entries and account for existing on-chain balance as platform rake.
    This is a one-time admin operation to start fresh.
    """
    from services.ledger import record_entry

    # Clear all existing ledger entries
    result = await db.user_ledger.delete_many({})
    deleted = result.deleted_count

    # Record the existing on-chain balance as platform rake
    PLATFORM_WALLET = "__platform__"
    existing_balance_sol = 0.008767
    await record_entry(
        PLATFORM_WALLET, "adjustment", existing_balance_sol,
        reference_type="platform_rake",
        description="Pre-existing on-chain balance attributed to platform rake (fresh start)",
        metadata={"reason": "fresh_start_reset", "original_balance_sol": existing_balance_sol}
    )

    return {
        "success": True,
        "deleted_entries": deleted,
        "platform_attribution_sol": existing_balance_sol,
        "message": f"Ledger reset. {deleted} entries cleared. {existing_balance_sol} SOL attributed to platform rake."
    }


@router.post("/admin/sync-open-positions/{user_wallet}")
async def api_sync_open_positions(user_wallet: str):
    """
    One-time admin operation: create trade_open ledger entries for existing open
    positions that were opened before the ledger system existed.
    """
    from services.ledger import record_entry

    # Find open positions without corresponding ledger entries
    positions = await db.ai_trader_positions.find(
        {"wallet_address": user_wallet, "status": "open"},
        {"_id": 0}
    ).to_list(100)

    synced = []
    for pos in positions:
        pid = pos.get("position_id", "")
        amt = pos.get("amount_sol", 0)
        if amt <= 0:
            continue

        # Check if a trade_open entry already exists for this position
        existing = await db.user_ledger.find_one({
            "user_wallet": user_wallet,
            "type": "trade_open",
            "metadata.position_id": pid,
        })
        if existing:
            continue

        await record_entry(
            user_wallet, "trade_open", -abs(amt),
            reference_id=pid,
            reference_type="position",
            description=f"Trade open: {pos.get('token_symbol', '?')} ({amt} SOL) [retroactive sync]",
            metadata={"position_id": pid, "token_symbol": pos.get("token_symbol", ""), "retroactive": True}
        )
        synced.append({"position_id": pid, "token": pos.get("token_symbol"), "amount_sol": amt})

    return {"success": True, "synced_count": len(synced), "synced": synced}


@router.get("/admin/reconciliation")
async def api_admin_reconciliation():
    """
    Admin endpoint: Compare total virtual balances (from ledger) against
    the actual on-chain custodial wallet balance. Returns drift and per-user breakdown.
    """
    from routers.custodial_wallet import get_wallet_balance

    # 1. Get all custodial wallets and their on-chain balances
    wallets = await db.custodial_wallets.find(
        {}, {"_id": 0, "user_wallet": 1, "custodial_address": 1, "balance_lamports": 1}
    ).to_list(500)

    total_on_chain_lamports = 0
    wallet_map = {}
    for w in wallets:
        addr = w.get("custodial_address", "")
        if addr:
            try:
                balance = await get_wallet_balance(addr)
            except Exception:
                balance = w.get("balance_lamports", 0)
            total_on_chain_lamports += balance
            wallet_map[w["user_wallet"]] = {
                "custodial_address": addr,
                "on_chain_lamports": balance,
                "on_chain_sol": round(balance / 1_000_000_000, 6),
            }

    total_on_chain_sol = round(total_on_chain_lamports / 1_000_000_000, 6)

    # 2. Get all user virtual balances from ledger (total_balance = deposits - withdrawals + PnL)
    # We need total deposits minus withdrawals to know total user entitlement
    pipeline = [
        {"$match": {"user_wallet": {"$ne": "__platform__"}}},
        {"$group": {
            "_id": "$user_wallet",
            "ledger_net": {"$sum": "$amount_sol"},
        }},
    ]
    ledger_rows = await db.user_ledger.aggregate(pipeline).to_list(500)

    # For each user, compute total_balance (available + locked_in_trades)
    ledger_map = {}
    for r in ledger_rows:
        uw = r["_id"]
        # Get full breakdown including locked
        breakdown = await get_balance_breakdown(uw)
        ledger_map[uw] = round(breakdown.get("total_balance_sol", 0), 6)

    total_virtual_sol = round(sum(ledger_map.values()), 6)

    # 3. Platform rake balance
    platform_pipeline = [
        {"$match": {"user_wallet": "__platform__"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_sol"}}},
    ]
    platform_result = await db.user_ledger.aggregate(platform_pipeline).to_list(1)
    platform_rake_sol = round(platform_result[0]["total"], 6) if platform_result else 0

    # 4. Compute drift
    drift_sol = round(total_on_chain_sol - total_virtual_sol - platform_rake_sol, 6)

    # 5. Per-user breakdown (exclude zero-balance noise)
    users = []
    all_wallets = set(list(wallet_map.keys()) + list(ledger_map.keys()))
    for uw in sorted(all_wallets):
        if uw == "__platform__":
            continue
        w_info = wallet_map.get(uw, {})
        on_chain = w_info.get("on_chain_sol", 0)
        virtual = ledger_map.get(uw, 0)
        # Skip wallets with zero everywhere
        if on_chain == 0 and virtual == 0:
            continue
        users.append({
            "user_wallet": uw,
            "short_wallet": f"{uw[:6]}...{uw[-4:]}" if len(uw) > 10 else uw,
            "custodial_address": w_info.get("custodial_address", "N/A"),
            "on_chain_sol": on_chain,
            "virtual_balance_sol": virtual,
            "drift_sol": round(on_chain - virtual, 6),
        })

    return {
        "total_on_chain_sol": total_on_chain_sol,
        "total_virtual_sol": total_virtual_sol,
        "platform_rake_sol": platform_rake_sol,
        "drift_sol": drift_sol,
        "healthy": abs(drift_sol) < 0.001,
        "users": users,
        "user_count": len(users),
        "checked_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


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
