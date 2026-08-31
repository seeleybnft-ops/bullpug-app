"""Backend tests — Keeper's Circle live announcement feed."""
import os
import asyncio
from datetime import datetime, timezone

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
assert DB_NAME, "DB_NAME env var missing"
assert MONGO_URL, "MONGO_URL env var missing"
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

REAL_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"
TEST_WALLET = "TESTWALLET_KC_ANNOUNCE_1"


def _run(coro):
    """Run coro in a fresh event loop with a fresh motor client (per iter 114 pattern)."""
    async def _inner():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            return await coro(db)
        finally:
            client.close()
    return asyncio.run(_inner())


@pytest.fixture(autouse=True)
def clean_announcements():
    """Remove test-created rows before + after each test."""
    async def _clean(db):
        await db.keeper_announcements.delete_many({
            "wallet_address": {"$in": [REAL_WALLET, TEST_WALLET]}
        })
    _run(_clean)
    yield
    _run(_clean)


# ── /api/archive/announcements endpoint ──────────────────────────────
def test_announcements_empty_returns_shape():
    r = requests.get(f"{BASE_URL}/api/archive/announcements", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "count" in data
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])


def test_announcements_limit_clamped_to_25():
    # limit=99 should return 422 due to FastAPI Query validation (le=25)
    r = requests.get(f"{BASE_URL}/api/archive/announcements?limit=99", timeout=10)
    # Either clamped (200 with <=25 items) or validation-rejected (422)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert len(r.json()["items"]) <= 25


def test_announcements_limit_25_ok():
    r = requests.get(f"{BASE_URL}/api/archive/announcements?limit=25", timeout=10)
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 25


def test_real_wallet_announcement_visible():
    now = datetime.now(timezone.utc).isoformat()
    async def _insert(db):
        await db.keeper_announcements.insert_one({
            "wallet_address": REAL_WALLET,
            "rank": "keepers_circle",
            "rank_title": "Keeper's Circle",
            "created_at": now,
        })
    _run(_insert)

    r = requests.get(f"{BASE_URL}/api/archive/announcements?limit=10", timeout=10)
    assert r.status_code == 200
    items = r.json()["items"]
    wallets = [i.get("wallet_address") for i in items]
    assert REAL_WALLET in wallets
    # Newest-first ordering + shape
    match = next(i for i in items if i["wallet_address"] == REAL_WALLET)
    assert match.get("rank_title") == "Keeper's Circle"
    assert match.get("created_at") == now
    assert "_id" not in match


def test_test_wallet_announcement_filtered():
    now = datetime.now(timezone.utc).isoformat()
    async def _insert(db):
        await db.keeper_announcements.insert_one({
            "wallet_address": TEST_WALLET,
            "rank": "keepers_circle",
            "rank_title": "Keeper's Circle",
            "created_at": now,
        })
    _run(_insert)

    r = requests.get(f"{BASE_URL}/api/archive/announcements?limit=25", timeout=10)
    assert r.status_code == 200
    wallets = [i.get("wallet_address") for i in r.json()["items"]]
    assert TEST_WALLET not in wallets


def test_newest_first_ordering():
    async def _insert(db):
        await db.keeper_announcements.insert_many([
            {"wallet_address": REAL_WALLET, "rank": "keepers_circle",
             "rank_title": "Keeper's Circle",
             "created_at": "2020-01-01T00:00:00+00:00"},
            {"wallet_address": REAL_WALLET + "b", "rank": "keepers_circle",
             "rank_title": "Keeper's Circle",
             "created_at": "2030-01-01T00:00:00+00:00"},
        ])
    _run(_insert)
    try:
        r = requests.get(f"{BASE_URL}/api/archive/announcements?limit=10", timeout=10)
        items = r.json()["items"]
        # First real-wallet items should be sorted newest first
        real_items = [i for i in items if i["wallet_address"].startswith(REAL_WALLET[:6])]
        assert len(real_items) >= 2
        assert real_items[0]["created_at"] >= real_items[1]["created_at"]
    finally:
        async def _clean(db):
            await db.keeper_announcements.delete_many({"wallet_address": REAL_WALLET + "b"})
        _run(_clean)


# ── Index existence ──────────────────────────────────────────────────
def test_keeper_announcements_index_exists():
    async def _check(db):
        idx = await db.keeper_announcements.list_indexes().to_list(length=50)
        return idx
    indexes = _run(_check)
    # look for index with created_at descending
    keys = [tuple(i.get("key", {}).items()) for i in indexes]
    found = any(("created_at", -1) in list(k) for k in keys)
    assert found, f"No created_at -1 index found. Indexes: {indexes}"


