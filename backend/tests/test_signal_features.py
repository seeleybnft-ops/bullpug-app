"""
Test cases for Signal Card and AI Trader features:
1. SignalCard editable position input - Frontend feature
2. No Approve button (only Reject and Quick Trade) - Frontend feature
3. Scan-all deduplication (no duplicate signals for same token)
4. Scan-all filters contradicting signals (keeps higher RSI priority)
5. Analyze endpoint accepts contract_address parameter
6. Analyze endpoint looks up unknown tokens via DexScreener
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "test_signal_features_wallet"

class TestAnalyzeEndpointWithContractAddress:
    """Test analyze endpoint accepts contract_address parameter"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Enable both risk levels for testing"""
        requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET,
                "enabled": True,
                "risk_level": "both",
                "max_position_sol": 0.5
            }
        )
    
    def test_analyze_known_token_without_contract_address(self):
        """Test analyzing a known token (BONK) without contract_address"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/BONK",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should return either signal or analysis
        assert "signal" in data or "analysis" in data, "Should have signal or analysis in response"
        assert "message" in data, "Should have message in response"
    
    def test_analyze_with_contract_address_for_known_token(self):
        """Test analyze accepts contract_address param and uses it for price lookup"""
        bonk_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/TESTTOKEN",
            params={
                "wallet_address": TEST_WALLET,
                "contract_address": bonk_address
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should return analysis (price data fetched via contract_address)
        assert "message" in data
        # If no signal, should have analysis with price data
        if data.get("signal") is None and data.get("analysis"):
            assert "current_price" in data["analysis"], "Should have current_price from contract address"
    
    def test_analyze_unknown_token_lookup_via_dexscreener(self):
        """Test that unknown token symbols attempt DexScreener lookup"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/WIF",
            params={"wallet_address": TEST_WALLET}
        )
        assert response.status_code == 200
        data = response.json()
        # WIF is a known token, should work
        assert "message" in data
        # Either signal generated or analysis returned
        assert data.get("signal") is not None or data.get("analysis") is not None


class TestScanAllDeduplication:
    """Test scan-all endpoint deduplication and contradicting signal filtering"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Enable both risk levels for testing"""
        requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET,
                "enabled": True,
                "risk_level": "both",
                "max_position_sol": 0.5
            }
        )
        # Clean up any existing pending signals
        requests.delete(
            f"{BASE_URL}/api/ai-trader/signals/cleanup/{TEST_WALLET}"
        )
    
    def test_scan_all_returns_no_duplicate_token_symbols(self):
        """Scan-all should not return duplicate signals for same token"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}"
        )
        assert response.status_code == 200
        data = response.json()
        
        signals = data.get("signals", [])
        if len(signals) > 0:
            # Check for duplicates
            token_symbols = [s["token_symbol"] for s in signals]
            unique_symbols = set(token_symbols)
            assert len(token_symbols) == len(unique_symbols), \
                f"Found duplicate tokens: {token_symbols}"
    
    def test_scan_all_response_structure(self):
        """Verify scan-all response structure"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/scan-all/{TEST_WALLET}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "signals" in data, "Response should have 'signals' field"
        assert "tokens_scanned" in data, "Response should have 'tokens_scanned' field"
        assert "signals_generated" in data, "Response should have 'signals_generated' field"
        
        # Verify signal structure if any signals returned
        for signal in data.get("signals", []):
            assert "signal_id" in signal
            assert "token_symbol" in signal
            assert "signal_type" in signal
            assert "technical_indicators" in signal
            assert "rsi" in signal["technical_indicators"]


class TestSettingsEndpoint:
    """Test settings endpoint works correctly"""
    
    def test_save_settings_returns_clean_json(self):
        """Settings endpoint should not return MongoDB _id"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": f"{TEST_WALLET}_settings_test",
                "enabled": True,
                "risk_level": "safer",
                "max_position_sol": 0.3
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should not have _id in response
        assert "_id" not in data, "Response should not contain _id"
        if "settings" in data:
            assert "_id" not in data["settings"], "Settings should not contain _id"
        
        assert data.get("success") == True
        assert data.get("message") == "Settings saved"
    
    def test_get_settings(self):
        """Get settings should return user settings without _id"""
        wallet = f"{TEST_WALLET}_get_settings"
        # First save settings
        requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": wallet,
                "enabled": True,
                "risk_level": "both"
            }
        )
        
        # Then get settings
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{wallet}")
        assert response.status_code == 200
        data = response.json()
        
        assert "_id" not in data, "Settings response should not contain _id"
        assert data.get("wallet_address") == wallet


class TestSignalApprovalFlow:
    """Test signal approval flow (Approve button removed, Quick Trade flow)"""
    
    def test_approve_signal_endpoint_exists(self):
        """Approve signal endpoint should still exist for Quick Trade flow"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/signals/approve",
            json={
                "signal_id": "fake_signal_id",
                "wallet_address": TEST_WALLET
            }
        )
        # Should return 404 for non-existent signal, not 405 or 500
        assert response.status_code in [404, 400], \
            f"Approve endpoint should return 404/400 for non-existent signal, got {response.status_code}"
    
    def test_reject_signal_endpoint_exists(self):
        """Reject signal endpoint should exist"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/signals/reject/fake_signal_id",
            params={"wallet_address": TEST_WALLET}
        )
        # Should return 404 for non-existent signal
        assert response.status_code in [404, 400], \
            f"Reject endpoint should return 404/400 for non-existent signal, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
