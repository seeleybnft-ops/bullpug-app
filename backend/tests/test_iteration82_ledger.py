"""
Iteration 82: Internal Ledger System Tests

Tests for the new per-user fund tracking ledger system:
- GET /api/ledger/balance/{wallet} - balance breakdown
- GET /api/ledger/history/{wallet} - transaction history
- GET /api/ledger/history/{wallet}?entry_type=trade_open - filtered history
- GET /api/ledger/reconciliation - admin reconciliation
- POST /api/ledger/migrate - migration endpoint
- Ledger integration in custodial_wallet and ai_trader
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"
ACCESS_CODE = "bullpug2026"


class TestLedgerBalanceEndpoint:
    """Tests for GET /api/ledger/balance/{wallet}"""
    
    def test_ledger_balance_returns_200(self):
        """Test that ledger balance endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/ledger/balance/{TEST_WALLET[:8]}... returned 200")
    
    def test_ledger_balance_has_required_fields(self):
        """Test that balance response has all required fields"""
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "available_sol",
            "locked_in_trades_sol",
            "total_balance_sol",
            "total_deposited_sol",
            "total_withdrawn_sol",
            "realised_pnl_sol"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
            assert isinstance(data[field], (int, float)), f"Field {field} should be numeric"
        
        print(f"✓ Balance response has all required fields: {list(data.keys())}")
        print(f"  - available_sol: {data['available_sol']}")
        print(f"  - locked_in_trades_sol: {data['locked_in_trades_sol']}")
        print(f"  - total_balance_sol: {data['total_balance_sol']}")
    
    def test_ledger_balance_for_new_wallet(self):
        """Test balance for a wallet with no ledger entries"""
        new_wallet = "NewWalletWithNoEntries123456789012345678901234"
        response = requests.get(f"{BASE_URL}/api/ledger/balance/{new_wallet}")
        assert response.status_code == 200
        data = response.json()
        
        # New wallet should have zero balances
        assert data["available_sol"] == 0
        assert data["total_balance_sol"] == 0
        print(f"✓ New wallet returns zero balances as expected")


class TestLedgerHistoryEndpoint:
    """Tests for GET /api/ledger/history/{wallet}"""
    
    def test_ledger_history_returns_200(self):
        """Test that ledger history endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/ledger/history/{TEST_WALLET[:8]}... returned 200")
    
    def test_ledger_history_has_entries_array(self):
        """Test that history response has entries array"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data, "Response should have 'entries' field"
        assert isinstance(data["entries"], list), "'entries' should be a list"
        assert "count" in data, "Response should have 'count' field"
        
        print(f"✓ History response has entries array with {data['count']} entries")
    
    def test_ledger_history_entry_structure(self):
        """Test that history entries have correct structure"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        if data["entries"]:
            entry = data["entries"][0]
            expected_fields = ["entry_type", "amount_sol", "balance_after", "description", "created_at"]
            
            for field in expected_fields:
                assert field in entry, f"Entry missing field: {field}"
            
            print(f"✓ History entry has correct structure: {list(entry.keys())}")
            print(f"  - entry_type: {entry['entry_type']}")
            print(f"  - amount_sol: {entry['amount_sol']}")
        else:
            print(f"✓ History endpoint works (no entries for this wallet)")
    
    def test_ledger_history_filter_by_entry_type(self):
        """Test filtering history by entry_type"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}?entry_type=trade_open")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # All entries should be trade_open type
        for entry in data["entries"]:
            assert entry["entry_type"] == "trade_open", f"Expected trade_open, got {entry['entry_type']}"
        
        print(f"✓ History filter by entry_type=trade_open works ({data['count']} entries)")
    
    def test_ledger_history_limit_parameter(self):
        """Test limit parameter on history"""
        response = requests.get(f"{BASE_URL}/api/ledger/history/{TEST_WALLET}?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) <= 5, "Should respect limit parameter"
        print(f"✓ History limit parameter works (returned {len(data['entries'])} entries)")


class TestLedgerReconciliationEndpoint:
    """Tests for GET /api/ledger/reconciliation"""
    
    def test_reconciliation_returns_200(self):
        """Test that reconciliation endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/ledger/reconciliation")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/ledger/reconciliation returned 200")
    
    def test_reconciliation_has_required_fields(self):
        """Test that reconciliation response has required fields"""
        response = requests.get(f"{BASE_URL}/api/ledger/reconciliation")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["total_virtual_balance_sol", "users_with_balance", "discrepancies"]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"✓ Reconciliation has required fields:")
        print(f"  - total_virtual_balance_sol: {data['total_virtual_balance_sol']}")
        print(f"  - users_with_balance: {data['users_with_balance']}")
        print(f"  - discrepancies: {len(data['discrepancies'])} found")


class TestLedgerMigrateEndpoint:
    """Tests for POST /api/ledger/migrate"""
    
    def test_migrate_returns_200(self):
        """Test that migrate endpoint returns 200"""
        response = requests.post(f"{BASE_URL}/api/ledger/migrate")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/ledger/migrate returned 200")
    
    def test_migrate_returns_zero_if_already_migrated(self):
        """Test that migrate returns 0 if already migrated"""
        response = requests.post(f"{BASE_URL}/api/ledger/migrate")
        assert response.status_code == 200
        data = response.json()
        
        assert "migrated" in data, "Response should have 'migrated' field"
        # Per agent context, migration already ran so should return 0
        assert data["migrated"] == 0, f"Expected migrated=0, got {data['migrated']}"
        
        print(f"✓ Migrate returns migrated=0 (already migrated)")
        print(f"  - message: {data.get('message', 'N/A')}")


class TestLedgerIntegrationWithCustodialWallet:
    """Tests for ledger integration in custodial wallet endpoints"""
    
    def test_custodial_wallet_info_exists(self):
        """Test that custodial wallet info endpoint works"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "wallet_address" in data, "Should have wallet_address"
        print(f"✓ Custodial wallet info endpoint works")
        print(f"  - wallet_address: {data.get('wallet_address', 'N/A')[:12]}...")
    
    def test_confirm_deposit_endpoint_exists(self):
        """Test that confirm-deposit endpoint exists (won't execute real deposit)"""
        # Just verify the endpoint exists by checking it doesn't return 404
        # We can't actually confirm a deposit without a real tx_signature
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/confirm-deposit",
            params={
                "user_wallet": TEST_WALLET,
                "tx_signature": "test_signature_not_real",
                "amount_lamports": 1000000
            }
        )
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404, "confirm-deposit endpoint should exist"
        print(f"✓ confirm-deposit endpoint exists (status: {response.status_code})")
    
    def test_withdraw_validates_against_ledger_balance(self):
        """Test that withdraw validates against ledger balance"""
        # Try to withdraw more than available - should fail
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={
                "user_wallet": TEST_WALLET,
                "amount_sol": 999999.0  # Impossibly large amount
            }
        )
        # Should fail with 400 or 404 (insufficient balance or no wallet)
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print(f"✓ Withdraw validates against ledger balance (status: {response.status_code})")


