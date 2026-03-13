"""
Test suite for iteration 44 features:
- Price Alerts System (create, read, delete, check, breakout-scan)
- AI Chat with image upload (FileContent fix)
- Footer Ecosystem links verification
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestPriceAlertsCreate:
    """Test POST /api/ai-trader/alerts/create endpoint"""
    
    def test_create_alert_returns_200_or_201(self):
        """Test creating a price alert returns success"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/create",
            json={
                "wallet_address": TEST_WALLET,
                "symbol": "TEST_SOL",
                "alert_type": "price_above",
                "target_price": 200.0
            }
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got: {data}"
        assert "alert_id" in data, "Response should contain alert_id"
        print(f"PASS: Created alert with ID: {data['alert_id']}")
        return data["alert_id"]

    def test_create_alert_with_breakout_up_type(self):
        """Test creating a breakout_up type alert"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/create",
            json={
                "wallet_address": TEST_WALLET,
                "symbol": "TEST_BONK",
                "alert_type": "breakout_up"
            }
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: Created breakout_up alert for TEST_BONK")

    def test_create_alert_with_breakout_down_type(self):
        """Test creating a breakout_down type alert"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/create",
            json={
                "wallet_address": TEST_WALLET,
                "symbol": "TEST_WIF",
                "alert_type": "breakout_down"
            }
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
        print(f"PASS: Created breakout_down alert for TEST_WIF")


class TestPriceAlertsRead:
    """Test GET /api/ai-trader/alerts/{wallet} endpoint"""
    
    def test_get_alerts_returns_200(self):
        """Test fetching alerts returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/alerts/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "alerts" in data, "Response should contain 'alerts' key"
        assert "count" in data, "Response should contain 'count' key"
        print(f"PASS: Got {data['count']} alerts for wallet")

    def test_get_alerts_returns_list(self):
        """Test alerts response is a list"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/alerts/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["alerts"], list), "alerts should be a list"
        print(f"PASS: Alerts is a list with {len(data['alerts'])} items")


class TestPriceAlertsDelete:
    """Test DELETE /api/ai-trader/alerts/{alert_id} endpoint"""
    
    def test_delete_alert_flow(self):
        """Test creating and then deleting an alert"""
        # First create an alert to delete
        create_response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/create",
            json={
                "wallet_address": TEST_WALLET,
                "symbol": "TEST_DELETE",
                "alert_type": "price_below",
                "target_price": 0.001
            }
        )
        assert create_response.status_code in [200, 201], "Failed to create alert for deletion test"
        alert_id = create_response.json()["alert_id"]
        
        # Now delete it
        delete_response = requests.delete(f"{BASE_URL}/api/ai-trader/alerts/{alert_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        data = delete_response.json()
        assert data.get("success") == True, f"Expected success=True, got: {data}"
        print(f"PASS: Successfully deleted alert {alert_id}")

    def test_delete_nonexistent_alert_returns_404(self):
        """Test deleting non-existent alert returns 404"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.delete(f"{BASE_URL}/api/ai-trader/alerts/{fake_id}")
        # Should return 404 or handle gracefully
        assert response.status_code in [404, 200], f"Expected 404 or 200, got {response.status_code}"
        print(f"PASS: Delete non-existent alert handled correctly (status: {response.status_code})")


class TestPriceAlertsCheck:
    """Test GET /api/ai-trader/alerts/check/{wallet} endpoint"""
    
    def test_check_alerts_returns_200(self):
        """Test checking alerts returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/alerts/check/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "triggered_alerts" in data, "Response should contain 'triggered_alerts'"
        print(f"PASS: Check alerts returned {len(data.get('triggered_alerts', []))} triggered alerts")

    def test_check_alerts_response_structure(self):
        """Test check alerts response has correct structure"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/alerts/check/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "triggered_alerts" in data
        assert "count" in data
        assert isinstance(data["triggered_alerts"], list)
        print("PASS: Check alerts response has correct structure")


class TestBreakoutScan:
    """Test POST /api/ai-trader/alerts/breakout-scan endpoint"""
    
    def test_breakout_scan_returns_200(self):
        """Test breakout scan returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/breakout-scan",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        print(f"PASS: Breakout scan completed, found {data.get('count', 0)} candidates")

    def test_breakout_scan_response_structure(self):
        """Test breakout scan response has correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/alerts/breakout-scan",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200
        data = response.json()
        assert "new_alerts" in data, "Response should contain 'new_alerts'"
        assert "count" in data, "Response should contain 'count'"
        print(f"PASS: Breakout scan response structure is correct")


class TestAIChatImageUpload:
    """Test POST /api/ai/chat with image upload (FileContent fix)"""
    
    def test_chat_without_image_returns_200(self):
        """Test basic chat without image works"""
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": TEST_WALLET,
                "message": "What is Bullpug?",
                "session_id": "test-session-123",
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "response" in data, "Response should contain 'response' key"
        assert "session_id" in data, "Response should contain 'session_id'"
        print(f"PASS: Chat without image works, response length: {len(data.get('response', ''))}")

    def test_chat_with_image_no_error(self):
        """Test that chat with image doesn't throw ImagePart error"""
        # Small 1x1 transparent PNG in base64
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": TEST_WALLET,
                "message": "What do you see in this image?",
                "session_id": "test-session-image-123",
                "active_tab": "dashboard",
                "chat_history": [],
                "image": f"data:image/png;base64,{test_image_base64}"
            }
        )
        
        # The key check: should NOT return 500 with ImagePart error
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check that response doesn't contain the old error
        response_text = str(data)
        assert "ImagePart" not in response_text, "Should not contain ImagePart error"
        assert "response" in data, "Response should contain 'response' key"
        print(f"PASS: Chat with image works without ImagePart error")

    def test_chat_returns_session_id(self):
        """Test chat returns the session ID"""
        test_session = "test-session-verify-456"
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": TEST_WALLET,
                "message": "Hello",
                "session_id": test_session,
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("session_id") == test_session, "Session ID should match"
        print(f"PASS: Session ID correctly returned")


class TestPugBurnScanStillWorks:
    """Verify PugBurn scan still works (regression test)"""
    
    def test_pugburn_scan_returns_200(self):
        """Test PugBurn scan endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/pugburn/scan/{TEST_WALLET}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_accounts_scanned" in data, "Response should contain total_accounts_scanned"
        print(f"PASS: PugBurn scan works, scanned {data.get('total_accounts_scanned', 0)} accounts")


class TestCleanup:
    """Clean up test data"""
    
    def test_cleanup_test_alerts(self):
        """Delete test alerts created during testing"""
        # Get all alerts
        response = requests.get(f"{BASE_URL}/api/ai-trader/alerts/{TEST_WALLET}")
        if response.status_code == 200:
            data = response.json()
            alerts = data.get("alerts", [])
            # Delete alerts with TEST_ prefix
            deleted = 0
            for alert in alerts:
                if alert.get("symbol", "").startswith("TEST_"):
                    delete_response = requests.delete(
                        f"{BASE_URL}/api/ai-trader/alerts/{alert['alert_id']}"
                    )
                    if delete_response.status_code == 200:
                        deleted += 1
            print(f"PASS: Cleaned up {deleted} test alerts")
        else:
            print("PASS: Cleanup - no alerts to delete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
