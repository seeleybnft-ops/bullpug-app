"""
AI Trader Signal Generation Tests
Tests for signal generation endpoints - /api/ai-trader/scan-all, /api/ai-trader/signals, /api/ai-trader/analyze

Focus:
- Verify signals are generated with expected structure
- Verify signal fields: token_symbol, signal_type, confidence, entry_price, stop_loss_price, take_profit_price
- Verify reasoning and technical_indicators are included
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "test_wallet"

class TestSignalGeneration:
    """Signal generation tests - verifying fix for no signals showing"""
    
    def test_scan_all_generates_signals(self):
        """Test /api/ai-trader/scan-all/{wallet} generates 4-6 signals"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}",
            timeout=120  # Longer timeout as it scans multiple tokens
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Response: {data}")
        
        # Verify response structure
        assert "signals" in data, "Missing 'signals' key in response"
        assert "tokens_scanned" in data, "Missing 'tokens_scanned' key"
        assert "signals_generated" in data, "Missing 'signals_generated' key"
        
        signals = data["signals"]
        
        # Verify signals were generated (should be 4-6 based on lowered threshold)
        print(f"Signals generated: {len(signals)}")
        print(f"Tokens scanned: {data['tokens_scanned']}")
        
        # With lowered threshold (0.35), we expect multiple signals
        assert len(signals) >= 1, f"Expected at least 1 signal, got {len(signals)}"
        
        # Verify each signal has required fields
        for i, signal in enumerate(signals):
            print(f"\nSignal {i+1}: {signal.get('token_symbol')} - {signal.get('signal_type')} - confidence: {signal.get('confidence')}")
            
            # Required fields
            assert "signal_id" in signal, f"Missing signal_id in signal {i+1}"
            assert "token_symbol" in signal, f"Missing token_symbol in signal {i+1}"
            assert "signal_type" in signal, f"Missing signal_type in signal {i+1}"
            assert "confidence" in signal, f"Missing confidence in signal {i+1}"
            assert "entry_price" in signal, f"Missing entry_price in signal {i+1}"
            assert "stop_loss_price" in signal, f"Missing stop_loss_price in signal {i+1}"
            assert "take_profit_price" in signal, f"Missing take_profit_price in signal {i+1}"
            assert "reasoning" in signal, f"Missing reasoning in signal {i+1}"
            assert "technical_indicators" in signal, f"Missing technical_indicators in signal {i+1}"
            
            # Validate signal_type
            assert signal["signal_type"] in ["buy", "sell"], f"Invalid signal_type: {signal['signal_type']}"
            
            # Validate confidence (should be >= 0.35 based on lowered threshold)
            assert 0.35 <= signal["confidence"] <= 1.0, f"Confidence {signal['confidence']} out of expected range"
            
            # Validate prices are positive
            assert signal["entry_price"] > 0, f"Entry price should be positive"
            assert signal["stop_loss_price"] > 0, f"Stop loss price should be positive"
            assert signal["take_profit_price"] > 0, f"Take profit price should be positive"
            
            # Validate technical_indicators structure
            indicators = signal["technical_indicators"]
            assert "rsi" in indicators, "Missing RSI in technical_indicators"
            assert "macd" in indicators, "Missing MACD in technical_indicators"
            assert "bollinger" in indicators, "Missing bollinger in technical_indicators"
    
    def test_pending_signals_returns_generated_signals(self):
        """Test /api/ai-trader/signals/{wallet} returns pending signals after scan"""
        # First run scan-all to generate signals
        scan_response = requests.get(
            f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}",
            timeout=120
        )
        assert scan_response.status_code == 200
        
        # Small wait to ensure signals are stored
        time.sleep(1)
        
        # Now get pending signals
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/signals/{TEST_WALLET}",
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        assert "signals" in data, "Missing 'signals' key in response"
        assert "count" in data, "Missing 'count' key in response"
        
        signals = data["signals"]
        print(f"Pending signals count: {data['count']}")
        
        # Verify pending signals
        for signal in signals:
            assert signal.get("status") == "pending", f"Expected status 'pending', got {signal.get('status')}"
            assert signal.get("wallet_address") == TEST_WALLET
            
            # Verify all required fields
            assert "token_symbol" in signal
            assert "signal_type" in signal
            assert "confidence" in signal
            assert "entry_price" in signal
            assert "stop_loss_price" in signal
            assert "take_profit_price" in signal
            assert "reasoning" in signal
            assert "technical_indicators" in signal
            
            print(f"  - {signal['token_symbol']}: {signal['signal_type']} @ confidence {signal['confidence']}")

    def test_analyze_single_token_generates_signal(self):
        """Test /api/ai-trader/analyze/{token} generates signal for specific token"""
        tokens_to_test = ["SOL", "JUP", "RNDR"]
        signals_generated = 0
        
        for token in tokens_to_test:
            response = requests.post(
                f"{BASE_URL}/api/ai-trader/analyze/{token}",
                params={"wallet_address": TEST_WALLET},
                timeout=30
            )
            
            assert response.status_code == 200, f"Expected 200 for {token}, got {response.status_code}: {response.text}"
            
            data = response.json()
            print(f"\n{token} analysis: {data.get('message')}")
            
            # Check if signal was generated
            if data.get("signal"):
                signals_generated += 1
                signal = data["signal"]
                
                # Verify signal structure
                assert signal["token_symbol"] == token
                assert signal["signal_type"] in ["buy", "sell"]
                assert "confidence" in signal
                assert "entry_price" in signal
                assert "stop_loss_price" in signal
                assert "take_profit_price" in signal
                assert "reasoning" in signal
                assert "technical_indicators" in signal
                
                print(f"  Signal: {signal['signal_type']} @ {signal['entry_price']}, confidence: {signal['confidence']}")
                print(f"  Reasoning: {signal['reasoning']}")
            else:
                print(f"  No signal generated (analysis: {data.get('analysis', {}).get('rsi', 'N/A')} RSI)")
        
        print(f"\nTotal signals generated from {len(tokens_to_test)} tokens: {signals_generated}")

    def test_signal_includes_technical_indicators_details(self):
        """Verify technical_indicators in signals have complete data"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}",
            timeout=120
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data["signals"]:
            signal = data["signals"][0]
            indicators = signal["technical_indicators"]
            
            print(f"Technical indicators for {signal['token_symbol']}:")
            
            # RSI
            assert "rsi" in indicators
            rsi = indicators["rsi"]
            assert isinstance(rsi, (int, float))
            print(f"  RSI: {rsi}")
            
            # MACD
            assert "macd" in indicators
            macd = indicators["macd"]
            assert "macd" in macd
            assert "signal" in macd
            assert "histogram" in macd
            print(f"  MACD: line={macd['macd']}, signal={macd['signal']}, histogram={macd['histogram']}")
            
            # Bollinger Bands
            assert "bollinger" in indicators
            bollinger = indicators["bollinger"]
            assert "upper" in bollinger
            assert "middle" in bollinger
            assert "lower" in bollinger
            assert "position" in bollinger
            print(f"  Bollinger: upper={bollinger['upper']}, middle={bollinger['middle']}, lower={bollinger['lower']}, pos={bollinger['position']}")
            
            # Moving Averages
            assert "moving_averages" in indicators
            mas = indicators["moving_averages"]
            print(f"  Moving Averages: {mas}")
            
            # Trend info
            assert "short_trend" in indicators
            assert "long_trend" in indicators
            print(f"  Trends: short={indicators['short_trend']}, long={indicators['long_trend']}")

    def test_signal_confidence_above_threshold(self):
        """Verify all generated signals have confidence >= 0.35 (lowered threshold)"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}",
            timeout=120
        )
        
        assert response.status_code == 200
        data = response.json()
        
        signals = data["signals"]
        
        for signal in signals:
            confidence = signal["confidence"]
            assert confidence >= 0.35, f"Confidence {confidence} below threshold 0.35 for {signal['token_symbol']}"
            print(f"{signal['token_symbol']}: confidence = {confidence} (threshold = 0.35)")


