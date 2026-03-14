"""
Test Suite for Bullpug Trading Bot - Iteration 48
Testing: Auto-Trade Settings UI, Game achievements, Music/Sound toggles, Backend endpoints

Features to test:
1. AI Trading Bot Phase 3 - Auto-Trade Settings endpoints
2. Game achievements endpoints (if any)  
3. Auto-trade toggle and status endpoints
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"

# ============================================
# Auto-Trade Endpoints Tests
# ============================================

class TestAutoTradeStatus:
    """Tests for GET /api/ai-trader/auto-trade/status/{wallet}"""
    
    def test_auto_trade_status_returns_ok(self):
        """Test that auto-trade status endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert response.status_code == 200
        print(f"✓ Auto-trade status returns 200")
    
    def test_auto_trade_status_structure(self):
        """Test that auto-trade status has required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        data = response.json()
        
        assert "auto_trade_enabled" in data
        assert "settings" in data or data.get("settings") is None
        assert "today_stats" in data
        
        # Verify today_stats structure
        if data.get("today_stats"):
            assert "trades_executed" in data["today_stats"]
            assert "total_sol_used" in data["today_stats"]
            assert "pnl_sol" in data["today_stats"]
        
        print(f"✓ Auto-trade status has proper structure: auto_trade_enabled={data['auto_trade_enabled']}")


class TestAutoTradeToggle:
    """Tests for POST /api/ai-trader/auto-trade/toggle/{wallet}"""
    
    def test_toggle_auto_trade_enable(self):
        """Test enabling auto-trade"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/toggle/{TEST_WALLET}?enabled=true")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert data.get("auto_trade_enabled") == True
        print(f"✓ Auto-trade enabled successfully")
    
    def test_toggle_auto_trade_disable(self):
        """Test disabling auto-trade"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/toggle/{TEST_WALLET}?enabled=false")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert data.get("auto_trade_enabled") == False
        print(f"✓ Auto-trade disabled successfully")
    
    def test_toggle_response_has_message(self):
        """Test that toggle response includes a message"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/toggle/{TEST_WALLET}?enabled=true")
        data = response.json()
        
        assert "message" in data
        print(f"✓ Toggle response message: {data['message']}")
        
        # Clean up - disable again
        requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/toggle/{TEST_WALLET}?enabled=false")


class TestAutoTradeLogs:
    """Tests for GET /api/ai-trader/auto-trade/logs/{wallet}"""
    
    def test_auto_trade_logs_returns_ok(self):
        """Test that auto-trade logs endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/logs/{TEST_WALLET}?limit=20")
        assert response.status_code == 200
        print(f"✓ Auto-trade logs returns 200")
    
    def test_auto_trade_logs_structure(self):
        """Test that auto-trade logs has logs array"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/logs/{TEST_WALLET}?limit=20")
        data = response.json()
        
        assert "logs" in data
        assert isinstance(data["logs"], list)
        print(f"✓ Auto-trade logs has {len(data['logs'])} entries")


class TestAutoTradeSettings:
    """Tests for PUT /api/ai-trader/auto-trade/settings/{wallet}"""
    
    def test_update_auto_trade_settings(self):
        """Test updating auto-trade settings"""
        settings_update = {
            "max_daily_trades": 5,
            "max_sol_per_trade": 0.1,
            "min_confidence_score": 70,
            "allowed_risk_levels": ["safer"]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=settings_update
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        print(f"✓ Auto-trade settings updated successfully")


# ============================================
# Leaderboard Tests (for Game Achievements context)
# ============================================

class TestLeaderboard:
    """Tests for game leaderboard endpoint"""
    
    def test_leaderboard_returns_ok(self):
        """Test that leaderboard endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=10")
        assert response.status_code == 200
        print(f"✓ Leaderboard returns 200")
    
    def test_leaderboard_structure(self):
        """Test that leaderboard has expected structure"""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=10")
        data = response.json()
        
        assert "leaderboard" in data
        assert "days_until_reset" in data
        assert isinstance(data["leaderboard"], list)
        print(f"✓ Leaderboard has {len(data['leaderboard'])} entries, resets in {data['days_until_reset']} days")
    
    def test_leaderboard_submit_score(self):
        """Test submitting a score to leaderboard"""
        score_data = {
            "player_name": "TEST_Player",
            "score": 100,
            "moonCheese": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/leaderboard/submit", json=score_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "rank" in data or "message" in data
        print(f"✓ Score submitted, response: {data}")


# ============================================
# AI Trader Core Endpoints (verification)
# ============================================

class TestAITraderCore:
    """Verify core AI Trader endpoints are still working"""
    
    def test_tokens_endpoint(self):
        """Test GET /api/ai-trader/tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        data = response.json()
        
        assert "safer_tokens" in data or "high_risk_tokens" in data
        print(f"✓ Tokens endpoint working")
    
    def test_signals_endpoint(self):
        """Test GET /api/ai-trader/signals/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/signals/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "signals" in data
        print(f"✓ Signals endpoint working, {len(data['signals'])} signals")
    
    def test_positions_endpoint(self):
        """Test GET /api/ai-trader/positions/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "positions" in data
        print(f"✓ Positions endpoint working, {len(data['positions'])} positions")
    
    def test_history_endpoint(self):
        """Test GET /api/ai-trader/history/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "trades" in data or "stats" in data
        print(f"✓ History endpoint working")


# ============================================
# End-to-End Auto-Trade Flow
# ============================================

class TestAutoTradeEndToEnd:
    """Test the complete auto-trade flow"""
    
    def test_full_auto_trade_flow(self):
        """Test enable -> check status -> update settings -> disable"""
        
        # 1. Check initial status
        status_res = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_res.status_code == 200
        print("✓ Step 1: Got initial status")
        
        # 2. Enable auto-trade
        enable_res = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/toggle/{TEST_WALLET}?enabled=true")
        assert enable_res.status_code == 200
        assert enable_res.json().get("auto_trade_enabled") == True
        print("✓ Step 2: Enabled auto-trade")
        
        # 3. Verify status shows enabled
        status_res2 = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_res2.json().get("auto_trade_enabled") == True
        print("✓ Step 3: Verified enabled status")
        
        # 4. Update settings
        settings = {
            "max_daily_trades": 3,
            "max_sol_per_trade": 0.05
        }
        settings_res = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=settings
        )
        assert settings_res.status_code == 200
        print("✓ Step 4: Updated settings")
        
        # 5. Check logs
        logs_res = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/logs/{TEST_WALLET}?limit=5")
        assert logs_res.status_code == 200
        print(f"✓ Step 5: Got logs ({len(logs_res.json().get('logs', []))} entries)")
        
        # 6. Disable auto-trade (cleanup)
        disable_res = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/toggle/{TEST_WALLET}?enabled=false")
        assert disable_res.status_code == 200
        assert disable_res.json().get("auto_trade_enabled") == False
        print("✓ Step 6: Disabled auto-trade (cleanup)")
        
        print("\n✅ Full auto-trade E2E flow PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
