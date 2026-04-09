"""
Iteration 96: Trading Bot Improvements Tests
Tests 6 data-driven improvements based on 8 days of live data analysis:
1. Pre-buy liquidity filter (MIN_LIQUIDITY_USD, MIN_SELL_TXNS_24H, MIN_BUY_SELL_RATIO)
2. Cap sell retries to 5 (MAX_SELL_RETRIES, closed_force status)
3. Widen trailing stop (trail_activation_pct=8, trail_distance_pct=0.05)
4. Recalibrate confidence scoring (conviction sizing bands)
5. Fix signal data pipeline (agreement boost reduced from 0.05 to 0.03)
6. Add minimum holding period (MIN_HOLD_MINUTES=15)

NOTE: These tests verify code structure and constants only - NO actual trades are executed.
"""

import pytest
import requests
import os
import sys

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cosmic-runner-hub.preview.emergentagent.com').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestMarketQualityConstants:
    """Test 1-2: Pre-buy liquidity filter constants and logic"""
    
    def test_min_liquidity_usd_lowered_to_5000(self):
        """Verify MIN_LIQUIDITY_USD is 5000 (lowered from 10000)"""
        from services.market_quality import MIN_LIQUIDITY_USD
        assert MIN_LIQUIDITY_USD == 5_000, f"Expected MIN_LIQUIDITY_USD=5000, got {MIN_LIQUIDITY_USD}"
        print(f"✓ MIN_LIQUIDITY_USD = {MIN_LIQUIDITY_USD} (lowered from 10K)")
    
    def test_min_sell_txns_24h_defined(self):
        """Verify MIN_SELL_TXNS_24H = 5 is defined"""
        from services.market_quality import MIN_SELL_TXNS_24H
        assert MIN_SELL_TXNS_24H == 5, f"Expected MIN_SELL_TXNS_24H=5, got {MIN_SELL_TXNS_24H}"
        print(f"✓ MIN_SELL_TXNS_24H = {MIN_SELL_TXNS_24H}")
    
    def test_min_buy_sell_ratio_defined(self):
        """Verify MIN_BUY_SELL_RATIO = 0.1 is defined"""
        from services.market_quality import MIN_BUY_SELL_RATIO
        assert MIN_BUY_SELL_RATIO == 0.1, f"Expected MIN_BUY_SELL_RATIO=0.1, got {MIN_BUY_SELL_RATIO}"
        print(f"✓ MIN_BUY_SELL_RATIO = {MIN_BUY_SELL_RATIO}")
    
    def test_extract_market_quality_returns_sells_ok_flag(self):
        """Verify extract_market_quality returns sells_ok flag"""
        from services.market_quality import extract_market_quality
        
        # Test with sufficient sells
        pair_data = {
            "volume": {"h24": 50000},
            "liquidity": {"usd": 10000},
            "txns": {"h24": {"buys": 100, "sells": 10}}
        }
        result = extract_market_quality(pair_data)
        assert "sells_ok" in result, "Missing sells_ok flag in result"
        assert result["sells_ok"] == True, f"Expected sells_ok=True for 10 sells, got {result['sells_ok']}"
        print(f"✓ extract_market_quality returns sells_ok flag (True for 10 sells)")
        
        # Test with insufficient sells
        pair_data_low_sells = {
            "volume": {"h24": 50000},
            "liquidity": {"usd": 10000},
            "txns": {"h24": {"buys": 100, "sells": 3}}
        }
        result_low = extract_market_quality(pair_data_low_sells)
        assert result_low["sells_ok"] == False, f"Expected sells_ok=False for 3 sells, got {result_low['sells_ok']}"
        print(f"✓ extract_market_quality correctly rejects tokens with < 5 sells/24h")
    
    def test_extract_market_quality_returns_ratio_ok_flag(self):
        """Verify extract_market_quality returns ratio_ok flag"""
        from services.market_quality import extract_market_quality
        
        # Test with good ratio (10 sells / 100 buys = 0.1)
        pair_data = {
            "volume": {"h24": 50000},
            "liquidity": {"usd": 10000},
            "txns": {"h24": {"buys": 100, "sells": 10}}
        }
        result = extract_market_quality(pair_data)
        assert "ratio_ok" in result, "Missing ratio_ok flag in result"
        assert result["ratio_ok"] == True, f"Expected ratio_ok=True for 10/100 ratio, got {result['ratio_ok']}"
        print(f"✓ extract_market_quality returns ratio_ok flag (True for 0.1 ratio)")
        
        # Test with bad ratio (1 sell / 100 buys = 0.01)
        pair_data_low_ratio = {
            "volume": {"h24": 50000},
            "liquidity": {"usd": 10000},
            "txns": {"h24": {"buys": 100, "sells": 1}}
        }
        result_low = extract_market_quality(pair_data_low_ratio)
        assert result_low["ratio_ok"] == False, f"Expected ratio_ok=False for 1/100 ratio, got {result_low['ratio_ok']}"
        print(f"✓ extract_market_quality correctly rejects tokens with low sell/buy ratio")


class TestSellRetryLogic:
    """Test 3-4: Cap sell retries to 5 and force-close logic"""
    
    def test_max_sell_retries_constant_exists(self):
        """Verify MAX_SELL_RETRIES = 5 constant exists in auto_trader_engine"""
        # Read the file and check for the constant
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        assert "MAX_SELL_RETRIES = 5" in content, "MAX_SELL_RETRIES = 5 not found in auto_trader_engine.py"
        print("✓ MAX_SELL_RETRIES = 5 constant exists")
    
    def test_force_close_status_exists(self):
        """Verify closed_force status is used after 5 retries"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        assert '"status": "closed_force"' in content, "closed_force status not found in auto_trader_engine.py"
        print("✓ closed_force status is used for force-closed positions")
    
    def test_sell_retry_count_increment_logic(self):
        """Verify sell_retry_count is incremented via $inc when sell fails"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        assert '"$inc": {"sell_retry_count":' in content, "sell_retry_count $inc not found"
        print("✓ sell_retry_count is incremented via $inc when sell fails")


