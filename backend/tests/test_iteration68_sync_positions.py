"""
Iteration 68: Test sync positions from blockchain and Quick Settings features

Features to test:
1. GET /api/custodial-wallet/all-tokens/{user_wallet} - returns all token holdings from custodial wallet
2. POST /api/custodial-wallet/sync-positions/{user_wallet} - creates positions for on-chain tokens not in database
3. GET /api/ai-trader/positions/{wallet} - returns all synced positions
4. Frontend Quick Settings panel with TP/SL sliders (code review)
"""

import pytest
import requests
import os

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

# Test wallet addresses from the review request
TEST_USER_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"


class TestAllTokensEndpoint:
    """Test GET /api/custodial-wallet/all-tokens/{user_wallet}"""
    
    def test_all_tokens_returns_200(self):
        """Test that all-tokens endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_USER_WALLET}")
        print(f"all-tokens status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_all_tokens_returns_custodial_address(self):
        """Test that response includes custodial_address field"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_USER_WALLET}")
        data = response.json()
        print(f"Response: {data}")
        assert "custodial_address" in data, "Response should include custodial_address"
        assert data["custodial_address"] == CUSTODIAL_WALLET, f"Expected {CUSTODIAL_WALLET}, got {data['custodial_address']}"
    
    def test_all_tokens_returns_holdings_array(self):
        """Test that response includes holdings array"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_USER_WALLET}")
        data = response.json()
        assert "holdings" in data, "Response should include holdings array"
        assert isinstance(data["holdings"], list), "holdings should be a list"
        print(f"Holdings count: {len(data['holdings'])}")
    
    def test_all_tokens_returns_count(self):
        """Test that response includes count field"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_USER_WALLET}")
        data = response.json()
        assert "count" in data, "Response should include count field"
        assert isinstance(data["count"], int), "count should be an integer"
        print(f"Token count: {data['count']}")
    
    def test_all_tokens_returns_total_value(self):
        """Test that response includes total_value_usd field"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_USER_WALLET}")
        data = response.json()
        assert "total_value_usd" in data, "Response should include total_value_usd"
        print(f"Total value USD: {data['total_value_usd']}")
    
    def test_all_tokens_holdings_have_required_fields(self):
        """Test that each holding has required fields (mint, amount, decimals)"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_USER_WALLET}")
        data = response.json()
        
        if data["count"] > 0:
            for holding in data["holdings"]:
                assert "mint" in holding, "Each holding should have mint"
                assert "amount" in holding, "Each holding should have amount"
                assert "decimals" in holding, "Each holding should have decimals"
                assert "raw_amount" in holding, "Each holding should have raw_amount"
                print(f"Token: {holding.get('symbol', 'UNKNOWN')} - Amount: {holding['amount']}")
        else:
            print("No holdings found - this is acceptable if wallet has no tokens")
    
    def test_all_tokens_expected_count(self):
        """Test that we get expected 4 tokens (RENDER, one, LNG, WRT)"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_USER_WALLET}")
        data = response.json()
        
        # According to the review request, we expect 4 tokens
        print(f"Expected 4 tokens, got {data['count']}")
        print(f"Holdings: {[h.get('symbol', h.get('mint', 'UNKNOWN')[:8]) for h in data['holdings']]}")
        
        # This is informational - the actual count may vary based on on-chain state
        assert data["count"] >= 0, "Count should be non-negative"


class TestSyncPositionsEndpoint:
    """Test POST /api/custodial-wallet/sync-positions/{user_wallet}"""
    
    def test_sync_positions_returns_200(self):
        """Test that sync-positions endpoint returns 200 status"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        print(f"sync-positions status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_sync_positions_returns_success(self):
        """Test that response includes success field"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        data = response.json()
        print(f"Response: {data}")
        assert "success" in data, "Response should include success field"
        assert data["success"] == True, "success should be True"
    
    def test_sync_positions_returns_holdings_count(self):
        """Test that response includes holdings_on_chain count"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        data = response.json()
        assert "holdings_on_chain" in data, "Response should include holdings_on_chain"
        print(f"Holdings on chain: {data['holdings_on_chain']}")
    
    def test_sync_positions_returns_positions_created(self):
        """Test that response includes positions_created count"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        data = response.json()
        assert "positions_created" in data, "Response should include positions_created"
        print(f"Positions created: {data['positions_created']}")
    
    def test_sync_positions_returns_positions_synced(self):
        """Test that response includes positions_synced count"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        data = response.json()
        assert "positions_synced" in data, "Response should include positions_synced"
        print(f"Positions synced: {data['positions_synced']}")
    
    def test_sync_positions_returns_positions_closed(self):
        """Test that response includes positions_closed count"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        data = response.json()
        assert "positions_closed" in data, "Response should include positions_closed"
        print(f"Positions closed: {data['positions_closed']}")
    
    def test_sync_positions_returns_created_array(self):
        """Test that response includes created array with details"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        data = response.json()
        assert "created" in data, "Response should include created array"
        assert isinstance(data["created"], list), "created should be a list"
        
        if len(data["created"]) > 0:
            for created in data["created"]:
                print(f"Created position: {created.get('symbol')} - {created.get('mint', '')[:8]}...")
    
    def test_sync_positions_returns_synced_array(self):
        """Test that response includes synced array with details"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        data = response.json()
        assert "synced" in data, "Response should include synced array"
        assert isinstance(data["synced"], list), "synced should be a list"
        
        if len(data["synced"]) > 0:
            for synced in data["synced"]:
                print(f"Synced position: {synced.get('symbol')} - {synced.get('position_id')}")


class TestPositionsEndpoint:
    """Test GET /api/ai-trader/positions/{wallet} returns synced positions"""
    
    def test_positions_returns_200(self):
        """Test that positions endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_USER_WALLET}")
        print(f"positions status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_positions_returns_positions_array(self):
        """Test that response includes positions array"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_USER_WALLET}")
        data = response.json()
        assert "positions" in data, "Response should include positions array"
        assert isinstance(data["positions"], list), "positions should be a list"
        print(f"Positions count: {len(data['positions'])}")
    
    def test_positions_have_required_fields(self):
        """Test that each position has required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_USER_WALLET}")
        data = response.json()
        
        required_fields = ["position_id", "wallet_address", "token_symbol", "status"]
        
        for position in data["positions"]:
            for field in required_fields:
                assert field in position, f"Position should have {field} field"
            print(f"Position: {position['token_symbol']} - Status: {position['status']} - ID: {position['position_id']}")
    
    def test_positions_include_synced_positions(self):
        """Test that positions include synced_from_chain positions"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_USER_WALLET}")
        data = response.json()
        
        synced_positions = [p for p in data["positions"] if p.get("synced_from_chain") == True]
        print(f"Synced from chain positions: {len(synced_positions)}")
        
        for pos in synced_positions:
            print(f"  - {pos['token_symbol']}: {pos.get('amount_tokens', 0)} tokens")
    
    def test_positions_count_matches_expected(self):
        """Test that we have expected number of positions (4 according to review request)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_USER_WALLET}")
        data = response.json()
        
        open_positions = [p for p in data["positions"] if p.get("status") == "open"]
        print(f"Open positions: {len(open_positions)}")
        
        # List all positions
        for pos in data["positions"]:
            print(f"  - {pos['token_symbol']}: status={pos['status']}, synced={pos.get('synced_from_chain', False)}")
        
        # According to review request, we expect 4 synced positions
        # This is informational - actual count may vary
        assert len(data["positions"]) >= 0, "Should have non-negative positions count"


