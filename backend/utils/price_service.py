"""Price fetching utilities with DexScreener as primary source and CoinGecko fallback.

DexScreener API doesn't require API keys and has generous rate limits (60-300 req/sec).
CoinGecko is used as fallback but often rate-limited on the free tier.
"""

import httpx
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# Unified price cache
_price_cache: Dict[str, Dict] = {}
CACHE_TTL_SECONDS = 60  # Cache prices for 60 seconds

# Known major coins - CoinGecko ID mapping for fallback
COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "DOGE": "dogecoin", "SHIB": "shiba-inu", "PEPE": "pepe",
    "BONK": "bonk", "WIF": "dogwifhat", "MATIC": "matic-network",
    "AVAX": "avalanche-2", "ADA": "cardano", "DOT": "polkadot",
    "LINK": "chainlink", "UNI": "uniswap", "BNB": "binancecoin",
    "XRP": "ripple", "ARB": "arbitrum", "OP": "optimism",
}

# DexScreener pair addresses for major tokens (Solana mainnet pairs)
DEXSCREENER_PAIRS = {
    "SOL": "So11111111111111111111111111111111111111112",  # Native SOL
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
}


async def get_dexscreener_prices(symbols: List[str]) -> Dict[str, Dict]:
    """Fetch prices from DexScreener API (primary source - no rate limits)."""
    prices = {}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # For Solana/memecoin prices, use DexScreener search
            for symbol in symbols:
                cache_key = f"dexscreener_{symbol.upper()}"
                
                # Check cache first
                if cache_key in _price_cache:
                    cached = _price_cache[cache_key]
                    age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
                    if age < CACHE_TTL_SECONDS:
                        prices[symbol.upper()] = cached["data"]
                        continue
                
                # Search DexScreener
                try:
                    response = await client.get(
                        f"https://api.dexscreener.com/latest/dex/search?q={symbol}",
                    )
                    if response.status_code == 200:
                        data = response.json()
                        pairs = data.get("pairs", [])
                        
                        # Find the best pair (highest liquidity)
                        if pairs:
                            # Filter to mainnet pairs with good liquidity
                            valid_pairs = [p for p in pairs 
                                         if p.get("liquidity", {}).get("usd", 0) > 10000
                                         and p.get("chainId") in ["solana", "ethereum", "base"]]
                            
                            if valid_pairs:
                                # Sort by liquidity
                                best = sorted(valid_pairs, 
                                            key=lambda x: x.get("liquidity", {}).get("usd", 0), 
                                            reverse=True)[0]
                                
                                price_data = {
                                    "usd": float(best.get("priceUsd", 0)),
                                    "change_24h": float(best.get("priceChange", {}).get("h24", 0)),
                                    "volume_24h": float(best.get("volume", {}).get("h24", 0)),
                                    "liquidity": float(best.get("liquidity", {}).get("usd", 0)),
                                    "source": "dexscreener"
                                }
                                prices[symbol.upper()] = price_data
                                
                                # Cache the result
                                _price_cache[cache_key] = {
                                    "data": price_data,
                                    "timestamp": datetime.now(timezone.utc)
                                }
                except Exception as e:
                    logger.warning(f"DexScreener error for {symbol}: {e}")
                    
    except Exception as e:
        logger.error(f"DexScreener batch error: {e}")
    
    return prices


