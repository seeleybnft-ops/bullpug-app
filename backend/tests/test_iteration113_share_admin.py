"""
Iteration 113 tests.

Covers:
  1. POST /api/archive/share returns total=61 & grand_total=62
  2. POST /api/archive/share returns DIFFERENT image_base64 on repeat call (no cache)
  3. The share PNG does NOT embed any lore text (no entry names / lore substrings)
  4. GET /api/archive/entries returns total=61 (regular) with 62 entries
  5. GET /api/archive/rank returns tier_progress.special {unlocked:0, total:1} and total=61
  6. GET /api/archive/record excludes wallets matching TEST_WALLET_REGEX
  7. CSRF header enforcement on POST /api/archive/share
"""
import base64
import os
import time
import uuid
import asyncio
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cosmic-runner-hub.preview.emergentagent.com").rstrip("/")
CSRF = {"X-Bullpug-CSRF": "1", "Content-Type": "application/json"}


def _fresh_wallet(tag="RegressionShare"):
    return f"{tag}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"


# ── Fix 1: totals on /share ────────────────────────────────────────
class TestShareTotals:
    def test_share_totals(self):
        w = _fresh_wallet()
        r = requests.post(f"{BASE_URL}/api/archive/share",
                          json={"wallet": w}, headers=CSRF, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total"] == 61, f"expected 61 regular tiers, got {d.get('total')}"
        assert d["grand_total"] == 62, f"expected grand_total 62, got {d.get('grand_total')}"
        assert d["mime"] == "image/png"
        assert isinstance(d["image_base64"], str) and len(d["image_base64"]) > 1000

    def test_share_csrf_required(self):
        w = _fresh_wallet()
        r = requests.post(f"{BASE_URL}/api/archive/share",
                          json={"wallet": w},
                          headers={"Content-Type": "application/json"},
                          timeout=15)
        assert r.status_code == 403, f"expected 403 without CSRF, got {r.status_code}"


# ── Fix 2: no cache — two calls return different PNGs ─────────────
class TestShareFreshGeneration:
    def test_two_calls_produce_different_images(self):
        w = _fresh_wallet()
        r1 = requests.post(f"{BASE_URL}/api/archive/share",
                           json={"wallet": w}, headers=CSRF, timeout=90)
        assert r1.status_code == 200, r1.text
        b1 = r1.json()["image_base64"]

        # brief pause to avoid rate-limit-driven identical outputs
        time.sleep(2)
        r2 = requests.post(f"{BASE_URL}/api/archive/share",
                           json={"wallet": w}, headers=CSRF, timeout=90)
        assert r2.status_code == 200, r2.text
        b2 = r2.json()["image_base64"]

        assert b1 != b2, "Fix 2 broken: two share calls returned identical image_base64 — cache is still active"
        # Both should be PNGs of reasonable size
        assert len(b1) > 5000 and len(b2) > 5000


# ── Fix 1b: PNG contains no lore text ─────────────────────────────
class TestShareNoLoreText:
    def test_png_bytes_have_no_lore_substrings(self):
        w = _fresh_wallet()
        r = requests.post(f"{BASE_URL}/api/archive/share",
                          json={"wallet": w}, headers=CSRF, timeout=90)
        assert r.status_code == 200
        png_bytes = base64.b64decode(r.json()["image_base64"])
        # PNG magic
        assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        # These substrings would only appear if lore/entry text is baked into the image encoding metadata
        for needle in [b"The Ledger", b"Grizzlor", b"Bullpug's origin",
                       b"origin", b"Ledger"]:
            assert needle not in png_bytes, f"share PNG contains lore substring {needle!r}"


# ── /entries totals ───────────────────────────────────────────────
class TestEntriesTotals:
    def test_entries_total_61_and_62_items(self):
        r = requests.get(f"{BASE_URL}/api/archive/entries",
                         params={"wallet": _fresh_wallet()}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("total") == 61, f"expected total=61, got {d.get('total')}"
        entries = d.get("entries") or d.get("items") or []
        assert len(entries) == 62, f"expected 62 entries in list, got {len(entries)}"
        slugs = [e.get("slug") for e in entries]
        assert "companions-secret" in slugs, "special companions-secret entry missing"


# ── /rank tier_progress.special ───────────────────────────────────
class TestRankSpecialProgress:
    def test_rank_has_special_progress(self):
        r = requests.get(f"{BASE_URL}/api/archive/rank",
                         params={"wallet": _fresh_wallet()}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("total") == 61
        tp = d.get("tier_progress") or {}
        special = tp.get("special")
        assert special == {"unlocked": 0, "total": 1}, \
            f"expected special {{unlocked:0,total:1}}, got {special}"


# ── /record filters TEST_WALLET_REGEX ─────────────────────────────
class TestRecordFiltersTestWallets:
    def test_test_wallet_not_in_leaderboard(self):
        """
        Insert a wallet matching TEST_WALLET_REGEX directly into archive_ranks
        and confirm /api/archive/record does not return it.
        """
        import sys
        sys.path.insert(0, "/app/backend")
        from utils.database import get_db  # noqa
        from utils.test_wallet_filter import is_test_wallet

        test_wallet = f"TESTWALLET_LEADERBOARD_{uuid.uuid4().hex[:8]}"
        assert is_test_wallet(test_wallet), "regex sanity check failed"

        async def _run():
            db = get_db()
            await db.archive_ranks.insert_one({
                "wallet_address": test_wallet,
                "rank": "keepers_circle",
                "rank_title": "Keeper's Circle",
                "unlocked_count": 99,
                "rank_reached_at": 1_700_000_000,
                "updated_at": 1_700_000_000,
            })
            try:
                # Fetch several pages to be safe
                for page in range(1, 8):
                    r = requests.get(f"{BASE_URL}/api/archive/record",
                                     params={"page": page, "limit": 50}, timeout=15)
                    assert r.status_code == 200, r.text
                    entries = r.json().get("entries", [])
                    for e in entries:
                        assert e.get("wallet_address") != test_wallet and \
                               e.get("wallet") != test_wallet, \
                               f"TEST wallet {test_wallet} leaked into /record"
                    if not r.json().get("has_more"):
                        break
            finally:
                await db.archive_ranks.delete_one({"wallet_address": test_wallet})

        asyncio.get_event_loop().run_until_complete(_run())
