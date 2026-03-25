"""
Iteration 75: Intelligence Systems Testing
Tests for the 4 new intelligence improvements:
1. Real OHLCV price data collection
2. Smart money whale tracking
3. Social sentiment analysis
4. Jito MEV-protected execution

Also tests existing endpoints for regression.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cosmic-runner-hub.preview.emergentagent.com')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"

# Token mints for testing
JUP_MINT = "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
BONK_MINT = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
WIF_MINT = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"


class TestIntelligenceDashboard:
    """Tests for the new /intelligence-dashboard endpoint"""
    
    def test_intelligence_dashboard_returns_200(self):
        """GET /api/ai-trader/intelligence-dashboard returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Intelligence dashboard returns 200")
    
    def test_intelligence_dashboard_has_price_collector(self):
        """Dashboard has price_collector with tokens_tracked > 0"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        assert "price_collector" in data, "Missing price_collector in response"
        assert data["price_collector"]["status"] == "active", "Price collector not active"
        assert data["price_collector"]["tokens_tracked"] > 0, "No tokens tracked"
        print(f"PASS: Price collector tracking {data['price_collector']['tokens_tracked']} tokens")
    
    def test_intelligence_dashboard_has_smart_money(self):
        """Dashboard has smart_money with wallets_tracked > 0"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        assert "smart_money" in data, "Missing smart_money in response"
        assert data["smart_money"]["status"] == "active", "Smart money not active"
        assert data["smart_money"]["wallets_tracked"] > 0, "No wallets tracked"
        print(f"PASS: Smart money tracking {data['smart_money']['wallets_tracked']} wallets")
    
    def test_intelligence_dashboard_has_sentiment(self):
        """Dashboard has sentiment status"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        assert "sentiment" in data, "Missing sentiment in response"
        assert data["sentiment"]["status"] == "active", "Sentiment not active"
        print(f"PASS: Sentiment system active with {data['sentiment']['cached_entries']} cached entries")
    
    def test_intelligence_dashboard_has_jito(self):
        """Dashboard has jito MEV protection status"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        assert "jito" in data, "Missing jito in response"
        assert data["jito"]["status"] == "active", "Jito not active"
        print("PASS: Jito MEV protection active")


class TestTokenIntelligence:
    """Tests for the new /intelligence/{token_mint} endpoint"""
    
    def test_jup_intelligence_returns_200(self):
        """GET /api/ai-trader/intelligence/{JUP_MINT} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: JUP intelligence returns 200")
    
    def test_bonk_intelligence_returns_200(self):
        """GET /api/ai-trader/intelligence/{BONK_MINT} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{BONK_MINT}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: BONK intelligence returns 200")
    
    def test_wif_intelligence_returns_200(self):
        """GET /api/ai-trader/intelligence/{WIF_MINT} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{WIF_MINT}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: WIF intelligence returns 200")
    
    def test_token_intelligence_has_sentiment(self):
        """Token intelligence has sentiment with score, label, factors, confidence_adjustment"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        data = response.json()
        
        assert "sentiment" in data, "Missing sentiment in response"
        sentiment = data["sentiment"]
        
        assert "score" in sentiment, "Missing sentiment.score"
        assert "label" in sentiment, "Missing sentiment.label"
        assert "factors" in sentiment, "Missing sentiment.factors"
        assert "confidence_adjustment" in sentiment, "Missing sentiment.confidence_adjustment"
        
        # Validate types
        assert isinstance(sentiment["score"], (int, float)), "sentiment.score should be numeric"
        assert isinstance(sentiment["label"], str), "sentiment.label should be string"
        assert isinstance(sentiment["factors"], list), "sentiment.factors should be array"
        assert isinstance(sentiment["confidence_adjustment"], (int, float)), "sentiment.confidence_adjustment should be numeric"
        
        print(f"PASS: Token sentiment - score: {sentiment['score']}, label: {sentiment['label']}, factors: {len(sentiment['factors'])}")
    
    def test_token_intelligence_has_smart_money(self):
        """Token intelligence has smart_money with action, whale_count, buy_count, sell_count"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        data = response.json()
        
        assert "smart_money" in data, "Missing smart_money in response"
        sm = data["smart_money"]
        
        assert "action" in sm, "Missing smart_money.action"
        assert "whale_count" in sm, "Missing smart_money.whale_count"
        assert "buy_count" in sm, "Missing smart_money.buy_count"
        assert "sell_count" in sm, "Missing smart_money.sell_count"
        
        # Validate action is one of expected values
        assert sm["action"] in ["buy", "sell", "neutral"], f"Unexpected action: {sm['action']}"
        
        print(f"PASS: Smart money - action: {sm['action']}, whales: {sm['whale_count']}, buys: {sm['buy_count']}, sells: {sm['sell_count']}")
    
    def test_token_intelligence_has_data_quality(self):
        """Token intelligence has data_quality with candles >= 0 and has_real_data boolean"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        data = response.json()
        
        assert "data_quality" in data, "Missing data_quality in response"
        dq = data["data_quality"]
        
        assert "candles" in dq, "Missing data_quality.candles"
        assert "has_real_data" in dq, "Missing data_quality.has_real_data"
        
        assert isinstance(dq["candles"], int), "data_quality.candles should be integer"
        assert dq["candles"] >= 0, "data_quality.candles should be >= 0"
        assert isinstance(dq["has_real_data"], bool), "data_quality.has_real_data should be boolean"
        
        print(f"PASS: Data quality - candles: {dq['candles']}, has_real_data: {dq['has_real_data']}")


class TestExistingEndpointsRegression:
    """Regression tests for existing endpoints to ensure no breakage"""
    
    def test_settings_endpoint(self):
        """GET /api/ai-trader/settings/{wallet} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Settings endpoint returns 200")
    
    def test_positions_endpoint(self):
        """GET /api/ai-trader/positions/{wallet} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "positions" in data, "Missing positions in response"
        print(f"PASS: Positions endpoint returns 200 with {len(data['positions'])} positions")
    
    def test_signals_endpoint(self):
        """GET /api/ai-trader/signals/{wallet} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/signals/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "signals" in data, "Missing signals in response"
        print(f"PASS: Signals endpoint returns 200 with {len(data['signals'])} signals")
    
    def test_platform_stats_endpoint(self):
        """GET /api/ai-trader/platform-stats returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_trades" in data, "Missing total_trades in response"
        print(f"PASS: Platform stats - {data['total_trades']} total trades, {data.get('win_rate', 0)}% win rate")
    
    def test_competitions_active_endpoint(self):
        """GET /api/competitions/active returns 200"""
        response = requests.get(f"{BASE_URL}/api/competitions/active")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Competitions active endpoint returns 200")
    
    def test_leaderboard_endpoint(self):
        """GET /api/leaderboard?limit=10 returns 200"""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=10")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Leaderboard endpoint returns 200")
    
    def test_journal_dashboard_endpoint(self):
        """GET /api/journal/dashboard returns 200"""
        response = requests.get(f"{BASE_URL}/api/journal/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Journal dashboard endpoint returns 200")


class TestTokensEndpoint:
    """Tests for tokens endpoint"""
    
    def test_tokens_endpoint(self):
        """GET /api/ai-trader/tokens returns 200 with safer and high_risk tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "safer_tokens" in data, "Missing safer_tokens"
        assert "high_risk_tokens" in data, "Missing high_risk_tokens"
        print(f"PASS: Tokens endpoint - {len(data['safer_tokens'])} safer, {len(data['high_risk_tokens'])} high risk")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