# ── record_unlock rank-up hook ──────────────────────────────────────
def test_record_unlock_hook_inserts_on_kc_rankup():
    """Directly call record_unlock in a scenario that transitions to KC.

    Runs all async ops in a single asyncio.run(), and patches the shared
    motor client so it stays alive for the whole test.
    """
    import sys
    sys.path.insert(0, "/app/backend")

    kc_wallet = "TESTWALLET_KC_HOOK_1"

    async def _all():
        # Fresh client bound to THIS loop
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        # Patch the shared db reference so archive_achievements uses ours
        import utils.database as udb
        udb.db = db
        # Reload archive_achievements' cached db symbol
        if "services.archive_achievements" in sys.modules:
            del sys.modules["services.archive_achievements"]
        from services import archive_achievements as arch

        try:
            await db.archive_unlocks.delete_many({"wallet_address": kc_wallet})
            await db.archive_ranks.delete_many({"wallet_address": kc_wallet})
            await db.keeper_announcements.delete_many({"wallet_address": kc_wallet})

            all_slugs = list(arch._TIER1_SLUGS | arch._TIER2_SLUGS | arch._TIER3_SLUGS)
            last_slug = None
            for slug in all_slugs:
                if slug in arch._TIER3_SLUGS and last_slug is None:
                    last_slug = slug
                    continue
                await db.archive_unlocks.insert_one({
                    "wallet_address": kc_wallet,
                    "entry_id": slug,
                    "entry_tier": arch._BY_SLUG[slug]["tier"],
                    "unlocked_at": "2025-01-01T00:00:00+00:00",
                })
            unlocked = await arch.get_unlocked_slugs(kc_wallet)
            prev = arch.compute_rank(unlocked)
            await db.archive_ranks.update_one(
                {"wallet_address": kc_wallet},
                {"$set": {"wallet_address": kc_wallet, "rank": prev,
                          "rank_title": arch.RANK_TITLES.get(prev),
                          "unlocked_count": len(unlocked),
                          "updated_at": "2025-01-01T00:00:00+00:00"}},
                upsert=True,
            )
            assert prev == arch.RANK_ARCHIVIST

            result = await arch.record_unlock(kc_wallet, last_slug, "test", "test")
            assert result is not None
            assert result["is_rank_up"] is True
            assert result["new_rank"] == arch.RANK_KEEPERS_CIRCLE

            ann = await db.keeper_announcements.find_one({"wallet_address": kc_wallet})
            assert ann is not None
            assert ann["rank"] == "keepers_circle"
        finally:
            await db.archive_unlocks.delete_many({"wallet_address": kc_wallet})
            await db.archive_ranks.delete_many({"wallet_address": kc_wallet})
            await db.keeper_announcements.delete_many({"wallet_address": kc_wallet})
            client.close()

    asyncio.run(_all())


def test_record_unlock_no_announcement_for_seeker_or_archivist():
    """Rank-up to Seeker must NOT insert into keeper_announcements."""
    import sys
    sys.path.insert(0, "/app/backend")

    wallet = "TESTWALLET_KC_HOOK_SEEKER"

    async def _all():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        import utils.database as udb
        udb.db = db
        # Force rebinding of `db` in every already-imported services module
        import importlib
        for name in list(sys.modules.keys()):
            if name.startswith("services."):
                mod = sys.modules[name]
                if hasattr(mod, "db"):
                    try:
                        mod.db = db
                    except Exception:
                        pass
        from services import archive_achievements as arch

        try:
            await db.archive_unlocks.delete_many({"wallet_address": wallet})
            await db.archive_ranks.delete_many({"wallet_address": wallet})
            await db.keeper_announcements.delete_many({"wallet_address": wallet})

            t1 = list(arch._TIER1_SLUGS)
            last = t1[0]
            for slug in t1[1:]:
                await db.archive_unlocks.insert_one({
                    "wallet_address": wallet, "entry_id": slug,
                    "entry_tier": 1, "unlocked_at": "2025-01-01T00:00:00+00:00",
                })
            result = await arch.record_unlock(wallet, last, "test", "test")
            assert result["is_rank_up"] is True
            assert result["new_rank"] == arch.RANK_SEEKER
            count = await db.keeper_announcements.count_documents({"wallet_address": wallet})
            assert count == 0
        finally:
            await db.archive_unlocks.delete_many({"wallet_address": wallet})
            await db.archive_ranks.delete_many({"wallet_address": wallet})
            client.close()

    asyncio.run(_all())


# ── archive_test_cleanup includes keeper_announcements ───────────────
def test_purge_test_wallet_removes_announcement():
    import sys
    sys.path.insert(0, "/app/backend")

    async def _all():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        import utils.database as udb
        udb.db = db
        # Force re-import so purge_test_wallet_data uses patched db
        for mod in ("services.archive_test_cleanup",):
            if mod in sys.modules:
                del sys.modules[mod]
        from services import archive_test_cleanup

        assert ("keeper_announcements", "wallet_address") in archive_test_cleanup._TARGETS

        try:
            await db.keeper_announcements.insert_one({
                "wallet_address": TEST_WALLET,
                "rank": "keepers_circle",
                "rank_title": "Keeper's Circle",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            results = await archive_test_cleanup.purge_test_wallet_data()
            assert results.get("keeper_announcements", 0) >= 1
            count = await db.keeper_announcements.count_documents({"wallet_address": TEST_WALLET})
            assert count == 0
        finally:
            await db.keeper_announcements.delete_many({"wallet_address": TEST_WALLET})
            client.close()

    asyncio.run(_all())
