"""
Test iteration 69: SOL price fix verification
Verifies that synced positions have correct invested SOL amounts after the fix
that uses Jupiter price API with fallback instead of wrong SOL price (0.019 instead of ~140)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test wallet from the review request
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestSOLPriceFix:
    """Tests to verify the SOL price fix in position sync"""
    
    def test_positions_endpoint_returns_200(self):
        """Test that positions endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Positions endpoint returns 200")
    
    def test_positions_count_is_4(self):
        """Test that all 4 positions are present (RNDR, one, LNG, WRT)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        data = response.json()
        
        assert "positions" in data, "Response should have 'positions' field"
        assert "count" in data, "Response should have 'count' field"
        assert data["count"] == 4, f"Expected 4 positions, got {data['count']}"
        
        # Verify all expected tokens are present
        symbols = [p.get("token_symbol") for p in data["positions"]]
        expected_symbols = ["RNDR", "one", "LNG", "WRT"]
        for symbol in expected_symbols:
            assert symbol in symbols, f"Missing position for {symbol}"
        
        print(f"✓ All 4 positions present: {symbols}")
    
    def test_synced_positions_have_correct_sol_amounts(self):
        """
        CRITICAL TEST: Verify synced positions have correct invested SOL amounts
        Expected: ~0.003 SOL each (not 29 SOL which was the bug)
        """
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        data = response.json()
        
        for position in data["positions"]:
            symbol = position.get("token_symbol")
            amount_sol = position.get("amount_sol", 0)
            
            # Synced positions (one, LNG, WRT) should be ~0.003 SOL each
            if position.get("synced_from_chain"):
                # Should be between 0.001 and 0.01 SOL (not 20-30 SOL)
                assert amount_sol < 0.1, f"{symbol}: amount_sol {amount_sol} is too high (bug: was ~29 SOL)"
                assert amount_sol > 0.001, f"{symbol}: amount_sol {amount_sol} is too low"
                print(f"✓ {symbol}: amount_sol = {amount_sol} SOL (correct range)")
            else:
                # RNDR was manually set to 0.01 SOL
                assert amount_sol == 0.01, f"RNDR should have amount_sol = 0.01, got {amount_sol}"
                print(f"✓ {symbol}: amount_sol = {amount_sol} SOL (manual position)")
    
    def test_total_invested_sol_is_reasonable(self):
        """
        CRITICAL TEST: Total invested SOL should be ~0.02 SOL (not 80+ SOL)
        """
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        data = response.json()
        
        total_invested_sol = sum(p.get("amount_sol", 0) for p in data["positions"])
        
        # Expected: ~0.02 SOL (0.003 * 3 + 0.01 = 0.019)
        # Bug value was: ~80+ SOL (29 * 3 + 0.01 = 87.01)
        assert total_invested_sol < 0.1, f"Total invested SOL {total_invested_sol} is too high (bug: was ~87 SOL)"
        assert total_invested_sol > 0.01, f"Total invested SOL {total_invested_sol} is too low"
        
        print(f"✓ Total invested SOL: {total_invested_sol:.6f} SOL (expected ~0.02 SOL)")
    
    def test_position_values_are_reasonable(self):
        """Test that current values are reasonable (total ~$2-3 USD)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        data = response.json()
        
        total_value_usd = sum(p.get("current_value_usd", 0) for p in data["positions"])
        total_value_sol = sum(p.get("current_value_sol", 0) for p in data["positions"])
        
        # Expected: ~$2-3 USD / ~0.02 SOL
        assert total_value_usd < 10, f"Total value ${total_value_usd} is too high"
        assert total_value_usd > 0.5, f"Total value ${total_value_usd} is too low"
        
        print(f"✓ Total portfolio value: ${total_value_usd:.2f} USD / {total_value_sol:.6f} SOL")
    
    def test_sol_price_in_response_is_reasonable(self):
        """Test that SOL price in response is reasonable (~$80-200)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        data = response.json()
        
        sol_price = data.get("sol_price_usd", 0)
        
        # SOL price should be in reasonable range (not 0.019 which was the bug)
        assert sol_price > 50, f"SOL price ${sol_price} is too low (bug: was $0.019)"
        assert sol_price < 500, f"SOL price ${sol_price} is too high"
        
        print(f"✓ SOL price: ${sol_price} (reasonable range)")


class TestSyncPositionsSOLPrice:
    """Tests for the sync-positions endpoint SOL price calculation"""
    
    def test_sync_positions_endpoint_returns_200(self):
        """Test that sync-positions endpoint returns 200"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Sync positions endpoint returns 200")
    
    def test_sync_positions_returns_correct_structure(self):
        """Test sync-positions response structure"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_WALLET}")
        data = response.json()
        
        assert data.get("success") == True, "Expected success=true"
        assert "holdings_on_chain" in data, "Missing holdings_on_chain"
        assert "positions_synced" in data, "Missing positions_synced"
        
        print(f"✓ Sync response: {data['holdings_on_chain']} holdings, {data['positions_synced']} synced")


class TestAllTokensEndpoint:
    """Tests for the all-tokens endpoint"""
    
    def test_all_tokens_returns_4_tokens(self):
        """Test that all-tokens returns 4 tokens"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("count") == 4, f"Expected 4 tokens, got {data.get('count')}"
        
        # Verify token symbols
        symbols = [h.get("symbol") for h in data.get("holdings", [])]
        print(f"✓ All tokens: {symbols}")
    
    def test_all_tokens_total_value_is_reasonable(self):
        """Test that total value from all-tokens is reasonable"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_WALLET}")
        data = response.json()
        
        total_value = data.get("total_value_usd", 0)
        
        # Expected: ~$2-3 USD
        assert total_value < 10, f"Total value ${total_value} is too high"
        assert total_value > 0.5, f"Total value ${total_value} is too low"
        
        print(f"✓ All tokens total value: ${total_value:.2f} USD")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
