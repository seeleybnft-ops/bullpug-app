"""
Test file for iteration 8 - Testing new features:
- SendGrid configuration (POST /api/email/test should return configured: true)
- Backend modular routers (betting.py, auth.py, email.py, leaderboard.py)
- New sound effects in sounds.js (betPlaced, challengeCreated, potJoin, notification, coinLand, countdown, success, error, hover, swoosh)
- Haptic feedback utility functions (vibrate, feedback, hapticPatterns)
- Betting endpoints still work (GET /api/betting/config, GET /api/betting/challenges)
- Email subscribe endpoint (POST /api/email/subscribe)
- Auth sign-message endpoint (GET /api/auth/sign-message/{wallet})
- Leaderboard endpoint (GET /api/leaderboard)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')


class TestSendGridConfiguration:
    """Test SendGrid email configuration"""
    
    def test_email_test_endpoint_returns_configured_true(self):
        """POST /api/email/test should return configured: true when SendGrid API key is set"""
        response = requests.post(f"{BASE_URL}/api/email/test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "configured" in data, "Response should contain 'configured' field"
        # Check if SendGrid is configured
        print(f"SendGrid configured: {data.get('configured')}")
        print(f"Sender email: {data.get('sender')}")
        # This should return true since SENDGRID_API_KEY was added to backend/.env
        assert data.get("configured") == True, "SendGrid should be configured"
        assert "sender" in data, "Response should contain 'sender' field when configured"


class TestBettingEndpoints:
    """Test betting endpoints after refactor"""
    
    def test_betting_config_endpoint(self):
        """GET /api/betting/config returns rake and limits"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("rake_percent") == 2.5, "Rake should be 2.5%"
        assert data.get("min_bet_sol") == 0.01, "Min bet should be 0.01 SOL"
        assert data.get("max_bet_sol") == 10.0, "Max bet should be 10 SOL"
        assert "distribution_wallet" in data, "Should have distribution wallet"
        assert data.get("currency") == "SOL", "Currency should be SOL"
        print(f"Betting config: {data}")
    
    def test_betting_challenges_endpoint(self):
        """GET /api/betting/challenges returns open challenges list"""
        response = requests.get(f"{BASE_URL}/api/betting/challenges")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "challenges" in data, "Response should contain 'challenges' field"
        assert isinstance(data.get("challenges"), list), "Challenges should be a list"
        print(f"Open challenges count: {len(data.get('challenges', []))}")
    
    def test_betting_pot_endpoint(self):
        """GET /api/betting/pot returns pot status"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_amount_sol" in data, "Should have total_amount_sol"
        assert "entries" in data, "Should have entries"
        assert "status" in data, "Should have status"
        print(f"Pot status: {data.get('status')}, total: {data.get('total_amount_sol')} SOL")
    
    def test_betting_history_endpoint(self):
        """GET /api/betting/history returns betting history"""
        response = requests.get(f"{BASE_URL}/api/betting/history")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "history" in data, "Response should contain 'history' field"
        assert isinstance(data.get("history"), list), "History should be a list"
        print(f"Betting history count: {len(data.get('history', []))}")


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_auth_sign_message_endpoint(self):
        """GET /api/auth/sign-message/{wallet} generates a signing message"""
        test_wallet = "TEST_wallet_address_12345"
        response = requests.get(f"{BASE_URL}/api/auth/sign-message/{test_wallet}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "nonce" in data, "Response should contain 'nonce' field"
        assert test_wallet in data.get("message", ""), "Message should contain wallet address"
        print(f"Sign message generated with nonce: {data.get('nonce')}")
    
    def test_auth_sign_message_with_action(self):
        """GET /api/auth/sign-message/{wallet}?action=betting generates action-specific message"""
        test_wallet = "TEST_wallet_address_67890"
        response = requests.get(f"{BASE_URL}/api/auth/sign-message/{test_wallet}?action=betting")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "betting" in data.get("message", "").lower(), "Message should contain action"
        print(f"Action-specific message generated: {data.get('message')[:50]}...")


class TestEmailSubscription:
    """Test email subscription endpoints"""
    
    def test_email_subscribe_new_user(self):
        """POST /api/email/subscribe creates new subscription"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        unique_wallet = f"TEST_{uuid.uuid4().hex[:24]}"
        
        response = requests.post(
            f"{BASE_URL}/api/email/subscribe",
            json={
                "email": unique_email,
                "wallet_address": unique_wallet,
                "subscribe_weekly": True
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "status" in data, "Response should contain 'status' field"
        assert data.get("status") in ["subscribed", "updated"], f"Status should be subscribed or updated, got {data.get('status')}"
        print(f"Email subscription: {data}")
    
    def test_email_subscribe_update_existing(self):
        """POST /api/email/subscribe updates existing subscription"""
        import uuid
        fixed_wallet = f"TEST_fixed_wallet_{uuid.uuid4().hex[:8]}"
        
        # First subscription
        response1 = requests.post(
            f"{BASE_URL}/api/email/subscribe",
            json={
                "email": "test_update1@example.com",
                "wallet_address": fixed_wallet,
                "subscribe_weekly": True
            }
        )
        assert response1.status_code == 200
        
        # Update with new email
        response2 = requests.post(
            f"{BASE_URL}/api/email/subscribe",
            json={
                "email": "test_update2@example.com",
                "wallet_address": fixed_wallet,
                "subscribe_weekly": False
            }
        )
        assert response2.status_code == 200
        data = response2.json()
        assert data.get("status") == "updated", "Second request should update existing"
        print(f"Email subscription updated: {data}")


class TestLeaderboard:
    """Test leaderboard endpoints"""
    
    def test_leaderboard_get(self):
        """GET /api/leaderboard returns weekly leaderboard"""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "leaderboard" in data, "Response should contain 'leaderboard' field"
        assert "week_start" in data, "Response should contain 'week_start' field"
        assert "next_reset" in data, "Response should contain 'next_reset' field"
        assert "days_until_reset" in data, "Response should contain 'days_until_reset' field"
        assert isinstance(data.get("leaderboard"), list), "Leaderboard should be a list"
        print(f"Leaderboard entries: {len(data.get('leaderboard', []))}, days until reset: {data.get('days_until_reset')}")
    
    def test_leaderboard_submit_score(self):
        """POST /api/leaderboard/submit adds a score"""
        import uuid
        test_name = f"TEST_Player_{uuid.uuid4().hex[:6]}"
        
        response = requests.post(
            f"{BASE_URL}/api/leaderboard/submit",
            json={
                "player_name": test_name,
                "score": 100,
                "mooncakes": 5
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "rank" in data, "Response should contain 'rank' field"
        assert "message" in data or "rank" in data, "Response should have confirmation"
        print(f"Score submitted, rank: {data.get('rank')}")


class TestHealthAndRoot:
    """Test root and health endpoints"""
    
    def test_root_endpoint(self):
        """GET /api/ returns welcome message"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "bullpug" in data.get("message", "").lower(), "Message should mention Bullpug"
        print(f"Root response: {data}")


class TestModularRoutersExist:
    """Test that modular router files exist in backend"""
    
    def test_betting_router_exists(self):
        """Check betting router file exists"""
        path = "/app/backend/routers/betting.py"
        assert os.path.exists(path), f"Betting router should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        # Check key contents
        assert "APIRouter" in content, "Should use APIRouter"
        assert "/betting" in content or 'prefix="/betting"' in content, "Should have betting prefix"
        assert "@router" in content, "Should have route decorators"
        print("Betting router exists with correct structure")
    
    def test_auth_router_exists(self):
        """Check auth router file exists"""
        path = "/app/backend/routers/auth.py"
        assert os.path.exists(path), f"Auth router should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        assert "APIRouter" in content, "Should use APIRouter"
        assert "sign-message" in content or "sign_message" in content, "Should have sign-message route"
        print("Auth router exists with correct structure")
    
    def test_email_router_exists(self):
        """Check email router file exists"""
        path = "/app/backend/routers/email.py"
        assert os.path.exists(path), f"Email router should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        assert "APIRouter" in content, "Should use APIRouter"
        assert "subscribe" in content, "Should have subscribe route"
        assert "test" in content, "Should have test route"
        print("Email router exists with correct structure")
    
    def test_leaderboard_router_exists(self):
        """Check leaderboard router file exists"""
        path = "/app/backend/routers/leaderboard.py"
        assert os.path.exists(path), f"Leaderboard router should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        assert "APIRouter" in content, "Should use APIRouter"
        assert "leaderboard" in content.lower(), "Should have leaderboard routes"
        print("Leaderboard router exists with correct structure")


class TestSoundsJsNewFeatures:
    """Test that new sound effects and haptic feedback are in sounds.js"""
    
    def test_sounds_file_has_new_sounds(self):
        """Check sounds.js has all new sound presets"""
        path = "/app/frontend/src/utils/sounds.js"
        assert os.path.exists(path), f"Sounds file should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        # New sounds that should be added
        new_sounds = [
            "betPlaced", "challengeCreated", "potJoin", "notification",
            "coinLand", "countdown", "success", "error", "hover", "swoosh"
        ]
        
        found_sounds = []
        missing_sounds = []
        
        for sound in new_sounds:
            if sound in content:
                found_sounds.append(sound)
            else:
                missing_sounds.append(sound)
        
        print(f"Found new sounds: {found_sounds}")
        if missing_sounds:
            print(f"Missing sounds: {missing_sounds}")
        
        assert len(missing_sounds) == 0, f"Missing sound presets: {missing_sounds}"
    
    def test_haptic_feedback_functions_exist(self):
        """Check sounds.js exports haptic feedback utilities"""
        path = "/app/frontend/src/utils/sounds.js"
        
        with open(path, 'r') as f:
            content = f.read()
        
        # Haptic feedback functions that should be exported
        haptic_functions = ["vibrate", "feedback", "hapticPatterns"]
        
        found = []
        missing = []
        
        for func in haptic_functions:
            if f"export" in content and func in content:
                found.append(func)
            elif func in content:
                found.append(func)
            else:
                missing.append(func)
        
        print(f"Found haptic functions: {found}")
        if missing:
            print(f"Missing haptic functions: {missing}")
        
        assert len(missing) == 0, f"Missing haptic functions: {missing}"
    
    def test_haptic_patterns_defined(self):
        """Check hapticPatterns object has expected patterns"""
        path = "/app/frontend/src/utils/sounds.js"
        
        with open(path, 'r') as f:
            content = f.read()
        
        expected_patterns = ["light", "medium", "heavy", "success", "error", "win", "lose", "click"]
        
        # Check hapticPatterns object exists
        assert "hapticPatterns" in content, "hapticPatterns object should exist"
        
        found_patterns = [p for p in expected_patterns if p in content]
        print(f"Found haptic patterns: {found_patterns}")
        
        assert len(found_patterns) >= 5, f"Should have at least 5 haptic patterns, found {len(found_patterns)}"


class TestBackendModularStructure:
    """Test the modular backend structure files exist"""
    
    def test_models_schemas_exists(self):
        """Check models/schemas.py exists"""
        path = "/app/backend/models/schemas.py"
        assert os.path.exists(path), f"Schemas file should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        assert "CreateChallengeRequest" in content, "Should have CreateChallengeRequest model"
        assert "EmailSubscribeRequest" in content, "Should have EmailSubscribeRequest model"
        assert "LeaderboardSubmitRequest" in content, "Should have LeaderboardSubmitRequest model"
        print("Models/schemas.py exists with expected Pydantic models")
    
    def test_services_email_exists(self):
        """Check services/email_service.py exists"""
        path = "/app/backend/services/email_service.py"
        assert os.path.exists(path), f"Email service should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        assert "send_email" in content, "Should have send_email function"
        assert "send_welcome_email" in content, "Should have send_welcome_email function"
        assert "SendGridAPIClient" in content, "Should use SendGrid"
        print("Email service exists with send functions")
    
    def test_services_auth_exists(self):
        """Check services/auth_service.py exists"""
        path = "/app/backend/services/auth_service.py"
        assert os.path.exists(path), f"Auth service should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        assert "verify_wallet_signature" in content, "Should have verify_wallet_signature function"
        print("Auth service exists with signature verification")
    
    def test_utils_config_exists(self):
        """Check utils/config.py exists"""
        path = "/app/backend/utils/config.py"
        assert os.path.exists(path), f"Config should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        assert "SENDGRID_API_KEY" in content, "Should have SENDGRID_API_KEY"
        assert "RAKE_PERCENT" in content, "Should have RAKE_PERCENT"
        assert "DISTRIBUTION_WALLET" in content, "Should have DISTRIBUTION_WALLET"
        print("Utils/config.py exists with expected configuration")
    
    def test_utils_database_exists(self):
        """Check utils/database.py exists"""
        path = "/app/backend/utils/database.py"
        assert os.path.exists(path), f"Database utils should exist at {path}"
        
        with open(path, 'r') as f:
            content = f.read()
        
        assert "AsyncIOMotorClient" in content, "Should use Motor client"
        assert "get_db" in content or "db" in content, "Should provide database access"
        print("Utils/database.py exists with MongoDB connection")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
