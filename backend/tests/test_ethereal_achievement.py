"""
Test suite for Ethereal Achievement Skin feature
Tests the new achievement system including:
- GET /api/skins/catalog (includes Ethereal)
- GET /api/skins/achievement-status/{wallet}
- GET /api/skins/owned/{wallet} (auto-unlock check)
- POST /api/skins/gift (reject Ethereal gifting)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSkinsEndpoints:
    """Test Ethereal achievement skin API endpoints"""
    
    def test_skins_catalog_includes_ethereal(self):
        """GET /api/skins/catalog should return Ethereal as achievement skin"""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "skins" in data, "Response should have 'skins' key"
        assert "achievement_skins" in data, "Response should have 'achievement_skins' key"
        
        # Check Ethereal is in achievement_skins
        assert "ethereal" in data["achievement_skins"], "Ethereal should be in achievement_skins"
        
        ethereal = data["achievement_skins"]["ethereal"]
        assert ethereal["name"] == "Ethereal", "Ethereal name should be 'Ethereal'"
        assert ethereal["bonus_percent"] == 10, "Ethereal should have 10% bonus"
        assert ethereal["rarity"] == "mythic", "Ethereal should have mythic rarity"
        assert ethereal["achievement"] == True, "Ethereal should be marked as achievement"
        assert ethereal["price_sol"] == 0, "Ethereal should not have a price (achievement only)"
        
        print("✅ GET /api/skins/catalog - Ethereal achievement skin returned correctly")

    def test_skins_catalog_has_10_purchasable_skins(self):
        """Verify exactly 10 purchasable skins exist for achievement requirement"""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        assert response.status_code == 200
        
        data = response.json()
        all_skins = data["skins"]
        achievement_skins = data["achievement_skins"]
        
        # Count purchasable skins (exclude achievement skins)
        purchasable_skins = {k: v for k, v in all_skins.items() if k not in achievement_skins}
        
        assert len(purchasable_skins) == 10, f"Expected 10 purchasable skins, got {len(purchasable_skins)}"
        
        # Verify expected skin IDs
        expected_skins = ["diamond", "gold", "silver", "heatmap", "radioactive", "zombie", "water", "fire", "robot", "skeletal"]
        for skin_id in expected_skins:
            assert skin_id in purchasable_skins, f"Missing skin: {skin_id}"
        
        print("✅ Catalog has exactly 10 purchasable skins for achievement")

    def test_achievement_status_for_new_wallet(self):
        """GET /api/skins/achievement-status/{wallet} should return 0/10 progress for new user"""
        test_wallet = f"TEST_new_wallet_{uuid.uuid4().hex[:8]}"
        
        response = requests.get(f"{BASE_URL}/api/skins/achievement-status/{test_wallet}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "ethereal" in data, "Response should have 'ethereal' key"
        
        ethereal = data["ethereal"]
        assert ethereal["unlocked"] == False, "New user should not have Ethereal unlocked"
        assert ethereal["progress"] == 0, "New user should have 0 progress"
        assert ethereal["required"] == 10, "Required should be 10 skins"
        assert len(ethereal["missing_skins"]) == 10, "New user should have all 10 skins missing"
        assert ethereal["bonus_percent"] == 10, "Bonus should be 10%"
        assert ethereal["rarity"] == "mythic", "Rarity should be mythic"
        
        print("✅ GET /api/skins/achievement-status - Returns 0/10 for new wallet")

    def test_owned_skins_for_new_wallet(self):
        """GET /api/skins/owned/{wallet} should return empty array for new user"""
        test_wallet = f"TEST_owned_new_{uuid.uuid4().hex[:8]}"
        
        response = requests.get(f"{BASE_URL}/api/skins/owned/{test_wallet}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "skins" in data, "Response should have 'skins' key"
        assert "wallet" in data, "Response should have 'wallet' key"
        assert data["skins"] == [], "New user should have empty skins array"
        
        print("✅ GET /api/skins/owned - Returns empty array for new wallet")

    def test_gift_ethereal_rejected(self):
        """POST /api/skins/gift should reject gifting Ethereal achievement skin"""
        test_sender = f"TEST_sender_{uuid.uuid4().hex[:8]}"
        test_recipient = f"TEST_recipient_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "sender_wallet": test_sender,
            "recipient_wallet": test_recipient,
            "skin_id": "ethereal"
        })
        
        assert response.status_code == 400, f"Expected 400 for gifting Ethereal, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should have 'detail'"
        assert "achievement" in data["detail"].lower() or "gift" in data["detail"].lower(), \
            f"Error message should mention achievement/gift restriction: {data['detail']}"
        
        print("✅ POST /api/skins/gift - Correctly rejects gifting Ethereal (achievement skins)")

    def test_achievement_status_structure(self):
        """Verify achievement-status response has all required fields"""
        test_wallet = f"TEST_structure_{uuid.uuid4().hex[:8]}"
        
        response = requests.get(f"{BASE_URL}/api/skins/achievement-status/{test_wallet}")
        assert response.status_code == 200
        
        data = response.json()
        ethereal = data["ethereal"]
        
        # Check all required fields exist
        required_fields = ["unlocked", "progress", "required", "missing_skins", "bonus_percent", "rarity"]
        for field in required_fields:
            assert field in ethereal, f"Missing field: {field}"
        
        # Check field types
        assert isinstance(ethereal["unlocked"], bool), "unlocked should be boolean"
        assert isinstance(ethereal["progress"], int), "progress should be integer"
        assert isinstance(ethereal["required"], int), "required should be integer"
        assert isinstance(ethereal["missing_skins"], list), "missing_skins should be list"
        assert isinstance(ethereal["bonus_percent"], int), "bonus_percent should be integer"
        assert isinstance(ethereal["rarity"], str), "rarity should be string"
        
        print("✅ Achievement status response has all required fields with correct types")

    def test_catalog_ethereal_in_all_skins(self):
        """Verify Ethereal is also included in the all_skins merged response"""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        assert response.status_code == 200
        
        data = response.json()
        all_skins = data["skins"]
        
        # Ethereal should be in the merged all_skins dict
        assert "ethereal" in all_skins, "Ethereal should be included in merged all_skins"
        
        ethereal = all_skins["ethereal"]
        assert ethereal["achievement"] == True, "Ethereal should be marked as achievement in merged skins"
        
        print("✅ Ethereal is correctly merged into all_skins response")


class TestEtherealUnlockLogic:
    """Test the Ethereal auto-unlock logic"""
    
    def test_missing_skins_list_is_accurate(self):
        """Verify missing_skins contains actual purchasable skin IDs"""
        test_wallet = f"TEST_missing_{uuid.uuid4().hex[:8]}"
        
        response = requests.get(f"{BASE_URL}/api/skins/achievement-status/{test_wallet}")
        assert response.status_code == 200
        
        data = response.json()
        missing_skins = data["ethereal"]["missing_skins"]
        
        # All missing skins should be valid purchasable skin IDs
        expected_purchasable = ["diamond", "gold", "silver", "heatmap", "radioactive", "zombie", "water", "fire", "robot", "skeletal"]
        
        for skin_id in missing_skins:
            assert skin_id in expected_purchasable, f"Invalid skin ID in missing_skins: {skin_id}"
        
        # For new wallet, all should be missing
        assert set(missing_skins) == set(expected_purchasable), "New wallet should have all purchasable skins missing"
        
        print("✅ missing_skins list contains valid purchasable skin IDs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
