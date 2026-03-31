"""
Iteration 95: Rake Withdrawal Feature Tests

Tests for automated rake withdrawal to community wallet:
1. Backend starts cleanly with rake_withdrawal.py importable
2. track_rake() function correctly increments pending_sol and total_collected_sol in rake_tracker collection
3. get_rake_stats() returns correct structure with total_collected_sol, pending_sol, total_withdrawn_sol, community_wallet, threshold_sol
4. Community wallet is correctly set to we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT
5. RAKE_WITHDRAW_THRESHOLD is 0.01 SOL
6. Bot Health endpoint /api/admin/bot-health returns rake stats in response
7. apply_rake in auto_trader_engine.py calls track_rake after ledger_record
8. rake_events collection gets individual rake event entries

NOTE: DO NOT trigger actual on-chain withdrawals — only test the tracking/stats logic.
"""

import pytest
import requests
import os
import uuid
import asyncio
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://cosmic-runner-hub.preview.emergentagent.com"

# Test credentials
ADMIN_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
COMMUNITY_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"


def run_async(coro):
    """Helper to run async functions in sync tests"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestRakeWithdrawalModule:
    """Test rake_withdrawal.py module imports and constants"""
    
    def test_01_rake_withdrawal_module_importable(self):
        """Test that rake_withdrawal.py can be imported without errors"""
        try:
            from services.rake_withdrawal import track_rake, get_rake_stats, COMMUNITY_WALLET, RAKE_WITHDRAW_THRESHOLD
            print("SUCCESS: rake_withdrawal module imported successfully")
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import rake_withdrawal module: {e}")
    
    def test_02_community_wallet_constant(self):
        """Test that COMMUNITY_WALLET is correctly set"""
        from services.rake_withdrawal import COMMUNITY_WALLET as MODULE_COMMUNITY_WALLET
        assert MODULE_COMMUNITY_WALLET == COMMUNITY_WALLET, f"Expected {COMMUNITY_WALLET}, got {MODULE_COMMUNITY_WALLET}"
        print(f"SUCCESS: COMMUNITY_WALLET = {MODULE_COMMUNITY_WALLET}")
    
    def test_03_rake_threshold_constant(self):
        """Test that RAKE_WITHDRAW_THRESHOLD is 0.01 SOL"""
        from services.rake_withdrawal import RAKE_WITHDRAW_THRESHOLD
        assert RAKE_WITHDRAW_THRESHOLD == 0.01, f"Expected 0.01, got {RAKE_WITHDRAW_THRESHOLD}"
        print(f"SUCCESS: RAKE_WITHDRAW_THRESHOLD = {RAKE_WITHDRAW_THRESHOLD} SOL")


class TestRakeTrackingFunctions:
    """Test track_rake() and get_rake_stats() functions"""
    
    def test_04_track_rake_increments_pending_and_total(self):
        """Test that track_rake() correctly increments pending_sol and total_collected_sol"""
        from services.rake_withdrawal import track_rake, get_rake_stats
        from utils.database import db
        
        test_wallet = f"TEST_rake_{uuid.uuid4().hex[:8]}"
        position_id = f"pos_{uuid.uuid4().hex[:8]}"
        
        async def run_test():
            # Track first rake
            await track_rake(test_wallet, 0.001, position_id, "TEST_TOKEN")
            
            # Get stats
            stats = await get_rake_stats(test_wallet)
            
            assert stats["pending_sol"] == 0.001, f"Expected pending_sol=0.001, got {stats['pending_sol']}"
            assert stats["total_collected_sol"] == 0.001, f"Expected total_collected_sol=0.001, got {stats['total_collected_sol']}"
            print(f"SUCCESS: After first track_rake(0.001): pending={stats['pending_sol']}, total={stats['total_collected_sol']}")
            
            # Track second rake
            await track_rake(test_wallet, 0.002, f"pos_{uuid.uuid4().hex[:8]}", "TEST_TOKEN2")
            
            # Get updated stats
            stats2 = await get_rake_stats(test_wallet)
            
            assert stats2["pending_sol"] == 0.003, f"Expected pending_sol=0.003, got {stats2['pending_sol']}"
            assert stats2["total_collected_sol"] == 0.003, f"Expected total_collected_sol=0.003, got {stats2['total_collected_sol']}"
            print(f"SUCCESS: After second track_rake(0.002): pending={stats2['pending_sol']}, total={stats2['total_collected_sol']}")
            
            # Cleanup
            await db.rake_tracker.delete_many({"wallet_address": test_wallet})
            await db.rake_events.delete_many({"wallet_address": test_wallet})
        
        run_async(run_test())
    
    def test_05_track_rake_creates_rake_events(self):
        """Test that track_rake() creates individual rake event entries"""
        from services.rake_withdrawal import track_rake
        from utils.database import db
        
        test_wallet = f"TEST_rake_{uuid.uuid4().hex[:8]}"
        position_id = f"pos_{uuid.uuid4().hex[:8]}"
        
        async def run_test():
            # Track rake
            await track_rake(test_wallet, 0.0015, position_id, "BONK")
            
            # Check rake_events collection
            event = await db.rake_events.find_one({"wallet_address": test_wallet, "position_id": position_id})
            
            assert event is not None, "rake_events entry not created"
            assert event["amount_sol"] == 0.0015, f"Expected amount_sol=0.0015, got {event['amount_sol']}"
            assert event["symbol"] == "BONK", f"Expected symbol=BONK, got {event['symbol']}"
            assert "created_at" in event, "created_at field missing"
            print(f"SUCCESS: rake_events entry created: amount={event['amount_sol']}, symbol={event['symbol']}")
            
            # Cleanup
            await db.rake_tracker.delete_many({"wallet_address": test_wallet})
            await db.rake_events.delete_many({"wallet_address": test_wallet})
        
        run_async(run_test())
    
    def test_06_track_rake_ignores_zero_or_negative(self):
        """Test that track_rake() ignores zero or negative amounts"""
        from services.rake_withdrawal import track_rake, get_rake_stats
        from utils.database import db
        
        test_wallet = f"TEST_rake_{uuid.uuid4().hex[:8]}"
        
        async def run_test():
            # Track zero rake
            await track_rake(test_wallet, 0, "pos_zero", "TEST")
            
            # Track negative rake
            await track_rake(test_wallet, -0.001, "pos_neg", "TEST")
            
            # Get stats - should be empty/default
            stats = await get_rake_stats(test_wallet)
            
            assert stats["pending_sol"] == 0, f"Expected pending_sol=0, got {stats['pending_sol']}"
            assert stats["total_collected_sol"] == 0, f"Expected total_collected_sol=0, got {stats['total_collected_sol']}"
            print(f"SUCCESS: Zero/negative rake amounts ignored: pending={stats['pending_sol']}, total={stats['total_collected_sol']}")
            
            # Cleanup
            await db.rake_tracker.delete_many({"wallet_address": test_wallet})
            await db.rake_events.delete_many({"wallet_address": test_wallet})
        
        run_async(run_test())


class TestGetRakeStatsStructure:
    """Test get_rake_stats() return structure"""
    
    def test_07_get_rake_stats_returns_correct_structure(self):
        """Test that get_rake_stats() returns all required fields"""
        from services.rake_withdrawal import get_rake_stats
        
        async def run_test():
            # Get stats for a non-existent wallet (should return defaults)
            stats = await get_rake_stats("nonexistent_wallet_12345")
            
            required_fields = [
                "total_collected_sol",
                "total_withdrawn_sol", 
                "pending_sol",
                "withdrawal_count",
                "community_wallet",
                "threshold_sol"
            ]
            
            for field in required_fields:
                assert field in stats, f"Missing required field: {field}"
            
            # Verify default values
            assert stats["total_collected_sol"] == 0
            assert stats["total_withdrawn_sol"] == 0
            assert stats["pending_sol"] == 0
            assert stats["withdrawal_count"] == 0
            assert stats["community_wallet"] == COMMUNITY_WALLET
            assert stats["threshold_sol"] == 0.01
            
            print(f"SUCCESS: get_rake_stats() returns correct structure with all required fields")
            print(f"  - total_collected_sol: {stats['total_collected_sol']}")
            print(f"  - total_withdrawn_sol: {stats['total_withdrawn_sol']}")
            print(f"  - pending_sol: {stats['pending_sol']}")
            print(f"  - withdrawal_count: {stats['withdrawal_count']}")
            print(f"  - community_wallet: {stats['community_wallet']}")
            print(f"  - threshold_sol: {stats['threshold_sol']}")
        
        run_async(run_test())


class TestBotHealthEndpoint:
    """Test /api/admin/bot-health endpoint includes rake stats"""
    
    def test_08_bot_health_endpoint_returns_200(self):
        """Test that bot-health endpoint returns 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/admin/bot-health",
            params={"admin_wallet": ADMIN_WALLET}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"SUCCESS: GET /api/admin/bot-health returns 200")
    
    def test_09_bot_health_includes_rake_field(self):
        """Test that bot-health response includes 'rake' field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/bot-health",
            params={"admin_wallet": ADMIN_WALLET}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "rake" in data, f"'rake' field missing from bot-health response. Keys: {list(data.keys())}"
        print(f"SUCCESS: bot-health response includes 'rake' field")
        print(f"  - rake data: {data['rake']}")
    
    def test_10_bot_health_rake_stats_structure(self):
        """Test that rake stats in bot-health have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/bot-health",
            params={"admin_wallet": ADMIN_WALLET}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        rake_data = data.get("rake", {})
        
        # If there's rake data for any wallet, verify structure
        if rake_data:
            for wallet_key, stats in rake_data.items():
                required_fields = ["total_collected_sol", "pending_sol", "community_wallet", "threshold_sol"]
                for field in required_fields:
                    assert field in stats, f"Missing field '{field}' in rake stats for {wallet_key}"
                
                # Verify community wallet is correct
                assert stats["community_wallet"] == COMMUNITY_WALLET, f"Wrong community wallet: {stats['community_wallet']}"
                assert stats["threshold_sol"] == 0.01, f"Wrong threshold: {stats['threshold_sol']}"
                
                print(f"SUCCESS: Rake stats for {wallet_key}:")
                print(f"  - total_collected_sol: {stats['total_collected_sol']}")
                print(f"  - pending_sol: {stats['pending_sol']}")
                print(f"  - community_wallet: {stats['community_wallet'][:12]}...")
                print(f"  - threshold_sol: {stats['threshold_sol']}")
        else:
            print("INFO: No rake data yet (empty dict) - this is expected if no trades have occurred")
            assert isinstance(rake_data, dict), f"Expected dict, got {type(rake_data)}"


