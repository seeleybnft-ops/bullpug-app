"""
Runner Detection Service

Detects potential 'runner' tokens - tokens showing momentum
that could have significant upside.

Multi-source: CoinGecko (primary) + DexScreener (fallback with rate-limit protection).
"""

import httpx
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Runner Detection Settings
RUNNER_MIN_LIQUIDITY = 10000  # Minimum $10k liquidity
RUNNER_MIN_VOLUME_24H = 50000  # Minimum $50k 24h volume
RUNNER_MIN_PRICE_CHANGE_1H = 5  # Minimum 5% gain in 1h
RUNNER_MAX_PRICE_CHANGE_1H = 100  # Max 100% (avoid pump & dumps)
RUNNER_MIN_TXNS_1H = 50  # Minimum transactions to avoid manipulation
RUNNER_MAX_AGE_HOURS = 72  # Focus on pairs created within 72 hours

# Known/established tokens to filter out
KNOWN_TOKENS = {
    "SOL", "USDC", "USDT", "BONK", "WIF", "JUP", "PYTH", "RNDR", "RAY", "ORCA"
}

# In-memory DexScreener backoff
_dex_backoff_until = 0.0


class RunnerDetector:
    """
    Detects potential 'runner' tokens with momentum signals.
    Uses CoinGecko as primary source, DexScreener as fallback.
    """

    @staticmethod
    async def fetch_trending_pairs(limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch trending Solana pairs from multiple sources.
        Returns pairs sorted by momentum potential.
        """
        runners = []

        # Source 1: CoinGecko Solana meme coins (most reliable, no aggressive rate limit)
        cg_runners = await RunnerDetector._fetch_from_coingecko()
        runners.extend(cg_runners)

        # Source 2: DexScreener boosted tokens (only if not rate-limited)
        global _dex_backoff_until
        if time.time() >= _dex_backoff_until:
            dex_runners = await RunnerDetector._fetch_from_dexscreener()
            if dex_runners is None:  # Rate limited
                _dex_backoff_until = time.time() + 120  # 2 min backoff
            elif dex_runners:
                # Deduplicate by symbol
                existing_symbols = {r["symbol"] for r in runners}
                for r in dex_runners:
                    if r["symbol"] not in existing_symbols:
                        runners.append(r)

        # Sort by runner score
        runners.sort(key=lambda x: x.get("runner_score", 0), reverse=True)
        return runners[:limit]

    @staticmethod
    async def _fetch_from_coingecko() -> List[Dict[str, Any]]:
        """Fetch runner candidates from CoinGecko Solana meme coins."""
        runners = []
        try:
            # Check shared CoinGecko backoff
            from services.market_data import _COINGECKO_BACKOFF_UNTIL
            if time.time() < _COINGECKO_BACKOFF_UNTIL:
                logger.debug("CoinGecko in shared backoff — skipping runner fetch")
                return []
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "category": "solana-meme-coins",
                        "order": "volume_desc",
                        "per_page": "30",
                        "page": "1",
                        "sparkline": "false",
                        "price_change_percentage": "1h,24h",
                    }
                )

                if resp.status_code == 429:
                    import services.market_data as md
                    md._COINGECKO_BACKOFF_UNTIL = time.time() + 90
                    logger.warning("CoinGecko runner fetch rate limited — 90s backoff")
                    return []
                
                if resp.status_code != 200:
                    logger.warning(f"CoinGecko meme coins failed: {resp.status_code}")
                    return []

                coins = resp.json()
                for coin in coins:
                    runner_data = RunnerDetector._analyze_coingecko_runner(coin)
                    if runner_data:
                        runners.append(runner_data)

        except Exception as e:
            logger.warning(f"CoinGecko runner fetch failed: {e}")

        return runners

    @staticmethod
    def _analyze_coingecko_runner(coin: Dict) -> Optional[Dict[str, Any]]:
        """Analyze a CoinGecko coin for runner potential."""
        try:
            symbol = coin.get("symbol", "").upper()
            price = float(coin.get("current_price", 0) or 0)
            volume_24h = float(coin.get("total_volume", 0) or 0)
            market_cap = float(coin.get("market_cap", 0) or 0)
            pc1h = float(coin.get("price_change_percentage_1h_in_currency", 0) or 0)
            pc24h = float(coin.get("price_change_percentage_24h", 0) or 0)
            coingecko_id = coin.get("id", "")

            if price <= 0 or volume_24h < 1_000_000:
                return None

            # Skip stablecoins and mega-caps
            if symbol in {"USDC", "USDT", "SOL", "USD1"}:
                return None

            # Score based on momentum (similar to DexScreener scoring)
            score = 0

            # Momentum score (0-40)
            if pc1h >= 10:
                score += 40
            elif pc1h >= 5:
                score += 30
            elif pc1h >= 2:
                score += 20
            elif pc1h >= 0.5:
                score += 10

            # Volume score (0-25)
            if volume_24h >= 50_000_000:
                score += 25
            elif volume_24h >= 20_000_000:
                score += 20
            elif volume_24h >= 5_000_000:
                score += 15
            elif volume_24h >= 1_000_000:
                score += 10

            # 24h trend bonus (0-20)
            if pc24h >= 20:
                score += 20
            elif pc24h >= 10:
                score += 15
            elif pc24h >= 5:
                score += 10
            elif pc24h >= 0:
                score += 5

            # Market cap size bonus (prefer mid/small caps for runner potential)
            if 5_000_000 <= market_cap <= 100_000_000:
                score += 15  # Sweet spot for runners
            elif 100_000_000 < market_cap <= 500_000_000:
                score += 10
            elif market_cap > 500_000_000:
                score += 5

            if score < 25:
                return None

            return {
                "symbol": symbol,
                "token_address": "",  # Will be resolved later via CoinGecko detail API
                "coingecko_id": coingecko_id,
                "price_usd": price,
                "liquidity_usd": market_cap * 0.01,  # Rough proxy
                "volume_24h": volume_24h,
                "price_change_1h": pc1h,
                "price_change_6h": 0,
                "price_change_24h": pc24h,
                "buys_1h": 0,
                "sells_1h": 0,
                "buy_ratio": 0.5,
                "hours_since_creation": 9999,
                "runner_score": score,
                "pair_address": "",
                "dex": "coingecko",
                "source": "coingecko",
            }

        except Exception as e:
            logger.debug(f"Failed to analyze CoinGecko runner: {e}")
            return None

    @staticmethod
    async def _fetch_from_dexscreener() -> Optional[List[Dict[str, Any]]]:
        """
        Fetch runner candidates from DexScreener boosted tokens.
        Returns None on rate limit (429), empty list on no results.
        """
        runners = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://api.dexscreener.com/token-boosts/top/v1",
                    params={"chainId": "solana"}
                )

                if response.status_code == 429:
                    logger.warning("DexScreener boosted API rate limited (429)")
                    return None  # Signal rate limit

                boosted_tokens = []
                if response.status_code == 200:
                    data = response.json()
                    # Filter to Solana only
                    boosted_tokens = [t for t in data if t.get("chainId") == "solana"][:15]

                # Fetch pair data for each (with delays)
                for token in boosted_tokens[:8]:
                    token_addr = token.get("tokenAddress")
                    if not token_addr:
                        continue

                    try:
                        await asyncio.sleep(2)  # Rate limit protection
                        pair_resp = await client.get(
                            f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}"
                        )

                        if pair_resp.status_code == 429:
                            logger.warning("DexScreener 429 during runner scan — stopping")
                            return None  # Signal rate limit

                        if pair_resp.status_code != 200:
                            continue

                        pairs = pair_resp.json().get("pairs", [])
                        solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                        if not solana_pairs:
                            continue

                        best_pair = max(solana_pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                        runner_data = RunnerDetector._analyze_runner_potential(best_pair)
                        if runner_data:
                            runners.append(runner_data)

                    except Exception as e:
                        logger.debug(f"DexScreener pair fetch failed: {e}")
                        continue

        except Exception as e:
            logger.warning(f"DexScreener runner fetch failed: {e}")

        return runners

    @staticmethod
    def _analyze_runner_potential(pair: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze if a DexScreener pair has runner potential."""
        try:
            liquidity = float(pair.get("liquidity", {}).get("usd", 0) or 0)
            volume_24h = float(pair.get("volume", {}).get("h24", 0) or 0)
            price_change_1h = float(pair.get("priceChange", {}).get("h1", 0) or 0)
            price_change_6h = float(pair.get("priceChange", {}).get("h6", 0) or 0)
            price_change_24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
            txns_1h = pair.get("txns", {}).get("h1", {})
            buys_1h = int(txns_1h.get("buys", 0) or 0)
            sells_1h = int(txns_1h.get("sells", 0) or 0)
            total_txns_1h = buys_1h + sells_1h

            base_token = pair.get("baseToken", {})
            symbol = base_token.get("symbol", "???")
            token_address = base_token.get("address", "")

            pair_created = pair.get("pairCreatedAt")
            hours_since_creation = 9999
            if pair_created:
                try:
                    created_ts = int(pair_created) / 1000
                    hours_since_creation = (datetime.now(timezone.utc).timestamp() - created_ts) / 3600
                except (ValueError, TypeError):
                    pass

            # Relaxed filters for DexScreener (boosted tokens tend to be lower quality)
            if liquidity < 5000:
                return None
            if volume_24h < 20000:
                return None
            if price_change_1h < 2:
                return None
            if price_change_1h > 150:
                return None

            buy_ratio = buys_1h / total_txns_1h if total_txns_1h > 0 else 0.5

            # Calculate score
            score = 0
            if price_change_1h >= 20:
                score += 40
            elif price_change_1h >= 15:
                score += 35
            elif price_change_1h >= 10:
                score += 30
            elif price_change_1h >= 5:
                score += 20
            elif price_change_1h >= 2:
                score += 10

            if volume_24h >= 500000:
                score += 25
            elif volume_24h >= 200000:
                score += 20
            elif volume_24h >= 100000:
                score += 15
            elif volume_24h >= 50000:
                score += 10
            elif volume_24h >= 20000:
                score += 5

            if buy_ratio >= 0.7:
                score += 20
            elif buy_ratio >= 0.6:
                score += 15
            elif buy_ratio >= 0.55:
                score += 10

            if hours_since_creation <= 6:
                score += 15
            elif hours_since_creation <= 24:
                score += 12
            elif hours_since_creation <= 48:
                score += 8
            elif hours_since_creation <= RUNNER_MAX_AGE_HOURS:
                score += 5

            if score < 20:
                return None

            return {
                "symbol": symbol,
                "token_address": token_address,
                "coingecko_id": "",
                "price_usd": float(pair.get("priceUsd", 0) or 0),
                "liquidity_usd": liquidity,
                "volume_24h": volume_24h,
                "price_change_1h": price_change_1h,
                "price_change_6h": price_change_6h,
                "price_change_24h": price_change_24h,
                "buys_1h": buys_1h,
                "sells_1h": sells_1h,
                "buy_ratio": buy_ratio,
                "hours_since_creation": hours_since_creation,
                "runner_score": score,
                "pair_address": pair.get("pairAddress", ""),
                "dex": pair.get("dexId", "unknown"),
                "source": "dexscreener",
            }

        except Exception as e:
            logger.debug(f"Failed to analyze DexScreener runner: {e}")
            return None

    @staticmethod
    async def get_best_runners(max_runners: int = 5, known_symbols: set = None) -> List[Dict[str, Any]]:
        """
        Get the best runner candidates for auto-trading.
        Filters out known/established tokens.
        """
        runners = await RunnerDetector.fetch_trending_pairs(limit=20)

        symbols_to_exclude = known_symbols or KNOWN_TOKENS
        fresh_runners = [r for r in runners if r["symbol"].upper() not in symbols_to_exclude]

        # Resolve Solana mint addresses for CoinGecko-sourced runners
        for runner in fresh_runners:
            if not runner.get("token_address") and runner.get("coingecko_id"):
                try:
                    from services.market_data import get_coingecko_token_mint
                    mint = await get_coingecko_token_mint(runner["coingecko_id"])
                    if mint:
                        runner["token_address"] = mint
                except Exception as e:
                    logger.debug(f"Mint resolution failed for {runner['symbol']}: {e}")

        # Only return runners with resolved mint addresses
        resolved = [r for r in fresh_runners if r.get("token_address")]
        return resolved[:max_runners]


# Need asyncio import for sleep in _fetch_from_dexscreener
import asyncio
