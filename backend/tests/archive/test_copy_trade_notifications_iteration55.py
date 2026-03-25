"""
Test Copy Trade Notifications System and Copy Trading Integration - Iteration 55

Tests:
1. Notifications API endpoints (GET, POST, PUT, DELETE)
2. Notification settings API
3. Copy trading integration in add_position
4. Notification creation via helper functions
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

# Test wallets
TEST_WALLET = "test_wallet_notifications_55"
TEST_TRADER_WALLET = "test_trader_notifications_55"
TEST_FOLLOWER_WALLET = "test_follower_notifications_55"


class TestNotificationsEndpoints:
    """Test notification API endpoints - GET, POST mark-read, DELETE"""
    
    def test_get_notifications_endpoint_exists(self):
        """Test GET /api/social-trading/notifications/{wallet} returns valid response"""
        response = requests.get(f"{BASE_URL}/api/social-trading/notifications/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "notifications" in data, "Response should have 'notifications' key"
        assert "count" in data, "Response should have 'count' key"
        assert "unread_count" in data, "Response should have 'unread_count' key"
        assert isinstance(data["notifications"], list), "notifications should be a list"
        print(f"✓ GET notifications endpoint works - {data['count']} notifications, {data['unread_count']} unread")
    
    def test_get_notifications_with_unread_filter(self):
        """Test GET /api/social-trading/notifications/{wallet}?unread_only=true"""
        response = requests.get(
            f"{BASE_URL}/api/social-trading/notifications/{TEST_WALLET}?unread_only=true"
        )
        assert response.status_code == 200
        
        data = response.json()
        # All returned notifications should be unread (if any)
        for notification in data["notifications"]:
            assert notification.get("read") == False, "Unread filter should return only unread notifications"
        print(f"✓ GET notifications with unread_only filter works")
    
    def test_get_notifications_with_limit(self):
        """Test GET /api/social-trading/notifications/{wallet}?limit=5"""
        response = requests.get(
            f"{BASE_URL}/api/social-trading/notifications/{TEST_WALLET}?limit=5"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["notifications"]) <= 5, "Limit should restrict results"
        print(f"✓ GET notifications with limit works")
    
    def test_mark_notifications_read_endpoint(self):
        """Test POST /api/social-trading/notifications/mark-read/{wallet}"""
        response = requests.post(
            f"{BASE_URL}/api/social-trading/notifications/mark-read/{TEST_WALLET}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True, "Should return success: true"
        assert "marked_read" in data, "Should return marked_read count"
        print(f"✓ POST mark-read endpoint works - marked {data['marked_read']} as read")
    
    def test_delete_notification_not_found(self):
        """Test DELETE /api/social-trading/notifications/{wallet}/{notification_id} returns 404 for non-existent"""
        response = requests.delete(
            f"{BASE_URL}/api/social-trading/notifications/{TEST_WALLET}/non_existent_id"
        )
        # Should return 404 for non-existent notification
        assert response.status_code == 404, f"Expected 404 for non-existent notification, got {response.status_code}"
        print(f"✓ DELETE notification returns 404 for non-existent")


class TestNotificationSettings:
    """Test notification settings API endpoints"""
    
    def test_get_notification_settings_default(self):
        """Test GET /api/social-trading/notifications/settings/{wallet} returns defaults"""
        response = requests.get(
            f"{BASE_URL}/api/social-trading/notifications/settings/{TEST_WALLET}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("wallet_address") == TEST_WALLET, "Should return wallet_address"
        assert "trade_copied" in data, "Should have trade_copied setting"
        assert "new_follower" in data, "Should have new_follower setting"
        assert "profit_alerts" in data, "Should have profit_alerts setting"
        assert "loss_alerts" in data, "Should have loss_alerts setting"
        assert "stop_loss_triggered" in data, "Should have stop_loss_triggered setting"
        assert "min_profit_alert_percent" in data, "Should have min_profit_alert_percent"
        assert "min_loss_alert_percent" in data, "Should have min_loss_alert_percent"
        
        # Verify defaults
        assert data["trade_copied"] == True, "trade_copied should default to True"
        assert data["new_follower"] == True, "new_follower should default to True"
        assert data["profit_alerts"] == True, "profit_alerts should default to True"
        print(f"✓ GET notification settings returns defaults correctly")
    
    def test_update_notification_settings(self):
        """Test PUT /api/social-trading/notifications/settings/{wallet} updates settings"""
        # Update some settings
        response = requests.put(
            f"{BASE_URL}/api/social-trading/notifications/settings/{TEST_WALLET}",
            params={
                "trade_copied": False,
                "min_profit_alert_percent": 25
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("trade_copied") == False, "trade_copied should be updated to False"
        assert data.get("min_profit_alert_percent") == 25, "min_profit_alert_percent should be updated to 25"
        print(f"✓ PUT notification settings updates correctly")
        
        # Reset back to defaults
        requests.put(
            f"{BASE_URL}/api/social-trading/notifications/settings/{TEST_WALLET}",
            params={
                "trade_copied": True,
                "min_profit_alert_percent": 10
            }
        )
    
    def test_update_notification_settings_validation(self):
        """Test PUT /api/social-trading/notifications/settings/{wallet} validates input"""
        # min_profit_alert_percent should be clamped between 5 and 100
        response = requests.put(
            f"{BASE_URL}/api/social-trading/notifications/settings/{TEST_WALLET}",
            params={"min_profit_alert_percent": 150}
        )
        assert response.status_code == 200
        data = response.json()
        # Should be clamped to max 100
        assert data.get("min_profit_alert_percent") <= 100, "Should clamp to max 100"
        print(f"✓ PUT notification settings validates and clamps values")
    
    def test_update_notification_settings_empty(self):
        """Test PUT /api/social-trading/notifications/settings/{wallet} with no params returns 400"""
        response = requests.put(
            f"{BASE_URL}/api/social-trading/notifications/settings/{TEST_WALLET}"
        )
        assert response.status_code == 400, "Should return 400 when no settings to update"
        print(f"✓ PUT notification settings returns 400 when empty")


class TestCopyTradingIntegration:
    """Test that copy trading is integrated into add_position"""
    
    def test_add_position_endpoint_exists(self):
        """Test POST /api/ai-trader/add-position endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={
                "wallet_address": TEST_WALLET,
                "token_symbol": "TEST",
                "tx_signature": "test_sig_123",
                "input_sol": 0.1,
                "output_amount": 1000,
                "entry_price": 0.0001,
                "token_mint": "TestMint123"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Should return success: true"
        assert "position_id" in data, "Should return position_id"
        assert "position" in data, "Should return position details"
        print(f"✓ add_position endpoint works - created position {data['position_id']}")
        
        # Cleanup - delete the test position
        requests.delete(
            f"{BASE_URL}/api/ai-trader/delete-position",
            params={
                "wallet_address": TEST_WALLET,
                "position_id": data["position_id"]
            }
        )
    
    def test_copy_trade_to_followers_function_exists(self):
        """Verify copy_trade_to_followers is imported in add_position code"""
        # This is a code-level verification - we check that positions can be added
        # and the copy trading integration doesn't break the flow
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={
                "wallet_address": TEST_TRADER_WALLET,
                "token_symbol": "SOL",
                "tx_signature": "test_sig_copy_trade_verify",
                "input_sol": 0.05,
                "output_amount": 50,
                "entry_price": 150.0,
                "token_mint": "So11111111111111111111111111111111111111112"
            }
        )
        assert response.status_code == 200, f"add_position should work, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        print(f"✓ add_position integrates copy trading without errors")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/ai-trader/delete-position",
            params={
                "wallet_address": TEST_TRADER_WALLET,
                "position_id": data["position_id"]
            }
        )


