"""
Multi-Chain Copy Trading System
Extends copy trading to support EVM chains (Ethereum, Base, Arbitrum)

Features:
- Cross-chain trader profiles
- Chain-specific copy settings
- Multi-chain trade copying
- Unified leaderboard across chains
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
router = APIRouter(prefix="/multichain-copy", tags=["Multi-Chain Copy Trading"])


# Supported chains configuration
SUPPORTED_CHAINS = {
    "solana": {
        "name": "Solana",
        "symbol": "SOL",
        "chain_id": None,
        "explorer": "https://solscan.io",
        "color": "#9945FF"
    },
    "ethereum": {
        "name": "Ethereum",
        "symbol": "ETH",
        "chain_id": 1,
        "explorer": "https://etherscan.io",
        "color": "#627EEA"
    },
    "base": {
        "name": "Base",
        "symbol": "ETH",
        "chain_id": 8453,
        "explorer": "https://basescan.org",
        "color": "#0052FF"
    },
    "arbitrum": {
        "name": "Arbitrum",
        "symbol": "ETH",
        "chain_id": 42161,
        "explorer": "https://arbiscan.io",
        "color": "#28A0F0"
    }
}


# ============== Models ==============

class MultiChainWallets(BaseModel):
    """User's wallets across multiple chains"""
    user_id: str
    solana_address: Optional[str] = None
    ethereum_address: Optional[str] = None
    primary_chain: str = "solana"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChainCopySettings(BaseModel):
    """Copy trading settings for a specific chain"""
    chain: str
    enabled: bool = True
    copy_percentage: float = Field(default=50.0, ge=10.0, le=100.0)
    max_position_native: float = Field(default=0.1, ge=0.01, le=10.0)  # In chain's native token
    auto_copy: bool = True


class MultiChainFollowRequest(BaseModel):
    """Request to follow a trader with multi-chain settings"""
    follower_user_id: str
    trader_user_id: str
    chain_settings: List[ChainCopySettings]


# ============== Wallet Management ==============

@router.get("/supported-chains")
async def get_supported_chains():
    """Get list of supported chains for copy trading."""
    return {
        "chains": SUPPORTED_CHAINS,
        "default_chain": "solana"
    }


