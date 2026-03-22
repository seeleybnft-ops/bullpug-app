"""
Test Multi-Chain Wallet Trades Endpoints - Iteration 51
Tests for /api/wallet-trades/* endpoints (Solana, Ethereum, Base, Arbitrum)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-trading-bot-65.preview.emergentagent.com')

# Test wallet addresses
TEST_SOLANA_ADDRESS = "7T4vW3VJmYkXHsxNQ1DKwCPxvw8bQ3v4J6vZ9R2Kk1Lp"
TEST_EVM_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f5aB05"


class TestSupportedChainsEndpoint:
    """Tests for GET /api/wallet-trades/supported-chains"""
    
    def test_supported_chains_returns_correct_structure(self):
        """Verify supported-chains endpoint returns correct chain info"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "evm_chains" in data
        assert "other_chains" in data
        assert "alchemy_configured" in data
        
        # Verify EVM chains
        evm_chains = data["evm_chains"]
        assert len(evm_chains) == 3
        
        chain_ids = {c["id"] for c in evm_chains}
        assert chain_ids == {"ethereum", "base", "arbitrum"}
        
        # Verify each EVM chain has required fields
        for chain in evm_chains:
            assert "id" in chain
            assert "name" in chain
            assert "chain_id" in chain
        
        # Verify Solana in other_chains
        other_chains = data["other_chains"]
        assert len(other_chains) >= 1
        assert any(c["id"] == "solana" for c in other_chains)
        print(f"PASSED: Supported chains endpoint returns correct structure")
    
    def test_supported_chains_has_correct_chain_ids(self):
        """Verify chain IDs match expected values"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        
        assert response.status_code == 200
        data = response.json()
        
        evm_chains = {c["id"]: c for c in data["evm_chains"]}
        
        assert evm_chains["ethereum"]["chain_id"] == 1
        assert evm_chains["base"]["chain_id"] == 8453
        assert evm_chains["arbitrum"]["chain_id"] == 42161
        print(f"PASSED: Chain IDs are correct (ETH=1, Base=8453, Arb=42161)")


class TestMultiChainEndpoint:
    """Tests for GET /api/wallet-trades/multi-chain"""
    
    def test_multi_chain_requires_wallet_address(self):
        """Verify endpoint requires at least one wallet address"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/multi-chain")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "wallet address" in data["detail"].lower() or "required" in data["detail"].lower()
        print(f"PASSED: Multi-chain endpoint requires wallet address")
    
    def test_multi_chain_accepts_solana_address(self):
        """Verify multi-chain endpoint accepts Solana address"""
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/multi-chain",
            params={"solana_address": TEST_SOLANA_ADDRESS}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["solana_address"] == TEST_SOLANA_ADDRESS
        assert data["evm_address"] is None
        assert "trades_by_chain" in data
        assert "total_trades" in data
        assert "chains_scanned" in data
        assert "solana" in data["chains_scanned"]
        print(f"PASSED: Multi-chain accepts Solana address, scanned chains: {data['chains_scanned']}")
    
    def test_multi_chain_accepts_evm_address(self):
        """Verify multi-chain endpoint accepts EVM address"""
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/multi-chain",
            params={"evm_address": TEST_EVM_ADDRESS}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["solana_address"] is None
        assert data["evm_address"] == TEST_EVM_ADDRESS
        assert "trades_by_chain" in data
        
        # Should scan all EVM chains
        for chain in ["ethereum", "base", "arbitrum"]:
            assert chain in data["chains_scanned"]
        print(f"PASSED: Multi-chain accepts EVM address, scanned chains: {data['chains_scanned']}")
    
    def test_multi_chain_accepts_both_addresses(self):
        """Verify multi-chain endpoint accepts both Solana and EVM addresses"""
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/multi-chain",
            params={
                "solana_address": TEST_SOLANA_ADDRESS,
                "evm_address": TEST_EVM_ADDRESS
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["solana_address"] == TEST_SOLANA_ADDRESS
        assert data["evm_address"] == TEST_EVM_ADDRESS
        
        # Should scan all chains
        expected_chains = {"solana", "ethereum", "base", "arbitrum"}
        scanned_chains = set(data["chains_scanned"])
        assert expected_chains == scanned_chains
        print(f"PASSED: Multi-chain accepts both addresses, all chains scanned")
    
    def test_multi_chain_selective_chains(self):
        """Verify chain selection parameter works"""
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/multi-chain",
            params={
                "evm_address": TEST_EVM_ADDRESS,
                "chains": "ethereum,base"  # Only scan 2 chains
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only scan selected chains
        assert "ethereum" in data["chains_scanned"]
        assert "base" in data["chains_scanned"]
        assert "arbitrum" not in data["chains_scanned"]
        print(f"PASSED: Chain selection parameter works, scanned: {data['chains_scanned']}")


class TestSolanaTradesEndpoint:
    """Tests for GET /api/wallet-trades/solana/{address}"""
    
    def test_solana_trades_returns_correct_structure(self):
        """Verify Solana trades endpoint returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "address" in data
        assert "chain" in data
        assert data["chain"] == "solana"
        assert "trades" in data
        assert isinstance(data["trades"], list)
        assert "total_found" in data
        assert "has_more" in data
        print(f"PASSED: Solana trades endpoint returns correct structure")


class TestEvmTradesEndpoint:
    """Tests for GET /api/wallet-trades/evm/{address}"""
    
    def test_evm_trades_ethereum(self):
        """Verify EVM trades endpoint works for Ethereum"""
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}",
            params={"chain": "ethereum"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["address"] == TEST_EVM_ADDRESS
        assert data["chain"] == "ethereum"
        assert "trades" in data
        assert isinstance(data["trades"], list)
        print(f"PASSED: EVM trades endpoint works for Ethereum")
    
    def test_evm_trades_base(self):
        """Verify EVM trades endpoint works for Base"""
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}",
            params={"chain": "base"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["chain"] == "base"
        print(f"PASSED: EVM trades endpoint works for Base")
    
    def test_evm_trades_arbitrum(self):
        """Verify EVM trades endpoint works for Arbitrum"""
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}",
            params={"chain": "arbitrum"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["chain"] == "arbitrum"
        print(f"PASSED: EVM trades endpoint works for Arbitrum")
    
    def test_evm_trades_unsupported_chain_rejected(self):
        """Verify unsupported chain is rejected"""
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}",
            params={"chain": "unsupported_chain"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "unsupported" in data["detail"].lower() or "supported" in data["detail"].lower()
        print(f"PASSED: Unsupported chain rejected with 400")


class TestTradeResponseFormat:
    """Tests to verify trade data format when trades are found"""
    
    def test_trade_data_contains_required_fields(self):
        """If trades exist, verify they have required fields"""
        # Test with multi-chain to check structure
        response = requests.get(
            f"{BASE_URL}/api/wallet-trades/multi-chain",
            params={"solana_address": TEST_SOLANA_ADDRESS}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Even if no trades, structure should be correct
        assert "trades_by_chain" in data
        for chain, trades in data["trades_by_chain"].items():
            assert isinstance(trades, list)
            # If there are trades, verify structure
            for trade in trades[:3]:  # Check up to 3 trades
                assert "chain" in trade
                assert "tx_hash" in trade
                assert "timestamp" in trade
                assert "dex_protocol" in trade
                assert "token_in_address" in trade
                assert "token_out_address" in trade
                assert "explorer_url" in trade
        
        print(f"PASSED: Trade data structure validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
