"""
Iteration 98 - Hardening P2P Arena: lamport math + MongoDB pot persistence + prize ticker.
Float-drift safe math, persisted pot across restarts, prize-pool ticker /status.
"""

import os
import time
import subprocess
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

WALLET_A = "A11ceWa11etAddrPubKeyBuLLpug98TestMockAAAAAAAA"
WALLET_B = "B0bWa11etAddrPubKeyBuLLpug98TestMockBBBBBBBB"
WALLET_C = "C0smWa11etAddrPubKeyBuLLpug98TestMockCCCCCCCC"


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


def _wait_health():
    for _ in range(40):
        try:
            r = requests.get(f"{API}/", timeout=3)
            if r.status_code == 200:
                time.sleep(1)
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Backend did not come back up")


def _restart_backend():
    subprocess.run(["sudo", "supervisorctl", "restart", "backend"],
                   capture_output=True, check=False)
    _wait_health()


def _clean_pot(mongo_db):
    """Fully clear pot: drop DB doc AND restart backend so in-memory cache reloads fresh."""
    mongo_db.active_pot.delete_many({})
    _restart_backend()


# ========== 1. GET /betting/pot includes total_lamports ==========
class TestPotSchema:
    @classmethod
    def setup_class(cls):
        client = MongoClient(MONGO_URL)
        _clean_pot(client[DB_NAME])

    def test_get_pot_has_total_lamports(self):
        r = requests.get(f"{API}/betting/pot", timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "total_lamports" in d, f"missing total_lamports: {d}"
        assert "total_amount_sol" in d
        assert d["total_lamports"] == 0
        assert d["total_amount_sol"] == 0


# ========== 2-7. Pot lamport math + boundaries + persistence ==========
class TestPotLamportMath:
    @classmethod
    def setup_class(cls):
        client = MongoClient(MONGO_URL)
        cls.mdb = client[DB_NAME]
        _clean_pot(cls.mdb)

    def test_01_min_boundary_success(self):
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.005, "wallet_address": WALLET_A,
            "display_name": "Alice", "tx_signature": "tx1"
        }, timeout=10)
        assert r.status_code == 200, r.text

        # verify via GET: entries[0].amount_lamports == 5_000_000 AND total_lamports == 5_000_000
        g = requests.get(f"{API}/betting/pot", timeout=10).json()
        assert g["total_lamports"] == 5_000_000
        assert g["total_amount_sol"] == 0.005

    def test_02_below_min_rejected_lamports(self):
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.0049, "wallet_address": WALLET_B,
            "display_name": "Bob", "tx_signature": "tx2"
        }, timeout=10)
        assert r.status_code == 400
        assert "Minimum bet is 0.005 SOL" in r.json().get("detail", "")

    def test_03_db_doc_persisted(self):
        doc = self.mdb.active_pot.find_one({"_id": "active"})
        assert doc is not None, "active_pot doc missing from MongoDB"
        assert doc["_id"] == "active"
        assert doc["status"] == "open"
        assert doc["total_lamports"] == 5_000_000
        assert len(doc["entries"]) == 1
        assert doc["entries"][0]["amount_lamports"] == 5_000_000
        assert doc["entries"][0]["wallet_address"] == WALLET_A


class TestFloatDriftSafety:
    @classmethod
    def setup_class(cls):
        client = MongoClient(MONGO_URL)
        cls.mdb = client[DB_NAME]
        _clean_pot(cls.mdb)

    def test_three_joins_of_0_1_sol_exact_300_000_000_lamports(self):
        for i in range(3):
            r = requests.post(f"{API}/betting/pot/join", json={
                "bet_amount_sol": 0.1, "wallet_address": WALLET_A,
                "display_name": "Alice", "tx_signature": f"drift_{i}"
            }, timeout=10)
            assert r.status_code == 200, r.text

        g = requests.get(f"{API}/betting/pot", timeout=10).json()
        assert g["total_lamports"] == 300_000_000, f"drift! got {g['total_lamports']}"
        # Float representation must be clean 0.3, not 0.30000000000000004
        assert g["total_amount_sol"] == 0.3


