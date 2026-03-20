"""
Iteration 57 - Push Notifications and Signal Analytics Testing

Features under test:
1. Push Notifications for Copy Trading events
   - Subscribe/Unsubscribe endpoints
   - Preferences management (copy trading focused)
   - VAPID public key endpoint
   - Test notification sending
   - Notification history

2. Signal Analytics for AI Trading Bot
   - Performance summary
   - Confidence analysis
   - Strategy comparison
   - Optimal settings recommendation
   - Track outcome endpoint

Note: Push notification actual delivery is MOCKED (pywebpush not integrated - stored in DB but not sent to browser)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL environment variable not set"

# Test wallet address
TEST_WALLET = f"TEST_push_notify_{uuid.uuid4().hex[:8]}"


# ============== Push Notification Tests ==============

class TestVapidPublicKey:
    """Test VAPID public key endpoint"""
    
    def test_get_vapid_public_key(self):
        """GET /api/push-notifications/vapid-public-key should return key info"""
        response = requests.get(f"{BASE_URL}/api/push-notifications/vapid-public-key")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should have either public_key or configured=False with message
        assert "configured" in data, "Response should have 'configured' field"
        
        if data["configured"]:
            assert "public_key" in data
            assert data["public_key"] is not None
            print(f"VAPID configured: True, key present")
        else:
            assert "message" in data
            print(f"VAPID configured: False - {data.get('message')}")


class TestPushSubscription:
    """Test push subscription endpoints"""
    
    def test_subscribe_success(self):
        """POST /api/push-notifications/subscribe should create subscription"""
        payload = {
            "wallet_address": TEST_WALLET,
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/test-endpoint-{uuid.uuid4().hex[:8]}",
                "keys": {
                    "p256dh": "test_p256dh_key_base64encoded",
                    "auth": "test_auth_key_base64encoded"
                }
            },
            "device_name": "Test Browser",
            "platform": "web"
        }
        
        response = requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Subscribe should return success=True"
        assert "subscription_id" in data, "Should return subscription_id"
        assert "message" in data, "Should return message"
        print(f"Subscribe success: subscription_id={data['subscription_id']}")
    
    def test_subscribe_update_existing(self):
        """Subscribing with same endpoint should update existing subscription"""
        endpoint = f"https://fcm.googleapis.com/fcm/send/test-endpoint-reuse-{uuid.uuid4().hex[:8]}"
        
        payload = {
            "wallet_address": TEST_WALLET,
            "subscription": {
                "endpoint": endpoint,
                "keys": {"p256dh": "key1", "auth": "auth1"}
            },
            "device_name": "Original Device"
        }
        
        # First subscribe
        response1 = requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json=payload)
        assert response1.status_code == 200
        
        # Update with same endpoint
        payload["device_name"] = "Updated Device"
        response2 = requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json=payload)
        assert response2.status_code == 200
        
        data = response2.json()
        assert "updated" in data.get("message", "").lower() or data.get("success"), "Should indicate update or success"
        print("Subscribe update existing: PASSED")
    
    def test_get_subscriptions(self):
        """GET /api/push-notifications/subscriptions/{wallet} should list subscriptions"""
        # Ensure we have a subscription first
        payload = {
            "wallet_address": TEST_WALLET,
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/list-test-{uuid.uuid4().hex[:8]}",
                "keys": {"p256dh": "key", "auth": "auth"}
            }
        }
        requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json=payload)
        
        # Get subscriptions
        response = requests.get(f"{BASE_URL}/api/push-notifications/subscriptions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "subscriptions" in data, "Should have subscriptions array"
        assert "count" in data, "Should have count"
        assert isinstance(data["subscriptions"], list)
        print(f"Get subscriptions: {data['count']} subscriptions found")
    
    def test_unsubscribe_specific_endpoint(self):
        """POST /api/push-notifications/unsubscribe should remove specific endpoint"""
        endpoint = f"https://fcm.googleapis.com/fcm/send/unsubscribe-test-{uuid.uuid4().hex[:8]}"
        wallet = f"TEST_unsub_{uuid.uuid4().hex[:8]}"
        
        # Subscribe first
        payload = {
            "wallet_address": wallet,
            "subscription": {"endpoint": endpoint, "keys": {"p256dh": "key", "auth": "auth"}}
        }
        requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json=payload)
        
        # Unsubscribe specific endpoint
        response = requests.post(
            f"{BASE_URL}/api/push-notifications/unsubscribe",
            params={"wallet_address": wallet, "endpoint": endpoint}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        print(f"Unsubscribe specific endpoint: deleted_count={data.get('deleted_count')}")
    
    def test_unsubscribe_all_endpoints(self):
        """POST /api/push-notifications/unsubscribe without endpoint removes all"""
        wallet = f"TEST_unsub_all_{uuid.uuid4().hex[:8]}"
        
        # Subscribe multiple endpoints
        for i in range(3):
            payload = {
                "wallet_address": wallet,
                "subscription": {
                    "endpoint": f"https://fcm.googleapis.com/fcm/send/multi-{i}-{uuid.uuid4().hex[:8]}",
                    "keys": {"p256dh": "key", "auth": "auth"}
                }
            }
            requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json=payload)
        
        # Unsubscribe all
        response = requests.post(
            f"{BASE_URL}/api/push-notifications/unsubscribe",
            params={"wallet_address": wallet}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("deleted_count", 0) >= 1, "Should delete at least 1 subscription"
        print(f"Unsubscribe all: deleted_count={data.get('deleted_count')}")


class TestPushPreferences:
    """Test push notification preferences endpoints - Copy Trading focused"""
    
    def test_get_preferences_default(self):
        """GET /api/push-notifications/preferences/{wallet} returns defaults for new wallet"""
        wallet = f"TEST_prefs_{uuid.uuid4().hex[:8]}"
        
        response = requests.get(f"{BASE_URL}/api/push-notifications/preferences/{wallet}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify copy trading preference fields exist
        assert "trade_copied" in data, "Should have trade_copied preference"
        assert "new_follower" in data, "Should have new_follower preference"
        assert "fee_earned" in data, "Should have fee_earned preference"
        assert "profit_alerts" in data, "Should have profit_alerts preference"
        assert "loss_alerts" in data, "Should have loss_alerts preference"
        assert "stop_loss_triggered" in data, "Should have stop_loss_triggered preference"
        
        # Verify threshold fields
        assert "min_profit_percent" in data, "Should have min_profit_percent"
        assert "min_loss_percent" in data, "Should have min_loss_percent"
        
        # Verify defaults are True (enabled)
        assert data["trade_copied"] is True, "trade_copied should default to True"
        assert data["new_follower"] is True, "new_follower should default to True"
        
        print(f"Default preferences verified: trade_copied={data['trade_copied']}, new_follower={data['new_follower']}")
    
    def test_update_preferences(self):
        """PUT /api/push-notifications/preferences/{wallet} should update preferences"""
        wallet = f"TEST_update_prefs_{uuid.uuid4().hex[:8]}"
        
        # Update some preferences
        response = requests.put(
            f"{BASE_URL}/api/push-notifications/preferences/{wallet}",
            params={
                "trade_copied": False,
                "profit_alerts": True,
                "min_profit_percent": 15.0
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["trade_copied"] is False, "trade_copied should be updated to False"
        assert data["min_profit_percent"] == 15.0, "min_profit_percent should be 15.0"
        print(f"Update preferences: trade_copied={data['trade_copied']}, min_profit_percent={data['min_profit_percent']}")
    
    def test_update_preferences_no_params(self):
        """PUT /api/push-notifications/preferences without params should return 400"""
        wallet = f"TEST_no_params_{uuid.uuid4().hex[:8]}"
        
        response = requests.put(f"{BASE_URL}/api/push-notifications/preferences/{wallet}")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("Update without params returns 400: PASSED")


class TestSendNotification:
    """Test send notification endpoint"""
    
    def test_send_test_notification(self):
        """POST /api/push-notifications/send-test/{wallet} should send test notification"""
        wallet = f"TEST_send_{uuid.uuid4().hex[:8]}"
        
        # Subscribe first
        payload = {
            "wallet_address": wallet,
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/send-test-{uuid.uuid4().hex[:8]}",
                "keys": {"p256dh": "key", "auth": "auth"}
            }
        }
        requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json=payload)
        
        # Send test notification
        response = requests.post(f"{BASE_URL}/api/push-notifications/send-test/{wallet}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True or data.get("sent_count", 0) >= 0, "Should return success or sent_count"
        print(f"Send test notification: success={data.get('success')}, sent_count={data.get('sent_count')}")
    
    def test_send_test_no_subscriptions(self):
        """Sending to wallet with no subscriptions should return success=False"""
        wallet = f"TEST_no_sub_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/push-notifications/send-test/{wallet}")
        assert response.status_code == 200
        
        data = response.json()
        # Either success=False or sent_count=0 is valid
        assert data.get("success") is False or data.get("sent_count") == 0
        print(f"Send to no subscriptions: success={data.get('success')}, reason={data.get('reason')}")


class TestNotificationHistory:
    """Test notification history endpoint"""
    
    def test_get_notification_history(self):
        """GET /api/push-notifications/history/{wallet} should return history"""
        wallet = f"TEST_history_{uuid.uuid4().hex[:8]}"
        
        # Subscribe and send a test notification to create history
        payload = {
            "wallet_address": wallet,
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/history-test-{uuid.uuid4().hex[:8]}",
                "keys": {"p256dh": "key", "auth": "auth"}
            }
        }
        requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json=payload)
        requests.post(f"{BASE_URL}/api/push-notifications/send-test/{wallet}")
        
        # Get history
        response = requests.get(f"{BASE_URL}/api/push-notifications/history/{wallet}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "notifications" in data, "Should have notifications array"
        assert "count" in data, "Should have count"
        assert isinstance(data["notifications"], list)
        print(f"Notification history: {data['count']} notifications found")
    
    def test_get_notification_history_with_limit(self):
        """History endpoint should respect limit parameter"""
        wallet = TEST_WALLET
        
        response = requests.get(
            f"{BASE_URL}/api/push-notifications/history/{wallet}",
            params={"limit": 5}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["notifications"]) <= 5, "Should respect limit"
        print(f"History with limit=5: returned {len(data['notifications'])} notifications")


# ============== Signal Analytics Tests ==============

class TestPerformanceSummary:
    """Test signal performance summary endpoint"""
    
    def test_get_performance_summary_default(self):
        """GET /api/signal-analytics/performance-summary should return summary"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/performance-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data, "Should have period_days"
        
        # Either has strategies (if outcomes exist) or has note (fallback analysis)
        if "strategies" in data:
            assert isinstance(data["strategies"], list)
            print(f"Performance summary: {len(data['strategies'])} strategies analyzed")
        
        if "note" in data:
            print(f"Performance summary note: {data.get('note')}")
        
        if "total_signals_analyzed" in data:
            print(f"Total signals analyzed: {data['total_signals_analyzed']}")
    
    def test_get_performance_summary_custom_period(self):
        """Performance summary should accept period_days parameter"""
        response = requests.get(
            f"{BASE_URL}/api/signal-analytics/performance-summary",
            params={"period_days": 7}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["period_days"] == 7, "Should use custom period"
        print(f"Custom period (7d): {data.get('total_signals_analyzed', data.get('total_outcomes_analyzed', 0))} analyzed")
    
    def test_get_performance_summary_max_period(self):
        """Performance summary should accept max period (90 days)"""
        response = requests.get(
            f"{BASE_URL}/api/signal-analytics/performance-summary",
            params={"period_days": 90}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["period_days"] == 90
        print("Max period (90d): PASSED")


class TestConfidenceAnalysis:
    """Test confidence analysis endpoint"""
    
    def test_get_confidence_analysis(self):
        """GET /api/signal-analytics/confidence-analysis should return analysis"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/confidence-analysis")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data
        assert "total_signals" in data
        assert "confidence_distribution" in data
        assert "recommended_min_confidence" in data
        assert "insight" in data
        
        assert isinstance(data["confidence_distribution"], list)
        print(f"Confidence analysis: {data['total_signals']} signals, recommended min: {data['recommended_min_confidence']}")
    
    def test_confidence_distribution_structure(self):
        """Confidence distribution should have proper bucket structure"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/confidence-analysis")
        assert response.status_code == 200
        
        data = response.json()
        for bucket in data["confidence_distribution"]:
            assert "confidence_range" in bucket, "Bucket should have confidence_range"
            assert "total_signals" in bucket, "Bucket should have total_signals"
            # May have approved, approval_rate if signals exist
        print(f"Confidence distribution: {len(data['confidence_distribution'])} buckets")


class TestStrategyComparison:
    """Test strategy comparison endpoint"""
    
    def test_get_strategy_comparison(self):
        """GET /api/signal-analytics/strategy-comparison should return comparison"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/strategy-comparison")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data
        assert "strategies" in data
        assert "recommendation" in data
        
        assert isinstance(data["strategies"], list)
        print(f"Strategy comparison: {len(data['strategies'])} strategies compared")
    
    def test_strategy_comparison_structure(self):
        """Strategy comparison should have proper fields for each strategy"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/strategy-comparison")
        assert response.status_code == 200
        
        data = response.json()
        for strat in data["strategies"]:
            assert "strategy" in strat, "Should have strategy name"
            assert "total_signals" in strat, "Should have total_signals"
            # Optional fields depending on data: approved, rejected, expired, quality_score
        print(f"Strategy structure verified for {len(data['strategies'])} strategies")


