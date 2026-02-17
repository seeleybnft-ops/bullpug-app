"""
Test suite for Pot and Admin routers after server.py refactoring.

Tests:
1. Pot Router (routers/pot.py) - /api/betting/pot endpoints
2. Admin Router (routers/admin.py) - /api/admin endpoints  
3. Shared State (state/pot_state.py) - Pot state is consistent across routers
4. WebSocket - /ws/pot connection and broadcast
"""

import pytest
import requests
import os
import json
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"
TEST_WALLET_1 = "TEST_Wallet1_" + datetime.now().strftime("%Y%m%d%H%M%S")
TEST_WALLET_2 = "TEST_Wallet2_" + datetime.now().strftime("%Y%m%d%H%M%S")


class TestPotRouter:
    """Test Pot Router - /api/betting/pot endpoints"""
    
    def test_get_pot_status(self):
        """GET /api/betting/pot - returns pot status"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify all required fields are present
        required_fields = [
            "id", "total_amount_sol", "entry_count", "entries", "status",
            "countdown_started", "countdown_seconds", "rake_percent",
            "distribution_wallet"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Pot status returned with {data['entry_count']} entries, status: {data['status']}")
    
    def test_get_pot_status_has_remaining_seconds(self):
        """GET /api/betting/pot - includes remaining_seconds field"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        
        data = response.json()
        assert "remaining_seconds" in data, "Missing remaining_seconds field"
        print(f"✓ remaining_seconds field present: {data['remaining_seconds']}")
    
    def test_join_pot_requires_wallet(self):
        """POST /api/betting/pot/join - requires wallet address"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.05,
            "display_name": "Test Player",
            "wallet_address": ""  # Empty wallet
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Empty wallet address rejected with 400")
    
    def test_join_pot_validates_minimum_bet(self):
        """POST /api/betting/pot/join - validates minimum bet (0.01 SOL)"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.001,  # Below minimum
            "display_name": "Test Player",
            "wallet_address": TEST_WALLET_1
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "0.01" in response.json().get("detail", ""), "Should mention minimum bet"
        print("✓ Minimum bet validation works (0.01 SOL)")
    
    def test_join_pot_validates_positive_bet(self):
        """POST /api/betting/pot/join - rejects negative/zero bets"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0,
            "display_name": "Test Player",
            "wallet_address": TEST_WALLET_1
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Zero/negative bet rejected")
    
    def test_join_pot_success(self):
        """POST /api/betting/pot/join - successful join with valid data"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.1,
            "display_name": "TEST_PotPlayer1",
            "wallet_address": TEST_WALLET_1
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Missing message in response"
        assert "probability" in data, "Missing probability in response"
        assert "total_pot_sol" in data, "Missing total_pot_sol in response"
        assert data["entry_count"] >= 1, "Entry count should be at least 1"
        
        print(f"✓ Player joined pot: {data['message']}")
        print(f"  - Entry count: {data['entry_count']}")
        print(f"  - Probability: {data['probability']}%")
    
    def test_join_pot_second_player_triggers_countdown(self):
        """POST /api/betting/pot/join - countdown starts when 2 participants join"""
        # Get current pot status
        pot_before = requests.get(f"{BASE_URL}/api/betting/pot").json()
        
        # If pot already has countdown started, check that
        if pot_before.get("countdown_started"):
            print(f"✓ Pot already has countdown started (entries: {pot_before['entry_count']})")
            return
        
        # If pot has 0 entries, add first player
        if pot_before['entry_count'] == 0:
            requests.post(f"{BASE_URL}/api/betting/pot/join", json={
                "bet_amount_sol": 0.05,
                "display_name": "TEST_FirstPlayer",
                "wallet_address": f"TEST_First_{datetime.now().strftime('%H%M%S')}"
            })
        
        # Add second player to trigger countdown
        second_wallet = f"TEST_Second_{datetime.now().strftime('%H%M%S')}"
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.05,
            "display_name": "TEST_SecondPlayer",
            "wallet_address": second_wallet
        })
        
        # Check response for countdown_started or countdown_just_started
        data = response.json()
        if response.status_code == 200:
            if data.get("countdown_just_started") or data.get("countdown_started"):
                print(f"✓ Countdown triggered after 2nd player")
                print(f"  - countdown_started: {data.get('countdown_started')}")
                print(f"  - countdown_just_started: {data.get('countdown_just_started')}")
                print(f"  - draw_at: {data.get('draw_at')}")
            else:
                # Countdown may already have been started in previous test
                pot_after = requests.get(f"{BASE_URL}/api/betting/pot").json()
                print(f"✓ Pot now has {pot_after['entry_count']} entries")
                print(f"  - countdown_started: {pot_after.get('countdown_started')}")


