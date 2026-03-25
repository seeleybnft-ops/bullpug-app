"""
Iteration 84: Layout Changes & Test Data Cleanup Tests
- Verify no TEST/RAKETEST positions or history entries exist
- Verify ledger API endpoints work correctly
- Verify all major pages load
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cosmic-runner-hub.preview.emergentagent.com')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_root_accessible(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "Bullpug" in data.get("message", "")
        print(f"✓ API root accessible: {data.get('message')}")


class TestDataCleanup:
    """Verify TEST/RAKETEST data has been cleaned up"""
    
    def test_no_test_positions(self):
        """Verify no TEST/RAKETEST positions exist"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        positions = data.get("positions", [])
        
        test_positions = [p for p in positions if "TEST" in p.get("token_symbol", "").upper() or "RAKETEST" in p.get("token_symbol", "").upper()]
        assert len(test_positions) == 0, f"Found {len(test_positions)} TEST/RAKETEST positions"
        print(f"✓ No TEST/RAKETEST positions found ({len(positions)} total positions)")
    
    def test_no_test_history_entries(self):
        """Verify no TEST/RAKETEST history entries exist"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", [])
        
        test_trades = [t for t in trades if "TEST" in t.get("token_symbol", "").upper() or "RAKETEST" in t.get("token_symbol", "").upper()]
        assert len(test_trades) == 0, f"Found {len(test_trades)} TEST/RAKETEST history entries"
        print(f"✓ No TEST/RAKETEST history entries found ({len(trades)} total trades)")
    
    def test_no_test_ledger_entries(self):
        """Verify no TEST/RAKETEST ledger entries exist"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}?limit=100")
        assert response.status_code == 200
        data = response.json()
        entries = data.get("entries", [])
        
        test_entries = [e for e in entries if "TEST" in str(e.get("description", "")).upper() or "RAKETEST" in str(e.get("description", "")).upper()]
        assert len(test_entries) == 0, f"Found {len(test_entries)} TEST/RAKETEST ledger entries"
        print(f"✓ No TEST/RAKETEST ledger entries found ({len(entries)} total entries)")


class TestLedgerEndpoints:
    """Verify all ledger API endpoints work correctly"""
    
    def test_ledger_balance_endpoint(self):
        """Test GET /api/ledger/balance/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        required_fields = ["available_sol", "locked_in_trades_sol", "total_balance_sol", 
                          "total_deposited_sol", "total_withdrawn_sol", "total_fees_sol", 
                          "realised_pnl_sol"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Ledger balance endpoint works - Total: {data['total_balance_sol']} SOL")
    
    def test_ledger_history_endpoint(self):
        """Test GET /api/ledger/history/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        print(f"✓ Ledger history endpoint works - {len(data['entries'])} entries")
    
    def test_ledger_rake_stats_endpoint(self):
        """Test GET /api/ledger/rake-stats/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ledger/rake-stats/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        required_fields = ["total_rake_sol", "total_gross_profit_sol", "rake_count", "rake_percent"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        assert data["rake_percent"] == 2.5, f"Expected rake_percent=2.5, got {data['rake_percent']}"
        print(f"✓ Rake stats endpoint works - Rake: {data['total_rake_sol']} SOL, Count: {data['rake_count']}")


class TestAITraderEndpoints:
    """Verify AI Trader endpoints work correctly"""
    
    def test_settings_endpoint(self):
        """Test GET /api/ai-trader/settings/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        print("✓ AI Trader settings endpoint works")
    
    def test_positions_endpoint(self):
        """Test GET /api/ai-trader/positions/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        print(f"✓ AI Trader positions endpoint works - {len(data['positions'])} positions")
    
    def test_history_endpoint(self):
        """Test GET /api/ai-trader/history/{wallet}"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        print(f"✓ AI Trader history endpoint works - {len(data['trades'])} trades")
    
    def test_platform_stats_endpoint(self):
        """Test GET /api/ai-trader/platform-stats"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200
        print("✓ Platform stats endpoint works")


class TestPageLoads:
    """Verify all major pages load correctly"""
    
    def test_homepage_loads(self):
        """Test homepage loads"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        print("✓ Homepage loads (200)")
    
    def test_origins_page_loads(self):
        """Test /origins page loads"""
        response = requests.get(f"{BASE_URL}/origins")
        assert response.status_code == 200
        print("✓ Origins page loads (200)")
    
    def test_journal_page_loads(self):
        """Test /journal page loads"""
        response = requests.get(f"{BASE_URL}/journal")
        assert response.status_code == 200
        print("✓ Journal page loads (200)")
    
    def test_ai_trader_page_loads(self):
        """Test /ai-trader page loads"""
        response = requests.get(f"{BASE_URL}/ai-trader")
        assert response.status_code == 200
        print("✓ AI Trader page loads (200)")
    
    def test_pugburn_page_loads(self):
        """Test /pugburn page loads"""
        response = requests.get(f"{BASE_URL}/pugburn")
        assert response.status_code == 200
        print("✓ Pugburn page loads (200)")
    
    def test_game_page_loads(self):
        """Test /game page loads"""
        response = requests.get(f"{BASE_URL}/game")
        assert response.status_code == 200
        print("✓ Game page loads (200)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
