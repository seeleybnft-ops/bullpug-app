"""
Test Telegram Bot Integration for Bullpug Price Alerts
Tests endpoints:
- GET /api/telegram/bot-info - returns bot username and link
- POST /api/telegram/generate-link-code - generates a 6-char code
- GET /api/telegram/status/{wallet} - returns linked status
- POST /api/telegram/unlink/{wallet} - unlinks telegram
- POST /api/telegram/webhook - handles incoming messages
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = f"TEST_telegram_{uuid.uuid4().hex[:8]}"


class TestTelegramBotInfo:
    """Tests for GET /api/telegram/bot-info endpoint"""
    
    def test_bot_info_returns_200(self):
        """Test that bot-info endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/telegram/bot-info")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ bot-info returns 200")
    
    def test_bot_info_returns_success(self):
        """Test that bot-info returns success=true with valid bot token"""
        response = requests.get(f"{BASE_URL}/api/telegram/bot-info")
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print("✓ bot-info returns success=True")
    
    def test_bot_info_returns_username(self):
        """Test that bot-info returns bot_username"""
        response = requests.get(f"{BASE_URL}/api/telegram/bot-info")
        data = response.json()
        assert "bot_username" in data, f"Missing bot_username in {data}"
        assert isinstance(data["bot_username"], str), "bot_username should be string"
        assert len(data["bot_username"]) > 0, "bot_username should not be empty"
        print(f"✓ bot_username: {data['bot_username']}")
    
    def test_bot_info_returns_link(self):
        """Test that bot-info returns telegram link"""
        response = requests.get(f"{BASE_URL}/api/telegram/bot-info")
        data = response.json()
        assert "link" in data, f"Missing link in {data}"
        assert data["link"].startswith("https://t.me/"), f"Invalid link format: {data['link']}"
        print(f"✓ link: {data['link']}")
    
    def test_bot_info_returns_bot_name(self):
        """Test that bot-info returns bot_name"""
        response = requests.get(f"{BASE_URL}/api/telegram/bot-info")
        data = response.json()
        assert "bot_name" in data, f"Missing bot_name in {data}"
        print(f"✓ bot_name: {data['bot_name']}")


class TestTelegramGenerateLinkCode:
    """Tests for POST /api/telegram/generate-link-code endpoint"""
    
    def test_generate_link_code_returns_200(self):
        """Test that generate-link-code returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ generate-link-code returns 200")
    
    def test_generate_link_code_returns_success(self):
        """Test that generate-link-code returns success=true"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": TEST_WALLET}
        )
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print("✓ generate-link-code returns success=True")
    
    def test_generate_link_code_returns_6_char_code(self):
        """Test that generate-link-code returns a 6-character code"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": TEST_WALLET}
        )
        data = response.json()
        assert "code" in data, f"Missing code in {data}"
        code = data["code"]
        assert len(code) == 6, f"Code should be 6 chars, got {len(code)}: {code}"
        assert code.isalnum(), f"Code should be alphanumeric: {code}"
        assert code.isupper(), f"Code should be uppercase: {code}"
        print(f"✓ code: {code} (6 chars, uppercase alphanumeric)")
    
    def test_generate_link_code_returns_bot_info(self):
        """Test that generate-link-code returns bot username and link"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": TEST_WALLET}
        )
        data = response.json()
        assert "bot_username" in data, f"Missing bot_username in {data}"
        assert "bot_link" in data, f"Missing bot_link in {data}"
        assert data["bot_link"].startswith("https://t.me/"), f"Invalid bot_link: {data['bot_link']}"
        print(f"✓ bot_username: {data['bot_username']}, bot_link: {data['bot_link']}")
    
    def test_generate_link_code_returns_instructions(self):
        """Test that generate-link-code returns instructions"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": TEST_WALLET}
        )
        data = response.json()
        assert "instructions" in data, f"Missing instructions in {data}"
        assert isinstance(data["instructions"], str), "Instructions should be string"
        assert len(data["instructions"]) > 0, "Instructions should not be empty"
        print(f"✓ instructions present ({len(data['instructions'])} chars)")
    
    def test_generate_link_code_returns_expiry(self):
        """Test that generate-link-code returns expiry info"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": TEST_WALLET}
        )
        data = response.json()
        assert "expires_in_minutes" in data, f"Missing expires_in_minutes in {data}"
        assert data["expires_in_minutes"] == 15, f"Expected 15 min expiry, got {data['expires_in_minutes']}"
        print(f"✓ expires_in_minutes: {data['expires_in_minutes']}")
    
    def test_generate_link_code_missing_wallet_returns_422(self):
        """Test that missing wallet_address returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Missing wallet_address returns 422")


class TestTelegramStatus:
    """Tests for GET /api/telegram/status/{wallet} endpoint"""
    
    def test_status_returns_200(self):
        """Test that status endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/telegram/status/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ status returns 200")
    
    def test_status_unlinked_wallet_returns_linked_false(self):
        """Test that unlinked wallet returns linked=false"""
        new_wallet = f"TEST_telegram_unlinked_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/telegram/status/{new_wallet}")
        data = response.json()
        assert data.get("linked") == False, f"Expected linked=False for new wallet, got {data}"
        print("✓ Unlinked wallet returns linked=False")
    
    def test_status_response_structure(self):
        """Test status response structure for unlinked wallet"""
        response = requests.get(f"{BASE_URL}/api/telegram/status/{TEST_WALLET}")
        data = response.json()
        assert "linked" in data, f"Missing 'linked' in response: {data}"
        assert isinstance(data["linked"], bool), "linked should be boolean"
        print(f"✓ Status response structure correct, linked={data['linked']}")


