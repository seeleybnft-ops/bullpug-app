"""
Iteration 91: Telegram Trade Alerts Wiring Tests
Tests:
1. GET /api/telegram/bot-info - returns bot info with username 'Bullpugbot'
2. GET /api/telegram/status/{wallet} - returns linked=true for user wallet
3. POST /api/telegram/test-alert/{wallet} - sends a real test message
4. POST /api/telegram/setup-webhook - sets the webhook correctly
5. GET /api/telegram/webhook-info - returns the current webhook URL
6. Verify send_trade_alert function exists and handles all action types
7. Verify auto_trader_engine.py imports and calls send_trade_alert at buy/sell points
8. GET /api/ - API health check
"""

import pytest
import requests
import os
import ast
import re

# Use the public URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cosmic-runner-hub.preview.emergentagent.com").rstrip("/")
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
ACCESS_CODE = "bullpug2026"


class TestTelegramEndpoints:
    """Test Telegram API endpoints"""
    
    def test_api_health_check(self):
        """Test GET /api/ returns API health check"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        # Should have some indication it's working
        assert data is not None, "Health check returned no data"
        print(f"✓ API health check passed: {data}")
    
    def test_telegram_bot_info(self):
        """Test GET /api/telegram/bot-info returns bot info with username 'Bullpugbot'"""
        response = requests.get(f"{BASE_URL}/api/telegram/bot-info")
        assert response.status_code == 200, f"Bot info failed: {response.status_code}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Missing 'success' field"
        assert data["success"] == True, f"Bot info not successful: {data}"
        assert "bot_username" in data, "Missing 'bot_username' field"
        
        # Verify bot username is Bullpugbot (case-insensitive check)
        bot_username = data.get("bot_username", "").lower()
        assert "bullpug" in bot_username, f"Expected 'Bullpugbot', got '{data.get('bot_username')}'"
        
        # Verify link is present
        assert "link" in data, "Missing 'link' field"
        assert "t.me" in data["link"], f"Invalid bot link: {data['link']}"
        
        print(f"✓ Bot info: username={data['bot_username']}, link={data['link']}")
    
    def test_telegram_status_linked(self):
        """Test GET /api/telegram/status/{wallet} returns linked=true for user wallet"""
        response = requests.get(f"{BASE_URL}/api/telegram/status/{TEST_WALLET}")
        assert response.status_code == 200, f"Status check failed: {response.status_code}"
        data = response.json()
        
        # Verify linked status
        assert "linked" in data, "Missing 'linked' field"
        assert data["linked"] == True, f"Expected linked=true, got {data}"
        
        # Verify additional fields when linked
        if data["linked"]:
            assert "telegram_username" in data, "Missing 'telegram_username' for linked account"
            assert "alerts_enabled" in data, "Missing 'alerts_enabled' for linked account"
            print(f"✓ Telegram linked: username={data.get('telegram_username')}, alerts_enabled={data.get('alerts_enabled')}")
        else:
            print(f"✗ Telegram NOT linked for wallet {TEST_WALLET}")
    
    def test_telegram_test_alert(self):
        """Test POST /api/telegram/test-alert/{wallet} sends a real test message"""
        response = requests.post(f"{BASE_URL}/api/telegram/test-alert/{TEST_WALLET}")
        assert response.status_code == 200, f"Test alert failed: {response.status_code}, response: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Missing 'success' field"
        assert data["success"] == True, f"Test alert not successful: {data}"
        assert "chat_id" in data, "Missing 'chat_id' field"
        
        print(f"✓ Test alert sent successfully to chat_id={data.get('chat_id')}, username={data.get('telegram_username')}")
    
    def test_telegram_webhook_info(self):
        """Test GET /api/telegram/webhook-info returns the current webhook URL"""
        response = requests.get(f"{BASE_URL}/api/telegram/webhook-info")
        assert response.status_code == 200, f"Webhook info failed: {response.status_code}"
        data = response.json()
        
        # Verify webhook URL is set
        assert "url" in data, "Missing 'url' field in webhook info"
        webhook_url = data.get("url", "")
        
        if webhook_url:
            # Verify it points to our API
            assert "/api/telegram/webhook" in webhook_url, f"Webhook URL doesn't contain expected path: {webhook_url}"
            print(f"✓ Webhook URL: {webhook_url}")
        else:
            print(f"⚠ Webhook URL is empty - may need to be set")
        
        # Check for pending updates count
        if "pending_update_count" in data:
            print(f"  Pending updates: {data['pending_update_count']}")
    
    def test_telegram_setup_webhook(self):
        """Test POST /api/telegram/setup-webhook sets the webhook correctly"""
        # Use the current preview URL
        webhook_base = BASE_URL
        response = requests.post(
            f"{BASE_URL}/api/telegram/setup-webhook",
            params={"webhook_url": webhook_base}
        )
        assert response.status_code == 200, f"Setup webhook failed: {response.status_code}, response: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Missing 'success' field"
        assert data["success"] == True, f"Webhook setup not successful: {data}"
        assert "webhook_url" in data, "Missing 'webhook_url' field"
        
        # Verify the webhook URL is correct
        expected_webhook = f"{webhook_base}/api/telegram/webhook"
        assert data["webhook_url"] == expected_webhook, f"Webhook URL mismatch: expected {expected_webhook}, got {data['webhook_url']}"
        
        print(f"✓ Webhook set to: {data['webhook_url']}")


class TestSendTradeAlertFunction:
    """Test send_trade_alert function exists and handles all action types"""
    
    def test_send_trade_alert_function_exists(self):
        """Verify send_trade_alert function exists in telegram.py"""
        telegram_file = "/app/backend/routers/telegram.py"
        
        with open(telegram_file, "r") as f:
            content = f.read()
        
        # Check function definition exists
        assert "async def send_trade_alert" in content, "send_trade_alert function not found"
        
        # Check function signature
        assert "wallet_address: str" in content, "Missing wallet_address parameter"
        assert "trade_data: dict" in content, "Missing trade_data parameter"
        
        print("✓ send_trade_alert function exists with correct signature")
    
    def test_send_trade_alert_handles_buy_action(self):
        """Verify send_trade_alert handles buy/auto_buy actions"""
        telegram_file = "/app/backend/routers/telegram.py"
        
        with open(telegram_file, "r") as f:
            content = f.read()
        
        # Check for buy action handling
        assert '"buy"' in content or "'buy'" in content, "buy action not handled"
        assert '"auto_buy"' in content or "'auto_buy'" in content, "auto_buy action not handled"
        assert "BUY Executed" in content or "BUY" in content, "BUY message not found"
        
        print("✓ send_trade_alert handles buy/auto_buy actions")
    
    def test_send_trade_alert_handles_take_profit_action(self):
        """Verify send_trade_alert handles take_profit actions"""
        telegram_file = "/app/backend/routers/telegram.py"
        
        with open(telegram_file, "r") as f:
            content = f.read()
        
        # Check for take_profit action handling
        assert '"take_profit"' in content or "'take_profit'" in content, "take_profit action not handled"
        assert "TAKE-PROFIT" in content or "Take-Profit" in content, "TAKE-PROFIT message not found"
        
        print("✓ send_trade_alert handles take_profit actions")
    
    def test_send_trade_alert_handles_stop_loss_action(self):
        """Verify send_trade_alert handles stop_loss actions"""
        telegram_file = "/app/backend/routers/telegram.py"
        
        with open(telegram_file, "r") as f:
            content = f.read()
        
        # Check for stop_loss action handling
        assert '"stop_loss"' in content or "'stop_loss'" in content, "stop_loss action not handled"
        assert "STOP-LOSS" in content or "Stop-Loss" in content, "STOP-LOSS message not found"
        
        print("✓ send_trade_alert handles stop_loss actions")
    
    def test_send_trade_alert_handles_trailing_stop_action(self):
        """Verify send_trade_alert handles trailing_stop actions"""
        telegram_file = "/app/backend/routers/telegram.py"
        
        with open(telegram_file, "r") as f:
            content = f.read()
        
        # Check for trailing_stop action handling
        assert '"trailing_stop"' in content or "'trailing_stop'" in content, "trailing_stop action not handled"
        assert "TRAILING STOP" in content or "Trailing Stop" in content, "TRAILING STOP message not found"
        
        print("✓ send_trade_alert handles trailing_stop actions")
    
    def test_send_trade_alert_handles_dca_actions(self):
        """Verify send_trade_alert handles DCA partial sell actions"""
        telegram_file = "/app/backend/routers/telegram.py"
        
        with open(telegram_file, "r") as f:
            content = f.read()
        
        # Check for DCA action handling
        assert '"dca_tp1"' in content or "'dca_tp1'" in content, "dca_tp1 action not handled"
        assert '"dca_tp2"' in content or "'dca_tp2'" in content, "dca_tp2 action not handled"
        assert "DCA" in content, "DCA message not found"
        
        print("✓ send_trade_alert handles DCA partial sell actions")
    
    def test_send_trade_alert_handles_runner_buy(self):
        """Verify send_trade_alert handles runner buy actions"""
        telegram_file = "/app/backend/routers/telegram.py"
        
        with open(telegram_file, "r") as f:
            content = f.read()
        
        # Check for runner handling
        assert "is_runner" in content, "is_runner field not handled"
        assert "RUNNER" in content, "RUNNER tag not found in message"
        
        print("✓ send_trade_alert handles runner buy actions")


class TestAutoTraderEngineWiring:
    """Test auto_trader_engine.py imports and calls send_trade_alert"""
    
    def test_auto_trader_imports_send_trade_alert(self):
        """Verify auto_trader_engine.py imports send_trade_alert"""
        engine_file = "/app/backend/services/auto_trader_engine.py"
        
        with open(engine_file, "r") as f:
            content = f.read()
        
        # Check for import statement
        assert "from routers.telegram import send_trade_alert" in content, "send_trade_alert not imported"
        
        print("✓ auto_trader_engine.py imports send_trade_alert")
    
    def test_auto_trader_calls_send_trade_alert_on_buy(self):
        """Verify auto_trader_engine.py calls send_trade_alert at buy execution points"""
        engine_file = "/app/backend/services/auto_trader_engine.py"
        
        with open(engine_file, "r") as f:
            content = f.read()
        
        # Count occurrences of send_trade_alert calls
        buy_alert_count = content.count('await send_trade_alert(wallet_address, {')
        
        # Should have at least 2 buy alert calls (known tokens + runners)
        assert buy_alert_count >= 2, f"Expected at least 2 send_trade_alert calls, found {buy_alert_count}"
        
        # Check for buy action in the calls
        assert '"action": "buy"' in content, "Buy action not found in send_trade_alert call"
        
        print(f"✓ auto_trader_engine.py calls send_trade_alert {buy_alert_count} times (buy + runner + exit)")
    
    def test_auto_trader_calls_send_trade_alert_on_exit(self):
        """Verify auto_trader_engine.py calls send_trade_alert at exit/sell execution points"""
        engine_file = "/app/backend/services/auto_trader_engine.py"
        
        with open(engine_file, "r") as f:
            content = f.read()
        
        # Check for exit alert call
        assert '"action": exit_action' in content, "Exit action not found in send_trade_alert call"
        
        # Check for pnl fields in exit alert
        assert '"pnl_percent"' in content, "pnl_percent not included in exit alert"
        assert '"pnl_sol"' in content, "pnl_sol not included in exit alert"
        
        print("✓ auto_trader_engine.py calls send_trade_alert at exit points with PnL data")
    
    def test_auto_trader_buy_alert_at_line_710(self):
        """Verify send_trade_alert is called around line 710 for known token buys"""
        engine_file = "/app/backend/services/auto_trader_engine.py"
        
        with open(engine_file, "r") as f:
            lines = f.readlines()
        
        # Check lines 700-730 for send_trade_alert call
        found = False
        for i in range(700, min(730, len(lines))):
            if "send_trade_alert" in lines[i]:
                found = True
                print(f"✓ Found send_trade_alert at line {i+1}: {lines[i].strip()[:60]}...")
                break
        
        assert found, "send_trade_alert not found around line 710 for known token buys"
    
    def test_auto_trader_runner_alert_at_line_1015(self):
        """Verify send_trade_alert is called around line 1015 for runner buys"""
        engine_file = "/app/backend/services/auto_trader_engine.py"
        
        with open(engine_file, "r") as f:
            lines = f.readlines()
        
        # Check lines 1010-1040 for send_trade_alert call
        found = False
        for i in range(1010, min(1040, len(lines))):
            if "send_trade_alert" in lines[i]:
                found = True
                print(f"✓ Found send_trade_alert at line {i+1}: {lines[i].strip()[:60]}...")
                break
        
        assert found, "send_trade_alert not found around line 1015 for runner buys"
    
    def test_auto_trader_exit_alert_at_line_1577(self):
        """Verify send_trade_alert is called around line 1577 for exit sells"""
        engine_file = "/app/backend/services/auto_trader_engine.py"
        
        with open(engine_file, "r") as f:
            lines = f.readlines()
        
        # Check lines 1590-1620 for send_trade_alert call
        found = False
        for i in range(1590, min(1620, len(lines))):
            if "send_trade_alert" in lines[i]:
                found = True
                print(f"✓ Found send_trade_alert at line {i+1}: {lines[i].strip()[:60]}...")
                break
        
        assert found, "send_trade_alert not found around line 1577 for exit sells"


class TestTelegramAccountData:
    """Test that the user's Telegram account is properly linked"""
    
    def test_telegram_account_has_chat_id(self):
        """Verify the linked Telegram account has a chat_id"""
        response = requests.get(f"{BASE_URL}/api/telegram/status/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("linked") == True, "Account not linked"
        # The chat_id is not exposed in the status endpoint for security
        # But we can verify alerts_enabled is present
        assert "alerts_enabled" in data, "alerts_enabled field missing"
        
        print(f"✓ Telegram account linked with alerts_enabled={data.get('alerts_enabled')}")
    
    def test_telegram_username_is_seeleyb(self):
        """Verify the linked Telegram username is Seeleyb"""
        response = requests.get(f"{BASE_URL}/api/telegram/status/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("linked") == True, "Account not linked"
        telegram_username = data.get("telegram_username", "")
        
        # Check username (case-insensitive)
        assert telegram_username.lower() == "seeleyb", f"Expected 'Seeleyb', got '{telegram_username}'"
        
        print(f"✓ Telegram username verified: {telegram_username}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
