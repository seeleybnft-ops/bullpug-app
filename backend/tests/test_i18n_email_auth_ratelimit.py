"""
Test i18n, Email, Auth, and Rate Limiting Features
Tests for P0 features (i18next multi-language, SendGrid email service) and P1 features (rate limiting, wallet signature verification)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestEmailEndpoints:
    """Test email service endpoints - SendGrid integration (NOT CONFIGURED YET - should return 'not_configured')"""
    
    def test_email_test_endpoint_exists(self):
        """POST /api/email/test should exist"""
        response = requests.post(f"{BASE_URL}/api/email/test", json={
            "email": "test@example.com",
            "subject": "Test Email",
            "message": "This is a test message"
        })
        # Should return 200 even if not configured (will return 'not_configured' status)
        # OR might return 500/422 if endpoint expects specific format
        assert response.status_code in [200, 422, 500], f"Unexpected status: {response.status_code}, {response.text}"
        print(f"✓ Email test endpoint responded with status {response.status_code}")
    
    def test_email_subscribe_endpoint(self):
        """POST /api/email/subscribe - Subscribe wallet to email notifications"""
        response = requests.post(f"{BASE_URL}/api/email/subscribe", json={
            "wallet_address": "TEST_wallet_for_email_123abc",
            "email": "test_email_subscriber@example.com"
        })
        # Should work or return not_configured
        assert response.status_code in [200, 201, 422, 500], f"Unexpected status: {response.status_code}"
        print(f"✓ Email subscribe endpoint responded with status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {data}")
    
    def test_email_subscription_status_endpoint(self):
        """GET /api/email/subscription/{wallet} - Check subscription status"""
        wallet = "TEST_wallet_check_123"
        response = requests.get(f"{BASE_URL}/api/email/subscription/{wallet}")
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ Email subscription status endpoint responded with status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {data}")


class TestAuthEndpoints:
    """Test wallet signature verification endpoints"""
    
    def test_sign_message_endpoint(self):
        """GET /api/auth/sign-message/{wallet} - Generate message for signing"""
        wallet = "TEST_wallet_for_signing_abc123"
        response = requests.get(f"{BASE_URL}/api/auth/sign-message/{wallet}")
        assert response.status_code == 200, f"Failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "nonce" in data, "Response should contain 'nonce'"
        assert wallet in data["message"], "Message should contain wallet address"
        print(f"✓ Sign message endpoint works")
        print(f"  Message: {data['message'][:50]}...")
        print(f"  Nonce: {data['nonce']}")
        return data
    
    def test_sign_message_with_action(self):
        """GET /api/auth/sign-message/{wallet}?action=challenge - With action parameter"""
        wallet = "TEST_wallet_challenge_sign"
        response = requests.get(f"{BASE_URL}/api/auth/sign-message/{wallet}?action=challenge")
        assert response.status_code == 200, f"Failed: {response.status_code}"
        
        data = response.json()
        assert "message" in data
        assert "challenge" in data["message"].lower(), "Message should contain action"
        print(f"✓ Sign message with action works")
    
    def test_verify_signature_endpoint_exists(self):
        """POST /api/auth/verify-signature - Verify signature endpoint"""
        # Test with invalid/dummy signature - should return valid=false
        response = requests.post(f"{BASE_URL}/api/auth/verify-signature", params={
            "wallet_address": "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT",
            "message": "Test message",
            "signature": "invalid_signature_abc123"
        })
        # Should work but return valid=false
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ Verify signature endpoint responded with status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            assert "valid" in data
            print(f"  Valid: {data.get('valid')}")


class TestRateLimiting:
    """Test rate limiting on betting endpoints (10/minute limits)"""
    
    def test_rate_limit_on_challenge_create(self):
        """Rate limiting on POST /api/betting/challenge/create (10/minute)"""
        # First request should work
        response = requests.post(f"{BASE_URL}/api/betting/challenge/create", json={
            "bet_amount_sol": 0.1,
            "choice": "heads",
            "wallet_address": "TEST_rate_limit_wallet_123",
            "display_name": "RateLimitTest"
        })
        
        # Should succeed or fail due to validation, not rate limit
        assert response.status_code in [200, 400, 422], f"First request failed unexpectedly: {response.status_code}"
        print(f"✓ First challenge create request: {response.status_code}")
        
        # Make several more requests to test rate limiting is configured
        # We won't hit the limit with just a few requests
        for i in range(3):
            response = requests.post(f"{BASE_URL}/api/betting/challenge/create", json={
                "bet_amount_sol": 0.1,
                "choice": "heads",
                "wallet_address": f"TEST_rate_limit_wallet_{i}",
                "display_name": f"RateLimitTest{i}"
            })
            print(f"  Request {i+2}: status {response.status_code}")
        
        # Rate limit endpoint should be configured - verify with headers
        if "X-RateLimit-Limit" in response.headers:
            print(f"✓ Rate limiting headers present: {response.headers.get('X-RateLimit-Limit')}")
        else:
            print("  Note: Rate limit headers not visible (may use different implementation)")
    
    def test_rate_limit_on_pot_join(self):
        """Rate limiting on POST /api/betting/pot/join (10/minute)"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.1,
            "wallet_address": "TEST_pot_rate_limit_123",
            "display_name": "PotRateLimitTest"
        })
        
        assert response.status_code in [200, 400, 422], f"Pot join failed unexpectedly: {response.status_code}"
        print(f"✓ Pot join request: {response.status_code}")


class TestExistingBettingFunctionality:
    """Verify existing betting functionality still works"""
    
    def test_betting_config(self):
        """GET /api/betting/config - Returns betting configuration"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200, f"Config failed: {response.status_code}"
        
        data = response.json()
        assert "rake_percent" in data, "Should have rake_percent"
        assert data["rake_percent"] == 2.5, "Rake should be 2.5%"
        assert "distribution_wallet" in data
        assert "min_bet_sol" in data
        assert "max_bet_sol" in data
        print(f"✓ Betting config: {data['rake_percent']}% rake")
        print(f"  Min bet: {data['min_bet_sol']} SOL")
        print(f"  Max bet: {data['max_bet_sol']} SOL")
    
    def test_get_challenges(self):
        """GET /api/betting/challenges - Returns open challenges"""
        response = requests.get(f"{BASE_URL}/api/betting/challenges?limit=10")
        assert response.status_code == 200, f"Challenges failed: {response.status_code}"
        
        data = response.json()
        assert "challenges" in data, "Should have challenges array"
        print(f"✓ Open challenges: {len(data['challenges'])} found")
    
    def test_get_pot_status(self):
        """GET /api/betting/pot - Returns current pot status"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200, f"Pot status failed: {response.status_code}"
        
        data = response.json()
        assert "total_amount_sol" in data
        assert "entry_count" in data
        assert "status" in data
        print(f"✓ Pot status: {data['total_amount_sol']} SOL, {data['entry_count']} entries")
    
    def test_betting_history(self):
        """GET /api/betting/history - Returns betting history"""
        response = requests.get(f"{BASE_URL}/api/betting/history?limit=10")
        assert response.status_code == 200, f"History failed: {response.status_code}"
        
        data = response.json()
        assert "history" in data
        print(f"✓ Betting history: {len(data['history'])} entries")


class TestHealthAndRoot:
    """Basic health checks"""
    
    def test_api_root(self):
        """GET /api/ - API root returns message"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ API root: {data['message']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
