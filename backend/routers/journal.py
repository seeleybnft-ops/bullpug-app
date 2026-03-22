"""Trading journal routes for tracking trades and performance."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import uuid
import io
import csv
import json as jsonlib
import statistics
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional, List

from utils.database import db

router = APIRouter(prefix="/journal", tags=["journal"])


class TradeEntry(BaseModel):
    trade_id: Optional[str] = None
    wallet_address: Optional[str] = None  # Wallet address for multi-user support
    date_entry: str
    date_exit: Optional[str] = None
    asset: str
    trade_type: str
    leverage: Optional[float] = 1.0
    entry_price: float
    position_size: float
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    fees: float = 0
    slippage: float = 0
    chart_link: Optional[str] = None
    entry_reason: Optional[str] = None
    strategy: Optional[str] = None
    market_conditions: Optional[str] = None
    expected_rr: Optional[float] = None
    emotion_entry: Optional[str] = None
    emotion_exit: Optional[str] = None
    confidence_level: Optional[int] = None
    mindset_notes: Optional[str] = None
    what_went_well: Optional[str] = None
    what_went_wrong: Optional[str] = None
    lessons: Optional[str] = None
    trade_grade: Optional[str] = None
    tags: Optional[List[str]] = []
    external_influences: Optional[str] = None
    health_notes: Optional[str] = None
    status: str = "open"
    # New fields for pending entries
    pending: bool = False
    source: Optional[str] = None  # "auto_trade", "manual"
    tx_signature: Optional[str] = None
    auto_logged_at: Optional[str] = None
    completed_at: Optional[str] = None


class PendingJournalEntry(BaseModel):
    """Model for auto-trade pending journal entries"""
    wallet_address: str
    asset: str
    trade_type: str  # "buy" or "sell"
    entry_price: float
    position_size: float  # in SOL
    position_size_tokens: Optional[float] = None
    tx_signature: Optional[str] = None
    source: str = "auto_trade"
    # Optional user input fields
    emotion_entry: Optional[str] = None
    entry_reason: Optional[str] = None
    strategy: Optional[str] = None
    confidence_level: Optional[int] = None
    mindset_notes: Optional[str] = None


class JournalBackupRequest(BaseModel):
    wallet_address: str


def calculate_pnl(entry_price: float, exit_price: Optional[float], position_size: float, 
                  trade_type: str, fees: float, slippage: float):
    """Calculate PnL for a trade."""
    if not exit_price or not entry_price:
        return 0, 0
    
    if trade_type.lower() in ["long", "spot"]:
        pnl = (exit_price - entry_price) * position_size
    else:
        pnl = (entry_price - exit_price) * position_size
    
    pnl -= fees + slippage
    pnl_percent = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
    if trade_type.lower() == "short":
        pnl_percent = -pnl_percent
    
    return round(pnl, 2), round(pnl_percent, 2)


@router.get("/trades")
async def get_trades(limit: int = 100, status: Optional[str] = None):
    """Get all trades."""
    query = {}
    if status:
        query["status"] = status
    trades = await db.trading_journal.find(query, {"_id": 0}).sort("date_entry", -1).to_list(limit)
    return {"trades": trades, "count": len(trades)}


@router.get("/trade/{trade_id}")
async def get_trade(trade_id: str):
    """Get a specific trade."""
    trade = await db.trading_journal.find_one({"trade_id": trade_id}, {"_id": 0})
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("/trade")
async def create_trade(data: TradeEntry):
    """Create a new trade entry."""
    trade_id = data.trade_id or f"T{str(uuid.uuid4())[:8].upper()}"
    pnl, pnl_percent = calculate_pnl(
        data.entry_price, data.exit_price, data.position_size,
        data.trade_type, data.fees, data.slippage
    )
    
    trade = {
        "trade_id": trade_id,
        **data.model_dump(),
        "asset": data.asset.upper(),
        "pnl": pnl,
        "pnl_percent": pnl_percent,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trading_journal.insert_one(trade)
    return {"message": "Trade logged!", "trade_id": trade_id, "pnl": pnl}


@router.put("/trade/{trade_id}")
async def update_trade(trade_id: str, data: TradeEntry):
    """Update an existing trade."""
    existing = await db.trading_journal.find_one({"trade_id": trade_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    pnl, pnl_percent = calculate_pnl(
        data.entry_price, data.exit_price, data.position_size,
        data.trade_type, data.fees, data.slippage
    )
    
    update_data = {
        **data.model_dump(),
        "asset": data.asset.upper(),
        "pnl": pnl,
        "pnl_percent": pnl_percent,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trading_journal.update_one({"trade_id": trade_id}, {"$set": update_data})
    return {"message": "Trade updated!", "trade_id": trade_id, "pnl": pnl}


@router.delete("/trade/{trade_id}")
async def delete_trade(trade_id: str):
    """Delete a trade."""
    result = await db.trading_journal.delete_one({"trade_id": trade_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"message": "Trade deleted!", "trade_id": trade_id}


# ============== Pending Journal Entries (Auto-Trade Integration) ==============

@router.post("/pending-entry")
async def create_pending_entry(entry: PendingJournalEntry):
    """
    Create a pending journal entry from an auto-trade.
    This entry will be highlighted in the journal for user to complete.
    Auto-logs after 24 hours if not completed.
    """
    trade_id = f"AT{str(uuid.uuid4())[:8].upper()}"
    
    pending_trade = {
        "trade_id": trade_id,
        "wallet_address": entry.wallet_address,
        "asset": entry.asset.upper(),
        "trade_type": entry.trade_type,
        "entry_price": entry.entry_price,
        "position_size": entry.position_size,
        "position_size_tokens": entry.position_size_tokens,
        "date_entry": datetime.now(timezone.utc).isoformat(),
        "tx_signature": entry.tx_signature,
        "source": entry.source,
        # User input fields (optional)
        "emotion_entry": entry.emotion_entry,
        "entry_reason": entry.entry_reason,
        "strategy": entry.strategy,
        "confidence_level": entry.confidence_level,
        "mindset_notes": entry.mindset_notes,
        # Pending status
        "pending": True,
        "auto_logged_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc).isoformat(),  # Will be updated by scheduler
        "status": "open" if entry.trade_type == "buy" else "closed",
        # Defaults
        "pnl": 0,
        "pnl_percent": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trading_journal.insert_one(pending_trade)
    
    return {
        "success": True,
        "trade_id": trade_id,
        "message": f"Pending journal entry created for {entry.asset} {entry.trade_type}"
    }


@router.get("/pending/{wallet_address}")
async def get_pending_entries(wallet_address: str):
    """Get all pending journal entries for a wallet."""
    pending = await db.trading_journal.find(
        {
            "wallet_address": wallet_address,
            "pending": True
        },
        {"_id": 0}
    ).sort("auto_logged_at", -1).to_list(50)
    
    return {
        "pending_entries": pending,
        "count": len(pending)
    }


class CompletePendingRequest(BaseModel):
    """Request to complete a pending journal entry"""
    emotion_entry: Optional[str] = None
    emotion_exit: Optional[str] = None
    entry_reason: Optional[str] = None
    strategy: Optional[str] = None
    market_conditions: Optional[str] = None
    confidence_level: Optional[int] = None
    mindset_notes: Optional[str] = None
    what_went_well: Optional[str] = None
    what_went_wrong: Optional[str] = None
    lessons: Optional[str] = None
    trade_grade: Optional[str] = None
    tags: Optional[List[str]] = []


@router.put("/pending/{trade_id}/complete")
async def complete_pending_entry(trade_id: str, data: CompletePendingRequest):
    """
    Complete a pending journal entry with user's psychological notes.
    Marks the entry as no longer pending.
    """
    existing = await db.trading_journal.find_one({"trade_id": trade_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Pending entry not found")
    
    update_data = {
        **data.model_dump(exclude_none=True),
        "pending": False,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trading_journal.update_one(
        {"trade_id": trade_id},
        {"$set": update_data}
    )
    
    return {
        "success": True,
        "trade_id": trade_id,
        "message": "Journal entry completed!"
    }


@router.post("/auto-complete-expired")
async def auto_complete_expired_entries():
    """
    Auto-complete pending entries older than 24 hours.
    Called by scheduler or manually.
    """
    from datetime import timedelta
    
    cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    
    # Find expired pending entries
    expired = await db.trading_journal.find(
        {
            "pending": True,
            "auto_logged_at": {"$lt": cutoff_time}
        }
    ).to_list(100)
    
    updated_count = 0
    for entry in expired:
        await db.trading_journal.update_one(
            {"trade_id": entry["trade_id"]},
            {
                "$set": {
                    "pending": False,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "auto_completed": True,
                    "tags": (entry.get("tags") or []) + ["incomplete"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        updated_count += 1
    
    return {
        "success": True,
        "auto_completed": updated_count,
        "message": f"Auto-completed {updated_count} expired pending entries"
    }


@router.get("/trades/{wallet_address}/stats")
async def get_trade_stats(wallet_address: str):
    """Get aggregated statistics for a wallet's logged trades."""
    trades = await db.trading_journal.find(
        {"wallet_address": wallet_address, "status": "closed"},
        {"_id": 0, "pnl": 1, "pnl_percent": 1, "asset": 1}
    ).to_list(1000)
    
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "best_trade": None,
            "worst_trade": None,
            "avg_pnl": 0,
            "wins": 0,
            "losses": 0,
            "top_assets": []
        }
    
    pnls = [t.get("pnl", 0) or 0 for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    total = len(pnls)
    
    # Get top performing assets
    asset_pnls = {}
    for t in trades:
        asset = t.get("asset", "Unknown")
        asset_pnls[asset] = asset_pnls.get(asset, 0) + (t.get("pnl", 0) or 0)
    
    top_assets = sorted(asset_pnls.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_trades": total,
        "win_rate": (wins / total * 100) if total > 0 else 0,
        "total_pnl": sum(pnls),
        "best_trade": max(pnls) if pnls else None,
        "worst_trade": min(pnls) if pnls else None,
        "avg_pnl": statistics.mean(pnls) if pnls else 0,
        "wins": wins,
        "losses": losses,
        "top_assets": [{"asset": a, "pnl": p} for a, p in top_assets]
    }


@router.get("/dashboard")
async def get_journal_dashboard():
    """Get trading journal dashboard statistics."""
    trades = await db.trading_journal.find({}, {"_id": 0}).to_list(1000)
    
    if not trades:
        return {
            "total_trades": 0,
            "open_trades": 0,
            "closed_trades": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "avg_pnl": 0,
            "biggest_win": None,
            "biggest_loss": None,
            "most_traded_asset": None,
            "avg_confidence": 0,
            "recent_emotions": [],
            "pnl_by_asset": {},
            "win_streak": 0,
            "loss_streak": 0,
            "avg_rr": 0,
            "sharpe_ratio": 0
        }
    
    closed_trades = [t for t in trades if t.get("status") == "closed" and t.get("pnl") is not None]
    open_trades = [t for t in trades if t.get("status") == "open"]
    
    total_pnl = sum(t.get("pnl", 0) for t in closed_trades)
    wins = [t for t in closed_trades if t.get("pnl", 0) > 0]
    losses = [t for t in closed_trades if t.get("pnl", 0) < 0]
    
    win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0
    avg_pnl = total_pnl / len(closed_trades) if closed_trades else 0
    
    biggest_win = max(closed_trades, key=lambda t: t.get("pnl", 0)) if wins else None
    biggest_loss = min(closed_trades, key=lambda t: t.get("pnl", 0)) if losses else None
    
    # Most traded asset
    asset_counts = {}
    for t in trades:
        asset = t.get("asset", "Unknown")
        asset_counts[asset] = asset_counts.get(asset, 0) + 1
    most_traded = max(asset_counts.items(), key=lambda x: x[1]) if asset_counts else (None, 0)
    
    # P&L by asset
    pnl_by_asset = {}
    for t in closed_trades:
        asset = t.get("asset", "Unknown")
        pnl_by_asset[asset] = pnl_by_asset.get(asset, 0) + t.get("pnl", 0)
    
    # Average confidence
    confidence_vals = [t.get("confidence_level") for t in trades if t.get("confidence_level")]
    avg_confidence = sum(confidence_vals) / len(confidence_vals) if confidence_vals else 0
    
    # Win/Loss streaks
    sorted_closed = sorted(closed_trades, key=lambda x: x.get("date_entry", ""))
    win_streak = loss_streak = current_win = current_loss = 0
    for t in sorted_closed:
        if t.get("pnl", 0) > 0:
            current_win += 1
            current_loss = 0
            win_streak = max(win_streak, current_win)
        elif t.get("pnl", 0) < 0:
            current_loss += 1
            current_win = 0
            loss_streak = max(loss_streak, current_loss)
    
    # Average R:R
    rr_vals = [t.get("expected_rr") for t in trades if t.get("expected_rr")]
    avg_rr = sum(rr_vals) / len(rr_vals) if rr_vals else 0
    
    # Sharpe-like ratio
    pnl_vals = [t.get("pnl", 0) for t in closed_trades]
    if len(pnl_vals) > 1:
        std_dev = statistics.stdev(pnl_vals)
        sharpe = (avg_pnl / std_dev) if std_dev > 0 else 0
    else:
        sharpe = 0
    
    return {
        "total_trades": len(trades),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 1),
        "avg_pnl": round(avg_pnl, 2),
        "biggest_win": {"trade_id": biggest_win.get("trade_id"), "asset": biggest_win.get("asset"), "pnl": biggest_win.get("pnl")} if biggest_win else None,
        "biggest_loss": {"trade_id": biggest_loss.get("trade_id"), "asset": biggest_loss.get("asset"), "pnl": biggest_loss.get("pnl")} if biggest_loss else None,
        "most_traded_asset": {"asset": most_traded[0], "count": most_traded[1]} if most_traded[0] else None,
        "avg_confidence": round(avg_confidence, 1),
        "pnl_by_asset": {k: round(v, 2) for k, v in pnl_by_asset.items()},
        "win_streak": win_streak,
        "loss_streak": loss_streak,
        "avg_rr": round(avg_rr, 2),
        "sharpe_ratio": round(sharpe, 3),
        "total_wins": len(wins),
        "total_losses": len(losses)
    }


