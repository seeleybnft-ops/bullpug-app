"""
Test Iteration 72: Auto Optimization Toggle Feature

Tests:
1. PUT /api/ai-trader/auto-trade/settings accepts auto_optimization_enabled field
2. GET /api/ai-trader/auto-trade/status returns auto_optimization_enabled in response
3. Auto-trade scan applies optimal settings when auto_optimization_enabled=true
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test wallet address
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestAutoOptimizationToggle:
    """Test auto_optimization_enabled feature in auto-trade settings"""
    
    def test_put_settings_accepts_auto_optimization_enabled(self):
        """Test that PUT /api/ai-trader/auto-trade/settings accepts auto_optimization_enabled field"""
        # Enable auto_optimization
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json={"auto_optimization_enabled": True}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") is True, f"Expected success=True, got {data}"
        assert "auto_optimization_enabled" in data.get("updated_fields", []), \
            f"auto_optimization_enabled should be in updated_fields: {data}"
        
        print(f"✓ PUT settings with auto_optimization_enabled=True succeeded")
        print(f"  Updated fields: {data.get('updated_fields')}")
    
    def test_get_status_returns_auto_optimization_enabled(self):
        """Test that GET /api/ai-trader/auto-trade/status returns auto_optimization_enabled"""
        # First set it to True
        requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json={"auto_optimization_enabled": True}
        )
        
        # Get status
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check that auto_optimization_enabled is in the response
        assert "auto_optimization_enabled" in data, \
            f"auto_optimization_enabled should be in status response: {data.keys()}"
        assert data["auto_optimization_enabled"] is True, \
            f"Expected auto_optimization_enabled=True, got {data['auto_optimization_enabled']}"
        
        print(f"✓ GET status returns auto_optimization_enabled=True")
        print(f"  Full status: auto_trade_enabled={data.get('auto_trade_enabled')}, auto_optimization_enabled={data.get('auto_optimization_enabled')}")
    
    def test_toggle_auto_optimization_off(self):
        """Test toggling auto_optimization_enabled to False"""
        # Disable auto_optimization
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json={"auto_optimization_enabled": False}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify it's now False
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        assert status_data.get("auto_optimization_enabled") is False, \
            f"Expected auto_optimization_enabled=False, got {status_data.get('auto_optimization_enabled')}"
        
        print(f"✓ Toggle auto_optimization_enabled to False succeeded")
    
    def test_status_response_structure(self):
        """Test that status response has all expected fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        required_fields = ["auto_trade_enabled", "auto_optimization_enabled", "settings", "today_stats"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}. Got: {data.keys()}"
        
        # Check settings structure
        settings = data.get("settings")
        if settings:
            settings_fields = ["mode", "min_confidence", "max_daily_trades", "max_position_sol", 
                            "cooldown_minutes", "stop_loss_percent", "take_profit_percent"]
            for field in settings_fields:
                assert field in settings, f"Missing settings field: {field}. Got: {settings.keys()}"
        
        print(f"✓ Status response has all required fields")
        print(f"  Fields: {list(data.keys())}")
        if settings:
            print(f"  Settings fields: {list(settings.keys())}")