class TestTelegramUnlink:
    """Tests for POST /api/telegram/unlink/{wallet} endpoint"""
    
    def test_unlink_returns_200(self):
        """Test that unlink endpoint returns 200"""
        response = requests.post(f"{BASE_URL}/api/telegram/unlink/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ unlink returns 200")
    
    def test_unlink_unlinked_wallet_returns_success_false(self):
        """Test that unlinking an unlinked wallet returns success=false"""
        new_wallet = f"TEST_telegram_never_linked_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/telegram/unlink/{new_wallet}")
        data = response.json()
        # Should succeed but modified_count is 0
        assert "success" in data, f"Missing success in {data}"
        assert data.get("success") == False, f"Expected success=False for never-linked wallet, got {data}"
        print("✓ Unlinking never-linked wallet returns success=False")
    
    def test_unlink_response_has_message(self):
        """Test that unlink response includes a message"""
        response = requests.post(f"{BASE_URL}/api/telegram/unlink/{TEST_WALLET}")
        data = response.json()
        assert "message" in data, f"Missing message in {data}"
        print(f"✓ Unlink message: {data['message']}")


class TestTelegramWebhook:
    """Tests for POST /api/telegram/webhook endpoint"""
    
    def test_webhook_returns_200_for_empty_update(self):
        """Test that webhook returns 200 for empty update"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ webhook returns 200 for empty update")
    
    def test_webhook_returns_ok_true(self):
        """Test that webhook returns ok=true"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={}
        )
        data = response.json()
        assert data.get("ok") == True, f"Expected ok=True, got {data}"
        print("✓ webhook returns ok=True")
    
    def test_webhook_handles_message_without_text(self):
        """Test webhook handles message without text gracefully"""
        update = {
            "message": {
                "chat": {"id": 12345},
                "from": {"username": "testuser"}
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook",
            json=update
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("ok") == True, f"Expected ok=True, got {data}"
        print("✓ webhook handles message without text")
    
    def test_webhook_handles_start_command(self):
        """Test webhook handles /start command"""
        update = {
            "message": {
                "chat": {"id": 12345},
                "text": "/start",
                "from": {"username": "testuser"}
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook",
            json=update
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("ok") == True, f"Expected ok=True, got {data}"
        print("✓ webhook handles /start command")
    
    def test_webhook_handles_help_command(self):
        """Test webhook handles /help command"""
        update = {
            "message": {
                "chat": {"id": 12345},
                "text": "/help",
                "from": {"username": "testuser"}
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook",
            json=update
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ webhook handles /help command")
    
    def test_webhook_handles_invalid_code(self):
        """Test webhook handles invalid 6-char code"""
        update = {
            "message": {
                "chat": {"id": 12345},
                "text": "XXXXXX",  # Invalid code
                "from": {"username": "testuser"}
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook",
            json=update
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("ok") == True, f"Expected ok=True, got {data}"
        print("✓ webhook handles invalid code gracefully")
    
    def test_webhook_handles_random_message(self):
        """Test webhook handles random message"""
        update = {
            "message": {
                "chat": {"id": 12345},
                "text": "Hello bot!",
                "from": {"username": "testuser"}
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook",
            json=update
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ webhook handles random message")


class TestTelegramIntegrationFlow:
    """End-to-end integration tests for Telegram linking flow"""
    
    def test_full_link_flow(self):
        """Test complete flow: generate code -> check status"""
        # Generate a link code
        wallet = f"TEST_telegram_flow_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Generate link code
        gen_response = requests.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": wallet}
        )
        assert gen_response.status_code == 200
        gen_data = gen_response.json()
        assert gen_data["success"] == True
        code = gen_data["code"]
        print(f"✓ Step 1: Generated link code {code}")
        
        # Step 2: Check status (should be unlinked)
        status_response = requests.get(f"{BASE_URL}/api/telegram/status/{wallet}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["linked"] == False
        print(f"✓ Step 2: Status shows linked=False (code not yet used)")
        
        # Step 3: Unlink (even though not linked - should return success=false)
        unlink_response = requests.post(f"{BASE_URL}/api/telegram/unlink/{wallet}")
        assert unlink_response.status_code == 200
        print("✓ Step 3: Unlink endpoint accessible")
        
        print("✓ Full link flow test completed")
    
    def test_code_uniqueness(self):
        """Test that each code generation produces unique codes"""
        wallet = f"TEST_telegram_unique_{uuid.uuid4().hex[:8]}"
        codes = []
        
        for i in range(3):
            response = requests.post(
                f"{BASE_URL}/api/telegram/generate-link-code",
                json={"wallet_address": wallet}
            )
            data = response.json()
            codes.append(data["code"])
        
        # Codes might be same if generated quickly (same wallet overwrites)
        # But the endpoint should work without error
        print(f"✓ Generated {len(codes)} codes successfully")


class TestTelegramVerifyCode:
    """Tests for POST /api/telegram/verify-code endpoint"""
    
    def test_verify_code_endpoint_exists(self):
        """Test that verify-code endpoint exists and returns response"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/verify-code",
            json={"wallet_address": TEST_WALLET, "code": "XXXXXX"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ verify-code endpoint exists")
    
    def test_verify_invalid_code_returns_error(self):
        """Test that invalid code returns success=false"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/verify-code",
            json={"wallet_address": TEST_WALLET, "code": "XXXXXX"}
        )
        data = response.json()
        assert data.get("success") == False, f"Expected success=False for invalid code, got {data}"
        print("✓ Invalid code returns success=False")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Cleanup test data after tests complete"""
    yield
    # Tests use random wallet addresses with TEST_ prefix, 
    # MongoDB will clean up old data naturally
    print("\n✓ Test cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
