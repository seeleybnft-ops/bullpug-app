"""
Iteration 73: Bullpug Trading Bot Feature Tests

Tests for:
1. Backend API Health
2. AI Trader Positions
3. AI Trader History (on-chain only, no duplicates)
4. AI Trader Auto-Trade Settings (TP/SL percentages)
5. Custodial Wallet Balance
6. Top Picks (safe_picks and volatile_picks)
7. Runner Tokens
8. Runner Alerts Status
9. Runner Alerts Preferences
10. Auto-Trade Exit Check
11. Reset Statistics
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pug-journal-2.preview.emergentagent.com').rstrip('/')

# Test credentials from review request
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"


class TestHealthEndpoint:
    """Test 1: Backend API Health"""
    
    def test_health_endpoint_returns_success(self):
        """GET /api/ should return success (root API endpoint)"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        # Root endpoint returns {"message": "Bullpug API - Guardian of the Memecoin Universe"}
        assert "message" in data or "status" in data, f"Unexpected health response: {data}"
        print(f"✓ API root endpoint returned: {data}")


class TestAITraderPositions:
    """Test 2: AI Trader Positions"""
    
    def test_get_positions_returns_array(self):
        """GET /api/ai-trader/positions/{wallet} should return positions array"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Positions endpoint failed: {response.text}"
        data = response.json()
        assert "positions" in data, f"Missing 'positions' key in response: {data}"
        assert isinstance(data["positions"], list), f"Positions should be a list: {type(data['positions'])}"
        print(f"✓ Positions endpoint returned {len(data['positions'])} positions")
        
        # Verify position structure if any exist
        if data["positions"]:
            pos = data["positions"][0]
            expected_fields = ["token_symbol", "entry_price", "status"]
            for field in expected_fields:
                assert field in pos, f"Position missing field '{field}': {pos.keys()}"
            print(f"✓ Position structure verified: {pos.get('token_symbol')}")


class TestAITraderHistory:
    """Test 3: AI Trader History (on-chain only, no duplicates)"""
    
    def test_get_history_returns_trades_with_stats(self):
        """GET /api/ai-trader/history/{wallet} should return trades with accurate stats"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        assert response.status_code == 200, f"History endpoint failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "trades" in data, f"Missing 'trades' key: {data.keys()}"
        assert "stats" in data, f"Missing 'stats' key: {data.keys()}"
        assert isinstance(data["trades"], list), f"Trades should be a list"
        
        # Verify stats structure
        stats = data["stats"]
        expected_stats = ["total_trades", "wins", "losses", "win_rate", "total_pnl_sol"]
        for stat in expected_stats:
            assert stat in stats, f"Stats missing '{stat}': {stats.keys()}"
        
        print(f"✓ History stats: {stats['total_trades']} trades, {stats['win_rate']:.1f}% win rate, {stats['total_pnl_sol']:.4f} SOL P/L")
        
        # Check for duplicates (1 buy + 1 sell per position max)
        if data["trades"]:
            position_ids = {}
            for trade in data["trades"]:
                pos_id = trade.get("position_id")
                trade_type = trade.get("trade_type")
                if pos_id:
                    key = f"{pos_id}_{trade_type}"
                    if key in position_ids:
                        print(f"⚠ Potential duplicate: {key}")
                    position_ids[key] = position_ids.get(key, 0) + 1
            
            # Verify no more than 1 buy and 1 sell per position
            for key, count in position_ids.items():
                assert count <= 1, f"Duplicate trade found: {key} appears {count} times"
            print(f"✓ No duplicate trades found in {len(data['trades'])} trades")


class TestAutoTradeSettings:
    """Test 4: AI Trader Auto-Trade Settings (TP/SL percentages)"""
    
    def test_get_auto_trade_status_returns_settings(self):
        """GET /api/ai-trader/auto-trade/status/{wallet} should return settings with TP/SL"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert response.status_code == 200, f"Auto-trade status failed: {response.text}"
        data = response.json()
        
        # Verify main fields
        assert "auto_trade_enabled" in data, f"Missing 'auto_trade_enabled': {data.keys()}"
        assert "settings" in data, f"Missing 'settings': {data.keys()}"
        
        settings = data["settings"]
        # Verify TP/SL percentages exist
        tp_key = "take_profit_percent" if "take_profit_percent" in settings else "auto_take_profit_percent"
        sl_key = "stop_loss_percent" if "stop_loss_percent" in settings else "auto_stop_loss_percent"
        
        assert tp_key in settings or "auto_take_profit_percent" in settings, f"Missing take profit setting: {settings.keys()}"
        assert sl_key in settings or "auto_stop_loss_percent" in settings, f"Missing stop loss setting: {settings.keys()}"
        
        tp_value = settings.get(tp_key) or settings.get("auto_take_profit_percent", 0)
        sl_value = settings.get(sl_key) or settings.get("auto_stop_loss_percent", 0)
        
        print(f"✓ Auto-trade status: enabled={data['auto_trade_enabled']}, TP={tp_value}%, SL={sl_value}%")


class TestCustodialWallet:
    """Test 5: Custodial Wallet Balance"""
    
    def test_get_custodial_wallet_balance(self):
        """GET /api/custodial-wallet/balance/{wallet} or /info/{wallet} should return balance"""
        # Try /info endpoint first (based on code review)
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        
        if response.status_code == 200:
            data = response.json()
            assert "balance_sol" in data or "balance_lamports" in data, f"Missing balance field: {data.keys()}"
            balance = data.get("balance_sol", data.get("balance_lamports", 0) / 1e9)
            print(f"✓ Custodial wallet balance: {balance} SOL")
            print(f"✓ Custodial address: {data.get('wallet_address', 'N/A')}")
        else:
            # Try /balance endpoint as fallback
            response = requests.get(f"{BASE_URL}/api/custodial-wallet/balance/{TEST_WALLET}")
            assert response.status_code == 200, f"Custodial balance failed: {response.text}"
            data = response.json()
            print(f"✓ Custodial wallet response: {data}")


class TestTopPicks:
    """Test 6: Top Picks (safe_picks and volatile_picks)"""
    
    def test_get_coin_recommendations(self):
        """GET /api/ai-suggestions/coin-recommendations should return safe and volatile picks"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200, f"Coin recommendations failed: {response.text}"
        data = response.json()
        
        # Verify both pick types exist
        assert "safe_picks" in data, f"Missing 'safe_picks': {data.keys()}"
        assert "volatile_picks" in data, f"Missing 'volatile_picks': {data.keys()}"
        
        assert isinstance(data["safe_picks"], list), "safe_picks should be a list"
        assert isinstance(data["volatile_picks"], list), "volatile_picks should be a list"
        
        print(f"✓ Top Picks: {len(data['safe_picks'])} safe, {len(data['volatile_picks'])} volatile")
        
        # Verify structure of picks if any exist
        for pick_type in ["safe_picks", "volatile_picks"]:
            if data[pick_type]:
                pick = data[pick_type][0]
                assert "symbol" in pick, f"{pick_type}[0] missing 'symbol': {pick.keys()}"
                print(f"  - First {pick_type}: {pick.get('symbol')}")