@router.get("/export/csv")
async def export_trades_csv():
    """Export all trades to CSV."""
    trades = await db.trading_journal.find({}, {"_id": 0}).sort("date_entry", -1).to_list(10000)
    
    if not trades:
        raise HTTPException(status_code=404, detail="No trades to export")
    
    output = io.StringIO()
    fieldnames = [
        "trade_id", "date_entry", "date_exit", "asset", "trade_type", "leverage",
        "entry_price", "position_size", "exit_price", "exit_reason", "stop_loss",
        "take_profit", "fees", "slippage", "pnl", "pnl_percent", "strategy",
        "entry_reason", "market_conditions", "expected_rr", "emotion_entry",
        "emotion_exit", "confidence_level", "trade_grade", "what_went_well",
        "what_went_wrong", "lessons", "tags", "status"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for trade in trades:
        trade["tags"] = ",".join(trade.get("tags", []))
        writer.writerow(trade)
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bullpug_trading_journal.csv"}
    )


@router.get("/export/json")
async def export_trades_json():
    """Export all trades to JSON."""
    trades = await db.trading_journal.find({}, {"_id": 0}).sort("date_entry", -1).to_list(10000)
    dashboard = await get_journal_dashboard()
    
    export_data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "summary": dashboard,
        "trades": trades
    }
    
    return StreamingResponse(
        io.BytesIO(jsonlib.dumps(export_data, indent=2).encode()),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=bullpug_trading_journal.json"}
    )


