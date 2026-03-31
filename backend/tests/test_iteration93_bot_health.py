"""
Iteration 93: Bot Health Dashboard Tests
Tests the new /api/admin/bot-health endpoint and related features
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
NON_ADMIN_WALLET = "FakeWalletForTestingPurposesOnly123456"


class TestBotHealthEndpoint:
    """Tests for GET /api/admin/bot-health endpoint"""
    
    def test_bot_health_returns_200_for_admin(self):
        """Test that admin wallet gets 200 response"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Bot health endpoint returns 200 for admin wallet")
    
    def test_bot_health_returns_403_for_non_admin(self):
        """Test that non-admin wallet gets 403 response"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={NON_ADMIN_WALLET}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Not authorized"
        print("PASS: Bot health endpoint returns 403 for non-admin wallet")
    
    def test_bot_health_response_structure(self):
        """Test that response has all required fields"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Check required top-level fields
        required_fields = ["checked_at", "funding", "activity", "open_positions", 
                          "recent_scans", "sniper_history", "burn_logs", "bot_configs"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"PASS: Response contains all required fields: {required_fields}")
    
    def test_funding_structure(self):
        """Test funding object structure"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        funding = data["funding"]
        assert "total_on_chain_sol" in funding
        assert "total_available_sol" in funding
        assert "wallets" in funding
        assert "overall_status" in funding
        
        # Verify overall_status is one of expected values
        assert funding["overall_status"] in ["ok", "low", "critical"], \
            f"Invalid overall_status: {funding['overall_status']}"
        
        print(f"PASS: Funding structure valid, overall_status={funding['overall_status']}")
    
    def test_funding_overall_status_values(self):
        """Test that funding.overall_status is one of 'ok', 'low', 'critical'"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        status = data["funding"]["overall_status"]
        valid_statuses = ["ok", "low", "critical"]
        assert status in valid_statuses, f"Invalid status '{status}', expected one of {valid_statuses}"
        print(f"PASS: funding.overall_status='{status}' is valid")
    
    def test_activity_structure(self):
        """Test activity object structure"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        activity = data["activity"]
        assert "today_buys" in activity
        assert "today_exits" in activity
        assert "week_buys" in activity
        assert "week_exits" in activity
        
        # Verify values are integers
        assert isinstance(activity["today_buys"], int)
        assert isinstance(activity["today_exits"], int)
        assert isinstance(activity["week_buys"], int)
        assert isinstance(activity["week_exits"], int)
        
        print(f"PASS: Activity structure valid - today_buys={activity['today_buys']}, week_buys={activity['week_buys']}")
    
    def test_open_positions_is_list(self):
        """Test that open_positions is a list"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        assert isinstance(data["open_positions"], list)
        print(f"PASS: open_positions is a list with {len(data['open_positions'])} items")
    
    def test_recent_scans_is_list(self):
        """Test that recent_scans is a list"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        assert isinstance(data["recent_scans"], list)
        print(f"PASS: recent_scans is a list with {len(data['recent_scans'])} items")
    
    def test_sniper_history_is_list(self):
        """Test that sniper_history is a list"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        assert isinstance(data["sniper_history"], list)
        print(f"PASS: sniper_history is a list with {len(data['sniper_history'])} items")
    
    def test_burn_logs_is_list(self):
        """Test that burn_logs is a list"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        assert isinstance(data["burn_logs"], list)
        print(f"PASS: burn_logs is a list with {len(data['burn_logs'])} items")
    
    def test_bot_configs_is_list(self):
        """Test that bot_configs is a list"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        assert isinstance(data["bot_configs"], list)
        print(f"PASS: bot_configs is a list with {len(data['bot_configs'])} items")
    
    def test_bot_configs_no_test_wallets(self):
        """Test that bot_configs filters out test wallets (no wallet starting with test_ or TEST_)"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        for config in data["bot_configs"]:
            wallet = config.get("wallet", "")
            # The wallet is truncated like "qdegDg...7Rjs", so we check the start
            assert not wallet.lower().startswith("test_"), \
                f"Found test wallet in bot_configs: {wallet}"
        
        print(f"PASS: No test wallets found in bot_configs (checked {len(data['bot_configs'])} configs)")
    
    def test_checked_at_is_iso_timestamp(self):
        """Test that checked_at is a valid ISO timestamp"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        checked_at = data["checked_at"]
        assert "T" in checked_at, "checked_at should be ISO format with T separator"
        assert "+" in checked_at or "Z" in checked_at, "checked_at should have timezone info"
        
        print(f"PASS: checked_at is valid ISO timestamp: {checked_at}")
    
    def test_wallet_health_structure(self):
        """Test individual wallet health structure in funding.wallets"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        wallets = data["funding"]["wallets"]
        if len(wallets) > 0:
            wallet = wallets[0]
            required_fields = ["user_wallet", "custodial", "on_chain_sol", 
                             "available_sol", "open_positions", "funding_status"]
            for field in required_fields:
                assert field in wallet, f"Missing field in wallet health: {field}"
            
            # Verify funding_status is valid
            assert wallet["funding_status"] in ["ok", "low", "critical"]
            
            print(f"PASS: Wallet health structure valid for {wallet['user_wallet']}")
        else:
            print("INFO: No wallets in funding.wallets to verify structure")


class TestAdminCheckEndpoint:
    """Tests for admin check endpoint"""
    
    def test_admin_check_returns_true_for_admin(self):
        """Test admin check returns is_admin=true for admin wallet"""
        response = requests.get(f"{BASE_URL}/api/admin/check/{ADMIN_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] == True
        print("PASS: Admin check returns is_admin=true for admin wallet")
    
    def test_admin_check_returns_false_for_non_admin(self):
        """Test admin check returns is_admin=false for non-admin wallet"""
        response = requests.get(f"{BASE_URL}/api/admin/check/{NON_ADMIN_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] == False
        print("PASS: Admin check returns is_admin=false for non-admin wallet")


class TestBotConfigsFiltering:
    """Tests for bot configs filtering logic"""
    
    def test_bot_configs_have_required_fields(self):
        """Test that each bot config has required fields"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        required_fields = ["wallet", "enabled", "mode", "min_conf", "max_pos", 
                          "max_daily", "cooldown", "stop_loss", "take_profit"]
        
        for config in data["bot_configs"]:
            for field in required_fields:
                assert field in config, f"Missing field '{field}' in bot config"
        
        print(f"PASS: All {len(data['bot_configs'])} bot configs have required fields")
    
    def test_bot_configs_enabled_is_boolean(self):
        """Test that enabled field is boolean"""
        response = requests.get(f"{BASE_URL}/api/admin/bot-health?admin_wallet={ADMIN_WALLET}")
        data = response.json()
        
        for config in data["bot_configs"]:
            assert isinstance(config["enabled"], bool), \
                f"enabled should be boolean, got {type(config['enabled'])}"
        
        print("PASS: All bot configs have boolean 'enabled' field")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
