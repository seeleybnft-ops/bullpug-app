"""Watchlist Router - Track favorite coins and their price movements."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone
import logging
import httpx

from utils.database import db

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
logger = logging.getLogger(__name__)


class WatchlistItem(BaseModel):
    symbol: str
    name: str
    contract_address: Optional[str] = None
    dex_url: Optional[str] = None
    platform: str = "Solana"
    added_price: float = 0
    added_at: Optional[str] = None


class AddToWatchlistRequest(BaseModel):
    wallet_address: str
    coin: WatchlistItem


class RemoveFromWatchlistRequest(BaseModel):
    wallet_address: str
    symbol: str


async def fetch_current_price(symbol: str, contract_address: str = None) -> Optional[float]:
    """Fetch current price for a coin from DexScreener."""
    try:
        search_term = contract_address if contract_address else symbol
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.dexscreener.com/latest/dex/search",
                params={"q": search_term}
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    # Get the highest liquidity pair
                    best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                    return float(best_pair.get("priceUsd", 0) or 0)
    except Exception as e:
        logger.warning(f"Failed to fetch price for {symbol}: {e}")
    return None


@router.get("/{wallet_address}")
async def get_watchlist(wallet_address: str):
    """Get user's watchlist with current prices."""
    try:
        # Get watchlist from database
        watchlist_doc = await db.watchlists.find_one(
            {"wallet_address": wallet_address},
            {"_id": 0}
        )
        
        if not watchlist_doc or not watchlist_doc.get("coins"):
            return {
                "wallet_address": wallet_address,
                "coins": [],
                "total_items": 0
            }
        
        coins = watchlist_doc.get("coins", [])
        enriched_coins = []
        
        # Fetch current prices for all coins
        for coin in coins:
            current_price = await fetch_current_price(
                coin.get("symbol"), 
                coin.get("contract_address")
            )
            
            added_price = coin.get("added_price", 0)
            price_change = 0
            price_change_pct = 0
            
            if current_price and added_price > 0:
                price_change = current_price - added_price
                price_change_pct = ((current_price - added_price) / added_price) * 100
            
            enriched_coins.append({
                **coin,
                "current_price": current_price or coin.get("added_price", 0),
                "price_change": price_change,
                "price_change_pct": price_change_pct,
                "is_profitable": price_change > 0
            })
        
        # Sort by profit percentage (descending)
        enriched_coins.sort(key=lambda x: x.get("price_change_pct", 0), reverse=True)
        
        return {
            "wallet_address": wallet_address,
            "coins": enriched_coins,
            "total_items": len(enriched_coins),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add")
async def add_to_watchlist(request: AddToWatchlistRequest):
    """Add a coin to user's watchlist."""
    try:
        wallet_address = request.wallet_address
        coin = request.coin.dict()
        
        # Set added timestamp
        coin["added_at"] = datetime.now(timezone.utc).isoformat()
        
        # Get current price if not provided
        if not coin.get("added_price") or coin["added_price"] == 0:
            current_price = await fetch_current_price(
                coin.get("symbol"),
                coin.get("contract_address")
            )
            if current_price:
                coin["added_price"] = current_price
        
        # Check if watchlist exists
        existing = await db.watchlists.find_one({"wallet_address": wallet_address})
        
        if existing:
            # Check if coin already in watchlist
            existing_coins = existing.get("coins", [])
            for existing_coin in existing_coins:
                if existing_coin.get("symbol") == coin.get("symbol"):
                    return {
                        "success": False,
                        "message": f"{coin['symbol']} is already in your watchlist"
                    }
            
            # Add coin to existing watchlist
            await db.watchlists.update_one(
                {"wallet_address": wallet_address},
                {
                    "$push": {"coins": coin},
                    "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
                }
            )
        else:
            # Create new watchlist
            await db.watchlists.insert_one({
                "wallet_address": wallet_address,
                "coins": [coin],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        
        return {
            "success": True,
            "message": f"{coin['symbol']} added to watchlist",
            "coin": coin
        }
        
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remove")
async def remove_from_watchlist(request: RemoveFromWatchlistRequest):
    """Remove a coin from user's watchlist."""
    try:
        wallet_address = request.wallet_address
        symbol = request.symbol.upper()
        
        result = await db.watchlists.update_one(
            {"wallet_address": wallet_address},
            {
                "$pull": {"coins": {"symbol": symbol}},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        if result.modified_count > 0:
            return {
                "success": True,
                "message": f"{symbol} removed from watchlist"
            }
        else:
            return {
                "success": False,
                "message": f"{symbol} not found in watchlist"
            }
        
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{wallet_address}/clear")
async def clear_watchlist(wallet_address: str):
    """Clear all coins from user's watchlist."""
    try:
        await db.watchlists.update_one(
            {"wallet_address": wallet_address},
            {
                "$set": {
                    "coins": [],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Watchlist cleared"
        }
        
    except Exception as e:
        logger.error(f"Error clearing watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))