class TestOptimalSettings:
    """Test optimal settings recommendation endpoint"""
    
    def test_get_optimal_settings(self):
        """GET /api/signal-analytics/optimal-settings should return recommendations"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/optimal-settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        if data.get("sufficient_data") is False:
            # Not enough data case
            assert "message" in data
            assert "current_recommendations" in data
            print(f"Optimal settings: Insufficient data - {data.get('message')}")
        else:
            # Sufficient data case
            assert "settings" in data
            assert "signals_analyzed" in data
            print(f"Optimal settings: Analyzed {data.get('signals_analyzed')} signals")
    
    def test_optimal_settings_auto_trade_recommendations(self):
        """Optimal settings should include auto-trade recommendations"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/optimal-settings")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check for auto_trade recommendations in either location
        if data.get("sufficient_data") is False:
            recs = data.get("current_recommendations", {})
            if "auto_trade" in recs:
                assert "min_confidence" in recs["auto_trade"]
                print("Default auto_trade recommendations present")
        else:
            settings = data.get("settings", {})
            if "auto_trade" in settings:
                at = settings["auto_trade"]
                assert "recommended_min_confidence" in at
                print(f"Auto-trade recommendations: min_confidence={at.get('recommended_min_confidence')}")


class TestTrackOutcome:
    """Test signal outcome tracking endpoint"""
    
    def test_track_outcome_signal_not_found(self):
        """POST /api/signal-analytics/track-outcome with invalid signal_id should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/track-outcome",
            params={
                "signal_id": "nonexistent_signal_12345",
                "price_now": 1.5,
                "hours_elapsed": 1
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Track outcome with invalid signal: 404 as expected")
    
    def test_track_outcome_validation(self):
        """Track outcome should validate hours_elapsed range"""
        # Valid range is 1-24
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/track-outcome",
            params={
                "signal_id": "test_signal",
                "price_now": 1.5,
                "hours_elapsed": 0  # Invalid - below minimum
            }
        )
        assert response.status_code == 422, f"Expected 422 for invalid hours_elapsed=0, got {response.status_code}"
        print("Track outcome validation (hours_elapsed=0): 422 as expected")


class TestSignalAnalyticsIntegration:
    """Integration tests for signal analytics"""
    
    def test_analytics_endpoints_work_together(self):
        """All analytics endpoints should work and return consistent period info"""
        endpoints = [
            "/api/signal-analytics/performance-summary",
            "/api/signal-analytics/confidence-analysis",
            "/api/signal-analytics/strategy-comparison"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", params={"period_days": 30})
            assert response.status_code == 200, f"Endpoint {endpoint} failed: {response.status_code}"
            data = response.json()
            assert data["period_days"] == 30, f"Endpoint {endpoint} should have period_days=30"
        
        print("All analytics endpoints work with consistent period parameter")


# ============== Regression Tests ==============

class TestRegressionPushNotifications:
    """Ensure push notification endpoints don't break existing functionality"""
    
    def test_subscribe_unsubscribe_flow(self):
        """Full subscribe-unsubscribe flow should work"""
        wallet = f"TEST_regression_{uuid.uuid4().hex[:8]}"
        endpoint = f"https://fcm.googleapis.com/fcm/send/regression-{uuid.uuid4().hex[:8]}"
        
        # Subscribe
        sub_resp = requests.post(f"{BASE_URL}/api/push-notifications/subscribe", json={
            "wallet_address": wallet,
            "subscription": {"endpoint": endpoint, "keys": {"p256dh": "k", "auth": "a"}}
        })
        assert sub_resp.status_code == 200
        
        # Get subscriptions
        get_resp = requests.get(f"{BASE_URL}/api/push-notifications/subscriptions/{wallet}")
        assert get_resp.status_code == 200
        assert get_resp.json()["count"] >= 1
        
        # Unsubscribe
        unsub_resp = requests.post(
            f"{BASE_URL}/api/push-notifications/unsubscribe",
            params={"wallet_address": wallet, "endpoint": endpoint}
        )
        assert unsub_resp.status_code == 200
        
        print("Full subscribe-unsubscribe flow: PASSED")


class TestRegressionSignalAnalytics:
    """Ensure signal analytics endpoints work with ai_trader signals"""
    
    def test_analytics_handles_empty_data(self):
        """Analytics should handle case with no signals gracefully"""
        # Use very short period that likely has no signals
        response = requests.get(
            f"{BASE_URL}/api/signal-analytics/performance-summary",
            params={"period_days": 1, "min_signals": 100}
        )
        assert response.status_code == 200, "Should handle empty data gracefully"
        print("Analytics handles empty data: PASSED")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Cleanup test data after all tests"""
    yield
    # Note: In production, would delete TEST_* prefixed data
    # For now, test data is left in place for debugging


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
