"""
Test Showcase API Endpoints
Tests for skin collection showcase feature:
- GET /api/showcase/{wallet} - User collection data
- GET /api/showcase/leaderboard/collectors - Top collectors
- GET /api/showcase/recent-acquisitions - Recent skin purchases
- POST /api/showcase/settings - Update showcase settings
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestShowcaseWalletCollection:
    """GET /api/showcase/{wallet} - User collection tests"""

    def test_showcase_new_wallet_returns_default_collection(self, api_client):
        """Test that a new wallet gets default collection with Guardian skin owned"""
        test_wallet = f"TEST_showcase_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "wallet_address" in data
        assert "display_name" in data
        assert "collection" in data
        assert "stats" in data
        assert "equipped_skin" in data
        assert data["wallet_address"] == test_wallet
        assert data["equipped_skin"] == "default"
        
    def test_showcase_collection_contains_all_skins(self, api_client):
        """Test that collection contains all 12 skins"""
        test_wallet = f"TEST_showcase_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have all 12 skins
        assert len(data["collection"]) == 12
        
        # Verify skin IDs are present
        skin_ids = [skin["id"] for skin in data["collection"]]
        expected_skins = ["default", "ethereal", "diamond", "gold", "silver", "heatmap", 
                        "radioactive", "zombie", "water", "fire", "robot", "skeletal"]
        for expected in expected_skins:
            assert expected in skin_ids, f"Missing skin: {expected}"
            
    def test_showcase_default_skin_always_owned(self, api_client):
        """Test that Guardian (default) skin is always marked as owned"""
        test_wallet = f"TEST_showcase_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        default_skin = next((s for s in data["collection"] if s["id"] == "default"), None)
        assert default_skin is not None
        assert default_skin["owned"] == True
        assert default_skin["name"] == "Guardian"
        assert default_skin["rarity"] == "common"
        
    def test_showcase_stats_for_new_wallet(self, api_client):
        """Test stats for a new wallet (only default owned)"""
        test_wallet = f"TEST_showcase_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        
        assert response.status_code == 200
        data = response.json()
        stats = data["stats"]
        
        # New wallet should have 1 skin owned (default)
        assert stats["total_owned"] == 1
        assert stats["total_skins"] == 12
        assert stats["completion_percent"] == pytest.approx(8.3, abs=0.1)
        assert stats["has_ethereal"] == False
        assert stats["missing_for_ethereal"] == 10
        
    def test_showcase_skin_rarity_counts(self, api_client):
        """Test that rarity counts are correct"""
        test_wallet = f"TEST_showcase_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        rarity_counts = data["stats"]["rarity_counts"]
        assert "mythic" in rarity_counts
        assert "legendary" in rarity_counts
        assert "epic" in rarity_counts
        assert "rare" in rarity_counts
        assert "uncommon" in rarity_counts
        assert "common" in rarity_counts


class TestShowcaseWithExistingPurchases:
    """Test showcase for wallet with existing skin purchases"""
    
    def test_showcase_test_wallet_with_gift(self, api_client):
        """Test showcase for the test wallet that received a gift"""
        test_wallet = "TEST_giftflow_recipient_ebb244d0"
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        # This wallet should have robot skin as a gift
        robot_skin = next((s for s in data["collection"] if s["id"] == "robot"), None)
        assert robot_skin is not None
        assert robot_skin["owned"] == True
        assert robot_skin["is_gift"] == True
        
        # Stats should reflect 2 skins owned (default + robot)
        assert data["stats"]["total_owned"] == 2
        assert data["stats"]["total_bonus"] == 1  # robot gives +1%


class TestCollectorLeaderboard:
    """GET /api/showcase/leaderboard/collectors tests"""
    
    def test_leaderboard_returns_list(self, api_client):
        """Test that leaderboard returns a list of collectors"""
        response = api_client.get(f"{BASE_URL}/api/showcase/leaderboard/collectors?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        
    def test_leaderboard_collector_structure(self, api_client):
        """Test the structure of collector entries"""
        response = api_client.get(f"{BASE_URL}/api/showcase/leaderboard/collectors?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["leaderboard"]) > 0:
            collector = data["leaderboard"][0]
            assert "rank" in collector
            assert "wallet_address" in collector
            assert "display_name" in collector
            assert "skin_count" in collector
            assert "has_ethereal" in collector
            assert "rarity_score" in collector
            assert "completion_percent" in collector
            
    def test_leaderboard_ranks_are_sequential(self, api_client):
        """Test that ranks are sequential starting from 1"""
        response = api_client.get(f"{BASE_URL}/api/showcase/leaderboard/collectors?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        for i, collector in enumerate(data["leaderboard"]):
            assert collector["rank"] == i + 1
            
    def test_leaderboard_respects_limit(self, api_client):
        """Test that limit parameter is respected"""
        response = api_client.get(f"{BASE_URL}/api/showcase/leaderboard/collectors?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["leaderboard"]) <= 3


class TestRecentAcquisitions:
    """GET /api/showcase/recent-acquisitions tests"""
    
    def test_recent_acquisitions_returns_list(self, api_client):
        """Test that recent acquisitions returns a list"""
        response = api_client.get(f"{BASE_URL}/api/showcase/recent-acquisitions?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "acquisitions" in data
        assert isinstance(data["acquisitions"], list)
        
    def test_acquisition_structure(self, api_client):
        """Test the structure of acquisition entries"""
        response = api_client.get(f"{BASE_URL}/api/showcase/recent-acquisitions?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["acquisitions"]) > 0:
            acquisition = data["acquisitions"][0]
            assert "wallet_address" in acquisition
            assert "display_name" in acquisition
            assert "skin_id" in acquisition
            assert "skin_name" in acquisition
            assert "rarity" in acquisition
            assert "acquired_at" in acquisition
            assert "acquisition_type" in acquisition
            
    def test_acquisition_types(self, api_client):
        """Test that acquisition types are valid"""
        response = api_client.get(f"{BASE_URL}/api/showcase/recent-acquisitions?limit=20")
        
        assert response.status_code == 200
        data = response.json()
        
        valid_types = ["purchase", "gift", "achievement"]
        for acq in data["acquisitions"]:
            assert acq["acquisition_type"] in valid_types
            
    def test_recent_acquisitions_respects_limit(self, api_client):
        """Test that limit parameter is respected"""
        response = api_client.get(f"{BASE_URL}/api/showcase/recent-acquisitions?limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["acquisitions"]) <= 2


class TestShowcaseSettings:
    """POST /api/showcase/settings tests"""
    
    def test_update_settings_success(self, api_client):
        """Test updating showcase settings"""
        test_wallet = f"TEST_showcase_settings_{uuid.uuid4().hex[:8]}"
        payload = {
            "wallet_address": test_wallet,
            "display_name": "TestCollector123",
            "bio": "This is my test bio",
            "is_public": True
        }
        
        response = api_client.post(f"{BASE_URL}/api/showcase/settings", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Showcase settings updated"
        assert data["settings"]["display_name"] == "TestCollector123"
        assert data["settings"]["bio"] == "This is my test bio"
        
    def test_settings_persist_to_showcase(self, api_client):
        """Test that settings are reflected in showcase endpoint"""
        test_wallet = f"TEST_showcase_persist_{uuid.uuid4().hex[:8]}"
        
        # Update settings
        payload = {
            "wallet_address": test_wallet,
            "display_name": "PersistTest",
            "bio": "Bio for persistence test"
        }
        api_client.post(f"{BASE_URL}/api/showcase/settings", json=payload)
        
        # Verify in showcase
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "PersistTest"
        assert data["bio"] == "Bio for persistence test"
        
    def test_display_name_truncation(self, api_client):
        """Test that display name is truncated to 30 chars"""
        test_wallet = f"TEST_showcase_trunc_{uuid.uuid4().hex[:8]}"
        long_name = "A" * 50  # 50 characters
        
        payload = {
            "wallet_address": test_wallet,
            "display_name": long_name
        }
        
        response = api_client.post(f"{BASE_URL}/api/showcase/settings", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["settings"]["display_name"]) == 30
        
    def test_bio_truncation(self, api_client):
        """Test that bio is truncated to 200 chars"""
        test_wallet = f"TEST_showcase_bio_{uuid.uuid4().hex[:8]}"
        long_bio = "B" * 250  # 250 characters
        
        payload = {
            "wallet_address": test_wallet,
            "bio": long_bio
        }
        
        response = api_client.post(f"{BASE_URL}/api/showcase/settings", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["settings"]["bio"]) == 200


class TestShowcaseSkinDetails:
    """Test skin detail data in collection"""
    
    def test_ethereal_skin_properties(self, api_client):
        """Test Ethereal skin has correct properties"""
        test_wallet = f"TEST_showcase_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        ethereal = next((s for s in data["collection"] if s["id"] == "ethereal"), None)
        assert ethereal is not None
        assert ethereal["name"] == "Ethereal"
        assert ethereal["rarity"] == "mythic"
        assert ethereal["bonus_percent"] == 10
        
    def test_legendary_skins_properties(self, api_client):
        """Test legendary skins have correct bonus"""
        test_wallet = f"TEST_showcase_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/showcase/{test_wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        legendary_skins = [s for s in data["collection"] if s["rarity"] == "legendary"]
        assert len(legendary_skins) == 2  # diamond and gold
        for skin in legendary_skins:
            assert skin["bonus_percent"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
