"""
Test Top Picks Auto-refresh & Holdings Portfolio Features

Tests for:
1. /api/ai-suggestions/coin-recommendations - returns safe_picks and volatile_picks
2. /api/portfolio/combined - returns chains and solana holdings (Alchemy integration)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestCoinRecommendations:
    """Test /api/ai-suggestions/coin-recommendations endpoint"""
    
    def test_recommendations_returns_200(self):
        """Test that coin-recommendations endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ /api/ai-suggestions/coin-recommendations returns 200")
    
    def test_recommendations_has_safe_picks(self):
        """Test that response contains safe_picks array"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        data = response.json()
        
        assert "safe_picks" in data, "Response missing 'safe_picks' field"
        assert isinstance(data["safe_picks"], list), "safe_picks should be a list"
        print(f"✓ safe_picks field present with {len(data['safe_picks'])} items")
    
    def test_recommendations_has_volatile_picks(self):
        """Test that response contains volatile_picks array"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        data = response.json()
        
        assert "volatile_picks" in data, "Response missing 'volatile_picks' field"
        assert isinstance(data["volatile_picks"], list), "volatile_picks should be a list"
        print(f"✓ volatile_picks field present with {len(data['volatile_picks'])} items")
    
    def test_safe_picks_structure(self):
        """Test safe_picks coin data structure"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("safe_picks"):
            coin = data["safe_picks"][0]
            required_fields = ["symbol", "name", "price", "change_24h", "platform"]
            for field in required_fields:
                assert field in coin, f"Safe pick missing required field: {field}"
            
            assert isinstance(coin["symbol"], str), "Symbol should be string"
            assert isinstance(coin["price"], (int, float)), "Price should be numeric"
            print(f"✓ Safe pick structure valid: {coin['symbol']} at ${coin['price']}")
    
    def test_volatile_picks_structure(self):
        """Test volatile_picks coin data structure"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("volatile_picks"):
            coin = data["volatile_picks"][0]
            required_fields = ["symbol", "name", "price", "change_24h", "platform"]
            for field in required_fields:
                assert field in coin, f"Volatile pick missing required field: {field}"
            
            print(f"✓ Volatile pick structure valid: {coin['symbol']} at ${coin['price']}")
    
    def test_recommendations_has_metadata(self):
        """Test that response contains necessary metadata"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/coin-recommendations")
        assert response.status_code == 200
        data = response.json()
        
        assert "source" in data, "Response missing 'source' field"
        assert "generated_at" in data, "Response missing 'generated_at' field"
        assert "disclaimer" in data, "Response missing 'disclaimer' field"
        print(f"✓ Metadata present - source: {data['source']}")


class TestPortfolioCombined:
    """Test /api/portfolio/combined endpoint"""
    
    def test_combined_requires_address(self):
        """Test that endpoint requires at least one address"""
        response = requests.get(f"{BASE_URL}/api/portfolio/combined")
        assert response.status_code == 400, "Should return 400 when no address provided"
        print("✓ /api/portfolio/combined correctly requires address")
    
    def test_combined_with_evm_address(self):
        """Test combined portfolio with EVM address"""
        # Using a known Ethereum address (Vitalik's)
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        response = requests.get(
            f"{BASE_URL}/api/portfolio/combined",
            params={"evm_address": test_address}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "chains" in data, "Response missing 'chains' field"
        assert "total_value_usd" in data, "Response missing 'total_value_usd' field"
        assert "last_updated" in data, "Response missing 'last_updated' field"
        assert isinstance(data["chains"], list), "chains should be a list"
        print(f"✓ EVM portfolio returns {len(data['chains'])} chains")
    
    def test_combined_with_solana_address(self):
        """Test combined portfolio with Solana address"""
        # Using a sample Solana address
        test_address = "9WzDXwBbmPdCBoccS4dcPxzXhMNZPcLqLqrU9CprN7E1"
        response = requests.get(
            f"{BASE_URL}/api/portfolio/combined",
            params={"solana_address": test_address}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "solana" in data, "Response missing 'solana' field"
        print(f"✓ Solana portfolio endpoint working")
    
    def test_combined_chain_structure(self):
        """Test that chains have proper structure"""
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        response = requests.get(
            f"{BASE_URL}/api/portfolio/combined",
            params={"evm_address": test_address}
        )
        assert response.status_code == 200
        
        data = response.json()
        if data.get("chains") and len(data["chains"]) > 0:
            chain = data["chains"][0]
            required_fields = ["chain", "chain_name", "native_balance", "native_symbol", "tokens"]
            for field in required_fields:
                assert field in chain, f"Chain missing required field: {field}"
            
            assert isinstance(chain["tokens"], list), "tokens should be a list"
            print(f"✓ Chain structure valid: {chain['chain_name']} with {len(chain['tokens'])} tokens")


class TestPortfolioPrices:
    """Test /api/portfolio/prices endpoint"""
    
    def test_prices_endpoint(self):
        """Test that prices endpoint returns ETH and SOL prices"""
        response = requests.get(f"{BASE_URL}/api/portfolio/prices")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "ETH" in data, "Response missing 'ETH' price"
        assert "SOL" in data, "Response missing 'SOL' price"
        assert "last_updated" in data, "Response missing 'last_updated'"
        
        assert "usd" in data["ETH"], "ETH missing usd price"
        assert "usd" in data["SOL"], "SOL missing usd price"
        print(f"✓ Prices: ETH=${data['ETH']['usd']}, SOL=${data['SOL']['usd']}")


class TestJournalHoldings:
    """Test /api/ai-suggestions/journal-holdings endpoint (fallback)"""
    
    def test_journal_holdings_endpoint(self):
        """Test journal holdings endpoint"""
        test_wallet = "TEST_wallet_123"
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/journal-holdings/{test_wallet}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "holdings" in data, "Response missing 'holdings' field"
        assert "suggestions" in data, "Response missing 'suggestions' field"
        print(f"✓ Journal holdings returns {len(data['holdings'])} holdings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
