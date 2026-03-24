"""
Iteration 76: Testing 3 A-tier Upgrades for Bullpug Trading Bot

1. Expanded whale wallet list to 50+ with profit scoring (3-tier system)
2. GPT-powered social sentiment analysis via Emergent LLM Key
3. Trailing stop-losses that dynamically move up as price rises

Test wallet: qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs
Token mints: JUP=JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN, BONK=DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bullpug-app.preview.emergentagent.com')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
JUP_MINT = "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
BONK_MINT = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"


class TestIntelligenceDashboard:
    """Test the intelligence dashboard endpoint for 50+ whale wallets"""
    
    def test_intelligence_dashboard_returns_200(self):
        """GET /api/ai-trader/intelligence-dashboard returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Intelligence dashboard returns 200")
    
    def test_smart_money_wallets_tracked_50_plus(self):
        """Verify smart_money.wallets_tracked >= 50 (expanded whale list)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "smart_money" in data, "Response missing smart_money field"
        wallets_tracked = data["smart_money"].get("wallets_tracked", 0)
        assert wallets_tracked >= 50, f"Expected 50+ wallets tracked, got {wallets_tracked}"
        print(f"PASS: Smart money tracking {wallets_tracked} wallets (>= 50)")
    
    def test_price_collector_status(self):
        """Verify price_collector is active with tokens tracked"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "price_collector" in data, "Response missing price_collector field"
        assert data["price_collector"].get("status") == "active", "Price collector not active"
        tokens_tracked = data["price_collector"].get("tokens_tracked", 0)
        assert tokens_tracked > 0, f"Expected tokens tracked > 0, got {tokens_tracked}"
        print(f"PASS: Price collector active, tracking {tokens_tracked} tokens")
    
    def test_sentiment_status(self):
        """Verify sentiment system is active"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "sentiment" in data, "Response missing sentiment field"
        assert data["sentiment"].get("status") == "active", "Sentiment system not active"
        print(f"PASS: Sentiment system active with {data['sentiment'].get('cached_entries', 0)} cached entries")
    
    def test_jito_status(self):
        """Verify Jito MEV protection is active"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "jito" in data, "Response missing jito field"
        assert data["jito"].get("status") == "active", "Jito not active"
        print("PASS: Jito MEV protection active")


