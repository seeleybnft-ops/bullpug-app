"""
Test Market Dashboard API endpoints for P1 UX enhancements
Tests /api/ai/market, /api/ai/sentiment, and /api/ai/news endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMarketDashboardAPIs:
    """Tests for Market Dashboard widget API endpoints"""
    
    def test_market_endpoint_returns_200(self):
        """Test /api/ai/market endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai/market", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ /api/ai/market returned 200")
    
    def test_market_endpoint_has_sentiment(self):
        """Test /api/ai/market contains sentiment (Fear & Greed) data"""
        response = requests.get(f"{BASE_URL}/api/ai/market", timeout=30)
        data = response.json()
        
        assert "sentiment" in data, "Response missing 'sentiment' field"
        sentiment = data["sentiment"]
        
        assert "value" in sentiment, "Sentiment missing 'value' field"
        assert "classification" in sentiment, "Sentiment missing 'classification' field"
        
        # Value should be between 0-100
        assert 0 <= sentiment["value"] <= 100, f"Sentiment value {sentiment['value']} out of range"
        
        # Classification should be a valid sentiment string
        valid_classifications = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
        assert sentiment["classification"] in valid_classifications, f"Invalid classification: {sentiment['classification']}"
        
        print(f"✅ Market sentiment: {sentiment['value']}/100 - {sentiment['classification']}")
    
    def test_market_endpoint_has_solana_ecosystem(self):
        """Test /api/ai/market contains Solana ecosystem data"""
        response = requests.get(f"{BASE_URL}/api/ai/market", timeout=30)
        data = response.json()
        
        assert "solana_ecosystem" in data, "Response missing 'solana_ecosystem' field"
        solana_data = data["solana_ecosystem"]
        
        # Should have top_gainers and top_volume arrays
        assert "top_gainers" in solana_data, "Missing top_gainers"
        assert "top_volume" in solana_data, "Missing top_volume"
        
        assert isinstance(solana_data["top_gainers"], list), "top_gainers should be a list"
        assert isinstance(solana_data["top_volume"], list), "top_volume should be a list"
        
        print(f"✅ Solana ecosystem: {len(solana_data['top_gainers'])} gainers, {len(solana_data['top_volume'])} volume leaders")
    
    def test_market_endpoint_has_global_data(self):
        """Test /api/ai/market contains global market data"""
        response = requests.get(f"{BASE_URL}/api/ai/market", timeout=30)
        data = response.json()
        
        assert "global" in data, "Response missing 'global' field"
        global_data = data["global"]
        
        # Should have key market metrics
        expected_fields = ["total_market_cap", "total_volume", "btc_dominance"]
        for field in expected_fields:
            assert field in global_data, f"Missing {field}"
        
        # Market cap should be a reasonable number (> 100 billion)
        if not global_data.get("error"):
            assert global_data["total_market_cap"] > 100_000_000_000, "Market cap seems too low"
            print(f"✅ Global market cap: ${global_data['total_market_cap']/1e12:.2f}T")
    
    def test_market_endpoint_has_timestamp(self):
        """Test /api/ai/market includes timestamp"""
        response = requests.get(f"{BASE_URL}/api/ai/market", timeout=30)
        data = response.json()
        
        assert "timestamp" in data, "Response missing 'timestamp' field"
        assert isinstance(data["timestamp"], str), "Timestamp should be a string"
        print(f"✅ Timestamp: {data['timestamp']}")


class TestSentimentEndpoint:
    """Tests for /api/ai/sentiment endpoint"""
    
    def test_sentiment_endpoint_returns_200(self):
        """Test /api/ai/sentiment returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai/sentiment", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ /api/ai/sentiment returned 200")
    
    def test_sentiment_has_fear_greed(self):
        """Test /api/ai/sentiment contains Fear & Greed Index"""
        response = requests.get(f"{BASE_URL}/api/ai/sentiment", timeout=30)
        data = response.json()
        
        assert "fear_greed" in data, "Response missing 'fear_greed' field"
        fng = data["fear_greed"]
        
        assert "value" in fng, "Missing 'value' field"
        assert "classification" in fng, "Missing 'classification' field"
        
        # Value should be 0-100
        assert 0 <= fng["value"] <= 100, f"Value {fng['value']} out of range"
        
        print(f"✅ Fear & Greed Index: {fng['value']}/100 - {fng['classification']}")
    
    def test_sentiment_has_timestamp(self):
        """Test /api/ai/sentiment includes timestamp"""
        response = requests.get(f"{BASE_URL}/api/ai/sentiment", timeout=30)
        data = response.json()
        
        assert "timestamp" in data, "Response missing 'timestamp'"
        print(f"✅ Timestamp present")


class TestNewsEndpoint:
    """Tests for /api/ai/news endpoint"""
    
    def test_news_endpoint_returns_200(self):
        """Test /api/ai/news returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai/news", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ /api/ai/news returned 200")
    
    def test_news_has_news_array(self):
        """Test /api/ai/news contains news array"""
        response = requests.get(f"{BASE_URL}/api/ai/news", timeout=30)
        data = response.json()
        
        assert "news" in data, "Response missing 'news' field"
        assert isinstance(data["news"], list), "news should be a list"
        
        print(f"✅ News items: {len(data['news'])}")
        
        # If news items exist, verify structure
        if data["news"]:
            news_item = data["news"][0]
            assert "title" in news_item, "News item missing 'title'"
            print(f"   First item: {news_item['title'][:50]}...")
    
    def test_news_has_timestamp(self):
        """Test /api/ai/news includes timestamp"""
        response = requests.get(f"{BASE_URL}/api/ai/news", timeout=30)
        data = response.json()
        
        assert "timestamp" in data, "Response missing 'timestamp'"
        print("✅ Timestamp present")


class TestLivePricesEndpoint:
    """Tests for /api/ai/prices endpoint"""
    
    def test_prices_endpoint_returns_200(self):
        """Test /api/ai/prices returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai/prices", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ /api/ai/prices returned 200")
    
    def test_prices_has_prices_object(self):
        """Test /api/ai/prices contains prices data"""
        response = requests.get(f"{BASE_URL}/api/ai/prices", timeout=30)
        data = response.json()
        
        assert "prices" in data, "Response missing 'prices' field"
        prices = data["prices"]
        
        # Should have some major crypto prices
        if prices:
            expected_cryptos = ["BTC", "ETH", "SOL"]
            found = [c for c in expected_cryptos if c in prices]
            print(f"✅ Found prices for: {', '.join(found)}")
            
            # Verify price structure
            for symbol, price_data in list(prices.items())[:1]:
                assert "price" in price_data, f"{symbol} missing 'price'"
                assert "change_24h" in price_data, f"{symbol} missing 'change_24h'"
                print(f"   {symbol}: ${price_data['price']:,.2f} ({price_data['change_24h']:.1f}%)")


class TestTrendingEndpoint:
    """Tests for /api/ai/trending endpoint"""
    
    def test_trending_endpoint_returns_200(self):
        """Test /api/ai/trending returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai/trending", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ /api/ai/trending returned 200")
    
    def test_trending_has_trending_array(self):
        """Test /api/ai/trending contains trending coins"""
        response = requests.get(f"{BASE_URL}/api/ai/trending", timeout=30)
        data = response.json()
        
        assert "trending" in data, "Response missing 'trending' field"
        assert isinstance(data["trending"], list), "trending should be a list"
        
        print(f"✅ Trending coins: {len(data['trending'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
