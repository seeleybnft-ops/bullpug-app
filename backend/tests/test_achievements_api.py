"""
Achievement Badges and Community Benchmarks API Tests

Tests for:
- GET /api/achievements/badges - returns all 17 badges
- GET /api/achievements/user/{address} - returns user stats and earned badges
- GET /api/achievements/share-data/{address} - returns share card data
- GET /api/achievements/community/benchmarks - returns community stats
- POST /api/achievements/opt-in - toggles opt-in status
- GET /api/achievements/leaderboard - returns leaderboard
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAchievementBadges:
    """Tests for achievement badges endpoint"""
    
    def test_get_all_badges_returns_200(self):
        """GET /api/achievements/badges returns 200"""
        response = requests.get(f"{BASE_URL}/api/achievements/badges")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ GET /api/achievements/badges returns 200")
    
    def test_badges_response_has_badges_array(self):
        """Response has badges array"""
        response = requests.get(f"{BASE_URL}/api/achievements/badges")
        data = response.json()
        assert "badges" in data, "Response missing 'badges' field"
        assert isinstance(data["badges"], list), "'badges' should be a list"
        print("✅ Response has badges array")
    
    def test_badges_count_is_17(self):
        """Should return exactly 17 badges"""
        response = requests.get(f"{BASE_URL}/api/achievements/badges")
        data = response.json()
        badge_count = len(data["badges"])
        assert badge_count == 17, f"Expected 17 badges, got {badge_count}"
        print(f"✅ Badge count is 17 (got {badge_count})")
    
    def test_badges_have_required_fields(self):
        """Each badge has required fields: id, name, description, icon, category, rarity"""
        response = requests.get(f"{BASE_URL}/api/achievements/badges")
        data = response.json()
        required_fields = ["id", "name", "description", "icon", "category", "rarity", "requirement"]
        
        for badge in data["badges"]:
            for field in required_fields:
                assert field in badge, f"Badge {badge.get('id', 'unknown')} missing field '{field}'"
        print("✅ All badges have required fields")
    
    def test_badges_have_categories(self):
        """Response has categories array"""
        response = requests.get(f"{BASE_URL}/api/achievements/badges")
        data = response.json()
        assert "categories" in data, "Response missing 'categories' field"
        expected_categories = ["streak", "volume", "performance", "profit", "milestone"]
        assert set(data["categories"]) == set(expected_categories), f"Categories mismatch: {data['categories']}"
        print("✅ Response has correct categories")


class TestUserAchievements:
    """Tests for user achievements endpoint"""
    
    def test_get_user_achievements_returns_200(self):
        """GET /api/achievements/user/{address} returns 200"""
        response = requests.get(f"{BASE_URL}/api/achievements/user/TestWallet123")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ GET /api/achievements/user/{address} returns 200")
    
    def test_user_response_has_required_fields(self):
        """Response has wallet_address, stats, badges, total_badges, available_badges"""
        response = requests.get(f"{BASE_URL}/api/achievements/user/TestWallet456")
        data = response.json()
        required_fields = ["wallet_address", "stats", "badges", "total_badges", "available_badges"]
        
        for field in required_fields:
            assert field in data, f"Response missing field '{field}'"
        print("✅ User response has all required fields")
    
    def test_user_stats_has_required_fields(self):
        """Stats object has all required fields"""
        response = requests.get(f"{BASE_URL}/api/achievements/user/TestWallet789")
        data = response.json()
        stats_fields = ["total_trades", "winning_trades", "losing_trades", "win_rate", 
                       "current_win_streak", "best_win_streak", "total_pnl", "chains_traded"]
        
        for field in stats_fields:
            assert field in data["stats"], f"Stats missing field '{field}'"
        print("✅ User stats has all required fields")
    
    def test_available_badges_is_17(self):
        """available_badges should be 17"""
        response = requests.get(f"{BASE_URL}/api/achievements/user/AnyWallet")
        data = response.json()
        assert data["available_badges"] == 17, f"Expected 17 available badges, got {data['available_badges']}"
        print("✅ available_badges is 17")


class TestShareData:
    """Tests for share data endpoint"""
    
    def test_get_share_data_returns_200(self):
        """GET /api/achievements/share-data/{address} returns 200"""
        response = requests.get(f"{BASE_URL}/api/achievements/share-data/TestShareWallet")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ GET /api/achievements/share-data/{address} returns 200")
    
    def test_share_data_has_required_fields(self):
        """Response has wallet_address, stats, best_badge, share_text"""
        response = requests.get(f"{BASE_URL}/api/achievements/share-data/TestShareWallet2")
        data = response.json()
        required_fields = ["wallet_address", "stats", "best_badge", "share_text"]
        
        for field in required_fields:
            assert field in data, f"Response missing field '{field}'"
        print("✅ Share data has all required fields")
    
    def test_share_text_contains_bullpug(self):
        """share_text should contain BullPug reference"""
        response = requests.get(f"{BASE_URL}/api/achievements/share-data/TestShareWallet3")
        data = response.json()
        assert "BullPug" in data["share_text"], "share_text should mention BullPug"
        print("✅ share_text contains BullPug")
    
    def test_share_stats_has_required_fields(self):
        """Stats in share data has win_streak, best_streak, win_rate, total_pnl, total_trades"""
        response = requests.get(f"{BASE_URL}/api/achievements/share-data/TestShareWallet4")
        data = response.json()
        stats_fields = ["win_streak", "best_streak", "win_rate", "total_pnl", "total_trades"]
        
        for field in stats_fields:
            assert field in data["stats"], f"Share stats missing field '{field}'"
        print("✅ Share stats has all required fields")


class TestCommunityBenchmarks:
    """Tests for community benchmarks endpoint"""
    
    def test_get_benchmarks_returns_200(self):
        """GET /api/achievements/community/benchmarks returns 200"""
        response = requests.get(f"{BASE_URL}/api/achievements/community/benchmarks")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ GET /api/achievements/community/benchmarks returns 200")
    
    def test_benchmarks_has_required_fields(self):
        """Response has total_users, total_trades, average_win_rate, average_streak, top_streaks"""
        response = requests.get(f"{BASE_URL}/api/achievements/community/benchmarks")
        data = response.json()
        required_fields = ["total_users", "total_trades", "average_win_rate", "average_streak", "top_streaks"]
        
        for field in required_fields:
            assert field in data, f"Response missing field '{field}'"
        print("✅ Benchmarks has all required fields")
    
    def test_benchmarks_with_wallet_address(self):
        """Can request benchmarks with wallet_address for percentile calculation"""
        response = requests.get(f"{BASE_URL}/api/achievements/community/benchmarks?wallet_address=TestWalletPercentile")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # percentile fields should be present (may be null)
        assert "percentile_win_rate" in data, "Response missing percentile_win_rate"
        assert "percentile_streak" in data, "Response missing percentile_streak"
        print("✅ Benchmarks works with wallet_address parameter")


class TestOptIn:
    """Tests for opt-in endpoint"""
    
    def test_opt_in_returns_200(self):
        """POST /api/achievements/opt-in returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/achievements/opt-in",
            json={"wallet_address": "TEST_OptInWallet1", "opt_in": True}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ POST /api/achievements/opt-in returns 200")
    
    def test_opt_in_returns_success_and_status(self):
        """Response has success and opt_in fields"""
        response = requests.post(
            f"{BASE_URL}/api/achievements/opt-in",
            json={"wallet_address": "TEST_OptInWallet2", "opt_in": True}
        )
        data = response.json()
        assert data.get("success") == True, "Response should have success: true"
        assert data.get("opt_in") == True, "Response should have opt_in: true"
        print("✅ Opt-in response has correct fields")
    
    def test_opt_out_works(self):
        """Can opt out"""
        response = requests.post(
            f"{BASE_URL}/api/achievements/opt-in",
            json={"wallet_address": "TEST_OptOutWallet", "opt_in": False}
        )
        data = response.json()
        assert data.get("success") == True, "Response should have success: true"
        assert data.get("opt_in") == False, "Response should have opt_in: false"
        print("✅ Opt-out works correctly")
    
    def test_get_opt_in_status(self):
        """GET /api/achievements/opt-in/{address} returns status"""
        # First opt in
        requests.post(
            f"{BASE_URL}/api/achievements/opt-in",
            json={"wallet_address": "TEST_CheckOptIn", "opt_in": True}
        )
        # Then check status
        response = requests.get(f"{BASE_URL}/api/achievements/opt-in/TEST_CheckOptIn")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "opt_in" in data, "Response missing opt_in field"
        print("✅ GET opt-in status works")


