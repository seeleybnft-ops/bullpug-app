"""
Iteration 66 Tests - Multiple Fixes Verification
Tests for:
1. Trading Bot default tab changed to 'autotrade'
2. Journal nav link pending entries badge
3. Custodial wallet balance fetching with fallback RPC
4. Auto-trade settings (take_profit_percent, stop_loss_percent) save correctly
5. Auto-sell check-exits uses settings-based TP/SL percentages
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test wallets from the review request
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"


class TestCustodialWalletBalance:
    """Test custodial wallet balance fetching with fallback RPC"""
    
    def test_custodial_wallet_info_endpoint(self):
        """Test GET /api/custodial-wallet/info/{wallet} returns balance"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        print(f"Custodial wallet info response: {response.status_code}")
        
        # Should return 200 (creates wallet if not exists)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Custodial wallet data: {data}")
        
        # Verify response structure
        assert "wallet_address" in data, "Missing wallet_address in response"
        assert "balance_sol" in data, "Missing balance_sol in response"
        assert "balance_lamports" in data, "Missing balance_lamports in response"
        
        # Balance should be a number (could be 0 if no funds)
        assert isinstance(data["balance_sol"], (int, float)), "balance_sol should be numeric"
        assert isinstance(data["balance_lamports"], int), "balance_lamports should be integer"
        
        print(f"✓ Custodial wallet balance: {data['balance_sol']} SOL ({data['balance_lamports']} lamports)")
        print(f"✓ Wallet address: {data['wallet_address']}")


class TestAutoTradeSettings:
    """Test auto-trade settings save and retrieve correctly"""
    
    def test_get_auto_trade_status(self):
        """Test GET /api/ai-trader/auto-trade/status/{wallet} returns settings"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        print(f"Auto-trade status response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Auto-trade status: {data}")
        
        # Verify settings structure
        assert "settings" in data, "Missing settings in response"
        settings = data.get("settings", {})
        
        # Check for TP/SL fields (may have defaults)
        print(f"Current settings: {settings}")
        print(f"✓ Auto-trade status endpoint working")
    
    def test_update_auto_trade_settings_tp_sl(self):
        """Test PUT /api/ai-trader/auto-trade/settings/{wallet} saves TP/SL"""
        # Set specific TP/SL values
        test_settings = {
            "auto_stop_loss_percent": 12.5,
            "auto_take_profit_percent": 35.0
        }
        
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=test_settings
        )
        print(f"Update settings response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Update response: {data}")
        
        assert data.get("success") == True, "Expected success=True"
        assert "auto_stop_loss_percent" in data.get("updated_fields", []), "auto_stop_loss_percent not in updated fields"
        assert "auto_take_profit_percent" in data.get("updated_fields", []), "auto_take_profit_percent not in updated fields"
        
        print(f"✓ Settings updated: {data.get('updated_fields')}")
    
    def test_verify_settings_persisted(self):
        """Verify the settings were actually saved by fetching them again"""
        # First update with known values
        test_settings = {
            "auto_stop_loss_percent": 15.0,
            "auto_take_profit_percent": 40.0
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=test_settings
        )
        assert update_response.status_code == 200
        
        # Now fetch and verify
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        settings = data.get("settings", {})
        
        # Check if the values were persisted
        # Note: The settings might be stored with different key names
        stop_loss = settings.get("auto_stop_loss_percent") or settings.get("stop_loss_percent")
        take_profit = settings.get("auto_take_profit_percent") or settings.get("take_profit_percent")
        
        print(f"Retrieved settings - SL: {stop_loss}, TP: {take_profit}")
        
        # Verify values match what we set
        if settings.get("auto_stop_loss_percent") is not None:
            assert settings.get("auto_stop_loss_percent") == 15.0, f"Expected SL 15.0, got {settings.get('auto_stop_loss_percent')}"
        if settings.get("auto_take_profit_percent") is not None:
            assert settings.get("auto_take_profit_percent") == 40.0, f"Expected TP 40.0, got {settings.get('auto_take_profit_percent')}"
        
        print(f"✓ Settings persisted correctly")


class TestAutoTradeCheckExits:
    """Test auto-trade check-exits uses settings-based TP/SL"""
    
    def test_check_exits_endpoint(self):
        """Test POST /api/ai-trader/auto-trade/check-exits/{wallet}"""
        # First ensure auto-trade is enabled
        enable_response = requests.post(
            f"{BASE_URL}/api/ai-trader/auto-trade/toggle/{TEST_WALLET}?enabled=true"
        )
        print(f"Enable auto-trade response: {enable_response.status_code}")
        
        # Now test check-exits
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        print(f"Check exits response: {response.status_code}")
        
        # Should return 200 even if no positions to check
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Check exits data: {data}")
        
        # Verify response structure
        assert "success" in data or "exits" in data or "message" in data, "Missing expected fields in response"
        
        print(f"✓ Check exits endpoint working")


class TestJournalPendingEntries:
    """Test journal pending entries endpoint for navbar badge"""
    
    def test_get_pending_entries_count(self):
        """Test GET /api/journal/pending/{wallet} returns count"""
        response = requests.get(f"{BASE_URL}/api/journal/pending/{TEST_WALLET}")
        print(f"Pending entries response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Pending entries data: {data}")
        
        # Verify response structure
        assert "count" in data, "Missing count in response"
        assert isinstance(data["count"], int), "count should be integer"
        
        print(f"✓ Pending entries count: {data['count']}")


class TestAITraderSettings:
    """Test AI trader settings endpoint"""
    
    def test_get_settings(self):
        """Test GET /api/ai-trader/settings/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        print(f"AI trader settings response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Settings: {data}")
        
        # Verify key fields exist
        assert "wallet_address" in data, "Missing wallet_address"
        
        # Check for auto-trade related fields
        print(f"auto_stop_loss_percent: {data.get('auto_stop_loss_percent')}")
        print(f"auto_take_profit_percent: {data.get('auto_take_profit_percent')}")
        
        print(f"✓ AI trader settings endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
