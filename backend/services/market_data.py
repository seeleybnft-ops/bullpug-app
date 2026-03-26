"""
Multi-source market data service.

Primary: Jupiter (quote API) for pricing, CoinGecko for discovery.
Fallback: DexScreener (with rate limit protection + in-memory cache).

This ensures the bot never goes blind due to a single API rate limit.
"""

import httpx
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# In-memory cache for DexScreener responses (avoids hammering the API)
_dexscreener_cache: Dict[str, Tuple[float, Any]] = {}  # key -> (timestamp, data)
DEXSCREENER_CACHE_TTL = 300  # 5 minutes
DEXSCREENER_BACKOFF_UNTIL = 0.0  # Global backoff timestamp

# Known CoinGecko IDs for our token list
COINGECKO_IDS = {
    "JUP": "jupiter-exchange-solana",
    "BONK": "bonk",
    "WIF": "dogwifcoin",
    "PYTH": "pyth-network",
    "RNDR": "render-token",
    "RAY": "raydium",
    "ORCA": "orca",
    "HNT": "helium",
    "JTO": "jito-governance-token",
    "TENSOR": "tensor",
    "DRIFT": "drift-protocol",
    "TRUMP": "official-trump",
    "PENGU": "pudgy-penguins",
    "POPCAT": "popcat",
    "FARTCOIN": "fartcoin",
    "MEW": "cat-in-a-dogs-world",
    "PIPPIN": "pippin",
}

# Reverse map: CoinGecko ID -> symbol
COINGECKO_ID_TO_SYMBOL = {v: k for k, v in COINGECKO_IDS.items()}

# CoinGecko batch cache (fetched once per scan cycle)
_coingecko_batch_cache: Dict[str, Tuple[float, Dict]] = {}  # symbol -> (timestamp, data)
COINGECKO_BATCH_CACHE_TTL = 600  # 10 minutes - avoid rate limits
_COINGECKO_BACKOFF_UNTIL = 0.0  # Shared CoinGecko rate limit backoff


async def prefetch_coingecko_batch(symbols: List[str] = None) -> Dict[str, Dict]:
    """
    Fetch market data for ALL known tokens from CoinGecko in a SINGLE API call.
    Caches results. Returns dict of symbol -> market data.
    """
    global _coingecko_batch_cache, _COINGECKO_BACKOFF_UNTIL

    # Check if cache is fresh
    if _coingecko_batch_cache:
        oldest = min(ts for ts, _ in _coingecko_batch_cache.values())
        if (time.time() - oldest) < COINGECKO_BATCH_CACHE_TTL:
            return {sym: data for sym, (ts, data) in _coingecko_batch_cache.items()}

    # Check CoinGecko backoff
    if time.time() < _COINGECKO_BACKOFF_UNTIL:
        logger.debug("CoinGecko in backoff — returning stale cache")
        return {sym: data for sym, (ts, data) in _coingecko_batch_cache.items()}

    # Build list of CoinGecko IDs to fetch
    if symbols:
        ids = [COINGECKO_IDS[s] for s in symbols if s in COINGECKO_IDS]
    else:
        ids = list(COINGECKO_IDS.values())

    if not ids:
        return {}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": ",".join(ids),
                    "order": "volume_desc",
                    "per_page": "50",
                    "page": "1",
                    "sparkline": "false",
                    "price_change_percentage": "1h,24h",
                }
            )

            if resp.status_code == 200:
                coins = resp.json()
                now = time.time()
                result = {}
                for coin in coins:
                    cg_id = coin.get("id", "")
                    symbol = COINGECKO_ID_TO_SYMBOL.get(cg_id, coin.get("symbol", "").upper())
                    data = {
                        "source": "coingecko",
                        "price_usd": float(coin.get("current_price", 0) or 0),
                        "volume_24h": float(coin.get("total_volume", 0) or 0),
                        "liquidity_usd": float(coin.get("market_cap", 0) or 0) * 0.01,
                        "price_change_1h": float(coin.get("price_change_percentage_1h_in_currency", 0) or 0),
                        "price_change_6h": 0,
                        "price_change_24h": float(coin.get("price_change_percentage_24h", 0) or 0),
                        "price_change_5m": 0,
                        "txns_1h": {"buys": 100, "sells": 100},
                        "pair_data": None,
                    }
                    _coingecko_batch_cache[symbol] = (now, data)
                    result[symbol] = data

                logger.info(f"CoinGecko batch: fetched {len(result)} tokens in 1 API call")
                return result
            elif resp.status_code == 429:
                _COINGECKO_BACKOFF_UNTIL = time.time() + 90  # 90-second backoff
                logger.warning("CoinGecko batch rate limited — 90s backoff")
            else:
                logger.warning(f"CoinGecko batch error: {resp.status_code}")
    except Exception as e:
        logger.warning(f"CoinGecko batch fetch failed: {e}")

    # Return stale cache if available
    return {sym: data for sym, (ts, data) in _coingecko_batch_cache.items()}


