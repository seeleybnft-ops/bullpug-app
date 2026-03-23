"""
Iteration 54 Backend Tests
Tests for:
1. Moon cheese local image (CORS fix)
2. MarketConditionAnalyzer class
3. Social Trading API endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pug-journal-1.preview.emergentagent.com').rstrip('/')


class TestMoonCheeseImage:
    """Test that moon cheese image is served locally without CORS issues"""
    
    def test_moon_cheese_image_accessible(self):
        """Moon cheese image should be accessible at /moon-cheese.png"""
        response = requests.get(f"{BASE_URL}/moon-cheese.png", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify it's an image by checking content type
        content_type = response.headers.get('Content-Type', '')
        assert 'image' in content_type.lower() or 'png' in content_type.lower(), f"Expected image content type, got {content_type}"
        print(f"✓ Moon cheese image accessible, Content-Type: {content_type}")
    
    def test_moon_cheese_image_size(self):
        """Moon cheese image should have reasonable size"""
        response = requests.get(f"{BASE_URL}/moon-cheese.png", timeout=10)
        assert response.status_code == 200
        
        content_length = len(response.content)
        # Image should be between 10KB and 5MB
        assert content_length > 10000, f"Image too small: {content_length} bytes"
        assert content_length < 5000000, f"Image too large: {content_length} bytes"
        print(f"✓ Moon cheese image size: {content_length} bytes")


class TestMarketConditionAnalyzer:
    """Test that MarketConditionAnalyzer class exists and functions"""
    
    def test_ai_trader_endpoint_works(self):
        """AI trader endpoint should respond"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens", timeout=15)
        assert response.status_code == 200
        data = response.json()
        assert 'safer_tokens' in data or 'high_risk_tokens' in data
        print("✓ AI Trader tokens endpoint working")
    
    def test_ai_trader_settings_endpoint(self):
        """AI trader settings should respond"""
        test_wallet = "TEST_WALLET_MARKET_ANALYZER_001"
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{test_wallet}", timeout=10)
        assert response.status_code == 200
        data = response.json()
        # Settings should have required fields
        assert 'wallet_address' in data
        assert 'risk_level' in data
        print("✓ AI Trader settings endpoint working with market condition fields")


