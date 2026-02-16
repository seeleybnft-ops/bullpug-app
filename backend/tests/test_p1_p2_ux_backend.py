"""
Tests for P1 UX improvements (sound effects, animations) and P2 backend refactoring.
Tests verify:
1. Backend API endpoints still work after refactoring
2. Backend modular files exist and are importable
"""
import pytest
import requests
import os
import importlib.util

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestBackendAPIsAfterRefactoring:
    """Test existing APIs still work after P2 backend refactoring"""
    
    def test_betting_config_endpoint(self):
        """GET /api/betting/config - returns betting configuration"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        data = response.json()
        
        # Verify config structure
        assert "rake_percent" in data
        assert data["rake_percent"] == 2.5
        assert "distribution_wallet" in data
        assert "min_bet_sol" in data
        assert "max_bet_sol" in data
        assert data["min_bet_sol"] == 0.01
        assert data["max_bet_sol"] == 10
        print("✓ Betting config endpoint working correctly")
    
    def test_betting_challenges_endpoint(self):
        """GET /api/betting/challenges - returns open challenges"""
        response = requests.get(f"{BASE_URL}/api/betting/challenges?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        assert "challenges" in data
        assert isinstance(data["challenges"], list)
        print(f"✓ Betting challenges endpoint working - {len(data['challenges'])} challenges")
    
    def test_leaderboard_endpoint(self):
        """GET /api/leaderboard - returns game leaderboard"""
        response = requests.get(f"{BASE_URL}/api/leaderboard?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert "leaderboard" in data
        assert "days_until_reset" in data
        assert "next_reset" in data
        print(f"✓ Leaderboard endpoint working - {len(data['leaderboard'])} entries")
    
    def test_api_root_health(self):
        """GET /api/ - health check"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Bullpug" in data["message"]
        print("✓ API root health check working")
    
    def test_betting_pot_endpoint(self):
        """GET /api/betting/pot - returns current pot status"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "total_amount_sol" in data
        print("✓ Betting pot endpoint working")
    
    def test_betting_history_endpoint(self):
        """GET /api/betting/history - returns betting history"""
        response = requests.get(f"{BASE_URL}/api/betting/history?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert "history" in data
        assert isinstance(data["history"], list)
        print(f"✓ Betting history endpoint working - {len(data['history'])} entries")


class TestBackendModularStructure:
    """Test P2 backend refactoring - modular file structure"""
    
    def test_models_schemas_file_exists(self):
        """models/schemas.py exists and contains Pydantic models"""
        schemas_path = "/app/backend/models/schemas.py"
        assert os.path.exists(schemas_path), "models/schemas.py should exist"
        
        # Check file content has expected models
        with open(schemas_path, 'r') as f:
            content = f.read()
        
        expected_models = [
            "CreateChallengeRequest",
            "AcceptChallengeRequest",
            "P2PPotJoinRequest",
            "CreatePostRequest",
            "LeaderboardSubmitRequest",
        ]
        
        for model in expected_models:
            assert model in content, f"models/schemas.py should contain {model}"
        
        print(f"✓ models/schemas.py exists with {len(expected_models)} expected models")
    
    def test_services_email_service_exists(self):
        """services/email_service.py exists with email functions"""
        email_path = "/app/backend/services/email_service.py"
        assert os.path.exists(email_path), "services/email_service.py should exist"
        
        with open(email_path, 'r') as f:
            content = f.read()
        
        expected_functions = ["send_email", "send_welcome_email", "send_weekly_summary_email"]
        
        for func in expected_functions:
            assert func in content, f"email_service.py should contain {func}"
        
        print(f"✓ services/email_service.py exists with {len(expected_functions)} expected functions")
    
    def test_services_auth_service_exists(self):
        """services/auth_service.py exists with signature verification"""
        auth_path = "/app/backend/services/auth_service.py"
        assert os.path.exists(auth_path), "services/auth_service.py should exist"
        
        with open(auth_path, 'r') as f:
            content = f.read()
        
        expected_functions = ["verify_wallet_signature", "verify_request_signature"]
        
        for func in expected_functions:
            assert func in content, f"auth_service.py should contain {func}"
        
        print(f"✓ services/auth_service.py exists with {len(expected_functions)} expected functions")
    
    def test_utils_config_exists(self):
        """utils/config.py exists with app configuration"""
        config_path = "/app/backend/utils/config.py"
        assert os.path.exists(config_path), "utils/config.py should exist"
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        expected_configs = ["RAKE_PERCENT", "DISTRIBUTION_WALLET", "ADMIN_WALLETS"]
        
        for config in expected_configs:
            assert config in content, f"config.py should contain {config}"
        
        print(f"✓ utils/config.py exists with {len(expected_configs)} expected configs")
    
    def test_utils_database_exists(self):
        """utils/database.py exists with DB connection"""
        db_path = "/app/backend/utils/database.py"
        assert os.path.exists(db_path), "utils/database.py should exist"
        
        with open(db_path, 'r') as f:
            content = f.read()
        
        expected_items = ["AsyncIOMotorClient", "mongo_client", "db", "get_db"]
        
        for item in expected_items:
            assert item in content, f"database.py should contain {item}"
        
        print(f"✓ utils/database.py exists with {len(expected_items)} expected items")
    
    def test_routers_directory_exists(self):
        """routers/ directory exists for future route modularization"""
        routers_path = "/app/backend/routers"
        assert os.path.isdir(routers_path), "routers/ directory should exist"
        
        init_file = os.path.join(routers_path, "__init__.py")
        assert os.path.exists(init_file), "routers/__init__.py should exist"
        
        print("✓ routers/ directory exists for future route modularization")


class TestFrontendSoundFiles:
    """Test P1 UX - Sound and animation files exist"""
    
    def test_sounds_utility_file_exists(self):
        """frontend/src/utils/sounds.js exists with sound functions"""
        sounds_path = "/app/frontend/src/utils/sounds.js"
        assert os.path.exists(sounds_path), "sounds.js should exist"
        
        with open(sounds_path, 'r') as f:
            content = f.read()
        
        expected_items = [
            "playTone",
            "playCoinFlipSequence", 
            "isSoundEnabled",
            "setSoundEnabled",
            "playSoundIfEnabled",
            "Web Audio API",
        ]
        
        for item in expected_items:
            assert item in content, f"sounds.js should contain {item}"
        
        # Check sound presets exist
        sound_types = ["win", "lose", "flip", "click", "collect", "powerup", "gameover", "jump", "newHighScore"]
        for sound in sound_types:
            assert sound in content, f"sounds.js should contain '{sound}' sound preset"
        
        print(f"✓ sounds.js exists with {len(sound_types)} sound presets")
    
    def test_animations_css_file_exists(self):
        """frontend/src/styles/animations.css exists with CSS animations"""
        css_path = "/app/frontend/src/styles/animations.css"
        assert os.path.exists(css_path), "animations.css should exist"
        
        with open(css_path, 'r') as f:
            content = f.read()
        
        expected_animations = [
            "@keyframes coinFlip",
            "@keyframes winPulse",
            "@keyframes losePulse",
            "@keyframes confetti-fall",
            ".coin-flip-animation",
            ".win-pulse",
            ".lose-pulse",
            ".confetti-particle",
        ]
        
        for anim in expected_animations:
            assert anim in content, f"animations.css should contain '{anim}'"
        
        print(f"✓ animations.css exists with {len(expected_animations)} expected animations")
    
    def test_betting_arena_imports_sounds(self):
        """BettingArena.js imports sound utilities"""
        arena_path = "/app/frontend/src/pages/BettingArena.js"
        assert os.path.exists(arena_path), "BettingArena.js should exist"
        
        with open(arena_path, 'r') as f:
            content = f.read()
        
        expected_items = [
            "playSoundIfEnabled",
            "isSoundEnabled",
            "setSoundEnabled",
            "playCoinFlipSequence",
            "Volume2",
            "VolumeX",
            "soundOn",
            "toggleSound",
            'data-testid="sound-toggle"',
            "@/styles/animations.css",
        ]
        
        for item in expected_items:
            assert item in content, f"BettingArena.js should contain '{item}'"
        
        print("✓ BettingArena.js correctly imports sound utilities and has sound toggle")
    
    def test_speedrun_game_imports_sounds(self):
        """SpeedRunGame.js imports sound utilities"""
        game_path = "/app/frontend/src/pages/SpeedRunGame.js"
        assert os.path.exists(game_path), "SpeedRunGame.js should exist"
        
        with open(game_path, 'r') as f:
            content = f.read()
        
        expected_items = [
            "playSoundIfEnabled",
            "isSoundEnabled",
            "setSoundEnabled",
            "Volume2",
            "VolumeX",
            "soundOn",
            "toggleSound",
            'data-testid="game-sound-toggle"',
            "@/styles/animations.css",
        ]
        
        for item in expected_items:
            assert item in content, f"SpeedRunGame.js should contain '{item}'"
        
        print("✓ SpeedRunGame.js correctly imports sound utilities and has sound toggle")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
