"""
Tests for refactored backend routers:
- Reflections Router: /api/reflections/calculate with Blowfish fee structure
- Notifications Router: CRUD operations for notifications
- Pot Game: /api/betting/pot status and join (still in server.py)
- Admin Dashboard: /api/admin/dashboard (still in server.py)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test wallet addresses
TEST_WALLET = f"TEST_{uuid.uuid4().hex[:16]}"
ADMIN_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"  # Known admin wallet


class TestReflectionsRouter:
    """Tests for the reflections calculator router"""
    
    def test_calculate_reflections_basic(self):
        """Test basic reflections calculation with default values"""
        response = requests.post(f"{BASE_URL}/api/reflections/calculate", json={
            "token_holdings": 10000000
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "holdings" in data
        assert "holder_share_percent" in data
        assert "volume_24h" in data
        assert "reflection_rate" in data
        assert "daily" in data
        assert "weekly" in data
        assert "monthly" in data
        assert "yearly" in data
        assert "estimated_apy" in data
        assert "price_usd" in data
        
        # Verify daily has usd and tokens
        assert "usd" in data["daily"]
        assert "tokens" in data["daily"]
        
        # Verify values are calculated correctly
        assert data["holdings"] == 10000000
        assert data["volume_24h"] == 89000  # Default
        assert data["reflection_rate"] == 2.0  # Default
        print(f"Reflections calculated: Daily: ${data['daily']['usd']}, APY: {data['estimated_apy']}%")
    
    def test_calculate_reflections_with_blowfish_rate(self):
        """Test reflections calculation with Blowfish fee rate (0.8%)"""
        response = requests.post(f"{BASE_URL}/api/reflections/calculate", json={
            "token_holdings": 10000000,
            "volume_24h": 100000,
            "reflection_rate": 0.8  # Blowfish: 1% fee * 80% to holders
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["reflection_rate"] == 0.8
        assert data["volume_24h"] == 100000
        # Verify calculations are reasonable
        assert data["daily"]["usd"] >= 0
        assert data["estimated_apy"] >= 0
        print(f"Blowfish rate (0.8%): Daily: ${data['daily']['usd']}, APY: {data['estimated_apy']}%")
    
    def test_calculate_reflections_zero_holdings(self):
        """Test reflections with zero holdings returns zero"""
        response = requests.post(f"{BASE_URL}/api/reflections/calculate", json={
            "token_holdings": 0
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["holdings"] == 0
        assert data["daily"]["usd"] == 0
        assert data["estimated_apy"] == 0
        print("Zero holdings returns zero reflections - PASS")
    
    def test_calculate_reflections_large_holdings(self):
        """Test reflections with large holdings"""
        response = requests.post(f"{BASE_URL}/api/reflections/calculate", json={
            "token_holdings": 500000000,  # 50% of circulating supply
            "volume_24h": 200000
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["holdings"] == 500000000
        # Should have significant share
        assert data["holder_share_percent"] > 50
        print(f"Large holdings ({data['holder_share_percent']}%): Daily: ${data['daily']['usd']}")
    
    def test_calculate_reflections_custom_volume(self):
        """Test reflections with custom volume"""
        response = requests.post(f"{BASE_URL}/api/reflections/calculate", json={
            "token_holdings": 10000000,
            "volume_24h": 500000,  # High volume day
            "reflection_rate": 2.0
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["volume_24h"] == 500000
        print(f"High volume day: Daily: ${data['daily']['usd']}")


class TestNotificationsRouter:
    """Tests for the notifications router"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.test_wallet = f"TEST_notif_{uuid.uuid4().hex[:8]}"
    
    def test_get_notifications_empty(self):
        """Test getting notifications for wallet with no notifications"""
        wallet = f"TEST_empty_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/notifications/{wallet}")
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert "unread_count" in data
        assert isinstance(data["notifications"], list)
        assert data["unread_count"] == 0
        print(f"Empty notifications for new wallet - PASS")
    
    def test_subscribe_push_notifications(self):
        """Test subscribing to push notifications"""
        subscription_data = {
            "wallet_address": self.test_wallet,
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test",
                "keys": {
                    "p256dh": "test_p256dh_key",
                    "auth": "test_auth_key"
                }
            }
        }
        response = requests.post(f"{BASE_URL}/api/notifications/subscribe", json=subscription_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Subscribed" in data["message"]
        print(f"Push subscription created - PASS")
    
    def test_mark_notification_read(self):
        """Test marking a notification as read"""
        # Use a random notification ID - endpoint should handle gracefully
        notif_id = str(uuid.uuid4())
        response = requests.post(f"{BASE_URL}/api/notifications/read/{notif_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        print(f"Mark notification read endpoint works - PASS")
    
    def test_mark_all_notifications_read(self):
        """Test marking all notifications as read for a wallet"""
        wallet = f"TEST_markall_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/notifications/read-all/{wallet}")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "All notifications marked as read" in data["message"]
        print(f"Mark all notifications read - PASS")
    
    def test_get_notifications_with_limit(self):
        """Test getting notifications with limit parameter"""
        wallet = f"TEST_limit_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/notifications/{wallet}?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert len(data["notifications"]) <= 10
        print(f"Notifications with limit parameter - PASS")


class TestPotGame:
    """Tests for the pot game endpoints (still in server.py)"""
    
    def test_get_pot_status(self):
        """Test getting current pot status"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "total_amount_sol" in data
        assert "entry_count" in data
        assert "entries" in data
        assert "status" in data
        assert "countdown_started" in data
        assert "countdown_seconds" in data
        assert "rake_percent" in data
        assert "distribution_wallet" in data
        
        print(f"Pot status: {data['total_amount_sol']} SOL, {data['entry_count']} entries, countdown: {data['countdown_started']}")
    
    def test_pot_has_remaining_seconds_field(self):
        """Test that pot status includes remaining_seconds field"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        data = response.json()
        
        assert "remaining_seconds" in data
        print(f"Remaining seconds field present: {data['remaining_seconds']}")
    
    def test_join_pot_requires_wallet(self):
        """Test that joining pot requires wallet address"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.1,
            "wallet_address": "",  # Empty wallet
            "display_name": "TEST_NoWallet"
        })
        assert response.status_code == 400
        print("Join pot requires wallet - PASS")
    
    def test_join_pot_minimum_bet(self):
        """Test pot minimum bet validation"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.001,  # Below minimum 0.01
            "wallet_address": f"TEST_pot_{uuid.uuid4().hex[:8]}",
            "display_name": "TEST_MinBet"
        })
        assert response.status_code == 400
        assert "Minimum" in response.json().get("detail", "")
        print("Minimum bet validation - PASS")
    
    def test_join_pot_success(self):
        """Test successfully joining the pot"""
        wallet = f"TEST_pot_{uuid.uuid4().hex[:16]}"
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.1,
            "wallet_address": wallet,
            "display_name": "TEST_PotPlayer"
        })
        
        # May fail with 400 if pot is closed, but should not be 500
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "probability" in data
            assert "total_pot_sol" in data
            print(f"Joined pot: {data['probability']}% chance, total pot: {data['total_pot_sol']} SOL")
        else:
            print(f"Could not join pot: {response.json().get('detail', 'unknown')}")