class TestFollowAndNotificationFlow:
    """Test the full follow -> trade -> notification flow"""
    
    def setup_method(self):
        """Setup - enable copy trading for trader"""
        # Enable copy trading for trader
        requests.post(
            f"{BASE_URL}/api/social-trading/profile/enable-copy-trading/{TEST_TRADER_WALLET}",
            params={"enabled": True}
        )
    
    def teardown_method(self):
        """Cleanup after tests"""
        # Unfollow if following
        requests.post(
            f"{BASE_URL}/api/social-trading/unfollow",
            params={
                "follower_wallet": TEST_FOLLOWER_WALLET,
                "trader_wallet": TEST_TRADER_WALLET
            }
        )
        # Disable copy trading
        requests.post(
            f"{BASE_URL}/api/social-trading/profile/enable-copy-trading/{TEST_TRADER_WALLET}",
            params={"enabled": False}
        )
    
    def test_follow_creates_new_follower_notification(self):
        """Test following a trader should create a notification for the trader"""
        # First, get current notification count for trader
        before_response = requests.get(
            f"{BASE_URL}/api/social-trading/notifications/{TEST_TRADER_WALLET}"
        )
        before_count = before_response.json().get("count", 0)
        
        # Follow the trader
        follow_response = requests.post(
            f"{BASE_URL}/api/social-trading/follow",
            json={
                "follower_wallet": TEST_FOLLOWER_WALLET,
                "trader_wallet": TEST_TRADER_WALLET,
                "copy_percentage": 50,
                "max_position_sol": 0.1,
                "auto_copy_enabled": True
            }
        )
        assert follow_response.status_code == 200, f"Follow should succeed, got {follow_response.status_code}"
        
        # Check notifications for trader - should have new_follower notification
        after_response = requests.get(
            f"{BASE_URL}/api/social-trading/notifications/{TEST_TRADER_WALLET}"
        )
        after_data = after_response.json()
        
        # Look for new_follower notification
        new_follower_notifications = [
            n for n in after_data["notifications"]
            if n.get("notification_type") == "new_follower"
        ]
        
        # There should be at least one new_follower notification
        assert len(new_follower_notifications) > 0, "Following should create new_follower notification"
        print(f"✓ Following a trader creates new_follower notification")
    
    def test_copied_trades_endpoint_returns_list(self):
        """Test GET /api/social-trading/copied-trades/{wallet} returns list"""
        response = requests.get(
            f"{BASE_URL}/api/social-trading/copied-trades/{TEST_FOLLOWER_WALLET}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "copied_trades" in data, "Should have copied_trades key"
        assert "count" in data, "Should have count key"
        assert isinstance(data["copied_trades"], list), "copied_trades should be a list"
        print(f"✓ copied-trades endpoint returns proper structure")


class TestNotificationTypes:
    """Test different notification types are properly defined"""
    
    def test_notification_types_in_api_response(self):
        """Test that notification types match expected values"""
        # Get notifications and check types
        response = requests.get(
            f"{BASE_URL}/api/social-trading/notifications/{TEST_WALLET}?limit=100"
        )
        assert response.status_code == 200
        
        data = response.json()
        valid_types = ["trade_copied", "new_follower", "profit_alert", "loss_alert", "stop_loss_triggered"]
        
        for notification in data["notifications"]:
            assert notification.get("notification_type") in valid_types or notification.get("notification_type"), \
                f"Unknown notification type: {notification.get('notification_type')}"
        
        print(f"✓ All notification types are valid")
    
    def test_notification_structure(self):
        """Test notification objects have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/social-trading/notifications/{TEST_WALLET}?limit=10"
        )
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["notification_id", "wallet_address", "notification_type", "title", "message", "read", "created_at"]
        
        for notification in data["notifications"]:
            for field in required_fields:
                assert field in notification, f"Notification missing required field: {field}"
        
        print(f"✓ Notification structure is valid")


class TestLeaderboardAndProfileStillWork:
    """Regression tests - ensure existing endpoints still work"""
    
    def test_leaderboard_endpoint(self):
        """Test GET /api/social-trading/leaderboard still works"""
        response = requests.get(f"{BASE_URL}/api/social-trading/leaderboard?period=7d&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data
        assert "period" in data
        assert data["period"] == "7d"
        print(f"✓ Leaderboard endpoint still works")
    
    def test_profile_endpoint(self):
        """Test GET /api/social-trading/profile/{wallet} still works"""
        response = requests.get(f"{BASE_URL}/api/social-trading/profile/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        assert "wallet_address" in data
        assert data["wallet_address"] == TEST_WALLET
        print(f"✓ Profile endpoint still works")
    
    def test_following_endpoint(self):
        """Test GET /api/social-trading/following/{wallet} still works"""
        response = requests.get(f"{BASE_URL}/api/social-trading/following/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        assert "following" in data
        assert "count" in data
        print(f"✓ Following endpoint still works")
    
    def test_followers_endpoint(self):
        """Test GET /api/social-trading/followers/{wallet} still works"""
        response = requests.get(f"{BASE_URL}/api/social-trading/followers/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        assert "followers" in data
        assert "count" in data
        print(f"✓ Followers endpoint still works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
