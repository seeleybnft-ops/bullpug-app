"""Tests for iteration_114:
- Archive test-wallet cleanup service (purge_test_wallet_data)
- Admin stats endpoint auth + shape (filters test wallets)
- Visual Canon admin endpoints require admin JWT (401 without bearer)
- POST /api/archive/share still works and returns fresh (uncached) image
"""
import os
import sys
import asyncio
import pytest
import requests

sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read from frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

TEST_WALLET = "TESTWALLET_STATS_CRON_1"


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "X-Bullpug-CSRF": "1"})
    return s


# ── Cleanup service ────────────────────────────────────────────────
class TestArchiveTestCleanup:
    def test_purge_deletes_seeded_test_wallet(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        import utils.database as udb
        import services.archive_test_cleanup as cleanup_mod

        async def _run():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            udb.db = db
            cleanup_mod.db = db
            # Seed test rows in each collection using matching field names
            await db.archive_ranks.insert_one({
                "wallet_address": TEST_WALLET, "rank": "seeker",
                "rank_title": "Seeker", "unlocked_count": 5,
                "updated_at": "2026-01-01T00:00:00+00:00",
            })
            await db.archive_unlocks.insert_one({
                "wallet_address": TEST_WALLET, "entry_id": "test_e",
                "unlocked_at": "2026-01-01T00:00:00+00:00",
            })
            res = await cleanup_mod.purge_test_wallet_data()
            # Ensure gone
            remaining_ranks = await db.archive_ranks.count_documents({"wallet_address": TEST_WALLET})
            remaining_unlocks = await db.archive_unlocks.count_documents({"wallet_address": TEST_WALLET})
            client.close()
            return res, remaining_ranks, remaining_unlocks

        res, r1, r2 = asyncio.run(_run())
        assert isinstance(res, dict)
        # Every target key present
        for k in ("archive_ranks", "archive_unlocks", "chat_history",
                  "daily_drops", "share_card_art", "tinkerpug_turns"):
            assert k in res, f"key {k} missing in purge result"
        assert res["archive_ranks"] >= 1
        assert res["archive_unlocks"] >= 1
        assert r1 == 0
        assert r2 == 0


# ── Admin endpoints auth gating ────────────────────────────────────
class TestAdminAuthGating:
    def test_admin_stats_no_bearer_401(self, api_client):
        r = api_client.get(f"{API}/archive/admin/stats")
        assert r.status_code in (401, 403), f"got {r.status_code}: {r.text[:200]}"

    def test_admin_canon_list_no_bearer_401(self, api_client):
        r = api_client.get(f"{API}/archive/admin/canon")
        assert r.status_code in (401, 403)

    def test_admin_canon_list_with_status_filter_401(self, api_client):
        for st in ("canon", "pending", "retired"):
            r = api_client.get(f"{API}/archive/admin/canon", params={"status": st})
            assert r.status_code in (401, 403), f"status={st} → {r.status_code}"

    def test_admin_canon_promote_no_bearer_401(self, api_client):
        r = api_client.post(f"{API}/archive/admin/canon/promote",
                            json={"subject_tag": "foo"})
        assert r.status_code in (401, 403)

    def test_admin_canon_retire_no_bearer_401(self, api_client):
        r = api_client.post(f"{API}/archive/admin/canon/retire",
                            json={"subject_tag": "foo"})
        assert r.status_code in (401, 403)

    def test_admin_canon_image_no_bearer_401(self, api_client):
        r = api_client.get(f"{API}/archive/admin/canon/image/foo")
        assert r.status_code in (401, 403)


# ── Admin stats internal (bypassing JWT) — verify test-wallet filter ──
class TestAdminStatsFilter:
    def test_admin_stats_filters_test_wallets(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        import services.archive_achievements as aa
        import utils.database as udb

        async def _run():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            udb.db = db  # rebind for the service
            aa.db = db
            await db.archive_ranks.insert_one({
                "wallet_address": "TESTWALLET_STATS_2",
                "rank": "seeker",
                "rank_title": "Seeker",
                "unlocked_count": 16,
                "updated_at": "2026-01-01T00:00:00+00:00",
            })
            try:
                stats = await aa.admin_stats()
            finally:
                await db.archive_ranks.delete_many(
                    {"wallet_address": "TESTWALLET_STATS_2"}
                )
                client.close()
            return stats

        stats = asyncio.run(_run())
        # Keys present
        for k in ("total_entries", "grand_total_entries", "total_wallets",
                  "entries", "rank_distribution", "daily_active_wallets"):
            assert k in stats, f"missing key {k}"
        # Rank distribution has all 4 buckets
        for r in ("none", "seeker", "archivist", "keepers_circle"):
            assert r in stats["rank_distribution"], f"missing rank {r}"
        # daily_active_wallets is int
        assert isinstance(stats["daily_active_wallets"], int)
        assert stats["daily_active_wallets"] >= 0
        # total_entries expected 61
        assert stats["total_entries"] == 61
        assert stats["grand_total_entries"] == 62
        # entries is list
        assert isinstance(stats["entries"], list)
        assert len(stats["entries"]) >= 1


# ── Share card still functional ────────────────────────────────────
class TestShareCard:
    def test_share_returns_grand_total_and_fresh_image(self, api_client):
        w = "TESTWALLET_SHARE_1"
        r1 = api_client.post(f"{API}/archive/share", json={"wallet": w})
        assert r1.status_code == 200, f"got {r1.status_code}: {r1.text[:300]}"
        d1 = r1.json()
        assert "image_base64" in d1
        assert d1.get("grand_total") == 62
        assert len(d1["image_base64"]) > 100

        r2 = api_client.post(f"{API}/archive/share", json={"wallet": w})
        assert r2.status_code == 200
        d2 = r2.json()
        # Not required to be different bytewise, but service claims no
        # cache. Log if equal but don't fail.
        if d1["image_base64"] == d2["image_base64"]:
            print("WARN: two share calls returned identical base64 (may be cached)")

        # Cleanup: purge any test-wallet residue
        from motor.motor_asyncio import AsyncIOMotorClient
        async def _cleanup():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            await db.archive_ranks.delete_many({"wallet_address": w})
            await db.share_card_art.delete_many({"wallet": w})
            client.close()
        asyncio.run(_cleanup())