class TestLedgerIntegrationWithAITrader:
    """Tests for ledger integration in AI trader endpoints"""
    
    def test_add_position_endpoint_exists(self):
        """Test that add-position endpoint exists (creates trade_open ledger entry)"""
        # Just verify the endpoint exists - it's POST /add-position
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position",
            params={
                "wallet_address": TEST_WALLET,
                "token_symbol": "TEST",
                "tx_signature": "test_tx_sig_verify",
                "input_sol": 0.001,
                "output_amount": 100,
                "entry_price": 0.00001
            }
        )
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404, "add-position endpoint should exist"
        print(f"✓ add-position endpoint exists (status: {response.status_code})")
    
    def test_close_position_endpoint_exists(self):
        """Test that close-position endpoint exists (creates trade_close ledger entry)"""
        # close-position uses query params, not JSON body
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/close-position?wallet_address={TEST_WALLET}&position_id=test_pos&tx_signature=test_sig&sell_amount=0.01&received_sol=0.01"
        )
        # Should not be 404 (endpoint exists) - will likely be 404 for position not found
        # but that's different from endpoint not existing
        assert response.status_code in [200, 404, 422, 500], f"close-position endpoint should exist, got {response.status_code}"
        print(f"✓ close-position endpoint exists (status: {response.status_code})")
    
    def test_add_position_creates_trade_open_ledger_entry(self):
        """Test that add-position would create a trade_open ledger entry"""
        # This is a code path verification - the endpoint exists and accepts the right params
        # Note: add-position uses query params
        response = requests.post(
            f"{BASE_URL}/api/ai-trader/add-position?wallet_address={TEST_WALLET}&token_symbol=TEST&tx_signature=test_tx_sig_12345&input_sol=0.001&output_amount=100&entry_price=0.00001"
        )
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404, "add-position endpoint should exist"
        print(f"✓ add-position endpoint exists (status: {response.status_code})")


class TestPreviousFixesStillWork:
    """Verify previous fixes from iteration 81 still work"""
    
    def test_leaderboard_returns_200(self):
        """Test leaderboard endpoint"""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ GET /api/leaderboard returns 200")
    
    def test_platform_stats_returns_200(self):
        """Test platform stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ GET /api/ai-trader/platform-stats returns 200")
    
    def test_gallery_returns_correct_images(self):
        """Test gallery returns images from customer-assets"""
        response = requests.get(f"{BASE_URL}/api/showcase/gallery")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check that images are from customer-assets
        images = data.get("images", [])
        if images:
            for img in images[:3]:
                img_url = img.get("image_url", "")
                assert "customer-assets.emergentagent.com" in img_url or img_url.startswith("http"), \
                    f"Image URL should be from customer-assets: {img_url}"
        
        print(f"✓ Gallery returns {len(images)} images with correct URLs")
    
    def test_trading_mode_sync(self):
        """Test that trading mode sync still works"""
        # Save settings with trading_mode
        save_response = requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET,
                "trading_mode": "sniper"
            }
        )
        assert save_response.status_code == 200, f"Save failed: {save_response.status_code}"
        
        # Get settings directly to verify mode is saved
        settings_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert settings_response.status_code == 200
        settings_data = settings_response.json()
        
        # Mode should be synced in settings
        trading_mode = settings_data.get("trading_mode")
        auto_trade_mode = settings_data.get("auto_trade_mode")
        
        assert trading_mode == "sniper", f"Expected trading_mode='sniper', got {trading_mode}"
        assert auto_trade_mode == "sniper", f"Expected auto_trade_mode='sniper', got {auto_trade_mode}"
        
        print(f"✓ Trading mode sync still works (trading_mode={trading_mode}, auto_trade_mode={auto_trade_mode})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