@router.post("/wallets/link")
async def link_wallets(
    solana_address: Optional[str] = None,
    ethereum_address: Optional[str] = None,
    primary_chain: str = Query("solana", regex="^(solana|ethereum|base|arbitrum)$")
):
    """Link multiple chain wallets to a single user profile."""
    if not solana_address and not ethereum_address:
        raise HTTPException(status_code=400, detail="At least one wallet address required")
    
    # Generate user ID based on primary wallet
    primary_address = solana_address if primary_chain == "solana" else ethereum_address
    if not primary_address:
        primary_address = solana_address or ethereum_address
    
    user_id = f"user_{primary_address[:8]}"
    
    # Check if wallets are already linked to another user
    existing_solana = None
    existing_evm = None
    
    if solana_address:
        existing_solana = await db.multichain_wallets.find_one({
            "solana_address": solana_address,
            "user_id": {"$ne": user_id}
        })
    
    if ethereum_address:
        existing_evm = await db.multichain_wallets.find_one({
            "ethereum_address": ethereum_address,
            "user_id": {"$ne": user_id}
        })
    
    if existing_solana:
        raise HTTPException(status_code=400, detail="Solana wallet already linked to another user")
    if existing_evm:
        raise HTTPException(status_code=400, detail="EVM wallet already linked to another user")
    
    # Upsert wallet record
    wallet_doc = {
        "user_id": user_id,
        "solana_address": solana_address,
        "ethereum_address": ethereum_address,
        "primary_chain": primary_chain,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.multichain_wallets.update_one(
        {"user_id": user_id},
        {
            "$set": wallet_doc,
            "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return {
        "success": True,
        "user_id": user_id,
        "wallets": {
            "solana": solana_address,
            "ethereum": ethereum_address
        },
        "primary_chain": primary_chain
    }


@router.get("/wallets/{address}")
async def get_linked_wallets(address: str):
    """Get all linked wallets for an address."""
    # Search by either Solana or EVM address
    wallet = await db.multichain_wallets.find_one({
        "$or": [
            {"solana_address": address},
            {"ethereum_address": address}
        ]
    }, {"_id": 0})
    
    if not wallet:
        return {
            "user_id": None,
            "wallets": {"solana": None, "ethereum": None},
            "linked": False
        }
    
    return {
        "user_id": wallet.get("user_id"),
        "wallets": {
            "solana": wallet.get("solana_address"),
            "ethereum": wallet.get("ethereum_address")
        },
        "primary_chain": wallet.get("primary_chain", "solana"),
        "linked": True
    }


# ============== Multi-Chain Following ==============

@router.post("/follow")
async def follow_multichain(request: MultiChainFollowRequest):
    """Follow a trader with multi-chain settings."""
    # Get trader's wallet info
    trader_wallets = await db.multichain_wallets.find_one({"user_id": request.trader_user_id})
    
    if not trader_wallets:
        raise HTTPException(status_code=404, detail="Trader not found")
    
    # Check if trader has copy trading enabled
    trader_profile = await db.trader_profiles.find_one({
        "$or": [
            {"wallet_address": trader_wallets.get("solana_address")},
            {"wallet_address": trader_wallets.get("ethereum_address")}
        ]
    })
    
    if not trader_profile or not trader_profile.get("copy_trading_enabled"):
        raise HTTPException(status_code=400, detail="Trader has not enabled copy trading")
    
    # Create multi-chain follow relationship
    follow_id = str(uuid.uuid4())[:8]
    follow_doc = {
        "follow_id": follow_id,
        "follower_user_id": request.follower_user_id,
        "trader_user_id": request.trader_user_id,
        "chain_settings": [s.dict() for s in request.chain_settings],
        "active": True,
        "trades_copied": 0,
        "total_pnl_usd": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Check for existing follow
    existing = await db.multichain_follows.find_one({
        "follower_user_id": request.follower_user_id,
        "trader_user_id": request.trader_user_id
    })
    
    if existing:
        await db.multichain_follows.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "chain_settings": [s.dict() for s in request.chain_settings],
                "active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return {"success": True, "follow_id": existing.get("follow_id"), "message": "Follow settings updated"}
    
    await db.multichain_follows.insert_one(follow_doc)
    
    return {
        "success": True,
        "follow_id": follow_id,
        "message": "Successfully following trader across selected chains"
    }


@router.get("/following/{user_id}")
async def get_multichain_following(user_id: str):
    """Get traders being followed with multi-chain settings."""
    follows = await db.multichain_follows.find(
        {"follower_user_id": user_id, "active": True},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with trader info
    for follow in follows:
        trader_wallets = await db.multichain_wallets.find_one(
            {"user_id": follow["trader_user_id"]},
            {"_id": 0}
        )
        if trader_wallets:
            follow["trader_wallets"] = {
                "solana": trader_wallets.get("solana_address"),
                "ethereum": trader_wallets.get("ethereum_address")
            }
        
        # Get trader profile
        trader_profile = await db.trader_profiles.find_one(
            {"wallet_address": trader_wallets.get("solana_address") or trader_wallets.get("ethereum_address")},
            {"_id": 0, "display_name": 1, "performance_fee_percent": 1}
        )
        if trader_profile:
            follow["trader_display_name"] = trader_profile.get("display_name")
            follow["trader_fee_percent"] = trader_profile.get("performance_fee_percent", 10)
    
    return {
        "following": follows,
        "count": len(follows)
    }


@router.put("/chain-settings")
async def update_chain_settings(
    follower_user_id: str,
    trader_user_id: str,
    chain: str = Query(..., regex="^(solana|ethereum|base|arbitrum)$"),
    enabled: Optional[bool] = None,
    copy_percentage: Optional[float] = None,
    max_position_native: Optional[float] = None,
    auto_copy: Optional[bool] = None
):
    """Update copy settings for a specific chain."""
    follow = await db.multichain_follows.find_one({
        "follower_user_id": follower_user_id,
        "trader_user_id": trader_user_id,
        "active": True
    })
    
    if not follow:
        raise HTTPException(status_code=404, detail="Follow relationship not found")
    
    # Find and update the chain settings
    chain_settings = follow.get("chain_settings", [])
    chain_found = False
    
    for settings in chain_settings:
        if settings.get("chain") == chain:
            if enabled is not None:
                settings["enabled"] = enabled
            if copy_percentage is not None:
                settings["copy_percentage"] = max(10, min(100, copy_percentage))
            if max_position_native is not None:
                settings["max_position_native"] = max(0.01, min(10, max_position_native))
            if auto_copy is not None:
                settings["auto_copy"] = auto_copy
            chain_found = True
            break
    
    if not chain_found:
        # Add new chain settings
        chain_settings.append({
            "chain": chain,
            "enabled": enabled if enabled is not None else True,
            "copy_percentage": copy_percentage if copy_percentage is not None else 50,
            "max_position_native": max_position_native if max_position_native is not None else 0.1,
            "auto_copy": auto_copy if auto_copy is not None else True
        })
    
    await db.multichain_follows.update_one(
        {"_id": follow["_id"]},
        {"$set": {
            "chain_settings": chain_settings,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "success": True,
        "chain": chain,
        "settings": next((s for s in chain_settings if s["chain"] == chain), None)
    }


# ============== Multi-Chain Leaderboard ==============

@router.get("/leaderboard")
async def get_multichain_leaderboard(
    chain: Optional[str] = Query(None, regex="^(solana|ethereum|base|arbitrum|all)$"),
    period: str = Query("7d", regex="^(24h|7d|30d|all)$"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get unified leaderboard across all chains or filtered by chain."""
    # Calculate period start
    now = datetime.now(timezone.utc)
    if period == "24h":
        period_start = now - timedelta(hours=24)
    elif period == "7d":
        period_start = now - timedelta(days=7)
    elif period == "30d":
        period_start = now - timedelta(days=30)
    else:
        period_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    
    period_start_str = period_start.isoformat()
    
    # Build match condition
    match_condition = {
        "status": {"$in": ["closed_profit", "closed_loss"]},
        "closed_at": {"$gte": period_start_str}
    }
    
    if chain and chain != "all":
        match_condition["chain"] = chain
    
    # Aggregate performance across all chains
    pipeline = [
        {"$match": match_condition},
        {"$group": {
            "_id": "$wallet_address",
            "total_trades": {"$sum": 1},
            "winning_trades": {"$sum": {"$cond": [{"$eq": ["$status", "closed_profit"]}, 1, 0]}},
            "total_pnl_usd": {"$sum": {"$ifNull": ["$pnl_usd", 0]}},
            "chains_traded": {"$addToSet": "$chain"}
        }},
        {"$addFields": {
            "win_rate": {"$multiply": [{"$divide": ["$winning_trades", "$total_trades"]}, 100]}
        }},
        {"$sort": {"total_pnl_usd": -1}},
        {"$limit": limit}
    ]
    
    results = await db.ai_trader_positions.aggregate(pipeline).to_list(limit)
    
    leaderboard = []
    for i, trader in enumerate(results):
        # Get profile info
        profile = await db.trader_profiles.find_one(
            {"wallet_address": trader["_id"]},
            {"_id": 0, "display_name": 1, "copy_trading_enabled": 1, "performance_fee_percent": 1}
        )
        
        # Get linked wallets
        wallets = await db.multichain_wallets.find_one({
            "$or": [
                {"solana_address": trader["_id"]},
                {"ethereum_address": trader["_id"]}
            ]
        }, {"_id": 0})
        
        leaderboard.append({
            "rank": i + 1,
            "wallet_address": trader["_id"],
            "user_id": wallets.get("user_id") if wallets else None,
            "display_name": profile.get("display_name", f"Trader_{trader['_id'][:6]}") if profile else f"Trader_{trader['_id'][:6]}",
            "copy_trading_enabled": profile.get("copy_trading_enabled", False) if profile else False,
            "performance_fee_percent": profile.get("performance_fee_percent", 10) if profile else 10,
            "total_trades": trader["total_trades"],
            "winning_trades": trader["winning_trades"],
            "win_rate": round(trader["win_rate"], 1),
            "total_pnl_usd": round(trader["total_pnl_usd"], 2),
            "chains_traded": trader.get("chains_traded", ["solana"])
        })
    
    return {
        "chain_filter": chain or "all",
        "period": period,
        "leaderboard": leaderboard,
        "total_traders": len(leaderboard)
    }


# ============== Cross-Chain Trade Copying ==============

async def copy_trade_multichain(
    trader_user_id: str,
    trade_info: Dict[str, Any],
    chain: str
) -> List[Dict[str, Any]]:
    """
    Copy a trade to followers across the appropriate chain.
    """
    # Get all active followers for this trader
    followers = await db.multichain_follows.find({
        "trader_user_id": trader_user_id,
        "active": True
    }).to_list(100)
    
    copied_trades = []
    
    for follow in followers:
        # Check if this chain is enabled for copying
        chain_settings = next(
            (s for s in follow.get("chain_settings", []) if s.get("chain") == chain and s.get("enabled")),
            None
        )
        
        if not chain_settings or not chain_settings.get("auto_copy"):
            continue
        
        # Calculate position size
        trader_position = trade_info.get("amount_native", 0)
        copy_percentage = chain_settings.get("copy_percentage", 50) / 100
        max_position = chain_settings.get("max_position_native", 0.1)
        
        copied_position = min(trader_position * copy_percentage, max_position)
        
        if copied_position < 0.001:  # Skip tiny positions
            continue
        
        # Get follower's wallet for this chain
        follower_wallets = await db.multichain_wallets.find_one(
            {"user_id": follow["follower_user_id"]},
            {"_id": 0}
        )
        
        if not follower_wallets:
            continue
        
        follower_address = (
            follower_wallets.get("solana_address") if chain == "solana"
            else follower_wallets.get("ethereum_address")
        )
        
        if not follower_address:
            continue
        
        # Create copied trade record
        copy_trade_id = str(uuid.uuid4())[:8]
        copied_trade = {
            "copy_trade_id": copy_trade_id,
            "original_trade_id": trade_info.get("position_id"),
            "chain": chain,
            "follower_user_id": follow["follower_user_id"],
            "follower_address": follower_address,
            "trader_user_id": trader_user_id,
            "token_symbol": trade_info.get("token_symbol"),
            "token_address": trade_info.get("token_address"),
            "trade_type": trade_info.get("trade_type", "buy"),
            "original_amount": trader_position,
            "copied_amount": copied_position,
            "entry_price": trade_info.get("entry_price"),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.multichain_copied_trades.insert_one(copied_trade)
        
        # Update stats
        await db.multichain_follows.update_one(
            {"_id": follow["_id"]},
            {"$inc": {"trades_copied": 1}}
        )
        
        copied_trades.append(copied_trade)
        logger.info(f"Copied {chain} trade {copy_trade_id} to {follower_address[:8]}...")
    
    return copied_trades


@router.get("/copied-trades/{user_id}")
async def get_multichain_copied_trades(
    user_id: str,
    chain: Optional[str] = Query(None, regex="^(solana|ethereum|base|arbitrum)$"),
    limit: int = Query(50, ge=1, le=200)
):
    """Get copied trades for a user, optionally filtered by chain."""
    query = {"follower_user_id": user_id}
    if chain:
        query["chain"] = chain
    
    trades = await db.multichain_copied_trades.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Group by chain
    by_chain = {}
    for trade in trades:
        c = trade.get("chain", "solana")
        if c not in by_chain:
            by_chain[c] = []
        by_chain[c].append(trade)
    
    return {
        "copied_trades": trades,
        "by_chain": by_chain,
        "count": len(trades)
    }


@router.get("/stats/{user_id}")
async def get_multichain_copy_stats(user_id: str):
    """Get multi-chain copy trading statistics for a user."""
    # Get follows
    following = await db.multichain_follows.find(
        {"follower_user_id": user_id, "active": True}
    ).to_list(100)
    
    # Get copied trades stats by chain
    pipeline = [
        {"$match": {"follower_user_id": user_id}},
        {"$group": {
            "_id": "$chain",
            "total_trades": {"$sum": 1},
            "total_pnl": {"$sum": {"$ifNull": ["$pnl_native", 0]}}
        }}
    ]
    
    chain_stats = await db.multichain_copied_trades.aggregate(pipeline).to_list(10)
    
    # Format stats
    stats_by_chain = {}
    for stat in chain_stats:
        chain_info = SUPPORTED_CHAINS.get(stat["_id"], {})
        stats_by_chain[stat["_id"]] = {
            "chain_name": chain_info.get("name", stat["_id"]),
            "total_trades": stat["total_trades"],
            "total_pnl_native": round(stat["total_pnl"], 6),
            "symbol": chain_info.get("symbol", "?")
        }
    
    return {
        "user_id": user_id,
        "traders_following": len(following),
        "chains_active": list(stats_by_chain.keys()),
        "stats_by_chain": stats_by_chain,
        "total_trades_copied": sum(s["total_trades"] for s in stats_by_chain.values())
    }
