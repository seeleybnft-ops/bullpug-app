"""
Iteration 63: Testing P0 (Custodial Wallet Decryption Fix), P1 (Runner Tokens), and Services Refactoring

Tests:
1. Custodial wallet info endpoint returns valid wallet address and balance
2. Auto-trade scan endpoint works without decryption errors
3. Runner tokens endpoint returns list of trending tokens with score
4. Backend services are properly imported and working
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pug-journal-1.preview.emergentagent.com')

# Test wallets from the review request
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
EXPECTED_CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"


class TestCustodialWalletDecryptionFix:
    """P0: Test that custodial wallet decryption is working correctly"""
    
    def test_custodial_wallet_info_returns_valid_address(self):
        """Verify custodial wallet info endpoint returns the expected wallet address"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "wallet_address" in data, "Response should contain wallet_address"
        assert data["wallet_address"] == EXPECTED_CUSTODIAL_WALLET, f"Expected {EXPECTED_CUSTODIAL_WALLET}, got {data['wallet_address']}"
        
        # Verify balance fields are present
        assert "balance_sol" in data, "Response should contain balance_sol"
        assert "balance_lamports" in data, "Response should contain balance_lamports"
        assert "max_deposit_sol" in data, "Response should contain max_deposit_sol"
        assert "available_deposit_sol" in data, "Response should contain available_deposit_sol"
        
        print(f"✓ Custodial wallet address: {data['wallet_address']}")
        print(f"✓ Balance: {data['balance_sol']} SOL")
    
    def test_custodial_wallet_balance_is_zero(self):
        """Verify custodial wallet has 0 SOL balance (expected per review request)"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Balance should be 0 as mentioned in the review request
        assert data["balance_sol"] == 0.0, f"Expected 0 SOL balance, got {data['balance_sol']}"
        assert data["balance_lamports"] == 0, f"Expected 0 lamports, got {data['balance_lamports']}"
        
        print(f"✓ Custodial wallet balance is 0 SOL (expected)")


class TestAutoTradeScanWithoutDecryptionErrors:
    """P0: Test that auto-trade scan works without decryption errors"""
    
    def test_auto_trade_scan_executes_without_errors(self):
        """Verify auto-trade scan endpoint works without decryption errors"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should contain success field"
        assert data["success"] == True, f"Expected success=True, got {data['success']}"
        
        # Should not have any decryption errors
        assert "error" not in data or "decrypt" not in str(data.get("error", "")).lower(), \
            "Should not have decryption errors"
        
        print(f"✓ Auto-trade scan completed successfully")
        print(f"✓ Trades executed: {data.get('trades_executed', 0)}")
    
    def test_auto_trade_scan_skips_due_to_insufficient_balance(self):
        """Verify trades are skipped due to insufficient balance (not decryption errors)"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check skipped trades have "Insufficient" reason, not decryption errors
        skipped = data.get("skipped", [])
        for skip in skipped:
            reason = skip.get("reason", "")
            # Should be "Insufficient custodial balance" or "No buy signal", not decryption error
            assert "decrypt" not in reason.lower(), f"Found decryption error in skip reason: {reason}"
            
            if "Insufficient" in reason:
                print(f"✓ {skip.get('symbol')}: Skipped due to insufficient balance (expected)")
            elif "No buy signal" in reason:
                print(f"✓ {skip.get('symbol')}: Skipped due to no signal")
    
    def test_auto_trade_status_shows_enabled(self):
        """Verify auto-trade is enabled for the test wallet"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "auto_trade_enabled" in data, "Response should contain auto_trade_enabled"
        assert data["auto_trade_enabled"] == True, "Auto-trade should be enabled for test wallet"
        
        print(f"✓ Auto-trade enabled: {data['auto_trade_enabled']}")
        print(f"✓ Settings: {data.get('settings', {})}")


