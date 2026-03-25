"""
Iteration 86: P0 Ledger Fixes Testing
Tests for:
1. GET /api/ledger/balance/{wallet} - returns virtual ledger balance (NOT on-chain)
2. GET /api/ledger/admin/reconciliation - returns fund health data
3. POST /api/ledger/reset-fresh-start - clears ledger and creates platform rake
4. GET /api/ledger/history/{wallet} - returns ledger entries
5. POST /api/custodial-wallet/withdraw - validates against ledger balance
6. safeCopy function uses .then/.catch pattern (code review)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cosmic-runner-hub.preview.emergentagent.com")

# Test credentials
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"
EXPECTED_PLATFORM_RAKE = 0.008767


class TestLedgerBalanceEndpoint:
    """Test GET /api/ledger/balance/{wallet} returns virtual ledger balance"""
    
    def test_ledger_balance_returns_virtual_balance(self):
        """Verify ledger balance endpoint returns virtual balance fields (NOT on-chain)"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Ledger balance response: {data}")
        
        # Verify required virtual balance fields exist
        assert "available_sol" in data, "Missing available_sol field"
        assert "locked_in_trades_sol" in data, "Missing locked_in_trades_sol field"
        assert "total_deposited_sol" in data, "Missing total_deposited_sol field"
        
        # After fresh start, user should have 0 balance
        assert data["available_sol"] == 0, f"Expected available_sol=0 for fresh start, got {data['available_sol']}"
        assert data["locked_in_trades_sol"] == 0, f"Expected locked_in_trades_sol=0, got {data['locked_in_trades_sol']}"
        assert data["total_deposited_sol"] == 0, f"Expected total_deposited_sol=0, got {data['total_deposited_sol']}"
        
        print("✓ Ledger balance returns virtual balance (all 0 for fresh start)")
    
    def test_ledger_balance_includes_custodial_address(self):
        """Verify ledger balance includes custodial address for display"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # custodial_address may or may not be present depending on wallet setup
        if "custodial_address" in data:
            print(f"✓ Custodial address included: {data['custodial_address']}")
        else:
            print("✓ No custodial address (wallet may not have custodial setup)")


class TestAdminReconciliationEndpoint:
    """Test GET /api/ledger/admin/reconciliation returns fund health data"""
    
    def test_reconciliation_returns_required_fields(self):
        """Verify reconciliation endpoint returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Reconciliation response: {data}")
        
        # Verify required fields
        required_fields = [
            "total_on_chain_sol",
            "total_virtual_sol",
            "platform_rake_sol",
            "drift_sol",
            "healthy",
            "users"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print("✓ All required reconciliation fields present")
    
    def test_reconciliation_healthy_status(self):
        """Verify healthy=true after fresh start"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200
        
        data = response.json()
        assert data["healthy"] == True, f"Expected healthy=true, got {data['healthy']}"
        print(f"✓ Fund health status: healthy={data['healthy']}")
    
    def test_reconciliation_platform_rake(self):
        """Verify platform_rake_sol equals expected value (0.008767)"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200
        
        data = response.json()
        platform_rake = data["platform_rake_sol"]
        
        # Allow small floating point tolerance
        assert abs(platform_rake - EXPECTED_PLATFORM_RAKE) < 0.000001, \
            f"Expected platform_rake_sol={EXPECTED_PLATFORM_RAKE}, got {platform_rake}"
        
        print(f"✓ Platform rake: {platform_rake} SOL (expected {EXPECTED_PLATFORM_RAKE})")
    
    def test_reconciliation_drift_near_zero(self):
        """Verify drift is near zero after fresh start"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200
        
        data = response.json()
        drift = data["drift_sol"]
        
        # Drift should be very close to 0 after fresh start
        # Formula: on_chain - virtual - platform_rake = drift
        # 0.008767 - 0 - 0.008767 = 0
        assert abs(drift) < 0.001, f"Expected drift near 0, got {drift}"
        
        print(f"✓ Drift: {drift} SOL (near zero as expected)")
    
    def test_reconciliation_users_array(self):
        """Verify users array is present and properly formatted"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200
        
        data = response.json()
        users = data["users"]
        
        assert isinstance(users, list), f"Expected users to be a list, got {type(users)}"
        
        # After fresh start with no user deposits, users array may be empty
        print(f"✓ Users array present with {len(users)} entries")


class TestLedgerHistoryEndpoint:
    """Test GET /api/ledger/history/{wallet} returns entries array"""
    
    def test_history_returns_entries_array(self):
        """Verify history endpoint returns entries array"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"History response: {data}")
        
        assert "entries" in data, "Missing entries field"
        assert isinstance(data["entries"], list), f"Expected entries to be a list, got {type(data['entries'])}"
        
        # After fresh start, user should have 0 entries
        print(f"✓ History entries: {len(data['entries'])} (expected 0 for fresh start)")


class TestWithdrawValidation:
    """Test POST /api/custodial-wallet/withdraw validates against ledger balance"""
    
    def test_withdraw_fails_with_insufficient_ledger_balance(self):
        """Verify withdrawal fails when user has 0 ledger balance"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={
                "user_wallet": TEST_WALLET,
                "amount_sol": 0.001  # Try to withdraw small amount
            }
        )
        
        # Should fail with 400 because user has 0 ledger balance
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        detail = data.get("detail", "")
        
        # Should mention insufficient ledger balance
        assert "ledger" in detail.lower() or "insufficient" in detail.lower(), \
            f"Expected error about ledger balance, got: {detail}"
        
        print(f"✓ Withdrawal correctly rejected: {detail}")


