"""
Test suite for verifying modular router endpoints after duplicate route removal from server.py.

Tests:
- Skins router: /api/skins/catalog, /api/skins/achievement-status/{wallet}
- Leaderboard router: /api/leaderboard, /api/leaderboard/submit
- Forum router: /api/forum/categories, /api/forum/posts
- Journal router: /api/journal/dashboard
- Messages router: /api/messages/conversations/{wallet}
- Showcase router: /api/showcase/{wallet}
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
if BASE_URL:
    BASE_URL = BASE_URL.rstrip('/')

TEST_WALLET = "TEST_giftflow_recipient_ebb244d0"


class TestSkinsRouter:
    """Test skins endpoints from modular router."""
    
    def test_skins_catalog_returns_200(self):
        """GET /api/skins/catalog should return 200 with skins data."""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "skins" in data, "Response should contain 'skins' key"
        assert "achievement_skins" in data, "Response should contain 'achievement_skins' key"
        
        # Verify known skins exist
        skins = data["skins"]
        assert "diamond" in skins, "Diamond skin should exist"
        assert "gold" in skins, "Gold skin should exist"
        assert "ethereal" in skins, "Ethereal achievement skin should exist"
        print(f"PASS: Skins catalog returned {len(skins)} skins")
    
    def test_skins_catalog_has_correct_structure(self):
        """Skins should have name, bonus_percent, price_sol, rarity."""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        assert response.status_code == 200
        
        data = response.json()
        diamond = data["skins"].get("diamond", {})
        
        assert "name" in diamond, "Skin should have name"
        assert "bonus_percent" in diamond, "Skin should have bonus_percent"
        assert "price_sol" in diamond, "Skin should have price_sol"
        assert "rarity" in diamond, "Skin should have rarity"
        
        assert diamond["rarity"] == "legendary", "Diamond should be legendary rarity"
        print(f"PASS: Diamond skin structure valid - {diamond['name']}, {diamond['bonus_percent']}% bonus")
    
    def test_achievement_status_returns_200(self):
        """GET /api/skins/achievement-status/{wallet} should return ethereal status."""
        response = requests.get(f"{BASE_URL}/api/skins/achievement-status/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "ethereal" in data, "Response should contain ethereal status"
        
        ethereal = data["ethereal"]
        assert "unlocked" in ethereal, "Should have unlocked status"
        assert "progress" in ethereal, "Should have progress count"
        assert "required" in ethereal, "Should have required count"
        assert "missing_skins" in ethereal, "Should have missing_skins list"
        
        print(f"PASS: Achievement status - Progress: {ethereal['progress']}/{ethereal['required']}")


class TestLeaderboardRouter:
    """Test leaderboard endpoints from modular router."""
    
    def test_leaderboard_returns_200(self):
        """GET /api/leaderboard should return weekly leaderboard."""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "leaderboard" in data, "Response should contain 'leaderboard' key"
        assert "week_start" in data, "Response should contain 'week_start' key"
        assert "next_reset" in data, "Response should contain 'next_reset' key"
        assert "days_until_reset" in data, "Response should contain 'days_until_reset' key"
        
        print(f"PASS: Leaderboard has {len(data['leaderboard'])} entries, resets in {data['days_until_reset']} days")
    
    def test_leaderboard_submit_returns_200(self):
        """POST /api/leaderboard/submit should accept score submission."""
        payload = {
            "player_name": "TEST_ModularRouteTest",
            "score": 500,
            "mooncakes": 3
        }
        response = requests.post(f"{BASE_URL}/api/leaderboard/submit", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rank" in data, "Response should contain rank"
        assert "score" in data, "Response should contain score"
        assert data["score"] == 500, "Score should match submitted value"
        
        print(f"PASS: Score submitted, achieved rank {data['rank']}")
    
    def test_leaderboard_with_limit(self):
        """GET /api/leaderboard with limit parameter."""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["leaderboard"]) <= 5, "Should respect limit parameter"
        print(f"PASS: Leaderboard limit works, returned {len(data['leaderboard'])} entries")


class TestForumRouter:
    """Test forum endpoints from modular router."""
    
    def test_forum_categories_returns_200(self):
        """GET /api/forum/categories should return forum categories."""
        response = requests.get(f"{BASE_URL}/api/forum/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "categories" in data, "Response should contain 'categories' key"
        
        categories = data["categories"]
        assert len(categories) > 0, "Should have at least one category"
        
        # Verify category structure
        first_cat = categories[0]
        assert "id" in first_cat, "Category should have id"
        assert "name" in first_cat, "Category should have name"
        
        cat_ids = [c["id"] for c in categories]
        assert "general" in cat_ids, "General category should exist"
        
        print(f"PASS: Forum has {len(categories)} categories: {cat_ids}")
    
    def test_forum_posts_returns_200(self):
        """GET /api/forum/posts should return forum posts."""
        response = requests.get(f"{BASE_URL}/api/forum/posts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "posts" in data, "Response should contain 'posts' key"
        
        print(f"PASS: Forum posts endpoint returned {len(data['posts'])} posts")
    
    def test_forum_posts_by_category(self):
        """GET /api/forum/posts?category=general should filter by category."""
        response = requests.get(f"{BASE_URL}/api/forum/posts?category=general")
        assert response.status_code == 200
        
        data = response.json()
        assert "posts" in data
        print(f"PASS: Forum posts by category filter works")


class TestJournalRouter:
    """Test journal endpoints from modular router."""
    
    def test_journal_dashboard_returns_200(self):
        """GET /api/journal/dashboard should return trading stats."""
        response = requests.get(f"{BASE_URL}/api/journal/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify all expected fields
        expected_fields = [
            "total_trades", "open_trades", "closed_trades", "total_pnl",
            "win_rate", "avg_pnl", "biggest_win", "biggest_loss",
            "most_traded_asset", "avg_confidence", "pnl_by_asset",
            "win_streak", "loss_streak", "avg_rr", "sharpe_ratio"
        ]
        
        for field in expected_fields:
            assert field in data, f"Dashboard should contain '{field}'"
        
        print(f"PASS: Journal dashboard - {data['total_trades']} trades, {data['win_rate']}% win rate")
    
    def test_journal_trades_returns_200(self):
        """GET /api/journal/trades should return trade list."""
        response = requests.get(f"{BASE_URL}/api/journal/trades?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "trades" in data
        assert "count" in data
        
        print(f"PASS: Journal trades returned {data['count']} trades")


class TestMessagesRouter:
    """Test messages endpoints from modular router."""
    
    def test_conversations_returns_200(self):
        """GET /api/messages/conversations/{wallet} should return conversations."""
        response = requests.get(f"{BASE_URL}/api/messages/conversations/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "conversations" in data, "Response should contain 'conversations' key"
        
        print(f"PASS: Messages endpoint returned {len(data['conversations'])} conversations")
    
    def test_inbox_returns_200(self):
        """GET /api/messages/inbox/{wallet} should return inbox."""
        response = requests.get(f"{BASE_URL}/api/messages/inbox/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        assert "messages" in data
        assert "unread_count" in data
        
        print(f"PASS: Inbox returned {len(data['messages'])} messages, {data['unread_count']} unread")


class TestShowcaseRouter:
    """Test showcase endpoints from modular router."""
    
    def test_showcase_returns_200(self):
        """GET /api/showcase/{wallet} should return showcase data."""
        response = requests.get(f"{BASE_URL}/api/showcase/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify expected fields
        assert "wallet_address" in data, "Should have wallet_address"
        assert "display_name" in data, "Should have display_name"
        assert "collection" in data, "Should have collection"
        assert "stats" in data, "Should have stats"
        
        stats = data["stats"]
        assert "total_owned" in stats, "Stats should have total_owned"
        assert "completion_percent" in stats, "Stats should have completion_percent"
        
        print(f"PASS: Showcase - {stats['total_owned']}/{stats['total_skins']} skins ({stats['completion_percent']}% complete)")
    
    def test_showcase_collection_structure(self):
        """Showcase collection should have proper skin structure."""
        response = requests.get(f"{BASE_URL}/api/showcase/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        collection = data["collection"]
        
        assert len(collection) > 0, "Collection should not be empty"
        
        first_skin = collection[0]
        assert "id" in first_skin, "Skin should have id"
        assert "name" in first_skin, "Skin should have name"
        assert "rarity" in first_skin, "Skin should have rarity"
        assert "owned" in first_skin, "Skin should have owned status"
        
        print(f"PASS: Showcase collection has {len(collection)} skins with proper structure")
    
    def test_showcase_collectors_leaderboard(self):
        """GET /api/showcase/leaderboard/collectors should return collector rankings."""
        response = requests.get(f"{BASE_URL}/api/showcase/leaderboard/collectors?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data
        
        if len(data["leaderboard"]) > 0:
            first = data["leaderboard"][0]
            assert "rank" in first
            assert "wallet_address" in first
            assert "skin_count" in first
        
        print(f"PASS: Collector leaderboard has {len(data['leaderboard'])} entries")
    
    def test_showcase_recent_acquisitions(self):
        """GET /api/showcase/recent-acquisitions should return recent skin purchases."""
        response = requests.get(f"{BASE_URL}/api/showcase/recent-acquisitions?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "acquisitions" in data
        
        print(f"PASS: Recent acquisitions returned {len(data['acquisitions'])} entries")


class TestRootEndpoint:
    """Test root API endpoint."""
    
    def test_api_root_returns_200(self):
        """GET /api/ should return welcome message."""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Bullpug" in data["message"]
        
        print(f"PASS: API root message: {data['message']}")


class TestOtherEndpoints:
    """Test other endpoints that should still work."""
    
    def test_tokenomics_stats(self):
        """GET /api/tokenomics/stats should return token stats."""
        response = requests.get(f"{BASE_URL}/api/tokenomics/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_supply" in data
        assert "price_usd" in data
        
        print(f"PASS: Tokenomics - Supply: {data['total_supply']:,}, Price: ${data['price_usd']}")
    
    def test_betting_config(self):
        """GET /api/betting/config should return betting configuration."""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "rake_percent" in data
        assert "distribution_wallet" in data
        
        print(f"PASS: Betting config - Rake: {data['rake_percent']}%")
    
    def test_betting_pot(self):
        """GET /api/betting/pot should return pot status."""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert "total_amount_sol" in data
        assert "status" in data
        
        print(f"PASS: Pot status - {data['total_amount_sol']} SOL, status: {data['status']}")
    
    def test_governance_proposals(self):
        """GET /api/governance/proposals should return proposals."""
        response = requests.get(f"{BASE_URL}/api/governance/proposals")
        assert response.status_code == 200
        
        data = response.json()
        assert "proposals" in data
        
        print(f"PASS: Governance has {len(data['proposals'])} proposals")
    
    def test_products(self):
        """GET /api/products should return shop products."""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        assert "products" in data
        
        print(f"PASS: Shop has {len(data['products'])} products")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
