"""
Backend API Tests for P2P Betting, Forum, Export Features
Tests: P2P Arena, Coin Flip Challenges, Pot System, Forum, CSV/JSON Export
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBettingConfig:
    """Test P2P betting configuration endpoint"""
    
    def test_betting_config_returns_correct_rake(self):
        """Verify betting config returns 2.5% rake"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        data = response.json()
        
        # Check rake percentage is 2.5%
        assert data["rake_percent"] == 2.5
        print(f"✓ Rake percent: {data['rake_percent']}%")
    
    def test_betting_config_returns_distribution_wallet(self):
        """Verify betting config returns correct distribution wallet"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        data = response.json()
        
        # Check distribution wallet
        expected_wallet = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"
        assert data["distribution_wallet"] == expected_wallet
        print(f"✓ Distribution wallet: {data['distribution_wallet']}")
    
    def test_betting_config_returns_sol_currency(self):
        """Verify betting config shows SOL as currency"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        data = response.json()
        
        assert data["currency"] == "SOL"
        print(f"✓ Currency: {data['currency']}")
    
    def test_betting_config_has_min_max_bet(self):
        """Verify betting config has min/max bet limits"""
        response = requests.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "min_bet_sol" in data
        assert "max_bet_sol" in data
        assert data["min_bet_sol"] < data["max_bet_sol"]
        print(f"✓ Bet limits: {data['min_bet_sol']} - {data['max_bet_sol']} SOL")


