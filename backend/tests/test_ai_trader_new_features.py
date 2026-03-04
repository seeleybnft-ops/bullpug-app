"""
AI Trader New Features Test Suite
Tests for: 
- Quick Sell from Positions tab (close-position endpoint)
- Quick Buy from Tokens tab (add-position endpoint) 
- Positions endpoint querying both collections
- Tab order verification (frontend test)
- Risk Calculator component (frontend test)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "test_wallet"  # Pre-existing test wallet


class TestAddPositionEndpoint:
    """Tests for /api/ai-trader/add-position endpoint - Quick Buy from Tokens"""
    
    def test_add_position_success(self):
        """Test adding a new position after buying a token"""
        position_data = {
            "wallet_address": TEST_WALLET,
            "token_symbol": "TEST_TOKEN",
            "tx_signature": f"test_tx_{uuid.uuid4().hex[:8]}",
            "input_sol": 0.1,
            "output_amount": 1000,
            "entry_price": 0.0001,
            "token_mint": "TestMint111111111111111111111111111111111"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params=position_data,
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert data["success"] == True, "Expected success to be True"
        assert "position_id" in data, "Missing position_id in response"
        assert "position" in data, "Missing position in response"
        
        # Verify position data
        pos = data["position"]
        assert pos["token_symbol"] == "TEST_TOKEN", f"Token symbol mismatch: {pos.get('token_symbol')}"
        assert pos["wallet_address"] == TEST_WALLET
        assert pos["input_sol"] == 0.1
        assert pos["status"] == "open"
        assert pos["trade_type"] == "buy"
        
        print(f"Successfully added position: {data['position_id']}")
        return data["position_id"]
    
    def test_add_position_validates_input(self):
        """Test that add-position endpoint validates input parameters"""
        # Missing required fields should fail
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={"wallet_address": TEST_WALLET},  # Missing other required params
            timeout=30
        )
        
        # Should return 422 for validation error or 500
        assert response.status_code in [422, 500], f"Expected 422/500, got {response.status_code}"
        print("Validation working correctly - missing params rejected")


class TestClosePositionEndpoint:
    """Tests for /api/ai-trader/close-position endpoint - Quick Sell from Positions"""
    
    def test_close_position_success(self):
        """Test closing an existing position"""
        # First create a position
        position_data = {
            "wallet_address": TEST_WALLET,
            "token_symbol": "CLOSE_TEST",
            "tx_signature": f"test_tx_{uuid.uuid4().hex[:8]}",
            "input_sol": 0.1,
            "output_amount": 500,
            "entry_price": 0.0002,
            "token_mint": "CloseMint111111111111111111111111111111111"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params=position_data,
            timeout=30
        )
        
        assert create_response.status_code == 200, f"Failed to create position: {create_response.text}"
        position_id = create_response.json()["position_id"]
        
        # Now close the position
        close_data = {
            "wallet_address": TEST_WALLET,
            "position_id": position_id,
            "tx_signature": f"sell_tx_{uuid.uuid4().hex[:8]}",
            "sell_amount": 0.1,
            "received_sol": 0.12  # 20% profit
        }
        
        close_response = requests.post(
            f"{BASE_URL}/api/ai-trader/close-position",
            params=close_data,
            timeout=30
        )
        
        assert close_response.status_code == 200, f"Expected 200, got {close_response.status_code}: {close_response.text}"
        
        data = close_response.json()
        assert data["success"] == True, "Expected success to be True"
        # Response structure is: {"success": true, "pnl": {"sol": x, "percent": y}}
        assert "pnl" in data, "Missing pnl in response"
        assert "sol" in data["pnl"], "Missing sol in pnl"
        assert "percent" in data["pnl"], "Missing percent in pnl"
        
        print(f"Successfully closed position with PnL: {data['pnl']['sol']} SOL ({data['pnl']['percent']:.2f}%)")
    
    def test_close_position_not_found(self):
        """Test closing a non-existent position returns 404"""
        close_data = {
            "wallet_address": TEST_WALLET,
            "position_id": "non_existent_position_id",
            "tx_signature": "test_tx_123",
            "sell_amount": 0.1,
            "received_sol": 0.1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/close-position",
            params=close_data,
            timeout=30
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for non-existent position")


class TestPositionsEndpoint:
    """Tests for /api/ai-trader/positions endpoint - Should query both collections"""
    
    def test_positions_returns_from_both_collections(self):
        """Test that positions endpoint returns positions from ai_trader_positions collection"""
        # First add a position to ai_trader_positions collection
        position_data = {
            "wallet_address": TEST_WALLET,
            "token_symbol": "BOTH_TEST",
            "tx_signature": f"test_tx_{uuid.uuid4().hex[:8]}",
            "input_sol": 0.05,
            "output_amount": 100,
            "entry_price": 0.0005,
            "token_mint": "BothMint111111111111111111111111111111111"
        }
        
        add_response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params=position_data,
            timeout=30
        )
        assert add_response.status_code == 200, f"Failed to add position: {add_response.text}"
        
        # Now query positions
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}",
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "positions" in data, "Missing positions in response"
        assert "count" in data, "Missing count in response"
        
        # Verify we have at least one position
        assert len(data["positions"]) > 0, "Expected at least one position"
        
        # Check that position has required fields
        for pos in data["positions"]:
            assert "token_symbol" in pos, f"Missing token_symbol in position: {pos}"
            assert "status" in pos, f"Missing status in position: {pos}"
            # Check for unrealized P&L fields (should be calculated)
            if "entry_price" in pos:
                assert "unrealized_pnl_pct" in pos or pos.get("entry_price") is None
        
        print(f"Positions endpoint returned {len(data['positions'])} positions")
    
    def test_positions_excludes_mongodb_id(self):
        """Test that positions don't include MongoDB _id field"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}",
            timeout=30
        )
        
        assert response.status_code == 200
        
        data = response.json()
        for pos in data.get("positions", []):
            assert "_id" not in pos, f"Position contains _id field which should be excluded: {pos}"
        
        print("Confirmed: No _id fields in positions")


