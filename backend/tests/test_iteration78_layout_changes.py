"""
Iteration 78: Testing Layout Changes for Bullpug Trading Bot
Tests:
1. GET /api/ai-trader/performance-scorecard/{wallet_address} - New endpoint
2. Regression tests for platform-stats, sniper-targets, intelligence-dashboard
3. Settings CRUD with trading_mode
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"

class TestPerformanceScorecard:
    """Test the new performance-scorecard endpoint"""
    
    def test_performance_scorecard_returns_200(self):
        """Test that performance scorecard endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/performance-scorecard/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Performance scorecard endpoint returns 200")
    
    def test_performance_scorecard_has_all_time_stats(self):
        """Test that scorecard has all_time stats"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/performance-scorecard/{TEST_WALLET}")
        data = response.json()
        
        assert "all_time" in data, "Missing all_time field"
        all_time = data["all_time"]
        assert "total_trades" in all_time, "Missing total_trades in all_time"
        assert "win_rate" in all_time, "Missing win_rate in all_time"
        assert "total_pnl_sol" in all_time, "Missing total_pnl_sol in all_time"
        assert "wins" in all_time, "Missing wins in all_time"
        assert "losses" in all_time, "Missing losses in all_time"
        print(f"✓ All-time stats present: {all_time['total_trades']} trades, {all_time['win_rate']}% WR")
    
    def test_performance_scorecard_has_this_week_stats(self):
        """Test that scorecard has this_week stats"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/performance-scorecard/{TEST_WALLET}")
        data = response.json()
        
        assert "this_week" in data, "Missing this_week field"
        this_week = data["this_week"]
        assert "trades" in this_week, "Missing trades in this_week"
        assert "pnl_sol" in this_week, "Missing pnl_sol in this_week"
        assert "wins" in this_week, "Missing wins in this_week"
        assert "win_rate" in this_week, "Missing win_rate in this_week"
        print(f"✓ This week stats present: {this_week['trades']} trades, {this_week['win_rate']}% WR")
    
    def test_performance_scorecard_has_current_streak(self):
        """Test that scorecard has current_streak"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/performance-scorecard/{TEST_WALLET}")
        data = response.json()
        
        assert "current_streak" in data, "Missing current_streak field"
        assert isinstance(data["current_streak"], int), "current_streak should be int"
        print(f"✓ Current streak: {data['current_streak']}")
    
    def test_performance_scorecard_has_active_positions(self):
        """Test that scorecard has active_positions"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/performance-scorecard/{TEST_WALLET}")
        data = response.json()
        
        assert "active_positions" in data, "Missing active_positions field"
        assert isinstance(data["active_positions"], int), "active_positions should be int"
        print(f"✓ Active positions: {data['active_positions']}")
    
    def test_performance_scorecard_has_best_trade_this_week(self):
        """Test that scorecard has best_trade_this_week (can be null)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/performance-scorecard/{TEST_WALLET}")
        data = response.json()
        
        assert "best_trade_this_week" in data, "Missing best_trade_this_week field"
        # Can be None if no trades this week
        if data["best_trade_this_week"]:
            assert "token_symbol" in data["best_trade_this_week"], "Missing token_symbol in best_trade"
            assert "pnl_pct" in data["best_trade_this_week"], "Missing pnl_pct in best_trade"
            print(f"✓ Best trade this week: {data['best_trade_this_week']['token_symbol']} +{data['best_trade_this_week']['pnl_pct']}%")
        else:
            print("✓ Best trade this week: None (no trades this week)")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    def test_platform_stats_returns_200(self):
        """Test platform-stats endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Platform stats returns 200")
    
    def test_platform_stats_has_correct_fields(self):
        """Test platform-stats has trading stats, not sniper targets"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        data = response.json()
        
        # Should have trading stats
        assert "total_trades" in data, "Missing total_trades"
        assert "win_rate" in data, "Missing win_rate"
        assert "total_pnl_sol" in data, "Missing total_pnl_sol"
        assert "active_positions" in data, "Missing active_positions"
        
        # Should NOT have sniper targets
        assert "targets" not in data, "Should not have targets (sniper data)"
        print(f"✓ Platform stats has correct fields: {data['total_trades']} trades, {data['win_rate']}% WR")
    
    def test_sniper_targets_returns_200(self):
        """Test sniper-targets endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/sniper-targets")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Sniper targets returns 200")
    
    def test_sniper_targets_has_targets_array(self):
        """Test sniper-targets has targets array"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/sniper-targets")
        data = response.json()
        
        assert "targets" in data, "Missing targets array"
        assert "count" in data, "Missing count"
        assert isinstance(data["targets"], list), "targets should be a list"
        print(f"✓ Sniper targets: {data['count']} targets found")
    
    def test_intelligence_dashboard_returns_200(self):
        """Test intelligence-dashboard endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Intelligence dashboard returns 200")
    
    def test_intelligence_dashboard_has_all_systems(self):
        """Test intelligence-dashboard has all 4 systems"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        assert "price_collector" in data, "Missing price_collector"
        assert "smart_money" in data, "Missing smart_money"
        assert "sentiment" in data, "Missing sentiment"
        assert "jito" in data, "Missing jito"
        
        # Check price_collector details
        assert data["price_collector"]["status"] == "active", "price_collector should be active"
        assert "tokens_tracked" in data["price_collector"], "Missing tokens_tracked"
        
        # Check smart_money details
        assert data["smart_money"]["status"] == "active", "smart_money should be active"
        assert "wallets_tracked" in data["smart_money"], "Missing wallets_tracked"
        
        print(f"✓ Intelligence dashboard has all 4 systems active")


class TestSettingsCRUD:
    """Test settings CRUD with trading_mode"""
    
    def test_get_settings_returns_200(self):
        """Test GET settings returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET settings returns 200")
    
    def test_settings_has_trading_mode(self):
        """Test settings has trading_mode field"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        data = response.json()
        
        assert "trading_mode" in data, "Missing trading_mode field"
        assert data["trading_mode"] in ["conservative", "normal", "aggressive", "sniper"], \
            f"Invalid trading_mode: {data['trading_mode']}"
        print(f"✓ Settings has trading_mode: {data['trading_mode']}")
    
    def test_save_settings_with_trading_mode(self):
        """Test saving settings with trading_mode"""
        # First get current settings
        get_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        current_settings = get_response.json()
        original_mode = current_settings.get("trading_mode", "normal")
        
        # Save with a different mode
        new_mode = "aggressive" if original_mode != "aggressive" else "normal"
        save_response = requests.post(f"{BASE_URL}/api/ai-trader/settings", json={
            "wallet_address": TEST_WALLET,
            "trading_mode": new_mode
        })
        assert save_response.status_code == 200, f"Expected 200, got {save_response.status_code}"
        
        # Verify it was saved
        verify_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        verify_data = verify_response.json()
        assert verify_data["trading_mode"] == new_mode, f"Expected {new_mode}, got {verify_data['trading_mode']}"
        
        # Restore original mode
        requests.post(f"{BASE_URL}/api/ai-trader/settings", json={
            "wallet_address": TEST_WALLET,
            "trading_mode": original_mode
        })
        
        print(f"✓ Settings CRUD with trading_mode works (tested: {new_mode})")


class TestHealthAndBasicEndpoints:
    """Basic health and endpoint tests"""
    
    def test_api_root_health(self):
        """Test API root returns 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ API root health check passed")
    
    def test_tokens_endpoint(self):
        """Test tokens endpoint returns safer and high_risk tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "safer_tokens" in data, "Missing safer_tokens"
        assert "high_risk_tokens" in data, "Missing high_risk_tokens"
        print(f"✓ Tokens endpoint: {len(data['safer_tokens'])} safer, {len(data['high_risk_tokens'])} high risk")
    
    def test_positions_endpoint(self):
        """Test positions endpoint returns positions array"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "positions" in data, "Missing positions array"
        assert "count" in data, "Missing count"
        print(f"✓ Positions endpoint: {data['count']} positions")
    
    def test_signals_endpoint(self):
        """Test signals endpoint returns signals array"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/signals/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "signals" in data, "Missing signals array"
        assert "count" in data, "Missing count"
        print(f"✓ Signals endpoint: {data['count']} signals")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