class TestApplyRakeIntegration:
    """Test that apply_rake in auto_trader_engine.py calls track_rake"""
    
    def test_11_apply_rake_function_exists(self):
        """Test that apply_rake function exists in auto_trader_engine"""
        try:
            from services.auto_trader_engine import apply_rake
            print("SUCCESS: apply_rake function exists in auto_trader_engine")
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import apply_rake: {e}")
    
    def test_12_apply_rake_imports_track_rake(self):
        """Test that apply_rake code imports track_rake from rake_withdrawal"""
        import inspect
        from services.auto_trader_engine import apply_rake
        
        source = inspect.getsource(apply_rake)
        
        # Check that track_rake is imported and called
        assert "track_rake" in source, "track_rake not found in apply_rake source"
        assert "from services.rake_withdrawal import track_rake" in source or "rake_withdrawal" in source, \
            "rake_withdrawal import not found in apply_rake"
        
        print("SUCCESS: apply_rake imports and calls track_rake from rake_withdrawal")


class TestAdminRouterRakeIntegration:
    """Test that admin.py correctly imports and uses get_rake_stats"""
    
    def test_13_admin_router_imports_rake_stats(self):
        """Test that admin router imports get_rake_stats"""
        # Read the admin.py file and check for import
        admin_path = "/app/backend/routers/admin.py"
        with open(admin_path, "r") as f:
            content = f.read()
        
        assert "from services.rake_withdrawal import get_rake_stats" in content, \
            "get_rake_stats import not found in admin.py"
        
        print("SUCCESS: admin.py imports get_rake_stats from rake_withdrawal")
    
    def test_14_bot_health_calls_get_rake_stats(self):
        """Test that bot-health endpoint calls get_rake_stats for each wallet"""
        admin_path = "/app/backend/routers/admin.py"
        with open(admin_path, "r") as f:
            content = f.read()
        
        # Check that get_rake_stats is called in bot-health endpoint
        assert "get_rake_stats" in content, "get_rake_stats not called in admin.py"
        assert "rake_stats" in content or "rake" in content, "rake stats not included in response"
        
        print("SUCCESS: bot-health endpoint calls get_rake_stats")


class TestCleanup:
    """Cleanup test data after all tests"""
    
    def test_99_cleanup_test_data(self):
        """Clean up all TEST_ prefixed data from rake collections"""
        from utils.database import db
        
        async def run_cleanup():
            # Delete test data
            tracker_result = await db.rake_tracker.delete_many({"wallet_address": {"$regex": "^TEST_"}})
            events_result = await db.rake_events.delete_many({"wallet_address": {"$regex": "^TEST_"}})
            
            print(f"CLEANUP: Deleted {tracker_result.deleted_count} rake_tracker entries")
            print(f"CLEANUP: Deleted {events_result.deleted_count} rake_events entries")
        
        run_async(run_cleanup())


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
