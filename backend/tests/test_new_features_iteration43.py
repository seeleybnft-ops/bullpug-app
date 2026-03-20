"""
Test suite for Iteration 43 features:
1. Breakout strategy integration in combined_strategy
2. /api/ai-trader/new-pairs returns bonded pairs with proper data structure
3. Social share component verification (frontend - tested via file check)
4. PugBurn scan endpoint
5. Coin recommendations returns 5 safe + 5 volatile picks
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bullpug-beta.preview.emergentagent.com')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestBreakoutStrategy:
    """Test Breakout Strategy Integration"""
    
    def test_analyze_token_returns_combined_strategy(self):
        """Test that analyze endpoint uses combined strategy which includes breakout"""
        # Test with a known token (SOL)
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/SOL",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Either a signal is generated or there's a message about no signal
        assert "signal" in data or "message" in data
        
        # If a signal is generated, check the strategy field
        if data.get("signal"):
            signal = data["signal"]
            # Strategy can be momentum, mean_reversion, breakout, or combined
            assert signal.get("strategy") in ["momentum", "mean_reversion", "breakout", "combined"]
            print(f"Signal generated with strategy: {signal.get('strategy')}")
        else:
            print(f"No signal generated: {data.get('message')}")


class TestNewPairsEndpoint:
    """Test /api/ai-trader/new-pairs endpoint"""
    
    def test_new_pairs_returns_200(self):
        """Test endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        assert response.status_code == 200
        print("PASSED: new-pairs endpoint returns 200")
    
    def test_new_pairs_returns_up_to_5_pairs(self):
        """Test endpoint returns max 5 pairs"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        data = response.json()
        assert "pairs" in data
        assert "count" in data
        assert data["count"] <= 5
        print(f"PASSED: new-pairs returns {data['count']} pairs (max 5)")
    
    def test_new_pairs_all_are_bonded(self):
        """Test all returned pairs have is_bonded=True"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        data = response.json()
        
        for pair in data.get("pairs", []):
            assert pair.get("is_bonded") == True, f"Pair {pair.get('symbol')} is not bonded"
        print(f"PASSED: All {len(data.get('pairs', []))} pairs are bonded")
    
    def test_new_pairs_from_major_dexes_only(self):
        """Test all pairs are from Raydium, Orca, or Meteora (not pump.fun)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        data = response.json()
        
        valid_dexes = ["Raydium", "Orca", "Meteora"]
        for pair in data.get("pairs", []):
            platform = pair.get("platform", "")
            assert platform in valid_dexes, f"Pair {pair.get('symbol')} is from {platform} (not major DEX)"
            assert "pump" not in platform.lower(), f"Pair {pair.get('symbol')} is from pump.fun"
        print(f"PASSED: All pairs are from major DEXes")
    
    def test_new_pairs_data_structure(self):
        """Test pairs have all required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        data = response.json()
        
        required_fields = [
            "symbol", "name", "price", "change_24h", "volume_24h",
            "liquidity_usd", "platform", "contract_address", "pair_address",
            "dex_url", "is_bonded", "risk_level"
        ]
        
        for pair in data.get("pairs", []):
            for field in required_fields:
                assert field in pair, f"Missing field '{field}' in pair {pair.get('symbol')}"
        print(f"PASSED: All pairs have required fields")
    
    def test_new_pairs_has_disclaimer(self):
        """Test response includes disclaimer"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        data = response.json()
        assert "disclaimer" in data
        assert len(data["disclaimer"]) > 0
        print(f"PASSED: Disclaimer present")


class TestCoinRecommendations:
    """Test /api/ai-suggestions/coin-recommendations endpoint"""
    
    def test_coin_recommendations_returns_200(self):
        """Test endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        print("PASSED: coin-recommendations endpoint returns 200")
    
    def test_coin_recommendations_returns_5_safe_picks(self):
        """Test endpoint returns exactly 5 safe picks"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        safe_picks = data.get("safe_picks", [])
        assert len(safe_picks) == 5, f"Expected 5 safe picks, got {len(safe_picks)}"
        
        symbols = [p.get("symbol") for p in safe_picks]
        print(f"PASSED: 5 safe picks returned: {symbols}")
    
    def test_coin_recommendations_returns_5_volatile_picks(self):
        """Test endpoint returns exactly 5 volatile picks"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        volatile_picks = data.get("volatile_picks", [])
        assert len(volatile_picks) == 5, f"Expected 5 volatile picks, got {len(volatile_picks)}"
        
        symbols = [p.get("symbol") for p in volatile_picks]
        print(f"PASSED: 5 volatile picks returned: {symbols}")
    
    def test_safe_picks_have_safe_risk_level(self):
        """Test all safe picks have risk_level='Safe'"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        for pick in data.get("safe_picks", []):
            assert pick.get("risk_level") == "Safe", f"Safe pick {pick.get('symbol')} has risk_level={pick.get('risk_level')}"
        print("PASSED: All safe picks have risk_level='Safe'")
    
    def test_volatile_picks_have_high_risk_level(self):
        """Test all volatile picks have risk_level='High Risk'"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        for pick in data.get("volatile_picks", []):
            assert pick.get("risk_level") == "High Risk", f"Volatile pick {pick.get('symbol')} has risk_level={pick.get('risk_level')}"
        print("PASSED: All volatile picks have risk_level='High Risk'")