async def get_coingecko_prices(symbols: List[str]) -> Dict[str, Dict]:
    """Fetch prices from CoinGecko API (fallback - may be rate limited)."""
    prices = {}
    
    # Map symbols to CoinGecko IDs
    coin_ids = []
    symbol_to_id = {}
    for symbol in symbols:
        coin_id = COINGECKO_IDS.get(symbol.upper(), symbol.lower())
        coin_ids.append(coin_id)
        symbol_to_id[coin_id] = symbol.upper()
    
    if not coin_ids:
        return prices
    
    cache_key = f"coingecko_{','.join(sorted(coin_ids))}"
    
    # Check cache first
    if cache_key in _price_cache:
        cached = _price_cache[cache_key]
        age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return cached["data"]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": ",".join(coin_ids),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true"
                }
            )
            
            if response.status_code == 429:
                logger.warning("CoinGecko rate limited")
                # Return cached data if available
                if cache_key in _price_cache:
                    return _price_cache[cache_key]["data"]
                return prices
            
            if response.status_code == 200:
                data = response.json()
                for coin_id, values in data.items():
                    symbol = symbol_to_id.get(coin_id, coin_id.upper())
                    prices[symbol] = {
                        "usd": values.get("usd", 0),
                        "change_24h": values.get("usd_24h_change", 0),
                        "volume_24h": values.get("usd_24h_vol", 0),
                        "source": "coingecko"
                    }
                
                # Cache the result
                _price_cache[cache_key] = {
                    "data": prices,
                    "timestamp": datetime.now(timezone.utc)
                }
                
    except Exception as e:
        logger.warning(f"CoinGecko error: {e}")
        if cache_key in _price_cache:
            return _price_cache[cache_key]["data"]
    
    return prices


async def get_eth_price() -> float:
    """Get ETH price using DexScreener first, then CoinGecko fallback."""
    cache_key = "eth_price_unified"
    
    # Check cache
    if cache_key in _price_cache:
        cached = _price_cache[cache_key]
        age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return cached["price"]
    
    # Try DexScreener first (search for WETH pairs)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.dexscreener.com/latest/dex/tokens/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH on Ethereum
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    # Get price from highest liquidity pair
                    best = max(pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0))
                    price = float(best.get("priceUsd", 0))
                    if price > 0:
                        _price_cache[cache_key] = {"price": price, "timestamp": datetime.now(timezone.utc)}
                        return price
    except Exception as e:
        logger.warning(f"DexScreener ETH price error: {e}")
    
    # Fallback to CoinGecko
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "ethereum", "vs_currencies": "usd"}
            )
            if response.status_code == 200:
                data = response.json()
                price = data.get("ethereum", {}).get("usd", 0)
                if price > 0:
                    _price_cache[cache_key] = {"price": price, "timestamp": datetime.now(timezone.utc)}
                    return price
    except Exception as e:
        logger.warning(f"CoinGecko ETH price error: {e}")
    
    # Return cached or fallback
    if cache_key in _price_cache:
        return _price_cache[cache_key]["price"]
    return 3500  # Fallback


async def get_sol_price() -> float:
    """Get SOL price using DexScreener first, then CoinGecko fallback."""
    cache_key = "sol_price_unified"
    
    # Check cache
    if cache_key in _price_cache:
        cached = _price_cache[cache_key]
        age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return cached["price"]
    
    # Try DexScreener first
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"  # Native SOL
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    # Get price from highest liquidity pair
                    best = max(pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0))
                    price = float(best.get("priceUsd", 0))
                    if price > 0:
                        _price_cache[cache_key] = {"price": price, "timestamp": datetime.now(timezone.utc)}
                        return price
    except Exception as e:
        logger.warning(f"DexScreener SOL price error: {e}")
    
    # Fallback to CoinGecko
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "solana", "vs_currencies": "usd"}
            )
            if response.status_code == 200:
                data = response.json()
                price = data.get("solana", {}).get("usd", 0)
                if price > 0:
                    _price_cache[cache_key] = {"price": price, "timestamp": datetime.now(timezone.utc)}
                    return price
    except Exception as e:
        logger.warning(f"CoinGecko SOL price error: {e}")
    
    # Return cached or fallback
    if cache_key in _price_cache:
        return _price_cache[cache_key]["price"]
    return 200  # Fallback


async def get_major_prices() -> Dict[str, Dict]:
    """Get prices for major assets (ETH, SOL) using unified approach."""
    eth_price = await get_eth_price()
    sol_price = await get_sol_price()
    
    return {
        "ETH": {"usd": eth_price, "symbol": "ETH", "icon": "⟠", "source": "dexscreener/coingecko"},
        "SOL": {"usd": sol_price, "symbol": "SOL", "icon": "◎", "source": "dexscreener/coingecko"},
        "last_updated": datetime.now(timezone.utc).isoformat()
    }


def clear_price_cache():
    """Clear the price cache (useful for testing)."""
    global _price_cache
    _price_cache = {}
