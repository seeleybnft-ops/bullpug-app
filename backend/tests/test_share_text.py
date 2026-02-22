"""
Test suite for Social Sharing feature - GET /api/showcase/share-text/{wallet}
Tests the dynamic share text generation for Twitter/X and Telegram sharing
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bullpug-trades.preview.emergentagent.com')


class TestShareTextEndpoint:
    """Tests for GET /api/showcase/share-text/{wallet} endpoint"""
    
    def test_share_text_returns_200(self):
        """Share text endpoint should return 200 for valid wallet"""
        response = requests.get(f"{BASE_URL}/api/showcase/share-text/TEST_giftflow_recipient_ebb244d0")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Share text endpoint returns 200")
    
    def test_share_text_has_required_fields(self):
        """Response should contain share_text, stats, hashtags, mentions"""
        response = requests.get(f"{BASE_URL}/api/showcase/share-text/TEST_giftflow_recipient_ebb244d0")
        data = response.json()
        
        assert "share_text" in data, "Missing 'share_text' field"
        assert "stats" in data, "Missing 'stats' field"
        assert "hashtags" in data, "Missing 'hashtags' field"
        assert "mentions" in data, "Missing 'mentions' field"
        print("PASS: Response contains all required fields (share_text, stats, hashtags, mentions)")
    
    def test_share_text_stats_structure(self):
        """Stats should contain total_owned, total_skins, completion_percent, has_ethereal"""
        response = requests.get(f"{BASE_URL}/api/showcase/share-text/TEST_giftflow_recipient_ebb244d0")
        stats = response.json()["stats"]
        
        assert "total_owned" in stats, "Missing 'total_owned' in stats"
        assert "total_skins" in stats, "Missing 'total_skins' in stats"
        assert "completion_percent" in stats, "Missing 'completion_percent' in stats"
        assert "has_ethereal" in stats, "Missing 'has_ethereal' in stats"
        
        assert isinstance(stats["total_owned"], int), "total_owned should be int"
        assert isinstance(stats["total_skins"], int), "total_skins should be int"
        assert isinstance(stats["completion_percent"], (int, float)), "completion_percent should be numeric"
        assert isinstance(stats["has_ethereal"], bool), "has_ethereal should be bool"
        print("PASS: Stats structure is correct")
    
    def test_share_text_contains_collection_info(self):
        """Share text should include collection count and emojis"""
        response = requests.get(f"{BASE_URL}/api/showcase/share-text/TEST_giftflow_recipient_ebb244d0")
        share_text = response.json()["share_text"]
        
        # Should contain skin count info
        assert "skins" in share_text.lower(), "Share text should mention skins"
        # Should contain emojis for engagement
        assert any(emoji in share_text for emoji in ["🚀", "✨", "🎯", "🔥", "🏆", "💎"]), "Share text should contain emojis"
        print("PASS: Share text contains collection info and emojis")
    
    def test_share_text_has_bullpug_mention(self):
        """Share text should mention @BullpugSOL"""
        response = requests.get(f"{BASE_URL}/api/showcase/share-text/TEST_giftflow_recipient_ebb244d0")
        data = response.json()
        
        assert "@BullpugSOL" in data["share_text"], "Share text should mention @BullpugSOL"
        assert "@BullpugSOL" in data["mentions"], "Mentions should include @BullpugSOL"
        print("PASS: Share text mentions @BullpugSOL")
    
    def test_share_text_has_hashtags(self):
        """Share text should include hashtags for discoverability"""
        response = requests.get(f"{BASE_URL}/api/showcase/share-text/TEST_giftflow_recipient_ebb244d0")
        hashtags = response.json()["hashtags"]
        
        assert "Bullpug" in hashtags, "Hashtags should include Bullpug"
        assert "Solana" in hashtags, "Hashtags should include Solana"
        assert "#Bullpug" in response.json()["share_text"], "Share text should contain #Bullpug"
        print("PASS: Share text has proper hashtags")
    
    def test_share_text_for_new_collector(self):
        """New collector (low collection) should get starter share text"""
        response = requests.get(f"{BASE_URL}/api/showcase/share-text/TEST_new_collector_share")
        data = response.json()
        
        # New collector should have low completion
        assert data["stats"]["total_owned"] <= 3, "New collector should have few skins"
        # Share text should encourage collecting
        assert any(word in data["share_text"].lower() for word in ["started", "collecting", "goal"]), \
            "New collector text should encourage collecting"
        print("PASS: New collector gets appropriate share text")
    
    def test_share_text_total_skins_matches(self):
        """Total skins in share text stats should match main showcase"""
        share_response = requests.get(f"{BASE_URL}/api/showcase/share-text/TEST_giftflow_recipient_ebb244d0")
        showcase_response = requests.get(f"{BASE_URL}/api/showcase/TEST_giftflow_recipient_ebb244d0")
        
        share_stats = share_response.json()["stats"]
        showcase_stats = showcase_response.json()["stats"]
        
        assert share_stats["total_skins"] == showcase_stats["total_skins"], \
            f"Total skins mismatch: share={share_stats['total_skins']}, showcase={showcase_stats['total_skins']}"
        print("PASS: Total skins count matches between share-text and showcase endpoints")


class TestWebSocketManagersImport:
    """Tests to verify WebSocket managers are properly imported from utils module"""
    
    def test_server_running(self):
        """Server should be running - confirms imports are working"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, "Server should be running"
        assert "Bullpug" in response.json().get("message", ""), "API should return Bullpug message"
        print("PASS: Server is running - WebSocket managers imported correctly")
    
    def test_pot_endpoint_works(self):
        """P2P Pot endpoint uses pot_ws_manager - should work if imports are correct"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200, f"Pot endpoint should work, got {response.status_code}"
        data = response.json()
        assert "total_amount_sol" in data, "Pot response should have total_amount_sol"
        print("PASS: Pot endpoint works - pot_ws_manager imported correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
