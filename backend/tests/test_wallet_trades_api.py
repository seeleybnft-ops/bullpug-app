"""
Test suite for Wallet Trades API endpoints.

Tests the multi-chain wallet integration feature:
- GET /api/wallet-trades/supported-chains - returns list of supported chains
- GET /api/wallet-trades/evm/{address} - returns EVM trades (empty without Alchemy key)
- GET /api/wallet-trades/solana/{address} - returns Solana trades
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-trading-bot-65.preview.emergentagent.com').rstrip('/')

# Test wallet addresses
TEST_EVM_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f4E9a1"
TEST_SOLANA_ADDRESS = "8xrt5yt6yZ1PBHMDqBTtCJd9ELBK1hcU6CRWmYZ4yAGY"


class TestSupportedChains:
    """Tests for GET /api/wallet-trades/supported-chains endpoint"""
    
    def test_supported_chains_returns_200(self):
        """Verify endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        assert response.status_code == 200
        print("✓ GET /api/wallet-trades/supported-chains returns 200")
    
    def test_supported_chains_has_required_fields(self):
        """Verify response has evm_chains, other_chains, alchemy_configured"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        
        assert "evm_chains" in data, "Response missing evm_chains"
        assert "other_chains" in data, "Response missing other_chains"
        assert "alchemy_configured" in data, "Response missing alchemy_configured"
        print("✓ Response has required fields: evm_chains, other_chains, alchemy_configured")
    
    def test_evm_chains_content(self):
        """Verify EVM chains include Ethereum, Base, Arbitrum"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        
        evm_chains = data["evm_chains"]
        assert len(evm_chains) == 3, f"Expected 3 EVM chains, got {len(evm_chains)}"
        
        chain_ids = {c["id"] for c in evm_chains}
        assert "ethereum" in chain_ids, "Missing ethereum chain"
        assert "base" in chain_ids, "Missing base chain"
        assert "arbitrum" in chain_ids, "Missing arbitrum chain"
        print("✓ EVM chains include ethereum, base, arbitrum")
    
    def test_evm_chains_have_required_properties(self):
        """Verify each EVM chain has id, name, chain_id"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        
        for chain in data["evm_chains"]:
            assert "id" in chain, f"Chain missing id"
            assert "name" in chain, f"Chain missing name"
            assert "chain_id" in chain, f"Chain missing chain_id"
            assert isinstance(chain["chain_id"], int), f"chain_id should be int"
        print("✓ Each EVM chain has id, name, chain_id properties")
    
    def test_other_chains_includes_solana(self):
        """Verify other_chains includes Solana"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        
        other_chains = data["other_chains"]
        assert len(other_chains) >= 1, "Expected at least 1 other chain"
        
        chain_ids = {c["id"] for c in other_chains}
        assert "solana" in chain_ids, "Missing solana in other_chains"
        print("✓ other_chains includes solana")
    
    def test_alchemy_configured_is_boolean(self):
        """Verify alchemy_configured is a boolean"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        
        assert isinstance(data["alchemy_configured"], bool), "alchemy_configured should be boolean"
        print(f"✓ alchemy_configured is boolean (value: {data['alchemy_configured']})")


class TestEVMWalletTrades:
    """Tests for GET /api/wallet-trades/evm/{address} endpoint"""
    
    def test_evm_trades_returns_200(self):
        """Verify endpoint returns 200 for valid Ethereum address"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=ethereum")
        assert response.status_code == 200
        print("✓ GET /api/wallet-trades/evm/{address} returns 200")
    
    def test_evm_trades_response_structure(self):
        """Verify response has address, chain, trades, total_found, has_more"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=ethereum")
        data = response.json()
        
        assert "address" in data, "Response missing address"
        assert "chain" in data, "Response missing chain"
        assert "trades" in data, "Response missing trades"
        assert "total_found" in data, "Response missing total_found"
        assert "has_more" in data, "Response missing has_more"
        print("✓ EVM trades response has required structure")
    
    def test_evm_trades_echoes_address(self):
        """Verify address is echoed back correctly"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=base")
        data = response.json()
        
        assert data["address"] == TEST_EVM_ADDRESS, "Address not echoed correctly"
        assert data["chain"] == "base", "Chain not echoed correctly"
        print("✓ Address and chain echoed correctly in response")
    
    def test_evm_trades_trades_is_list(self):
        """Verify trades is a list"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=ethereum")
        data = response.json()
        
        assert isinstance(data["trades"], list), "trades should be a list"
        print(f"✓ trades is a list (length: {len(data['trades'])})")
    
    def test_evm_trades_different_chains(self):
        """Test all supported EVM chains"""
        for chain in ["ethereum", "base", "arbitrum"]:
            response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain={chain}")
            assert response.status_code == 200, f"Failed for chain {chain}"
            data = response.json()
            assert data["chain"] == chain
        print("✓ All EVM chains (ethereum, base, arbitrum) work correctly")
    
    def test_evm_trades_invalid_chain(self):
        """Test that invalid chain returns 400 error"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=invalid_chain")
        assert response.status_code == 400, "Should return 400 for invalid chain"
        print("✓ Invalid chain returns 400 error")
    
    def test_evm_trades_limit_param(self):
        """Test limit parameter is accepted"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=ethereum&limit=10")
        assert response.status_code == 200
        print("✓ limit parameter accepted")


class TestSolanaWalletTrades:
    """Tests for GET /api/wallet-trades/solana/{address} endpoint"""
    
    def test_solana_trades_returns_200(self):
        """Verify endpoint returns 200 for valid Solana address"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}")
        assert response.status_code == 200
        print("✓ GET /api/wallet-trades/solana/{address} returns 200")
    
    def test_solana_trades_response_structure(self):
        """Verify response has address, chain, trades, total_found, has_more"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}")
        data = response.json()
        
        assert "address" in data, "Response missing address"
        assert "chain" in data, "Response missing chain"
        assert "trades" in data, "Response missing trades"
        assert "total_found" in data, "Response missing total_found"
        assert "has_more" in data, "Response missing has_more"
        print("✓ Solana trades response has required structure")
    
    def test_solana_trades_chain_is_solana(self):
        """Verify chain field is 'solana'"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}")
        data = response.json()
        
        assert data["chain"] == "solana", f"Expected chain 'solana', got '{data['chain']}'"
        print("✓ Chain field is 'solana'")
    
    def test_solana_trades_echoes_address(self):
        """Verify address is echoed back correctly"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}")
        data = response.json()
        
        assert data["address"] == TEST_SOLANA_ADDRESS, "Address not echoed correctly"
        print("✓ Solana address echoed correctly in response")
    
    def test_solana_trades_trades_is_list(self):
        """Verify trades is a list"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}")
        data = response.json()
        
        assert isinstance(data["trades"], list), "trades should be a list"
        print(f"✓ Solana trades is a list (length: {len(data['trades'])})")
    
    def test_solana_trades_limit_param(self):
        """Test limit parameter is accepted"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}?limit=20")
        assert response.status_code == 200
        print("✓ Solana limit parameter accepted")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
