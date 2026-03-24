"""
Iteration 77: Testing A-Tier/B-Tier Bot Enhancements
Tests for:
1. /api/ai-trader/platform-stats - returns correct stats (not sniper targets)
2. /api/ai-trader/sniper-targets - returns sniper data independently
3. /api/ai-trader/intelligence-dashboard - returns all 4 systems status
4. /api/ai-trader/intelligence/{token_mint} - returns token-specific intelligence
5. /api/ai-trader/settings POST with trading_mode field
6. /api/ai-trader/settings GET returns saved trading_mode and A-tier fields
7. /api/ai-trader/scan-all/{wallet_address} - auto-scan with new features
8. /api/ai-trader/auto-trade/check-exits/{wallet_address} - exit check with trailing/DCA
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pug-journal-2.preview.emergentagent.com')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
JUP_MINT = "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
BONK_MINT = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"


class TestPlatformStatsEndpoint:
    """Test 1: /api/ai-trader/platform-stats returns correct stats (not sniper targets)"""
    
    def test_platform_stats_returns_200(self):
        """Platform stats endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Platform stats returns 200")
    
    def test_platform_stats_has_correct_structure(self):
        """Platform stats should have trading stats, not sniper targets"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        data = response.json()
        
        # Should have trading stats fields
        assert "total_trades" in data, "Missing total_trades field"
        assert "win_rate" in data, "Missing win_rate field"
        assert "total_pnl_sol" in data, "Missing total_pnl_sol field"
        assert "active_positions" in data, "Missing active_positions field"
        assert "active_traders" in data, "Missing active_traders field"
        
        # Should NOT have sniper targets fields (this was the bug)
        assert "targets" not in data, "ERROR: platform-stats returning sniper targets data!"
        assert "count" not in data or isinstance(data.get("count"), int) == False or "total_trades" in data, "Possible sniper data leak"
        
        print(f"✓ Platform stats structure correct: {data}")
    
    def test_platform_stats_values_are_valid(self):
        """Platform stats values should be valid numbers"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        data = response.json()
        
        assert isinstance(data.get("total_trades"), int), "total_trades should be int"
        assert isinstance(data.get("win_rate"), (int, float)), "win_rate should be numeric"
        assert isinstance(data.get("total_pnl_sol"), (int, float)), "total_pnl_sol should be numeric"
        assert isinstance(data.get("active_positions"), int), "active_positions should be int"
        
        print(f"✓ Platform stats values valid: trades={data['total_trades']}, win_rate={data['win_rate']}%")


class TestSniperTargetsEndpoint:
    """Test 2: /api/ai-trader/sniper-targets returns sniper data independently"""
    
    def test_sniper_targets_returns_200(self):
        """Sniper targets endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/sniper-targets")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Sniper targets returns 200")
    
    def test_sniper_targets_has_correct_structure(self):
        """Sniper targets should have targets array and count"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/sniper-targets")
        data = response.json()
        
        assert "targets" in data, "Missing targets field"
        assert "count" in data, "Missing count field"
        assert isinstance(data["targets"], list), "targets should be a list"
        assert isinstance(data["count"], int), "count should be int"
        assert data["count"] == len(data["targets"]), "count should match targets length"
        
        print(f"✓ Sniper targets structure correct: {data['count']} targets found")


class TestIntelligenceDashboard:
    """Test 3: /api/ai-trader/intelligence-dashboard returns all 4 systems status"""
    
    def test_intelligence_dashboard_returns_200(self):
        """Intelligence dashboard should return 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Intelligence dashboard returns 200")
    
    def test_intelligence_dashboard_has_all_systems(self):
        """Dashboard should have all 4 intelligence systems"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        # Check all 4 systems are present
        assert "price_collector" in data, "Missing price_collector"
        assert "smart_money" in data, "Missing smart_money"
        assert "sentiment" in data, "Missing sentiment"
        assert "jito" in data, "Missing jito"
        
        print(f"✓ All 4 intelligence systems present")
    
    def test_price_collector_status(self):
        """Price collector should have status and tracking info"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        pc = data.get("price_collector", {})
        assert pc.get("status") == "active", f"Price collector status should be active, got {pc.get('status')}"
        assert "tokens_tracked" in pc, "Missing tokens_tracked"
        assert "tokens_with_real_data" in pc, "Missing tokens_with_real_data"
        assert pc["tokens_tracked"] >= 0, "tokens_tracked should be >= 0"
        
        print(f"✓ Price collector: {pc['tokens_with_real_data']}/{pc['tokens_tracked']} tokens with real data")
    
    def test_smart_money_status(self):
        """Smart money should have wallets tracked and signals"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        sm = data.get("smart_money", {})
        assert sm.get("status") == "active", f"Smart money status should be active, got {sm.get('status')}"
        assert "wallets_tracked" in sm, "Missing wallets_tracked"
        assert "recent_signals" in sm, "Missing recent_signals"
        assert sm["wallets_tracked"] >= 50, f"Should track 50+ whale wallets, got {sm['wallets_tracked']}"
        
        print(f"✓ Smart money: {sm['wallets_tracked']} wallets tracked, {sm['recent_signals']} recent signals")
    
    def test_sentiment_status(self):
        """Sentiment should have cached entries"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        sent = data.get("sentiment", {})
        assert sent.get("status") == "active", f"Sentiment status should be active, got {sent.get('status')}"
        assert "cached_entries" in sent, "Missing cached_entries"
        
        print(f"✓ Sentiment: {sent['cached_entries']} cached entries")
    
    def test_jito_status(self):
        """Jito should be active"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence-dashboard")
        data = response.json()
        
        jito = data.get("jito", {})
        assert jito.get("status") == "active", f"Jito status should be active, got {jito.get('status')}"
        
        print(f"✓ Jito MEV protection: active")


