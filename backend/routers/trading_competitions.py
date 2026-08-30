"""
Trading Competitions System
Compete with other traders for prizes based on trading performance

Features:
- Weekly/Monthly trading competitions
- PnL-based ranking
- Prize pool distribution
- Competition history and stats
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from utils.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/competitions", tags=["Trading Competitions"])


# ============== Models ==============

class Competition(BaseModel):
    """Trading competition configuration"""
    competition_id: str
    name: str
    description: str
    competition_type: str  # weekly, monthly, special
    start_time: str
    end_time: str
    status: str = "upcoming"  # upcoming, active, ended, cancelled
    min_participants: int = 10
    max_participants: Optional[int] = None
    entry_fee_sol: float = 0  # Free to enter by default
    prize_pool_sol: float = 0
    prize_distribution: Dict[str, float] = Field(default_factory=lambda: {
        "1": 40, "2": 25, "3": 15, "4": 10, "5": 5, "6-10": 5  # Percentages
    })
    rules: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CompetitionEntry(BaseModel):
    """User entry in a competition"""
    entry_id: str
    competition_id: str
    wallet_address: str
    display_name: str
    entry_time: str
    starting_portfolio_sol: float = 0
    current_portfolio_sol: float = 0
    total_pnl_sol: float = 0
    total_pnl_percent: float = 0
    total_trades: int = 0
    winning_trades: int = 0
    best_trade_pnl_percent: float = 0
    rank: int = 0
    prize_won_sol: float = 0


# ============== Competition Management ==============

@router.post("/create")
async def create_competition(
    name: str,
    description: str,
    competition_type: str = Query("weekly", regex="^(weekly|monthly|special)$"),
    duration_days: int = Query(7, ge=1, le=90),
    prize_pool_sol: float = Query(0, ge=0),
    entry_fee_sol: float = Query(0, ge=0),
    start_immediately: bool = False
):
    """Create a new trading competition."""
    competition_id = str(uuid.uuid4())[:8]
    
    now = datetime.now(timezone.utc)
    if start_immediately:
        start_time = now
    else:
        # Start at next midnight UTC
        start_time = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    end_time = start_time + timedelta(days=duration_days)
    
    competition = {
        "competition_id": competition_id,
        "name": name,
        "description": description,
        "competition_type": competition_type,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "active" if start_immediately else "upcoming",
        "prize_pool_sol": prize_pool_sol,
        "entry_fee_sol": entry_fee_sol,
        "prize_distribution": {"1": 40, "2": 25, "3": 15, "4": 10, "5": 5, "6-10": 5},
        "participants_count": 0,
        "rules": {
            "min_trades": 3,  # Minimum trades to qualify
            "allowed_tokens": "all",  # or specific list
            "max_position_sol": 1.0  # Max per trade
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trading_competitions.insert_one(competition)
    
    return {
        "success": True,
        "competition": {k: v for k, v in competition.items() if k != "_id"}
    }


@router.get("/active")
async def get_active_competitions():
    """Get all active and upcoming competitions."""
    now = datetime.now(timezone.utc).isoformat()
    
    competitions = await db.trading_competitions.find({
        "$or": [
            {"status": "active"},
            {"status": "upcoming", "start_time": {"$gt": now}}
        ]
    }, {"_id": 0}).sort("start_time", 1).to_list(20)
    
    # Enrich with participant counts
    for comp in competitions:
        comp["participants_count"] = await db.competition_entries.count_documents({
            "competition_id": comp["competition_id"]
        })
    
    return {
        "competitions": competitions,
        "count": len(competitions)
    }


@router.get("/history")
async def get_competition_history(limit: int = Query(20, ge=1, le=100)):
    """Get past competitions."""
    competitions = await db.trading_competitions.find(
        {"status": "ended"},
        {"_id": 0}
    ).sort("ended_at", -1).limit(limit).to_list(limit)
    
    return {
        "competitions": competitions,
        "count": len(competitions)
    }


@router.get("/{competition_id}")
async def get_competition(competition_id: str):
    """Get competition details."""
    competition = await db.trading_competitions.find_one(
        {"competition_id": competition_id},
        {"_id": 0}
    )
    
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    # Get participant count and top performers
    participants_count = await db.competition_entries.count_documents({
        "competition_id": competition_id
    })
    
    top_performers = await db.competition_entries.find(
        {"competition_id": competition_id},
        {"_id": 0}
    ).sort("total_pnl_sol", -1).limit(10).to_list(10)
    
    return {
        **competition,
        "participants_count": participants_count,
        "top_performers": top_performers
    }


# ============== Entry Management ==============

@router.post("/join/{competition_id}")
async def join_competition(competition_id: str, wallet_address: str, display_name: Optional[str] = None):
    """Join a trading competition."""
    # Get competition
    competition = await db.trading_competitions.find_one({"competition_id": competition_id})
    
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    if competition["status"] not in ["upcoming", "active"]:
        raise HTTPException(status_code=400, detail="Competition is not accepting entries")
    
    # Check if already joined
    existing = await db.competition_entries.find_one({
        "competition_id": competition_id,
        "wallet_address": wallet_address
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Already joined this competition")
    
    # Check max participants
    if competition.get("max_participants"):
        current_count = await db.competition_entries.count_documents({"competition_id": competition_id})
        if current_count >= competition["max_participants"]:
            raise HTTPException(status_code=400, detail="Competition is full")
    
    # Get user's current portfolio value
    portfolio_value = await calculate_portfolio_value(wallet_address)
    
    # Create entry
    entry_id = str(uuid.uuid4())[:8]
    entry = {
        "entry_id": entry_id,
        "competition_id": competition_id,
        "wallet_address": wallet_address,
        "display_name": display_name or f"Trader_{wallet_address[:6]}",
        "entry_time": datetime.now(timezone.utc).isoformat(),
        "starting_portfolio_sol": portfolio_value,
        "current_portfolio_sol": portfolio_value,
        "total_pnl_sol": 0,
        "total_pnl_percent": 0,
        "total_trades": 0,
        "winning_trades": 0,
        "best_trade_pnl_percent": 0,
        "rank": 0,
        "prize_won_sol": 0
    }
    
    await db.competition_entries.insert_one(entry)
    
    # Update participant count
    await db.trading_competitions.update_one(
        {"competition_id": competition_id},
        {"$inc": {"participants_count": 1}}
    )
    
    return {
        "success": True,
        "entry_id": entry_id,
        "message": f"Successfully joined {competition['name']}",
        "starting_portfolio_sol": portfolio_value
    }


@router.get("/my-entries/{wallet_address}")
async def get_my_entries(wallet_address: str):
    """Get all competition entries for a wallet."""
    entries = await db.competition_entries.find(
        {"wallet_address": wallet_address},
        {"_id": 0}
    ).sort("entry_time", -1).to_list(50)
    
    # Enrich with competition details
    for entry in entries:
        comp = await db.trading_competitions.find_one(
            {"competition_id": entry["competition_id"]},
            {"_id": 0, "name": 1, "status": 1, "end_time": 1, "prize_pool_sol": 1}
        )
        if comp:
            entry["competition_name"] = comp.get("name")
            entry["competition_status"] = comp.get("status")
            entry["competition_end_time"] = comp.get("end_time")
            entry["prize_pool_sol"] = comp.get("prize_pool_sol")
    
    return {
        "entries": entries,
        "count": len(entries)
    }


# ============== Leaderboard ==============

@router.get("/leaderboard/{competition_id}")
async def get_competition_leaderboard(
    competition_id: str,
    limit: int = Query(50, ge=1, le=100)
):
    """Get competition leaderboard."""
    competition = await db.trading_competitions.find_one(
        {"competition_id": competition_id},
        {"_id": 0}
    )
    
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    # Get all entries sorted by PnL
    entries = await db.competition_entries.find(
        {"competition_id": competition_id},
        {"_id": 0}
    ).sort("total_pnl_sol", -1).limit(limit).to_list(limit)
    
    # Add ranks
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1
        
        # Calculate prize for top 10
        if i < 10:
            prize_percent = get_prize_percent(i + 1, competition.get("prize_distribution", {}))
            entry["potential_prize_sol"] = competition.get("prize_pool_sol", 0) * prize_percent / 100
    
    return {
        "competition": {
            "competition_id": competition_id,
            "name": competition.get("name"),
            "status": competition.get("status"),
            "prize_pool_sol": competition.get("prize_pool_sol"),
            "end_time": competition.get("end_time")
        },
        "leaderboard": entries,
        "total_participants": await db.competition_entries.count_documents({"competition_id": competition_id})
    }


def get_prize_percent(rank: int, distribution: Dict[str, float]) -> float:
    """Get prize percentage for a rank."""
    if str(rank) in distribution:
        return distribution[str(rank)]
    if rank >= 6 and rank <= 10 and "6-10" in distribution:
        return distribution["6-10"] / 5  # Split among 6-10
    return 0


# ============== Stats & Updates ==============

@router.post("/update-stats/{competition_id}/{wallet_address}")
async def update_competition_stats(competition_id: str, wallet_address: str):
    """Update a participant's competition stats based on their trades."""
    entry = await db.competition_entries.find_one({
        "competition_id": competition_id,
        "wallet_address": wallet_address
    })
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    competition = await db.trading_competitions.find_one({"competition_id": competition_id})
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    # Get trades during competition period
    start_time = competition.get("start_time")
    end_time = competition.get("end_time")
    
    # Query closed positions during competition
    positions = await db.ai_trader_positions.find({
        "wallet_address": wallet_address,
        "status": {"$in": ["closed_profit", "closed_loss"]},
        "closed_at": {"$gte": start_time, "$lte": end_time}
    }).to_list(1000)
    
    # Calculate stats
    total_trades = len(positions)
    winning_trades = len([p for p in positions if p.get("status") == "closed_profit"])
    total_pnl_sol = sum(p.get("pnl_sol", 0) for p in positions)
    pnl_percents = [p.get("pnl_percent", 0) for p in positions if p.get("pnl_percent")]
    best_trade = max(pnl_percents) if pnl_percents else 0
    
    # Get current portfolio value
    current_portfolio = await calculate_portfolio_value(wallet_address)
    starting_portfolio = entry.get("starting_portfolio_sol", 0)
    
    if starting_portfolio > 0:
        total_pnl_percent = ((current_portfolio - starting_portfolio) / starting_portfolio) * 100
    else:
        total_pnl_percent = 0
    
    # Update entry
    await db.competition_entries.update_one(
        {"_id": entry["_id"]},
        {"$set": {
            "current_portfolio_sol": current_portfolio,
            "total_pnl_sol": round(total_pnl_sol, 6),
            "total_pnl_percent": round(total_pnl_percent, 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "best_trade_pnl_percent": round(best_trade, 2),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "success": True,
        "stats": {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "total_pnl_sol": round(total_pnl_sol, 6),
            "total_pnl_percent": round(total_pnl_percent, 2),
            "best_trade_pnl_percent": round(best_trade, 2)
        }
    }


async def calculate_portfolio_value(wallet_address: str) -> float:
    """Calculate total portfolio value for a wallet."""
    # Get open positions value
    positions = await db.ai_trader_positions.find({
        "wallet_address": wallet_address,
        "status": "open"
    }).to_list(100)
    
    total_value = sum(p.get("current_value_sol", p.get("amount_sol", 0)) for p in positions)
    
    return round(total_value, 6)


# ============== End Competition & Distribute Prizes ==============

@router.post("/end/{competition_id}")
async def end_competition(competition_id: str):
    """End a competition and calculate final rankings."""
    competition = await db.trading_competitions.find_one({"competition_id": competition_id})
    
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    if competition["status"] == "ended":
        raise HTTPException(status_code=400, detail="Competition already ended")
    
    # Update all participant stats first
    entries = await db.competition_entries.find({"competition_id": competition_id}).to_list(1000)
    
    for entry in entries:
        try:
            await update_competition_stats(competition_id, entry["wallet_address"])
        except Exception as e:
            logger.warning(f"Failed to update stats for {entry['wallet_address']}: {e}")
    
    # Get final rankings
    final_entries = await db.competition_entries.find(
        {"competition_id": competition_id},
        {"_id": 0}
    ).sort("total_pnl_sol", -1).to_list(1000)
    
    prize_pool = competition.get("prize_pool_sol", 0)
    distribution = competition.get("prize_distribution", {})
    
    # Assign ranks and prizes
    winners = []
    for i, entry in enumerate(final_entries):
        rank = i + 1
        prize_percent = get_prize_percent(rank, distribution)
        prize_sol = prize_pool * prize_percent / 100
        
        # Update entry with final rank and prize
        await db.competition_entries.update_one(
            {"entry_id": entry["entry_id"]},
            {"$set": {
                "rank": rank,
                "prize_won_sol": round(prize_sol, 6)
            }}
        )
        
        if prize_sol > 0:
            winners.append({
                "rank": rank,
                "wallet_address": entry["wallet_address"],
                "display_name": entry["display_name"],
                "total_pnl_sol": entry.get("total_pnl_sol", 0),
                "prize_sol": round(prize_sol, 6)
            })
    
    # Update competition status
    await db.trading_competitions.update_one(
        {"competition_id": competition_id},
        {"$set": {
            "status": "ended",
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "winners": winners[:10]
        }}
    )
    
    return {
        "success": True,
        "message": f"Competition ended with {len(final_entries)} participants",
        "winners": winners[:10],
        "total_prize_distributed_sol": round(sum(w["prize_sol"] for w in winners), 6)
    }


@router.get("/stats/{wallet_address}")
async def get_competition_stats(wallet_address: str):
    """Get a user's competition statistics."""
    entries = await db.competition_entries.find(
        {"wallet_address": wallet_address},
        {"_id": 0}
    ).to_list(100)
    
    total_competitions = len(entries)
    total_prize_won = sum(e.get("prize_won_sol", 0) for e in entries)
    best_rank = min([e.get("rank", 999) for e in entries if e.get("rank", 0) > 0], default=0)
    podium_finishes = len([e for e in entries if e.get("rank", 999) <= 3])
    top_10_finishes = len([e for e in entries if e.get("rank", 999) <= 10])
    
    return {
        "wallet_address": wallet_address,
        "total_competitions": total_competitions,
        "total_prize_won_sol": round(total_prize_won, 6),
        "best_rank": best_rank if best_rank < 999 else None,
        "podium_finishes": podium_finishes,
        "top_10_finishes": top_10_finishes,
        "avg_pnl_percent": round(
            sum(e.get("total_pnl_percent", 0) for e in entries) / total_competitions, 2
        ) if total_competitions > 0 else 0
    }
