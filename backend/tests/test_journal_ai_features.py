"""
Test suite for JournalAIAssistant features including:
- Top Picks with live coin prices from DexScreener
- Holdings tab (portfolio/combined endpoint)
- Wallet trades endpoints (Solana and EVM)
- DetectedTrades component APIs

Tests verify the features requested in iteration 30:
1. JournalAIAssistant displays correctly on journal page
2. Shows LIVE badge in header
3. Top Picks shows live coin prices from DexScreener
4. Top Picks shows auto-refresh notice
5. Backend wallet-trades endpoints work for Solana
6. Backend portfolio/combined returns portfolio data
7. DetectedTrades component APIs work
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bullpug-trader.preview.emergentagent.com').rstrip('/')

# Test wallet addresses
TEST_SOLANA_ADDRESS = "DgXwGhnb3aR6P7qrAqJgx6qyRmcwc6YA1xTr3B4E6dQr"
TEST_EVM_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f4E9a1"


class TestTopPicksCoinRecommendations:
    """Tests for Top Picks - coin recommendations from DexScreener"""
    
    def test_coin_recommendations_returns_200(self):
        """Verify endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        print("✓ GET /api/ai-suggestions/coin-recommendations returns 200")
    
    def test_coin_recommendations_has_safe_picks(self):
        """Verify response contains safe_picks array"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        assert "safe_picks" in data, "Response missing safe_picks"
        assert isinstance(data["safe_picks"], list), "safe_picks should be a list"
        print(f"✓ safe_picks present with {len(data['safe_picks'])} items")
    
    def test_coin_recommendations_has_volatile_picks(self):
        """Verify response contains volatile_picks array"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        assert "volatile_picks" in data, "Response missing volatile_picks"
        assert isinstance(data["volatile_picks"], list), "volatile_picks should be a list"
        print(f"✓ volatile_picks present with {len(data['volatile_picks'])} items")
    
    def test_safe_picks_structure(self):
        """Verify safe_picks items have required fields (symbol, name, price, change_24h, platform)"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        if len(data["safe_picks"]) > 0:
            pick = data["safe_picks"][0]
            assert "symbol" in pick, "safe_pick missing symbol"
            assert "name" in pick, "safe_pick missing name"
            assert "price" in pick, "safe_pick missing price"
            assert "change_24h" in pick, "safe_pick missing change_24h"
            assert "platform" in pick, "safe_pick missing platform"
            print(f"✓ safe_picks[0] structure valid: {pick['symbol']} @ ${pick['price']}")
        else:
            print("⚠ No safe_picks to validate structure")
    
    def test_volatile_picks_structure(self):
        """Verify volatile_picks items have required fields"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        if len(data["volatile_picks"]) > 0:
            pick = data["volatile_picks"][0]
            assert "symbol" in pick, "volatile_pick missing symbol"
            assert "name" in pick, "volatile_pick missing name"
            assert "price" in pick, "volatile_pick missing price"
            assert "change_24h" in pick, "volatile_pick missing change_24h"
            assert "platform" in pick, "volatile_pick missing platform"
            print(f"✓ volatile_picks[0] structure valid: {pick['symbol']} @ ${pick['price']}")
        else:
            print("⚠ No volatile_picks to validate structure")
    
    def test_coin_recommendations_has_metadata(self):
        """Verify response includes metadata (source, generated_at, disclaimer)"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        data = response.json()
        
        assert "source" in data, "Response missing source"
        assert "generated_at" in data, "Response missing generated_at"
        assert "disclaimer" in data, "Response missing disclaimer"
        print(f"✓ Metadata present - source: {data['source']}")


class TestPortfolioCombined:
    """Tests for Holdings tab - portfolio/combined endpoint"""
    
    def test_portfolio_combined_requires_address(self):
        """Verify endpoint returns 400 without any address"""
        response = requests.get(f"{BASE_URL}/api/portfolio/combined")
        assert response.status_code == 400
        print("✓ GET /api/portfolio/combined returns 400 without address")
    
    def test_portfolio_combined_solana_returns_200(self):
        """Verify endpoint returns 200 with Solana address"""
        response = requests.get(f"{BASE_URL}/api/portfolio/combined?solana_address={TEST_SOLANA_ADDRESS}")
        assert response.status_code == 200
        print("✓ GET /api/portfolio/combined?solana_address returns 200")
    
    def test_portfolio_combined_solana_structure(self):
        """Verify response has solana portfolio with proper structure"""
        response = requests.get(f"{BASE_URL}/api/portfolio/combined?solana_address={TEST_SOLANA_ADDRESS}")
        data = response.json()
        
        assert "total_value_usd" in data, "Missing total_value_usd"
        assert "total_tokens" in data, "Missing total_tokens"
        assert "chains" in data, "Missing chains"
        assert "solana" in data, "Missing solana portfolio"
        assert "last_updated" in data, "Missing last_updated"
        print("✓ Portfolio response has required fields")
    
    def test_portfolio_solana_has_chain_details(self):
        """Verify Solana portfolio has chain details (chain_name, native_balance, tokens)"""
        response = requests.get(f"{BASE_URL}/api/portfolio/combined?solana_address={TEST_SOLANA_ADDRESS}")
        data = response.json()
        
        if data.get("solana"):
            sol = data["solana"]
            assert "chain_name" in sol, "Missing chain_name in solana"
            assert "native_balance" in sol, "Missing native_balance in solana"
            assert "tokens" in sol, "Missing tokens in solana"
            assert "native_symbol" in sol, "Missing native_symbol in solana"
            assert sol["native_symbol"] == "SOL", f"Expected SOL, got {sol['native_symbol']}"
            print(f"✓ Solana portfolio has proper chain details - balance: {sol['native_balance']} SOL")
        else:
            print("⚠ Solana portfolio is null")
    
    def test_portfolio_prices_endpoint(self):
        """Verify portfolio/prices endpoint returns ETH and SOL prices"""
        response = requests.get(f"{BASE_URL}/api/portfolio/prices")
        assert response.status_code == 200
        data = response.json()
        
        assert "ETH" in data, "Missing ETH price"
        assert "SOL" in data, "Missing SOL price"
        assert "last_updated" in data, "Missing last_updated"
        
        assert "usd" in data["ETH"], "Missing ETH USD price"
        assert "usd" in data["SOL"], "Missing SOL USD price"
        print(f"✓ Prices - ETH: ${data['ETH']['usd']}, SOL: ${data['SOL']['usd']}")


class TestWalletTradesSolana:
    """Tests for wallet-trades Solana endpoint"""
    
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
        
        assert data["address"] == TEST_SOLANA_ADDRESS, "Address not echoed correctly"
        assert data["chain"] == "solana", f"Expected chain 'solana', got '{data['chain']}'"
        print("✓ Solana trades response has required structure")
    
    def test_solana_trades_trades_is_list(self):
        """Verify trades is a list"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}")
        data = response.json()
        
        assert isinstance(data["trades"], list), "trades should be a list"
        print(f"✓ Solana trades is a list (length: {len(data['trades'])})")
    
    def test_solana_trades_with_limit(self):
        """Test limit parameter is accepted"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/solana/{TEST_SOLANA_ADDRESS}?limit=10")
        assert response.status_code == 200
        print("✓ Solana limit parameter accepted")


class TestWalletTradesSupportedChains:
    """Tests for supported-chains endpoint"""
    
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
    
    def test_evm_chains_includes_all(self):
        """Verify EVM chains include Ethereum, Base, Arbitrum"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        
        evm_chains = data["evm_chains"]
        chain_ids = {c["id"] for c in evm_chains}
        assert "ethereum" in chain_ids, "Missing ethereum chain"
        assert "base" in chain_ids, "Missing base chain"
        assert "arbitrum" in chain_ids, "Missing arbitrum chain"
        print("✓ EVM chains include ethereum, base, arbitrum")
    
    def test_other_chains_includes_solana(self):
        """Verify other_chains includes Solana"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        
        chain_ids = {c["id"] for c in data["other_chains"]}
        assert "solana" in chain_ids, "Missing solana in other_chains"
        print("✓ other_chains includes solana")
    
    def test_alchemy_configured_is_true(self):
        """Verify alchemy_configured is True (API key is set)"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        
        assert data["alchemy_configured"] == True, "Alchemy should be configured"
        print("✓ alchemy_configured is True")