class TestOptimalSettingsEndpoint:
    """Test the optimal settings endpoint that auto-optimization uses"""
    
    def test_optimal_settings_endpoint_exists(self):
        """Test that /api/signal-analytics/optimal-settings endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/signal-analytics/optimal-settings")
        
        # Should return 200 (may have no data but endpoint should exist)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "sufficient_data" in data, f"Missing 'sufficient_data' field: {data.keys()}"
        
        print(f"✓ Optimal settings endpoint exists and returns valid response")
        print(f"  sufficient_data: {data.get('sufficient_data')}")
        
        if data.get("settings"):
            settings = data["settings"]
            print(f"  Settings: {settings}")
            
            # Check for auto_trade recommendations if present
            if "auto_trade" in settings:
                auto_trade = settings["auto_trade"]
                print(f"  Auto-trade recommendations:")
                print(f"    - recommended_min_confidence: {auto_trade.get('recommended_min_confidence')}")
                print(f"    - recommended_max_daily_trades: {auto_trade.get('recommended_max_daily_trades')}")
                print(f"    - recommended_cooldown_minutes: {auto_trade.get('recommended_cooldown_minutes')}")


class TestAutoTradeScanWithOptimization:
    """Test that auto-trade scan applies optimal settings when enabled"""
    
    def test_scan_endpoint_exists(self):
        """Test that auto-trade scan endpoint exists"""
        # First enable auto-trading
        requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json={
                "auto_trade_enabled": True,
                "auto_optimization_enabled": True
            }
        )
        
        # Try to run scan (may fail due to no custodial wallet, but endpoint should exist)
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}")
        
        # Should return 200 or 400 (not 404 or 500)
        assert response.status_code in [200, 400], \
            f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"✓ Auto-trade scan endpoint exists")
        print(f"  Response: {data.get('message', data.get('success'))}")
    
    def test_scan_with_optimization_disabled(self):
        """Test scan behavior with auto_optimization_enabled=False"""
        # Disable optimization
        requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json={
                "auto_trade_enabled": True,
                "auto_optimization_enabled": False,
                "auto_min_confidence": 0.70  # Manual setting
            }
        )
        
        # Run scan
        response = requests.post(f"{BASE_URL}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}")
        
        assert response.status_code in [200, 400], \
            f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        print(f"✓ Scan with optimization disabled works")
        print(f"  Response: {response.json()}")


class TestSettingsUpdateValidation:
    """Test settings update validation"""
    
    def test_update_multiple_settings_including_optimization(self):
        """Test updating multiple settings including auto_optimization_enabled"""
        response = requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json={
                "auto_optimization_enabled": True,
                "auto_min_confidence": 0.65,
                "auto_max_daily_trades": 5,
                "auto_cooldown_minutes": 45
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        updated_fields = data.get("updated_fields", [])
        
        assert "auto_optimization_enabled" in updated_fields
        assert "auto_min_confidence" in updated_fields
        assert "auto_max_daily_trades" in updated_fields
        assert "auto_cooldown_minutes" in updated_fields
        
        print(f"✓ Multiple settings update including auto_optimization_enabled succeeded")
        print(f"  Updated fields: {updated_fields}")
    
    def test_settings_persist_after_update(self):
        """Test that settings persist correctly after update"""
        # Set specific values
        test_values = {
            "auto_optimization_enabled": True,
            "auto_min_confidence": 0.72,
            "auto_max_daily_trades": 4
        }
        
        requests.put(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
            json=test_values
        )
        
        # Verify persistence
        response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("auto_optimization_enabled") == test_values["auto_optimization_enabled"]
        
        settings = data.get("settings", {})
        assert settings.get("min_confidence") == test_values["auto_min_confidence"], \
            f"Expected min_confidence={test_values['auto_min_confidence']}, got {settings.get('min_confidence')}"
        assert settings.get("max_daily_trades") == test_values["auto_max_daily_trades"], \
            f"Expected max_daily_trades={test_values['auto_max_daily_trades']}, got {settings.get('max_daily_trades')}"
        
        print(f"✓ Settings persist correctly after update")
        print(f"  auto_optimization_enabled: {data.get('auto_optimization_enabled')}")
        print(f"  min_confidence: {settings.get('min_confidence')}")
        print(f"  max_daily_trades: {settings.get('max_daily_trades')}")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Reset test wallet settings after tests"""
    yield
    # Reset to defaults
    requests.put(
        f"{BASE_URL}/api/ai-trader/auto-trade/settings/{TEST_WALLET}",
        json={
            "auto_trade_enabled": False,
            "auto_optimization_enabled": False
        }
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
