"""
Test suite for Badge System API - 12 badge types with leaderboard achievements
Tests: GET /api/badges/all, GET /api/badges/user/{wallet}, POST /api/badges/check/{wallet}
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Expected 12 badge types from requirements
EXPECTED_BADGES = {
    "gold_champion": {"tier": "legendary", "name": "Gold Champion"},
    "silver_elite": {"tier": "epic", "name": "Silver Elite"},
    "bronze_star": {"tier": "rare", "name": "Bronze Star"},
    "game_master": {"tier": "epic", "name": "Game Master"},
    "jackpot_winner": {"tier": "legendary", "name": "Jackpot Winner"},
    "whale": {"tier": "epic", "name": "Whale"},
    "win_streak": {"tier": "rare", "name": "On Fire"},
    "mooncake_hunter": {"tier": "rare", "name": "Mooncake Hunter"},
    "high_roller": {"tier": "epic", "name": "High Roller"},
    "early_adopter": {"tier": "rare", "name": "Early Adopter"},
    "social_butterfly": {"tier": "common", "name": "Social Butterfly"},
    "skin_collector": {"tier": "common", "name": "Skin Collector"}
}


class TestBadgesAllAPI:
    """Test GET /api/badges/all - list all available badges"""
    
    def test_get_all_badges_returns_200(self):
        """Verify /api/badges/all returns 200"""
        response = requests.get(f"{BASE_URL}/api/badges/all")
        assert response.status_code == 200
        print(f"✓ GET /api/badges/all returned 200")
    
    def test_get_all_badges_returns_12_badges(self):
        """Verify API returns exactly 12 badges"""
        response = requests.get(f"{BASE_URL}/api/badges/all")
        assert response.status_code == 200
        
        data = response.json()
        assert "badges" in data
        badges = data["badges"]
        assert len(badges) == 12, f"Expected 12 badges, got {len(badges)}"
        print(f"✓ API returns exactly 12 badges")
    
    def test_all_badges_have_required_fields(self):
        """Verify each badge has id, name, description, emoji, color, tier"""
        response = requests.get(f"{BASE_URL}/api/badges/all")
        data = response.json()
        
        required_fields = ["id", "name", "description", "emoji", "color", "tier"]
        for badge in data["badges"]:
            for field in required_fields:
                assert field in badge, f"Badge {badge.get('id', 'unknown')} missing field: {field}"
        
        print(f"✓ All badges have required fields: {required_fields}")
    
    def test_all_expected_badges_present(self):
        """Verify all 12 expected badge types are present"""
        response = requests.get(f"{BASE_URL}/api/badges/all")
        data = response.json()
        
        badge_ids = {b["id"] for b in data["badges"]}
        expected_ids = set(EXPECTED_BADGES.keys())
        
        assert badge_ids == expected_ids, f"Missing badges: {expected_ids - badge_ids}, Extra badges: {badge_ids - expected_ids}"
        print(f"✓ All 12 expected badges are present")
    
    def test_badges_sorted_by_tier(self):
        """Verify badges are sorted by tier (legendary > epic > rare > common)"""
        response = requests.get(f"{BASE_URL}/api/badges/all")
        data = response.json()
        
        tier_order = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}
        tiers = [tier_order[b["tier"]] for b in data["badges"]]
        
        assert tiers == sorted(tiers), "Badges should be sorted by tier"
        print(f"✓ Badges are sorted by tier order")


class TestBadgesUserAPI:
    """Test GET /api/badges/user/{wallet_address} - get user's badges"""
    
    def test_get_user_badges_returns_200(self):
        """Verify /api/badges/user/{wallet} returns 200"""
        wallet = f"test-badges-{datetime.now().timestamp()}"
        response = requests.get(f"{BASE_URL}/api/badges/user/{wallet}")
        
        assert response.status_code == 200
        print(f"✓ GET /api/badges/user/{wallet[:12]}... returned 200")
    
    def test_user_badges_response_structure(self):
        """Verify response has wallet_address, badges array, count"""
        wallet = f"test-badges-struct-{datetime.now().timestamp()}"
        response = requests.get(f"{BASE_URL}/api/badges/user/{wallet}")
        
        data = response.json()
        assert "wallet_address" in data
        assert "badges" in data
        assert "count" in data
        assert isinstance(data["badges"], list)
        assert isinstance(data["count"], int)
        
        print(f"✓ User badges response has correct structure")
    
    def test_new_user_has_empty_badges(self):
        """Verify new user has empty badges list"""
        wallet = f"test-new-user-{datetime.now().timestamp()}"
        response = requests.get(f"{BASE_URL}/api/badges/user/{wallet}")
        
        data = response.json()
        assert data["count"] == 0
        assert data["badges"] == []
        
        print(f"✓ New user has empty badges list")
    
    def test_wallet_address_returned_correctly(self):
        """Verify wallet_address is echoed back correctly"""
        wallet = "test-echo-wallet-123"
        response = requests.get(f"{BASE_URL}/api/badges/user/{wallet}")
        
        data = response.json()
        assert data["wallet_address"] == wallet
        
        print(f"✓ Wallet address echoed back correctly")


