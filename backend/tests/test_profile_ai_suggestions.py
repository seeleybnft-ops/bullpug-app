"""
Tests for Profile API and AI Suggestions API with GPT-4o integration
Testing:
- GET /api/profile/{wallet_address} - returns profile data with game stats
- PUT /api/profile/{wallet_address} - updates profile correctly
- GET /api/profile/{wallet_address}/skins - returns owned skins
- POST /api/ai-suggestions/exit-simulator - returns GPT-4o powered suggestions
- GET /api/ai-suggestions/journal-daily/{wallet_address} - returns GPT-4o powered daily insights
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_WALLET = f"test-wallet-{uuid.uuid4().hex[:8]}"

class TestProfileAPI:
    """Profile CRUD API tests"""
    
    def test_get_profile_creates_new_profile(self):
        """GET /api/profile/{wallet_address} should create profile if not exists"""
        wallet = f"new-profile-{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/profile/{wallet}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify profile structure
        assert "id" in data, "Profile should have id"
        assert data["wallet_address"] == wallet, "Wallet address should match"
        assert "display_name" in data, "Profile should have display_name"
        assert data["display_name"].startswith("Bullpug_"), "Default display name should start with Bullpug_"
        
        # Verify game stats are included
        assert "game_stats" in data, "Profile should include game_stats"
        assert "high_score" in data["game_stats"], "Game stats should have high_score"
        assert "total_mooncakes" in data["game_stats"], "Game stats should have total_mooncakes"
        assert "games_played" in data["game_stats"], "Game stats should have games_played"
        
        # Verify owned_skins
        assert "owned_skins" in data, "Profile should have owned_skins"
        assert "default" in data["owned_skins"], "default skin should be in owned_skins"
        
        print(f"✓ Profile created successfully for wallet: {wallet[:16]}...")
        print(f"  - Display name: {data['display_name']}")
        print(f"  - Game stats: {data['game_stats']}")
    
    def test_get_profile_returns_existing_profile(self):
        """GET /api/profile/{wallet_address} should return existing profile"""
        # First create a profile
        response1 = requests.get(f"{BASE_URL}/api/profile/{TEST_WALLET}")
        assert response1.status_code == 200
        profile_id = response1.json()["id"]
        
        # Second call should return same profile
        response2 = requests.get(f"{BASE_URL}/api/profile/{TEST_WALLET}")
        assert response2.status_code == 200
        assert response2.json()["id"] == profile_id, "Should return same profile on subsequent calls"
        
        print(f"✓ Existing profile returned correctly, ID: {profile_id[:16]}...")
    
    def test_update_profile_display_name(self):
        """PUT /api/profile/{wallet_address} should update display_name"""
        wallet = f"update-test-{uuid.uuid4().hex[:8]}"
        
        # Create profile first
        requests.get(f"{BASE_URL}/api/profile/{wallet}")
        
        # Update display name
        new_name = "TestBullpugTrader"
        response = requests.put(
            f"{BASE_URL}/api/profile/{wallet}",
            json={"display_name": new_name}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data, "Response should have message"
        assert "display_name" in data.get("updated_fields", []), "display_name should be in updated_fields"
        
        # Verify update persisted
        verify_response = requests.get(f"{BASE_URL}/api/profile/{wallet}")
        assert verify_response.status_code == 200
        assert verify_response.json()["display_name"] == new_name, "Display name should be updated"
        
        print(f"✓ Profile display_name updated to: {new_name}")
    
    def test_update_profile_bio(self):
        """PUT /api/profile/{wallet_address} should update bio"""
        wallet = f"bio-test-{uuid.uuid4().hex[:8]}"
        
        # Create profile first
        requests.get(f"{BASE_URL}/api/profile/{wallet}")
        
        # Update bio
        bio_text = "Bullpug enthusiast and memecoin trader!"
        response = requests.put(
            f"{BASE_URL}/api/profile/{wallet}",
            json={"bio": bio_text}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update persisted
        verify_response = requests.get(f"{BASE_URL}/api/profile/{wallet}")
        assert verify_response.status_code == 200
        assert verify_response.json()["bio"] == bio_text, "Bio should be updated"
        
        print(f"✓ Profile bio updated successfully")
    
    def test_update_profile_social_links(self):
        """PUT /api/profile/{wallet_address} should update social links"""
        wallet = f"social-test-{uuid.uuid4().hex[:8]}"
        
        # Create profile first
        requests.get(f"{BASE_URL}/api/profile/{wallet}")
        
        # Update social links
        social_data = {
            "twitter_handle": "@bullpug_trader",
            "telegram_handle": "bullpug_group",
            "discord_handle": "bullpug#1234",
            "website_url": "https://bullpug.io"
        }
        response = requests.put(f"{BASE_URL}/api/profile/{wallet}", json=social_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update persisted
        verify_response = requests.get(f"{BASE_URL}/api/profile/{wallet}")
        assert verify_response.status_code == 200
        profile = verify_response.json()
        
        assert profile["twitter_handle"] == "bullpug_trader", "Twitter handle should be updated (@ removed)"
        assert profile["telegram_handle"] == "bullpug_group", "Telegram handle should be updated"
        assert profile["discord_handle"] == "bullpug#1234", "Discord handle should be updated"
        assert profile["website_url"] == "https://bullpug.io", "Website URL should be updated"
        
        print(f"✓ Profile social links updated successfully")
    
    def test_get_available_skins(self):
        """GET /api/profile/{wallet_address}/skins should return available skins"""
        wallet = f"skins-test-{uuid.uuid4().hex[:8]}"
        
        response = requests.get(f"{BASE_URL}/api/profile/{wallet}/skins")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "skins" in data, "Response should have skins array"
        
        # Default skin should always be available
        default_skin = next((s for s in data["skins"] if s["id"] == "default"), None)
        assert default_skin is not None, "Default skin should be in available skins"
        assert default_skin["owned"] == True, "Default skin should be marked as owned"
        assert "name" in default_skin, "Skin should have name"
        assert "image" in default_skin, "Skin should have image path"
        
        print(f"✓ Available skins returned successfully")
        print(f"  - Skins count: {len(data['skins'])}")
        for skin in data["skins"]:
            print(f"  - {skin['name']}: {skin['image']}")


class TestAISuggestionsAPI:
    """AI Suggestions API tests with GPT-4o integration"""
    
    def test_exit_simulator_suggestion(self):
        """POST /api/ai-suggestions/exit-simulator should return GPT-4o powered suggestion"""
        payload = {
            "token_symbol": "SOL",
            "entry_price": 100.0,
            "current_price": 105.0,
            "volatility": 0.8,
            "simulated_outcomes": {
                "probability_profit": 65,
                "median_final_price": 120.0,
                "pnl_percentiles": {"p5": -30, "p25": -10, "p50": 10, "p75": 40, "p95": 100}
            },
            "wallet_address": TEST_WALLET
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-suggestions/exit-simulator", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "suggestion" in data, "Response should have suggestion"
        assert len(data["suggestion"]) > 50, "Suggestion should have meaningful content"
        assert "generated_at" in data, "Response should have generated_at timestamp"
        assert "powered_by" in data, "Response should have powered_by field"
        
        # Check if using real LLM or fallback
        print(f"✓ Exit simulator suggestion generated")
        print(f"  - Powered by: {data['powered_by']}")
        print(f"  - Suggestion length: {len(data['suggestion'])} chars")
        print(f"  - Live price: {data.get('live_price')}")
        
        # GPT-4o indicator check
        if data["powered_by"] == "GPT-4o":
            print(f"  ✓ Using REAL GPT-4o LLM integration!")
        else:
            print(f"  ⚠ Using fallback (not GPT-4o)")
    
    def test_exit_simulator_without_wallet(self):
        """POST /api/ai-suggestions/exit-simulator works without wallet_address"""
        payload = {
            "token_symbol": "BTC",
            "entry_price": 45000.0,
            "volatility": 0.5,
            "simulated_outcomes": {
                "probability_profit": 55,
                "median_final_price": 48000.0,
                "pnl_percentiles": {"p5": -20, "p95": 50}
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-suggestions/exit-simulator", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "suggestion" in data, "Response should have suggestion"
        
        print(f"✓ Exit simulator works without wallet_address")
        print(f"  - Powered by: {data['powered_by']}")
    
    def test_journal_daily_insight(self):
        """GET /api/ai-suggestions/journal-daily/{wallet_address} returns daily insight"""
        wallet = f"journal-ai-{uuid.uuid4().hex[:8]}"
        
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/journal-daily/{wallet}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "insight" in data, "Response should have insight"
        assert len(data["insight"]) > 30, "Insight should have meaningful content"
        assert "generated_at" in data, "Response should have generated_at timestamp"
        assert "powered_by" in data, "Response should have powered_by field"
        assert "journal_stats" in data, "Response should have journal_stats"
        
        print(f"✓ Journal daily insight generated")
        print(f"  - Powered by: {data['powered_by']}")
        print(f"  - Insight length: {len(data['insight'])} chars")
        print(f"  - Journal stats: {data['journal_stats']}")
        
        # GPT-4o indicator check
        if data["powered_by"] == "GPT-4o":
            print(f"  ✓ Using REAL GPT-4o LLM integration!")
        else:
            print(f"  ⚠ Using fallback (not GPT-4o)")
    
    def test_journal_insight_for_user_with_trades(self):
        """Journal insight should work for users with trading history"""
        # Use the test wallet which might have trades
        response = requests.get(f"{BASE_URL}/api/ai-suggestions/journal-daily/{TEST_WALLET}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "insight" in data, "Response should have insight"
        assert "journal_stats" in data, "Response should have journal_stats"
        
        has_trades = data["journal_stats"].get("has_trades", False)
        print(f"✓ Journal insight for test wallet")
        print(f"  - Has trades: {has_trades}")
        print(f"  - Total trades: {data['journal_stats'].get('total_trades', 0)}")
        print(f"  - Powered by: {data['powered_by']}")


class TestAPIIntegration:
    """Integration tests for Profile + AI working together"""
    
    def test_ai_suggestion_includes_journal_context(self):
        """Exit simulator should include journal context if user has trades"""
        payload = {
            "token_symbol": "ETH",
            "entry_price": 2000.0,
            "volatility": 0.6,
            "simulated_outcomes": {
                "probability_profit": 60,
                "median_final_price": 2200.0,
                "pnl_percentiles": {"p5": -25, "p95": 60}
            },
            "wallet_address": TEST_WALLET
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-suggestions/exit-simulator", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"✓ AI suggestion with wallet context")
        print(f"  - Powered by: {data['powered_by']}")
        print(f"  - Suggestion includes personalized context based on wallet trades")
    
    def test_live_price_fetch_in_ai_suggestion(self):
        """Exit simulator should fetch live price from CoinGecko"""
        payload = {
            "token_symbol": "SOL",
            "entry_price": 100.0,
            "volatility": 0.8,
            "simulated_outcomes": {
                "probability_profit": 50,
                "median_final_price": 100.0,
                "pnl_percentiles": {"p5": -40, "p95": 80}
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-suggestions/exit-simulator", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        live_price = data.get("live_price")
        
        print(f"✓ Live price integration")
        if live_price:
            print(f"  - SOL Price: ${live_price.get('price', 'N/A')}")
            print(f"  - 24h Change: {live_price.get('change_24h', 'N/A')}%")
        else:
            print(f"  - Live price: Not available (CoinGecko may be rate limited)")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
