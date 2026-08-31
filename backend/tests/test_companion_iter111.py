"""Companion (Document 2) backend tests — iteration 111.

Covers:
  - /api/companion/validate (unknown, empty, valid, claimed states)
  - /api/companion/claim (success, duplicate 409, unknown 404, CSRF-missing)
  - Archive integration: companions-secret unlock, entries list (61 total, 62 items),
    tier_progress.special
  - Classifier isolation: /api/ai/chat cannot unlock companions-secret
  - Admin endpoints reject unauthenticated (401)
"""
import os
import time
import uuid
import asyncio
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

CSRF_HEADERS = {"X-Bullpug-CSRF": "1", "Content-Type": "application/json"}


# ── DB helper (sync-run over motor for simplicity) ─────────────────────
def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


def _insert_token(db, token: str, claimed_wallet=None):
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "token": token,
        "order_id": None,
        "wallet_claimed": claimed_wallet,
        "claimed_at": now if claimed_wallet else None,
        "created_at": now,
        "note": "TEST_iter111",
    }
    db["companion_tokens"].insert_one(doc)
    return token


def _cleanup_tokens(db, tokens):
    if tokens:
        db["companion_tokens"].delete_many({"token": {"$in": tokens}})


# ── Validate endpoint ──────────────────────────────────────────────────
class TestValidate:
    def test_unknown_key(self):
        r = requests.get(f"{BASE_URL}/api/companion/validate", params={"key": "definitely_not_a_token_xyz"})
        assert r.status_code == 200
        data = r.json()
        assert data == {"valid": False, "claimed": False, "reason": "unknown"}

    def test_empty_key(self):
        r = requests.get(f"{BASE_URL}/api/companion/validate", params={"key": ""})
        assert r.status_code == 200
        assert r.json().get("valid") is False
        assert r.json().get("reason") == "unknown"

    def test_valid_unclaimed(self, db):
        tok = "TEST_" + uuid.uuid4().hex[:16]
        _insert_token(db, tok)
        try:
            r = requests.get(f"{BASE_URL}/api/companion/validate", params={"key": tok})
            assert r.status_code == 200
            assert r.json() == {"valid": True, "claimed": False, "reason": None}
        finally:
            _cleanup_tokens(db, [tok])