class TestP2PCoinFlipChallenges:
    """Test P2P Coin Flip Challenge System"""
    
    @pytest.fixture
    def test_wallet(self):
        """Generate a test wallet address"""
        return f"TEST_{uuid.uuid4().hex[:20]}"
    
    def test_create_challenge_success(self, test_wallet):
        """Test creating a P2P coin flip challenge"""
        response = requests.post(f"{BASE_URL}/api/betting/challenge/create", json={
            "bet_amount_sol": 0.1,
            "choice": "heads",
            "wallet_address": test_wallet,
            "display_name": "TEST_Guardian"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "challenge_id" in data
        assert data["bet_amount_sol"] == 0.1
        assert data["creator_choice"] == "heads"
        assert data["status"] == "open"
        print(f"✓ Challenge created: {data['challenge_id']}")
        return data["challenge_id"]
    
    def test_create_challenge_with_tails(self, test_wallet):
        """Test creating a challenge with tails choice"""
        response = requests.post(f"{BASE_URL}/api/betting/challenge/create", json={
            "bet_amount_sol": 0.05,
            "choice": "tails",
            "wallet_address": test_wallet,
            "display_name": "TEST_TailsPlayer"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["creator_choice"] == "tails"
        print(f"✓ Challenge with tails choice created")
    
    def test_create_challenge_invalid_choice(self, test_wallet):
        """Test creating a challenge with invalid choice fails"""
        response = requests.post(f"{BASE_URL}/api/betting/challenge/create", json={
            "bet_amount_sol": 0.1,
            "choice": "invalid_choice",
            "wallet_address": test_wallet,
            "display_name": "TEST_Player"
        })
        assert response.status_code == 400
        print("✓ Invalid choice rejected")
    
    def test_create_challenge_below_minimum(self, test_wallet):
        """Test creating a challenge below minimum bet fails"""
        response = requests.post(f"{BASE_URL}/api/betting/challenge/create", json={
            "bet_amount_sol": 0.001,  # Below 0.01 minimum
            "choice": "heads",
            "wallet_address": test_wallet,
            "display_name": "TEST_Player"
        })
        assert response.status_code == 400
        print("✓ Below minimum bet rejected")
    
    def test_create_challenge_above_maximum(self, test_wallet):
        """Test creating a challenge above maximum bet fails"""
        response = requests.post(f"{BASE_URL}/api/betting/challenge/create", json={
            "bet_amount_sol": 100,  # Above 10 maximum
            "choice": "heads",
            "wallet_address": test_wallet,
            "display_name": "TEST_Player"
        })
        assert response.status_code == 400
        print("✓ Above maximum bet rejected")
    
    def test_get_open_challenges(self):
        """Test getting list of open challenges"""
        response = requests.get(f"{BASE_URL}/api/betting/challenges?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        assert "challenges" in data
        assert isinstance(data["challenges"], list)
        print(f"✓ Open challenges endpoint working, found {len(data['challenges'])} challenges")


class TestP2PPotSystem:
    """Test P2P Pot System"""
    
    @pytest.fixture
    def test_wallet(self):
        """Generate a test wallet address"""
        return f"TEST_{uuid.uuid4().hex[:20]}"
    
    def test_get_pot_status(self):
        """Test getting current pot status"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_amount_sol" in data
        assert "entries" in data
        assert "status" in data
        assert "rake_percent" in data
        assert "distribution_wallet" in data
        
        # Verify correct rake and wallet
        assert data["rake_percent"] == 2.5
        assert data["distribution_wallet"] == "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"
        print(f"✓ Pot status: {data['total_amount_sol']} SOL, {data['entry_count']} entries")
    
    def test_join_pot_success(self, test_wallet):
        """Test joining the pot with SOL"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.1,
            "wallet_address": test_wallet,
            "display_name": "TEST_PotPlayer"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "probability" in data
        assert "total_pot_sol" in data
        print(f"✓ Joined pot: {data['probability']}% win chance")
    
    def test_join_pot_below_minimum(self, test_wallet):
        """Test joining pot below minimum fails"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.001,
            "wallet_address": test_wallet,
            "display_name": "TEST_Player"
        })
        assert response.status_code == 400
        print("✓ Below minimum pot join rejected")
    
    def test_join_pot_without_wallet(self):
        """Test joining pot without wallet fails"""
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.1,
            "wallet_address": "",
            "display_name": "TEST_Player"
        })
        assert response.status_code == 400
        print("✓ Pot join without wallet rejected")
    
    def test_pot_entries_show_probability(self, test_wallet):
        """Test pot entries show probability percentages"""
        # Join pot first
        requests.post(f"{BASE_URL}/api/betting/pot/join", json={
            "bet_amount_sol": 0.2,
            "wallet_address": test_wallet,
            "display_name": "TEST_ProbPlayer"
        })
        
        # Get pot status
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        data = response.json()
        
        if data["entries"]:
            # Check entries have probability
            for entry in data["entries"]:
                assert "probability" in entry
            print(f"✓ Entries show probability: {data['entries'][-1] if data['entries'] else 'No entries'}")


class TestBettingHistory:
    """Test betting history endpoint"""
    
    def test_get_betting_history(self):
        """Test getting betting history"""
        response = requests.get(f"{BASE_URL}/api/betting/history?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        assert "history" in data
        assert isinstance(data["history"], list)
        print(f"✓ Betting history: {len(data['history'])} records")
    
    def test_get_betting_history_by_wallet(self):
        """Test filtering history by wallet"""
        test_wallet = f"TEST_{uuid.uuid4().hex[:20]}"
        response = requests.get(f"{BASE_URL}/api/betting/history?wallet_address={test_wallet}")
        assert response.status_code == 200
        data = response.json()
        
        assert "history" in data
        print(f"✓ Wallet-specific history working")


class TestForumCategories:
    """Test Forum Categories"""
    
    def test_get_forum_categories(self):
        """Test getting forum categories returns 6 categories"""
        response = requests.get(f"{BASE_URL}/api/forum/categories")
        assert response.status_code == 200
        data = response.json()
        
        assert "categories" in data
        assert len(data["categories"]) == 6
        
        # Check expected categories exist
        category_ids = [c["id"] for c in data["categories"]]
        expected = ["general", "trading", "betting", "memes", "support", "announcements"]
        for cat in expected:
            assert cat in category_ids
        
        print(f"✓ Forum has {len(data['categories'])} categories: {category_ids}")


class TestForumPosts:
    """Test Forum Posts CRUD"""
    
    @pytest.fixture
    def test_wallet(self):
        """Generate a test wallet address"""
        return f"TEST_{uuid.uuid4().hex[:20]}"
    
    def test_get_forum_posts(self):
        """Test getting forum posts"""
        response = requests.get(f"{BASE_URL}/api/forum/posts?limit=50")
        assert response.status_code == 200
        data = response.json()
        
        assert "posts" in data
        assert isinstance(data["posts"], list)
        print(f"✓ Forum posts endpoint working, {len(data['posts'])} posts found")
    
    def test_get_forum_posts_by_category(self):
        """Test filtering posts by category"""
        response = requests.get(f"{BASE_URL}/api/forum/posts?category=general")
        assert response.status_code == 200
        data = response.json()
        
        assert "posts" in data
        print("✓ Category filter working")
    
    def test_create_forum_post(self, test_wallet):
        """Test creating a forum post"""
        response = requests.post(f"{BASE_URL}/api/forum/post", json={
            "title": "TEST_Post_Title",
            "content": "This is a TEST post content for testing the forum API.",
            "author_wallet": test_wallet,
            "author_name": "TEST_Author",
            "category": "general"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "post_id" in data
        assert data["message"] == "Post created!"
        print(f"✓ Forum post created: {data['post_id']}")
        return data["post_id"]
    
    def test_create_forum_post_without_wallet(self):
        """Test creating post without wallet fails"""
        response = requests.post(f"{BASE_URL}/api/forum/post", json={
            "title": "Test Title",
            "content": "Test content",
            "author_wallet": "",
            "author_name": "Test Author"
        })
        assert response.status_code == 400
        print("✓ Post without wallet rejected")
    
    def test_create_forum_post_without_title(self, test_wallet):
        """Test creating post without title fails"""
        response = requests.post(f"{BASE_URL}/api/forum/post", json={
            "title": "",
            "content": "Test content",
            "author_wallet": test_wallet,
            "author_name": "Test"
        })
        assert response.status_code == 400
        print("✓ Post without title rejected")
    
    def test_get_single_post(self, test_wallet):
        """Test getting a single post with replies"""
        # Create a post first
        create_response = requests.post(f"{BASE_URL}/api/forum/post", json={
            "title": "TEST_Single_Post",
            "content": "Content for single post test",
            "author_wallet": test_wallet,
            "author_name": "TEST_SingleAuthor",
            "category": "trading"
        })
        post_id = create_response.json()["post_id"]
        
        # Get the post
        response = requests.get(f"{BASE_URL}/api/forum/post/{post_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == post_id
        assert "replies" in data
        assert "reply_count" in data
        print(f"✓ Single post retrieved with {data['reply_count']} replies")


class TestForumReplies:
    """Test Forum Replies"""
    
    @pytest.fixture
    def test_wallet(self):
        """Generate a test wallet address"""
        return f"TEST_{uuid.uuid4().hex[:20]}"
    
    @pytest.fixture
    def test_post_id(self, test_wallet):
        """Create a test post and return its ID"""
        response = requests.post(f"{BASE_URL}/api/forum/post", json={
            "title": "TEST_Reply_Post",
            "content": "Post for reply testing",
            "author_wallet": test_wallet,
            "author_name": "TEST_ReplyAuthor",
            "category": "support"
        })
        return response.json()["post_id"]
    
    def test_create_reply(self, test_wallet, test_post_id):
        """Test creating a reply to a post"""
        response = requests.post(f"{BASE_URL}/api/forum/reply", json={
            "post_id": test_post_id,
            "content": "This is a TEST reply to the post",
            "author_wallet": test_wallet,
            "author_name": "TEST_Replier"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "reply_id" in data
        assert data["message"] == "Reply posted!"
        print(f"✓ Reply created: {data['reply_id']}")
    
    def test_create_reply_without_content(self, test_wallet, test_post_id):
        """Test creating empty reply fails"""
        response = requests.post(f"{BASE_URL}/api/forum/reply", json={
            "post_id": test_post_id,
            "content": "",
            "author_wallet": test_wallet,
            "author_name": "TEST_Replier"
        })
        assert response.status_code == 400
        print("✓ Empty reply rejected")
    
    def test_create_reply_to_nonexistent_post(self, test_wallet):
        """Test replying to non-existent post fails"""
        response = requests.post(f"{BASE_URL}/api/forum/reply", json={
            "post_id": "nonexistent-post-id",
            "content": "Test reply",
            "author_wallet": test_wallet,
            "author_name": "TEST_Replier"
        })
        assert response.status_code == 404
        print("✓ Reply to non-existent post rejected")


class TestTradingJournalExport:
    """Test Trading Journal Export endpoints"""
    
    def test_export_csv(self):
        """Test CSV export endpoint"""
        response = requests.get(f"{BASE_URL}/api/journal/export/csv")
        
        # Should return 200 if trades exist, 404 if no trades
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")
            assert "Content-Disposition" in response.headers
            print(f"✓ CSV export working, size: {len(response.content)} bytes")
        else:
            print("✓ CSV export returns 404 when no trades (expected)")
    
    def test_export_json(self):
        """Test JSON export endpoint"""
        response = requests.get(f"{BASE_URL}/api/journal/export/json")
        
        # Should return 200 with JSON
        assert response.status_code == 200
        
        data = response.json()
        assert "exported_at" in data
        assert "summary" in data
        assert "trades" in data
        print(f"✓ JSON export working, {len(data['trades'])} trades")


class TestShareScoreOnX:
    """Test Share Score functionality (game game over screen)"""
    
    def test_leaderboard_submit_for_share(self):
        """Test score submission that would be shared on X"""
        test_name = f"TEST_SharePlayer_{uuid.uuid4().hex[:6]}"
        response = requests.post(f"{BASE_URL}/api/leaderboard/submit", json={
            "player_name": test_name,
            "score": 150,
            "mooncakes": 5
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "rank" in data
        print(f"✓ Score submitted for sharing: Rank #{data['rank']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
