"""
Tests for Iteration 15 features:
1. Pot Game Countdown Timer (starts when 2 participants join)
2. Wallet Page Hidden from Navbar/Footer (UI test)
3. Reflections Calculator with Blowfish fee structure
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bullpug-cosmic.preview.emergentagent.com').rstrip('/')

class TestPotGameCountdown:
    """Tests for Pot Game 60s countdown that starts when 2 participants join"""
    
    def test_get_pot_status_initial(self):
        """Test GET /api/betting/pot returns pot status with countdown fields"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        
        data = response.json()
        # Verify countdown fields exist
        assert "countdown_started" in data, "Missing countdown_started field"
        assert "countdown_seconds" in data, "Missing countdown_seconds field"
        assert "remaining_seconds" in data, "Missing remaining_seconds field"
        assert "draw_at" in data, "Missing draw_at field"
        assert "entry_count" in data, "Missing entry_count field"
        
        # Verify countdown_seconds default value
        assert data["countdown_seconds"] == 60, f"Expected countdown_seconds=60, got {data['countdown_seconds']}"
        
        print(f"✓ Pot status returned with countdown fields: countdown_started={data['countdown_started']}, remaining_seconds={data['remaining_seconds']}")
    
    def test_pot_join_first_participant_no_countdown(self):
        """Test joining pot with first participant - countdown should NOT start"""
        # First, get current pot status
        initial_status = requests.get(f"{BASE_URL}/api/betting/pot").json()
        initial_count = initial_status.get("entry_count", 0)
        
        # Join pot with first participant
        join_data = {
            "bet_amount_sol": 0.05,
            "wallet_address": "TEST_Wallet_Countdown_1",
            "display_name": "TEST_CountdownPlayer1"
        }
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json=join_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "countdown_started" in data, "Missing countdown_started in response"
        
        # If this was the first participant (entry_count was 0), countdown should NOT have started
        if initial_count == 0:
            assert data["countdown_started"] == False, "Countdown should NOT start with only 1 participant"
            assert data.get("countdown_just_started") == False, "countdown_just_started should be False"
            print("✓ First participant joined - countdown NOT started (expected)")
        else:
            print(f"✓ Pot had {initial_count} participants before join, countdown_started={data['countdown_started']}")
    
    def test_pot_join_second_participant_starts_countdown(self):
        """Test joining pot with second participant - countdown SHOULD start"""
        # Get current pot status
        status = requests.get(f"{BASE_URL}/api/betting/pot").json()
        current_count = status.get("entry_count", 0)
        countdown_already_started = status.get("countdown_started", False)
        
        # Join pot with second participant
        join_data = {
            "bet_amount_sol": 0.05,
            "wallet_address": "TEST_Wallet_Countdown_2",
            "display_name": "TEST_CountdownPlayer2"
        }
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json=join_data)
        assert response.status_code == 200
        
        data = response.json()
        
        # If countdown wasn't started before and we had 1 participant, this should start it
        if current_count == 1 and not countdown_already_started:
            assert data["countdown_started"] == True, "Countdown should start with 2nd participant"
            assert data.get("countdown_just_started") == True, "countdown_just_started should be True"
            assert data.get("draw_at") is not None, "draw_at should be set when countdown starts"
            print(f"✓ Second participant joined - countdown STARTED! draw_at={data.get('draw_at')}")
        else:
            print(f"✓ Pot state: {current_count} participants, countdown_started={data['countdown_started']}")
    
    def test_pot_status_shows_remaining_seconds(self):
        """Test that pot status shows remaining_seconds when countdown is active"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        
        data = response.json()
        if data.get("countdown_started") and data.get("draw_at"):
            assert data["remaining_seconds"] is not None, "remaining_seconds should be calculated when countdown active"
            assert isinstance(data["remaining_seconds"], int), "remaining_seconds should be an integer"
            assert data["remaining_seconds"] >= 0, "remaining_seconds should not be negative"
            print(f"✓ Countdown active: remaining_seconds={data['remaining_seconds']}")
        else:
            print(f"✓ Countdown not active: remaining_seconds={data.get('remaining_seconds')}")


class TestReflectionsCalculatorBlowfish:
    """Tests for Reflections Calculator with Blowfish fee structure"""
    
    def test_reflections_calculate_with_blowfish_rate(self):
        """Test POST /api/reflections/calculate with Blowfish effective rate (1% x 80% = 0.8%)"""
        # Blowfish fee structure: 1% trading fee, 80% to holders = 0.8% effective rate
        calc_data = {
            "token_holdings": 10000000,
            "volume_24h": 89000,
            "reflection_rate": 0.8  # 1% fee × 80% to holders = 0.8%
        }
        response = requests.post(f"{BASE_URL}/api/reflections/calculate", json=calc_data)
        assert response.status_code == 200
        
        data = response.json()
        # Verify required fields
        assert "holdings" in data, "Missing holdings in response"
        assert "holder_share_percent" in data, "Missing holder_share_percent"
        assert "reflection_rate" in data, "Missing reflection_rate"
        assert "daily" in data, "Missing daily reflections"
        assert "weekly" in data, "Missing weekly reflections"
        assert "monthly" in data, "Missing monthly reflections"
        assert "yearly" in data, "Missing yearly reflections"
        assert "estimated_apy" in data, "Missing estimated_apy"
        
        # Verify the reflection_rate matches input
        assert data["reflection_rate"] == 0.8, f"Expected reflection_rate=0.8, got {data['reflection_rate']}"
        
        # Verify calculations are reasonable
        assert data["daily"]["usd"] > 0, "Daily reflections should be positive"
        assert data["yearly"]["usd"] > data["monthly"]["usd"] > data["weekly"]["usd"] > data["daily"]["usd"], "Reflections should scale with time"
        
        print(f"✓ Reflections calculated: daily=${data['daily']['usd']}, APY={data['estimated_apy']}%")
    
    def test_reflections_with_various_holdings(self):
        """Test reflections calculation with different token holdings"""
        holdings_tests = [1000000, 10000000, 50000000, 100000000]
        
        prev_daily = 0
        for holdings in holdings_tests:
            calc_data = {
                "token_holdings": holdings,
                "volume_24h": 89000,
                "reflection_rate": 0.8
            }
            response = requests.post(f"{BASE_URL}/api/reflections/calculate", json=calc_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["holdings"] == holdings
            assert data["daily"]["usd"] > prev_daily, f"Higher holdings should yield higher reflections"
            prev_daily = data["daily"]["usd"]
            print(f"  Holdings: {holdings:,} -> Daily: ${data['daily']['usd']:.4f}")
        
        print(f"✓ Reflections scale correctly with token holdings")
    
    def test_reflections_with_zero_holdings_returns_zero(self):
        """Test that zero or negative holdings return appropriate error or zero reflections"""
        calc_data = {
            "token_holdings": 0,
            "volume_24h": 89000,
            "reflection_rate": 0.8
        }
        response = requests.post(f"{BASE_URL}/api/reflections/calculate", json=calc_data)
        # May return 200 with zero or 400 error - both acceptable
        if response.status_code == 200:
            data = response.json()
            assert data["daily"]["usd"] == 0, "Zero holdings should yield zero reflections"
            print("✓ Zero holdings returns zero reflections")
        else:
            print(f"✓ Zero holdings rejected with status {response.status_code}")


class TestBettingConfig:
    """Tests for betting configuration endpoint"""
    
    def test_betting_config_returns_all_fields(self):
        """Test GET /api/betting/config returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "rake_percent" in data, "Missing rake_percent"
        assert "distribution_wallet" in data, "Missing distribution_wallet"
        assert "currency" in data, "Missing currency"
        assert "min_bet_sol" in data, "Missing min_bet_sol"
        assert "max_bet_sol" in data, "Missing max_bet_sol"
        
        assert data["rake_percent"] == 2.5, f"Expected rake_percent=2.5, got {data['rake_percent']}"
        assert data["currency"] == "SOL"
        
        print(f"✓ Betting config: rake={data['rake_percent']}%, limits={data['min_bet_sol']}-{data['max_bet_sol']} SOL")


class TestChallengesEndpoint:
    """Tests for P2P challenges endpoint"""
    
    def test_get_open_challenges(self):
        """Test GET /api/betting/challenges returns challenges list"""
        response = requests.get(f"{BASE_URL}/api/betting/challenges")
        assert response.status_code == 200
        
        data = response.json()
        assert "challenges" in data, "Missing challenges array"
        assert isinstance(data["challenges"], list), "challenges should be a list"
        print(f"✓ Open challenges endpoint working: {len(data['challenges'])} challenges")
    
    def test_get_betting_history(self):
        """Test GET /api/betting/history returns history"""
        response = requests.get(f"{BASE_URL}/api/betting/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "history" in data, "Missing history array"
        print(f"✓ Betting history endpoint working: {len(data['history'])} entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
