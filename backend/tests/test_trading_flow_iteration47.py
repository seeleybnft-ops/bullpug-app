"""
Test Trading Flow for Bullpug Trading Bot - Iteration 47
Tests: Tokens tab, signals, positions, delete positions, alerts
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pug-trader-hub.preview.emergentagent.com').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestNewPairsEndpoint:
    """Test GET /api/ai-trader/new-pairs - Returns bonded pairs with token_mint"""
    
    def test_new_pairs_returns_ok(self):
        """Verify new-pairs endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/ai-trader/new-pairs returns 200")
    
    def test_new_pairs_structure(self):
        """Verify new-pairs returns pairs array with required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        assert response.status_code == 200
        
        data = response.json()
        assert "pairs" in data, "Response should have 'pairs' key"
        assert "count" in data, "Response should have 'count' key"
        assert "disclaimer" in data, "Response should have 'disclaimer' key"
        
        # If pairs exist, check structure
        if data["pairs"]:
            pair = data["pairs"][0]
            assert "symbol" in pair, "Pair should have 'symbol'"
            assert "contract_address" in pair, "Pair should have 'contract_address' (token_mint)"
            assert "platform" in pair, "Pair should have 'platform'"
            assert "is_bonded" in pair, "Pair should have 'is_bonded' flag"
            assert pair["is_bonded"] == True, "Pairs should be bonded"
            print(f"✓ New pairs structure valid, found {data['count']} pairs")
        else:
            print("✓ New pairs structure valid (0 pairs found - depends on market)")


class TestCoinRecommendations:
    """Test GET /api/ai-suggestions/coin-recommendations - Safe and volatile picks"""
    
    def test_recommendations_returns_ok(self):
        """Verify coin-recommendations endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/ai-suggestions/coin-recommendations returns 200")
    
    def test_recommendations_has_safe_picks(self):
        """Verify response has safe_picks array"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        
        data = response.json()
        assert "safe_picks" in data, "Response should have 'safe_picks'"
        assert isinstance(data["safe_picks"], list), "safe_picks should be a list"
        print(f"✓ Found {len(data['safe_picks'])} safe picks")
    
    def test_recommendations_has_volatile_picks(self):
        """Verify response has volatile_picks array"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        
        data = response.json()
        assert "volatile_picks" in data, "Response should have 'volatile_picks'"
        assert isinstance(data["volatile_picks"], list), "volatile_picks should be a list"
        print(f"✓ Found {len(data['volatile_picks'])} volatile picks")
    
    def test_recommendations_pick_structure(self):
        """Verify pick structure has required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check safe pick structure
        if data["safe_picks"]:
            pick = data["safe_picks"][0]
            assert "symbol" in pick, "Pick should have 'symbol'"
            assert "price" in pick, "Pick should have 'price'"
            assert "contract_address" in pick, "Pick should have 'contract_address'"
            assert "dex_url" in pick, "Pick should have 'dex_url'"
            assert "risk_level" in pick, "Pick should have 'risk_level'"
            print(f"✓ Safe pick structure valid: {pick['symbol']}")
        
        # Check volatile pick structure
        if data["volatile_picks"]:
            pick = data["volatile_picks"][0]
            assert "symbol" in pick, "Volatile pick should have 'symbol'"
            assert "contract_address" in pick, "Volatile pick should have 'contract_address'"
            print(f"✓ Volatile pick structure valid: {pick['symbol']}")


class TestAnalyzeToken:
    """Test POST /api/ai-trader/analyze/{symbol} - Generate trading signal"""
    
    def test_analyze_sol_returns_ok(self):
        """Verify analyze endpoint returns 200 for SOL"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/SOL",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ POST /api/ai-trader/analyze/SOL returns 200")
    
    def test_analyze_returns_analysis(self):
        """Verify analyze returns technical analysis"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/SOL",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should have either signal or analysis
        assert "signal" in data or "analysis" in data, "Response should have signal or analysis"
        assert "message" in data, "Response should have message"
        print(f"✓ Analyze returns: {data.get('message', 'signal generated')}")
    
    def test_analyze_bonk_returns_ok(self):
        """Verify analyze works for BONK (high risk token)"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/BONK",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200
        print("✓ POST /api/ai-trader/analyze/BONK returns 200")
    
    def test_analyze_with_contract_address(self):
        """Verify analyze works with custom contract address"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/CUSTOMTOKEN",
            params={
                "wallet_address": TEST_WALLET,
                "contract_address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK address
            }
        )
        assert response.status_code == 200
        print("✓ Analyze works with custom contract address")


class TestPositions:
    """Test GET /api/ai-trader/positions/{wallet} - Returns open positions"""
    
    def test_positions_returns_ok(self):
        """Verify positions endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/ai-trader/positions returns 200")
    
    def test_positions_structure(self):
        """Verify positions response structure"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        assert "positions" in data, "Response should have 'positions'"
        assert "count" in data, "Response should have 'count'"
        assert "sol_price_usd" in data, "Response should have 'sol_price_usd'"
        
        print(f"✓ Positions structure valid, found {data['count']} positions")
    
    def test_positions_have_pnl(self):
        """Verify positions have P&L calculations"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        if data["positions"]:
            pos = data["positions"][0]
            # Check P&L fields exist
            assert "unrealized_pnl_pct" in pos, "Position should have unrealized_pnl_pct"
            assert "unrealized_pnl_sol" in pos, "Position should have unrealized_pnl_sol"
            assert "current_price" in pos, "Position should have current_price"
            print(f"✓ Position has P&L: {pos['unrealized_pnl_pct']}%")


