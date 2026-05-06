"""
Iteration 97 - P2P Arena restoration tests.

Covers:
- /api/betting/config (min=0.005, max=10, rake=2.5)
- /api/betting/pot GET (empty pot)
- /api/betting/pot/join: min boundary, max single-entry, cumulative cap, stacking, unique-player countdown, aggregation
- /api/betting/challenge/*: min/max boundary, create, list, accept (full e2e incl. rake & prize pool)
- /api/betting/challenge/cancel (creator only)

NOTE: Pot state is in-memory on the backend process. Tests in the PotSuite run in sequence
against a freshly restarted backend to guarantee a clean pot.
"""

import os
import time
import subprocess
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

WALLET_A = "A11ceWa11etAddrPubKeyBuLLpugTestMockAAAAAAAA"
WALLET_B = "B0bWa11etAddrPubKeyBuLLpugTestMockBBBBBBBBBB"
WALLET_C = "C0smWa11etAddrPubKeyBuLLpugTestMockCCCCCCCCC"


def _restart_backend_and_wait():
    """Restart backend so the in-memory pot state is clean; wait for health."""
    subprocess.run(["sudo", "supervisorctl", "restart", "backend"],
                   capture_output=True, check=False)
    for _ in range(30):
        try:
            r = requests.get(f"{API}/", timeout=3)
            if r.status_code == 200:
                time.sleep(1)  # settle
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Backend did not come back up")


# ========== Betting config ==========
class TestBettingConfig:
    def test_config_values(self):
        r = requests.get(f"{API}/betting/config", timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["min_bet_sol"] == 0.005
        assert d["max_bet_sol"] == 10.0
        assert d["rake_percent"] == 2.5
        assert d["currency"] == "SOL"
        assert isinstance(d.get("distribution_wallet"), str)


# ========== Pot suite: runs against a fresh backend ==========
class TestPotSuite:
    @classmethod
    def setup_class(cls):
        _restart_backend_and_wait()

    def test_01_empty_pot(self):
        r = requests.get(f"{API}/betting/pot", timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["entry_count"] == 0
        assert d["entries"] == []
        assert d["status"] == "open"
        assert d["countdown_started"] is False
        assert d["total_amount_sol"] == 0

    def test_02_join_below_min_rejected(self):
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.003,
            "wallet_address": WALLET_A,
            "display_name": "Alice",
            "tx_signature": "dummy_tx_1"
        }, timeout=10)
        assert r.status_code == 400
        assert "Minimum bet is 0.005 SOL" in r.json().get("detail", "")

    def test_03_join_above_max_rejected(self):
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 11.0,
            "wallet_address": WALLET_A,
            "display_name": "Alice",
            "tx_signature": "dummy_tx_2"
        }, timeout=10)
        assert r.status_code == 400
        assert "Maximum single entry is 10 SOL" in r.json().get("detail", "")

    def test_04_join_min_boundary_success(self):
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.005,
            "wallet_address": WALLET_A,
            "display_name": "Alice",
            "tx_signature": "dummy_tx_3"
        }, timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["entry_count"] == 1
        assert d["total_pot_sol"] == pytest.approx(0.005)
        # Countdown must NOT start with a single unique player
        assert d["countdown_started"] is False

    def test_05_countdown_not_started_on_stacking(self):
        # Same wallet joins again - still 1 unique player, no countdown
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 6.0,
            "wallet_address": WALLET_A,
            "display_name": "Alice",
            "tx_signature": "dummy_tx_4"
        }, timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["countdown_started"] is False
        assert d["entry_count"] == 2

    def test_06_cumulative_cap_rejected(self):
        # Alice has 0.005 + 6 = 6.005. Adding 5 -> 11.005 > 10 -> reject.
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 5.0,
            "wallet_address": WALLET_A,
            "display_name": "Alice",
            "tx_signature": "dummy_tx_5"
        }, timeout=10)
        assert r.status_code == 400
        assert "Per-player cap is 10 SOL" in r.json().get("detail", "")

    def test_07_second_unique_player_starts_countdown(self):
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.005,
            "wallet_address": WALLET_B,
            "display_name": "Bob",
            "tx_signature": "dummy_tx_6"
        }, timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["countdown_started"] is True
        assert d["countdown_just_started"] is True
        assert d["draw_at"] is not None

    def test_08_entries_display_aggregated(self):
        r = requests.get(f"{API}/betting/pot", timeout=10)
        assert r.status_code == 200
        d = r.json()
        # Raw entry count = 3 (Alice x2, Bob x1), display = 2 cards
        assert d["entry_count"] == 3
        assert len(d["entries"]) == 2
        alice = next(e for e in d["entries"] if e["display_name"] == "Alice")
        bob = next(e for e in d["entries"] if e["display_name"] == "Bob")
        assert alice["entry_count"] == 2
        assert alice["amount_sol"] == pytest.approx(6.005, rel=1e-3)
        assert bob["entry_count"] == 1
        assert bob["amount_sol"] == pytest.approx(0.005)
        # Probability is a number
        assert isinstance(alice["probability"], (int, float))
        assert d["countdown_started"] is True
        assert isinstance(d["remaining_seconds"], int)


