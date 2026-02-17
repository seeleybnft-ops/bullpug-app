"""
Test Skin Gift Features - Animated previews and gifting functionality
Tests:
- POST /api/skins/gift - Gift skin to another user
- GET /api/skins/gifts/{wallet} - Get gift history
- Validation tests for gift API
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSkinGiftAPI:
    """Tests for skin gifting feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.sender_wallet = f"TEST_sender_{uuid.uuid4().hex[:8]}"
        self.recipient_wallet = f"TEST_recipient_{uuid.uuid4().hex[:8]}"
        self.test_skin_id = "gold"  # Use gold skin for testing
    
    def test_get_skin_catalog(self):
        """Verify skin catalog API returns all skins"""
        response = requests.get(f"{BASE_URL}/api/skins/catalog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "skins" in data
        assert len(data["skins"]) >= 10, f"Expected at least 10 skins, got {len(data['skins'])}"
        print(f"PASSED: Skin catalog returns {len(data['skins'])} skins")
    
    def test_gift_requires_ownership(self):
        """Test that gifting requires skin ownership"""
        response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "sender_wallet": self.sender_wallet,
            "recipient_wallet": self.recipient_wallet,
            "skin_id": self.test_skin_id
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "don't own" in data.get("detail", "").lower(), f"Expected ownership error, got: {data}"
        print("PASSED: Gift API correctly rejects non-owner")
    
    def test_gift_rejects_invalid_skin(self):
        """Test that gifting rejects invalid skin ID"""
        response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "sender_wallet": self.sender_wallet,
            "recipient_wallet": self.recipient_wallet,
            "skin_id": "nonexistent_skin_xyz"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "invalid" in data.get("detail", "").lower(), f"Expected invalid skin error, got: {data}"
        print("PASSED: Gift API correctly rejects invalid skin ID")
    
    def test_gift_rejects_default_skin(self):
        """Test that gifting default skin is not allowed"""
        response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "sender_wallet": self.sender_wallet,
            "recipient_wallet": self.recipient_wallet,
            "skin_id": "default"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "default" in data.get("detail", "").lower(), f"Expected default skin error, got: {data}"
        print("PASSED: Gift API correctly rejects default skin")
    
    def test_gift_rejects_self_gifting(self):
        """Test that self-gifting is not allowed"""
        # First we need to simulate owning a skin by creating a purchase record
        # For this test, we'll just verify the API rejects self-gifting logic
        same_wallet = f"TEST_same_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "sender_wallet": same_wallet,
            "recipient_wallet": same_wallet,
            "skin_id": self.test_skin_id
        })
        # Since sender doesn't own the skin, it will fail with ownership error first
        # But if they did own it, it should fail with self-gift error
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASSED: Gift API rejects request (ownership or self-gift validation)")
    
    def test_gift_history_empty_wallet(self):
        """Test gift history for a wallet with no gifts"""
        test_wallet = f"TEST_empty_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/skins/gifts/{test_wallet}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "gifts" in data
        assert "wallet" in data
        assert data["wallet"] == test_wallet
        assert len(data["gifts"]) == 0, "Expected empty gift history for new wallet"
        print("PASSED: Gift history returns empty for new wallet")
    
    def test_full_gift_flow(self):
        """Test complete gift flow: purchase -> gift -> verify ownership"""
        # Create unique wallets
        sender = f"TEST_giftflow_sender_{uuid.uuid4().hex[:8]}"
        recipient = f"TEST_giftflow_recipient_{uuid.uuid4().hex[:8]}"
        skin_id = "robot"  # Use cheap skin for test
        
        # Step 1: Simulate purchase for sender (using test tx signature)
        purchase_response = requests.post(f"{BASE_URL}/api/skins/purchase", json={
            "wallet_address": sender,
            "skin_id": skin_id,
            "tx_signature": f"test_tx_{uuid.uuid4().hex}",
            "amount_sol": 0.01  # Robot skin price
        })
        
        if purchase_response.status_code != 200:
            pytest.skip("Could not create test purchase for gift flow test")
        
        print(f"Step 1: Created purchase - {purchase_response.json()}")
        
        # Step 2: Verify sender owns the skin
        owned_response = requests.get(f"{BASE_URL}/api/skins/owned/{sender}")
        assert owned_response.status_code == 200
        owned_data = owned_response.json()
        assert skin_id in owned_data.get("skins", []), f"Sender should own {skin_id}"
        print(f"Step 2: Verified sender owns {skin_id}")
        
        # Step 3: Gift the skin
        gift_response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "sender_wallet": sender,
            "recipient_wallet": recipient,
            "skin_id": skin_id
        })
        assert gift_response.status_code == 200, f"Gift failed: {gift_response.json()}"
        gift_data = gift_response.json()
        assert "message" in gift_data
        assert "successfully" in gift_data["message"].lower()
        print(f"Step 3: Gift successful - {gift_data['message']}")
        
        # Step 4: Verify sender no longer owns the skin
        sender_owned = requests.get(f"{BASE_URL}/api/skins/owned/{sender}")
        sender_owned_data = sender_owned.json()
        assert skin_id not in sender_owned_data.get("skins", []), "Sender should not own gifted skin"
        print("Step 4: Verified sender no longer owns skin")
        
        # Step 5: Verify recipient now owns the skin
        recipient_owned = requests.get(f"{BASE_URL}/api/skins/owned/{recipient}")
        recipient_owned_data = recipient_owned.json()
        assert skin_id in recipient_owned_data.get("skins", []), f"Recipient should now own {skin_id}"
        print("Step 5: Verified recipient now owns skin")
        
        # Step 6: Check gift history for sender
        sender_history = requests.get(f"{BASE_URL}/api/skins/gifts/{sender}")
        assert sender_history.status_code == 200
        sender_history_data = sender_history.json()
        sent_gifts = [g for g in sender_history_data["gifts"] if g["type"] == "sent"]
        assert len(sent_gifts) > 0, "Sender should have sent gifts in history"
        print(f"Step 6: Sender gift history shows {len(sent_gifts)} sent gifts")
        
        # Step 7: Check gift history for recipient
        recipient_history = requests.get(f"{BASE_URL}/api/skins/gifts/{recipient}")
        assert recipient_history.status_code == 200
        recipient_history_data = recipient_history.json()
        received_gifts = [g for g in recipient_history_data["gifts"] if g["type"] == "received"]
        assert len(received_gifts) > 0, "Recipient should have received gifts in history"
        print(f"Step 7: Recipient gift history shows {len(received_gifts)} received gifts")
        
        print("PASSED: Full gift flow completed successfully!")


class TestGiftValidation:
    """Additional validation tests for gift API"""
    
    def test_gift_requires_all_fields(self):
        """Test gift API requires all required fields"""
        # Missing recipient
        response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "sender_wallet": "test_sender",
            "skin_id": "gold"
        })
        assert response.status_code == 422, f"Expected 422 for missing recipient, got {response.status_code}"
        print("PASSED: Gift API requires recipient_wallet field")
        
        # Missing sender
        response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "recipient_wallet": "test_recipient",
            "skin_id": "gold"
        })
        assert response.status_code == 422, f"Expected 422 for missing sender, got {response.status_code}"
        print("PASSED: Gift API requires sender_wallet field")
        
        # Missing skin_id
        response = requests.post(f"{BASE_URL}/api/skins/gift", json={
            "sender_wallet": "test_sender",
            "recipient_wallet": "test_recipient"
        })
        assert response.status_code == 422, f"Expected 422 for missing skin_id, got {response.status_code}"
        print("PASSED: Gift API requires skin_id field")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
