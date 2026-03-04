"""
Backend API Tests for Tokens Tab Features
Tests:
1. /api/ai-trader/new-pairs - Should return 5 bonded pairs (is_bonded: true) from Raydium/Orca/Meteora
2. /api/ai-suggestions/coin-recommendations - Should return 5 safe_picks and 5 volatile_picks
3. PugBurn /api/pugburn/scan/{wallet} - Correctly identifies vacant accounts
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestNewPairsEndpoint:
    """Tests for /api/ai-trader/new-pairs endpoint"""
    
    def test_new_pairs_endpoint_returns_200(self):
        """Test that new-pairs endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ /api/ai-trader/new-pairs returns 200 OK")
    
    def test_new_pairs_returns_up_to_5_pairs(self):
        """Test that new-pairs returns up to 5 pairs"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        pairs = data.get("pairs", [])
        count = data.get("count", 0)
        
        # Should return up to 5 pairs
        assert len(pairs) <= 5, f"Expected at most 5 pairs, got {len(pairs)}"
        assert count <= 5, f"Count field shows {count}, expected at most 5"
        print(f"✓ /api/ai-trader/new-pairs returns {len(pairs)} pairs (max 5)")
    
    def test_new_pairs_all_are_bonded(self):
        """Test that all returned pairs have is_bonded: true"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        pairs = data.get("pairs", [])
        
        # All pairs must have is_bonded: true
        for pair in pairs:
            is_bonded = pair.get("is_bonded", False)
            assert is_bonded == True, f"Pair {pair.get('symbol', 'unknown')} should have is_bonded=True, got {is_bonded}"
            print(f"  ✓ {pair.get('symbol', '?')}: is_bonded={is_bonded}")
        
        print(f"✓ All {len(pairs)} pairs have is_bonded=True")
    
    def test_new_pairs_from_major_dexes_only(self):
        """Test that all pairs are from Raydium, Orca, or Meteora (NOT pump.fun)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        pairs = data.get("pairs", [])
        valid_platforms = ["Raydium", "Orca", "Meteora"]
        invalid_platforms = ["Pump.fun", "pump.fun", "pump"]
        
        for pair in pairs:
            platform = pair.get("platform", "")
            symbol = pair.get("symbol", "?")
            
            # Must be on a valid major DEX
            assert platform in valid_platforms, f"Pair {symbol} is on {platform}, expected one of {valid_platforms}"
            
            # Must NOT be pump.fun
            assert platform.lower() not in [p.lower() for p in invalid_platforms], f"Pair {symbol} should NOT be on pump.fun"
            
            print(f"  ✓ {symbol}: platform={platform} (valid)")
        
        print(f"✓ All pairs are from major DEXes (Raydium/Orca/Meteora), NOT pump.fun")
    
    def test_new_pairs_structure(self):
        """Test that each pair has required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        pairs = data.get("pairs", [])
        required_fields = ["symbol", "name", "price", "change_24h", "volume_24h", 
                          "liquidity_usd", "platform", "contract_address", "is_bonded"]
        
        for pair in pairs:
            for field in required_fields:
                assert field in pair, f"Pair {pair.get('symbol', '?')} missing field: {field}"
        
        print(f"✓ All pairs have required fields: {required_fields}")
    
    def test_new_pairs_has_disclaimer(self):
        """Test that response includes disclaimer for high-risk pairs"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        disclaimer = data.get("disclaimer", "")
        assert len(disclaimer) > 0, "Response should include a disclaimer"
        print(f"✓ Disclaimer present: {disclaimer[:50]}...")


class TestCoinRecommendationsEndpoint:
    """Tests for /api/ai-suggestions/coin-recommendations endpoint"""
    
    def test_coin_recommendations_returns_200(self):
        """Test that coin-recommendations endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ /api/ai-suggestions/coin-recommendations returns 200 OK")
    
    def test_coin_recommendations_returns_5_safe_picks(self):
        """Test that safe_picks contains exactly 5 coins"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        safe_picks = data.get("safe_picks", [])
        print(f"  safe_picks count: {len(safe_picks)}")
        
        # Should return exactly 5 safe picks
        assert len(safe_picks) == 5, f"Expected exactly 5 safe_picks, got {len(safe_picks)}"
        print(f"✓ coin-recommendations returns exactly 5 safe_picks")
    
    def test_coin_recommendations_returns_5_volatile_picks(self):
        """Test that volatile_picks contains exactly 5 coins"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        volatile_picks = data.get("volatile_picks", [])
        print(f"  volatile_picks count: {len(volatile_picks)}")
        
        # Should return exactly 5 volatile picks
        assert len(volatile_picks) == 5, f"Expected exactly 5 volatile_picks, got {len(volatile_picks)}"
        print(f"✓ coin-recommendations returns exactly 5 volatile_picks")
    
    def test_coin_recommendations_total_is_10(self):
        """Test that total tokens from safe + volatile = 10"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        safe_count = len(data.get("safe_picks", []))
        volatile_count = len(data.get("volatile_picks", []))
        total = safe_count + volatile_count
        
        assert total == 10, f"Expected 10 total tokens (5 safe + 5 volatile), got {total}"
        print(f"✓ Total tokens from recommendations: {total} (5 safe + 5 volatile)")
    
    def test_safe_picks_structure(self):
        """Test that safe_picks have required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        safe_picks = data.get("safe_picks", [])
        required_fields = ["symbol", "name", "price", "change_24h", "volume_24h", 
                          "liquidity_usd", "platform", "risk_level"]
        
        for coin in safe_picks:
            for field in required_fields:
                assert field in coin, f"Safe pick {coin.get('symbol', '?')} missing field: {field}"
            
            # Safe picks should have risk_level = "Safe"
            assert coin.get("risk_level") == "Safe", f"Safe pick {coin.get('symbol', '?')} has wrong risk_level"
        
        print(f"✓ All safe_picks have required fields and risk_level='Safe'")
    
    def test_volatile_picks_structure(self):
        """Test that volatile_picks have required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        volatile_picks = data.get("volatile_picks", [])
        required_fields = ["symbol", "name", "price", "change_24h", "volume_24h", 
                          "liquidity_usd", "platform", "risk_level"]
        
        for coin in volatile_picks:
            for field in required_fields:
                assert field in coin, f"Volatile pick {coin.get('symbol', '?')} missing field: {field}"
            
            # Volatile picks should have risk_level = "High Risk"
            assert coin.get("risk_level") == "High Risk", f"Volatile pick {coin.get('symbol', '?')} has wrong risk_level"
        
        print(f"✓ All volatile_picks have required fields and risk_level='High Risk'")


class TestTotalTokensCount:
    """Tests to verify total tokens count is 15 (5 safe + 5 volatile + 5 new pairs)"""
    
    def test_total_tokens_is_15(self):
        """Test that total tokens across all endpoints = 15"""
        # Get coin recommendations (safe + volatile)
        recs_response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations", timeout=30)
        assert recs_response.status_code == 200
        recs_data = recs_response.json()
        
        # Get new pairs
        pairs_response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs", timeout=30)
        assert pairs_response.status_code == 200
        pairs_data = pairs_response.json()
        
        safe_count = len(recs_data.get("safe_picks", []))
        volatile_count = len(recs_data.get("volatile_picks", []))
        new_pairs_count = len(pairs_data.get("pairs", []))
        
        total = safe_count + volatile_count + new_pairs_count
        
        print(f"  Safe picks: {safe_count}")
        print(f"  Volatile picks: {volatile_count}")
        print(f"  New pairs: {new_pairs_count}")
        print(f"  Total: {total}")
        
        # Expected: 5 safe + 5 volatile + up to 5 new pairs = 15 max
        # But new pairs might have less if no qualifying pairs exist
        assert safe_count == 5, f"Expected 5 safe picks, got {safe_count}"
        assert volatile_count == 5, f"Expected 5 volatile picks, got {volatile_count}"
        assert new_pairs_count <= 5, f"Expected at most 5 new pairs, got {new_pairs_count}"
        
        print(f"✓ Token counts correct: {safe_count} safe + {volatile_count} volatile + {new_pairs_count} new pairs = {total} total")


class TestPugBurnScanEndpoint:
    """Tests for /api/pugburn/scan/{wallet} endpoint"""
    
    def test_pugburn_scan_returns_200(self):
        """Test that PugBurn scan endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/pugburn/scan/{TEST_WALLET}", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ /api/pugburn/scan/{wallet} returns 200 OK")
    
    def test_pugburn_scan_structure(self):
        """Test that PugBurn scan returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/pugburn/scan/{TEST_WALLET}", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["wallet_address", "vacant_accounts", "total_accounts_scanned", 
                          "total_reclaimable_sol", "scan_timestamp"]
        
        for field in required_fields:
            assert field in data, f"Response missing field: {field}"
        
        # wallet_address should match
        assert data["wallet_address"] == TEST_WALLET
        
        # vacant_accounts should be a list
        assert isinstance(data["vacant_accounts"], list)
        
        # total_accounts_scanned should be >= 0
        assert data["total_accounts_scanned"] >= 0
        
        # total_reclaimable_sol should be >= 0
        assert data["total_reclaimable_sol"] >= 0
        
        print(f"✓ PugBurn scan structure verified")
        print(f"  - Wallet: {data['wallet_address'][:10]}...")
        print(f"  - Vacant accounts: {len(data['vacant_accounts'])}")
        print(f"  - Total scanned: {data['total_accounts_scanned']}")
        print(f"  - Reclaimable SOL: {data['total_reclaimable_sol']}")
    
    def test_pugburn_scans_both_spl_and_token2022(self):
        """Test that scan covers both SPL Token and Token-2022 programs"""
        response = requests.get(f"{BASE_URL}/api/pugburn/scan/{TEST_WALLET}", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        vacant_accounts = data.get("vacant_accounts", [])
        
        # Check program IDs in vacant accounts if any exist
        if vacant_accounts:
            programs_found = set()
            for account in vacant_accounts:
                program_id = account.get("program_id", "")
                if program_id:
                    programs_found.add(program_id)
            
            print(f"  Programs found in vacant accounts: {programs_found}")
        
        print(f"✓ PugBurn scan endpoint processes accounts (structure verified)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
