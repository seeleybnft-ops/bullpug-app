"""
Backend API tests for chat history and tradeable assets endpoints.
Tests the 3 enhancements: MongoDB-backed chat persistence and live pricing API.
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTradeableAssetsAPI:
    """Tests for /api/ai/tradeable-assets endpoint - live pricing for trade form"""
    
    def test_tradeable_assets_returns_200(self):
        """API returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/ai/tradeable-assets")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ GET /api/ai/tradeable-assets returned 200")
    
    def test_tradeable_assets_has_assets_array(self):
        """Response contains 'assets' array"""
        response = requests.get(f"{BASE_URL}/api/ai/tradeable-assets")
        data = response.json()
        assert "assets" in data, "Response missing 'assets' field"
        assert isinstance(data["assets"], list), "'assets' should be a list"
        print(f"✅ Response contains assets array with {len(data['assets'])} items")
    
    def test_tradeable_assets_has_required_fields(self):
        """Each asset has required fields: symbol, price, change_24h"""
        response = requests.get(f"{BASE_URL}/api/ai/tradeable-assets")
        data = response.json()
        
        if len(data["assets"]) > 0:
            asset = data["assets"][0]
            assert "symbol" in asset, "Asset missing 'symbol'"
            assert "price" in asset, "Asset missing 'price'"
            assert "change_24h" in asset, "Asset missing 'change_24h'"
            print(f"✅ First asset: {asset['symbol']} at ${asset['price']}")
        else:
            pytest.skip("No assets returned - API may have rate limited")
    
    def test_tradeable_assets_has_timestamp(self):
        """Response includes timestamp"""
        response = requests.get(f"{BASE_URL}/api/ai/tradeable-assets")
        data = response.json()
        assert "timestamp" in data, "Response missing 'timestamp'"
        print(f"✅ Timestamp: {data['timestamp']}")


class TestChatHistorySave:
    """Tests for /api/ai/history/save endpoint - MongoDB persistence"""
    
    @pytest.fixture
    def test_wallet(self):
        return f"TEST_wallet_{int(time.time())}"
    
    def test_save_chat_history_returns_200(self, test_wallet):
        """Saving chat history returns 200 OK"""
        payload = {
            "wallet_address": test_wallet,
            "session_id": "test_session_123",
            "messages": [
                {"role": "user", "content": "Hello!", "timestamp": int(time.time() * 1000)},
                {"role": "assistant", "content": "Hi there!", "timestamp": int(time.time() * 1000)}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/ai/history/save", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ POST /api/ai/history/save returned 200")
    
    def test_save_chat_history_returns_success(self, test_wallet):
        """Response contains success=true"""
        payload = {
            "wallet_address": test_wallet,
            "session_id": "test_session_456",
            "messages": [
                {"role": "user", "content": "Test message", "timestamp": int(time.time() * 1000)}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/ai/history/save", json=payload)
        data = response.json()
        assert data.get("success") == True, f"Expected success=true, got {data.get('success')}"
        assert "message_count" in data, "Response missing 'message_count'"
        print(f"✅ Saved {data['message_count']} message(s)")


class TestChatHistoryGet:
    """Tests for /api/ai/history/{wallet} endpoint - retrieve chat history"""
    
    def test_get_empty_history_returns_200(self):
        """Getting history for non-existent wallet returns 200 with empty messages"""
        response = requests.get(f"{BASE_URL}/api/ai/history/nonexistent_wallet_xyz")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("messages") == []
        print(f"✅ Empty wallet returns success=true with empty messages")
    
    def test_get_saved_history(self):
        """Can retrieve previously saved chat history"""
        wallet = f"TEST_persist_{int(time.time())}"
        
        # Save
        save_payload = {
            "wallet_address": wallet,
            "session_id": "persist_session",
            "messages": [
                {"role": "user", "content": "Remember this!", "timestamp": int(time.time() * 1000)}
            ]
        }
        save_response = requests.post(f"{BASE_URL}/api/ai/history/save", json=save_payload)
        assert save_response.status_code == 200
        
        # Retrieve
        get_response = requests.get(f"{BASE_URL}/api/ai/history/{wallet}")
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data.get("success") == True
        assert len(data.get("messages", [])) == 1
        assert data["messages"][0]["content"] == "Remember this!"
        print(f"✅ Successfully retrieved persisted message: '{data['messages'][0]['content']}'")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/ai/history/{wallet}")


class TestChatHistoryDelete:
    """Tests for DELETE /api/ai/history/{wallet} endpoint - clear chat history"""
    
    def test_delete_history_returns_200(self):
        """Deleting history returns 200 OK"""
        wallet = f"TEST_delete_{int(time.time())}"
        
        # First save something
        save_payload = {
            "wallet_address": wallet,
            "session_id": "delete_test",
            "messages": [{"role": "user", "content": "To be deleted", "timestamp": int(time.time() * 1000)}]
        }
        requests.post(f"{BASE_URL}/api/ai/history/save", json=save_payload)
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/ai/history/{wallet}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✅ DELETE returned success=true, deleted={data.get('deleted')}")
    
    def test_delete_clears_messages(self):
        """After delete, messages should be empty"""
        wallet = f"TEST_clear_{int(time.time())}"
        
        # Save
        save_payload = {
            "wallet_address": wallet,
            "session_id": "clear_test",
            "messages": [{"role": "user", "content": "Should disappear", "timestamp": int(time.time() * 1000)}]
        }
        requests.post(f"{BASE_URL}/api/ai/history/save", json=save_payload)
        
        # Delete
        requests.delete(f"{BASE_URL}/api/ai/history/{wallet}")
        
        # Verify cleared
        get_response = requests.get(f"{BASE_URL}/api/ai/history/{wallet}")
        data = get_response.json()
        assert data.get("messages") == []
        print(f"✅ Messages cleared after delete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
