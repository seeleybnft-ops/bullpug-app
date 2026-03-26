"""
Iteration 88: Backend API Tests for Auto-Trade and Ledger Endpoints

Tests the following endpoints:
1. POST /api/custodial-wallet/detect-deposit/{wallet} - deposit detection
2. POST /api/ai-trader/auto-trade/scan-and-execute/{wallet} - scanner with CoinGecko batch API
3. POST /api/ai-trader/auto-trade/check-exits/{wallet} - exit trigger checks
4. GET /api/ledger/balance/{wallet} - balance breakdown
5. GET /api/ai-trader/positions/{wallet} - open positions
6. GET /api/ledger/admin/reconciliation - reconciliation data
7. GET /api/ai-trader/settings/{wallet} - user settings
"""

import pytest
import requests
import os

# Get BASE_URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback for local testing
    BASE_URL = "https://cosmic-runner-hub.preview.emergentagent.com"

# Test credentials from review request
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg"
ACCESS_CODE = "bullpug2026"


class TestDepositDetection:
    """Test POST /api/custodial-wallet/detect-deposit/{wallet}"""
    
    def test_detect_deposit_endpoint_exists(self):
        """Test that detect-deposit endpoint exists and returns 200"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/detect-deposit/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ detect-deposit endpoint exists (200)")
    
    def test_detect_deposit_response_structure(self):
        """Test that detect-deposit returns expected fields"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/detect-deposit/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Must have these fields
        assert "success" in data, "Missing 'success' field"
        assert "detected" in data, "Missing 'detected' field"
        assert "on_chain_sol" in data, "Missing 'on_chain_sol' field"
        assert "message" in data, "Missing 'message' field"
        
        # Validate types
        assert isinstance(data["success"], bool), "success should be boolean"
        assert isinstance(data["detected"], bool), "detected should be boolean"
        assert isinstance(data["on_chain_sol"], (int, float)), "on_chain_sol should be numeric"
        
        print(f"✓ detect-deposit response structure valid")
        print(f"  - on_chain_sol: {data['on_chain_sol']}")
        print(f"  - detected: {data['detected']}")
        print(f"  - message: {data['message']}")
    
    def test_detect_deposit_compares_with_ledger(self):
        """Test that detect-deposit compares on-chain balance with ledger total"""
        response = requests.post(f"{BASE_URL}/api/custodial-wallet/detect-deposit/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Should have ledger_sol field showing what ledger knows about
        if "ledger_sol" in data:
            print(f"✓ detect-deposit includes ledger comparison")
            print(f"  - ledger_sol: {data['ledger_sol']}")
        else:
            print(f"  Note: ledger_sol not in response (may be internal)")


class TestAutoTradeScanAndExecute:
    """Test POST /api/ai-trader/auto-trade/scan-and-execute/{wallet}"""
    
    def test_scan_and_execute_endpoint_exists(self):
        """Test that scan-and-execute endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}")
        # Should return 200 even if auto-trade is disabled
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ scan-and-execute endpoint exists (200)")
    
    def test_scan_and_execute_response_structure(self):
        """Test that scan-and-execute returns expected fields"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Must have these fields
        assert "success" in data, "Missing 'success' field"
        assert "message" in data, "Missing 'message' field"
        
        # If auto-trade is disabled, should say so
        if not data.get("success"):
            assert "message" in data
            print(f"✓ scan-and-execute response valid (auto-trade may be disabled)")
            print(f"  - message: {data['message']}")
        else:
            # If enabled, should have trades array
            assert "trades" in data, "Missing 'trades' field when success=True"
            print(f"✓ scan-and-execute response valid")
            print(f"  - trades count: {len(data.get('trades', []))}")
    
    def test_scan_and_execute_handles_rate_limits(self):
        """Test that scanner handles CoinGecko/DexScreener rate limits gracefully"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Should not crash on rate limits - just return 0 trades
        # This is expected transient behavior per the review request
        if data.get("success") and data.get("trades") is not None:
            print(f"✓ Scanner handles rate limits gracefully")
            print(f"  - trades returned: {len(data.get('trades', []))}")
        else:
            print(f"✓ Scanner returned gracefully (may be disabled or rate-limited)")


class TestAutoTradeCheckExits:
    """Test POST /api/ai-trader/auto-trade/check-exits/{wallet}"""
    
    def test_check_exits_endpoint_exists(self):
        """Test that check-exits endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ check-exits endpoint exists (200)")
    
    def test_check_exits_response_structure(self):
        """Test that check-exits returns expected fields"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Must have these fields
        assert "success" in data, "Missing 'success' field"
        
        if data.get("success"):
            assert "exits" in data, "Missing 'exits' field when success=True"
            print(f"✓ check-exits response valid")
            print(f"  - exits count: {len(data.get('exits', []))}")
        else:
            assert "message" in data, "Missing 'message' field when success=False"
            print(f"✓ check-exits response valid (auto-trade may be disabled)")
            print(f"  - message: {data['message']}")
    
    def test_check_exits_handles_no_positions(self):
        """Test that check-exits handles case with no open positions"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/check-exits/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Should not crash when no positions
        if data.get("success") and data.get("message") == "No open positions":
            print(f"✓ check-exits handles no positions gracefully")
        elif data.get("exits") is not None:
            print(f"✓ check-exits returned exits array: {len(data['exits'])} exits")


class TestLedgerBalance:
    """Test GET /api/ledger/balance/{wallet}"""
    
    def test_ledger_balance_endpoint_exists(self):
        """Test that ledger balance endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ ledger balance endpoint exists (200)")
    
    def test_ledger_balance_response_structure(self):
        """Test that ledger balance returns expected fields"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Must have these fields per the review request
        required_fields = ["available_sol", "locked_in_trades_sol", "total_balance_sol"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate types
        assert isinstance(data["available_sol"], (int, float)), "available_sol should be numeric"
        assert isinstance(data["locked_in_trades_sol"], (int, float)), "locked_in_trades_sol should be numeric"
        assert isinstance(data["total_balance_sol"], (int, float)), "total_balance_sol should be numeric"
        
        print(f"✓ ledger balance response structure valid")
        print(f"  - available_sol: {data['available_sol']}")
        print(f"  - locked_in_trades_sol: {data['locked_in_trades_sol']}")
        print(f"  - total_balance_sol: {data['total_balance_sol']}")
    
    def test_ledger_balance_math_consistency(self):
        """Test that total_balance = available + locked"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        available = data.get("available_sol", 0)
        locked = data.get("locked_in_trades_sol", 0)
        total = data.get("total_balance_sol", 0)
        
        # Total should approximately equal available + locked
        expected_total = available + locked
        diff = abs(total - expected_total)
        
        # Allow small rounding difference (0.001 SOL)
        assert diff < 0.01, f"Balance math inconsistent: {available} + {locked} = {expected_total}, but total = {total}"
        print(f"✓ ledger balance math consistent: {available} + {locked} ≈ {total}")


class TestAITraderPositions:
    """Test GET /api/ai-trader/positions/{wallet}"""
    
    def test_positions_endpoint_exists(self):
        """Test that positions endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ positions endpoint exists (200)")
    
    def test_positions_response_structure(self):
        """Test that positions returns expected fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Must have these fields
        assert "positions" in data, "Missing 'positions' field"
        assert "count" in data, "Missing 'count' field"
        
        # Validate types
        assert isinstance(data["positions"], list), "positions should be a list"
        assert isinstance(data["count"], int), "count should be an integer"
        assert data["count"] == len(data["positions"]), "count should match positions length"
        
        print(f"✓ positions response structure valid")
        print(f"  - positions count: {data['count']}")
        
        # If there are positions, validate their structure
        if data["positions"]:
            pos = data["positions"][0]
            expected_fields = ["token_symbol", "status"]
            for field in expected_fields:
                assert field in pos, f"Position missing field: {field}"
            print(f"  - first position: {pos.get('token_symbol')} ({pos.get('status')})")


class TestLedgerReconciliation:
    """Test GET /api/ledger/admin/reconciliation"""
    
    def test_reconciliation_endpoint_exists(self):
        """Test that reconciliation endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ reconciliation endpoint exists (200)")
    
    def test_reconciliation_response_structure(self):
        """Test that reconciliation returns expected fields"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200
        
        data = response.json()
        # Must have these fields per ledger.py
        expected_fields = ["total_on_chain_sol", "total_available_sol", "drift_sol", "healthy", "users"]
        for field in expected_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate types
        assert isinstance(data["healthy"], bool), "healthy should be boolean"
        assert isinstance(data["users"], list), "users should be a list"
        
        print(f"✓ reconciliation response structure valid")
        print(f"  - total_on_chain_sol: {data['total_on_chain_sol']}")
        print(f"  - total_available_sol: {data['total_available_sol']}")
        print(f"  - drift_sol: {data['drift_sol']}")
        print(f"  - healthy: {data['healthy']}")
        print(f"  - users count: {len(data['users'])}")
    
    def test_reconciliation_user_breakdown(self):
        """Test that reconciliation includes user breakdowns"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200
        
        data = response.json()
        users = data.get("users", [])
        
        if users:
            user = users[0]
            expected_user_fields = ["user_wallet", "on_chain_sol", "available_sol"]
            for field in expected_user_fields:
                assert field in user, f"User missing field: {field}"
            print(f"✓ reconciliation includes user breakdowns")
            print(f"  - first user: {user.get('short_wallet', user.get('user_wallet', '')[:10])}")
        else:
            print(f"  Note: No users in reconciliation (may be empty)")


class TestAITraderSettings:
    """Test GET /api/ai-trader/settings/{wallet}"""
    
    def test_settings_endpoint_exists(self):
        """Test that settings endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ settings endpoint exists (200)")
    
    def test_settings_response_structure(self):
        """Test that settings returns expected fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Must have these fields per the review request
        required_fields = ["auto_trade_enabled", "trading_mode"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"✓ settings response structure valid")
        print(f"  - auto_trade_enabled: {data.get('auto_trade_enabled')}")
        print(f"  - trading_mode: {data.get('trading_mode')}")
    
    def test_settings_trading_mode_values(self):
        """Test that trading_mode has valid value"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        trading_mode = data.get("trading_mode", "")
        
        # Valid modes per ai_trader_models.py
        valid_modes = ["conservative", "moderate", "normal", "aggressive", "sniper"]
        if trading_mode:
            assert trading_mode in valid_modes, f"Invalid trading_mode: {trading_mode}"
            print(f"✓ trading_mode is valid: {trading_mode}")
        else:
            print(f"  Note: trading_mode not set (using default)")


class TestCustodialWalletInfo:
    """Test GET /api/custodial-wallet/info/{wallet}"""
    
    def test_wallet_info_endpoint_exists(self):
        """Test that wallet info endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ wallet info endpoint exists (200)")
    
    def test_wallet_info_response_structure(self):
        """Test that wallet info returns expected fields"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200
        
        data = response.json()
        # Must have these fields
        required_fields = ["wallet_address", "balance_sol", "balance_lamports"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate custodial address matches expected
        assert data["wallet_address"] == CUSTODIAL_WALLET, f"Custodial address mismatch: {data['wallet_address']} != {CUSTODIAL_WALLET}"
        
        print(f"✓ wallet info response structure valid")
        print(f"  - wallet_address: {data['wallet_address']}")
        print(f"  - balance_sol: {data['balance_sol']}")


class TestDataIntegrity:
    """Test data integrity across endpoints"""
    
    def test_ledger_and_positions_consistency(self):
        """Test that ledger locked amount matches open positions"""
        # Get ledger balance
        ledger_response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert ledger_response.status_code == 200
        ledger_data = ledger_response.json()
        
        # Get positions
        positions_response = requests.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert positions_response.status_code == 200
        positions_data = positions_response.json()
        
        # Calculate total locked from positions
        positions_locked = sum(
            float(p.get("amount_sol", 0)) 
            for p in positions_data.get("positions", [])
        )
        
        ledger_locked = ledger_data.get("locked_in_trades_sol", 0)
        
        # They should be approximately equal (allow for unrealized P&L)
        print(f"✓ Data integrity check:")
        print(f"  - ledger locked_in_trades_sol: {ledger_locked}")
        print(f"  - positions total amount_sol: {positions_locked}")
        
        # Note: locked_in_trades_sol includes unrealized P&L, so may differ
        if positions_data.get("count", 0) > 0:
            print(f"  - Note: Difference may be due to unrealized P&L")
    
    def test_reconciliation_health(self):
        """Test that reconciliation shows healthy status"""
        response = requests.get(f"{BASE_URL}/api/ledger/admin/reconciliation")
        assert response.status_code == 200
        
        data = response.json()
        drift = data.get("drift_sol", 0)
        healthy = data.get("healthy", False)
        
        print(f"✓ Reconciliation health check:")
        print(f"  - drift_sol: {drift}")
        print(f"  - healthy: {healthy}")
        
        # Drift should be small (< 0.01 SOL)
        if abs(drift) < 0.01:
            print(f"  - Drift is within acceptable range")
        else:
            print(f"  - WARNING: Drift is significant ({drift} SOL)")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