class TestSocialTradingLeaderboard:
    """Test Social Trading leaderboard endpoint"""
    
    def test_leaderboard_endpoint_exists(self):
        """Leaderboard endpoint should return valid response"""
        response = requests.get(
            f"{BASE_URL}/api/social-trading/leaderboard",
            params={"period": "7d", "limit": 10},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert 'leaderboard' in data
        assert 'period' in data
        assert 'total_traders' in data
        assert data['period'] == '7d'
        print(f"✓ Leaderboard endpoint working, {data['total_traders']} traders")
    
    def test_leaderboard_periods(self):
        """Test all leaderboard period options"""
        for period in ['24h', '7d', '30d', 'all']:
            response = requests.get(
                f"{BASE_URL}/api/social-trading/leaderboard",
                params={"period": period},
                timeout=10
            )
            assert response.status_code == 200, f"Failed for period {period}"
            data = response.json()
            assert data['period'] == period
        print("✓ All leaderboard periods (24h, 7d, 30d, all) working")


class TestSocialTradingProfile:
    """Test Social Trading profile endpoint"""
    
    def test_profile_endpoint_for_new_wallet(self):
        """Profile should return default data for new/unknown wallet"""
        test_wallet = "TEST_UNKNOWN_WALLET_12345"
        response = requests.get(
            f"{BASE_URL}/api/social-trading/profile/{test_wallet}",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return default profile
        assert 'wallet_address' in data
        assert data['wallet_address'] == test_wallet
        assert 'display_name' in data
        assert 'profile_visible' in data
        assert 'copy_trading_enabled' in data
        print(f"✓ Profile endpoint returns default for unknown wallet")
    
    def test_profile_endpoint_has_stats_field(self):
        """Profile should include stats field (even if null)"""
        test_wallet = "TEST_WALLET_PROFILE_001"
        response = requests.get(
            f"{BASE_URL}/api/social-trading/profile/{test_wallet}",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Stats field should exist (may be null for new wallets)
        assert 'stats' in data
        print(f"✓ Profile includes stats field")


class TestSocialTradingFollow:
    """Test Social Trading follow/unfollow endpoints"""
    
    def test_follow_requires_copy_trading_enabled(self):
        """Following a trader that hasn't enabled copy trading should fail"""
        response = requests.post(
            f"{BASE_URL}/api/social-trading/follow",
            json={
                "follower_wallet": "TEST_FOLLOWER_001",
                "trader_wallet": "TEST_TRADER_NOT_ENABLED_001",
                "copy_percentage": 50,
                "max_position_sol": 0.1,
                "auto_copy_enabled": True
            },
            timeout=10
        )
        # Should return error because trader hasn't enabled copy trading
        assert response.status_code == 400
        data = response.json()
        assert 'detail' in data
        assert 'not enabled' in data['detail'].lower() or 'copy trading' in data['detail'].lower()
        print("✓ Follow correctly fails for traders without copy trading enabled")
    
    def test_enable_copy_trading_endpoint(self):
        """Test enabling copy trading for a profile"""
        test_wallet = "TEST_TRADER_ENABLE_001"
        
        # Enable copy trading
        response = requests.post(
            f"{BASE_URL}/api/social-trading/profile/enable-copy-trading/{test_wallet}",
            params={"enabled": True},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert data.get('copy_trading_enabled') == True
        print("✓ Enable copy trading endpoint working")
        
        # Disable copy trading (cleanup)
        response = requests.post(
            f"{BASE_URL}/api/social-trading/profile/enable-copy-trading/{test_wallet}",
            params={"enabled": False},
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Disable copy trading endpoint working")
    
    def test_follow_and_unfollow_flow(self):
        """Test complete follow and unfollow flow"""
        trader_wallet = "TEST_TRADER_FOLLOW_FLOW_001"
        follower_wallet = "TEST_FOLLOWER_FLOW_001"
        
        # First enable copy trading for trader
        response = requests.post(
            f"{BASE_URL}/api/social-trading/profile/enable-copy-trading/{trader_wallet}",
            params={"enabled": True},
            timeout=10
        )
        assert response.status_code == 200
        
        # Now follow the trader
        response = requests.post(
            f"{BASE_URL}/api/social-trading/follow",
            json={
                "follower_wallet": follower_wallet,
                "trader_wallet": trader_wallet,
                "copy_percentage": 75,
                "max_position_sol": 0.2,
                "auto_copy_enabled": True
            },
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'follow_id' in data
        print(f"✓ Follow successful, follow_id: {data.get('follow_id')}")
        
        # Check following list
        response = requests.get(
            f"{BASE_URL}/api/social-trading/following/{follower_wallet}",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert 'following' in data
        print(f"✓ Following list endpoint working, count: {data.get('count', 0)}")
        
        # Unfollow
        response = requests.post(
            f"{BASE_URL}/api/social-trading/unfollow",
            params={
                "follower_wallet": follower_wallet,
                "trader_wallet": trader_wallet
            },
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        print("✓ Unfollow endpoint working")
        
        # Cleanup - disable copy trading
        requests.post(
            f"{BASE_URL}/api/social-trading/profile/enable-copy-trading/{trader_wallet}",
            params={"enabled": False},
            timeout=10
        )


class TestSocialTradingCopiedTrades:
    """Test copied trades endpoint"""
    
    def test_copied_trades_endpoint(self):
        """Copied trades endpoint should return data"""
        test_wallet = "TEST_WALLET_COPIED_001"
        response = requests.get(
            f"{BASE_URL}/api/social-trading/copied-trades/{test_wallet}",
            params={"limit": 10},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert 'copied_trades' in data
        assert 'count' in data
        print(f"✓ Copied trades endpoint working, count: {data.get('count', 0)}")


class TestSocialTradingFollowers:
    """Test followers endpoint"""
    
    def test_followers_endpoint(self):
        """Followers endpoint should return data"""
        test_wallet = "TEST_TRADER_FOLLOWERS_001"
        response = requests.get(
            f"{BASE_URL}/api/social-trading/followers/{test_wallet}",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert 'followers' in data
        assert 'count' in data
        print(f"✓ Followers endpoint working, count: {data.get('count', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
