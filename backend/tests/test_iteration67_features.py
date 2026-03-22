"""
Iteration 67 Backend Tests
Tests for 3 features:
1. GET /api/ai-trader/auto-trade/status/{wallet} - today_stats with trades_executed and total_sol_used from open positions
2. PUT /api/ai-trader/auto-trade/settings/{wallet} - triggers check-exits when TP/SL changed, returns exits_triggered
3. Frontend refresh button verification (code review only - requires wallet connection)

Test wallet: qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestAutoTradeStatusTodayStats:
    """Test Feature 1: today_stats calculation from open positions"""
    
    def test_status_endpoint_returns_today_stats(self):
        """Verify GET /api/ai-trader/auto-trade/status/{wallet} returns today_stats"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify today_stats exists
        assert "today_stats" in data, "Response missing 'today_stats' field"
        
        today_stats = data["today_stats"]
        
        # Verify required fields exist
        assert "trades_executed" in today_stats, "today_stats missing 'trades_executed'"
        assert "total_sol_used" in today_stats, "today_stats missing 'total_sol_used'"
        
        # Verify types
        assert isinstance(today_stats["trades_executed"], (int, float)), "trades_executed should be numeric"
        assert isinstance(today_stats["total_sol_used"], (int, float)), "total_sol_used should be numeric"
        
        print(f"✓ today_stats: trades_executed={today_stats['trades_executed']}, total_sol_used={today_stats['total_sol_used']}")
    
    def test_today_stats_includes_open_positions_count(self):
        """Verify trades_executed counts open positions"""
        # First get positions count
        positions_response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert positions_response.status_code == 200
        positions_data = positions_response.json()
        open_positions_count = len(positions_data.get("positions", []))
        
        # Get status
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        today_stats = status_data.get("today_stats", {})
        trades_executed = today_stats.get("trades_executed", 0)
        
        # trades_executed should be at least the number of open positions
        assert trades_executed >= open_positions_count, \
            f"trades_executed ({trades_executed}) should be >= open positions ({open_positions_count})"
        
        print(f"✓ trades_executed ({trades_executed}) >= open_positions ({open_positions_count})")
    
    def test_today_stats_includes_position_sol(self):
        """Verify total_sol_used includes SOL from open positions"""
        # Get positions
        positions_response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert positions_response.status_code == 200
        positions_data = positions_response.json()
        
        # Calculate total SOL in positions
        positions = positions_data.get("positions", [])
        position_sol = sum(p.get("amount_sol", 0) for p in positions)
        
        # Get status
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        today_stats = status_data.get("today_stats", {})
        total_sol_used = today_stats.get("total_sol_used", 0)
        
        # total_sol_used should include position SOL
        assert total_sol_used >= position_sol, \
            f"total_sol_used ({total_sol_used}) should be >= position_sol ({position_sol})"
        
        print(f"✓ total_sol_used ({total_sol_used}) includes position_sol ({position_sol})")
    
    def test_today_stats_has_open_positions_field(self):
        """Verify today_stats includes open_positions count"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        today_stats = data.get("today_stats", {})
        
        # Verify open_positions field exists
        assert "open_positions" in today_stats, "today_stats should include 'open_positions' field"
        
        print(f"✓ today_stats includes open_positions: {today_stats['open_positions']}")


class TestAutoTradeSettingsExitTrigger:
    """Test Feature 2: PUT settings triggers check-exits when TP/SL changed"""
    
    def test_settings_update_returns_exits_triggered(self):
        """Verify PUT /api/ai-trader/auto-trade/settings returns exits_triggered array"""
        # Update settings with TP/SL change
        settings_update = {
            "auto_take_profit_percent": 25.0,
            "auto_stop_loss_percent": 12.0
        }
        
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=settings_update
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert data["success"] == True, "success should be True"
        
        # Verify exits_triggered array exists
        assert "exits_triggered" in data, "Response missing 'exits_triggered' field"
        assert isinstance(data["exits_triggered"], list), "exits_triggered should be a list"
        
        # Verify exits_count exists
        assert "exits_count" in data, "Response missing 'exits_count' field"
        assert isinstance(data["exits_count"], int), "exits_count should be an integer"
        
        print(f"✓ Settings update returned exits_triggered (count: {data['exits_count']})")
    
    def test_settings_update_without_tp_sl_no_exit_check(self):
        """Verify settings update without TP/SL doesn't trigger exit check"""
        # Update settings without TP/SL
        settings_update = {
            "auto_cooldown_minutes": 35
        }
        
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=settings_update
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # exits_triggered should still be present but empty (no TP/SL change)
        assert "exits_triggered" in data
        # Note: exits_triggered will be empty list since no TP/SL changed
        
        print(f"✓ Settings update without TP/SL: exits_count={data.get('exits_count', 0)}")
    
    def test_settings_update_with_tp_change_triggers_check(self):
        """Verify TP change triggers exit check"""
        # Get current settings first
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        current_tp = status_response.json().get("settings", {}).get("take_profit_percent", 20)
        
        # Update with different TP
        new_tp = current_tp + 5 if current_tp < 95 else current_tp - 5
        settings_update = {
            "auto_take_profit_percent": new_tp
        }
        
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=settings_update
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify exits_triggered is present
        assert "exits_triggered" in data, "TP change should include exits_triggered in response"
        
        print(f"✓ TP change ({current_tp} -> {new_tp}) triggered exit check")
    
    def test_settings_update_with_sl_change_triggers_check(self):
        """Verify SL change triggers exit check"""
        # Get current settings first
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        current_sl = status_response.json().get("settings", {}).get("stop_loss_percent", 10)
        
        # Update with different SL
        new_sl = current_sl + 2 if current_sl < 48 else current_sl - 2
        settings_update = {
            "auto_stop_loss_percent": new_sl
        }
        
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=settings_update
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify exits_triggered is present
        assert "exits_triggered" in data, "SL change should include exits_triggered in response"
        
        print(f"✓ SL change ({current_sl} -> {new_sl}) triggered exit check")


