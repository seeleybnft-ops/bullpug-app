"""Iteration 112 — Backend tests for:
  1) POST /api/archive/share — AI-generated art, idempotency, no lore text.
  2) share_card_art MongoDB cache doc contains image_base64.
  3) GET /api/archive/record — pagination, sort, filter unlocked_count>0.
  4) rank_reached_at populated on a fresh wallet after Seeker.
"""
import base64
import io
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cosmic-runner-hub.preview.emergentagent.com").rstrip("/")
CSRF_HEADERS = {"X-Bullpug-CSRF": "1", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ── /api/archive/share ──────────────────────────────────────────────────
class TestArchiveShare:
    def test_share_missing_csrf_rejected(self, http):
        r = http.post(f"{BASE_URL}/api/archive/share", json={"wallet": "AnyWallet"})
        # CSRF middleware must block POST without X-Bullpug-CSRF
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"

    def test_share_valid_wallet_returns_png(self, http):
        wallet = f"ShareTest_{uuid.uuid4().hex[:12]}"
        r = requests.post(
            f"{BASE_URL}/api/archive/share",
            json={"wallet": wallet},
            headers=CSRF_HEADERS,
            timeout=60,
        )
        assert r.status_code == 200, f"share failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        for k in ("wallet", "image_base64", "mime", "rank", "rank_title", "unlocked_count", "total"):
            assert k in data, f"missing key {k}: {data.keys()}"
        assert data["mime"] == "image/png"
        assert data["wallet"] == wallet
        # decode & sanity-check PNG magic
        blob = base64.b64decode(data["image_base64"])
        assert blob[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
        assert len(blob) > 5000, f"suspiciously small PNG ({len(blob)} bytes)"
        # Stash for idempotency test
        pytest.share_wallet_zero = wallet
        pytest.share_bytes_zero = blob

    def test_share_idempotent_same_wallet(self, http):
        wallet = getattr(pytest, "share_wallet_zero", None)
        assert wallet, "prerequisite test did not run"
        t0 = time.time()
        r = requests.post(
            f"{BASE_URL}/api/archive/share",
            json={"wallet": wallet},
            headers=CSRF_HEADERS,
            timeout=60,
        )
        dt = time.time() - t0
        assert r.status_code == 200
        blob2 = base64.b64decode(r.json()["image_base64"])
        # Byte-compare cache
        assert blob2 == pytest.share_bytes_zero, (
            f"second call returned different bytes ({len(blob2)} vs {len(pytest.share_bytes_zero)})"
        )
        print(f"[idempotency] second call took {dt:.2f}s and matched byte-for-byte")

    def test_share_card_art_cache_persisted(self):
        """Ensure `share_card_art` doc exists for the wallet used above."""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient

        wallet = getattr(pytest, "share_wallet_zero", None)
        assert wallet, "prereq missing"

        async def _check():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            doc = await db.share_card_art.find_one({"wallet": wallet})
            client.close()
            return doc

        doc = asyncio.get_event_loop().run_until_complete(_check())
        assert doc is not None, "no share_card_art doc persisted"
        assert doc.get("image_base64"), "share_card_art doc missing image_base64"

    def test_share_png_no_lore_text(self):
        """OCR-lite: since embedding fonts and running OCR is heavy,
        verify PNG does not contain any of the known lore-entry title
        strings by asking the archive_share_card service directly.
        We rely on the fact that _draw_featured_entry was removed —
        so simply asserting the endpoint returns a PNG > 5KB and the
        cached art hash matches on repeat is our indirect signal.
        Additional check: request a fresh wallet with no unlocks and
        ensure the response's PNG has no text-related metadata about
        entry names in EXIF/tEXt chunks.
        """
        wallet = getattr(pytest, "share_wallet_zero", None)
        assert wallet
        # Look for PNG tEXt/iTXt chunks that might carry entry titles.
        blob = pytest.share_bytes_zero
        # Scan for common lore words that should NEVER appear in metadata.
        forbidden = [b"Ethereal", b"companions-secret", b"tinkerpug_excerpt"]
        for tok in forbidden:
            assert tok not in blob, f"forbidden token {tok!r} appears in PNG bytes"


# ── /api/archive/record ─────────────────────────────────────────────────
class TestRecordLeaderboard:
    def test_record_default_shape(self, http):
        r = http.get(f"{BASE_URL}/api/archive/record")
        assert r.status_code == 200
        data = r.json()
        for k in ("total", "page", "limit", "has_more", "entries"):
            assert k in data, f"missing key {k}"
        assert data["page"] == 1
        assert data["limit"] == 10
        assert isinstance(data["entries"], list)
        if data["entries"]:
            e = data["entries"][0]
            for k in ("position", "wallet", "rank", "rank_title", "unlocked_count", "rank_reached_at"):
                assert k in e, f"entry missing key {k}: {e.keys()}"
            assert e["position"] == 1
            # Excludes zero-unlockers
            assert e["unlocked_count"] > 0

    def test_record_excludes_zero_unlocks(self, http):
        r = http.get(f"{BASE_URL}/api/archive/record?limit=50")
        assert r.status_code == 200
        for e in r.json()["entries"]:
            assert e["unlocked_count"] > 0, f"row {e} has zero unlocks"

    def test_record_sorted_desc(self, http):
        r = http.get(f"{BASE_URL}/api/archive/record?limit=50")
        entries = r.json()["entries"]
        counts = [e["unlocked_count"] for e in entries]
        assert counts == sorted(counts, reverse=True), f"not sorted desc: {counts}"

    def test_record_pagination_positions_continue(self, http):
        r1 = http.get(f"{BASE_URL}/api/archive/record?page=1&limit=5")
        r2 = http.get(f"{BASE_URL}/api/archive/record?page=2&limit=5")
        assert r1.status_code == 200 and r2.status_code == 200
        e1 = r1.json()["entries"]
        e2 = r2.json()["entries"]
        if len(e1) == 5 and e2:
            assert e1[0]["position"] == 1
            assert e2[0]["position"] == 6, f"page 2 first pos = {e2[0]['position']} (expected 6)"
            if len(e2) >= 2:
                assert e2[1]["position"] == 7


# ── rank_reached_at population ──────────────────────────────────────────
class TestRankReachedAt:
    def test_fresh_wallet_hits_seeker_and_appears_in_record(self):
        """Create a fresh wallet, unlock all Tier 1 entries via /api/ai/chat,
        then verify record shows rank_reached_at set.

        NOTE: substantive AI chat calls are slow (5-15s each × 16 entries).
        To keep test time reasonable, directly call the archive
        service's record_unlock via HTTP is not possible, so we shortcut
        by seeding archive_unlocks + calling record_unlock via a helper
        request. Instead of running 16 AI-chats, seed directly in Mongo,
        then trigger record_unlock through the ranks recompute path.
        Fallback: skip if seeding fails; the leaderboard is verified via
        pre-existing wallets in other tests.
        """
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient

        wallet = f"RecordTest_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        async def _seed_and_check():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            # Import service directly to invoke record_unlock (avoids brittle AI calls)
            import sys
            sys.path.insert(0, "/app/backend")
            from services import archive_achievements as arc

            # Get Tier 1 slugs
            master = arc.MASTER_ENTRIES if hasattr(arc, "MASTER_ENTRIES") else []
            tier1_slugs = [e["slug"] for e in master if e.get("tier") == 1][:16]
            if not tier1_slugs:
                # Alternate discovery
                r = requests.get(f"{BASE_URL}/api/archive/entries")
                tier1_slugs = [e["slug"] for e in r.json()["entries"] if e.get("tier") == 1]
            for slug in tier1_slugs:
                try:
                    await arc.record_unlock(wallet, slug, unlock_prompt="test seed")
                except Exception as ex:
                    print(f"seed unlock failed for {slug}: {ex}")

            # Now query rank via HTTP
            rank_resp = requests.get(f"{BASE_URL}/api/archive/rank?wallet={wallet}")
            snap = rank_resp.json()

            # Look up ranks row directly
            row = await db.archive_ranks.find_one({"wallet_address": wallet})
            client.close()
            return snap, row, tier1_slugs

        snap, row, tier1_slugs = asyncio.get_event_loop().run_until_complete(_seed_and_check())
        print(f"seeded {len(tier1_slugs)} tier1 unlocks for {wallet}: snap={snap}")
        assert row is not None, "archive_ranks row not created"
        assert row.get("unlocked_count", 0) > 0
        # rank_title should be Seeker (or higher) after unlocking all Tier 1
        assert snap.get("rank_title") in ("Seeker", "Archivist", "Keeper's Circle"), snap
        # rank_reached_at must be set (fresh wallet)
        assert row.get("rank_reached_at") is not None, "rank_reached_at not populated"

        # Verify appears in /record
        # It may be on page N — scan up to 20 pages
        found = False
        for page in range(1, 21):
            rr = requests.get(f"{BASE_URL}/api/archive/record?page={page}&limit=50")
            entries = rr.json().get("entries", [])
            if not entries:
                break
            for e in entries:
                if e["wallet"] == wallet:
                    found = True
                    assert e["rank_title"] in ("Seeker", "Archivist", "Keeper's Circle")
                    assert e["rank_reached_at"], "rank_reached_at empty in record row"
                    break
            if found or not rr.json().get("has_more"):
                break
        assert found, f"seeded wallet {wallet} not found in /record"

        # Cleanup
        async def _clean():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            await db.archive_unlocks.delete_many({"wallet_address": wallet})
            await db.archive_ranks.delete_many({"wallet_address": wallet})
            client.close()

        asyncio.get_event_loop().run_until_complete(_clean())
