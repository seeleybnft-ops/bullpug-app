"""
Iteration 85: Bug Fixes Testing
- Bug 1: Copy address clipboard fallback (non-secure context)
- Bug 2: Withdraw button greyed out when wallet has balance
- Bug 3: Fund Ledger showing wrong balance (should show on-chain balance)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"


class TestLedgerBalanceEndpoint:
    """Test /api/ledger/balance/{wallet} returns on-chain balance"""

    def test_ledger_balance_returns_on_chain_balance(self):
        """Bug 3 fix: Ledger balance should include on_chain_balance_sol"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify on_chain_balance_sol field exists
        assert "on_chain_balance_sol" in data, "Missing on_chain_balance_sol field"
        assert isinstance(data["on_chain_balance_sol"], (int, float))
        
        # Verify custodial_address field exists
        assert "custodial_address" in data, "Missing custodial_address field"
        assert data["custodial_address"] == CUSTODIAL_WALLET
        
        print(f"✅ on_chain_balance_sol: {data['on_chain_balance_sol']}")
        print(f"✅ custodial_address: {data['custodial_address']}")

    def test_ledger_balance_on_chain_greater_than_zero(self):
        """Bug 2 fix: On-chain balance should be > 0 for withdraw button to be enabled"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        on_chain_balance = data.get("on_chain_balance_sol", 0)
        assert on_chain_balance > 0.00001, f"On-chain balance {on_chain_balance} should be > 0.00001 for withdraw to be enabled"
        print(f"✅ On-chain balance {on_chain_balance} > 0.00001 - withdraw should be enabled")


class TestCustodialWalletInfoEndpoint:
    """Test /api/custodial-wallet/info/{wallet} returns balance_sol"""

    def test_custodial_wallet_info_returns_balance(self):
        """Verify custodial wallet info endpoint returns balance_sol > 0"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify balance_sol field exists and is > 0
        assert "balance_sol" in data, "Missing balance_sol field"
        assert data["balance_sol"] > 0, f"balance_sol should be > 0, got {data['balance_sol']}"
        
        # Verify wallet_address matches expected custodial wallet
        assert "wallet_address" in data
        assert data["wallet_address"] == CUSTODIAL_WALLET
        
        print(f"✅ balance_sol: {data['balance_sol']}")
        print(f"✅ wallet_address: {data['wallet_address']}")

    def test_custodial_wallet_info_has_required_fields(self):
        """Verify all required fields are present"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["wallet_address", "balance_sol", "balance_lamports", "total_deposits", "total_withdrawals"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"✅ All required fields present: {required_fields}")


class TestLedgerHistoryEndpoint:
    """Test /api/ledger/history/{wallet} - should be empty after cleanup"""

    def test_ledger_history_empty_after_cleanup(self):
        """Verify ledger history is empty (data was cleaned)"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert "count" in data
        assert data["count"] == 0, f"Expected 0 entries after cleanup, got {data['count']}"
        
        print(f"✅ Ledger history empty: {data['count']} entries")


class TestAllPagesLoad:
    """Test all pages load without errors"""

    @pytest.mark.parametrize("path,expected_status", [
        ("/", 200),
        ("/origins", 200),
        ("/journal", 200),
        ("/ai-trader", 200),
        ("/pugburn", 200),
        ("/game", 200),
    ])
    def test_page_loads(self, path, expected_status):
        """Verify each page returns 200"""
        response = requests.get(f"{BASE_URL}{path}", allow_redirects=True)
        assert response.status_code == expected_status, f"Page {path} returned {response.status_code}"
        print(f"✅ Page {path} loads - {response.status_code}")


class TestNoTestData:
    """Verify no TEST/RAKETEST data in positions or history"""

    def test_no_test_positions(self):
        """Verify no TEST/RAKETEST positions"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        positions = data.get("positions", [])
        test_positions = [p for p in positions if "TEST" in p.get("token_symbol", "").upper() or "RAKETEST" in p.get("token_symbol", "").upper()]
        assert len(test_positions) == 0, f"Found TEST/RAKETEST positions: {test_positions}"
        
        print(f"✅ No TEST/RAKETEST positions found ({len(positions)} total positions)")

    def test_no_test_history(self):
        """Verify no TEST/RAKETEST history entries"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        trades = data.get("trades", [])
        test_trades = [t for t in trades if "TEST" in t.get("token_symbol", "").upper() or "RAKETEST" in t.get("token_symbol", "").upper()]
        assert len(test_trades) == 0, f"Found TEST/RAKETEST trades: {test_trades}"
        
        print(f"✅ No TEST/RAKETEST history entries found ({len(trades)} total trades)")


class TestRakeStats:
    """Test rake stats endpoint"""

    def test_rake_stats_returns_correct_percent(self):
        """Verify rake_percent is 2.5"""
        response = requests.get(f"{BASE_URL}/api/ledger/rake-stats/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "rake_percent" in data
        assert data["rake_percent"] == 2.5
        
        print(f"✅ rake_percent: {data['rake_percent']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
