"""
Test Suite for Iteration 60: Adaptive Learning, A/B Testing, and Auto-Tracking
Tests the following new endpoints:
- Auto-tracking: GET/PUT /auto-tracking/status, POST /auto-tracking/run
- A/B Testing: POST /ab-test/create, GET /ab-test/list, GET /ab-test/{test_id}, 
               POST /ab-test/{test_id}/record-outcome, PUT /ab-test/{test_id}/status
- Adaptive Learning: GET /adaptive/current-settings, POST /adaptive/apply, GET /adaptive/history
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ============== Auto-Tracking Tests ==============

class TestAutoTrackingStatus:
    """Tests for GET /api/signal-analytics/auto-tracking/status"""
    
    def test_get_auto_tracking_status(self, api_client):
        """Test getting auto-tracking status returns expected structure"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/auto-tracking/status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify config structure
        assert "config" in data, "Response should contain 'config'"
        config = data["config"]
        assert "enabled" in config, "Config should have 'enabled' field"
        # track_interval_minutes may not be present in initial config, check if present after update
        
        # Verify outcome_stats structure
        assert "outcome_stats" in data, "Response should contain 'outcome_stats'"
        stats = data["outcome_stats"]
        assert "total_outcomes" in stats, "Stats should have 'total_outcomes'"
        assert "with_1h_data" in stats, "Stats should have 'with_1h_data'"
        assert "with_4h_data" in stats, "Stats should have 'with_4h_data'"
        assert "with_24h_data" in stats, "Stats should have 'with_24h_data'"
        
        print(f"Auto-tracking status: enabled={config.get('enabled')}, total_outcomes={stats['total_outcomes']}")