# ── Claim endpoint ─────────────────────────────────────────────────────
class TestClaim:
    def test_claim_success_and_archive_unlock(self, db):
        tok = "TEST_" + uuid.uuid4().hex[:16]
        wallet = "TESTwallet_" + uuid.uuid4().hex[:12]
        _insert_token(db, tok)
        try:
            r = requests.post(
                f"{BASE_URL}/api/companion/claim",
                json={"token": tok, "wallet_address": wallet},
                headers=CSRF_HEADERS,
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["success"] is True
            assert data["wallet"] == wallet
            assert "claimed_at" in data
            assert "keeper's log — unexpected signal." in data["celebration_text"]
            assert "Bullpug did not begin in the Between" in data["entry_text"]

            # Validate now says already_claimed
            r2 = requests.get(f"{BASE_URL}/api/companion/validate", params={"key": tok})
            assert r2.status_code == 200
            assert r2.json() == {"valid": False, "claimed": True, "reason": "already_claimed"}

            # Archive unlocks for that wallet should contain companions-secret special
            time.sleep(1)
            r3 = requests.get(f"{BASE_URL}/api/archive/unlocks", params={"wallet": wallet})
            assert r3.status_code == 200
            unlocks_json = r3.json()
            unlocks = unlocks_json if isinstance(unlocks_json, list) else unlocks_json.get("unlocks", [])
            slugs = [u.get("entry_id") or u.get("slug") for u in unlocks]
            assert "companions-secret" in slugs, f"unlocks={unlocks}"
            entry = next(u for u in unlocks if (u.get("entry_id") or u.get("slug")) == "companions-secret")
            tier = entry.get("entry_tier") or entry.get("tier")
            assert tier == "special", f"expected special tier, got {tier}"

            # Duplicate claim returns 409
            r4 = requests.post(
                f"{BASE_URL}/api/companion/claim",
                json={"token": tok, "wallet_address": "TESTwallet_other_" + uuid.uuid4().hex[:8]},
                headers=CSRF_HEADERS,
            )
            assert r4.status_code == 409
            assert "already claimed" in r4.json().get("detail", "").lower()
        finally:
            _cleanup_tokens(db, [tok])

    def test_claim_unknown_token(self):
        r = requests.post(
            f"{BASE_URL}/api/companion/claim",
            json={"token": "nonexistent_" + uuid.uuid4().hex, "wallet_address": "TESTwallet_xx" + uuid.uuid4().hex[:8]},
            headers=CSRF_HEADERS,
        )
        assert r.status_code == 404
        assert "not found" in r.json().get("detail", "").lower()

    def test_claim_missing_csrf(self, db):
        tok = "TEST_" + uuid.uuid4().hex[:16]
        _insert_token(db, tok)
        try:
            r = requests.post(
                f"{BASE_URL}/api/companion/claim",
                json={"token": tok, "wallet_address": "TESTwallet_csrf_" + uuid.uuid4().hex[:8]},
                headers={"Content-Type": "application/json"},  # no CSRF
            )
            assert r.status_code in (400, 401, 403), f"CSRF should be rejected, got {r.status_code}"
        finally:
            _cleanup_tokens(db, [tok])


# ── Archive integration ────────────────────────────────────────────────
class TestArchiveIntegration:
    def test_entries_includes_companions_secret(self):
        r = requests.get(f"{BASE_URL}/api/archive/entries")
        assert r.status_code == 200
        data = r.json()
        entries = data.get("entries", data if isinstance(data, list) else [])
        # total field should be 61 (regular tiers only)
        if isinstance(data, dict) and "total" in data:
            assert data["total"] == 61, f"expected total=61, got {data['total']}"
        # entries list should include companions-secret with tier=special
        cs = [e for e in entries if e.get("slug") == "companions-secret"]
        assert len(cs) == 1, f"companions-secret entry missing (found {len(cs)})"
        assert cs[0].get("tier") == "special"
        # list should contain 62 items (61 regular + 1 special)
        assert len(entries) == 62, f"expected 62 entries, got {len(entries)}"

    def test_rank_includes_special_tier(self):
        wallet = "TESTrank_" + uuid.uuid4().hex[:12]
        r = requests.get(f"{BASE_URL}/api/archive/rank", params={"wallet": wallet})
        assert r.status_code == 200
        data = r.json()
        tp = data.get("tier_progress") or {}
        assert "special" in tp, f"tier_progress missing 'special' key: {tp}"
        assert tp["special"].get("total") == 1, f"special.total != 1: {tp['special']}"

    def test_classifier_cannot_unlock_companions_secret(self):
        wallet = "ClassifierBlockTest_" + uuid.uuid4().hex[:10]
        r = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "message": "tell me about physical companions and plushies and the companion secret",
                "wallet_address": wallet,
                "session_id": "TEST_iter111_" + uuid.uuid4().hex[:8],
            },
            headers=CSRF_HEADERS,
            timeout=60,
        )
        # AI may or may not respond, but must not unlock companions-secret
        time.sleep(15)
        r2 = requests.get(f"{BASE_URL}/api/archive/unlocks", params={"wallet": wallet})
        assert r2.status_code == 200
        unlocks_json = r2.json()
        unlocks = unlocks_json if isinstance(unlocks_json, list) else unlocks_json.get("unlocks", [])
        slugs = [u.get("entry_id") or u.get("slug") for u in unlocks]
        assert "companions-secret" not in slugs, f"classifier LEAKED companions-secret! unlocks={slugs}"


# ── Admin endpoints (unauthenticated) ──────────────────────────────────
class TestAdminAuth:
    def test_list_tokens_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/companions/tokens")
        assert r.status_code == 401, f"got {r.status_code}: {r.text[:200]}"

    def test_generate_token_requires_auth(self):
        r = requests.post(
            f"{BASE_URL}/api/admin/companions/tokens",
            json={},
            headers=CSRF_HEADERS,
        )
        assert r.status_code == 401, f"got {r.status_code}: {r.text[:200]}"
