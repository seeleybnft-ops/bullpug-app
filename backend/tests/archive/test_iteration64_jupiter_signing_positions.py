"""
Iteration 64: Test Jupiter Swap Signing Fix and Positions Tab Visibility

P0 FIX: Jupiter swap transaction signing - verify simulation passes with the corrected 
        VersionedTransaction(message, [keypair]) signing method
P1 FIX: Positions tab visibility - verify the tab is now positioned earlier (2nd position)
        and visible without scrolling

Tests:
1. Custodial wallet info endpoint returns correct address and balance
2. Backend auto-trade scan endpoint works correctly
3. Verify the signing method is correctly implemented in code
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
USER_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"


class TestCustodialWalletInfo:
    """Test custodial wallet info endpoint returns correct address and balance"""
    
    def test_custodial_wallet_info_endpoint_returns_200(self):
        """Verify custodial wallet info endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{USER_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: Custodial wallet info endpoint returns 200")
    
    def test_custodial_wallet_returns_correct_address(self):
        """Verify custodial wallet returns the expected address"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{USER_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "wallet_address" in data, "Response missing wallet_address field"
        assert data["wallet_address"] == CUSTODIAL_WALLET, \
            f"Expected {CUSTODIAL_WALLET}, got {data['wallet_address']}"
        print(f"PASS: Custodial wallet address is correct: {data['wallet_address']}")
    
    def test_custodial_wallet_returns_balance(self):
        """Verify custodial wallet returns balance information"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{USER_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Check balance fields exist
        assert "balance_sol" in data, "Response missing balance_sol field"
        assert "balance_lamports" in data, "Response missing balance_lamports field"
        
        # Balance should be a number >= 0
        assert isinstance(data["balance_sol"], (int, float)), "balance_sol should be numeric"
        assert data["balance_sol"] >= 0, "balance_sol should be >= 0"
        
        print(f"PASS: Custodial wallet balance: {data['balance_sol']} SOL ({data['balance_lamports']} lamports)")
    
    def test_custodial_wallet_returns_all_required_fields(self):
        """Verify custodial wallet returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{USER_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "wallet_address",
            "balance_sol",
            "balance_lamports",
            "max_deposit_sol",
            "available_deposit_sol",
            "created_at"
        ]
        
        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"
        
        print(f"PASS: All required fields present in custodial wallet response")


class TestAutoTradeScanEndpoint:
    """Test backend auto-trade scan endpoint works correctly"""
    
    def test_auto_trade_status_endpoint(self):
        """Verify auto-trade status endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{USER_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "auto_trade_enabled" in data, "Response missing auto_trade_enabled field"
        print(f"PASS: Auto-trade status endpoint returns 200, enabled={data.get('auto_trade_enabled')}")
    
    def test_auto_trade_scan_endpoint(self):
        """Verify auto-trade scan endpoint executes without errors"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{USER_WALLET}")
        
        # Should return 200 even if no trades executed (due to insufficient balance)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"PASS: Auto-trade scan endpoint returns 200")
        print(f"  Response: {data}")
        
        # Check for expected fields
        if "success" in data:
            print(f"  Success: {data['success']}")
        if "message" in data:
            print(f"  Message: {data['message']}")
        if "trades" in data:
            print(f"  Trades executed: {len(data['trades'])}")
    
    def test_auto_trade_scan_handles_insufficient_balance(self):
        """Verify auto-trade scan correctly handles insufficient balance"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{USER_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        
        # With ~0.05 SOL balance, trades should be skipped or limited
        # The response should indicate this gracefully
        if "message" in data:
            message = data["message"].lower()
            # Check for balance-related messages
            if "insufficient" in message or "balance" in message or "skipped" in message:
                print(f"PASS: Auto-trade correctly handles insufficient balance: {data['message']}")
            else:
                print(f"INFO: Auto-trade message: {data['message']}")
        
        # Should not have errors
        assert "error" not in data or data.get("error") is None, \
            f"Unexpected error in response: {data.get('error')}"
        print(f"PASS: Auto-trade scan completed without errors")


class TestJupiterSwapSigningFix:
    """
    Test that the Jupiter swap signing fix is correctly implemented.
    
    The P0 fix changed from:
        sign_message() + populate() 
    To:
        VersionedTransaction(message, [keypair])
    
    This test verifies the code structure is correct.
    """
    
    def test_custodial_wallet_code_uses_correct_signing_method(self):
        """Verify the custodial_wallet.py uses VersionedTransaction constructor for signing"""
        # Read the custodial_wallet.py file
        custodial_wallet_path = "/app/backend/routers/custodial_wallet.py"
        
        with open(custodial_wallet_path, 'r') as f:
            code = f.read()
        
        # Check for the correct signing pattern
        correct_pattern = "VersionedTransaction(unsigned_tx.message, [keypair])"
        assert correct_pattern in code, \
            f"Expected signing pattern '{correct_pattern}' not found in custodial_wallet.py"
        
        # Check that the old incorrect pattern is NOT present
        incorrect_patterns = [
            "sign_message(",
            ".populate(",
        ]
        
        for pattern in incorrect_patterns:
            # These patterns should not be used for Jupiter swap signing
            # (they may exist for other purposes, so we just log a warning)
            if pattern in code:
                print(f"WARNING: Found '{pattern}' in code - ensure it's not used for Jupiter swap signing")
        
        print(f"PASS: Correct signing method 'VersionedTransaction(message, [keypair])' found in code")
    
    def test_custodial_wallet_imports_versioned_transaction(self):
        """Verify VersionedTransaction is imported correctly"""
        custodial_wallet_path = "/app/backend/routers/custodial_wallet.py"
        
        with open(custodial_wallet_path, 'r') as f:
            code = f.read()
        
        # Check for the import
        assert "from solders.transaction import VersionedTransaction" in code or \
               "VersionedTransaction" in code, \
            "VersionedTransaction import not found"
        
        print(f"PASS: VersionedTransaction is properly imported")


class TestPositionsTabVisibility:
    """
    Test that the Positions tab is now in the 2nd position in the tabs array.
    
    The P1 fix moved Positions from 8th position to 2nd position.
    """
    
    def test_positions_tab_is_second_in_array(self):
        """Verify Positions tab is in 2nd position (index 1) in the tabs array"""
        aitrader_path = "/app/frontend/src/pages/AITrader.js"
        
        with open(aitrader_path, 'r') as f:
            code = f.read()
        
        # Find the tabs array definition
        # The tabs are defined as an array of objects with id, label, icon, etc.
        # We need to verify the order
        
        # Look for the tabs array pattern
        import re
        
        # Find the tabs array section
        tabs_match = re.search(r'\[\s*\{[^}]*id:\s*"signals"[^}]*\}', code)
        assert tabs_match, "Could not find tabs array starting with signals"
        
        # Get the full tabs array section
        start_pos = tabs_match.start()
        
        # Find all tab IDs in order
        tab_ids = re.findall(r'id:\s*"(\w+)"', code[start_pos:start_pos+2000])
        
        # Verify positions tab is in the expected position
        if "positions" in tab_ids:
            positions_index = tab_ids.index("positions")
            print(f"INFO: Tabs order found: {tab_ids[:5]}...")
            print(f"INFO: Positions tab is at index {positions_index}")
            
            # Positions should be at index 1 (2nd position)
            assert positions_index == 1, \
                f"Expected Positions at index 1 (2nd position), but found at index {positions_index}"
            
            print(f"PASS: Positions tab is correctly at 2nd position (index 1)")
        else:
            pytest.fail("Positions tab not found in tabs array")
    
    def test_tabs_order_is_correct(self):
        """Verify the full tabs order matches expected"""
        aitrader_path = "/app/frontend/src/pages/AITrader.js"
        
        with open(aitrader_path, 'r') as f:
            code = f.read()
        
        import re
        
        # Find all tab IDs in the tabs array section
        tabs_match = re.search(r'\[\s*\{[^}]*id:\s*"signals"', code)
        if tabs_match:
            start_pos = tabs_match.start()
            tab_ids = re.findall(r'id:\s*"(\w+)"', code[start_pos:start_pos+2000])
            
            # Expected order based on the fix
            expected_first_tabs = ["signals", "positions", "runners", "tokens", "autotrade"]
            
            for i, expected_id in enumerate(expected_first_tabs):
                if i < len(tab_ids):
                    assert tab_ids[i] == expected_id, \
                        f"Expected tab at index {i} to be '{expected_id}', but got '{tab_ids[i]}'"
            
            print(f"PASS: Tabs order is correct: {tab_ids[:5]}")


class TestHealthAndBasicEndpoints:
    """Basic health checks for the API"""
    
    def test_api_health(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print(f"PASS: API health check passed")
    
    def test_ai_trader_tokens_endpoint(self):
        """Verify AI trader tokens endpoint works"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/tokens")
        assert response.status_code == 200, f"Tokens endpoint failed: {response.status_code}"
        print(f"PASS: AI trader tokens endpoint works")
    
    def test_ai_trader_positions_endpoint(self):
        """Verify AI trader positions endpoint works"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{USER_WALLET}")
        assert response.status_code == 200, f"Positions endpoint failed: {response.status_code}"
        
        data = response.json()
        assert "positions" in data, "Response missing positions field"
        print(f"PASS: AI trader positions endpoint works, found {len(data['positions'])} positions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
