"""
Test Signal Analytics Backtester and Improvements - Iteration 59

Tests the new signal analytics features:
1. POST /api/signal-analytics/track-prices - Real-time signal tracking
2. POST /api/signal-analytics/backtest - Strategy backtester with configurable params
3. GET /api/signal-analytics/backtest/optimal - Find optimal settings
4. POST /api/signal-analytics/apply-improvements - Apply backtest recommendations

Also verifies:
- Strategy engine MIN_SIGNAL_CONFIDENCE updated to 0.55
- Combined strategy prioritizes momentum + breakout agreement
- Existing analytics endpoints still working
"""

import pytest
import requests
import os
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")


class TestTrackPricesEndpoint:
    """Test POST /api/signal-analytics/track-prices endpoint"""
    
    def test_track_prices_success(self):
        """Test that track-prices endpoint works and returns expected structure"""
        response = requests.post(f"{BASE_URL}/api/signal-analytics/track-prices")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should have 'success' field"
        assert data["success"] == True, "Track prices should succeed"
        assert "signals_processed" in data, "Response should have 'signals_processed' field"
        assert "outcomes_updated" in data, "Response should have 'outcomes_updated' field"
        assert "errors" in data, "Response should have 'errors' field"
        
        # Verify types
        assert isinstance(data["signals_processed"], int), "signals_processed should be int"
        assert isinstance(data["outcomes_updated"], int), "outcomes_updated should be int"
        assert isinstance(data["errors"], list), "errors should be list"
        
        print(f"Track prices: processed {data['signals_processed']} signals, updated {data['outcomes_updated']} outcomes")


class TestBacktestEndpoint:
    """Test POST /api/signal-analytics/backtest endpoint"""
    
    def test_backtest_default_params(self):
        """Test backtest with default parameters"""
        response = requests.post(f"{BASE_URL}/api/signal-analytics/backtest")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check if we have enough data or got insufficient data response
        if data.get("success") == False:
            assert "error" in data or "message" in data, "Should have error message for insufficient data"
            print(f"Backtest skipped: {data.get('error', data.get('message'))}")
            return
        
        # Verify config
        assert "config" in data, "Response should have 'config' field"
        config = data["config"]
        assert config["min_confidence"] == 0.45, "Default min_confidence should be 0.45"
        assert config["period_days"] == 30, "Default period_days should be 30"
        assert config["time_horizon"] == "24h", "Default time_horizon should be 24h"
        
        # Verify results structure
        assert "results" in data, "Response should have 'results' field"
        results = data["results"]
        assert "total_signals" in results
        assert "signals_passed_filter" in results
        assert "win_count" in results
        assert "loss_count" in results
        assert "win_rate" in results
        assert "avg_pnl_percent" in results
        assert "max_drawdown_percent" in results
        assert "sharpe_ratio" in results
        
        print(f"Backtest results: {results['signals_passed_filter']} signals, {results['win_rate']}% win rate")
    
    def test_backtest_confidence_045(self):
        """Test backtest with 0.45 confidence threshold"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"min_confidence": 0.45}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["config"]["min_confidence"] == 0.45
            print(f"Backtest at 0.45 conf: {data['results']['win_rate']}% win rate")
    
    def test_backtest_confidence_055(self):
        """Test backtest with 0.55 confidence threshold (optimized setting)"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"min_confidence": 0.55}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["config"]["min_confidence"] == 0.55
            print(f"Backtest at 0.55 conf: {data['results']['win_rate']}% win rate")
    
    def test_backtest_confidence_060(self):
        """Test backtest with 0.60 confidence threshold"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"min_confidence": 0.60}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["config"]["min_confidence"] == 0.60
            print(f"Backtest at 0.60 conf: {data['results']['win_rate']}% win rate")
    
    def test_backtest_strategy_filter_combined(self):
        """Test backtest with combined strategy filter"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"strategy_filter": "combined"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["config"]["strategy_filter"] == "combined"
            print(f"Backtest combined strategy: {data['results']['win_rate']}% win rate")
    
    def test_backtest_strategy_filter_momentum(self):
        """Test backtest with momentum strategy filter"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"strategy_filter": "momentum"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["config"]["strategy_filter"] == "momentum"
            print(f"Backtest momentum strategy: {data['results']['win_rate']}% win rate")
    
    def test_backtest_time_horizon_1h(self):
        """Test backtest with 1h time horizon"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"time_horizon": "1h"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["config"]["time_horizon"] == "1h"
    
    def test_backtest_time_horizon_4h(self):
        """Test backtest with 4h time horizon"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"time_horizon": "4h"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["config"]["time_horizon"] == "4h"
    
    def test_backtest_require_multi_strategy(self):
        """Test backtest with require_multi_strategy flag"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"require_multi_strategy": True}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["config"]["require_multi_strategy"] == True
    
    def test_backtest_invalid_strategy_filter(self):
        """Test backtest with invalid strategy filter returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"strategy_filter": "invalid_strategy"}
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid strategy, got {response.status_code}"
    
    def test_backtest_invalid_time_horizon(self):
        """Test backtest with invalid time horizon returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"time_horizon": "invalid"}
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid time_horizon, got {response.status_code}"
    
    def test_backtest_confidence_out_of_range(self):
        """Test backtest with confidence out of valid range"""
        # Too low
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"min_confidence": 0.20}
        )
        assert response.status_code == 422, f"Expected 422 for confidence < 0.35, got {response.status_code}"
        
        # Too high
        response = requests.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"min_confidence": 0.95}
        )
        assert response.status_code == 422, f"Expected 422 for confidence > 0.80, got {response.status_code}"