class TestTokenIntelligence:
    """Test 4: /api/ai-trader/intelligence/{token_mint} returns token-specific intelligence"""
    
    def test_jup_intelligence_returns_200(self):
        """JUP token intelligence should return 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ JUP intelligence returns 200")
    
    def test_bonk_intelligence_returns_200(self):
        """BONK token intelligence should return 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{BONK_MINT}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ BONK intelligence returns 200")
    
    def test_token_intelligence_has_all_fields(self):
        """Token intelligence should have smart_money, sentiment, data_quality"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        data = response.json()
        
        assert "token_mint" in data, "Missing token_mint"
        assert "smart_money" in data, "Missing smart_money"
        assert "sentiment" in data, "Missing sentiment"
        assert "data_quality" in data, "Missing data_quality"
        assert "combined_confidence_adj" in data, "Missing combined_confidence_adj"
        
        print(f"✓ Token intelligence has all required fields")
    
    def test_sentiment_has_required_fields(self):
        """Sentiment should have score, label, factors, confidence_adjustment"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        data = response.json()
        
        sent = data.get("sentiment", {})
        assert "score" in sent, "Missing sentiment.score"
        assert "label" in sent, "Missing sentiment.label"
        assert "factors" in sent, "Missing sentiment.factors"
        assert "confidence_adjustment" in sent, "Missing sentiment.confidence_adjustment"
        
        print(f"✓ Sentiment: score={sent['score']}, label={sent['label']}")
    
    def test_smart_money_has_required_fields(self):
        """Smart money should have action, whale_count, buy_count, sell_count, tier1_whales, weighted_buy_ratio"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        data = response.json()
        
        sm = data.get("smart_money", {})
        assert "action" in sm, "Missing smart_money.action"
        assert "whale_count" in sm, "Missing smart_money.whale_count"
        assert "buy_count" in sm, "Missing smart_money.buy_count"
        assert "sell_count" in sm, "Missing smart_money.sell_count"
        assert "tier1_whales" in sm, "Missing smart_money.tier1_whales (A-tier field)"
        assert "weighted_buy_ratio" in sm, "Missing smart_money.weighted_buy_ratio (A-tier field)"
        
        print(f"✓ Smart money: action={sm['action']}, tier1={sm['tier1_whales']}, weighted_ratio={sm['weighted_buy_ratio']}")
    
    def test_data_quality_has_required_fields(self):
        """Data quality should have candles and has_real_data"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/intelligence/{JUP_MINT}")
        data = response.json()
        
        dq = data.get("data_quality", {})
        assert "candles" in dq, "Missing data_quality.candles"
        assert "has_real_data" in dq, "Missing data_quality.has_real_data"
        
        print(f"✓ Data quality: {dq['candles']} candles, has_real_data={dq['has_real_data']}")


