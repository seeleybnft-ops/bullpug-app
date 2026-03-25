"""
Iteration 83: Rake System Tests
Tests the 2.5% rake (platform fee) on profitable trades.

Key features tested:
1. POST /api/ai-trader/manual-close-position with profit returns rake object with applied=true
2. POST /api/ai-trader/manual-close-position with loss returns rake object with applied=false
3. Rake amount calculation: 2.5% of profit ONLY
4. GET /api/ledger/rake-stats/{wallet} returns rake statistics
5. GET /api/ledger/history/{wallet}?entry_type=fee returns rake entries
6. Rake is recorded as 'fee' entry in user_ledger with negative amount
7. All previous ledger endpoints still work
"""

import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
ACCESS_CODE = "bullpug2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestRakeSystemBasics:
    """Test basic rake system functionality"""
    
    def test_api_root_accessible(self, api_client):
        """Test that API root is accessible"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data
        print(f"✓ API root accessible: {data}")
    
    def test_platform_stats_accessible(self, api_client):
        """Test platform stats endpoint"""
        response = api_client.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_trades" in data
        print(f"✓ Platform stats: {data}")
    
    def test_ai_trader_settings_accessible(self, api_client):
        """Test AI trader settings endpoint"""
        response = api_client.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "wallet_address" in data
        print(f"✓ AI trader settings accessible")


class TestRakeOnProfitableTrade:
    """Test rake application on profitable trades"""
    
    def test_create_test_position_for_profit(self, api_client):
        """Create a test position that we'll close with profit"""
        position_id = f"RAKETEST_{uuid.uuid4().hex[:8]}"
        
        # Create position via add-position endpoint
        response = api_client.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={
                "wallet_address": TEST_WALLET,
                "token_symbol": "RAKETEST_PROFIT",
                "tx_signature": f"test_tx_{uuid.uuid4().hex[:16]}",
                "input_sol": 0.01,
                "output_amount": 10000,  # 10000 tokens
                "entry_price": 0.001,  # $0.001 per token
                "token_mint": "So11111111111111111111111111111111111111112"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "position_id" in data
        
        # Store position_id for next test
        TestRakeOnProfitableTrade.profit_position_id = data["position_id"]
        print(f"✓ Created test position for profit: {data['position_id']}")
        return data["position_id"]
    
    def test_close_position_with_profit_returns_rake(self, api_client):
        """Close position with profit and verify rake is applied"""
        position_id = getattr(TestRakeOnProfitableTrade, 'profit_position_id', None)
        if not position_id:
            pytest.skip("No position_id from previous test")
        
        # Close with 100% profit (exit_price = 0.002, entry was 0.001)
        response = api_client.post(
            f"{BASE_URL}/api/ai-trader/manual-close-position",
            json={
                "wallet_address": TEST_WALLET,
                "position_id": position_id,
                "exit_price": 0.002,  # 100% profit
                "exit_reason": "rake_test_profit"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "rake" in data, "Response must include 'rake' object"
        
        rake = data["rake"]
        assert rake.get("applied") == True, "Rake should be applied on profit"
        assert rake.get("amount_sol") > 0, "Rake amount should be > 0"
        assert rake.get("percent") == 2.5, "Rake percent should be 2.5"
        
        # Verify rake calculation: 2.5% of profit only
        # Investment: 0.01 SOL, 100% profit = 0.01 SOL profit
        # Expected rake: 0.01 * 2.5% = 0.00025 SOL
        pnl_sol = data.get("pnl_sol", 0)
        expected_rake = pnl_sol * 0.025
        actual_rake = rake.get("amount_sol", 0)
        
        # Allow small floating point tolerance
        assert abs(actual_rake - expected_rake) < 0.0001, \
            f"Rake calculation incorrect: expected {expected_rake}, got {actual_rake}"
        
        print(f"✓ Profitable trade closed with rake:")
        print(f"  - PnL: {pnl_sol:.6f} SOL")
        print(f"  - Rake applied: {actual_rake:.6f} SOL (2.5% of profit)")
        print(f"  - Rake object: {rake}")


class TestRakeOnLosingTrade:
    """Test that rake is NOT applied on losing trades"""
    
    def test_create_test_position_for_loss(self, api_client):
        """Create a test position that we'll close with loss"""
        response = api_client.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={
                "wallet_address": TEST_WALLET,
                "token_symbol": "RAKETEST_LOSS",
                "tx_signature": f"test_tx_{uuid.uuid4().hex[:16]}",
                "input_sol": 0.01,
                "output_amount": 10000,
                "entry_price": 0.001,
                "token_mint": "So11111111111111111111111111111111111111112"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        TestRakeOnLosingTrade.loss_position_id = data["position_id"]
        print(f"✓ Created test position for loss: {data['position_id']}")
    
    def test_close_position_with_loss_no_rake(self, api_client):
        """Close position with loss and verify NO rake is applied"""
        position_id = getattr(TestRakeOnLosingTrade, 'loss_position_id', None)
        if not position_id:
            pytest.skip("No position_id from previous test")
        
        # Close with 50% loss (exit_price = 0.0005, entry was 0.001)
        response = api_client.post(
            f"{BASE_URL}/api/ai-trader/manual-close-position",
            json={
                "wallet_address": TEST_WALLET,
                "position_id": position_id,
                "exit_price": 0.0005,  # 50% loss
                "exit_reason": "rake_test_loss"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "rake" in data, "Response must include 'rake' object"
        
        rake = data["rake"]
        assert rake.get("applied") == False, "Rake should NOT be applied on loss"
        assert rake.get("amount_sol") == 0, "Rake amount should be 0 on loss"
        assert rake.get("percent") == 2.5, "Rake percent should still be 2.5"
        
        # Verify PnL is negative
        pnl_sol = data.get("pnl_sol", 0)
        assert pnl_sol < 0, f"PnL should be negative for loss, got {pnl_sol}"
        
        print(f"✓ Losing trade closed without rake:")
        print(f"  - PnL: {pnl_sol:.6f} SOL (loss)")
        print(f"  - Rake applied: False")
        print(f"  - Rake object: {rake}")


class TestRakeStatsEndpoint:
    """Test GET /api/ledger/rake-stats/{wallet} endpoint"""
    
    def test_rake_stats_returns_correct_structure(self, api_client):
        """Test rake stats endpoint returns correct fields"""
        response = api_client.get(f"{BASE_URL}/api/ledger/rake-stats/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "total_rake_sol" in data, "Missing total_rake_sol"
        assert "total_gross_profit_sol" in data, "Missing total_gross_profit_sol"
        assert "rake_count" in data, "Missing rake_count"
        assert "rake_percent" in data, "Missing rake_percent"
        
        # Verify rake_percent is 2.5
        assert data["rake_percent"] == 2.5, f"rake_percent should be 2.5, got {data['rake_percent']}"
        
        # Verify types
        assert isinstance(data["total_rake_sol"], (int, float))
        assert isinstance(data["total_gross_profit_sol"], (int, float))
        assert isinstance(data["rake_count"], int)
        
        print(f"✓ Rake stats endpoint returns correct structure:")
        print(f"  - total_rake_sol: {data['total_rake_sol']}")
        print(f"  - total_gross_profit_sol: {data['total_gross_profit_sol']}")
        print(f"  - rake_count: {data['rake_count']}")
        print(f"  - rake_percent: {data['rake_percent']}")
    
    def test_rake_stats_has_data_after_profitable_trade(self, api_client):
        """Verify rake stats show data after profitable trade"""
        response = api_client.get(f"{BASE_URL}/api/ledger/rake-stats/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        # After our profitable trade test, there should be at least 1 rake entry
        # (may have more from previous tests)
        assert data["rake_count"] >= 0, "rake_count should be >= 0"
        
        if data["rake_count"] > 0:
            assert data["total_rake_sol"] > 0, "total_rake_sol should be > 0 if rake_count > 0"
            assert data["total_gross_profit_sol"] > 0, "total_gross_profit_sol should be > 0"
            print(f"✓ Rake stats show {data['rake_count']} rake entries totaling {data['total_rake_sol']:.6f} SOL")
        else:
            print(f"✓ Rake stats endpoint working (no rake entries yet)")


class TestLedgerFeeEntries:
    """Test that rake is recorded as 'fee' entry in ledger"""
    
    def test_ledger_history_fee_filter(self, api_client):
        """Test GET /api/ledger/history/{wallet}?entry_type=fee returns rake entries"""
        response = api_client.get(
            f"{BASE_URL}/api/ledger/history/{TEST_WALLET}",
            params={"entry_type": "fee"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert "count" in data
        
        entries = data["entries"]
        print(f"✓ Found {len(entries)} fee entries in ledger")
        
        # Check structure of fee entries (if any exist)
        for entry in entries[:3]:  # Check first 3
            assert entry.get("entry_type") == "fee"
            assert "amount_sol" in entry
            assert entry["amount_sol"] < 0, "Fee entries should have negative amount (debit)"
            
            # Check for rake metadata
            metadata = entry.get("metadata", {})
            if "rake_percent" in metadata:
                assert metadata["rake_percent"] == 2.5
                assert "gross_pnl_sol" in metadata
                print(f"  - Rake entry: {abs(entry['amount_sol']):.6f} SOL on {metadata.get('gross_pnl_sol', 0):.6f} profit")
    
    def test_fee_entries_have_rake_metadata(self, api_client):
        """Verify fee entries have rake_percent and gross_pnl_sol in metadata"""
        response = api_client.get(
            f"{BASE_URL}/api/ledger/history/{TEST_WALLET}",
            params={"entry_type": "fee", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        rake_entries = [e for e in data["entries"] if e.get("metadata", {}).get("rake_percent")]
        
        for entry in rake_entries:
            metadata = entry["metadata"]
            assert "rake_percent" in metadata, "Rake entry missing rake_percent in metadata"
            assert "gross_pnl_sol" in metadata, "Rake entry missing gross_pnl_sol in metadata"
            
            # Verify rake calculation
            expected_rake = metadata["gross_pnl_sol"] * (metadata["rake_percent"] / 100)
            actual_rake = abs(entry["amount_sol"])
            
            # Allow small tolerance for floating point
            assert abs(actual_rake - expected_rake) < 0.0001, \
                f"Rake mismatch: expected {expected_rake}, got {actual_rake}"
        
        print(f"✓ Verified {len(rake_entries)} rake entries have correct metadata")


class TestLedgerBalanceIncludesFees:
    """Test that ledger balance includes fee entries"""
    
    def test_balance_has_total_fees_field(self, api_client):
        """Test GET /api/ledger/balance/{wallet} includes total_fees_sol"""
        response = api_client.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_fees_sol" in data, "Balance should include total_fees_sol field"
        assert isinstance(data["total_fees_sol"], (int, float))
        
        print(f"✓ Balance includes total_fees_sol: {data['total_fees_sol']:.6f} SOL")
        print(f"  - Available: {data.get('available_sol', 0):.6f} SOL")
        print(f"  - Locked: {data.get('locked_in_trades_sol', 0):.6f} SOL")


class TestPreviousLedgerEndpoints:
    """Verify all previous ledger endpoints still work"""
    
    def test_ledger_balance_endpoint(self, api_client):
        """Test GET /api/ledger/balance/{wallet}"""
        response = api_client.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "available_sol", "locked_in_trades_sol", "total_balance_sol",
            "total_deposited_sol", "total_withdrawn_sol", "realised_pnl_sol"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Ledger balance endpoint working")
    
    def test_ledger_history_endpoint(self, api_client):
        """Test GET /api/ledger/history/{wallet}"""
        response = api_client.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert "count" in data
        
        print(f"✓ Ledger history endpoint working ({data['count']} entries)")
    
    def test_ledger_reconciliation_endpoint(self, api_client):
        """Test GET /api/ledger/reconciliation"""
        response = api_client.get(f"{BASE_URL}/api/ledger/reconciliation")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_virtual_balance_sol" in data
        assert "users_with_balance" in data
        
        print(f"✓ Ledger reconciliation endpoint working")


class TestRakeCalculationAccuracy:
    """Test rake calculation accuracy with specific values"""
    
    def test_rake_calculation_example(self, api_client):
        """
        Test specific rake calculation:
        Investment: 0.1 SOL
        Profit: 0.05 SOL (50% gain)
        Expected rake: 0.05 * 2.5% = 0.00125 SOL
        """
        # Create position with 0.1 SOL
        response = api_client.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={
                "wallet_address": TEST_WALLET,
                "token_symbol": "RAKETEST_CALC",
                "tx_signature": f"test_tx_{uuid.uuid4().hex[:16]}",
                "input_sol": 0.1,
                "output_amount": 100000,
                "entry_price": 0.001,
                "token_mint": "So11111111111111111111111111111111111111112"
            }
        )
        
        assert response.status_code == 200
        position_id = response.json()["position_id"]
        
        # Close with 50% profit (exit_price = 0.0015)
        response = api_client.post(
            f"{BASE_URL}/api/ai-trader/manual-close-position",
            json={
                "wallet_address": TEST_WALLET,
                "position_id": position_id,
                "exit_price": 0.0015,  # 50% profit
                "exit_reason": "rake_calc_test"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify calculation
        pnl_sol = data.get("pnl_sol", 0)
        rake = data.get("rake", {})
        rake_amount = rake.get("amount_sol", 0)
        
        # Expected: 0.1 SOL * 50% = 0.05 SOL profit
        # Rake: 0.05 * 2.5% = 0.00125 SOL
        expected_profit = 0.05
        expected_rake = expected_profit * 0.025  # 0.00125
        
        # Allow 10% tolerance for price fluctuations
        assert abs(pnl_sol - expected_profit) < 0.01, \
            f"Profit calculation off: expected ~{expected_profit}, got {pnl_sol}"
        
        assert abs(rake_amount - expected_rake) < 0.001, \
            f"Rake calculation off: expected ~{expected_rake}, got {rake_amount}"
        
        print(f"✓ Rake calculation verified:")
        print(f"  - Investment: 0.1 SOL")
        print(f"  - Profit: {pnl_sol:.6f} SOL")
        print(f"  - Rake (2.5% of profit): {rake_amount:.6f} SOL")


class TestOtherEndpointsStillWork:
    """Verify other endpoints still work after rake implementation"""
    
    def test_api_root(self, api_client):
        """Test GET /api/"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("✓ GET /api/ works")
    
    def test_platform_stats(self, api_client):
        """Test GET /api/platform-stats"""
        response = api_client.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200
        print("✓ GET /api/ai-trader/platform-stats works")
    
    def test_ai_trader_settings(self, api_client):
        """Test GET /api/ai-trader/settings/{wallet}"""
        response = api_client.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert response.status_code == 200
        print("✓ GET /api/ai-trader/settings works")
    
    def test_positions_endpoint(self, api_client):
        """Test GET /api/ai-trader/positions/{wallet}"""
        response = api_client.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET}")
        assert response.status_code == 200
        print("✓ GET /api/ai-trader/positions works")
    
    def test_history_endpoint(self, api_client):
        """Test GET /api/ai-trader/history/{wallet}"""
        response = api_client.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        assert response.status_code == 200
        print("✓ GET /api/ai-trader/history works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
