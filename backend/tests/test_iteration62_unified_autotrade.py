"""
Iteration 62: Test Unified Auto-Trader and Multi-Chain Copy Trading
Tests:
1. UnifiedAutoTrader component endpoints (signal-analytics/performance-summary)
2. Telegram bot-info endpoint
3. Multi-chain copy trading endpoints
4. Tab navigation verification (analytics tab removed)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTelegramBotInfo:
    """Test /api/telegram/bot-info endpoint"""
    
    def test_telegram_bot_info_returns_valid_data(self):
        """GET /api/telegram/bot-info should return bot info"""
        response = requests.get(f"{BASE_URL}/api/telegram/bot-info")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "bot_username" in data
        assert "bot_name" in data
        assert "link" in data
        assert data["bot_username"] == "Bullpugbot"
        print(f"SUCCESS: Telegram bot info - username: {data['bot_username']}, name: {data['bot_name']}")


class TestSignalAnalyticsPerformanceSummary:
    """Test /api/signal-analytics/performance-summary endpoint (used by UnifiedAutoTrader)"""
    
    def test_performance_summary_default(self):
        """GET /api/signal-analytics/performance-summary returns data"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/performance-summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "period_days" in data
        assert "total_signals_analyzed" in data
        assert "strategies" in data
        assert isinstance(data["strategies"], list)
        print(f"SUCCESS: Performance summary - {data['total_signals_analyzed']} signals analyzed, {len(data['strategies'])} strategies")
    
    def test_performance_summary_with_period(self):
        """GET /api/signal-analytics/performance-summary with period_days param"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/performance-summary?period_days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period_days"] == 7
        print(f"SUCCESS: Performance summary with 7-day period works")


class TestSignalAnalyticsOptimalSettings:
    """Test /api/signal-analytics/optimal-settings endpoint (used by UnifiedAutoTrader)"""
    
    def test_optimal_settings(self):
        """GET /api/signal-analytics/optimal-settings returns recommendations"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/optimal-settings")
        assert response.status_code == 200
        
        data = response.json()
        assert "settings" in data
        assert "sufficient_data" in data
        print(f"SUCCESS: Optimal settings endpoint works - sufficient_data: {data['sufficient_data']}")


