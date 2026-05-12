"""Iteration 99 - Leaderboard endpoint tests for Cosmic Runner 3D score submission."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "https://cosmic-runner-hub.preview.emergentagent.com"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


class TestLeaderboardSubmit:
    """Tests POST /api/leaderboard/submit and GET /api/leaderboard (used by Phase1Runner3D on game over)."""

    def test_get_leaderboard_initial(self, api):
        r = api.get(f"{BASE_URL}/api/leaderboard?limit=10", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        assert "cycle_start" in data
        assert "next_payout" in data
        assert "days_until_reset" in data

    def test_submit_new_score_returns_rank(self, api):
        payload = {"player_name": "TestRunner3D", "score": 1234, "moonCheese": 42}
        r = api.post(f"{BASE_URL}/api/leaderboard/submit", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "rank" in body and isinstance(body["rank"], int) and body["rank"] >= 1
        assert body["score"] == 1234
        assert body["moonCheese"] == 42

    def test_submitted_appears_in_get_leaderboard(self, api):
        r = api.get(f"{BASE_URL}/api/leaderboard?limit=50", timeout=15)
        assert r.status_code == 200
        entries = r.json()["leaderboard"]
        names = [e.get("player_name") for e in entries]
        assert "TestRunner3D" in names, f"TestRunner3D not in {names}"
        entry = next(e for e in entries if e.get("player_name") == "TestRunner3D")
        # Score is at least the one we submitted (could be higher if prior run existed)
        assert entry["score"] >= 1234

    def test_higher_score_updates_existing_entry(self, api):
        # Submit a higher score - should update, not duplicate
        payload = {"player_name": "TestRunner3D", "score": 9999, "moonCheese": 100}
        r = api.post(f"{BASE_URL}/api/leaderboard/submit", json=payload, timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == 9999

        # GET back and confirm only one entry with updated score
        r2 = api.get(f"{BASE_URL}/api/leaderboard?limit=50", timeout=15)
        entries = r2.json()["leaderboard"]
        matches = [e for e in entries if e.get("player_name") == "TestRunner3D"]
        assert len(matches) == 1, f"Expected 1 entry, got {len(matches)}"
        assert matches[0]["score"] == 9999

    def test_lower_score_does_not_overwrite(self, api):
        payload = {"player_name": "TestRunner3D", "score": 1, "moonCheese": 0}
        r = api.post(f"{BASE_URL}/api/leaderboard/submit", json=payload, timeout=15)
        assert r.status_code == 200
        r2 = api.get(f"{BASE_URL}/api/leaderboard?limit=50", timeout=15)
        entries = r2.json()["leaderboard"]
        entry = next(e for e in entries if e.get("player_name") == "TestRunner3D")
        # Score should still be 9999 (not overwritten by 1)
        assert entry["score"] == 9999

    def test_submit_default_player_name(self, api):
        # Simulate the default fallback used in Phase1Runner3D when localStorage is empty
        payload = {"player_name": "Cosmic Pug", "score": 500, "moonCheese": 5}
        r = api.post(f"{BASE_URL}/api/leaderboard/submit", json=payload, timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == 500
        assert body["moonCheese"] == 5
        assert body["rank"] >= 1

    def test_submit_missing_field_returns_422(self, api):
        # Pydantic should reject missing required fields
        r = api.post(f"{BASE_URL}/api/leaderboard/submit", json={"player_name": "X"}, timeout=15)
        assert r.status_code in (400, 422), r.text


class TestRegressionSmoke:
    """Smoke check that other routers still respond."""

    def test_arena_active_pot_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/pot/active", timeout=15)
        # Either returns a pot or 200 with empty - just verify no 5xx
        assert r.status_code < 500, r.text

    def test_prize_pool_status(self, api):
        r = api.get(f"{BASE_URL}/api/prize-pool/status", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "total_sol" in data or "total" in data or "prize_breakdown" in data
