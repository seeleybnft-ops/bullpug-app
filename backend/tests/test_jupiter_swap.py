"""
Tests for Jupiter DEX swap integration in AI Trader
Tests swap-transaction and execute-swap endpoints
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test public key for swap transaction testing
TEST_PUBLIC_KEY = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"

# Token mints
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
AMOUNT_LAMPORTS = 100000000  # 0.1 SOL

class TestJupiterQuoteEndpoint:
    """Test /api/ai-trader/quote endpoint"""
    
    def test_quote_returns_valid_response(self):
        """Quote endpoint returns valid quote from Jupiter"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/quote",
            params={
                "input_mint": SOL_MINT,
                "output_mint": USDC_MINT,
                "amount_lamports": AMOUNT_LAMPORTS,
                "slippage_bps": 100
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "inputMint" in data, "Quote should contain inputMint"
        assert "outputMint" in data, "Quote should contain outputMint"
        assert "inAmount" in data, "Quote should contain inAmount"
        assert "outAmount" in data, "Quote should contain outAmount"
        assert data["inputMint"] == SOL_MINT, "Input mint should match"
        assert data["outputMint"] == USDC_MINT, "Output mint should match"
        print(f"✓ Quote received: {data['inAmount']} input -> {data['outAmount']} output")
    
    def test_quote_has_route_plan(self):
        """Quote should include route plan"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/quote",
            params={
                "input_mint": SOL_MINT,
                "output_mint": USDC_MINT,
                "amount_lamports": AMOUNT_LAMPORTS,
                "slippage_bps": 100
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "routePlan" in data, "Quote should contain routePlan"
        assert isinstance(data["routePlan"], list), "routePlan should be a list"
        if len(data["routePlan"]) > 0:
            route = data["routePlan"][0]
            assert "swapInfo" in route, "Route should contain swapInfo"
            print(f"✓ Route plan found with {len(data['routePlan'])} route(s)")


class TestSwapTransactionEndpoint:
    """Test /api/ai-trader/swap-transaction endpoint"""
    
    def test_swap_transaction_returns_serialized_tx(self):
        """Swap transaction endpoint returns serialized transaction"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/swap-transaction",
            params={
                "user_public_key": TEST_PUBLIC_KEY,
                "input_mint": SOL_MINT,
                "output_mint": USDC_MINT,
                "amount_lamports": AMOUNT_LAMPORTS,
                "slippage_bps": 100
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "swapTransaction" in data, "Response should contain swapTransaction"
        assert len(data["swapTransaction"]) > 100, "swapTransaction should be a base64 encoded string"
        print(f"✓ Swap transaction received: {len(data['swapTransaction'])} chars")
    
    def test_swap_transaction_includes_quote_info(self):
        """Swap transaction should include quote summary"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/swap-transaction",
            params={
                "user_public_key": TEST_PUBLIC_KEY,
                "input_mint": SOL_MINT,
                "output_mint": USDC_MINT,
                "amount_lamports": AMOUNT_LAMPORTS,
                "slippage_bps": 100
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "quote" in data, "Response should contain quote summary"
        quote = data["quote"]
        assert "inputMint" in quote, "Quote should contain inputMint"
        assert "outputMint" in quote, "Quote should contain outputMint"
        assert "inAmount" in quote, "Quote should contain inAmount"
        assert "outAmount" in quote, "Quote should contain outAmount"
        print(f"✓ Quote summary: {quote['inAmount']} -> {quote['outAmount']}")
    
    def test_swap_transaction_includes_block_height(self):
        """Swap transaction should include lastValidBlockHeight"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/swap-transaction",
            params={
                "user_public_key": TEST_PUBLIC_KEY,
                "input_mint": SOL_MINT,
                "output_mint": USDC_MINT,
                "amount_lamports": AMOUNT_LAMPORTS,
                "slippage_bps": 100
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "lastValidBlockHeight" in data, "Response should contain lastValidBlockHeight"
        assert isinstance(data["lastValidBlockHeight"], int), "lastValidBlockHeight should be an integer"
        print(f"✓ Last valid block height: {data['lastValidBlockHeight']}")


class TestExecuteSwapEndpoint:
    """Test /api/ai-trader/execute-swap endpoint"""
    
    def test_execute_swap_requires_valid_signal(self):
        """Execute swap should fail if signal doesn't exist"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/execute-swap",
            params={
                "wallet_address": TEST_PUBLIC_KEY,
                "signal_id": "non-existent-signal-id",
                "tx_signature": "test_tx_signature_123",
                "input_amount": 0.1,
                "output_amount": 8.5
            }
        )
        # Should return 404 for non-existent signal
        assert response.status_code == 404, f"Expected 404 for non-existent signal, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain detail"
        assert "not found" in data["detail"].lower(), "Error should mention signal not found"
        print(f"✓ Execute swap correctly rejects non-existent signal: {data['detail']}")
    
    def test_execute_swap_requires_all_params(self):
        """Execute swap should require all parameters"""
        # Missing tx_signature
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/execute-swap",
            params={
                "wallet_address": TEST_PUBLIC_KEY,
                "signal_id": "test-signal",
                "input_amount": 0.1,
                "output_amount": 8.5
            }
        )
        # Should return 422 for missing required parameter
        assert response.status_code == 422, f"Expected 422 for missing param, got {response.status_code}"
        print("✓ Execute swap correctly validates required parameters")


class TestAITraderEndpointsExist:
    """Verify all AI Trader endpoints exist and are accessible"""
    
    def test_disclaimer_endpoint(self):
        """Disclaimer endpoint should return terms"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/disclaimer")
        assert response.status_code == 200
        data = response.json()
        assert "terms" in data
        assert "risk_acknowledgment" in data
        print("✓ Disclaimer endpoint working")
    
    def test_tokens_endpoint(self):
        """Tokens endpoint should return available tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200
        data = response.json()
        assert "safer_tokens" in data
        assert "high_risk_tokens" in data
        assert "position_limits" in data
        print(f"✓ Tokens endpoint working: {len(data['safer_tokens'])} safer, {len(data['high_risk_tokens'])} high risk")
    
    def test_analyze_endpoint_exists(self):
        """Analyze endpoint should exist and work with valid token"""
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/analyze/SOL",
            params={"wallet_address": TEST_PUBLIC_KEY}
        )
        # Should return 200 with signal or message
        assert response.status_code == 200, f"Analyze returned {response.status_code}"
        data = response.json()
        assert "signal" in data or "message" in data
        print(f"✓ Analyze endpoint working")
    
    def test_scan_all_endpoint(self):
        """Scan-all endpoint should scan all tokens"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/scan-all/{TEST_PUBLIC_KEY}")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "tokens_scanned" in data
        assert "signals_generated" in data
        print(f"✓ Scan-all endpoint working: scanned {data['tokens_scanned']} tokens")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
