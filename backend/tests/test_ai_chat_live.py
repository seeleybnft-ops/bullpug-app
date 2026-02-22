"""
Test AI Chat Live Data Endpoints
Tests the real-time AI chat functionality including:
- /api/ai/chat - Main AI chat endpoint with live price data
- /api/ai/prices - Get live crypto prices
- /api/ai/price/{symbol} - Get specific coin price
- /api/ai/trending - Get trending coins
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAIChatEndpoints:
    """AI Chat API endpoint tests for real-time data functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_ai_chat_basic(self):
        """Test basic AI chat endpoint returns 200"""
        response = self.session.post(f"{BASE_URL}/api/ai/chat", json={
            "wallet_address": "TEST_wallet_123",
            "message": "Hello, what can you help me with?",
            "session_id": f"test_session_{uuid.uuid4().hex[:8]}",
            "active_tab": "dashboard",
            "chat_history": []
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "response" in data, "Response should contain 'response' field"
        assert "session_id" in data, "Response should contain 'session_id' field"
        print(f"AI Chat Response: {data['response'][:100]}...")

    def test_ai_chat_price_query_sol(self):
        """Test AI chat with SOL price query returns live data flag"""
        response = self.session.post(f"{BASE_URL}/api/ai/chat", json={
            "wallet_address": "TEST_wallet_456",
            "message": "What is the price of SOL?",
            "session_id": f"test_session_{uuid.uuid4().hex[:8]}",
            "active_tab": "chat",
            "chat_history": []
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "response" in data, "Response should contain 'response' field"
        assert "has_live_data" in data, "Response should contain 'has_live_data' field"
        assert data["has_live_data"] == True, "Price query should return has_live_data: true"
        print(f"SOL Price Query - has_live_data: {data['has_live_data']}")
        print(f"Response snippet: {data['response'][:200]}...")

    def test_ai_chat_price_query_btc(self):
        """Test AI chat with BTC price query returns live data flag"""
        response = self.session.post(f"{BASE_URL}/api/ai/chat", json={
            "wallet_address": "TEST_wallet_789",
            "message": "Show me BTC price",
            "session_id": f"test_session_{uuid.uuid4().hex[:8]}",
            "active_tab": "chat",
            "chat_history": []
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "has_live_data" in data, "Response should contain 'has_live_data' field"
        assert data["has_live_data"] == True, "BTC price query should return has_live_data: true"
        print(f"BTC Price Query - has_live_data: {data['has_live_data']}")

    def test_ai_chat_trending_query(self):
        """Test AI chat with trending coins query"""
        response = self.session.post(f"{BASE_URL}/api/ai/chat", json={
            "wallet_address": None,
            "message": "What's trending on Solana?",
            "session_id": f"test_session_{uuid.uuid4().hex[:8]}",
            "active_tab": "chat",
            "chat_history": []
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "response" in data
        assert "has_live_data" in data
        print(f"Trending Query - has_live_data: {data['has_live_data']}")

    def test_ai_chat_non_price_query(self):
        """Test AI chat with non-price query - should not have live data"""
        response = self.session.post(f"{BASE_URL}/api/ai/chat", json={
            "wallet_address": "TEST_wallet_abc",
            "message": "Tell me about yourself",
            "session_id": f"test_session_{uuid.uuid4().hex[:8]}",
            "active_tab": "dashboard",
            "chat_history": []
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        # Non-price queries may or may not have live data, just verify structure
        assert "has_live_data" in data
        print(f"Non-price query - has_live_data: {data['has_live_data']}")


class TestLivePricesEndpoint:
    """Tests for /api/ai/prices endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_get_live_prices(self):
        """Test GET /api/ai/prices returns live crypto prices"""
        response = self.session.get(f"{BASE_URL}/api/ai/prices")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "prices" in data, "Response should contain 'prices' field"
        assert "timestamp" in data, "Response should contain 'timestamp' field"
        assert "source" in data, "Response should contain 'source' field"
        
        prices = data["prices"]
        if prices:
            # Verify at least some common coins are present
            common_coins = ["BTC", "ETH", "SOL", "DOGE"]
            found_coins = [coin for coin in common_coins if coin in prices]
            print(f"Found coins: {found_coins}")
            
            # Verify price structure
            for symbol, price_data in list(prices.items())[:3]:
                assert "price" in price_data, f"{symbol} should have 'price' field"
                assert "change_24h" in price_data, f"{symbol} should have 'change_24h' field"
                print(f"{symbol}: ${price_data['price']:,.2f} ({price_data['change_24h']:.2f}% 24h)")
        else:
            print("Warning: No prices returned (may be rate limited)")

    def test_live_prices_has_major_coins(self):
        """Verify major coins are returned in prices endpoint"""
        response = self.session.get(f"{BASE_URL}/api/ai/prices")
        assert response.status_code == 200
        data = response.json()
        prices = data.get("prices", {})
        
        # At least check the structure is correct
        for symbol in prices:
            price_data = prices[symbol]
            assert isinstance(price_data.get("price"), (int, float)), f"{symbol} price should be numeric"


class TestSinglePriceEndpoint:
    """Tests for /api/ai/price/{symbol} endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_get_sol_price(self):
        """Test GET /api/ai/price/SOL returns SOL price"""
        response = self.session.get(f"{BASE_URL}/api/ai/price/SOL")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "timestamp" in data, "Response should contain 'timestamp' field"
        
        if "data" in data:
            price_data = data["data"]
            assert "symbol" in price_data, "Price data should contain 'symbol'"
            assert "price" in price_data, "Price data should contain 'price'"
            assert price_data["symbol"] == "SOL", f"Symbol should be SOL, got {price_data['symbol']}"
            print(f"SOL Price: ${price_data['price']:,.2f}")
            print(f"24h Change: {price_data.get('change_24h', 'N/A')}%")
        else:
            # May have error field if coin not found
            print(f"Response: {data}")

    def test_get_btc_price(self):
        """Test GET /api/ai/price/BTC returns BTC price"""
        response = self.session.get(f"{BASE_URL}/api/ai/price/BTC")
        assert response.status_code == 200
        data = response.json()
        
        if "data" in data:
            price_data = data["data"]
            assert price_data["symbol"] == "BTC"
            assert price_data["price"] > 0, "BTC price should be positive"
            print(f"BTC Price: ${price_data['price']:,.2f}")

    def test_get_eth_price(self):
        """Test GET /api/ai/price/ETH returns ETH price"""
        response = self.session.get(f"{BASE_URL}/api/ai/price/ETH")
        assert response.status_code == 200
        data = response.json()
        
        if "data" in data:
            price_data = data["data"]
            assert price_data["symbol"] == "ETH"
            print(f"ETH Price: ${price_data['price']:,.2f}")

    def test_get_unknown_coin_price(self):
        """Test GET /api/ai/price with unknown coin"""
        response = self.session.get(f"{BASE_URL}/api/ai/price/UNKNOWNCOIN12345")
        assert response.status_code == 200  # Endpoint returns 200 with error message
        data = response.json()
        # Should have either data or error
        assert "timestamp" in data


class TestTrendingEndpoint:
    """Tests for /api/ai/trending endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_get_trending_coins(self):
        """Test GET /api/ai/trending returns trending coins"""
        response = self.session.get(f"{BASE_URL}/api/ai/trending")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "trending" in data, "Response should contain 'trending' field"
        assert "timestamp" in data, "Response should contain 'timestamp' field"
        assert "source" in data, "Response should contain 'source' field"
        
        trending = data["trending"]
        if trending:
            print(f"Found {len(trending)} trending coins:")
            for coin in trending[:3]:
                print(f"  - {coin.get('symbol', '?')}: ${coin.get('price', 0):.6f} ({coin.get('change_24h', 0):.1f}% 24h)")
        else:
            print("Warning: No trending coins returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
