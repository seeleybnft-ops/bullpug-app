"""
Iteration 80: Community Spotlight Feature Tests
Tests for the new Community Spotlight section on homepage.
Verifies leaderboard and platform-stats APIs that power the carousel.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCommunitySpotlightAPIs:
    """Tests for APIs used by Community Spotlight component"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "Bullpug API" in data.get("message", "")
        print("SUCCESS: API root returns correct message")
    
    def test_leaderboard_endpoint(self):
        """Test /api/leaderboard returns leaderboard data for Cosmic Runner"""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "leaderboard" in data, "Response should contain 'leaderboard' key"
        assert isinstance(data["leaderboard"], list), "Leaderboard should be a list"
        
        # Verify cycle info
        assert "cycle_start" in data, "Response should contain 'cycle_start'"
        assert "next_payout" in data, "Response should contain 'next_payout'"
        
        # If there are entries, verify structure
        if len(data["leaderboard"]) > 0:
            entry = data["leaderboard"][0]
            assert "player_name" in entry, "Entry should have player_name"
            assert "score" in entry, "Entry should have score"
            print(f"SUCCESS: Leaderboard has {len(data['leaderboard'])} entries")
            print(f"  Top player: {entry['player_name']} with {entry['score']} pts")
        else:
            print("INFO: Leaderboard is empty (no players yet)")
    
    def test_platform_stats_endpoint(self):
        """Test /api/ai-trader/platform-stats returns platform statistics"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "active_positions" in data, "Response should contain 'active_positions'"
        assert "total_trades" in data, "Response should contain 'total_trades'"
        assert "active_traders" in data, "Response should contain 'active_traders'"
        
        # Verify data types
        assert isinstance(data["active_positions"], int), "active_positions should be int"
        assert isinstance(data["total_trades"], int), "total_trades should be int"
        
        print(f"SUCCESS: Platform stats returned")
        print(f"  Active positions: {data['active_positions']}")
        print(f"  Total trades: {data['total_trades']}")
        print(f"  Active traders: {data['active_traders']}")
    
    def test_social_trading_leaderboard(self):
        """Test /api/social-trading/leaderboard endpoint (optional for traders slide)"""
        response = requests.get(f"{BASE_URL}/api/social-trading/leaderboard?limit=5")
        # This endpoint may return 200 with empty data or 404 if not implemented
        if response.status_code == 200:
            data = response.json()
            assert "leaderboard" in data, "Response should contain 'leaderboard'"
            print(f"SUCCESS: Social trading leaderboard has {len(data.get('leaderboard', []))} entries")
        else:
            print(f"INFO: Social trading leaderboard returned {response.status_code} (may not be implemented)")


class TestPreviousFixes:
    """Regression tests for previous iteration fixes"""
    
    def test_tokenomics_stats(self):
        """Test /api/tokenomics/stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/tokenomics/stats")
        assert response.status_code == 200
        data = response.json()
        print(f"SUCCESS: Tokenomics stats returned: {data}")
    
    def test_newsletter_subscribe(self):
        """Test newsletter subscription endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/newsletter/subscribe",
            json={"email": "test_iteration80@example.com"}
        )
        # Should return 200 or 409 if already subscribed
        assert response.status_code in [200, 409], f"Unexpected status: {response.status_code}"
        print(f"SUCCESS: Newsletter subscribe returned {response.status_code}")
    
    def test_ai_trader_settings(self):
        """Test AI trader settings endpoint"""
        test_wallet = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{test_wallet}")
        assert response.status_code == 200
        data = response.json()
        assert "trading_mode" in data, "Settings should contain trading_mode"
        print(f"SUCCESS: AI trader settings returned with trading_mode: {data.get('trading_mode')}")


class TestPageEndpoints:
    """Test that major page routes don't return server errors"""
    
    def test_home_page_api_calls(self):
        """Verify APIs called by homepage work"""
        # These are the APIs called by HomePage.js
        endpoints = [
            "/api/tokenomics/stats",
            "/api/leaderboard",
            "/api/ai-trader/platform-stats",
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"{endpoint} returned {response.status_code}"
            print(f"SUCCESS: {endpoint} returns 200")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