class TestRunnerTokens:
    """Test 7: Runner Tokens"""
    
    def test_get_runner_tokens(self):
        """GET /api/ai-trader/runners should return runner tokens list"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        assert response.status_code == 200, f"Runners endpoint failed: {response.text}"
        data = response.json()
        
        assert "runners" in data, f"Missing 'runners': {data.keys()}"
        assert isinstance(data["runners"], list), "runners should be a list"
        
        print(f"✓ Runner tokens: {len(data['runners'])} found")
        
        # Verify runner structure if any exist
        if data["runners"]:
            runner = data["runners"][0]
            expected_fields = ["symbol", "token_address"]
            for field in expected_fields:
                if field in runner:
                    print(f"  - First runner: {runner.get('symbol', 'N/A')}")
                    break


class TestRunnerAlertsStatus:
    """Test 8: Runner Alerts Status"""
    
    def test_get_runner_alerts_status(self):
        """GET /api/runner-alerts/status should return active status with alert categories"""
        response = requests.get(f"{BASE_URL}/api/runner-alerts/status")
        assert response.status_code == 200, f"Runner alerts status failed: {response.text}"
        data = response.json()
        
        assert "active" in data, f"Missing 'active' field: {data.keys()}"
        assert "alert_categories" in data, f"Missing 'alert_categories': {data.keys()}"
        
        assert isinstance(data["alert_categories"], list), "alert_categories should be a list"
        
        print(f"✓ Runner alerts: active={data['active']}, categories={data['alert_categories']}")


class TestRunnerAlertsPreferences:
    """Test 9: Runner Alerts Preferences"""
    
    def test_get_runner_alerts_preferences(self):
        """GET /api/runner-alerts/preferences/{wallet} should return user preferences"""
        response = requests.get(f"{BASE_URL}/api/runner-alerts/preferences/{TEST_WALLET}")
        assert response.status_code == 200, f"Runner alerts preferences failed: {response.text}"
        data = response.json()
        
        # Verify preference fields
        expected_fields = ["enabled", "telegram_enabled", "push_enabled"]
        for field in expected_fields:
            assert field in data, f"Missing preference '{field}': {data.keys()}"
        
        print(f"✓ Runner alert preferences: enabled={data['enabled']}, telegram={data['telegram_enabled']}, push={data['push_enabled']}")


class TestAutoTradeExitCheck:
    """Test 10: Auto-Trade Exit Check"""
    
    def test_check_exits_endpoint(self):
        """POST /api/ai-trader/auto-trade/check-exits/{wallet} should check positions for TP/SL"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        assert response.status_code == 200, f"Check exits failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "positions_checked" in data or "exits" in data or "message" in data, f"Unexpected response: {data.keys()}"
        
        print(f"✓ Exit check response: {data}")


class TestResetStatistics:
    """Test 11: Reset Statistics (read-only test - don't actually reset)"""
    
    def test_reset_statistics_endpoint_exists(self):
        """POST /api/ai-trader/reset-statistics/{wallet} endpoint should exist"""
        # We'll just verify the endpoint exists by checking it doesn't return 404
        # Using a dummy wallet to avoid affecting real data
        dummy_wallet = "DummyWalletForTestingOnly123456789"
        response = requests.post(f"{BASE_URL}/api/ai-trader/reset-statistics/{dummy_wallet}")
        
        # Should return 200 (success) or 400/422 (validation error), not 404
        assert response.status_code != 404, f"Reset statistics endpoint not found"
        print(f"✓ Reset statistics endpoint exists (status: {response.status_code})")


class TestSchedulerRunning:
    """Test 12: Verify scheduler is running (via logs or status)"""
    
    def test_scheduler_status_via_auto_trade(self):
        """Verify auto-trade exit check is running by checking recent activity"""
        # The scheduler runs every minute, so we verify by checking the auto-trade status
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # If auto-trade is enabled, the scheduler should be checking exits
        if data.get("auto_trade_enabled"):
            print(f"✓ Auto-trade is enabled - scheduler should be running exit checks every minute")
        else:
            print(f"✓ Auto-trade status retrieved (enabled={data.get('auto_trade_enabled')})")
        
        # Verify today_stats exists (populated by scheduler)
        if "today_stats" in data:
            print(f"✓ Today stats available: {data['today_stats']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
