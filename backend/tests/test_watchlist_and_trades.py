"""
Test suite for Watchlist and Auto-Trade Fetching features
Tests:
1. Watchlist CRUD - GET, POST add, POST remove, DELETE clear
2. Wallet Trades - supported-chains, EVM trades
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "test_wallet_pytest_123"

class TestWatchlistAPI:
    """Watchlist CRUD endpoint tests"""
    
    def test_get_watchlist_empty(self):
        """GET /api/watchlist/{wallet_address} returns empty list for new wallet"""
        response = requests.get(f"{BASE_URL}/api/watchlist/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "wallet_address" in data
        assert data["wallet_address"] == TEST_WALLET
        assert "coins" in data
        assert isinstance(data["coins"], list)
        assert "total_items" in data
        print(f"PASS: GET watchlist returned {data['total_items']} items for {TEST_WALLET}")
    
    def test_add_coin_to_watchlist(self):
        """POST /api/watchlist/add successfully adds a coin"""
        payload = {
            "wallet_address": TEST_WALLET,
            "coin": {
                "symbol": "TEST_DOGE",
                "name": "Test Dogecoin",
                "contract_address": "test123abc",
                "platform": "Solana",
                "added_price": 0.5
            }
        }
        response = requests.post(f"{BASE_URL}/api/watchlist/add", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        assert "message" in data
        print(f"PASS: Add coin response: {data['message']}")
    
    def test_verify_coin_added(self):
        """GET /api/watchlist/{wallet_address} shows added coin"""
        response = requests.get(f"{BASE_URL}/api/watchlist/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        coins = data.get("coins", [])
        symbols = [c.get("symbol") for c in coins]
        assert "TEST_DOGE" in symbols, f"TEST_DOGE not found in {symbols}"
        print(f"PASS: Verified TEST_DOGE in watchlist with {len(coins)} coins")
    
    def test_remove_from_watchlist(self):
        """POST /api/watchlist/remove successfully removes a coin"""
        payload = {
            "wallet_address": TEST_WALLET,
            "symbol": "TEST_DOGE"
        }
        response = requests.post(f"{BASE_URL}/api/watchlist/remove", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "success" in data
        assert "message" in data
        print(f"PASS: Remove coin response: success={data['success']}, {data['message']}")
    
    def test_clear_watchlist(self):
        """DELETE /api/watchlist/{wallet_address}/clear clears all coins"""
        # First add a coin
        payload = {
            "wallet_address": TEST_WALLET,
            "coin": {
                "symbol": "CLEAR_TEST",
                "name": "Clear Test",
                "platform": "Solana"
            }
        }
        requests.post(f"{BASE_URL}/api/watchlist/add", json=payload)
        
        # Clear the watchlist
        response = requests.delete(f"{BASE_URL}/api/watchlist/{TEST_WALLET}/clear")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: Clear watchlist response: {data}")


class TestWalletTradesAPI:
    """Wallet trades fetching endpoint tests"""
    
    def test_supported_chains(self):
        """GET /api/wallet-trades/supported-chains returns chain info"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        assert response.status_code == 200
        
        data = response.json()
        assert "evm_chains" in data
        assert "other_chains" in data
        assert "alchemy_configured" in data
        
        evm_chain_ids = [c["id"] for c in data["evm_chains"]]
        assert "ethereum" in evm_chain_ids
        assert "base" in evm_chain_ids
        assert "arbitrum" in evm_chain_ids
        
        print(f"PASS: Supported chains - Alchemy: {data['alchemy_configured']}")
    
    def test_alchemy_configured(self):
        """GET /api/wallet-trades/supported-chains shows alchemy_configured: true"""
        response = requests.get(f"{BASE_URL}/api/wallet-trades/supported-chains")
        data = response.json()
        assert data.get("alchemy_configured") == True
        print("PASS: alchemy_configured is True")
    
    def test_evm_trades_endpoint(self):
        """GET /api/wallet-trades/evm/{address} returns trades array"""
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{test_address}?chain=ethereum&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "address" in data
        assert "chain" in data
        assert "trades" in data
        assert isinstance(data["trades"], list)
        
        print(f"PASS: EVM trades structure valid - found {data['total_found']} trades")
    
    def test_invalid_chain_returns_400(self):
        """GET /api/wallet-trades/evm/{address}?chain=invalid returns 400"""
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        response = requests.get(f"{BASE_URL}/api/wallet-trades/evm/{test_address}?chain=invalid")
        assert response.status_code == 400
        print("PASS: Invalid chain returns 400")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