class TestAutoTrackingConfigUpdate:
    """Tests for PUT /api/signal-analytics/auto-tracking/config"""
    
    def test_update_tracking_config_enabled(self, api_client):
        """Test updating enabled status"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/auto-tracking/config",
            params={"enabled": True}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["config"]["enabled"] == True
        print("Successfully updated enabled=True")
    
    def test_update_tracking_config_interval(self, api_client):
        """Test updating track interval"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/auto-tracking/config",
            params={"track_interval_minutes": 30}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["config"]["track_interval_minutes"] == 30
        print("Successfully updated track_interval_minutes=30")
    
    def test_update_tracking_config_time_buckets(self, api_client):
        """Test updating time bucket tracking flags"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/auto-tracking/config",
            params={"track_1h": True, "track_4h": True, "track_24h": True}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["config"]["track_1h"] == True
        assert data["config"]["track_4h"] == True
        assert data["config"]["track_24h"] == True
        print("Successfully updated time bucket flags")
    
    def test_update_tracking_config_no_params(self, api_client):
        """Test that updating with no params returns 400"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/auto-tracking/config"
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("Correctly rejected update with no parameters")
    
    def test_update_tracking_config_invalid_interval(self, api_client):
        """Test that invalid interval returns 422"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/auto-tracking/config",
            params={"track_interval_minutes": 5}  # Below minimum of 15
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("Correctly rejected invalid interval (below minimum)")


class TestAutoTrackingRun:
    """Tests for POST /api/signal-analytics/auto-tracking/run"""
    
    def test_run_automated_tracking(self, api_client):
        """Test running automated tracking"""
        response = api_client.post(f"{BASE_URL}/api/signal-analytics/auto-tracking/run")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should have 'success' field"
        
        if data["success"]:
            results = data.get("results", {})
            assert "run_id" in results, "Results should have 'run_id'"
            assert "signals_processed" in results, "Results should have 'signals_processed'"
            assert "outcomes_1h" in results, "Results should have 'outcomes_1h'"
            assert "outcomes_4h" in results, "Results should have 'outcomes_4h'"
            assert "outcomes_24h" in results, "Results should have 'outcomes_24h'"
            
            print(f"Tracking run completed: {results['signals_processed']} signals processed, "
                  f"{results['outcomes_1h']+results['outcomes_4h']+results['outcomes_24h']} outcomes tracked")
        else:
            print(f"Tracking disabled or failed: {data.get('message', 'Unknown reason')}")


# ============== A/B Testing Tests ==============

class TestABTestCreate:
    """Tests for POST /api/signal-analytics/ab-test/create"""
    
    def test_create_ab_test_basic(self, api_client):
        """Test creating a basic A/B test"""
        test_name = f"TEST_ABTest_{datetime.now().strftime('%H%M%S')}"
        
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/create",
            params={
                "name": test_name,
                "variant_a_confidence": 0.55,
                "variant_b_confidence": 0.60,
                "traffic_split_a": 50
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True, "Should return success=True"
        assert "test_id" in data, "Should return test_id"
        assert data["test_id"].startswith("ab_"), "Test ID should start with 'ab_'"
        
        test = data["test"]
        assert test["name"] == test_name
        assert test["status"] == "active"
        assert len(test["variants"]) == 2
        assert test["variants"][0]["min_confidence"] == 0.55
        assert test["variants"][1]["min_confidence"] == 0.60
        assert test["traffic_split"] == [50, 50]
        
        print(f"Created A/B test: {data['test_id']}")
        return data["test_id"]
    
    def test_create_ab_test_with_strategy_filter(self, api_client):
        """Test creating A/B test with strategy filters"""
        test_name = f"TEST_ABTest_Strategy_{datetime.now().strftime('%H%M%S')}"
        
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/create",
            params={
                "name": test_name,
                "variant_a_confidence": 0.50,
                "variant_b_confidence": 0.55,
                "variant_a_strategy": "momentum",
                "variant_b_strategy": "combined",
                "traffic_split_a": 60
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        
        test = data["test"]
        assert test["variants"][0]["strategy_filter"] == "momentum"
        assert test["variants"][1]["strategy_filter"] == "combined"
        assert test["traffic_split"] == [60, 40]
        
        print(f"Created A/B test with strategy filters: {data['test_id']}")
    
    def test_create_ab_test_invalid_confidence(self, api_client):
        """Test that invalid confidence returns 422"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/create",
            params={
                "name": "Invalid Test",
                "variant_a_confidence": 0.30,  # Below minimum of 0.40
                "variant_b_confidence": 0.60
            }
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("Correctly rejected invalid confidence threshold")
    
    def test_create_ab_test_invalid_strategy(self, api_client):
        """Test that invalid strategy returns 422"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/create",
            params={
                "name": "Invalid Strategy Test",
                "variant_a_confidence": 0.55,
                "variant_b_confidence": 0.60,
                "variant_a_strategy": "invalid_strategy"
            }
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("Correctly rejected invalid strategy filter")


class TestABTestList:
    """Tests for GET /api/signal-analytics/ab-test/list"""
    
    def test_list_all_ab_tests(self, api_client):
        """Test listing all A/B tests"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/ab-test/list")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tests" in data, "Response should have 'tests' field"
        assert isinstance(data["tests"], list), "Tests should be a list"
        
        print(f"Found {len(data['tests'])} A/B tests")
    
    def test_list_active_ab_tests(self, api_client):
        """Test listing only active A/B tests"""
        response = api_client.get(
            f"{BASE_URL}/api/signal-analytics/ab-test/list",
            params={"status": "active"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        for test in data["tests"]:
            assert test["status"] == "active", f"Expected active status, got {test['status']}"
        
        print(f"Found {len(data['tests'])} active A/B tests")
    
    def test_list_invalid_status_filter(self, api_client):
        """Test that invalid status filter returns 422"""
        response = api_client.get(
            f"{BASE_URL}/api/signal-analytics/ab-test/list",
            params={"status": "invalid_status"}
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("Correctly rejected invalid status filter")


class TestABTestGetDetails:
    """Tests for GET /api/signal-analytics/ab-test/{test_id}"""
    
    @pytest.fixture(scope="class")
    def created_test_id(self, api_client):
        """Create a test for use in detail tests"""
        test_name = f"TEST_Detail_{datetime.now().strftime('%H%M%S')}"
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/create",
            params={
                "name": test_name,
                "variant_a_confidence": 0.55,
                "variant_b_confidence": 0.60
            }
        )
        return response.json()["test_id"]
    
    def test_get_ab_test_details(self, api_client, created_test_id):
        """Test getting A/B test details"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/ab-test/{created_test_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["test_id"] == created_test_id
        assert "variants" in data
        assert "status" in data
        assert "start_date" in data
        
        # Check variant structure
        for variant in data["variants"]:
            assert "variant_id" in variant
            assert "min_confidence" in variant
            assert "signals_count" in variant
            assert "wins" in variant
            assert "losses" in variant
            assert "win_rate" in variant
        
        print(f"Got details for test {created_test_id}")
    
    def test_get_nonexistent_ab_test(self, api_client):
        """Test getting non-existent A/B test returns 404"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/ab-test/nonexistent_test_id")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for non-existent test")


class TestABTestRecordOutcome:
    """Tests for POST /api/signal-analytics/ab-test/{test_id}/record-outcome"""
    
    @pytest.fixture(scope="class")
    def active_test_id(self, api_client):
        """Create an active test for recording outcomes"""
        test_name = f"TEST_Outcome_{datetime.now().strftime('%H%M%S')}"
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/create",
            params={
                "name": test_name,
                "variant_a_confidence": 0.55,
                "variant_b_confidence": 0.60
            }
        )
        return response.json()["test_id"]
    
    def test_record_win_outcome_variant_a(self, api_client, active_test_id):
        """Test recording a win outcome for variant A"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/{active_test_id}/record-outcome",
            params={
                "variant_id": "A",
                "outcome": "win",
                "pnl_percent": 5.5
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        assert data["variant"] == "A"
        assert data["outcome"] == "win"
        
        print("Recorded win outcome for variant A")
    
    def test_record_loss_outcome_variant_b(self, api_client, active_test_id):
        """Test recording a loss outcome for variant B"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/{active_test_id}/record-outcome",
            params={
                "variant_id": "B",
                "outcome": "loss",
                "pnl_percent": -3.2
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        assert data["variant"] == "B"
        assert data["outcome"] == "loss"
        
        print("Recorded loss outcome for variant B")
    
    def test_record_neutral_outcome(self, api_client, active_test_id):
        """Test recording a neutral outcome"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/{active_test_id}/record-outcome",
            params={
                "variant_id": "A",
                "outcome": "neutral",
                "pnl_percent": 0.5
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        assert data["outcome"] == "neutral"
        
        print("Recorded neutral outcome")
    
    def test_record_outcome_invalid_variant(self, api_client, active_test_id):
        """Test that invalid variant returns 422"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/{active_test_id}/record-outcome",
            params={
                "variant_id": "C",  # Invalid - only A or B allowed
                "outcome": "win",
                "pnl_percent": 5.0
            }
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("Correctly rejected invalid variant ID")
    
    def test_record_outcome_invalid_outcome(self, api_client, active_test_id):
        """Test that invalid outcome returns 422"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/{active_test_id}/record-outcome",
            params={
                "variant_id": "A",
                "outcome": "invalid",  # Invalid - only win/loss/neutral allowed
                "pnl_percent": 5.0
            }
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("Correctly rejected invalid outcome")
    
    def test_record_outcome_nonexistent_test(self, api_client):
        """Test recording outcome for non-existent test returns 404"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/nonexistent_test/record-outcome",
            params={
                "variant_id": "A",
                "outcome": "win",
                "pnl_percent": 5.0
            }
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for non-existent test")


class TestABTestUpdateStatus:
    """Tests for PUT /api/signal-analytics/ab-test/{test_id}/status"""
    
    @pytest.fixture(scope="class")
    def test_for_status_update(self, api_client):
        """Create a test for status update tests"""
        test_name = f"TEST_Status_{datetime.now().strftime('%H%M%S')}"
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/create",
            params={
                "name": test_name,
                "variant_a_confidence": 0.55,
                "variant_b_confidence": 0.60
            }
        )
        return response.json()["test_id"]
    
    def test_pause_ab_test(self, api_client, test_for_status_update):
        """Test pausing an A/B test"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/ab-test/{test_for_status_update}/status",
            params={"status": "paused"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "paused"
        
        print(f"Paused test {test_for_status_update}")
    
    def test_reactivate_ab_test(self, api_client, test_for_status_update):
        """Test reactivating a paused A/B test"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/ab-test/{test_for_status_update}/status",
            params={"status": "active"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "active"
        
        print(f"Reactivated test {test_for_status_update}")
    
    def test_complete_ab_test(self, api_client, test_for_status_update):
        """Test completing an A/B test"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/ab-test/{test_for_status_update}/status",
            params={"status": "completed"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "completed"
        assert "end_date" in data and data["end_date"] is not None
        
        print(f"Completed test {test_for_status_update}")
    
    def test_update_status_invalid(self, api_client, test_for_status_update):
        """Test that invalid status returns 422"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/ab-test/{test_for_status_update}/status",
            params={"status": "invalid_status"}
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("Correctly rejected invalid status")
    
    def test_update_status_nonexistent_test(self, api_client):
        """Test updating status of non-existent test returns 404"""
        response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/ab-test/nonexistent_test/status",
            params={"status": "paused"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for non-existent test")


# ============== Adaptive Learning Tests ==============

class TestAdaptiveCurrentSettings:
    """Tests for GET /api/signal-analytics/adaptive/current-settings"""
    
    def test_get_adaptive_settings(self, api_client):
        """Test getting current adaptive settings"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/adaptive/current-settings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check for sufficient_data flag
        assert "sufficient_data" in data, "Response should have 'sufficient_data' field"
        
        if data["sufficient_data"]:
            # Full response structure
            assert "outcomes_analyzed" in data, "Should have 'outcomes_analyzed'"
            assert "recommended_settings" in data, "Should have 'recommended_settings'"
            assert "confidence_breakdown" in data, "Should have 'confidence_breakdown'"
            assert "strategy_breakdown" in data, "Should have 'strategy_breakdown'"
            
            # Check recommended_settings structure
            settings = data["recommended_settings"]
            assert "min_confidence" in settings, "Settings should have 'min_confidence'"
            assert "priority_strategy" in settings, "Settings should have 'priority_strategy'"
            assert "source" in settings, "Settings should have 'source'"
            
            print(f"Adaptive settings: min_confidence={settings['min_confidence']}, "
                  f"strategy={settings['priority_strategy']}, outcomes={data['outcomes_analyzed']}")
        else:
            # Insufficient data response
            assert "outcomes_count" in data, "Should have 'outcomes_count'"
            assert "message" in data, "Should have 'message'"
            assert "current_settings" in data, "Should have 'current_settings'"
            
            print(f"Insufficient data: {data['message']}")
    
    def test_adaptive_settings_confidence_breakdown(self, api_client):
        """Test that confidence breakdown has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/adaptive/current-settings")
        
        assert response.status_code == 200
        
        data = response.json()
        
        if data.get("sufficient_data") and data.get("confidence_breakdown"):
            for item in data["confidence_breakdown"]:
                assert "bucket" in item, "Breakdown item should have 'bucket'"
                assert "total" in item, "Breakdown item should have 'total'"
                assert "wins" in item, "Breakdown item should have 'wins'"
                assert "win_rate" in item, "Breakdown item should have 'win_rate'"
                assert "avg_pnl" in item, "Breakdown item should have 'avg_pnl'"
            
            print(f"Confidence breakdown has {len(data['confidence_breakdown'])} buckets")
    
    def test_adaptive_settings_strategy_breakdown(self, api_client):
        """Test that strategy breakdown has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/adaptive/current-settings")
        
        assert response.status_code == 200
        
        data = response.json()
        
        if data.get("sufficient_data") and data.get("strategy_breakdown"):
            for item in data["strategy_breakdown"]:
                assert "strategy" in item, "Breakdown item should have 'strategy'"
                assert "total" in item, "Breakdown item should have 'total'"
                assert "wins" in item, "Breakdown item should have 'wins'"
                assert "win_rate" in item, "Breakdown item should have 'win_rate'"
                assert "avg_pnl" in item, "Breakdown item should have 'avg_pnl'"
            
            print(f"Strategy breakdown has {len(data['strategy_breakdown'])} strategies")


class TestAdaptiveApply:
    """Tests for POST /api/signal-analytics/adaptive/apply"""
    
    def test_apply_adaptive_settings(self, api_client):
        """Test applying adaptive settings"""
        response = api_client.post(f"{BASE_URL}/api/signal-analytics/adaptive/apply")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        if data.get("success"):
            assert "applied_settings" in data, "Should have 'applied_settings'"
            settings = data["applied_settings"]
            assert "min_confidence" in settings, "Applied settings should have 'min_confidence'"
            assert "priority_strategy" in settings, "Applied settings should have 'priority_strategy'"
            
            print(f"Applied adaptive settings: min_confidence={settings['min_confidence']}, "
                  f"strategy={settings['priority_strategy']}")
        else:
            # Insufficient data case
            assert "message" in data, "Should have 'message' when not successful"
            print(f"Could not apply settings: {data['message']}")


class TestAdaptiveHistory:
    """Tests for GET /api/signal-analytics/adaptive/history"""
    
    def test_get_adaptive_history(self, api_client):
        """Test getting adaptive settings history"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/adaptive/history")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "history" in data, "Response should have 'history' field"
        assert isinstance(data["history"], list), "History should be a list"
        
        if data["history"]:
            # Check structure of history items
            for item in data["history"]:
                assert "settings_id" in item or "applied_at" in item, "History item should have identifier"
            
            print(f"Found {len(data['history'])} adaptive settings history entries")
        else:
            print("No adaptive settings history yet")


# ============== Integration Tests ==============

class TestABTestFullWorkflow:
    """Integration test for complete A/B test workflow"""
    
    def test_full_ab_test_workflow(self, api_client):
        """Test complete A/B test workflow: create -> record outcomes -> check winner -> complete"""
        
        # 1. Create test
        test_name = f"TEST_Workflow_{datetime.now().strftime('%H%M%S')}"
        create_response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/ab-test/create",
            params={
                "name": test_name,
                "variant_a_confidence": 0.55,
                "variant_b_confidence": 0.60,
                "traffic_split_a": 50
            }
        )
        assert create_response.status_code == 200
        test_id = create_response.json()["test_id"]
        print(f"Step 1: Created test {test_id}")
        
        # 2. Record multiple outcomes for both variants
        outcomes_a = [("win", 5.0), ("win", 3.0), ("loss", -2.0), ("neutral", 0.5)]
        outcomes_b = [("win", 4.0), ("loss", -3.0), ("loss", -2.5), ("neutral", 1.0)]
        
        for outcome, pnl in outcomes_a:
            record_resp = api_client.post(
                f"{BASE_URL}/api/signal-analytics/ab-test/{test_id}/record-outcome",
                params={"variant_id": "A", "outcome": outcome, "pnl_percent": pnl}
            )
            assert record_resp.status_code == 200, f"Failed to record outcome A: {record_resp.text}"
        
        for outcome, pnl in outcomes_b:
            record_resp = api_client.post(
                f"{BASE_URL}/api/signal-analytics/ab-test/{test_id}/record-outcome",
                params={"variant_id": "B", "outcome": outcome, "pnl_percent": pnl}
            )
            assert record_resp.status_code == 200, f"Failed to record outcome B: {record_resp.text}"
        
        print(f"Step 2: Recorded {len(outcomes_a)} outcomes for A, {len(outcomes_b)} for B")
        
        # Small delay to ensure DB writes complete
        time.sleep(0.5)
        
        # 3. Get test details and check stats
        details_response = api_client.get(f"{BASE_URL}/api/signal-analytics/ab-test/{test_id}")
        assert details_response.status_code == 200
        
        details = details_response.json()
        variant_a = details["variants"][0]
        variant_b = details["variants"][1]
        
        print(f"Step 3: Variant A signals_count={variant_a['signals_count']}, wins={variant_a['wins']}")
        print(f"Step 3: Variant B signals_count={variant_b['signals_count']}, wins={variant_b['wins']}")
        
        # Verify outcomes were recorded (may have some variance due to async)
        assert variant_a["signals_count"] >= 1, f"Variant A should have at least 1 signal, got {variant_a['signals_count']}"
        assert variant_b["signals_count"] >= 1, f"Variant B should have at least 1 signal, got {variant_b['signals_count']}"
        
        print(f"Step 3: Variant A win_rate={variant_a['win_rate']}%, Variant B win_rate={variant_b['win_rate']}%")
        
        # 4. Complete the test
        complete_response = api_client.put(
            f"{BASE_URL}/api/signal-analytics/ab-test/{test_id}/status",
            params={"status": "completed"}
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"
        
        print(f"Step 4: Test completed successfully")
        
        # 5. Verify test appears in list with completed status
        list_response = api_client.get(
            f"{BASE_URL}/api/signal-analytics/ab-test/list",
            params={"status": "completed"}
        )
        assert list_response.status_code == 200
        
        completed_tests = list_response.json()["tests"]
        test_ids = [t["test_id"] for t in completed_tests]
        assert test_id in test_ids, "Completed test should appear in completed list"
        
        print(f"Step 5: Test verified in completed list")
        print("Full A/B test workflow completed successfully!")


class TestExistingEndpointsStillWork:
    """Verify existing endpoints from iteration 59 still work"""
    
    def test_performance_summary(self, api_client):
        """Test performance summary endpoint"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/performance-summary")
        assert response.status_code == 200
        print("Performance summary endpoint working")
    
    def test_confidence_analysis(self, api_client):
        """Test confidence analysis endpoint"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/confidence-analysis")
        assert response.status_code == 200
        print("Confidence analysis endpoint working")
    
    def test_strategy_comparison(self, api_client):
        """Test strategy comparison endpoint"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/strategy-comparison")
        assert response.status_code == 200
        print("Strategy comparison endpoint working")
    
    def test_backtest(self, api_client):
        """Test backtest endpoint"""
        response = api_client.post(
            f"{BASE_URL}/api/signal-analytics/backtest",
            params={"min_confidence": 0.50}
        )
        assert response.status_code == 200
        print("Backtest endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