@router.post("/backup")
async def create_backup(data: JournalBackupRequest):
    """Create a cloud backup of the journal."""
    trades = await db.trading_journal.find({}, {"_id": 0}).to_list(10000)
    dashboard = await get_journal_dashboard()
    
    backup = {
        "id": str(uuid.uuid4()),
        "wallet_address": data.wallet_address,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "trade_count": len(trades),
        "summary": dashboard,
        "trades": trades
    }
    
    await db.journal_backups.insert_one(backup)
    return {"message": "Backup created", "backup_id": backup["id"], "trade_count": len(trades)}


@router.get("/backups/{wallet_address}")
async def get_backups(wallet_address: str):
    """Get all backups for a wallet."""
    backups = await db.journal_backups.find(
        {"wallet_address": wallet_address},
        {"_id": 0, "trades": 0}
    ).sort("created_at", -1).to_list(20)
    
    return {"backups": backups}


@router.post("/restore/{backup_id}")
async def restore_backup(backup_id: str, wallet_address: str):
    """Restore trades from a backup."""
    backup = await db.journal_backups.find_one({
        "id": backup_id,
        "wallet_address": wallet_address
    })
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    trades = backup.get("trades", [])
    restored_count = 0
    
    for trade in trades:
        existing = await db.trading_journal.find_one({"trade_id": trade.get("trade_id")})
        if not existing:
            trade["wallet_address"] = wallet_address
            trade["restored_from_backup"] = backup_id
            trade["restored_at"] = datetime.now(timezone.utc).isoformat()
            await db.trading_journal.insert_one(trade)
            restored_count += 1
    
    return {
        "message": f"Restored {restored_count} trades",
        "restored_count": restored_count,
        "total_in_backup": len(trades)
    }


@router.delete("/backup/{backup_id}")
async def delete_backup(backup_id: str, wallet_address: str):
    """Delete a backup."""
    result = await db.journal_backups.delete_one({
        "id": backup_id,
        "wallet_address": wallet_address
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return {"message": "Backup deleted"}