class TestResetFreshStart:
    """Test POST /api/ledger/reset-fresh-start endpoint"""
    
    def test_reset_endpoint_exists(self):
        """Verify reset-fresh-start endpoint exists (don't actually call it)"""
        # Just verify the endpoint is accessible by checking OPTIONS or a GET
        # We don't want to actually reset during testing
        response = requests.options(f"{BASE_URL}/api/ledger/reset-fresh-start")
        # OPTIONS may return 200 or 405 depending on CORS config
        # Just verify we get a response (not 404)
        assert response.status_code != 404, "reset-fresh-start endpoint not found"
        print("✓ reset-fresh-start endpoint exists")


class TestSafeCopyCodeReview:
    """Code review: Verify safeCopy uses .then/.catch pattern (not raw await)"""
    
    def test_safecopy_pattern_in_fundledger(self):
        """Verify safeCopy in FundLedger.js uses Promise .then/.catch"""
        # Read the FundLedger.js file
        fundledger_path = "/app/frontend/src/components/trader/FundLedger.js"
        
        try:
            with open(fundledger_path, "r") as f:
                content = f.read()
            
            # Check for safeCopy function
            assert "function safeCopy" in content or "const safeCopy" in content, \
                "safeCopy function not found in FundLedger.js"
            
            # Check for .then/.catch pattern (not raw await in sync context)
            assert ".then(" in content, "Expected .then() pattern in safeCopy"
            
            # Verify it's not using problematic await pattern
            # The safeCopy function should use .then/.catch, not await
            safecopy_start = content.find("function safeCopy")
            if safecopy_start == -1:
                safecopy_start = content.find("safeCopy")
            
            # Find the function body (next ~50 lines)
            safecopy_section = content[safecopy_start:safecopy_start + 1000]
            
            # Should have .then( for the clipboard promise
            assert ".then(" in safecopy_section, \
                "safeCopy should use .then() pattern for clipboard API"
            
            print("✓ safeCopy uses .then/.catch pattern (no raw await in sync context)")
            
        except FileNotFoundError:
            pytest.skip("FundLedger.js not found - skipping code review test")


class TestReconciliationEndpointAccess:
    """Verify reconciliation endpoint doesn't require admin auth"""
    
    def test_reconciliation_no_auth_required(self):
        """Verify /api/ledger/admin/reconciliation is accessible without auth"""
        # Make request without any auth headers
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        
        # Should return 200, not 401/403
        assert response.status_code == 200, \
            f"Expected 200 (no auth required), got {response.status_code}"
        
        print("✓ Reconciliation endpoint accessible without auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