class TestAdminDashboard:
    """Tests for admin dashboard endpoint (still in server.py)"""
    
    def test_admin_check(self):
        """Test admin check endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/check/{ADMIN_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "is_admin" in data
        assert data["is_admin"] == True
        print(f"Admin wallet verified - PASS")
    
    def test_admin_check_non_admin(self):
        """Test admin check for non-admin wallet"""
        non_admin = f"TEST_nonadmin_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/admin/check/{non_admin}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["is_admin"] == False
        print(f"Non-admin wallet correctly identified - PASS")
    
    def test_admin_dashboard_authorized(self):
        """Test admin dashboard with authorized wallet"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard?admin_wallet={ADMIN_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify dashboard structure
        assert "total_bets" in data
        assert "total_challenges" in data
        assert "open_challenges" in data
        assert "completed_challenges" in data
        assert "total_deposits" in data
        assert "total_messages" in data
        assert "total_forum_posts" in data
        assert "estimated_users" in data
        assert "total_rake_collected_sol" in data
        assert "current_pot" in data
        assert "distribution_wallet" in data
        
        print(f"Admin dashboard: {data['total_bets']} bets, {data['total_challenges']} challenges, {data['total_rake_collected_sol']} SOL rake")
    
    def test_admin_dashboard_unauthorized(self):
        """Test admin dashboard with unauthorized wallet"""
        non_admin = f"TEST_unauth_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/admin/dashboard?admin_wallet={non_admin}")
        assert response.status_code == 403
        print("Unauthorized admin access blocked - PASS")


class TestBettingConfig:
    """Tests for betting configuration endpoint"""
    
    def test_get_betting_config(self):
        """Test getting betting configuration"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "rake_percent" in data
        assert "distribution_wallet" in data
        assert "currency" in data
        assert "min_bet_sol" in data
        assert "max_bet_sol" in data
        
        assert data["currency"] == "SOL"
        assert data["rake_percent"] == 2.5
        print(f"Betting config: {data['rake_percent']}% rake, min: {data['min_bet_sol']}, max: {data['max_bet_sol']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
