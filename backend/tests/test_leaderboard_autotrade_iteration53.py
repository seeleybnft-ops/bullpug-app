"""
Test for Iteration 53: Leaderboard Wallet Linking & Auto-Trade Advanced Features

Features tested:
1. Leaderboard with wallet_address field
2. Wallet link status endpoint
3. Link wallet endpoint
4. Unlink wallet endpoint
5. Auto-trade settings with new advanced fields
6. Update trailing stops endpoint
7. Check scale-in endpoint
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLeaderboardWalletLinking:
    """Tests for leaderboard wallet linking feature"""
    
    def test_leaderboard_returns_wallet_address_field(self):
        """Test /api/leaderboard returns wallet_address in entries"""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert "leaderboard" in data
        assert "cycle_start" in data
        assert "next_payout" in data
        assert "days_until_reset" in data
        
        # Each entry should have wallet_address field
        for entry in data["leaderboard"]:
            assert "wallet_address" in entry
            assert "player_name" in entry
            assert "score" in entry
    
    def test_wallet_link_status_endpoint(self):
        """Test /api/leaderboard/wallet-link/{player_name} returns link status"""
        response = requests.get(f"{BASE_URL}/api/leaderboard/wallet-link/Guardian")
        assert response.status_code == 200
        data = response.json()
        
        assert "player_name" in data
        assert data["player_name"] == "Guardian"
        assert "wallet_address" in data
        assert "linked" in data
        assert isinstance(data["linked"], bool)
    
    def test_wallet_link_status_for_unknown_player(self):
        """Test wallet-link returns proper response for non-existent player"""
        response = requests.get(f"{BASE_URL}/api/leaderboard/wallet-link/NONEXISTENT_PLAYER_XYZ")
        assert response.status_code == 200
        data = response.json()
        
        assert data["wallet_address"] is None
        assert data["linked"] == False
    
    def test_link_wallet_endpoint(self):
        """Test POST /api/leaderboard/link-wallet links wallet to player"""
        response = requests.post(
            f"{BASE_URL}/api/leaderboard/link-wallet",
            json={
                "player_name": "TEST_PLAYER_LINK_53",
                "wallet_address": "TEST_WALLET_LINK_ADDRESS_53"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["player_name"] == "TEST_PLAYER_LINK_53"
        assert data["wallet_address"] == "TEST_WALLET_LINK_ADDRESS_53"
        assert "message" in data
        
        # Verify link status
        verify_response = requests.get(f"{BASE_URL}/api/leaderboard/wallet-link/TEST_PLAYER_LINK_53")
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["linked"] == True
        assert verify_data["wallet_address"] == "TEST_WALLET_LINK_ADDRESS_53"
    
    def test_link_wallet_requires_player_name(self):
        """Test link-wallet returns error when player_name missing"""
        response = requests.post(
            f"{BASE_URL}/api/leaderboard/link-wallet",
            json={"wallet_address": "SOME_WALLET"}
        )
        assert response.status_code in [400, 422]
    
    def test_link_wallet_requires_wallet_address(self):
        """Test link-wallet returns error when wallet_address missing"""
        response = requests.post(
            f"{BASE_URL}/api/leaderboard/link-wallet",
            json={"player_name": "SOME_PLAYER"}
        )
        assert response.status_code in [400, 422]
    
    def test_unlink_wallet_endpoint(self):
        """Test POST /api/leaderboard/unlink-wallet unlinks wallet"""
        # First link a wallet
        requests.post(
            f"{BASE_URL}/api/leaderboard/link-wallet",
            json={
                "player_name": "TEST_PLAYER_UNLINK_53",
                "wallet_address": "TEST_WALLET_UNLINK_ADDRESS_53"
            }
        )
        
        # Now unlink
        response = requests.post(
            f"{BASE_URL}/api/leaderboard/unlink-wallet",
            json={"player_name": "TEST_PLAYER_UNLINK_53"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # Verify unlinked
        verify_response = requests.get(f"{BASE_URL}/api/leaderboard/wallet-link/TEST_PLAYER_UNLINK_53")
        verify_data = verify_response.json()
        assert verify_data["linked"] == False
        assert verify_data["wallet_address"] is None


class TestAutoTradeAdvancedSettings:
    """Tests for auto-trade advanced settings (trailing stop, scale-in)"""
    
    TEST_WALLET = "TEST_AUTOTRADE_ADVANCED_53"
    
    def test_settings_include_advanced_fields(self):
        """Test settings endpoint returns new advanced auto-trade fields"""
        # Use a fresh wallet to ensure default values
        fresh_wallet = "TEST_FRESH_WALLET_ADVANCED_53"
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{fresh_wallet}")
        assert response.status_code == 200
        data = response.json()
        
        # New advanced fields MUST be present
        assert "auto_trailing_stop_enabled" in data
        assert "auto_trailing_stop_percent" in data
        assert "auto_scale_in_enabled" in data
        assert "auto_scale_in_threshold" in data
        assert "auto_scale_in_max_adds" in data
        assert "auto_avoid_volatile_hours" in data
        assert "auto_profit_target_alert" in data
        
        # Default values for a fresh wallet
        assert data["auto_trailing_stop_enabled"] == False
        assert data["auto_trailing_stop_percent"] == 5.0
        assert data["auto_scale_in_enabled"] == False
        assert data["auto_scale_in_threshold"] == 5.0
        assert data["auto_scale_in_max_adds"] == 2
    
    def test_save_advanced_settings(self):
        """Test saving advanced auto-trade settings"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": self.TEST_WALLET,
                "auto_trailing_stop_enabled": True,
                "auto_trailing_stop_percent": 7.5,
                "auto_scale_in_enabled": True,
                "auto_scale_in_threshold": 6.0,
                "auto_scale_in_max_adds": 3,
                "auto_avoid_volatile_hours": False,
                "auto_profit_target_alert": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # Verify settings saved
        verify_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{self.TEST_WALLET}")
        verify_data = verify_response.json()
        assert verify_data["auto_trailing_stop_enabled"] == True
        assert verify_data["auto_trailing_stop_percent"] == 7.5
        assert verify_data["auto_scale_in_enabled"] == True
        assert verify_data["auto_scale_in_threshold"] == 6.0
        assert verify_data["auto_scale_in_max_adds"] == 3
    
    def test_update_trailing_stops_endpoint_exists(self):
        """Test /api/ai-trader/auto-trade/update-trailing-stops/{wallet} exists"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/auto-trade/update-trailing-stops/{self.TEST_WALLET}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert "message" in data
        assert "updated" in data
    
    def test_update_trailing_stops_disabled_by_default(self):
        """Test trailing stops returns 'not enabled' when disabled"""
        # First ensure it's disabled
        requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": "TEST_TRAILING_DISABLED_53",
                "auto_trailing_stop_enabled": False
            }
        )
        
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/auto-trade/update-trailing-stops/TEST_TRAILING_DISABLED_53"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert "not enabled" in data["message"].lower()
    
    def test_check_scale_in_endpoint_exists(self):
        """Test /api/ai-trader/auto-trade/check-scale-in/{wallet} exists"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/auto-trade/check-scale-in/{self.TEST_WALLET}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert "message" in data
        assert "scaled" in data
    
    def test_check_scale_in_disabled_by_default(self):
        """Test scale-in returns 'not enabled' when disabled"""
        # First ensure it's disabled
        requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": "TEST_SCALEIN_DISABLED_53",
                "auto_scale_in_enabled": False
            }
        )
        
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/auto-trade/check-scale-in/TEST_SCALEIN_DISABLED_53"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert "not enabled" in data["message"].lower()


class TestAutoTradeStatusAndLogs:
    """Tests for auto-trade status and logs endpoints"""
    
    TEST_WALLET = "TEST_STATUS_LOGS_53"
    
    def test_auto_trade_status_endpoint(self):
        """Test /api/ai-trader/auto-trade/status/{wallet} returns status"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{self.TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Should have these fields
        assert "auto_trade_enabled" in data or "enabled" in data or "status" in data
    
    def test_auto_trade_logs_endpoint(self):
        """Test /api/ai-trader/auto-trade/logs/{wallet} returns logs"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/logs/{self.TEST_WALLET}?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        assert "logs" in data
        assert isinstance(data["logs"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
