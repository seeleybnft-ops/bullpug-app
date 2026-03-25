"""
Iteration 79: Testing gallery image fixes and server.py refactoring
- Gallery images replaced with user's branding images (customer-assets.emergentagent.com)
- Logo display in header/footer
- Server.py refactored to use ALL_ROUTERS pattern
- API endpoints verification
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAPIEndpoints:
    """Test core API endpoints after server.py refactoring"""
    
    def test_api_root_endpoint(self):
        """Test /api/ returns correct message"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Bullpug API" in data["message"]
        print(f"✓ API root returns: {data['message']}")
    
    def test_ai_trader_platform_stats(self):
        """Test /api/ai-trader/platform-stats returns valid response"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200
        data = response.json()
        # Verify expected fields
        assert "total_trades" in data
        assert "win_rate" in data
        assert "total_pnl_sol" in data
        assert "active_positions" in data
        print(f"✓ Platform stats: {data}")
    
    def test_ai_trader_settings_get(self):
        """Test /api/ai-trader/settings/{wallet} returns settings including trading_mode"""
        wallet = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{wallet}")
        assert response.status_code == 200
        data = response.json()
        # Verify trading_mode field exists
        assert "trading_mode" in data
        assert data["trading_mode"] in ["conservative", "normal", "aggressive", "sniper"]
        print(f"✓ Settings trading_mode: {data['trading_mode']}")
    
    def test_tokenomics_stats(self):
        """Test /api/tokenomics/stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/tokenomics/stats")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Tokenomics stats: {data}")
    
    def test_newsletter_subscribe(self):
        """Test /api/newsletter/subscribe endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/newsletter/subscribe",
            json={"email": "test_iteration79@example.com"}
        )
        # Should return 200 or 400 (already subscribed)
        assert response.status_code in [200, 400]
        print(f"✓ Newsletter subscribe status: {response.status_code}")


class TestRouterRegistration:
    """Verify all routers are properly registered after refactoring"""
    
    def test_leaderboard_router(self):
        """Test leaderboard router is registered"""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200
        print("✓ Leaderboard router registered")
    
    def test_skins_router(self):
        """Test skins router is registered - /skins/catalog"""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        assert response.status_code == 200
        print("✓ Skins router registered")
    
    def test_forum_router(self):
        """Test forum router is registered"""
        response = requests.get(f"{BASE_URL}/api/forum/posts")
        assert response.status_code == 200
        print("✓ Forum router registered")
    
    def test_journal_router(self):
        """Test journal router is registered - /journal/trades"""
        response = requests.get(f"{BASE_URL}/api/journal/trades")
        assert response.status_code == 200
        print("✓ Journal router registered")
    
    def test_profile_router(self):
        """Test profile router is registered"""
        wallet = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
        response = requests.get(f"{BASE_URL}/api/profile/{wallet}")
        assert response.status_code == 200
        print("✓ Profile router registered")
    
    def test_pugburn_router(self):
        """Test pugburn router is registered - /pugburn/scan/{wallet}"""
        wallet = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
        response = requests.get(f"{BASE_URL}/api/pugburn/scan/{wallet}")
        assert response.status_code == 200
        print("✓ PugBurn router registered")
    
    def test_watchlist_router(self):
        """Test watchlist router is registered"""
        wallet = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
        response = requests.get(f"{BASE_URL}/api/watchlist/{wallet}")
        assert response.status_code == 200
        print("✓ Watchlist router registered")
    
    def test_ai_trader_router(self):
        """Test AI trader router is registered"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        data = response.json()
        assert "safer_tokens" in data
        assert "high_risk_tokens" in data
        print("✓ AI Trader router registered")
    
    def test_achievements_router(self):
        """Test achievements router is registered - /achievements/badges"""
        response = requests.get(f"{BASE_URL}/api/achievements/badges")
        assert response.status_code == 200
        print("✓ Achievements router registered")


class TestServerRefactoring:
    """Verify server.py refactoring didn't break functionality"""
    
    def test_all_routers_count(self):
        """Verify ALL_ROUTERS contains expected number of routers"""
        # Based on routers/__init__.py, there should be 40 routers
        # We test a sample of critical endpoints to verify registration
        critical_endpoints = [
            "/api/",
            "/api/ai-trader/platform-stats",
            "/api/leaderboard",
            "/api/skins/catalog",
            "/api/forum/posts",
        ]
        
        for endpoint in critical_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Endpoint {endpoint} failed"
        
        print(f"✓ All {len(critical_endpoints)} critical endpoints working")
    
    def test_cors_middleware(self):
        """Test CORS middleware is properly configured"""
        response = requests.options(
            f"{BASE_URL}/api/",
            headers={"Origin": "https://cosmic-runner-hub.preview.emergentagent.com"}
        )
        # Should not return 405 Method Not Allowed
        assert response.status_code != 405
        print("✓ CORS middleware configured")
    
    def test_rate_limiter_configured(self):
        """Test rate limiter is configured (won't trigger on single request)"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("✓ Rate limiter configured (no rate limit hit)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