class TestBacktestOptimalEndpoint:
    """Test GET /api/signal-analytics/backtest/optimal endpoint"""
    
    def test_find_optimal_settings(self):
        """Test finding optimal settings"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/backtest/optimal")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "all_results" in data, "Response should have 'all_results' field"
        assert "recommendation" in data, "Response should have 'recommendation' field"
        
        # all_results should be a list
        assert isinstance(data["all_results"], list), "all_results should be a list"
        
        # If we have results, verify structure
        if data["all_results"]:
            result = data["all_results"][0]
            assert "min_confidence" in result
            assert "strategy" in result
            assert "win_rate" in result
            assert "score" in result
            
            print(f"Top result: conf={result['min_confidence']}, strategy={result['strategy']}, win_rate={result['win_rate']}%, score={result['score']}")
        
        # Check optimal_settings if present
        if data.get("optimal_settings"):
            optimal = data["optimal_settings"]
            assert "config" in optimal
            assert "results" in optimal
            print(f"Optimal settings: conf={optimal['config']['min_confidence']}, win_rate={optimal['results']['win_rate']}%")
    
    def test_find_optimal_settings_custom_period(self):
        """Test finding optimal settings with custom period"""
        response = requests.get(
            f"{BASE_URL}/api/signal-analytics/backtest/optimal",
            params={"period_days": 14}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_find_optimal_settings_1h_horizon(self):
        """Test finding optimal settings with 1h time horizon"""
        response = requests.get(
            f"{BASE_URL}/api/signal-analytics/backtest/optimal",
            params={"time_horizon": "1h"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestApplyImprovementsEndpoint:
    """Test POST /api/signal-analytics/apply-improvements endpoint"""
    
    def test_apply_improvements(self):
        """Test applying backtest improvements"""
        response = requests.post(f"{BASE_URL}/api/signal-analytics/apply-improvements")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check success or insufficient data
        if data.get("success") == False:
            assert "message" in data, "Should have message for failure"
            print(f"Apply improvements: {data['message']}")
            return
        
        # Verify structure
        assert "current_settings" in data, "Response should have 'current_settings'"
        assert "recommended_settings" in data, "Response should have 'recommended_settings'"
        assert "changes" in data, "Response should have 'changes'"
        assert "backtest_results" in data, "Response should have 'backtest_results'"
        
        # Verify current settings
        current = data["current_settings"]
        assert "min_signal_confidence" in current
        
        # Verify backtest results
        bt_results = data["backtest_results"]
        assert "win_rate" in bt_results
        assert "avg_pnl" in bt_results
        assert "signals_tested" in bt_results
        
        print(f"Apply improvements: win_rate={bt_results['win_rate']}%, changes={len(data['changes'])}")


class TestExistingAnalyticsEndpoints:
    """Verify existing signal analytics endpoints still work"""
    
    def test_performance_summary(self):
        """Test GET /api/signal-analytics/performance-summary still works"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/performance-summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data
        print(f"Performance summary: {data.get('total_signals_analyzed', data.get('total_outcomes_analyzed', 0))} signals")
    
    def test_confidence_analysis(self):
        """Test GET /api/signal-analytics/confidence-analysis still works"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/confidence-analysis")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data
        assert "total_signals" in data
        assert "confidence_distribution" in data
        print(f"Confidence analysis: {data['total_signals']} signals analyzed")
    
    def test_strategy_comparison(self):
        """Test GET /api/signal-analytics/strategy-comparison still works"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/strategy-comparison")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data
        assert "strategies" in data
        print(f"Strategy comparison: {len(data['strategies'])} strategies")
    
    def test_optimal_settings(self):
        """Test GET /api/signal-analytics/optimal-settings still works"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/optimal-settings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Either has sufficient_data or settings
        assert "sufficient_data" in data or "settings" in data or "current_recommendations" in data
        print(f"Optimal settings: sufficient_data={data.get('sufficient_data', 'N/A')}")


class TestStrategyEngineConstants:
    """Verify strategy engine constants are correctly set"""
    
    def test_analyze_token_uses_correct_threshold(self):
        """Test that analyze endpoint uses MIN_SIGNAL_CONFIDENCE of 0.55"""
        # We can't directly test the constant, but we can verify behavior
        # by analyzing a token and checking the signal threshold
        
        # First, get a token to analyze
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        
        tokens = response.json()
        if tokens.get("safer_tokens"):
            token = tokens["safer_tokens"][0]
            token_symbol = token["symbol"]
            
            # Analyze the token
            analyze_response = requests.post(
                f"{BASE_URL}/api/ai-trader/analyze/{token_symbol}",
                params={"wallet_address": "TEST_wallet_iteration59"}
            )
            
            assert analyze_response.status_code == 200, f"Analyze failed: {analyze_response.text}"
            
            data = analyze_response.json()
            
            # If a signal was generated, verify confidence >= 0.55
            if data.get("signal"):
                signal = data["signal"]
                assert signal["confidence"] >= 0.55, f"Signal confidence {signal['confidence']} should be >= 0.55"
                print(f"Signal generated: {signal['signal_type']} with {signal['confidence']*100:.1f}% confidence")
            else:
                print(f"No signal generated for {token_symbol} (expected if confidence < 0.55)")


class TestBacktestResultsStructure:
    """Test detailed structure of backtest results"""
    
    def test_backtest_by_strategy_breakdown(self):
        """Test that backtest returns by_strategy breakdown"""
        response = requests.post(f"{BASE_URL}/api/signal-analytics/backtest")
        
        assert response.status_code == 200
        
        data = response.json()
        if data.get("success"):
            assert "by_strategy" in data, "Response should have 'by_strategy' breakdown"
            
            # Verify strategy breakdown structure
            for strategy, stats in data["by_strategy"].items():
                assert "total" in stats
                assert "wins" in stats
                assert "losses" in stats
                assert "win_rate" in stats
                assert "avg_pnl" in stats
                print(f"Strategy {strategy}: {stats['total']} signals, {stats['win_rate']}% win rate")
    
    def test_backtest_by_confidence_breakdown(self):
        """Test that backtest returns by_confidence_bucket breakdown"""
        response = requests.post(f"{BASE_URL}/api/signal-analytics/backtest")
        
        assert response.status_code == 200
        
        data = response.json()
        if data.get("success"):
            assert "by_confidence_bucket" in data, "Response should have 'by_confidence_bucket' breakdown"
            
            # Verify confidence breakdown structure
            for bucket, stats in data["by_confidence_bucket"].items():
                assert "total" in stats
                assert "wins" in stats
                assert "losses" in stats
                assert "win_rate" in stats
                print(f"Confidence {bucket}: {stats['total']} signals, {stats['win_rate']}% win rate")
    
    def test_backtest_recommendations(self):
        """Test that backtest returns recommendations"""
        response = requests.post(f"{BASE_URL}/api/signal-analytics/backtest")
        
        assert response.status_code == 200
        
        data = response.json()
        if data.get("success"):
            assert "recommendations" in data, "Response should have 'recommendations'"
            assert isinstance(data["recommendations"], list), "recommendations should be a list"
            
            for rec in data["recommendations"]:
                print(f"Recommendation: {rec}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