class TestDeletePosition:
    """Test DELETE /api/ai-trader/delete-position - Delete positions"""
    
    def test_create_and_delete_position(self):
        """Test creating a position and then deleting it"""
        test_wallet = "test_wallet_delete_test_47"
        
        # Step 1: Create a test position
        create_response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={
                "wallet_address": test_wallet,
                "token_symbol": "TESTDELETE",
                "tx_signature": "test_sig_delete_47",
                "input_sol": 0.1,
                "output_amount": 1000,
                "entry_price": 0.0001
            }
        )
        assert create_response.status_code == 200, "Position creation should succeed"
        create_data = create_response.json()
        assert create_data["success"] == True
        position_id = create_data["position_id"]
        print(f"✓ Created test position: {position_id}")
        
        # Step 2: Verify position exists
        verify_response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{test_wallet}")
        assert verify_response.status_code == 200
        positions_before = len(verify_response.json()["positions"])
        print(f"✓ Positions before delete: {positions_before}")
        
        # Step 3: Delete the position
        delete_response = requests.delete(
            f"{BASE_URL}/api/ai-trader/delete-position",
            params={
                "wallet_address": test_wallet,
                "position_id": position_id
            }
        )
        assert delete_response.status_code == 200, f"Delete should succeed, got {delete_response.status_code}"
        delete_data = delete_response.json()
        assert delete_data["success"] == True
        assert delete_data["message"] == "Position removed"
        print(f"✓ Deleted position: {position_id}")
        
        # Step 4: Verify position is deleted
        verify_after = requests.get(f"{BASE_URL}/api/ai-trader/positions/{test_wallet}")
        positions_after = len(verify_after.json()["positions"])
        assert positions_after < positions_before, "Position count should decrease"
        print(f"✓ Positions after delete: {positions_after}")
    
    def test_delete_nonexistent_position(self):
        """Test deleting a position that doesn't exist returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/ai-trader/delete-position",
            params={
                "wallet_address": "nonexistent_wallet",
                "position_id": "nonexistent_position_id"
            }
        )
        assert response.status_code == 404, f"Expected 404 for nonexistent position, got {response.status_code}"
        print("✓ Delete nonexistent position returns 404")


class TestAlerts:
    """Test alerts endpoints - Create, get, and breakout scan"""
    
    def test_get_alerts_returns_ok(self):
        """Verify get alerts endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/alerts/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/ai-trader/alerts returns 200")
    
    def test_alerts_structure(self):
        """Verify alerts response structure"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/alerts/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        assert "alerts" in data, "Response should have 'alerts'"
        assert "count" in data, "Response should have 'count'"
        print(f"✓ Alerts structure valid, found {data['count']} alerts")
    
    def test_alert_has_required_fields(self):
        """Verify alert structure"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/alerts/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        if data["alerts"]:
            alert = data["alerts"][0]
            assert "alert_id" in alert, "Alert should have alert_id"
            assert "symbol" in alert, "Alert should have symbol"
            assert "alert_type" in alert, "Alert should have alert_type"
            assert "token_mint" in alert or alert.get("token_mint") is None, "Alert can have token_mint"
            print(f"✓ Alert structure valid: {alert['symbol']} - {alert['alert_type']}")
    
    def test_create_alert(self):
        """Test creating an alert"""
        test_wallet = "test_wallet_alert_47"
        
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/create",
            json={
                "wallet_address": test_wallet,
                "symbol": "TESTALERT",
                "alert_type": "breakout_up",
                "token_mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True
        assert "alert_id" in data
        print(f"✓ Created alert: {data['alert_id']}")
    
    def test_breakout_scan(self):
        """Test breakout scan endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/breakout-scan",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "success" in data
        assert "count" in data
        print(f"✓ Breakout scan completed, found {data['count']} candidates")


class TestTokensEndpoint:
    """Test GET /api/ai-trader/tokens - Get available tokens"""
    
    def test_tokens_returns_ok(self):
        """Verify tokens endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/ai-trader/tokens returns 200")
    
    def test_tokens_structure(self):
        """Verify tokens response structure"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        
        data = response.json()
        assert "safer_tokens" in data, "Response should have 'safer_tokens'"
        assert "high_risk_tokens" in data, "Response should have 'high_risk_tokens'"
        assert "position_limits" in data, "Response should have 'position_limits'"
        
        print(f"✓ Found {len(data['safer_tokens'])} safer tokens, {len(data['high_risk_tokens'])} high risk tokens")
    
    def test_tokens_have_mint_address(self):
        """Verify tokens have mint addresses"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        
        data = response.json()
        if data["safer_tokens"]:
            token = data["safer_tokens"][0]
            assert "mint" in token, "Token should have 'mint' address"
            assert "symbol" in token, "Token should have 'symbol'"
            assert "price_usd" in token, "Token should have 'price_usd'"
            print(f"✓ Token structure valid: {token['symbol']} - {token['mint'][:20]}...")


class TestEndToEndFlow:
    """Test complete trading flow end-to-end"""
    
    def test_full_trading_flow(self):
        """Test complete flow: tokens -> analyze -> position -> delete"""
        test_wallet = "test_e2e_flow_47"
        
        # Step 1: Get available tokens
        tokens_response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert tokens_response.status_code == 200
        tokens = tokens_response.json()
        assert len(tokens["safer_tokens"]) > 0
        print("✓ Step 1: Got available tokens")
        
        # Step 2: Analyze a token
        analyze_response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/SOL",
            params={"wallet_address": test_wallet}
        )
        assert analyze_response.status_code == 200
        print("✓ Step 2: Analyzed token")
        
        # Step 3: Create a position (simulating buy)
        position_response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={
                "wallet_address": test_wallet,
                "token_symbol": "E2ETEST",
                "tx_signature": "test_e2e_sig",
                "input_sol": 0.1,
                "output_amount": 500,
                "entry_price": 0.002
            }
        )
        assert position_response.status_code == 200
        position_id = position_response.json()["position_id"]
        print(f"✓ Step 3: Created position {position_id}")
        
        # Step 4: Check positions
        positions_response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{test_wallet}")
        assert positions_response.status_code == 200
        positions = positions_response.json()["positions"]
        assert len(positions) > 0
        print(f"✓ Step 4: Verified position exists ({len(positions)} positions)")
        
        # Step 5: Create an alert
        alert_response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/create",
            json={
                "wallet_address": test_wallet,
                "symbol": "E2ETEST",
                "alert_type": "price_above",
                "target_price": 0.003
            }
        )
        assert alert_response.status_code == 200
        print("✓ Step 5: Created alert")
        
        # Step 6: Delete position
        delete_response = requests.delete(
            f"{BASE_URL}/api/ai-trader/delete-position",
            params={
                "wallet_address": test_wallet,
                "position_id": position_id
            }
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] == True
        print("✓ Step 6: Deleted position")
        
        print("\n✅ Complete E2E flow passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