class TestStackingCap:
    @classmethod
    def setup_class(cls):
        client = MongoClient(MONGO_URL)
        cls.mdb = client[DB_NAME]
        _clean_pot(cls.mdb)

    def test_01_stacking_over_cap_rejected_with_exact_message(self):
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 7.0, "wallet_address": WALLET_A,
            "display_name": "Alice", "tx_signature": "stk1"
        }, timeout=10)
        assert r.status_code == 200, r.text

        # 7 + 4 -> 11 > 10 cap, expect message quoting 3.0 SOL remaining
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 4.0, "wallet_address": WALLET_A,
            "display_name": "Alice", "tx_signature": "stk2"
        }, timeout=10)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "Per-player cap is 10 SOL per round" in detail
        assert "add at most 3.0 SOL more" in detail, f"got: {detail}"

    def test_02_stacking_exact_cap_succeeds_then_zero_remaining(self):
        # Add 3 SOL to reach exactly 10
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 3.0, "wallet_address": WALLET_A,
            "display_name": "Alice", "tx_signature": "stk3"
        }, timeout=10)
        assert r.status_code == 200, r.text

        g = requests.get(f"{API}/betting/pot", timeout=10).json()
        assert g["total_lamports"] == 10_000_000_000

        # Now 0.005 more -> rejected with '0.0 SOL more'
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.005, "wallet_address": WALLET_A,
            "display_name": "Alice", "tx_signature": "stk4"
        }, timeout=10)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "add at most 0.0 SOL more" in detail, f"got: {detail}"


# ========== 8. Persistence across backend restart ==========
class TestPotPersistenceAcrossRestart:
    @classmethod
    def setup_class(cls):
        client = MongoClient(MONGO_URL)
        cls.mdb = client[DB_NAME]
        _clean_pot(cls.mdb)

    def test_entry_survives_backend_restart(self):
        r = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.1, "wallet_address": WALLET_A,
            "display_name": "Alice", "tx_signature": "persist1"
        }, timeout=10)
        assert r.status_code == 200, r.text

        pre = requests.get(f"{API}/betting/pot", timeout=10).json()
        pre_id = pre["id"]
        pre_total = pre["total_lamports"]

        # Restart backend mid-round
        subprocess.run(["sudo", "supervisorctl", "restart", "backend"],
                       capture_output=True, check=False)
        _wait_health()
        time.sleep(5)

        post = requests.get(f"{API}/betting/pot", timeout=10).json()
        assert post["id"] == pre_id, f"pot id changed: {pre_id} -> {post['id']}"
        assert post["total_lamports"] == pre_total == 100_000_000
        assert post["entry_count"] == 1


# ========== 9-10. Coinflip lamport math ==========
class TestCoinflipLamportMath:
    def test_rake_payout_lamport_math_0_123_sol(self):
        r = requests.post(f"{API}/betting/challenge/create", json={
            "bet_amount_sol": 0.123, "choice": "heads",
            "wallet_address": WALLET_A, "display_name": "TEST_Alice"
        }, timeout=10)
        assert r.status_code == 200, r.text
        cid = r.json()["challenge_id"]

        # Fetch full challenge for verification (lamport fields)
        c = requests.get(f"{API}/betting/challenge/{cid}", timeout=10).json()
        # pot_lamports = 246_000_000, rake = 246_000_000 * 250 // 10000 = 6_150_000
        assert c["bet_amount_lamports"] == 123_000_000
        assert c["rake_lamports"] == 6_150_000, f"rake_lamports wrong: {c['rake_lamports']}"
        assert c["payout_lamports"] == 239_850_000
        assert c["rake_lamports"] + c["payout_lamports"] == 246_000_000

    def test_coinflip_min_boundary(self):
        ok = requests.post(f"{API}/betting/challenge/create", json={
            "bet_amount_sol": 0.005, "choice": "heads",
            "wallet_address": WALLET_A, "display_name": "TEST_Alice"
        }, timeout=10)
        assert ok.status_code == 200, ok.text

        bad = requests.post(f"{API}/betting/challenge/create", json={
            "bet_amount_sol": 0.0049, "choice": "heads",
            "wallet_address": WALLET_A, "display_name": "TEST_Alice"
        }, timeout=10)
        assert bad.status_code == 400
        assert "Minimum bet is 0.005 SOL" in bad.json().get("detail", "")