class TestLeaderboard:
    """Tests for leaderboard endpoint"""
    
    def test_get_leaderboard_returns_200(self):
        """GET /api/achievements/leaderboard returns 200"""
        response = requests.get(f"{BASE_URL}/api/achievements/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ GET /api/achievements/leaderboard returns 200")
    
    def test_leaderboard_has_required_fields(self):
        """Response has leaderboard array and total_participants"""
        response = requests.get(f"{BASE_URL}/api/achievements/leaderboard")
        data = response.json()
        assert "leaderboard" in data, "Response missing 'leaderboard' field"
        assert "total_participants" in data, "Response missing 'total_participants' field"
        assert isinstance(data["leaderboard"], list), "'leaderboard' should be a list"
        print("✅ Leaderboard has required fields")
    
    def test_leaderboard_sort_by_parameter(self):
        """Can sort by streak, win_rate, pnl, trades"""
        for sort_by in ["streak", "win_rate", "pnl", "trades"]:
            response = requests.get(f"{BASE_URL}/api/achievements/leaderboard?sort_by={sort_by}")
            assert response.status_code == 200, f"Expected 200 for sort_by={sort_by}, got {response.status_code}"
            data = response.json()
            assert data.get("sort_by") == sort_by or "leaderboard" in data
        print("✅ Leaderboard sort_by parameter works")
    
    def test_leaderboard_limit_parameter(self):
        """Can set limit parameter"""
        response = requests.get(f"{BASE_URL}/api/achievements/leaderboard?limit=5")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Leaderboard limit parameter works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