class TestSettingsWithTradingMode:
    """Test 5 & 6: Settings CRUD with trading_mode and A-tier fields"""
    
    def test_get_settings_returns_200(self):
        """GET settings should return 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET settings returns 200")
    
    def test_settings_has_trading_mode_field(self):
        """Settings should have trading_mode field"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        data = response.json()
        
        assert "trading_mode" in data, "Missing trading_mode field"
        assert data["trading_mode"] in ["conservative", "normal", "aggressive", "sniper"], \
            f"Invalid trading_mode: {data['trading_mode']}"
        
        print(f"✓ Settings has trading_mode: {data['trading_mode']}")
    
    def test_settings_has_atier_fields(self):
        """Settings should have all A-tier fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        data = response.json()
        
        # A-tier fields
        assert "conviction_sizing_enabled" in data, "Missing conviction_sizing_enabled"
        assert "multi_timeframe_enabled" in data, "Missing multi_timeframe_enabled"
        assert "dca_exit_enabled" in data, "Missing dca_exit_enabled"
        assert "dca_tp1_percent" in data, "Missing dca_tp1_percent"
        assert "dca_tp2_percent" in data, "Missing dca_tp2_percent"
        assert "auto_trailing_stop_enabled" in data, "Missing auto_trailing_stop_enabled"
        assert "auto_trailing_stop_percent" in data, "Missing auto_trailing_stop_percent"
        
        print(f"✓ Settings has all A-tier fields: conviction={data['conviction_sizing_enabled']}, multi_tf={data['multi_timeframe_enabled']}, dca={data['dca_exit_enabled']}")
    
    def test_post_settings_with_trading_mode(self):
        """POST settings with trading_mode should save correctly"""
        # First get current settings
        get_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        current_settings = get_response.json()
        original_mode = current_settings.get("trading_mode", "normal")
        
        # Test setting to aggressive
        test_mode = "aggressive" if original_mode != "aggressive" else "conservative"
        
        payload = {
            "wallet_address": TEST_WALLET,
            "trading_mode": test_mode,
            "enabled": current_settings.get("enabled", False),
            "risk_level": current_settings.get("risk_level", "safer"),
            "max_position_sol": current_settings.get("max_position_sol", 0.5),
            "min_position_sol": current_settings.get("min_position_sol", 0.05),
            "stop_loss_percent": current_settings.get("stop_loss_percent", 10.0),
            "take_profit_percent": current_settings.get("take_profit_percent", 20.0),
            "max_daily_trades": current_settings.get("max_daily_trades", 5),
            "auto_trade_enabled": current_settings.get("auto_trade_enabled", False),
            "auto_trade_mode": current_settings.get("auto_trade_mode", "conservative"),
            "auto_min_confidence": current_settings.get("auto_min_confidence", 0.65),
            "auto_max_daily_trades": current_settings.get("auto_max_daily_trades", 3),
            "auto_max_position_sol": current_settings.get("auto_max_position_sol", 0.2),
            "auto_cooldown_minutes": current_settings.get("auto_cooldown_minutes", 30),
            "auto_require_multiple_signals": current_settings.get("auto_require_multiple_signals", True),
            "auto_pause_on_loss": current_settings.get("auto_pause_on_loss", True),
            "auto_total_daily_limit_sol": current_settings.get("auto_total_daily_limit_sol", 1.0),
            "auto_stop_loss_percent": current_settings.get("auto_stop_loss_percent", 10.0),
            "auto_take_profit_percent": current_settings.get("auto_take_profit_percent", 20.0),
            "auto_trailing_stop_enabled": current_settings.get("auto_trailing_stop_enabled", False),
            "auto_trailing_stop_percent": current_settings.get("auto_trailing_stop_percent", 5.0),
            "conviction_sizing_enabled": current_settings.get("conviction_sizing_enabled", True),
            "multi_timeframe_enabled": current_settings.get("multi_timeframe_enabled", True),
            "dca_exit_enabled": current_settings.get("dca_exit_enabled", False),
            "dca_tp1_percent": current_settings.get("dca_tp1_percent", 15.0),
            "dca_tp2_percent": current_settings.get("dca_tp2_percent", 30.0),
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-trader/settings", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify it was saved
        verify_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        verify_data = verify_response.json()
        assert verify_data["trading_mode"] == test_mode, f"trading_mode not saved: expected {test_mode}, got {verify_data['trading_mode']}"
        
        # Restore original mode
        payload["trading_mode"] = original_mode
        requests.post(f"{BASE_URL}/api/ai-trader/settings", json=payload)
        
        print(f"✓ POST settings with trading_mode works: saved {test_mode}, restored {original_mode}")
    
    def test_post_settings_with_sniper_mode(self):
        """POST settings with sniper mode should save correctly"""
        get_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        current_settings = get_response.json()
        original_mode = current_settings.get("trading_mode", "normal")
        
        payload = {
            "wallet_address": TEST_WALLET,
            "trading_mode": "sniper",
            "enabled": current_settings.get("enabled", False),
            "risk_level": current_settings.get("risk_level", "safer"),
            "max_position_sol": current_settings.get("max_position_sol", 0.5),
            "min_position_sol": current_settings.get("min_position_sol", 0.05),
            "stop_loss_percent": current_settings.get("stop_loss_percent", 10.0),
            "take_profit_percent": current_settings.get("take_profit_percent", 20.0),
            "max_daily_trades": current_settings.get("max_daily_trades", 5),
            "auto_trade_enabled": current_settings.get("auto_trade_enabled", False),
            "auto_trade_mode": current_settings.get("auto_trade_mode", "conservative"),
            "auto_min_confidence": current_settings.get("auto_min_confidence", 0.65),
            "auto_max_daily_trades": current_settings.get("auto_max_daily_trades", 3),
            "auto_max_position_sol": current_settings.get("auto_max_position_sol", 0.2),
            "auto_cooldown_minutes": current_settings.get("auto_cooldown_minutes", 30),
            "auto_require_multiple_signals": current_settings.get("auto_require_multiple_signals", True),
            "auto_pause_on_loss": current_settings.get("auto_pause_on_loss", True),
            "auto_total_daily_limit_sol": current_settings.get("auto_total_daily_limit_sol", 1.0),
            "auto_stop_loss_percent": current_settings.get("auto_stop_loss_percent", 10.0),
            "auto_take_profit_percent": current_settings.get("auto_take_profit_percent", 20.0),
            "auto_trailing_stop_enabled": current_settings.get("auto_trailing_stop_enabled", False),
            "auto_trailing_stop_percent": current_settings.get("auto_trailing_stop_percent", 5.0),
            "conviction_sizing_enabled": current_settings.get("conviction_sizing_enabled", True),
            "multi_timeframe_enabled": current_settings.get("multi_timeframe_enabled", True),
            "dca_exit_enabled": current_settings.get("dca_exit_enabled", False),
            "dca_tp1_percent": current_settings.get("dca_tp1_percent", 15.0),
            "dca_tp2_percent": current_settings.get("dca_tp2_percent", 30.0),
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-trader/settings", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify sniper mode was saved
        verify_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        verify_data = verify_response.json()
        assert verify_data["trading_mode"] == "sniper", f"sniper mode not saved: got {verify_data['trading_mode']}"
        
        # Restore original mode
        payload["trading_mode"] = original_mode
        requests.post(f"{BASE_URL}/api/ai-trader/settings", json=payload)
        
        print(f"✓ Sniper mode saves correctly")


class TestScanAllEndpoint:
    """Test 7: /api/ai-trader/scan-all/{wallet_address} with new features"""
    
    def test_scan_all_returns_200(self):
        """Scan all endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Scan all returns 200")
    
    def test_scan_all_has_correct_structure(self):
        """Scan all should return signals_generated and signals array"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}")
        data = response.json()
        
        assert "signals_generated" in data, "Missing signals_generated"
        assert "signals" in data, "Missing signals array"
        assert isinstance(data["signals"], list), "signals should be a list"
        
        print(f"✓ Scan all structure correct: {data['signals_generated']} signals generated")


class TestCheckExitsEndpoint:
    """Test 8: /api/ai-trader/auto-trade/check-exits/{wallet_address}"""
    
    def test_check_exits_returns_200(self):
        """Check exits endpoint should return 200"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Check exits returns 200")
    
    def test_check_exits_has_correct_structure(self):
        """Check exits should return exits array and exits_triggered count"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        data = response.json()
        
        assert "success" in data, "Missing success field"
        assert "exits" in data, "Missing exits array"
        assert "positions_checked" in data, "Missing positions_checked"
        assert "exits_triggered" in data, "Missing exits_triggered count"
        assert isinstance(data["exits"], list), "exits should be a list"
        assert isinstance(data["exits_triggered"], int), "exits_triggered should be an int count"
        
        print(f"✓ Check exits structure correct: {data['exits_triggered']} exits triggered, {data['positions_checked']} positions checked")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    def test_root_health(self):
        """Root health check"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Root health check passes")
    
    def test_tokens_endpoint(self):
        """Tokens endpoint"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "safer_tokens" in data, "Missing safer_tokens"
        assert "high_risk_tokens" in data, "Missing high_risk_tokens"
        print("✓ Tokens endpoint passes")
    
    def test_positions_endpoint(self):
        """Positions endpoint"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "positions" in data, "Missing positions"
        print(f"✓ Positions endpoint passes: {len(data['positions'])} positions")
    
    def test_signals_endpoint(self):
        """Signals endpoint"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/signals/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "signals" in data, "Missing signals"
        print(f"✓ Signals endpoint passes: {len(data['signals'])} signals")
    
    def test_auto_trade_status(self):
        """Auto-trade status endpoint"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Auto-trade status endpoint passes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