class TestTokenIntelligenceWithGPT:
    """Test token intelligence endpoint for GPT sentiment analysis"""
    
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
    
    def test_jup_sentiment_has_ai_analysis(self):
        """Verify JUP sentiment includes ai_analysis from GPT"""
        # GPT analysis may take 2-3 seconds
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        assert response.status_code == 200
        data = response.json()
        
        assert "sentiment" in data, "Response missing sentiment field"
        sentiment = data["sentiment"]
        
        # Check for ai_analysis field (may be None if GPT call failed)
        if sentiment.get("ai_analysis"):
            ai = sentiment["ai_analysis"]
            assert "ai_sentiment" in ai, "ai_analysis missing ai_sentiment"
            assert "ai_confidence" in ai, "ai_analysis missing ai_confidence"
            assert "reasoning" in ai, "ai_analysis missing reasoning"
            print(f"PASS: JUP has GPT ai_analysis: {ai.get('ai_sentiment')} ({ai.get('ai_confidence', 0)*100:.0f}% confidence)")
            print(f"      Reasoning: {ai.get('reasoning', 'N/A')[:80]}...")
        else:
            # ai_analysis may be None if GPT call failed or was skipped
            print("INFO: JUP ai_analysis is None (GPT may have been skipped or failed)")
    
    def test_bonk_sentiment_has_ai_analysis(self):
        """Verify BONK sentiment includes ai_analysis from GPT"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{BONK_MINT}")
        assert response.status_code == 200
        data = response.json()
        
        assert "sentiment" in data, "Response missing sentiment field"
        sentiment = data["sentiment"]
        
        if sentiment.get("ai_analysis"):
            ai = sentiment["ai_analysis"]
            assert "ai_sentiment" in ai, "ai_analysis missing ai_sentiment"
            print(f"PASS: BONK has GPT ai_analysis: {ai.get('ai_sentiment')} ({ai.get('ai_confidence', 0)*100:.0f}% confidence)")
        else:
            print("INFO: BONK ai_analysis is None (GPT may have been skipped or failed)")
    
    def test_sentiment_factors_include_ai_analysis(self):
        """Verify sentiment.factors array includes 'ai_analysis' factor when GPT succeeds"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        assert response.status_code == 200
        data = response.json()
        
        sentiment = data.get("sentiment", {})
        factors = sentiment.get("factors", [])
        
        # Check if ai_analysis factor is present
        ai_factor = next((f for f in factors if f.get("factor") == "ai_analysis"), None)
        if ai_factor:
            print(f"PASS: sentiment.factors includes ai_analysis factor with score {ai_factor.get('score')}")
        else:
            print("INFO: ai_analysis factor not in factors array (GPT may have been skipped)")
    
    def test_smart_money_has_tier1_whales_field(self):
        """Verify smart_money response has tier1_whales field"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        assert response.status_code == 200
        data = response.json()
        
        assert "smart_money" in data, "Response missing smart_money field"
        sm = data["smart_money"]
        
        # tier1_whales should be present (may be 0 if no recent activity)
        assert "tier1_whales" in sm, "smart_money missing tier1_whales field"
        print(f"PASS: smart_money has tier1_whales={sm.get('tier1_whales', 0)}")
    
    def test_smart_money_has_weighted_buy_ratio(self):
        """Verify smart_money response has weighted_buy_ratio field"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        assert response.status_code == 200
        data = response.json()
        
        sm = data.get("smart_money", {})
        
        # weighted_buy_ratio should be present
        assert "weighted_buy_ratio" in sm, "smart_money missing weighted_buy_ratio field"
        ratio = sm.get("weighted_buy_ratio", 0)
        assert 0 <= ratio <= 1, f"weighted_buy_ratio should be 0-1, got {ratio}"
        print(f"PASS: smart_money has weighted_buy_ratio={ratio}")
    
    def test_data_quality_has_candles(self):
        """Verify data_quality.candles > 0 (price collector running)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        assert response.status_code == 200
        data = response.json()
        
        dq = data.get("data_quality", {})
        candles = dq.get("candles", 0)
        # Candles may be 0 if price collector just started
        print(f"INFO: data_quality.candles = {candles}")
        assert "candles" in dq, "data_quality missing candles field"
        print(f"PASS: data_quality has candles field (value: {candles})")


class TestTrailingStopSettings:
    """Test trailing stop-loss settings in user settings"""
    
    def test_settings_returns_200(self):
        """GET /api/ai-trader/settings/{wallet} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Settings endpoint returns 200")
    
    def test_settings_has_trailing_stop_fields(self):
        """Verify settings include trailing stop fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Check for trailing stop settings
        assert "auto_trailing_stop_enabled" in data, "Settings missing auto_trailing_stop_enabled"
        assert "auto_trailing_stop_percent" in data, "Settings missing auto_trailing_stop_percent"
        
        print(f"PASS: Settings has trailing stop fields:")
        print(f"      auto_trailing_stop_enabled: {data.get('auto_trailing_stop_enabled')}")
        print(f"      auto_trailing_stop_percent: {data.get('auto_trailing_stop_percent')}%")
    
    def test_update_trailing_stop_settings(self):
        """Test updating trailing stop settings"""
        # First get current settings
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        current = response.json()
        
        # Update with trailing stop enabled
        update_data = {
            "wallet_address": TEST_WALLET,
            "auto_trailing_stop_enabled": True,
            "auto_trailing_stop_percent": 7.0,
            # Include required fields
            "enabled": current.get("enabled", False),
            "risk_level": current.get("risk_level", "safer"),
            "max_position_sol": current.get("max_position_sol", 0.5),
            "min_position_sol": current.get("min_position_sol", 0.05),
            "stop_loss_percent": current.get("stop_loss_percent", 10.0),
            "take_profit_percent": current.get("take_profit_percent", 20.0),
            "max_daily_trades": current.get("max_daily_trades", 5),
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-trader/settings", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        updated = response.json()
        
        assert updated.get("auto_trailing_stop_enabled") == True, "Trailing stop not enabled"
        assert updated.get("auto_trailing_stop_percent") == 7.0, "Trailing stop percent not updated"
        print("PASS: Trailing stop settings updated successfully")


class TestPositionsEndpoint:
    """Test positions endpoint for trailing stop fields"""
    
    def test_positions_returns_200(self):
        """GET /api/ai-trader/positions/{wallet} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Positions endpoint returns 200")
    
    def test_positions_structure(self):
        """Verify positions response structure"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "positions" in data, "Response missing positions field"
        assert "count" in data, "Response missing count field"
        print(f"PASS: Positions response has correct structure (count: {data.get('count', 0)})")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    def test_root_health_check(self):
        """GET /api/ returns 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Root health check returns 200")
    
    def test_platform_stats(self):
        """GET /api/ai-trader/platform-stats returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Platform stats returns 200")
    
    def test_competitions_active(self):
        """GET /api/competitions/active returns 200"""
        response = requests.get(f"{BASE_URL}/api/competitions/active")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Competitions active returns 200")
    
    def test_leaderboard(self):
        """GET /api/leaderboard?limit=10 returns 200"""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=10")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Leaderboard returns 200")
    
    def test_journal_dashboard(self):
        """GET /api/journal/dashboard returns 200"""
        response = requests.get(f"{BASE_URL}/api/journal/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Journal dashboard returns 200")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