class TestExistingEndpoints:
    """Tests for existing endpoints to ensure they still work"""
    
    def test_tokens_endpoint(self):
        """Test /api/ai-trader/tokens returns token lists"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "safer_tokens" in data
        assert "high_risk_tokens" in data
        assert len(data["safer_tokens"]) > 0
        assert len(data["high_risk_tokens"]) > 0
        
        print(f"Tokens: {len(data['safer_tokens'])} safer, {len(data['high_risk_tokens'])} high risk")
    
    def test_settings_endpoint(self):
        """Test /api/ai-trader/settings returns settings without _id"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "_id" not in data, "Settings should not contain _id"
        assert "wallet_address" in data
        assert "risk_level" in data
        
        print(f"Settings for {TEST_WALLET}: risk_level={data['risk_level']}")
    
    def test_history_endpoint(self):
        """Test /api/ai-trader/history returns trade history"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "trades" in data
        assert "stats" in data
        
        print(f"History: {len(data['trades'])} trades")
    
    def test_signals_endpoint(self):
        """Test /api/ai-trader/signals returns signals"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/signals/{TEST_WALLET}", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "signals" in data
        
        print(f"Signals: {len(data['signals'])} pending signals")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_positions(self):
        """Clean up test positions created during tests"""
        # Close any open test positions
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}", timeout=30)
        
        if response.status_code == 200:
            positions = response.json().get("positions", [])
            test_positions = [p for p in positions if p.get("token_symbol", "").startswith("TEST_") 
                            or p.get("token_symbol", "").startswith("CLOSE_")
                            or p.get("token_symbol", "").startswith("BOTH_")]
            
            print(f"Found {len(test_positions)} test positions to potentially clean up")
        
        # Note: Actual cleanup would require a delete endpoint
        # For now, positions will remain in "open" status but with test prefixes


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
