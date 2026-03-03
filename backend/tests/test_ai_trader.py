"""
AI Trader API Endpoints Test Suite
Tests for /api/ai-trader/* endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAITraderEndpoints:
    """AI Trader API endpoint tests"""
    
    def test_get_tokens_endpoint(self):
        """Test /api/ai-trader/tokens returns token lists"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify structure
        assert "safer_tokens" in data, "Missing safer_tokens in response"
        assert "high_risk_tokens" in data, "Missing high_risk_tokens in response"
        assert "position_limits" in data, "Missing position_limits in response"
        
        # Verify safer tokens
        assert len(data["safer_tokens"]) > 0, "No safer tokens returned"
        for token in data["safer_tokens"]:
            assert "symbol" in token
            assert "mint" in token
            assert "risk_category" in token
            assert token["risk_category"] == "safer"
        
        # Verify high risk tokens
        assert len(data["high_risk_tokens"]) > 0, "No high risk tokens returned"
        for token in data["high_risk_tokens"]:
            assert "symbol" in token
            assert "mint" in token
            assert "risk_category" in token
            assert token["risk_category"] == "high_risk"
        
        # Verify position limits
        assert "min_sol" in data["position_limits"]
        assert "max_sol" in data["position_limits"]
        assert data["position_limits"]["min_sol"] == 0.05
        assert data["position_limits"]["max_sol"] == 1.0
        
        print(f"Tokens endpoint returned {len(data['safer_tokens'])} safer tokens and {len(data['high_risk_tokens'])} high risk tokens")
    
    def test_get_disclaimer_endpoint(self):
        """Test /api/ai-trader/disclaimer returns disclaimer"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/disclaimer", timeout=10)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify structure
        assert "title" in data, "Missing title in disclaimer"
        assert "terms" in data, "Missing terms in disclaimer"
        assert "risk_acknowledgment" in data, "Missing risk_acknowledgment"
        assert "min_position" in data, "Missing min_position"
        assert "max_position" in data, "Missing max_position"
        
        # Verify content
        assert data["title"] == "AI Trading Bot Disclaimer"
        assert len(data["terms"]) >= 5, "Should have at least 5 terms"
        assert data["min_position"] == 0.05
        assert data["max_position"] == 1.0
        
        print(f"Disclaimer returned with {len(data['terms'])} terms")
    
    def test_get_settings_default(self):
        """Test /api/ai-trader/settings/{wallet} returns default settings for new wallet"""
        test_wallet = "TestWallet123456789"
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{test_wallet}", timeout=10)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify default settings structure
        assert "wallet_address" in data, "Missing wallet_address"
        assert data["wallet_address"] == test_wallet
        assert "risk_level" in data
        assert "max_position_sol" in data
        assert "stop_loss_percent" in data
        assert "take_profit_percent" in data
        
        # Verify defaults
        assert data["risk_level"] == "safer"
        assert data["max_position_sol"] == 0.5
        assert data["stop_loss_percent"] == 10.0
        assert data["take_profit_percent"] == 20.0
        
        print("Default settings returned correctly for new wallet")
    
    def test_get_pending_signals_empty(self):
        """Test /api/ai-trader/signals/{wallet} returns empty for new wallet"""
        test_wallet = "NewTestWallet987654321"
        response = requests.get(f"{BASE_URL}/api/ai-trader/signals/{test_wallet}", timeout=10)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "signals" in data
        assert "count" in data
        assert isinstance(data["signals"], list)
        
        print(f"Signals endpoint returned {data['count']} signals")
    
    def test_get_positions_empty(self):
        """Test /api/ai-trader/positions/{wallet} returns empty for new wallet"""
        test_wallet = "NewTestWallet987654321"
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{test_wallet}", timeout=10)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "positions" in data
        assert "count" in data
        assert isinstance(data["positions"], list)
        
        print(f"Positions endpoint returned {data['count']} positions")
    
    def test_get_history_empty(self):
        """Test /api/ai-trader/history/{wallet} returns history with stats"""
        test_wallet = "NewTestWallet987654321"
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{test_wallet}", timeout=10)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "trades" in data
        assert "stats" in data
        assert isinstance(data["trades"], list)
        assert isinstance(data["stats"], dict)
        
        # Verify stats structure
        stats = data["stats"]
        assert "total_trades" in stats
        assert "win_rate" in stats
        assert "total_pnl_sol" in stats
        
        print(f"History endpoint returned {len(data['trades'])} trades with stats")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
