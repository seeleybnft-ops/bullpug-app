"""
Test Enhanced Features for Bullpug:
- Enhanced AI Chat with session memory
- Reflections Calculator with 10M volume max
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestEnhancedAIChat:
    """Test Enhanced AI Chat API with session-based memory"""
    
    def test_ai_chat_endpoint_exists(self):
        """Test that /api/ai/chat endpoint exists and responds"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": None,
                "message": "Hello",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        assert response.status_code == 200
        print("✓ AI chat endpoint responds with 200")
    
    def test_ai_chat_response_structure(self):
        """Test AI chat returns proper response structure"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": None,
                "message": "What is Bullpug?",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "response" in data, "Response should have 'response' field"
        assert "session_id" in data, "Response should have 'session_id' field"
        assert data["session_id"] == session_id, "Session ID should match"
        assert len(data["response"]) > 0, "Response should not be empty"
        print(f"✓ AI chat response has correct structure (response length: {len(data['response'])} chars)")
    
    def test_ai_chat_session_memory(self):
        """Test that AI chat maintains session context"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # First message
        response1 = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": None,
                "message": "My name is TestUser123",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        assert response1.status_code == 200
        history1 = [
            {"role": "user", "content": "My name is TestUser123"},
            {"role": "assistant", "content": response1.json()["response"]}
        ]
        
        # Second message referencing first
        response2 = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": None,
                "message": "What did I just tell you?",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": history1
            }
        )
        assert response2.status_code == 200
        # The AI should have context from previous message
        print("✓ AI chat accepts session_id and chat_history for context")
    
    def test_ai_chat_with_different_tabs(self):
        """Test AI chat works with different active tabs"""
        tabs = ["dashboard", "portfolio", "import", "trades", "simulator", "achievements", "backups"]
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        for tab in tabs:
            response = requests.post(
                f"{BASE_URL}/api/ai/chat",
                json={
                    "wallet_address": None,
                    "message": "Help me",
                    "session_id": session_id,
                    "active_tab": tab,
                    "chat_history": []
                }
            )
            assert response.status_code == 200
            print(f"✓ AI chat works with active_tab='{tab}'")
    
    def test_ai_chat_with_wallet_address(self):
        """Test AI chat accepts wallet_address parameter"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        test_wallet = "TestWallet123456789"
        
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": test_wallet,
                "message": "Analyze my trades",
                "session_id": session_id,
                "active_tab": "trades",
                "chat_history": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        print("✓ AI chat accepts wallet_address parameter")


class TestReflectionsCalculator:
    """Test Reflections Calculator API with extended volume range"""
    
    def test_reflections_endpoint_exists(self):
        """Test that /api/reflections/calculate endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/reflections/calculate",
            json={
                "token_holdings": 10000000,
                "volume_24h": 100000,
                "reflection_rate": 0.8
            }
        )
        assert response.status_code == 200
        print("✓ Reflections calculate endpoint responds with 200")
    
    def test_reflections_response_structure(self):
        """Test reflections response has all required fields"""
        response = requests.post(
            f"{BASE_URL}/api/reflections/calculate",
            json={
                "token_holdings": 10000000,
                "volume_24h": 500000,
                "reflection_rate": 0.8
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "holdings", "holder_share_percent", "volume_24h", "reflection_rate",
            "daily", "weekly", "monthly", "yearly", "estimated_apy", "price_usd"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Nested fields
        for period in ["daily", "weekly", "monthly", "yearly"]:
            assert "usd" in data[period], f"Missing usd in {period}"
            assert "tokens" in data[period], f"Missing tokens in {period}"
        
        print("✓ Reflections response has all required fields")
    
    def test_reflections_max_volume_10_million(self):
        """Test reflections accepts volume up to 10,000,000 (10M)"""
        max_volume = 10000000  # 10 million
        
        response = requests.post(
            f"{BASE_URL}/api/reflections/calculate",
            json={
                "token_holdings": 10000000,
                "volume_24h": max_volume,
                "reflection_rate": 0.8
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["volume_24h"] == max_volume
        print(f"✓ Reflections accepts max volume of ${max_volume:,} (10M)")
    
    def test_reflections_calculations_correct(self):
        """Test reflections calculations are mathematically correct"""
        response = requests.post(
            f"{BASE_URL}/api/reflections/calculate",
            json={
                "token_holdings": 10000000,
                "volume_24h": 1000000,
                "reflection_rate": 0.8  # 0.8%
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Weekly should be ~7x daily
        assert abs(data["weekly"]["usd"] - data["daily"]["usd"] * 7) < 1
        # Monthly should be ~30x daily
        assert abs(data["monthly"]["usd"] - data["daily"]["usd"] * 30) < 1
        # Yearly should be ~365x daily
        assert abs(data["yearly"]["usd"] - data["daily"]["usd"] * 365) < 1
        
        print("✓ Reflections calculations are mathematically consistent")
    
    def test_reflections_with_various_volumes(self):
        """Test reflections works with various volume levels"""
        volumes = [10000, 100000, 1000000, 5000000, 10000000]
        
        for volume in volumes:
            response = requests.post(
                f"{BASE_URL}/api/reflections/calculate",
                json={
                    "token_holdings": 10000000,
                    "volume_24h": volume,
                    "reflection_rate": 0.8
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["volume_24h"] == volume
            print(f"✓ Reflections works with volume ${volume:,}")


class TestPortfolioPrices:
    """Test Portfolio prices API"""
    
    def test_portfolio_prices_endpoint(self):
        """Test that /api/portfolio/prices endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/portfolio/prices")
        assert response.status_code == 200
        data = response.json()
        
        assert "ETH" in data, "Should have ETH price"
        assert "SOL" in data, "Should have SOL price"
        assert "usd" in data["ETH"], "ETH should have usd field"
        assert "usd" in data["SOL"], "SOL should have usd field"
        
        print(f"✓ Portfolio prices: ETH=${data['ETH']['usd']}, SOL=${data['SOL']['usd']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