# ========== 11. Prize-pool status endpoint ==========
class TestPrizePoolStatus:
    def test_status_has_required_fields(self):
        r = requests.get(f"{API}/prize-pool/status", timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "total_sol" in d
        assert "next_payout_at" in d
        assert "seconds_remaining" in d
        assert isinstance(d["seconds_remaining"], int)
        assert d.get("payout_interval_days") == 3
        assert "prize_breakdown" in d and len(d["prize_breakdown"]) == 10
        rank1 = next(b for b in d["prize_breakdown"] if b["rank"] == 1)
        assert rank1["percentage"] == 25


# ========== 12. End-to-end: auto-draw after countdown w/ lamport math ==========
class TestAutoDrawE2E:
    @classmethod
    def setup_class(cls):
        client = MongoClient(MONGO_URL)
        cls.mdb = client[DB_NAME]
        _clean_pot(cls.mdb)

    def test_auto_draw_and_prize_pool_growth(self):
        pre_pool = requests.get(f"{API}/prize-pool/status", timeout=10).json()
        pre_total = pre_pool.get("total_sol", 0)

        # 2 unique wallets
        r1 = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.01, "wallet_address": WALLET_A,
            "display_name": "Alice", "tx_signature": "e2e1"
        }, timeout=10)
        assert r1.status_code == 200, r1.text
        r2 = requests.post(f"{API}/betting/pot/join", json={
            "bet_amount_sol": 0.02, "wallet_address": WALLET_B,
            "display_name": "Bob", "tx_signature": "e2e2"
        }, timeout=10)
        assert r2.status_code == 200, r2.text
        assert r2.json()["countdown_started"] is True

        # Wait ~70s for auto-draw scheduler (runs every 5s, countdown=60s)
        deadline = time.time() + 90
        drawn = False
        while time.time() < deadline:
            time.sleep(5)
            g = requests.get(f"{API}/betting/pot", timeout=10).json()
            # After draw, reset_pot creates a fresh pot (new id, 0 entries, open)
            if g["entry_count"] == 0 and g["total_lamports"] == 0:
                drawn = True
                break

        assert drawn, "Pot did not auto-draw within 90s"

        # Check pot_results has new doc with lamport fields
        latest = self.mdb.pot_results.find_one(
            {"entries.wallet_address": {"$in": [WALLET_A, WALLET_B]}},
            sort=[("drawn_at", -1)]
        )
        assert latest is not None, "No pot_results doc created after auto-draw"
        assert "rake_lamports" in latest
        assert "payout_lamports" in latest
        # total = 0.03 SOL = 30_000_000 lamports; rake = 30_000_000 * 250 // 10000 = 750_000
        assert latest["total_lamports"] == 30_000_000
        assert latest["rake_lamports"] == 750_000
        assert latest["payout_lamports"] == 29_250_000

        # Prize pool grew by 25% of rake = 750_000 lamports * 0.25 = 187_500 lamports = 0.0001875 SOL
        time.sleep(2)
        post_pool = requests.get(f"{API}/prize-pool/status", timeout=10).json()
        delta = post_pool["total_sol"] - pre_total
        expected = 0.03 * 0.025 * 0.25  # 0.0001875
        assert delta == pytest.approx(expected, abs=1e-6), \
            f"prize-pool delta {delta} != expected {expected}"


# ========== Cleanup ==========
class TestCleanup:
    def test_zz_cleanup_pot(self):
        client = MongoClient(MONGO_URL)
        _clean_pot(client[DB_NAME])
        r = requests.get(f"{API}/betting/pot", timeout=10).json()
        assert r["entry_count"] == 0
        assert r["total_lamports"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