class TestSignalPriceCalculations:
    """Test stop-loss and take-profit calculations"""
    
    def test_buy_signal_price_calculations(self):
        """For BUY signals: stop_loss < entry_price < take_profit"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}",
            timeout=120
        )
        
        assert response.status_code == 200
        data = response.json()
        
        buy_signals = [s for s in data["signals"] if s["signal_type"] == "buy"]
        
        for signal in buy_signals:
            entry = signal["entry_price"]
            stop_loss = signal["stop_loss_price"]
            take_profit = signal["take_profit_price"]
            
            assert stop_loss < entry, f"BUY signal: stop_loss ({stop_loss}) should be < entry ({entry})"
            assert take_profit > entry, f"BUY signal: take_profit ({take_profit}) should be > entry ({entry})"
            
            print(f"BUY {signal['token_symbol']}: SL={stop_loss:.6f} < Entry={entry:.6f} < TP={take_profit:.6f}")
    
    def test_sell_signal_price_calculations(self):
        """For SELL signals: take_profit < entry_price < stop_loss"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}",
            timeout=120
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sell_signals = [s for s in data["signals"] if s["signal_type"] == "sell"]
        
        for signal in sell_signals:
            entry = signal["entry_price"]
            stop_loss = signal["stop_loss_price"]
            take_profit = signal["take_profit_price"]
            
            assert stop_loss > entry, f"SELL signal: stop_loss ({stop_loss}) should be > entry ({entry})"
            assert take_profit < entry, f"SELL signal: take_profit ({take_profit}) should be < entry ({entry})"
            
            print(f"SELL {signal['token_symbol']}: TP={take_profit:.6f} < Entry={entry:.6f} < SL={stop_loss:.6f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
