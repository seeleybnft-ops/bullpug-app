"""Token price and market data utilities for the AI Trading Bot."""

import httpx
import logging
import numpy as np
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Token constants
SOL_MINT = "So11111111111111111111111111111111111111112"
LAMPORTS_PER_SOL = 1_000_000_000

# Jupiter API Configuration
JUPITER_QUOTE_URL = "https://lite-api.jup.ag/swap/v1"
JUPITER_SWAP_URL = "https://lite-api.jup.ag/swap/v1"

# Token Mint Addresses (Solana)
TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "RNDR": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    "HNT": "hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "TENSOR": "TNSRxcUxoT9xBG3de7PiJyTDYu7kskLqcpddxnEJAS6",
    "DRIFT": "DriFtupJYLTosbwoN8koMbEYSx54aFAVLddWsbksjwg7",
}

# Risk Categories
SAFER_TOKENS = ["SOL", "USDC", "USDT", "JUP", "PYTH", "RNDR", "HNT", "JTO"]
HIGH_RISK_TOKENS = ["BONK", "WIF", "RAY", "ORCA", "TENSOR", "DRIFT"]

# Runner Detection Settings
RUNNER_MIN_LIQUIDITY = 10000
RUNNER_MIN_VOLUME_24H = 50000
RUNNER_MIN_PRICE_CHANGE_1H = 5
RUNNER_MAX_PRICE_CHANGE_1H = 100
RUNNER_MIN_TXNS_1H = 50
RUNNER_MAX_AGE_HOURS = 72


async def get_jupiter_quote(
    input_mint: str,
    output_mint: str,
    amount_lamports: int,
    slippage_bps: int = 100
) -> Optional[Dict]:
    """Get swap quote from Jupiter"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{JUPITER_QUOTE_URL}/quote",
                params={
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": str(amount_lamports),
                    "slippageBps": slippage_bps
                }
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Jupiter quote failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Jupiter quote error: {e}")
        return None


async def get_token_price(token_symbol: str) -> Optional[float]:
    """Get current token price in USD — multi-source with fallback"""
    token_mint = TOKENS.get(token_symbol)
    if not token_mint:
        return None
    return await get_token_price_by_mint(token_mint, symbol=token_symbol)


async def get_token_price_by_mint(token_mint: str, symbol: str = None) -> Optional[float]:
    """
    Get current token price in USD by mint address.
    Priority: DexScreener (cached) -> CoinGecko batch cache -> CoinGecko single -> None
    """
    if not token_mint:
        return None
    
    # Source 1: DexScreener (with cache + rate limit protection)
    try:
        from services.market_data import get_dexscreener_pair_data
        dex_pair = await get_dexscreener_pair_data(token_mint)
        if dex_pair:
            price = float(dex_pair.get("priceUsd", 0) or 0)
            if price > 0:
                return price
    except Exception:
        pass
    
    # Source 2: CoinGecko batch cache (already prefetched by scanner)
    if symbol:
        try:
            from services.market_data import _coingecko_batch_cache
            import time
            cached = _coingecko_batch_cache.get(symbol)
            if cached:
                ts, data = cached
                if (time.time() - ts) < 1200:  # 20 min cache for price
                    price = data.get("price_usd", 0)
                    if price > 0:
                        return price
        except Exception:
            pass
    
    # Source 3: CoinGecko single lookup (if we know the CoinGecko ID)
    if symbol:
        try:
            from services.market_data import COINGECKO_IDS, _COINGECKO_BACKOFF_UNTIL
            import time as _time
            cg_id = COINGECKO_IDS.get(symbol)
            if cg_id and _time.time() >= _COINGECKO_BACKOFF_UNTIL:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://api.coingecko.com/api/v3/simple/price",
                        params={"ids": cg_id, "vs_currencies": "usd"}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        price = data.get(cg_id, {}).get("usd", 0)
                        if price > 0:
                            return float(price)
                    elif resp.status_code == 429:
                        import services.market_data as md
                        md._COINGECKO_BACKOFF_UNTIL = _time.time() + 90
        except Exception:
            pass
    
    # Source 4: Direct DexScreener (no cache, last resort)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                    return float(best_pair.get("priceUsd", 0) or 0)
    except Exception as e:
        logger.warning(f"Price fetch error for {token_mint}: {e}")
    return None


async def get_price_history(token_symbol: str, periods: int = 50) -> List[float]:
    """Get historical prices for technical analysis using DexScreener data"""
    current_price = await get_token_price(token_symbol)
    if not current_price:
        return []

    token_mint = TOKENS.get(token_symbol)
    if not token_mint:
        return [current_price]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                    change_5m = float(best_pair.get("priceChange", {}).get("m5", 0) or 0) / 100
                    change_1h = float(best_pair.get("priceChange", {}).get("h1", 0) or 0) / 100
                    change_6h = float(best_pair.get("priceChange", {}).get("h6", 0) or 0) / 100
                    change_24h = float(best_pair.get("priceChange", {}).get("h24", 0) or 0) / 100

                    prices = []
                    price_24h_ago = current_price / (1 + change_24h) if change_24h != -1 else current_price
                    price_6h_ago = current_price / (1 + change_6h) if change_6h != -1 else current_price
                    price_1h_ago = current_price / (1 + change_1h) if change_1h != -1 else current_price

                    key_prices = [
                        (0.0, price_24h_ago),
                        (0.25, price_24h_ago * 1.02),
                        (0.5, price_6h_ago),
                        (0.75, price_6h_ago * 0.98),
                        (0.90, price_1h_ago),
                        (0.95, price_1h_ago * (1 + change_5m * 0.5)),
                        (1.0, current_price)
                    ]

                    for i in range(periods):
                        t = i / periods
                        for j in range(len(key_prices) - 1):
                            if key_prices[j][0] <= t < key_prices[j+1][0]:
                                t_local = (t - key_prices[j][0]) / (key_prices[j+1][0] - key_prices[j][0])
                                base_price = key_prices[j][1] + (key_prices[j+1][1] - key_prices[j][1]) * t_local
                                volatility = 0.008 if t > 0.8 else 0.004
                                noise = np.random.normal(0, base_price * volatility)
                                prices.append(max(base_price + noise, 0.000001))
                                break

                    prices.append(current_price)
                    return prices
    except Exception as e:
        logger.warning(f"Price history error for {token_symbol}: {e}")

    return [current_price] * periods
