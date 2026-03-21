"""
Runner Detection Service

Detects potential 'runner' tokens - new pairs showing early momentum
that could have significant upside before they run.
"""

import httpx
import logging
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


class RunnerDetector:
    """
    Detects potential 'runner' tokens - new pairs showing early momentum
    that could have significant upside before they run.
    """
    
    @staticmethod
    async def fetch_trending_pairs(limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch trending Solana pairs from DexScreener.
        Returns pairs sorted by momentum potential.
        """
        runners = []
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Fetch boosted/trending tokens on Solana
                response = await client.get(
                    "https://api.dexscreener.com/token-boosts/top/v1",
                    params={"chainId": "solana"}
                )
                
                boosted_tokens = []
                if response.status_code == 200:
                    boosted_tokens = response.json()[:20]  # Top 20 boosted
                
                # Also fetch latest pairs on Solana
                latest_response = await client.get(
                    "https://api.dexscreener.com/token-profiles/latest/v1",
                    params={"chainId": "solana"}
                )
                
                latest_tokens = []
                if latest_response.status_code == 200:
                    latest_tokens = latest_response.json()[:20]
                
                # Combine unique tokens
                all_tokens = []
                seen_addresses = set()
                
                for token in boosted_tokens + latest_tokens:
                    addr = token.get("tokenAddress")
                    if addr and addr not in seen_addresses:
                        seen_addresses.add(addr)
                        all_tokens.append(addr)
                
                # Fetch detailed pair data for each token
                for token_addr in all_tokens[:15]:  # Limit API calls
                    try:
                        pair_response = await client.get(
                            f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}"
                        )
                        
                        if pair_response.status_code != 200:
                            continue
                        
                        pairs = pair_response.json().get("pairs", [])
                        if not pairs:
                            continue
                        
                        # Get the most liquid Solana pair
                        solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                        if not solana_pairs:
                            continue
                        
                        best_pair = max(solana_pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                        
                        # Check if it meets runner criteria
                        runner_data = RunnerDetector._analyze_runner_potential(best_pair)
                        if runner_data:
                            runners.append(runner_data)
                    
                    except Exception as e:
                        logger.debug(f"Failed to fetch pair data for {token_addr}: {e}")
                        continue
                
                # Sort by runner score (momentum + volume + freshness)
                runners.sort(key=lambda x: x.get("runner_score", 0), reverse=True)
        
        except Exception as e:
            logger.warning(f"Failed to fetch trending pairs: {e}")
        
        return runners[:limit]
    
    @staticmethod
    def _analyze_runner_potential(pair: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze if a pair has runner potential based on key metrics.
        Returns runner data if it passes criteria, None otherwise.
        """
        try:
            # Extract metrics
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
            
            # Pair creation time
            pair_created = pair.get("pairCreatedAt")
            hours_since_creation = 9999
            if pair_created:
                try:
                    created_ts = int(pair_created) / 1000  # ms to seconds
                    hours_since_creation = (datetime.now(timezone.utc).timestamp() - created_ts) / 3600
                except (ValueError, TypeError):
                    pass
            
            # Apply filters
            if liquidity < RUNNER_MIN_LIQUIDITY:
                return None
            if volume_24h < RUNNER_MIN_VOLUME_24H:
                return None
            if price_change_1h < RUNNER_MIN_PRICE_CHANGE_1H:
                return None
            if price_change_1h > RUNNER_MAX_PRICE_CHANGE_1H:
                return None  # Avoid obvious pump & dumps
            if total_txns_1h < RUNNER_MIN_TXNS_1H:
                return None  # Not enough organic activity
            
            # Calculate buy/sell ratio (bullish if more buys)
            buy_ratio = buys_1h / total_txns_1h if total_txns_1h > 0 else 0.5
            
            # Calculate runner score (0-100)
            score = 0
            
            # Momentum score (0-40 points)
            if price_change_1h >= 20:
                score += 40
            elif price_change_1h >= 15:
                score += 35
            elif price_change_1h >= 10:
                score += 30
            elif price_change_1h >= 5:
                score += 20
            
            # Volume score (0-25 points)
            if volume_24h >= 500000:
                score += 25
            elif volume_24h >= 200000:
                score += 20
            elif volume_24h >= 100000:
                score += 15
            elif volume_24h >= 50000:
                score += 10
            
            # Buy pressure score (0-20 points)
            if buy_ratio >= 0.7:
                score += 20
            elif buy_ratio >= 0.6:
                score += 15
            elif buy_ratio >= 0.55:
                score += 10
            
            # Freshness score (0-15 points) - newer pairs get bonus
            if hours_since_creation <= 6:
                score += 15
            elif hours_since_creation <= 24:
                score += 12
            elif hours_since_creation <= 48:
                score += 8
            elif hours_since_creation <= RUNNER_MAX_AGE_HOURS:
                score += 5
            
            # Minimum score threshold
            if score < 30:
                return None
            
            return {
                "symbol": symbol,
                "token_address": token_address,
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
                "dex": pair.get("dexId", "unknown")
            }
        
        except Exception as e:
            logger.debug(f"Failed to analyze runner potential: {e}")
            return None
    
    @staticmethod
    async def get_best_runners(max_runners: int = 5, known_symbols: set = None) -> List[Dict[str, Any]]:
        """
        Get the best runner candidates for auto-trading.
        Filters out known tokens and returns fresh opportunities.
        """
        runners = await RunnerDetector.fetch_trending_pairs(limit=20)
        
        # Filter out known/established tokens
        symbols_to_exclude = known_symbols or KNOWN_TOKENS
        fresh_runners = [r for r in runners if r["symbol"].upper() not in symbols_to_exclude]
        
        return fresh_runners[:max_runners]