class TestMultiChainCopyTradingEndpoints:
    """Test Multi-Chain Copy Trading endpoints"""
    
    def test_supported_chains(self):
        """GET /api/multichain-copy/supported-chains returns chain config"""
        response = requests.get(f"{BASE_URL}/api/multichain-copy/supported-chains")
        assert response.status_code == 200
        
        data = response.json()
        assert "chains" in data
        assert "default_chain" in data
        
        chains = data["chains"]
        assert "solana" in chains
        assert "ethereum" in chains
        assert "base" in chains
        assert "arbitrum" in chains
        
        # Verify chain structure
        solana = chains["solana"]
        assert solana["name"] == "Solana"
        assert solana["symbol"] == "SOL"
        print(f"SUCCESS: Supported chains - {list(chains.keys())}")
    
    def test_leaderboard(self):
        """GET /api/multichain-copy/leaderboard returns leaderboard data"""
        response = requests.get(f"{BASE_URL}/api/multichain-copy/leaderboard?period=7d&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data
        assert "period" in data
        assert isinstance(data["leaderboard"], list)
        print(f"SUCCESS: Leaderboard endpoint works - {len(data['leaderboard'])} traders")
    
    def test_leaderboard_with_chain_filter(self):
        """GET /api/multichain-copy/leaderboard with chain filter"""
        response = requests.get(f"{BASE_URL}/api/multichain-copy/leaderboard?period=30d&chain=solana&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data
        print(f"SUCCESS: Leaderboard with chain filter works")
    
    def test_config_endpoint_not_found(self):
        """GET /api/multichain-copy/config should return 404 (endpoint doesn't exist)"""
        response = requests.get(f"{BASE_URL}/api/multichain-copy/config")
        # This endpoint doesn't exist - it's not in the router
        assert response.status_code == 404
        print("INFO: /api/multichain-copy/config returns 404 as expected (endpoint not implemented)")


class TestTelegramCopyTradingNotifications:
    """Test Telegram copy trading notification functions exist in router"""
    
    def test_telegram_router_has_copy_trade_functions(self):
        """Verify telegram.py has copy trading notification functions"""
        # Read the telegram.py file to verify functions exist
        telegram_file = "/app/backend/routers/telegram.py"
        with open(telegram_file, 'r') as f:
            content = f.read()
        
        # Check for copy trading notification functions
        assert "send_copy_trade_alert" in content
        assert "send_new_follower_alert" in content
        assert "send_copy_pnl_update" in content
        assert "send_trader_milestone_alert" in content
        assert "send_followed_trader_update" in content
        assert "send_copy_trade_executed_alert" in content
        assert "send_copy_trade_failed_alert" in content
        print("SUCCESS: All copy trading notification functions found in telegram.py")


class TestSocialTradingTelegramIntegration:
    """Test social_trading.py has Telegram notification integration"""
    
    def test_social_trading_imports_telegram(self):
        """Verify social_trading.py imports telegram notification functions"""
        social_file = "/app/backend/routers/social_trading.py"
        with open(social_file, 'r') as f:
            content = f.read()
        
        # Check for telegram imports in notification functions
        assert "from routers.telegram import send_copy_trade_alert" in content
        assert "from routers.telegram import send_new_follower_alert" in content
        print("SUCCESS: social_trading.py imports Telegram notification functions")


class TestUnifiedAutoTraderComponent:
    """Test UnifiedAutoTrader component file exists and has correct structure"""
    
    def test_unified_auto_trader_file_exists(self):
        """Verify UnifiedAutoTrader.js exists"""
        component_file = "/app/frontend/src/components/UnifiedAutoTrader.js"
        assert os.path.exists(component_file)
        print("SUCCESS: UnifiedAutoTrader.js exists")
    
    def test_unified_auto_trader_has_analytics_metrics(self):
        """Verify UnifiedAutoTrader has analytics summary metrics"""
        component_file = "/app/frontend/src/components/UnifiedAutoTrader.js"
        with open(component_file, 'r') as f:
            content = f.read()
        
        # Check for analytics metrics
        assert "Win Rate" in content
        assert "Avg Confidence" in content
        assert "Recommended Min" in content
        assert "performanceSummary" in content
        assert "optimalSettings" in content
        print("SUCCESS: UnifiedAutoTrader has analytics summary metrics")
    
    def test_unified_auto_trader_fetches_analytics(self):
        """Verify UnifiedAutoTrader fetches analytics data"""
        component_file = "/app/frontend/src/components/UnifiedAutoTrader.js"
        with open(component_file, 'r') as f:
            content = f.read()
        
        # Check for analytics API calls
        assert "/signal-analytics/performance-summary" in content
        assert "/signal-analytics/optimal-settings" in content
        print("SUCCESS: UnifiedAutoTrader fetches analytics data from API")


class TestAITraderTabConfiguration:
    """Test AITrader.js has correct tab configuration"""
    
    def test_ai_trader_tabs_correct(self):
        """Verify AITrader.js has correct tabs (analytics removed, autotrade merged)"""
        ai_trader_file = "/app/frontend/src/pages/AITrader.js"
        with open(ai_trader_file, 'r') as f:
            content = f.read()
        
        # Check for expected tabs
        assert 'id: "signals"' in content
        assert 'id: "tokens"' in content
        assert 'id: "autotrade"' in content
        assert 'id: "social"' in content
        assert 'id: "multichain"' in content
        assert 'id: "alerts"' in content
        assert 'id: "positions"' in content
        assert 'id: "history"' in content
        
        # Check that analytics tab is NOT present as a separate tab
        # The analytics functionality is now merged into autotrade
        assert 'id: "analytics"' not in content or 'description: "& Analytics"' in content
        print("SUCCESS: AITrader.js has correct tab configuration")
    
    def test_ai_trader_uses_unified_auto_trader(self):
        """Verify AITrader.js uses UnifiedAutoTrader component for autotrade tab"""
        ai_trader_file = "/app/frontend/src/pages/AITrader.js"
        with open(ai_trader_file, 'r') as f:
            content = f.read()
        
        # Check for UnifiedAutoTrader import and usage
        assert "import UnifiedAutoTrader" in content
        assert "<UnifiedAutoTrader" in content
        assert 'activeTab === "autotrade"' in content
        print("SUCCESS: AITrader.js uses UnifiedAutoTrader for autotrade tab")


class TestMultiChainCopyTradingComponent:
    """Test MultiChainCopyTrading component"""
    
    def test_multichain_component_exists(self):
        """Verify MultiChainCopyTrading.js exists"""
        component_file = "/app/frontend/src/components/MultiChainCopyTrading.js"
        assert os.path.exists(component_file)
        print("SUCCESS: MultiChainCopyTrading.js exists")
    
    def test_multichain_component_has_chain_config(self):
        """Verify MultiChainCopyTrading has chain configurations"""
        component_file = "/app/frontend/src/components/MultiChainCopyTrading.js"
        with open(component_file, 'r') as f:
            content = f.read()
        
        # Check for chain configurations
        assert "CHAIN_CONFIG" in content
        assert "solana:" in content
        assert "ethereum:" in content
        assert "base:" in content
        assert "arbitrum:" in content
        print("SUCCESS: MultiChainCopyTrading has chain configurations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