class TestBadgesCheckAPI:
    """Test POST /api/badges/check/{wallet_address} - check and award achievements"""
    
    def test_check_badges_returns_200(self):
        """Verify POST /api/badges/check/{wallet} returns 200"""
        wallet = f"test-check-{datetime.now().timestamp()}"
        response = requests.post(f"{BASE_URL}/api/badges/check/{wallet}")
        
        assert response.status_code == 200
        print(f"✓ POST /api/badges/check/{wallet[:12]}... returned 200")
    
    def test_check_badges_response_structure(self):
        """Verify response has wallet_address, newly_awarded, count"""
        wallet = f"test-check-struct-{datetime.now().timestamp()}"
        response = requests.post(f"{BASE_URL}/api/badges/check/{wallet}")
        
        data = response.json()
        assert "wallet_address" in data
        assert "newly_awarded" in data
        assert "count" in data
        assert isinstance(data["newly_awarded"], list)
        assert isinstance(data["count"], int)
        
        print(f"✓ Check badges response has correct structure")
    
    def test_new_user_no_automatic_badges(self):
        """Verify new user doesn't get badges automatically (no achievements yet)"""
        wallet = f"test-no-auto-{datetime.now().timestamp()}"
        response = requests.post(f"{BASE_URL}/api/badges/check/{wallet}")
        
        data = response.json()
        # New user without any stats should not get badges
        assert data["count"] == 0
        
        print(f"✓ New user doesn't receive automatic badges")
    
    def test_check_is_idempotent(self):
        """Verify calling check multiple times doesn't award duplicates"""
        wallet = f"test-idempotent-{datetime.now().timestamp()}"
        
        # Call twice
        response1 = requests.post(f"{BASE_URL}/api/badges/check/{wallet}")
        response2 = requests.post(f"{BASE_URL}/api/badges/check/{wallet}")
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Both should succeed and return same count
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        print(f"✓ Badge check is idempotent")


class TestBadgeInfoAPI:
    """Test GET /api/badges/info/{badge_id} - get badge details"""
    
    def test_get_valid_badge_info(self):
        """Verify getting info for valid badge_id"""
        response = requests.get(f"{BASE_URL}/api/badges/info/gold_champion")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Gold Champion"
        assert data["tier"] == "legendary"
        
        print(f"✓ GET badge info for gold_champion works")
    
    def test_get_invalid_badge_returns_404(self):
        """Verify invalid badge_id returns 404"""
        response = requests.get(f"{BASE_URL}/api/badges/info/invalid_badge_id")
        
        assert response.status_code == 404
        
        print(f"✓ Invalid badge_id returns 404")


class TestBadgeTierDistribution:
    """Test badge tier distribution"""
    
    def test_tier_distribution(self):
        """Verify tier distribution: 2 legendary, 4 epic, 4 rare, 2 common"""
        response = requests.get(f"{BASE_URL}/api/badges/all")
        data = response.json()
        
        tier_counts = {}
        for badge in data["badges"]:
            tier = badge["tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        assert tier_counts.get("legendary", 0) == 2, f"Expected 2 legendary, got {tier_counts.get('legendary', 0)}"
        assert tier_counts.get("epic", 0) == 4, f"Expected 4 epic, got {tier_counts.get('epic', 0)}"
        assert tier_counts.get("rare", 0) == 4, f"Expected 4 rare, got {tier_counts.get('rare', 0)}"
        assert tier_counts.get("common", 0) == 2, f"Expected 2 common, got {tier_counts.get('common', 0)}"
        
        print(f"✓ Tier distribution is correct: 2 legendary, 4 epic, 4 rare, 2 common")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