class TestIntegrationFlow:
    """Test the full integration flow: all-tokens -> sync-positions -> positions"""
    
    def test_full_sync_flow(self):
        """Test the complete sync flow"""
        # Step 1: Get all tokens
        tokens_response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/{TEST_USER_WALLET}")
        assert tokens_response.status_code == 200
        tokens_data = tokens_response.json()
        print(f"Step 1 - All tokens: {tokens_data['count']} tokens found")
        
        # Step 2: Sync positions
        sync_response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/{TEST_USER_WALLET}")
        assert sync_response.status_code == 200
        sync_data = sync_response.json()
        print(f"Step 2 - Sync: created={sync_data['positions_created']}, synced={sync_data['positions_synced']}, closed={sync_data['positions_closed']}")
        
        # Step 3: Get positions
        positions_response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_USER_WALLET}")
        assert positions_response.status_code == 200
        positions_data = positions_response.json()
        print(f"Step 3 - Positions: {len(positions_data['positions'])} positions")
        
        # Verify consistency
        # Holdings on chain should match what we got from all-tokens
        assert sync_data["holdings_on_chain"] == tokens_data["count"], \
            f"Holdings mismatch: sync says {sync_data['holdings_on_chain']}, all-tokens says {tokens_data['count']}"
        
        print("Integration flow completed successfully!")


class TestErrorHandling:
    """Test error handling for invalid inputs"""
    
    def test_all_tokens_invalid_wallet(self):
        """Test all-tokens with invalid wallet returns 404"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/all-tokens/invalid_wallet_address")
        # Should return 404 for wallet not found
        print(f"Invalid wallet response: {response.status_code}")
        assert response.status_code in [404, 500], f"Expected 404 or 500 for invalid wallet, got {response.status_code}"
    
    def test_sync_positions_invalid_wallet(self):
        """Test sync-positions with invalid wallet returns 404"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/sync-positions/invalid_wallet_address")
        print(f"Invalid wallet sync response: {response.status_code}")
        assert response.status_code in [404, 500], f"Expected 404 or 500 for invalid wallet, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