async def get_jupiter_price(input_mint: str, output_mint: str, amount_lamports: int = 1_000_000_000) -> Optional[Dict]:
    """
    Get token price using Jupiter Quote API.
    Returns price in USD by routing through SOL/USDC.
    amount_lamports: Amount of input token to quote (default 1 SOL = 1B lamports)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://lite-api.jup.ag/swap/v1/quote",
                params={
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": str(amount_lamports),
                    "slippageBps": "100",
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data
    except Exception as e:
        logger.debug(f"Jupiter quote failed: {e}")
    return None


async def get_token_price_jupiter(token_mint: str) -> Optional[float]:
    """
    Get token price in USD using Jupiter.
    Not currently used — CoinGecko provides better price data.
    Kept as potential fallback for future use.
    """
    return None


async def get_coingecko_market_data(symbols: List[str] = None, category: str = "solana-meme-coins") -> List[Dict]:
    """
    Fetch market data from CoinGecko for Solana tokens.
    Returns list of token data with prices, volume, and price changes.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if symbols:
                # Look up specific tokens by CoinGecko ID
                ids = [COINGECKO_IDS[s] for s in symbols if s in COINGECKO_IDS]
                if not ids:
                    return []
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "ids": ",".join(ids),
                        "order": "volume_desc",
                        "per_page": "50",
                        "page": "1",
                        "sparkline": "false",
                        "price_change_percentage": "1h,24h",
                    }
                )
            else:
                # Fetch by category
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "category": category,
                        "order": "volume_desc",
                        "per_page": "30",
                        "page": "1",
                        "sparkline": "false",
                        "price_change_percentage": "1h,24h",
                    }
                )

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                logger.warning("CoinGecko rate limited")
            else:
                logger.warning(f"CoinGecko error: {resp.status_code}")
    except Exception as e:
        logger.warning(f"CoinGecko fetch failed: {e}")
    return []


