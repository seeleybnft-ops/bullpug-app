"""
Iteration 74: Comprehensive Testing of Bullpug Full-Stack Website
Tests all major features: AI Trading Bot, Trading Journal, Cosmic Runner, PugBurn, Forum, etc.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cosmic-runner-hub.preview.emergentagent.com')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"


class TestAPIHealth:
    """Test basic API health and root endpoint"""
    
    def test_api_root(self):
        """GET /api/ - Backend API health check"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Bullpug" in data["message"]
        print(f"✓ API Root: {data['message']}")


class TestLeaderboard:
    """Test Cosmic Runner game leaderboard endpoints"""
    
    def test_get_leaderboard(self):
        """GET /api/leaderboard?limit=10 - Get game leaderboard"""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        print(f"✓ Leaderboard: {len(data['leaderboard'])} entries")
    
    def test_submit_score(self):
        """POST /api/leaderboard/submit - Submit test score"""
        payload = {
            "player_name": "TEST_Guardian",
            "score": 100,
            "moonCheese": 5
        }
        response = requests.post(f"{BASE_URL}/api/leaderboard/submit", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "rank" in data
        print(f"✓ Score submitted: Rank #{data['rank']}")


class TestTradingJournal:
    """Test Trading Journal endpoints"""
    
    def test_get_dashboard(self):
        """GET /api/journal/dashboard - Get journal dashboard stats"""
        response = requests.get(f"{BASE_URL}/api/journal/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_trades" in data
        assert "win_rate" in data
        print(f"✓ Journal Dashboard: {data['total_trades']} trades, {data['win_rate']}% win rate")
    
    def test_get_trades(self):
        """GET /api/journal/trades?limit=10 - Get trades list"""
        response = requests.get(f"{BASE_URL}/api/journal/trades?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert isinstance(data["trades"], list)
        print(f"✓ Journal Trades: {len(data['trades'])} trades returned")
    
    def test_create_trade(self):
        """POST /api/journal/trade - Create a test trade entry"""
        payload = {
            "date_entry": "2026-01-15T10:00:00Z",
            "asset": "TEST_SOL",
            "trade_type": "long",
            "entry_price": 100.0,
            "position_size": 1.0,
            "wallet_address": TEST_WALLET
        }
        response = requests.post(f"{BASE_URL}/api/journal/trade", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "trade_id" in data
        print(f"✓ Trade created: {data['trade_id']}")
        return data["trade_id"]


class TestAITrader:
    """Test AI Trading Bot endpoints"""
    
    def test_get_settings(self):
        """GET /api/ai-trader/settings/{wallet} - Get user trading settings"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "wallet_address" in data
        print(f"✓ AI Trader Settings: enabled={data.get('enabled', False)}")
    
    def test_get_positions(self):
        """GET /api/ai-trader/positions/{wallet} - Get open positions"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert isinstance(data["positions"], list)
        print(f"✓ AI Trader Positions: {len(data['positions'])} open positions")
    
    def test_get_signals(self):
        """GET /api/ai-trader/signals/{wallet} - Get pending signals"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/signals/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        print(f"✓ AI Trader Signals: {len(data['signals'])} pending signals")
    
    def test_get_platform_stats(self):
        """GET /api/ai-trader/platform-stats - Get aggregate trading stats"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_trades" in data
        assert "win_rate" in data
        print(f"✓ Platform Stats: {data['total_trades']} trades, {data['win_rate']}% win rate")
    
    def test_get_tokens(self):
        """GET /api/ai-trader/tokens - Get available tokens for trading"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        data = response.json()
        assert "safer_tokens" in data
        assert "high_risk_tokens" in data
        print(f"✓ Available Tokens: {len(data['safer_tokens'])} safer, {len(data['high_risk_tokens'])} high-risk")
    
    def test_get_runners(self):
        """GET /api/ai-trader/runners - Get runner tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        assert response.status_code == 200
        data = response.json()
        assert "runners" in data or "success" in data
        print(f"✓ Runner Tokens: {data.get('count', len(data.get('runners', [])))} runners found")


class TestCompetitions:
    """Test Trading Competitions endpoints"""
    
    def test_get_active_competitions(self):
        """GET /api/competitions/active - Get active competitions"""
        response = requests.get(f"{BASE_URL}/api/competitions/active")
        assert response.status_code == 200
        data = response.json()
        assert "competitions" in data
        print(f"✓ Active Competitions: {len(data['competitions'])} competitions")


class TestProfile:
    """Test Profile endpoints"""
    
    def test_get_profile(self):
        """GET /api/profile/{wallet} - Get user profile"""
        response = requests.get(f"{BASE_URL}/api/profile/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        # Profile may not exist, but endpoint should return 200
        print(f"✓ Profile endpoint working")


class TestSocialTrading:
    """Test Social Trading endpoints"""
    
    def test_get_leaderboard(self):
        """GET /api/social-trading/leaderboard - Get social trading leaderboard"""
        response = requests.get(f"{BASE_URL}/api/social-trading/leaderboard?period=all&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data or "traders" in data
        print(f"✓ Social Trading Leaderboard working")


class TestForum:
    """Test Forum endpoints"""
    
    def test_get_posts(self):
        """GET /api/forum/posts?limit=10 - Get forum posts"""
        response = requests.get(f"{BASE_URL}/api/forum/posts?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
        print(f"✓ Forum Posts: {len(data['posts'])} posts")


class TestCustodialWallet:
    """Test Custodial Wallet endpoints"""
    
    def test_get_wallet_info(self):
        """GET /api/custodial-wallet/info/{wallet} - Get custodial wallet info"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        # May return 404 if no custodial wallet exists, which is fine
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Custodial Wallet: {data.get('balance_sol', 0)} SOL")
        else:
            print(f"✓ Custodial Wallet endpoint working (no wallet for test user)")


class TestAISuggestions:
    """Test AI Suggestions endpoints"""
    
    def test_get_coin_recommendations(self):
        """GET /api/ai-suggestions/coin-recommendations - Get AI coin picks"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        data = response.json()
        assert "safe_picks" in data or "volatile_picks" in data
        safe_count = len(data.get("safe_picks", []))
        volatile_count = len(data.get("volatile_picks", []))
        print(f"✓ AI Suggestions: {safe_count} safe picks, {volatile_count} volatile picks")


class TestRunnerAlerts:
    """Test Runner Alerts endpoints"""
    
    def test_get_status(self):
        """GET /api/runner-alerts/status - Get runner alerts status"""
        response = requests.get(f"{BASE_URL}/api/runner-alerts/status")
        assert response.status_code == 200
        data = response.json()
        assert "active" in data
        print(f"✓ Runner Alerts: active={data.get('active', False)}")
    
    def test_get_preferences(self):
        """GET /api/runner-alerts/preferences/{wallet} - Get user alert preferences"""
        response = requests.get(f"{BASE_URL}/api/runner-alerts/preferences/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Runner Alert Preferences: enabled={data.get('enabled', False)}")


class TestAutoTrade:
    """Test Auto-Trade specific endpoints"""
    
    def test_get_auto_trade_status(self):
        """GET /api/ai-trader/auto-trade/status/{wallet} - Get auto-trade status"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "auto_trade_enabled" in data or "settings" in data
        print(f"✓ Auto-Trade Status: enabled={data.get('auto_trade_enabled', False)}")
    
    def test_check_exits(self):
        """POST /api/ai-trader/auto-trade/check-exits/{wallet} - Check for TP/SL triggers"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Auto-Trade Exit Check: {data.get('positions_checked', 0)} positions checked")


class TestTokenomics:
    """Test Tokenomics endpoints"""
    
    def test_get_stats(self):
        """GET /api/tokenomics/stats - Get token stats"""
        response = requests.get(f"{BASE_URL}/api/tokenomics/stats")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Tokenomics Stats: {data.get('holders', 'N/A')} holders")


class TestPrizePool:
    """Test Prize Pool endpoints"""
    
    def test_get_prize_pool(self):
        """GET /api/prize-pool - Get current prize pool"""
        response = requests.get(f"{BASE_URL}/api/prize-pool")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Prize Pool: {data.get('total_sol', 0)} SOL")


class TestNewsletter:
    """Test Newsletter endpoints"""
    
    def test_subscribe(self):
        """POST /api/newsletter/subscribe - Subscribe to newsletter"""
        payload = {"email": "test_iteration74@bullpug.test"}
        response = requests.post(f"{BASE_URL}/api/newsletter/subscribe", json=payload)
        # May return 200 or 400 if already subscribed
        assert response.status_code in [200, 400]
        print(f"✓ Newsletter subscription endpoint working")


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
