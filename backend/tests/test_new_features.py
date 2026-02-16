"""
Tests for new Bullpug features:
- Leaderboard (weekly reset)
- Reflections Calculator
- Trading Journal CRUD
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLeaderboard:
    """Leaderboard API tests with 7-day reset"""
    
    def test_get_leaderboard(self):
        """Test GET /api/leaderboard returns scores and reset info"""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data
        assert "week_start" in data
        assert "next_reset" in data
        assert "days_until_reset" in data
        assert isinstance(data["leaderboard"], list)
        assert isinstance(data["days_until_reset"], int)
        print(f"✓ Leaderboard GET: {len(data['leaderboard'])} entries, resets in {data['days_until_reset']} days")
    
    def test_submit_score(self):
        """Test POST /api/leaderboard/submit creates score entry"""
        player_name = f"TEST_Player_{uuid.uuid4().hex[:6]}"
        payload = {
            "player_name": player_name,
            "score": 1500,
            "mooncakes": 25
        }
        response = requests.post(f"{BASE_URL}/api/leaderboard/submit", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "rank" in data
        assert "entry_id" in data
        assert isinstance(data["rank"], int)
        print(f"✓ Score submitted: rank #{data['rank']}, entry_id: {data['entry_id']}")
    
    def test_submit_score_zero_rejected(self):
        """Test that zero/negative scores are rejected"""
        payload = {
            "player_name": "TEST_BadScore",
            "score": 0,
            "mooncakes": 0
        }
        response = requests.post(f"{BASE_URL}/api/leaderboard/submit", json=payload)
        assert response.status_code == 400
        print("✓ Zero score correctly rejected")
    
    def test_score_persistence(self):
        """Test that submitted score appears in leaderboard"""
        player_name = f"TEST_Persist_{uuid.uuid4().hex[:6]}"
        score_val = 9999
        
        # Submit score
        submit_response = requests.post(f"{BASE_URL}/api/leaderboard/submit", json={
            "player_name": player_name,
            "score": score_val,
            "mooncakes": 50
        })
        assert submit_response.status_code == 200
        
        # Verify in leaderboard
        get_response = requests.get(f"{BASE_URL}/api/leaderboard?limit=100")
        assert get_response.status_code == 200
        leaderboard = get_response.json()["leaderboard"]
        
        found = any(e["player_name"] == player_name and e["score"] == score_val for e in leaderboard)
        assert found, f"Score for {player_name} not found in leaderboard"
        print(f"✓ Score persistence verified for {player_name}")


class TestReflectionsCalculator:
    """Reflections Calculator API tests"""
    
    def test_calculate_reflections_basic(self):
        """Test POST /api/reflections/calculate with default params"""
        payload = {
            "token_holdings": 10000000,
            "volume_24h": 89000,
            "reflection_rate": 2.0
        }
        response = requests.post(f"{BASE_URL}/api/reflections/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # Verify all expected fields
        assert "holdings" in data
        assert "holder_share_percent" in data
        assert "volume_24h" in data
        assert "reflection_rate" in data
        assert "daily" in data
        assert "weekly" in data
        assert "monthly" in data
        assert "yearly" in data
        assert "estimated_apy" in data
        assert "price_usd" in data
        
        # Verify projections have usd and tokens
        assert "usd" in data["daily"]
        assert "tokens" in data["daily"]
        assert "usd" in data["yearly"]
        
        print(f"✓ Reflections calculated: APY {data['estimated_apy']}%, daily ${data['daily']['usd']}")
    
    def test_calculate_reflections_different_volumes(self):
        """Test reflections with varying volumes"""
        for vol in [10000, 100000, 500000]:
            payload = {
                "token_holdings": 50000000,
                "volume_24h": vol,
                "reflection_rate": 2.0
            }
            response = requests.post(f"{BASE_URL}/api/reflections/calculate", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["volume_24h"] == vol
            assert data["yearly"]["usd"] > 0
            print(f"✓ Volume ${vol}: yearly ${data['yearly']['usd']:.2f}")
    
    def test_calculate_reflections_different_rates(self):
        """Test reflections with varying reflection rates"""
        for rate in [1.0, 2.0, 3.0, 5.0]:
            payload = {
                "token_holdings": 10000000,
                "volume_24h": 89000,
                "reflection_rate": rate
            }
            response = requests.post(f"{BASE_URL}/api/reflections/calculate", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["reflection_rate"] == rate
            print(f"✓ Rate {rate}%: APY {data['estimated_apy']}%")


class TestTradingJournal:
    """Trading Journal CRUD API tests"""
    
    @pytest.fixture
    def test_trade_id(self):
        """Create a test trade and return its ID"""
        payload = {
            "date_entry": datetime.now().strftime("%Y-%m-%d"),
            "asset": "TEST_BTC",
            "trade_type": "Long",
            "entry_price": 50000,
            "position_size": 0.1,
            "status": "open"
        }
        response = requests.post(f"{BASE_URL}/api/journal/trade", json=payload)
        assert response.status_code == 200
        return response.json()["trade_id"]
    
    def test_get_dashboard_empty(self):
        """Test GET /api/journal/dashboard returns metrics"""
        response = requests.get(f"{BASE_URL}/api/journal/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        # Verify dashboard fields exist
        assert "total_trades" in data
        assert "open_trades" in data
        assert "closed_trades" in data
        assert "total_pnl" in data
        assert "win_rate" in data
        assert "avg_pnl" in data
        print(f"✓ Dashboard: {data['total_trades']} trades, PnL ${data['total_pnl']}, win rate {data['win_rate']}%")
    
    def test_get_trades_list(self):
        """Test GET /api/journal/trades returns trade list"""
        response = requests.get(f"{BASE_URL}/api/journal/trades?limit=50")
        assert response.status_code == 200
        
        data = response.json()
        assert "trades" in data
        assert "count" in data
        assert isinstance(data["trades"], list)
        print(f"✓ Trades list: {data['count']} trades")
    
    def test_create_trade_basic(self):
        """Test POST /api/journal/trade creates a trade"""
        payload = {
            "date_entry": "2026-01-15",
            "asset": "TEST_ETH",
            "trade_type": "Long",
            "entry_price": 3000,
            "position_size": 1.0,
            "leverage": 2,
            "status": "open"
        }
        response = requests.post(f"{BASE_URL}/api/journal/trade", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "trade_id" in data
        assert data["trade_id"].startswith("T")
        print(f"✓ Trade created: {data['trade_id']}")
        return data["trade_id"]
    
    def test_create_trade_with_full_fields(self):
        """Test creating trade with all 30+ fields"""
        payload = {
            "date_entry": "2026-01-15",
            "date_exit": "2026-01-16",
            "asset": "TEST_SOL",
            "trade_type": "Long",
            "leverage": 5.0,
            "entry_price": 150,
            "position_size": 10,
            "exit_price": 160,
            "exit_reason": "Take profit hit",
            "stop_loss": 140,
            "take_profit": 170,
            "fees": 2.5,
            "slippage": 0.5,
            "chart_link": "https://tradingview.com/test",
            "entry_reason": "Breakout above resistance",
            "strategy": "Breakout",
            "market_conditions": "Bullish",
            "expected_rr": 3.0,
            "emotion_entry": "Confident",
            "emotion_exit": "Calm",
            "confidence_level": 8,
            "mindset_notes": "Felt good, followed plan",
            "what_went_well": "Good entry timing",
            "what_went_wrong": "Exited too early",
            "lessons": "Let winners run",
            "trade_grade": "B+",
            "tags": ["breakout", "sol", "test"],
            "external_influences": "Fed announcement",
            "health_notes": "Well rested",
            "status": "closed"
        }
        response = requests.post(f"{BASE_URL}/api/journal/trade", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "trade_id" in data
        assert "pnl" in data
        # P&L should be calculated: (160-150)*10 - 3 = 97
        expected_pnl = (160 - 150) * 10 - 2.5 - 0.5  # 97
        assert data["pnl"] == 97
        print(f"✓ Full trade created with calculated P&L: ${data['pnl']}")
        return data["trade_id"]
    
    def test_get_single_trade(self, test_trade_id):
        """Test GET /api/journal/trade/{trade_id} returns trade details"""
        response = requests.get(f"{BASE_URL}/api/journal/trade/{test_trade_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["trade_id"] == test_trade_id
        assert "asset" in data
        assert "entry_price" in data
        print(f"✓ Trade retrieved: {data['trade_id']}, {data['asset']} @ {data['entry_price']}")
    
    def test_update_trade(self, test_trade_id):
        """Test PUT /api/journal/trade/{trade_id} updates trade"""
        payload = {
            "date_entry": datetime.now().strftime("%Y-%m-%d"),
            "asset": "TEST_BTC",
            "trade_type": "Long",
            "entry_price": 50000,
            "position_size": 0.1,
            "exit_price": 55000,
            "status": "closed"
        }
        response = requests.put(f"{BASE_URL}/api/journal/trade/{test_trade_id}", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "pnl" in data
        # P&L should be (55000-50000)*0.1 = 500
        assert data["pnl"] == 500
        print(f"✓ Trade updated: P&L ${data['pnl']}")
    
    def test_delete_trade(self, test_trade_id):
        """Test DELETE /api/journal/trade/{trade_id} removes trade"""
        response = requests.delete(f"{BASE_URL}/api/journal/trade/{test_trade_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert data["trade_id"] == test_trade_id
        
        # Verify deleted
        get_response = requests.get(f"{BASE_URL}/api/journal/trade/{test_trade_id}")
        assert get_response.status_code == 404
        print(f"✓ Trade deleted and verified: {test_trade_id}")
    
    def test_get_nonexistent_trade(self):
        """Test GET /api/journal/trade with invalid ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/journal/trade/NONEXISTENT123")
        assert response.status_code == 404
        print("✓ Nonexistent trade correctly returns 404")
    
    def test_trades_filter_by_status(self):
        """Test filtering trades by status"""
        for status in ["open", "closed"]:
            response = requests.get(f"{BASE_URL}/api/journal/trades?status={status}")
            assert response.status_code == 200
            data = response.json()
            # All returned trades should have matching status (if any exist)
            for trade in data["trades"]:
                if trade.get("asset", "").startswith("TEST_"):
                    assert trade["status"] == status
            print(f"✓ Filter by status={status}: {data['count']} trades")
    
    def test_dashboard_with_trades(self):
        """Test dashboard shows correct metrics after trades"""
        # Create a winning and losing trade
        win_payload = {
            "date_entry": "2026-01-10",
            "date_exit": "2026-01-11",
            "asset": "TEST_DASH_WIN",
            "trade_type": "Long",
            "entry_price": 100,
            "position_size": 10,
            "exit_price": 120,
            "status": "closed"
        }
        loss_payload = {
            "date_entry": "2026-01-12",
            "date_exit": "2026-01-13",
            "asset": "TEST_DASH_LOSS",
            "trade_type": "Long",
            "entry_price": 100,
            "position_size": 10,
            "exit_price": 80,
            "status": "closed"
        }
        
        requests.post(f"{BASE_URL}/api/journal/trade", json=win_payload)
        requests.post(f"{BASE_URL}/api/journal/trade", json=loss_payload)
        
        # Check dashboard
        response = requests.get(f"{BASE_URL}/api/journal/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_trades"] >= 2
        assert "pnl_by_asset" in data
        print(f"✓ Dashboard metrics: {data['total_trades']} trades, PnL ${data['total_pnl']}")


class TestExistingEndpoints:
    """Verify existing endpoints still work"""
    
    def test_root_api(self):
        """Test API root"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        assert "Bullpug API" in response.json()["message"]
        print("✓ Root API working")
    
    def test_tokenomics(self):
        """Test tokenomics endpoint"""
        response = requests.get(f"{BASE_URL}/api/tokenomics/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_supply" in data
        assert "reflection_rate" in data
        print(f"✓ Tokenomics: supply {data['total_supply']}, reflection {data['reflection_rate']}")
    
    def test_betting_history(self):
        """Test betting history"""
        response = requests.get(f"{BASE_URL}/api/betting/history?limit=5")
        assert response.status_code == 200
        assert "history" in response.json()
        print("✓ Betting history working")
    
    def test_products(self):
        """Test products endpoint"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        assert "products" in response.json()
        print(f"✓ Products: {len(response.json()['products'])} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
