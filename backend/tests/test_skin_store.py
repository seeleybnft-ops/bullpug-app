"""
Skin Store API Tests - Iteration 9
Tests for Speed Run game purchasable skins with Solana payments
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pug-auto-trade.preview.emergentagent.com').rstrip('/')

class TestSkinsAPI:
    """Tests for /api/skins/* endpoints"""
    
    def test_get_skins_catalog(self):
        """GET /api/skins/catalog - Returns all 10 skins with correct pricing"""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        assert response.status_code == 200
        
        data = response.json()
        assert "skins" in data
        skins = data["skins"]
        
        # Verify all 10 skins exist
        expected_skins = ["diamond", "gold", "silver", "heatmap", "radioactive", "zombie", "water", "fire", "robot", "skeletal"]
        for skin_id in expected_skins:
            assert skin_id in skins, f"Missing skin: {skin_id}"
        
        # Verify skin count
        assert len(skins) == 10, f"Expected 10 skins, got {len(skins)}"
        
        # Verify legendary skins (Diamond, Gold) - 5% bonus, 0.05 SOL
        assert skins["diamond"]["bonus_percent"] == 5
        assert skins["diamond"]["price_sol"] == 0.05
        assert skins["diamond"]["rarity"] == "legendary"
        
        assert skins["gold"]["bonus_percent"] == 5
        assert skins["gold"]["price_sol"] == 0.05
        assert skins["gold"]["rarity"] == "legendary"
        
        # Verify epic skin (Silver) - 4% bonus, 0.04 SOL
        assert skins["silver"]["bonus_percent"] == 4
        assert skins["silver"]["price_sol"] == 0.04
        assert skins["silver"]["rarity"] == "epic"
        
        # Verify rare skins (Heatmap, Radioactive, Zombie) - 3% bonus, 0.03 SOL
        for skin_id in ["heatmap", "radioactive", "zombie"]:
            assert skins[skin_id]["bonus_percent"] == 3
            assert skins[skin_id]["price_sol"] == 0.03
            assert skins[skin_id]["rarity"] == "rare"
        
        # Verify uncommon skins (Water, Fire) - 2% bonus, 0.02 SOL
        for skin_id in ["water", "fire"]:
            assert skins[skin_id]["bonus_percent"] == 2
            assert skins[skin_id]["price_sol"] == 0.02
            assert skins[skin_id]["rarity"] == "uncommon"
        
        # Verify common skins (Robot, Skeletal) - 1% bonus, 0.01 SOL
        for skin_id in ["robot", "skeletal"]:
            assert skins[skin_id]["bonus_percent"] == 1
            assert skins[skin_id]["price_sol"] == 0.01
            assert skins[skin_id]["rarity"] == "common"
        
        print("✓ All 10 skins verified with correct pricing and bonus percentages")
    
    def test_get_owned_skins_empty(self):
        """GET /api/skins/owned/{wallet} - Returns empty array for new wallet"""
        test_wallet = "TEST_new_wallet_no_skins_12345"
        response = requests.get(f"{BASE_URL}/api/skins/owned/{test_wallet}")
        assert response.status_code == 200
        
        data = response.json()
        assert "skins" in data
        assert data["skins"] == [], "Expected empty skins array for new wallet"
        assert data["wallet"] == test_wallet
        
        print("✓ Owned skins returns empty array for new wallet")
    
    def test_skin_purchase_invalid_skin(self):
        """POST /api/skins/purchase - Rejects invalid skin ID"""
        response = requests.post(f"{BASE_URL}/api/skins/purchase", json={
            "wallet_address": "TEST_wallet_invalid_skin",
            "skin_id": "invalid_skin_id",
            "tx_signature": "test_tx_sig",
            "amount_sol": 0.05
        })
        assert response.status_code == 400
        assert "Invalid skin ID" in response.json().get("detail", "")
        
        print("✓ Invalid skin ID rejected")
    
    def test_skin_purchase_wrong_amount(self):
        """POST /api/skins/purchase - Rejects wrong payment amount"""
        response = requests.post(f"{BASE_URL}/api/skins/purchase", json={
            "wallet_address": "TEST_wallet_wrong_amount",
            "skin_id": "diamond",
            "tx_signature": "test_tx_sig",
            "amount_sol": 0.01  # Diamond costs 0.05 SOL
        })
        assert response.status_code == 400
        assert "Invalid payment amount" in response.json().get("detail", "")
        
        print("✓ Wrong payment amount rejected")
    
    def test_skin_purchase_success(self):
        """POST /api/skins/purchase - Successfully records purchase"""
        import uuid
        test_wallet = f"TEST_skin_purchase_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/skins/purchase", json={
            "wallet_address": test_wallet,
            "skin_id": "robot",  # 0.01 SOL, common skin
            "tx_signature": f"test_tx_{uuid.uuid4().hex[:16]}",
            "amount_sol": 0.01
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "Successfully purchased" in data["message"]
        assert data["skin_id"] == "robot"
        assert data["bonus_percent"] == 1
        
        # Verify skin is now owned
        owned_response = requests.get(f"{BASE_URL}/api/skins/owned/{test_wallet}")
        assert owned_response.status_code == 200
        assert "robot" in owned_response.json()["skins"]
        
        print(f"✓ Skin purchase successful and verified for wallet {test_wallet}")
    
    def test_skin_purchase_duplicate_rejected(self):
        """POST /api/skins/purchase - Rejects duplicate purchase"""
        import uuid
        test_wallet = f"TEST_skin_dup_{uuid.uuid4().hex[:8]}"
        
        # First purchase should succeed
        first_response = requests.post(f"{BASE_URL}/api/skins/purchase", json={
            "wallet_address": test_wallet,
            "skin_id": "skeletal",
            "tx_signature": f"test_tx_{uuid.uuid4().hex[:16]}",
            "amount_sol": 0.01
        })
        assert first_response.status_code == 200
        
        # Second purchase should fail
        second_response = requests.post(f"{BASE_URL}/api/skins/purchase", json={
            "wallet_address": test_wallet,
            "skin_id": "skeletal",
            "tx_signature": f"test_tx_{uuid.uuid4().hex[:16]}",
            "amount_sol": 0.01
        })
        assert second_response.status_code == 400
        assert "already owned" in second_response.json().get("detail", "").lower()
        
        print("✓ Duplicate skin purchase rejected")
    
    def test_get_skins_stats(self):
        """GET /api/skins/stats - Returns skin purchase statistics"""
        response = requests.get(f"{BASE_URL}/api/skins/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "by_skin" in data
        assert "total_sales" in data
        assert "total_revenue_sol" in data
        assert isinstance(data["by_skin"], list)
        assert isinstance(data["total_sales"], int)
        assert isinstance(data["total_revenue_sol"], (int, float))
        
        print(f"✓ Skin stats returned: {data['total_sales']} sales, {data['total_revenue_sol']} SOL revenue")


class TestSkinPricing:
    """Verify skin pricing matches spec"""
    
    def test_pricing_spec_compliance(self):
        """Verify all skins match the original spec"""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        skins = response.json()["skins"]
        
        spec = {
            "diamond": {"bonus": 5, "price": 0.05},
            "gold": {"bonus": 5, "price": 0.05},
            "silver": {"bonus": 4, "price": 0.04},
            "heatmap": {"bonus": 3, "price": 0.03},
            "radioactive": {"bonus": 3, "price": 0.03},
            "zombie": {"bonus": 3, "price": 0.03},
            "water": {"bonus": 2, "price": 0.02},
            "fire": {"bonus": 2, "price": 0.02},
            "robot": {"bonus": 1, "price": 0.01},
            "skeletal": {"bonus": 1, "price": 0.01},
        }
        
        for skin_id, expected in spec.items():
            assert skins[skin_id]["bonus_percent"] == expected["bonus"], f"{skin_id} bonus mismatch"
            assert skins[skin_id]["price_sol"] == expected["price"], f"{skin_id} price mismatch"
        
        print("✓ All skin pricing matches original spec")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