class TestTrailingStopDefaults:
    """Test 5: Widen trailing stop defaults"""
    
    def test_trail_activation_pct_default_is_8(self):
        """Verify trail_activation_pct default is 8 (was 5)"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Look for the default value assignment
        assert 'trailing_activation_pct", 8)' in content, "trail_activation_pct default 8 not found"
        print("✓ trail_activation_pct default is 8 (was 5)")
    
    def test_trail_distance_pct_fallback_is_005(self):
        """Verify trail_distance_pct fallback is 0.05 (was stop_loss_pct)"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        assert "trail_distance_pct = 0.05" in content, "trail_distance_pct = 0.05 fallback not found"
        print("✓ trail_distance_pct fallback is 0.05 (was stop_loss_pct)")


class TestConvictionSizing:
    """Test 6: Recalibrated conviction sizing bands"""
    
    def test_conviction_sizing_085_is_13x(self):
        """Verify 0.85+ confidence = 1.3x (was 0.90+ = 1.5x)"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check for the new sizing bands
        assert "if trade_confidence >= 0.85:" in content, "0.85 confidence threshold not found"
        assert "sizing_mult = 1.3" in content, "sizing_mult = 1.3 not found"
        print("✓ Conviction sizing: 0.85+ = 1.3x (was 0.90+ = 1.5x)")
    
    def test_conviction_sizing_bands_recalibrated(self):
        """Verify all conviction sizing bands are recalibrated"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check all bands exist
        assert "trade_confidence >= 0.85" in content, "0.85 band not found"
        assert "trade_confidence >= 0.75" in content, "0.75 band not found"
        assert "trade_confidence >= 0.65" in content, "0.65 band not found"
        assert "trade_confidence >= 0.55" in content, "0.55 band not found"
        
        # Check sizing multipliers
        assert "sizing_mult = 1.3" in content, "1.3x sizing not found"
        assert "sizing_mult = 1.1" in content, "1.1x sizing not found"
        assert "sizing_mult = 1.0" in content, "1.0x sizing not found"
        assert "sizing_mult = 0.8" in content, "0.8x sizing not found"
        assert "sizing_mult = 0.6" in content, "0.6x sizing not found"
        print("✓ All conviction sizing bands recalibrated: 0.85+=1.3x, 0.75+=1.1x, 0.65+=1.0x, 0.55+=0.8x, <0.55=0.6x")


class TestAgreementBoost:
    """Test 7: Multi-agreement boost reduced"""
    
    def test_agreement_boost_reduced_to_003(self):
        """Verify multi-agreement boost reduced from 0.05 to 0.03"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check for the reduced boost
        assert "trade_confidence + 0.03)" in content, "0.03 agreement boost not found"
        # Verify the comment about the change
        assert "Reduced from 0.05 to 0.03" in content, "Comment about reduction not found"
        print("✓ Multi-agreement boost reduced from 0.05 to 0.03")


class TestMinHoldingPeriod:
    """Test 8: Minimum holding period"""
    
    def test_min_hold_minutes_constant_exists(self):
        """Verify MIN_HOLD_MINUTES = 15 exists"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        assert "MIN_HOLD_MINUTES = 15" in content, "MIN_HOLD_MINUTES = 15 not found"
        print("✓ MIN_HOLD_MINUTES = 15 exists")
    
    def test_min_hold_skips_exit_check(self):
        """Verify positions younger than 15 min with status 'open' skip exit check"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check for the age check logic
        assert "age_minutes < MIN_HOLD_MINUTES" in content, "MIN_HOLD_MINUTES age check not found"
        print("✓ Exit check skipped for positions younger than MIN_HOLD_MINUTES")


class TestBackendHealth:
    """Test 9: Backend starts cleanly without errors"""
    
    def test_backend_imports_cleanly(self):
        """Verify backend modules import without errors"""
        try:
            from services.market_quality import extract_market_quality, MIN_LIQUIDITY_USD, MIN_SELL_TXNS_24H, MIN_BUY_SELL_RATIO
            from services.auto_trader_engine import run_scan_and_execute, run_check_exits
            print("✓ Backend modules import cleanly")
        except Exception as e:
            pytest.fail(f"Backend import failed: {e}")
    
    def test_backend_responds_to_requests(self):
        """Verify backend responds to API requests"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/analytics/performance/{TEST_WALLET}", timeout=10)
        assert response.status_code == 200, f"Backend returned {response.status_code}"
        print(f"✓ Backend responds to requests (status {response.status_code})")


class TestPerformanceEndpoint:
    """Test 10: Performance endpoint still works"""
    
    def test_performance_endpoint_returns_200(self):
        """Verify /api/ai-trader/analytics/performance/{wallet} returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/analytics/performance/{TEST_WALLET}", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Performance endpoint returns 200")
    
    def test_performance_endpoint_returns_valid_json(self):
        """Verify performance endpoint returns valid JSON with expected fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/analytics/performance/{TEST_WALLET}", timeout=10)
        data = response.json()
        
        # Check expected fields exist
        expected_fields = ["strategy_performance", "confidence_buckets", "total_positions", "period_days"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Performance endpoint returns valid JSON with expected fields")
        print(f"  - strategy_performance: {list(data.get('strategy_performance', {}).keys())}")
        print(f"  - total_positions: {data.get('total_positions')}")
        print(f"  - period_days: {data.get('period_days')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
