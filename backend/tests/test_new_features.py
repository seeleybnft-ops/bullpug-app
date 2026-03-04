"""
Test new features:
1. AI Trading Bot Tokens tab with Top Picks 
2. New pairs endpoint for potential runners
3. Journal trades stats endpoint for Insights
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAITraderTopPicks:
    """Tests for AI Trading Bot Top Picks features"""
    
    def test_tokens_endpoint_returns_safer_picks(self):
        """Test that /api/ai-trader/tokens returns safer tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        data = response.json()
        
        # Check safer_tokens exist
        assert "safer_tokens" in data
        assert isinstance(data["safer_tokens"], list)
        assert len(data["safer_tokens"]) > 0
        
        # Check structure of safer tokens
        for token in data["safer_tokens"]:
            assert "symbol" in token
            assert "mint" in token
            assert "price_usd" in token
            assert "risk_category" in token
            assert token["risk_category"] == "safer"
    
    def test_tokens_endpoint_returns_high_risk_picks(self):
        """Test that /api/ai-trader/tokens returns high risk tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        data = response.json()
        
        # Check high_risk_tokens exist
        assert "high_risk_tokens" in data
        assert isinstance(data["high_risk_tokens"], list)
        assert len(data["high_risk_tokens"]) > 0
        
        # Check structure of high risk tokens
        for token in data["high_risk_tokens"]:
            assert "symbol" in token
            assert "mint" in token
            assert "risk_category" in token
            assert token["risk_category"] == "high_risk"
    
    def test_tokens_endpoint_returns_position_limits(self):
        """Test that /api/ai-trader/tokens returns position limits"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        data = response.json()
        
        assert "position_limits" in data
        assert "min_sol" in data["position_limits"]
        assert "max_sol" in data["position_limits"]
        assert data["position_limits"]["min_sol"] == 0.05
        assert data["position_limits"]["max_sol"] == 1.0


class TestNewPairsEndpoint:
    """Tests for new pairs (potential runners) endpoint"""
    
    def test_new_pairs_endpoint_exists(self):
        """Test that /api/ai-trader/new-pairs endpoint exists and returns data"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "pairs" in data
        assert "count" in data
        assert "disclaimer" in data
        assert "generated_at" in data
        
        # Check disclaimer content
        assert "EXTREMELY HIGH RISK" in data["disclaimer"]
    
    def test_new_pairs_returns_list(self):
        """Test that pairs is always a list"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["pairs"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["pairs"])
    
    def test_new_pairs_pair_structure(self):
        """Test structure of returned pairs (if any)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/new-pairs")
        assert response.status_code == 200
        data = response.json()
        
        # If pairs exist, check their structure
        for pair in data["pairs"]:
            assert "symbol" in pair
            assert "price" in pair
            assert "platform" in pair
            assert "contract_address" in pair
            assert "dex_url" in pair
            assert "risk_level" in pair


class TestJournalTradeStats:
    """Tests for Journal trade statistics endpoint (for Insights)"""
    
    def test_trade_stats_endpoint_exists(self):
        """Test that /api/journal/trades/{wallet}/stats endpoint exists"""
        test_wallet = "test-wallet-12345"
        response = requests.get(f"{BASE_URL}/api/journal/trades/{test_wallet}/stats")
        assert response.status_code == 200
    
    def test_trade_stats_returns_correct_structure(self):
        """Test that trade stats returns correct data structure"""
        test_wallet = "test-wallet-empty"
        response = requests.get(f"{BASE_URL}/api/journal/trades/{test_wallet}/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_trades" in data
        assert "win_rate" in data
        assert "total_pnl" in data
        assert "best_trade" in data
        assert "worst_trade" in data
        assert "avg_pnl" in data
        assert "wins" in data
        assert "losses" in data
        assert "top_assets" in data
    
    def test_trade_stats_empty_wallet_defaults(self):
        """Test that empty wallet returns default values"""
        test_wallet = "nonexistent-wallet-abc123"
        response = requests.get(f"{BASE_URL}/api/journal/trades/{test_wallet}/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Empty wallet should have 0 trades
        assert data["total_trades"] == 0
        assert data["win_rate"] == 0
        assert data["total_pnl"] == 0
        assert data["best_trade"] is None
        assert data["worst_trade"] is None
        assert data["wins"] == 0
        assert data["losses"] == 0
        assert data["top_assets"] == []


class TestCoinRecommendationsEndpoint:
    """Tests for coin recommendations (used by Top Picks)"""
    
    def test_coin_recommendations_endpoint_exists(self):
        """Test that /api/ai-suggestions/coin-recommendations endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
    
    def test_coin_recommendations_returns_safe_picks(self):
        """Test that recommendations returns safe picks"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        data = response.json()
        
        assert "safe_picks" in data
        assert isinstance(data["safe_picks"], list)
    
    def test_coin_recommendations_returns_volatile_picks(self):
        """Test that recommendations returns volatile picks"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        data = response.json()
        
        assert "volatile_picks" in data
        assert isinstance(data["volatile_picks"], list)


class TestAnalyzeEndpoint:
    """Tests for analyze endpoint (for Analyze button on Top Picks)"""
    
    def test_analyze_endpoint_exists(self):
        """Test that /api/ai-trader/analyze/{token} endpoint exists"""
        test_wallet = "test-wallet-analyze"
        response = requests.post(f"{BASE_URL}/api/ai-trader/analyze/SOL?wallet_address={test_wallet}")
        # Can be 200 (signal found) or 200 (no signal)
        assert response.status_code == 200
    
    def test_analyze_returns_signal_or_message(self):
        """Test that analyze returns either a signal or a message"""
        test_wallet = "test-wallet-analyze-2"
        response = requests.post(f"{BASE_URL}/api/ai-trader/analyze/BONK?wallet_address={test_wallet}")
        assert response.status_code == 200
        data = response.json()
        
        # Should have either signal or message
        assert "signal" in data or "message" in data
    
    def test_analyze_invalid_token_returns_error(self):
        """Test that invalid token returns 400"""
        test_wallet = "test-wallet-invalid"
        response = requests.post(f"{BASE_URL}/api/ai-trader/analyze/INVALID_TOKEN?wallet_address={test_wallet}")
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