# ========== Coinflip (challenge) tests ==========
class TestCoinflip:
    created_ids: list = []

    def test_01_create_min_boundary(self):
        r = requests.post(f"{API}/betting/challenge/create", json={
            "bet_amount_sol": 0.005,
            "choice": "heads",
            "wallet_address": WALLET_A,
            "display_name": "TEST_Alice"
        }, timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "open"
        assert d["bet_amount_sol"] == 0.005
        assert d["creator_choice"] == "heads"
        assert "server_seed_hash" in d
        TestCoinflip.created_ids.append(d["challenge_id"])

    def test_02_create_below_min_rejected(self):
        r = requests.post(f"{API}/betting/challenge/create", json={
            "bet_amount_sol": 0.004,
            "choice": "heads",
            "wallet_address": WALLET_A,
            "display_name": "TEST_Alice"
        }, timeout=10)
        assert r.status_code == 400
        assert "Minimum bet is 0.005 SOL" in r.json().get("detail", "")

    def test_03_create_max_boundary(self):
        r = requests.post(f"{API}/betting/challenge/create", json={
            "bet_amount_sol": 10.0,
            "choice": "tails",
            "wallet_address": WALLET_A,
            "display_name": "TEST_Alice"
        }, timeout=10)
        assert r.status_code == 200, r.text
        TestCoinflip.created_ids.append(r.json()["challenge_id"])

    def test_04_create_above_max_rejected(self):
        r = requests.post(f"{API}/betting/challenge/create", json={
            "bet_amount_sol": 10.01,
            "choice": "tails",
            "wallet_address": WALLET_A,
            "display_name": "TEST_Alice"
        }, timeout=10)
        assert r.status_code == 400
        assert "Maximum bet is 10 SOL" in r.json().get("detail", "")

    def test_05_list_challenges_includes_created(self):
        r = requests.get(f"{API}/betting/challenges?limit=100", timeout=10)
        assert r.status_code == 200, r.text
        ids = {c["id"] for c in r.json()["challenges"]}
        assert TestCoinflip.created_ids[0] in ids

    def test_06_cancel_challenge_creator_only(self):
        # Cancel the second (10 SOL) challenge
        cid = TestCoinflip.created_ids[1]
        # Wrong wallet -> 403
        r = requests.post(f"{API}/betting/challenge/cancel/{cid}",
                          params={"wallet_address": WALLET_B}, timeout=10)
        assert r.status_code == 403
        # Creator cancels OK
        r = requests.post(f"{API}/betting/challenge/cancel/{cid}",
                          params={"wallet_address": WALLET_A}, timeout=10)
        assert r.status_code == 200
        assert r.json()["challenge_id"] == cid

    def test_07_full_coinflip_e2e(self):
        # Record prize pool before
        pre = requests.get(f"{API}/prize-pool/status", timeout=10).json()
        pre_total = pre.get("total_sol", 0)

        # Create a fresh challenge
        bet = 0.01
        r = requests.post(f"{API}/betting/challenge/create", json={
            "bet_amount_sol": bet,
            "choice": "heads",
            "wallet_address": WALLET_A,
            "display_name": "TEST_Alice"
        }, timeout=10)
        assert r.status_code == 200, r.text
        cid = r.json()["challenge_id"]

        # Opponent accepts
        r = requests.post(f"{API}/betting/challenge/accept", json={
            "challenge_id": cid,
            "wallet_address": WALLET_C,
            "display_name": "TEST_Carol",
            "client_seed": "test-client-seed-123"
        }, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()

        assert d["outcome"] in ("heads", "tails")
        assert d["winner_wallet"] in (WALLET_A, WALLET_C)

        expected_rake = round(bet * 2 * 0.025, 6)
        expected_payout = round(bet * 2 * 0.975, 6)
        assert d["rake_sol"] == pytest.approx(expected_rake, abs=1e-6)
        assert d["payout_sol"] == pytest.approx(expected_payout, abs=1e-6)
        assert "server_seed" in d and "result_hash" in d

        # Prize pool should have grown by 25% of rake
        time.sleep(1)
        post = requests.get(f"{API}/prize-pool/status", timeout=10).json()
        expected_contribution = expected_rake * 0.25
        delta = post["total_sol"] - pre_total
        assert delta == pytest.approx(expected_contribution, abs=1e-6), \
            f"Expected prize-pool delta ~{expected_contribution}, got {delta}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
