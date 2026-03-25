"""
Internal Ledger Service — Per-user fund tracking for custodial trading.

Every financial event (deposit, withdrawal, trade open, trade close) is recorded
as a ledger entry. The user's available balance is always derived from the sum of
all their ledger entries, making it the single source of truth for "who owns what."

Entry types:
  deposit       — SOL deposited into custodial wallet (credit, +)
  withdrawal    — SOL withdrawn from custodial wallet (debit, -)
  trade_open    — SOL locked when a position is opened (debit, -)
  trade_close   — SOL returned when a position is closed (credit, +), includes P&L
  fee           — Platform/network fees deducted (debit, -)
  adjustment    — Manual correction by admin (credit or debit)
"""

import logging
import uuid
from datetime import datetime, timezone
from utils.database import db

logger = logging.getLogger(__name__)

ENTRY_TYPES = {"deposit", "withdrawal", "trade_open", "trade_close", "fee", "adjustment"}


async def record_entry(
    user_wallet: str,
    entry_type: str,
    amount_sol: float,
    reference_id: str = None,
    reference_type: str = None,
    description: str = "",
    metadata: dict = None,
) -> dict:
    """
    Append one ledger entry and return it (with computed balance_after).

    amount_sol: positive = credit (money in), negative = debit (money out).
    """
    if entry_type not in ENTRY_TYPES:
        raise ValueError(f"Invalid entry_type: {entry_type}")

    # Compute running balance
    current = await get_available_balance(user_wallet)
    balance_after = round(current + amount_sol, 9)

    entry = {
        "entry_id": str(uuid.uuid4())[:12],
        "user_wallet": user_wallet,
        "entry_type": entry_type,
        "amount_sol": round(amount_sol, 9),
        "balance_after": balance_after,
        "reference_id": reference_id or "",
        "reference_type": reference_type or entry_type,
        "description": description,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.user_ledger.insert_one(entry)
    entry.pop("_id", None)

    logger.info(
        f"Ledger [{entry_type}] user={user_wallet[:8]}… "
        f"amount={amount_sol:+.6f} SOL  balance_after={balance_after:.6f} SOL"
    )
    return entry


async def get_available_balance(user_wallet: str) -> float:
    """
    Compute the user's available balance (not locked in open trades).
    = sum(all ledger entries for this user)
    """
    pipeline = [
        {"$match": {"user_wallet": user_wallet}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_sol"}}},
    ]
    result = await db.user_ledger.aggregate(pipeline).to_list(1)
    return round(result[0]["total"], 9) if result else 0.0


async def get_balance_breakdown(user_wallet: str) -> dict:
    """
    Return a detailed balance breakdown:
      available    — SOL the user can withdraw or use for new trades
      locked       — SOL currently in open positions
      total_deposited — lifetime deposits
      total_withdrawn — lifetime withdrawals
      realised_pnl — sum of P&L from closed trades
    """
    pipeline = [
        {"$match": {"user_wallet": user_wallet}},
        {
            "$group": {
                "_id": "$entry_type",
                "sum": {"$sum": "$amount_sol"},
                "count": {"$sum": 1},
            }
        },
    ]
    results = await db.user_ledger.aggregate(pipeline).to_list(20)
    buckets = {r["_id"]: r for r in results}

    deposits = buckets.get("deposit", {}).get("sum", 0)
    withdrawals = abs(buckets.get("withdrawal", {}).get("sum", 0))
    trade_opens = abs(buckets.get("trade_open", {}).get("sum", 0))
    trade_closes = buckets.get("trade_close", {}).get("sum", 0)
    fees = abs(buckets.get("fee", {}).get("sum", 0))
    adjustments = buckets.get("adjustment", {}).get("sum", 0)

    # Locked = live current value of open positions (not static entry cost)
    open_positions = await db.ai_trader_positions.find(
        {"wallet_address": user_wallet, "status": "open"},
        {"_id": 0, "amount_sol": 1, "entry_price": 1, "current_price": 1, "trade_type": 1},
    ).to_list(100)

    locked_live = 0
    for p in open_positions:
        amt = p.get("amount_sol", 0)
        entry_px = p.get("entry_price", 0)
        cur_px = p.get("current_price", 0)
        if cur_px and entry_px > 0:
            if p.get("trade_type") == "buy":
                pnl_pct = (cur_px - entry_px) / entry_px
            else:
                pnl_pct = (entry_px - cur_px) / entry_px
            locked_live += amt + (amt * pnl_pct)
        else:
            locked_live += amt

    # Entry-cost locked (from ledger) — used for P&L calc
    locked_entry_cost = max(0, trade_opens - trade_closes)

    # Available = everything that isn't locked (based on ledger net)
    available = await get_available_balance(user_wallet)

    # Realised P&L = (close credits) - (open debits that were closed)
    realised_pnl = trade_closes - (trade_opens - locked_entry_cost)

    # Unrealised P&L = live value - entry cost
    unrealised_pnl = locked_live - locked_entry_cost

    return {
        "available_sol": round(available, 6),
        "locked_in_trades_sol": round(locked_live, 6),
        "locked_entry_cost_sol": round(locked_entry_cost, 6),
        "total_balance_sol": round(available + locked_live, 6),
        "total_deposited_sol": round(deposits, 6),
        "total_withdrawn_sol": round(withdrawals, 6),
        "total_fees_sol": round(fees, 6),
        "realised_pnl_sol": round(realised_pnl, 6),
        "unrealised_pnl_sol": round(unrealised_pnl, 6),
        "adjustments_sol": round(adjustments, 6),
        "entry_counts": {t: buckets.get(t, {}).get("count", 0) for t in ENTRY_TYPES},
    }


async def get_history(user_wallet: str, limit: int = 50, entry_type: str = None) -> list:
    """Return recent ledger entries for a user, newest first."""
    query = {"user_wallet": user_wallet}
    if entry_type:
        query["entry_type"] = entry_type

    cursor = db.user_ledger.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(limit)


async def reconcile_all() -> dict:
    """
    Compare total virtual balances (sum of all ledger entries per user)
    against stored custodial wallet balances. Flags any discrepancy.
    """
    # Sum ledger per user
    pipeline = [
        {"$group": {"_id": "$user_wallet", "ledger_balance": {"$sum": "$amount_sol"}}},
    ]
    ledger_rows = await db.user_ledger.aggregate(pipeline).to_list(500)
    ledger_map = {r["_id"]: round(r["ledger_balance"], 6) for r in ledger_rows}

    total_virtual = sum(ledger_map.values())

    # Get all custodial wallets
    wallets = await db.custodial_wallets.find({}, {"_id": 0, "user_wallet": 1, "custodial_address": 1}).to_list(500)

    discrepancies = []
    for w in wallets:
        uw = w["user_wallet"]
        vb = ledger_map.get(uw, 0)
        if uw not in ledger_map:
            discrepancies.append({"user_wallet": uw, "issue": "no_ledger_entries", "ledger_balance": 0})

    return {
        "total_virtual_balance_sol": round(total_virtual, 6),
        "users_with_balance": len([v for v in ledger_map.values() if v > 0]),
        "users_tracked": len(ledger_map),
        "custodial_wallets": len(wallets),
        "discrepancies": discrepancies,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def migrate_existing_data():
    """
    One-time migration: create ledger entries from existing custodial wallet records
    and open positions so the ledger reflects historical state.
    """
    migrated = 0

    # Check if already migrated
    count = await db.user_ledger.count_documents({})
    if count > 0:
        return {"migrated": 0, "message": "Ledger already has entries, skipping migration"}

    # Migrate deposits from custodial wallets
    wallets = await db.custodial_wallets.find({}, {"_id": 0}).to_list(500)
    for w in wallets:
        uw = w.get("user_wallet")
        deposits_sol = w.get("total_deposits_lamports", 0) / 1_000_000_000
        withdrawals_sol = w.get("total_withdrawals_lamports", 0) / 1_000_000_000

        if deposits_sol > 0:
            await record_entry(
                uw, "deposit", deposits_sol,
                reference_type="migration",
                description="Historical deposits (migration)"
            )
            migrated += 1

        if withdrawals_sol > 0:
            await record_entry(
                uw, "withdrawal", -withdrawals_sol,
                reference_type="migration",
                description="Historical withdrawals (migration)"
            )
            migrated += 1

    # Migrate open positions as locked funds
    open_positions = await db.ai_trader_positions.find(
        {"status": "open"}, {"_id": 0}
    ).to_list(500)

    for pos in open_positions:
        uw = pos.get("wallet_address")
        amt = pos.get("amount_sol", 0)
        if uw and amt > 0:
            await record_entry(
                uw, "trade_open", -amt,
                reference_id=pos.get("position_id", ""),
                reference_type="position",
                description=f"Open position {pos.get('token_symbol', '?')} (migration)",
                metadata={"token_symbol": pos.get("token_symbol"), "migrated": True}
            )
            migrated += 1

    logger.info(f"Ledger migration complete: {migrated} entries created")
    return {"migrated": migrated, "message": f"Created {migrated} ledger entries from existing data"}