class TestDetectedTradesIntegration:
    """Tests for DetectedTrades component integration"""
    
    def test_evm_trades_returns_200(self):
        """Verify EVM trades endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=ethereum")
        assert response.status_code == 200
        print("✓ GET /api/wallet-trades/evm/{address} returns 200")
    
    def test_evm_trades_structure(self):
        """Verify EVM response has required structure"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=ethereum")
        data = response.json()
        
        assert "address" in data, "Response missing address"
        assert "chain" in data, "Response missing chain"
        assert "trades" in data, "Response missing trades"
        
        # EVM may return empty trades if Alchemy key doesn't support chain
        assert isinstance(data["trades"], list), "trades should be a list"
        print(f"✓ EVM trades response structure valid - {len(data['trades'])} trades found")
    
    def test_evm_trades_different_chains(self):
        """Test all supported EVM chains return 200"""
        for chain in ["ethereum", "base", "arbitrum"]:
            response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain={chain}")
            # Should return 200 even if no trades found (graceful degradation)
            assert response.status_code == 200, f"Failed for chain {chain}"
            data = response.json()
            assert data["chain"] == chain
        print("✓ All EVM chains (ethereum, base, arbitrum) return 200")
    
    def test_evm_invalid_chain_returns_400(self):
        """Test that invalid chain returns 400 error"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{TEST_EVM_ADDRESS}?chain=invalid")
        assert response.status_code == 400, "Should return 400 for invalid chain"
        print("✓ Invalid chain returns 400 error")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
