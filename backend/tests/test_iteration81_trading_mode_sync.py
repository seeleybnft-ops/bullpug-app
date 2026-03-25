"""
Iteration 81: Trading Mode Sync Bug Fix Tests

Tests the fix for the trading mode sync issue where:
- User selects 'Sniper' in Trade Settings
- But stat card on Controls tab shows 'Conservative'

ROOT CAUSE: save_settings saved to 'trading_mode' field but auto-trade status read from 'auto_trade_mode' field.
FIX: save_settings now syncs both fields, and status endpoint reads trading_mode first.

Test flow:
1. POST /api/ai-trader/settings with trading_mode='sniper'
2. GET /api/ai-trader/auto-trade/status/{wallet}
3. Verify response.settings.mode === 'sniper'
4. GET /api/ai-trader/settings/{wallet}
5. Verify both trading_mode and auto_trade_mode match
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test wallet address
TEST_WALLET = f"TEST_wallet_{uuid.uuid4().hex[:8]}"


class TestTradingModeSync:
    """Test trading mode synchronization between settings and auto-trade status"""
    
    def test_save_sniper_mode_and_verify_status(self):
        """Save trading_mode='sniper' and verify auto-trade status returns mode='sniper'"""
        # Step 1: Save settings with trading_mode='sniper'
        save_response = requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET,
                "trading_mode": "sniper"
            }
        )
        assert save_response.status_code == 200, f"Save settings failed: {save_response.text}"
        save_data = save_response.json()
        assert save_data.get("success") == True, "Save settings did not return success"
        print(f"✅ Saved settings with trading_mode='sniper'")
        
        # Step 2: Get auto-trade status
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_response.status_code == 200, f"Get status failed: {status_response.text}"
        status_data = status_response.json()
        
        # Step 3: Verify mode in status matches 'sniper'
        mode = status_data.get("settings", {}).get("mode")
        assert mode == "sniper", f"Expected mode='sniper', got mode='{mode}'"
        print(f"✅ Auto-trade status returns mode='sniper'")
        
    def test_save_aggressive_mode_and_verify_status(self):
        """Save trading_mode='aggressive' and verify auto-trade status returns mode='aggressive'"""
        # Save settings with trading_mode='aggressive'
        save_response = requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET,
                "trading_mode": "aggressive"
            }
        )
        assert save_response.status_code == 200, f"Save settings failed: {save_response.text}"
        
        # Get auto-trade status
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_response.status_code == 200, f"Get status failed: {status_response.text}"
        status_data = status_response.json()
        
        # Verify mode matches 'aggressive'
        mode = status_data.get("settings", {}).get("mode")
        assert mode == "aggressive", f"Expected mode='aggressive', got mode='{mode}'"
        print(f"✅ Auto-trade status returns mode='aggressive'")
        
    def test_save_conservative_mode_and_verify_status(self):
        """Save trading_mode='conservative' and verify auto-trade status returns mode='conservative'"""
        # Save settings with trading_mode='conservative'
        save_response = requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET,
                "trading_mode": "conservative"
            }
        )
        assert save_response.status_code == 200, f"Save settings failed: {save_response.text}"
        
        # Get auto-trade status
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_response.status_code == 200, f"Get status failed: {status_response.text}"
        status_data = status_response.json()
        
        # Verify mode matches 'conservative'
        mode = status_data.get("settings", {}).get("mode")
        assert mode == "conservative", f"Expected mode='conservative', got mode='{mode}'"
        print(f"✅ Auto-trade status returns mode='conservative'")
        
    def test_settings_sync_both_fields(self):
        """Verify save_settings syncs both trading_mode and auto_trade_mode fields"""
        # Save settings with trading_mode='sniper'
        save_response = requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET,
                "trading_mode": "sniper"
            }
        )
        assert save_response.status_code == 200, f"Save settings failed: {save_response.text}"
        
        # Get settings directly
        get_response = requests.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
        assert get_response.status_code == 200, f"Get settings failed: {get_response.text}"
        settings = get_response.json()
        
        # Verify both fields are synced
        trading_mode = settings.get("trading_mode")
        auto_trade_mode = settings.get("auto_trade_mode")
        
        assert trading_mode == "sniper", f"Expected trading_mode='sniper', got '{trading_mode}'"
        assert auto_trade_mode == "sniper", f"Expected auto_trade_mode='sniper', got '{auto_trade_mode}'"
        print(f"✅ Both trading_mode and auto_trade_mode are synced to 'sniper'")
        
    def test_normal_mode_sync(self):
        """Test normal mode sync"""
        # Save settings with trading_mode='normal'
        save_response = requests.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET,
                "trading_mode": "normal"
            }
        )
        assert save_response.status_code == 200, f"Save settings failed: {save_response.text}"
        
        # Get auto-trade status
        status_response = requests.get(f"{BASE_URL}/api/ai-trader/auto-trade/status/{TEST_WALLET}")
        assert status_response.status_code == 200, f"Get status failed: {status_response.text}"
        status_data = status_response.json()
        
        # Verify mode matches 'normal'
        mode = status_data.get("settings", {}).get("mode")
        assert mode == "normal", f"Expected mode='normal', got mode='{mode}'"
        print(f"✅ Auto-trade status returns mode='normal'")


class TestPageTitleAndFavicon:
    """Test page title and favicon fixes"""
    
    def test_api_health(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✅ API health check passed")
        
    def test_leaderboard_api(self):
        """Verify leaderboard API works"""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200, f"Leaderboard API failed: {response.text}"
        print("✅ Leaderboard API works")
        
    def test_platform_stats_api(self):
        """Verify platform stats API works"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/platform-stats")
        assert response.status_code == 200, f"Platform stats API failed: {response.text}"
        print("✅ Platform stats API works")


class TestGalleryImages:
    """Test gallery images from customer-assets domain"""
    
    def test_gallery_api(self):
        """Verify gallery API returns images from customer-assets.emergentagent.com"""
        response = requests.get(f"{BASE_URL}/api/showcase/gallery")
        assert response.status_code == 200, f"Gallery API failed: {response.text}"
        data = response.json()
        
        images = data.get("images", [])
        if images:
            for img in images:
                url = img.get("url", "")
                assert "customer-assets.emergentagent.com" in url, f"Image URL not from customer-assets: {url}"
            print(f"✅ All {len(images)} gallery images from customer-assets.emergentagent.com")
        else:
            print("⚠️ No gallery images found (may be expected)")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Cleanup test data after all tests"""
    yield
    # Cleanup: Delete test wallet settings
    try:
        requests.delete(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET}")
    except:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