async def get_coingecko_token_mint(coingecko_id: str) -> Optional[str]:
    """Get the Solana mint address for a CoinGecko token."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/coins/{coingecko_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "false",
                    "community_data": "false",
                    "developer_data": "false",
                    "sparkline": "false",
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                platforms = data.get("detail_platforms", data.get("platforms", {}))
                solana_info = platforms.get("solana", {})
                if isinstance(solana_info, dict):
                    return solana_info.get("contract_address")
                elif isinstance(solana_info, str):
                    return solana_info
    except Exception as e:
        logger.debug(f"CoinGecko mint lookup failed for {coingecko_id}: {e}")
    return None


async def get_dexscreener_pair_data(token_mint: str) -> Optional[Dict]:
    """
    Get DexScreener pair data with caching and rate-limit backoff.
    Returns the best Solana pair or None.
    """
    global DEXSCREENER_BACKOFF_UNTIL

    # Check backoff
    if time.time() < DEXSCREENER_BACKOFF_UNTIL:
        logger.debug(f"DexScreener in backoff until {DEXSCREENER_BACKOFF_UNTIL - time.time():.0f}s")
        # Check cache
        cached = _dexscreener_cache.get(token_mint)
        if cached and (time.time() - cached[0]) < DEXSCREENER_CACHE_TTL * 2:  # Extend TTL during backoff
            return cached[1]
        return None

    # Check cache
    cached = _dexscreener_cache.get(token_mint)
    if cached and (time.time() - cached[0]) < DEXSCREENER_CACHE_TTL:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}")

            if resp.status_code == 429:
                DEXSCREENER_BACKOFF_UNTIL = time.time() + 120  # 2-minute backoff
                logger.warning("DexScreener 429 — entering 2-min backoff")
                return None

            if resp.status_code != 200:
                return None

            pairs = resp.json().get("pairs", [])
            solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
            if not solana_pairs:
                return None

            best_pair = max(solana_pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))

            # Cache the result
            _dexscreener_cache[token_mint] = (time.time(), best_pair)
            return best_pair

    except Exception as e:
        logger.debug(f"DexScreener lookup failed for {token_mint}: {e}")
    return None


async def get_token_market_data_multi(token_symbol: str, token_mint: str) -> Optional[Dict]:
    """
    Get comprehensive market data for a token from multiple sources.
    Returns a standardized dict with price, volume, liquidity, and price changes.
    
    Priority: DexScreener (cached) -> CoinGecko (batch cached) -> None
    """
    # Source 1: DexScreener (with cache + rate limit)
    dex_pair = await get_dexscreener_pair_data(token_mint)
    if dex_pair:
        return {
            "source": "dexscreener",
            "price_usd": float(dex_pair.get("priceUsd", 0) or 0),
            "volume_24h": float(dex_pair.get("volume", {}).get("h24", 0) or 0),
            "liquidity_usd": float(dex_pair.get("liquidity", {}).get("usd", 0) or 0),
            "price_change_1h": float(dex_pair.get("priceChange", {}).get("h1", 0) or 0),
            "price_change_6h": float(dex_pair.get("priceChange", {}).get("h6", 0) or 0),
            "price_change_24h": float(dex_pair.get("priceChange", {}).get("h24", 0) or 0),
            "price_change_5m": float(dex_pair.get("priceChange", {}).get("m5", 0) or 0),
            "txns_1h": dex_pair.get("txns", {}).get("h1", {}),
            "pair_data": dex_pair,
        }

    # Source 2: CoinGecko batch cache (prefetched at scan start)
    cached = _coingecko_batch_cache.get(token_symbol)
    if cached:
        ts, data = cached
        if (time.time() - ts) < COINGECKO_BATCH_CACHE_TTL * 2:  # Allow slightly stale
            return data

    # Source 3: If batch cache empty, try a fresh batch fetch
    if token_symbol in COINGECKO_IDS:
        batch = await prefetch_coingecko_batch()
        if token_symbol in batch:
            return batch[token_symbol]

    return None


async def discover_trending_solana_tokens(max_tokens: int = 10) -> List[Dict]:
    """
    Discover trending Solana tokens from CoinGecko.
    Returns tokens with momentum signals (positive price changes).
    """
    tokens = []
    
    try:
        # Fetch Solana meme coins (these are the most likely runners)
        meme_data = await get_coingecko_market_data(category="solana-meme-coins")
        
        # Also fetch trending coins from CoinGecko
        trending_data = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://api.coingecko.com/api/v3/search/trending")
                if resp.status_code == 200:
                    data = resp.json()
                    trending_coins = data.get("coins", [])
                    # Get IDs and fetch market data
                    trending_ids = [c["item"]["id"] for c in trending_coins[:10]]
                    if trending_ids:
                        resp2 = await client.get(
                            "https://api.coingecko.com/api/v3/coins/markets",
                            params={
                                "vs_currency": "usd",
                                "ids": ",".join(trending_ids),
                                "order": "volume_desc",
                                "per_page": "20",
                                "sparkline": "false",
                                "price_change_percentage": "1h,24h",
                            }
                        )
                        if resp2.status_code == 200:
                            trending_data = resp2.json()
        except Exception as e:
            logger.debug(f"Trending fetch failed: {e}")
        
        # Combine and deduplicate
        seen_ids = set()
        for coin in meme_data + trending_data:
            cid = coin.get("id", "")
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            
            symbol = coin.get("symbol", "").upper()
            price = float(coin.get("current_price", 0) or 0)
            volume = float(coin.get("total_volume", 0) or 0)
            market_cap = float(coin.get("market_cap", 0) or 0)
            pc1h = float(coin.get("price_change_percentage_1h_in_currency", 0) or 0)
            pc24h = float(coin.get("price_change_percentage_24h", 0) or 0)
            
            # Basic quality filter
            if volume < 1_000_000:  # Min $1M daily volume
                continue
            if price <= 0:
                continue
            
            tokens.append({
                "symbol": symbol,
                "coingecko_id": cid,
                "price_usd": price,
                "volume_24h": volume,
                "market_cap": market_cap,
                "price_change_1h": pc1h,
                "price_change_24h": pc24h,
                "source": "coingecko",
            })
        
        # Sort by 1h momentum (positive first)
        tokens.sort(key=lambda x: x.get("price_change_1h", 0), reverse=True)
        
    except Exception as e:
        logger.warning(f"Token discovery failed: {e}")
    
    return tokens[:max_tokens]


async def resolve_solana_mint(symbol: str, coingecko_id: str = None) -> Optional[str]:
    """Resolve a token symbol to its Solana mint address."""
    from services.token_price import TOKENS
    
    # Check known tokens first
    if symbol in TOKENS:
        return TOKENS[symbol]
    
    # Try CoinGecko lookup
    cid = coingecko_id or COINGECKO_IDS.get(symbol)
    if cid:
        mint = await get_coingecko_token_mint(cid)
        if mint:
            return mint
    
    return None
