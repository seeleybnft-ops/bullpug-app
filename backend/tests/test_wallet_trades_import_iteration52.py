"""
Backend Tests for Wallet Trades Import API Endpoint - Iteration 52

Tests the /api/wallet-trades/import-to-journal endpoint:
- Accepts trades array and wallet_address
- Returns correct response structure
- Handles duplicates appropriately
"""

import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestImportToJournalEndpoint:
    """Tests for /api/wallet-trades/import-to-journal POST endpoint."""
    
    def test_import_requires_wallet_address(self):
        """Test that endpoint requires wallet_address query parameter."""
        response = requests.post(
            f"{BASE_URL}/api/wallet-trades/import-to-journal",
            json=[]
        )
        # Should fail with 422 (validation error) without wallet_address
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASSED: import-to-journal requires wallet_address parameter")
    
    def test_import_accepts_trades_array(self):
        """Test that endpoint accepts trades array and wallet_address."""
        test_wallet = "TEST_IMPORT_7sB9E1vYHGLqbMvdM2FGYXqkFwKqYz"
        test_trades = [
            {
                "chain": "solana",
                "tx_hash": f"TEST_tx_hash_{datetime.now().timestamp()}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dex_protocol": "Jupiter/Raydium",
                "token_in_symbol": "SOL",
                "token_in_address": "So11111111111111111111111111111111111111112",
                "token_in_amount": 0.5,
                "token_out_symbol": "USDC",
                "token_out_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "token_out_amount": 50.0,
                "explorer_url": "https://solscan.io/tx/test123",
                "status": "detected"
            }
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/wallet-trades/import-to-journal?wallet_address={test_wallet}",
            json=test_trades
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data
        assert data["success"] == True
        assert "imported_count" in data
        assert "duplicates_skipped" in data
        assert "message" in data
        
        print(f"PASSED: import-to-journal accepts trades array - imported {data['imported_count']} trades")
    
    def test_import_handles_duplicates(self):
        """Test that importing same trade twice doesn't create duplicates."""
        test_wallet = "TEST_DUP_7sB9E1vYHGLqbMvdM2FGYXqkFwKqYz"
        unique_tx_hash = f"TEST_dup_tx_{datetime.now().timestamp()}"
        
        test_trade = {
            "chain": "ethereum",
            "tx_hash": unique_tx_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dex_protocol": "Uniswap V3",
            "token_in_symbol": "ETH",
            "token_in_address": "native",
            "token_in_amount": 1.0,
            "token_out_symbol": "USDC",
            "token_out_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "token_out_amount": 2000.0,
            "explorer_url": "https://etherscan.io/tx/test",
            "status": "detected"
        }
        
        # First import
        response1 = requests.post(
            f"{BASE_URL}/api/wallet-trades/import-to-journal?wallet_address={test_wallet}",
            json=[test_trade]
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["imported_count"] == 1
        
        # Second import of same trade (should be duplicate)
        response2 = requests.post(
            f"{BASE_URL}/api/wallet-trades/import-to-journal?wallet_address={test_wallet}",
            json=[test_trade]
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["duplicates_skipped"] == 1, f"Expected 1 duplicate skipped, got {data2['duplicates_skipped']}"
        assert data2["imported_count"] == 0
        
        print("PASSED: import-to-journal handles duplicates correctly")
    
    def test_import_empty_array(self):
        """Test that importing empty array works."""
        test_wallet = "TEST_EMPTY_7sB9E1vYHGLqbMvdM2FGYXqkFwKqYz"
        
        response = requests.post(
            f"{BASE_URL}/api/wallet-trades/import-to-journal?wallet_address={test_wallet}",
            json=[]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["imported_count"] == 0
        
        print("PASSED: import-to-journal handles empty array")
    
    def test_import_multiple_chains(self):
        """Test importing trades from multiple chains."""
        test_wallet = "TEST_MULTI_7sB9E1vYHGLqbMvdM2FGYXqkFwKqYz"
        timestamp_suffix = datetime.now().timestamp()
        
        test_trades = [
            {
                "chain": "solana",
                "tx_hash": f"TEST_sol_tx_{timestamp_suffix}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dex_protocol": "Jupiter",
                "token_in_address": "So11111111111111111111111111111111111111112",
                "token_in_amount": 1.0,
                "token_out_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "token_out_amount": 100.0,
                "explorer_url": "https://solscan.io/tx/test",
                "status": "detected"
            },
            {
                "chain": "base",
                "tx_hash": f"TEST_base_tx_{timestamp_suffix}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dex_protocol": "Aerodrome",
                "token_in_address": "native",
                "token_in_amount": 0.5,
                "token_out_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "token_out_amount": 1000.0,
                "explorer_url": "https://basescan.org/tx/test",
                "status": "detected"
            },
            {
                "chain": "arbitrum",
                "tx_hash": f"TEST_arb_tx_{timestamp_suffix}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dex_protocol": "Uniswap V3",
                "token_in_address": "native",
                "token_in_amount": 0.3,
                "token_out_address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                "token_out_amount": 600.0,
                "explorer_url": "https://arbiscan.io/tx/test",
                "status": "detected"
            }
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/wallet-trades/import-to-journal?wallet_address={test_wallet}",
            json=test_trades
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["imported_count"] == 3, f"Expected 3, got {data['imported_count']}"
        
        print(f"PASSED: import-to-journal handles multiple chains - imported {data['imported_count']} trades")


class TestExistingEndpointsStillWork:
    """Verify existing wallet-trades endpoints are still functional."""
    
    def test_supported_chains_endpoint(self):
        """Test /api/wallet-trades/supported-chains endpoint."""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        assert response.status_code == 200
        
        data = response.json()
        assert "evm_chains" in data
        assert "other_chains" in data
        
        # Verify chain IDs
        evm_chains = {c["id"]: c["chain_id"] for c in data["evm_chains"]}
        assert evm_chains.get("ethereum") == 1
        assert evm_chains.get("base") == 8453
        assert evm_chains.get("arbitrum") == 42161
        
        print("PASSED: supported-chains endpoint works")
    
    def test_multi_chain_endpoint_with_addresses(self):
        """Test /api/wallet-trades/multi-chain endpoint."""
        test_solana_addr = "7sB9E1vYHGLqbMvdM2FGYXqkFwKqYzBDCSvZwRp4gRti"
        
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/multi-chain",
            params={
                "solana_address": test_solana_addr,
                "chains": "solana"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "trades_by_chain" in data
        assert "total_trades" in data
        assert "chains_scanned" in data
        
        print(f"PASSED: multi-chain endpoint works - scanned {data['chains_scanned']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