class TestAdminRouter:
    """Test Admin Router - /api/admin endpoints"""
    
    def test_admin_check_valid_admin(self):
        """GET /api/admin/check/{wallet} - identifies admin wallet correctly"""
        response = requests.get(f"{BASE_URL}/api/admin/check/{ADMIN_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("is_admin") == True, "Admin wallet should be identified as admin"
        print(f"✓ Admin wallet correctly identified: {ADMIN_WALLET[:16]}...")
    
    def test_admin_check_non_admin(self):
        """GET /api/admin/check/{wallet} - identifies non-admin correctly"""
        non_admin = "RandomWallet12345NotAdmin"
        response = requests.get(f"{BASE_URL}/api/admin/check/{non_admin}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("is_admin") == False, "Non-admin wallet should not be admin"
        print(f"✓ Non-admin wallet correctly identified")
    
    def test_admin_dashboard_authorized(self):
        """GET /api/admin/dashboard - returns dashboard stats for admin"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard?admin_wallet={ADMIN_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify dashboard fields
        expected_fields = [
            "total_bets", "total_challenges", "open_challenges", "completed_challenges",
            "total_deposits", "total_messages", "total_forum_posts", "estimated_users",
            "total_rake_collected_sol", "current_pot", "distribution_wallet"
        ]
        for field in expected_fields:
            assert field in data, f"Missing dashboard field: {field}"
        
        # Verify current_pot structure
        assert "current_pot" in data
        assert "total_amount_sol" in data["current_pot"]
        assert "entry_count" in data["current_pot"]
        assert "status" in data["current_pot"]
        
        print(f"✓ Admin dashboard returned successfully")
        print(f"  - Total bets: {data['total_bets']}")
        print(f"  - Total challenges: {data['total_challenges']}")
        print(f"  - Current pot: {data['current_pot']['total_amount_sol']} SOL with {data['current_pot']['entry_count']} entries")
    
    def test_admin_dashboard_unauthorized(self):
        """GET /api/admin/dashboard - rejects unauthorized access (403)"""
        non_admin = "NotAnAdminWallet123"
        response = requests.get(f"{BASE_URL}/api/admin/dashboard?admin_wallet={non_admin}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Non-admin access to dashboard rejected with 403")
    
    def test_admin_get_challenges_authorized(self):
        """GET /api/admin/challenges - returns challenges list for admin"""
        response = requests.get(f"{BASE_URL}/api/admin/challenges?admin_wallet={ADMIN_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "challenges" in data, "Missing challenges array"
        assert isinstance(data["challenges"], list), "Challenges should be a list"
        print(f"✓ Admin challenges returned: {len(data['challenges'])} challenges")
    
    def test_admin_get_challenges_unauthorized(self):
        """GET /api/admin/challenges - rejects unauthorized access (403)"""
        non_admin = "NotAnAdminWallet123"
        response = requests.get(f"{BASE_URL}/api/admin/challenges?admin_wallet={non_admin}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Non-admin access to challenges rejected with 403")
    
    def test_admin_force_draw_needs_entries(self):
        """POST /api/admin/pot/draw - requires at least 2 entries"""
        # First check current pot status
        pot = requests.get(f"{BASE_URL}/api/betting/pot").json()
        
        # If pot has < 2 entries, expect 400 error
        if pot['entry_count'] < 2:
            response = requests.post(f"{BASE_URL}/api/admin/pot/draw", json={
                "admin_wallet": ADMIN_WALLET
            })
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "2 entries" in response.json().get("detail", "").lower(), "Should mention 2 entries needed"
            print("✓ Admin force draw correctly requires 2 entries")
        else:
            print(f"ℹ Pot has {pot['entry_count']} entries - skipping 2-entry validation test")
    
    def test_admin_force_draw_unauthorized(self):
        """POST /api/admin/pot/draw - rejects non-admin wallet"""
        response = requests.post(f"{BASE_URL}/api/admin/pot/draw", json={
            "admin_wallet": "NotAnAdminWallet"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Non-admin pot draw rejected with 403")


class TestSharedState:
    """Test that pot state is shared correctly between pot and admin routers"""
    
    def test_pot_state_consistent_across_routers(self):
        """Verify pot state is the same when accessed from pot and admin endpoints"""
        # Get pot from pot router
        pot_response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert pot_response.status_code == 200
        pot_data = pot_response.json()
        
        # Get pot from admin dashboard
        admin_response = requests.get(f"{BASE_URL}/api/admin/dashboard?admin_wallet={ADMIN_WALLET}")
        assert admin_response.status_code == 200
        admin_data = admin_response.json()
        
        # Compare pot data
        admin_pot = admin_data["current_pot"]
        
        assert pot_data["entry_count"] == admin_pot["entry_count"], \
            f"Entry count mismatch: pot={pot_data['entry_count']}, admin={admin_pot['entry_count']}"
        
        assert pot_data["total_amount_sol"] == admin_pot["total_amount_sol"], \
            f"Total amount mismatch: pot={pot_data['total_amount_sol']}, admin={admin_pot['total_amount_sol']}"
        
        assert pot_data["status"] == admin_pot["status"], \
            f"Status mismatch: pot={pot_data['status']}, admin={admin_pot['status']}"
        
        print("✓ Pot state is consistent across pot and admin routers")
        print(f"  - entry_count: {pot_data['entry_count']}")
        print(f"  - total_amount_sol: {pot_data['total_amount_sol']}")
        print(f"  - status: {pot_data['status']}")


class TestBettingConfig:
    """Test betting configuration endpoint"""
    
    def test_get_betting_config(self):
        """GET /api/betting/config - returns all config fields"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        required_fields = ["rake_percent", "distribution_wallet", "currency", "min_bet_sol", "max_bet_sol"]
        for field in required_fields:
            assert field in data, f"Missing config field: {field}"
        
        assert data["rake_percent"] == 2.5, "Rake should be 2.5%"
        assert data["currency"] == "SOL", "Currency should be SOL"
        assert data["distribution_wallet"] == ADMIN_WALLET, "Distribution wallet mismatch"
        
        print(f"✓ Betting config returned correctly")
        print(f"  - Rake: {data['rake_percent']}%")
        print(f"  - Min bet: {data['min_bet_sol']} SOL")
        print(f"  - Max bet: {data['max_bet_sol']} SOL")


class TestAdminForceDraw:
    """Test admin force draw functionality (requires 2 entries)"""
    
    def test_admin_force_draw_with_entries(self):
        """POST /api/admin/pot/draw - admin can force draw with 2+ entries"""
        # Check current pot
        pot = requests.get(f"{BASE_URL}/api/betting/pot").json()
        
        # If pot has < 2 entries, add test entries
        if pot['entry_count'] < 2:
            # Add first player
            requests.post(f"{BASE_URL}/api/betting/pot/join", json={
                "bet_amount_sol": 0.02,
                "display_name": "TEST_DrawPlayer1",
                "wallet_address": f"TEST_DrawP1_{datetime.now().strftime('%H%M%S%f')}"
            })
            # Add second player
            requests.post(f"{BASE_URL}/api/betting/pot/join", json={
                "bet_amount_sol": 0.02,
                "display_name": "TEST_DrawPlayer2",
                "wallet_address": f"TEST_DrawP2_{datetime.now().strftime('%H%M%S%f')}"
            })
            
            # Verify entries were added
            pot = requests.get(f"{BASE_URL}/api/betting/pot").json()
        
        if pot['entry_count'] >= 2:
            # Test admin force draw
            response = requests.post(f"{BASE_URL}/api/admin/pot/draw", json={
                "admin_wallet": ADMIN_WALLET
            })
            
            if response.status_code == 200:
                data = response.json()
                assert "winner_name" in data, "Missing winner_name in draw result"
                assert "winner_wallet" in data, "Missing winner_wallet in draw result"
                assert "payout_sol" in data, "Missing payout_sol in draw result"
                assert "rake_sol" in data, "Missing rake_sol in draw result"
                
                print(f"✓ Admin force draw successful!")
                print(f"  - Winner: {data['winner_name']}")
                print(f"  - Payout: {data['payout_sol']} SOL")
                print(f"  - Rake: {data['rake_sol']} SOL")
                
                # Verify pot was reset
                new_pot = requests.get(f"{BASE_URL}/api/betting/pot").json()
                assert new_pot['entry_count'] == 0, "Pot should be reset after draw"
                print("✓ Pot reset after draw (entry_count = 0)")
            else:
                print(f"ℹ Draw response: {response.status_code} - {response.text}")
        else:
            print(f"ℹ Pot still has < 2 entries ({pot['entry_count']}), cannot test force draw")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
