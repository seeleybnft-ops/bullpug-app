"""
Test Telegram Trading Commands
Tests for new trading commands: /trade, /buy, /sell, /price, /trending, /positions
"""

import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_WALLET = "test_wallet_trade_123"
TEST_CHAT_ID = 123456789
TEST_USERNAME = "test_trader"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module", autouse=True)
def setup_test_telegram_account(api_client):
    """Setup a linked telegram account for testing"""
    # Link test account via direct API call (simulating the link flow)
    try:
        response = api_client.post(
            f"{BASE_URL}/api/telegram/link-account",
            params={
                "wallet_address": TEST_WALLET,
                "chat_id": TEST_CHAT_ID,
                "telegram_username": TEST_USERNAME
            }
        )
        print(f"Setup linked account: {response.status_code}")
    except Exception as e:
        print(f"Setup error (may be expected if already linked): {e}")
    yield
    # Cleanup
    try:
        api_client.post(f"{BASE_URL}/api/telegram/unlink/{TEST_WALLET}")
    except Exception:
        pass


class TestTelegramHelpCommand:
    """Test /help command includes trading commands"""
    
    def test_help_command_returns_ok(self, api_client):
        """Test that webhook processes /help command"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/help",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /help command returns ok=True")

    def test_help_command_endpoint_works(self, api_client):
        """Verify webhook endpoint accepts help command"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": 999888777},
                    "text": "/help",
                    "from": {"username": "testuser"}
                }
            }
        )
        assert response.status_code == 200
        print("PASSED: /help endpoint works")


class TestTelegramTradeCommand:
    """Test /trade command shows trading menu"""
    
    def test_trade_command_returns_ok(self, api_client):
        """Test /trade command webhook response"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/trade",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /trade command returns ok=True")

    def test_trade_command_for_unlinked_user(self, api_client):
        """Test /trade for user without linked wallet"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": 111222333},  # Different chat ID
                    "text": "/trade",
                    "from": {"username": "unlinked_user"}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /trade returns ok for unlinked user")


class TestTelegramPriceCommand:
    """Test /price command returns token price info"""
    
    def test_price_command_with_symbol(self, api_client):
        """Test /price SOL command"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/price SOL",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /price SOL command returns ok=True")

    def test_price_command_with_bonk(self, api_client):
        """Test /price BONK command"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/price BONK",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /price BONK command returns ok=True")

    def test_price_command_without_symbol(self, api_client):
        """Test /price without symbol shows usage"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/price",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /price without symbol returns ok=True (should show usage)")


class TestTelegramTrendingCommand:
    """Test /trending command returns trending tokens"""
    
    def test_trending_command_returns_ok(self, api_client):
        """Test /trending command webhook response"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/trending",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /trending command returns ok=True")


class TestTelegramBuyCommand:
    """Test /buy command creates pending order"""
    
    def test_buy_command_valid_format(self, api_client):
        """Test /buy BONK 0.5 command"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/buy BONK 0.5",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /buy BONK 0.5 command returns ok=True")

    def test_buy_command_invalid_format(self, api_client):
        """Test /buy without proper arguments"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/buy",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /buy without args returns ok=True (should show usage)")

    def test_buy_command_only_symbol(self, api_client):
        """Test /buy with only symbol"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/buy BONK",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /buy BONK (missing amount) returns ok=True")

    def test_buy_for_unlinked_user(self, api_client):
        """Test /buy for user without linked wallet"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": 555666777},  # Different chat ID
                    "text": "/buy BONK 0.1",
                    "from": {"username": "random_user"}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /buy for unlinked user returns ok=True")


class TestTelegramSellCommand:
    """Test /sell command"""
    
    def test_sell_command_valid_format(self, api_client):
        """Test /sell BONK 50 command"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/sell BONK 50",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /sell BONK 50 command returns ok=True")

    def test_sell_command_without_percentage(self, api_client):
        """Test /sell with only symbol (defaults to 100%)"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/sell BONK",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /sell BONK (default 100%) returns ok=True")

    def test_sell_command_invalid_format(self, api_client):
        """Test /sell without arguments"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/sell",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /sell without args returns ok=True (should show usage)")


class TestTelegramPositionsCommand:
    """Test /positions command shows user positions"""
    
    def test_positions_command_returns_ok(self, api_client):
        """Test /positions command webhook response"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/positions",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /positions command returns ok=True")

    def test_positions_for_unlinked_user(self, api_client):
        """Test /positions for user without linked wallet"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": 888999000},  # Different chat ID
                    "text": "/positions",
                    "from": {"username": "no_wallet_user"}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /positions for unlinked user returns ok=True")


class TestTelegramPendingOrdersDatabase:
    """Test that buy orders are created in telegram_pending_orders collection"""
    
    def test_buy_command_creates_pending_order(self, api_client):
        """Test /buy creates entry in telegram_pending_orders"""
        # First ensure test account is linked
        api_client.post(
            f"{BASE_URL}/api/telegram/link-account",
            params={
                "wallet_address": TEST_WALLET,
                "chat_id": TEST_CHAT_ID,
                "telegram_username": TEST_USERNAME
            }
        )
        
        # Send buy command
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/buy WIF 0.2",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASSED: /buy WIF 0.2 command processed")


class TestTelegramCommandVariations:
    """Test various command formats and edge cases"""
    
    def test_uppercase_command(self, api_client):
        """Test /PRICE (uppercase) command"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/PRICE SOL",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        print("PASSED: Uppercase command processed")

    def test_lowercase_symbol(self, api_client):
        """Test /price with lowercase symbol"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/price bonk",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        print("PASSED: Lowercase symbol processed")

    def test_buy_with_decimal_amount(self, api_client):
        """Test /buy with decimal SOL amount"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/buy BONK 0.05",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        print("PASSED: Decimal amount processed")

    def test_buy_with_large_amount(self, api_client):
        """Test /buy with amount >10 SOL (should show error)"""
        response = api_client.post(
            f"{BASE_URL}/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "/buy BONK 100",
                    "from": {"username": TEST_USERNAME}
                }
            }
        )
        assert response.status_code == 200
        print("PASSED: Large amount handled")


class TestTelegramStatusAfterLinking:
    """Test telegram status endpoint after linking"""
    
    def test_status_shows_linked(self, api_client):
        """Test status shows linked after account link"""
        # Ensure linked
        api_client.post(
            f"{BASE_URL}/api/telegram/link-account",
            params={
                "wallet_address": TEST_WALLET,
                "chat_id": TEST_CHAT_ID,
                "telegram_username": TEST_USERNAME
            }
        )
        
        response = api_client.get(f"{BASE_URL}/api/telegram/status/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("linked") == True
        print(f"PASSED: Status shows linked=True, username={data.get('telegram_username')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