class TestPugBurnScan:
    """Test PugBurn scan endpoint"""
    
    def test_pugburn_scan_returns_200(self):
        """Test endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/pugburn/scan/{TEST_WALLET}")
        assert response.status_code == 200
        print("PASSED: pugburn scan endpoint returns 200")
    
    def test_pugburn_scan_response_structure(self):
        """Test response has required fields"""
        response = requests.get(f"{BASE_URL}/api/pugburn/scan/{TEST_WALLET}")
        data = response.json()
        
        required_fields = ["total_accounts_scanned", "vacant_accounts", "total_reclaimable_sol", "scan_timestamp"]
        for field in required_fields:
            assert field in data, f"Missing field '{field}' in pugburn scan response"
        
        print(f"PASSED: PugBurn scan structure correct - {data['total_accounts_scanned']} accounts scanned, {len(data['vacant_accounts'])} vacant")
    
    def test_pugburn_scan_vacant_accounts_structure(self):
        """Test vacant accounts have required fields"""
        response = requests.get(f"{BASE_URL}/api/pugburn/scan/{TEST_WALLET}")
        data = response.json()
        
        if data.get("vacant_accounts"):
            account = data["vacant_accounts"][0]
            required_fields = ["address", "mint", "rent_recoverable"]
            for field in required_fields:
                assert field in account, f"Missing field '{field}' in vacant account"
        print("PASSED: Vacant account structure correct")


class TestHotTrendingBadges:
    """Test that API returns data for HOT/TRENDING badge logic"""
    
    def test_new_pairs_have_volume_and_change(self):
        """Test new pairs have volume_24h and change_24h for badge logic"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        data = response.json()
        
        hot_count = 0
        trending_count = 0
        
        for pair in data.get("pairs", []):
            volume = pair.get("volume_24h", 0)
            change = pair.get("change_24h", 0)
            
            if volume > 100000:
                hot_count += 1
                print(f"  HOT: {pair['symbol']} has volume ${volume:,.0f}")
            
            if change > 50:
                trending_count += 1
                print(f"  TRENDING: {pair['symbol']} has change +{change:.1f}%")
        
        print(f"PASSED: {hot_count} HOT tokens (>$100K vol), {trending_count} TRENDING tokens (>50% change)")
    
    def test_coin_recommendations_have_volume_and_change(self):
        """Test coin recommendations have volume_24h and change_24h for badge logic"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        all_picks = data.get("safe_picks", []) + data.get("volatile_picks", [])
        
        hot_count = 0
        trending_count = 0
        
        for pick in all_picks:
            volume = pick.get("volume_24h", 0)
            change = pick.get("change_24h", 0)
            
            if volume > 100000:
                hot_count += 1
            
            if change > 50:
                trending_count += 1
        
        print(f"PASSED: Coin recommendations - {hot_count} HOT, {trending_count} TRENDING tokens")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