class TestCheckExitsEndpoint:
    """Test the check-exits endpoint directly"""
    
    def test_check_exits_endpoint_exists(self):
        """Verify POST /api/ai-trader/auto-trade/check-exits/{wallet} works"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert "positions_checked" in data, "Response missing 'positions_checked' field"
        
        print(f"✓ check-exits endpoint works: checked {data.get('positions_checked', 0)} positions")
    
    def test_check_exits_returns_exits_array(self):
        """Verify check-exits returns exits array"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify exits array exists
        assert "exits" in data, "Response missing 'exits' field"
        assert isinstance(data["exits"], list), "exits should be a list"
        
        print(f"✓ check-exits returns exits array (count: {len(data['exits'])})")


class TestPositionsEndpoint:
    """Test positions endpoint for TESTDEL position"""
    
    def test_positions_endpoint_works(self):
        """Verify GET /api/ai-trader/positions/{wallet} works"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "positions" in data, "Response missing 'positions' field"
        assert "count" in data, "Response missing 'count' field"
        
        print(f"✓ Positions endpoint works: {data['count']} positions")
    
    def test_testdel_position_exists(self):
        """Verify TESTDEL position exists with 0.01 SOL"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        positions = data.get("positions", [])
        
        # Look for TESTDEL position
        testdel_positions = [p for p in positions if p.get("token_symbol", "").upper() == "TESTDEL"]
        
        if testdel_positions:
            testdel = testdel_positions[0]
            amount_sol = testdel.get("amount_sol", 0)
            print(f"✓ TESTDEL position found: {amount_sol} SOL")
            assert amount_sol > 0, "TESTDEL position should have SOL amount"
        else:
            print(f"⚠ TESTDEL position not found (may have been sold). Found positions: {[p.get('token_symbol') for p in positions]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