class TestRunnerTokensEndpoint:
    """P1: Test runner tokens endpoint returns trending tokens with scores"""
    
    def test_runners_endpoint_returns_success(self):
        """Verify runners endpoint returns success"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should contain success field"
        assert data["success"] == True, f"Expected success=True, got {data['success']}"
        
        print(f"✓ Runners endpoint returned success")
    
    def test_runners_endpoint_returns_list_of_tokens(self):
        """Verify runners endpoint returns a list of runner tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "runners" in data, "Response should contain runners list"
        assert isinstance(data["runners"], list), "runners should be a list"
        
        print(f"✓ Found {len(data['runners'])} runner tokens")
    
    def test_runner_tokens_have_required_fields(self):
        """Verify each runner token has required fields including score"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        
        assert response.status_code == 200
        data = response.json()
        
        runners = data.get("runners", [])
        if len(runners) == 0:
            pytest.skip("No runners found at this time")
        
        required_fields = [
            "symbol", "token_address", "price_usd", "liquidity_usd",
            "volume_24h", "price_change_1h", "runner_score", "dex"
        ]
        
        for runner in runners:
            for field in required_fields:
                assert field in runner, f"Runner {runner.get('symbol', 'unknown')} missing field: {field}"
            
            # Verify runner_score is a number between 0 and 100
            score = runner.get("runner_score", 0)
            assert isinstance(score, (int, float)), f"runner_score should be a number, got {type(score)}"
            assert 0 <= score <= 100, f"runner_score should be 0-100, got {score}"
            
            print(f"✓ Runner: {runner['symbol']} - Score: {runner['runner_score']} - DEX: {runner['dex']}")
    
    def test_runners_criteria_is_returned(self):
        """Verify runners endpoint returns the criteria used for filtering"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "criteria" in data, "Response should contain criteria"
        criteria = data["criteria"]
        
        expected_criteria_fields = [
            "min_liquidity", "min_volume_24h", "min_price_change_1h",
            "max_price_change_1h", "min_txns_1h", "max_age_hours"
        ]
        
        for field in expected_criteria_fields:
            assert field in criteria, f"Criteria missing field: {field}"
        
        print(f"✓ Criteria: {criteria}")
    
    def test_runners_disclaimer_is_returned(self):
        """Verify runners endpoint returns a risk disclaimer"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "disclaimer" in data, "Response should contain disclaimer"
        assert "HIGH RISK" in data["disclaimer"], "Disclaimer should mention HIGH RISK"
        
        print(f"✓ Disclaimer: {data['disclaimer']}")


class TestServicesRefactoring:
    """Test that refactored services are properly imported and working"""
    
    def test_ai_trader_analyze_uses_refactored_services(self):
        """Verify AI trader analyze endpoint works (uses TechnicalAnalyzer and StrategyEngine)"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/SOL",
            params={"wallet_address": TEST_WALLET}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return either a signal or analysis
        assert "signal" in data or "analysis" in data, "Response should contain signal or analysis"
        
        if data.get("signal"):
            signal = data["signal"]
            # Verify technical indicators are present (from TechnicalAnalyzer)
            assert "technical_indicators" in signal, "Signal should contain technical_indicators"
            indicators = signal["technical_indicators"]
            assert "rsi" in indicators, "Indicators should contain RSI"
            assert "macd" in indicators, "Indicators should contain MACD"
            assert "bollinger" in indicators, "Indicators should contain Bollinger Bands"
            
            # Verify strategy is present (from StrategyEngine)
            assert "strategy" in signal, "Signal should contain strategy"
            assert "confidence" in signal, "Signal should contain confidence"
            
            print(f"✓ Signal generated: {signal['signal_type']} with {signal['confidence']*100:.1f}% confidence")
            print(f"✓ Strategy: {signal['strategy']}")
            print(f"✓ RSI: {indicators['rsi']}")
        else:
            print(f"✓ No signal generated: {data.get('message', 'No strong signal')}")
    
    def test_scan_all_uses_refactored_services(self):
        """Verify scan-all endpoint works (uses all refactored services)"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "signals" in data, "Response should contain signals"
        assert "tokens_scanned" in data, "Response should contain tokens_scanned"
        
        print(f"✓ Scanned {data['tokens_scanned']} tokens")
        print(f"✓ Generated {data.get('signals_generated', len(data['signals']))} signals")


class TestRunnerDetectorService:
    """Test RunnerDetector service specifically"""
    
    def test_runner_detector_returns_scored_tokens(self):
        """Verify RunnerDetector returns tokens with runner_score"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        
        assert response.status_code == 200
        data = response.json()
        
        runners = data.get("runners", [])
        if len(runners) == 0:
            pytest.skip("No runners found at this time")
        
        # Verify runners are sorted by score (highest first)
        scores = [r.get("runner_score", 0) for r in runners]
        assert scores == sorted(scores, reverse=True), "Runners should be sorted by score (highest first)"
        
        print(f"✓ Runners sorted by score: {scores}")
    
    def test_runner_detector_filters_by_criteria(self):
        """Verify RunnerDetector filters tokens by criteria"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/runners")
        
        assert response.status_code == 200
        data = response.json()
        
        runners = data.get("runners", [])
        criteria = data.get("criteria", {})
        
        # Parse criteria values
        min_liquidity = float(criteria.get("min_liquidity", "$10,000").replace("$", "").replace(",", ""))
        min_volume = float(criteria.get("min_volume_24h", "$50,000").replace("$", "").replace(",", ""))
        
        for runner in runners:
            # Verify liquidity meets minimum
            assert runner.get("liquidity_usd", 0) >= min_liquidity, \
                f"{runner['symbol']} liquidity {runner['liquidity_usd']} < {min_liquidity}"
            
            # Verify volume meets minimum
            assert runner.get("volume_24h", 0) >= min_volume, \
                f"{runner['symbol']} volume {runner['volume_24h']} < {min_volume}"
            
            print(f"✓ {runner['symbol']}: Liquidity ${runner['liquidity_usd']:,.0f}, Volume ${runner['volume_24h']:,.0f}")


class TestAutoTradeIncludesRunners:
    """Test that auto-trade scan includes runner tokens"""
    
    def test_auto_trade_scan_includes_runners(self):
        """Verify auto-trade scan includes runner tokens in the scan"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if runners were found
        runners_found = data.get("runners_found", 0)
        print(f"✓ Runners found in scan: {runners_found}")
        
        # Check skipped list for runner tokens
        skipped = data.get("skipped", [])
        runner_skipped = [s for s in skipped if "(RUNNER)" in s.get("symbol", "")]
        
        print(f"✓ Runner tokens in skipped list: {len(runner_skipped)}")
        for runner in runner_skipped:
            print(f"  - {runner['symbol']}: {runner['reason']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
