"""One-off backfill: add `user_id` alongside existing `wallet_address`
fields across all identity-bearing collections (spec Phase A).

Hybrid strategy — we do NOT rewrite / rename any existing field. We
only ADD a `user_id` field to each document that already carries a
wallet identifier. Existing wallet code paths keep working untouched.

Deterministic: `user_id = "wallet_" + wallet_address`. Running the
script twice is a no-op.

Usage:
  # Preview what would change without writing anything:
  python -m backend.scripts.migrate_wallet_to_user_id --dry-run

  # Apply (against whichever Mongo the backend/.env points at):
  python -m backend.scripts.migrate_wallet_to_user_id

  # Or the one-liner form for prod (from /app/backend):
  MONGO_URL=<prod-url> DB_NAME=<prod-db> \
    python scripts/migrate_wallet_to_user_id.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# Support both `python -m …` and direct `python scripts/…` invocations
# by pushing /app/backend onto sys.path when run directly.
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(_BACKEND / ".env")


# ─── Collection → wallet-field map (per spec) ───────────────────────
# The value is the *existing* wallet identifier field on the document.
# The `user_id` field is added alongside it.
COLLECTIONS: List[Tuple[str, str]] = [
    ("archive_unlocks",       "wallet_address"),
    ("archive_ranks",         "wallet_address"),
    ("archive_announcements", "wallet_address"),
    ("daily_drops",           "wallet_address"),
    ("chat_history",          "wallet_address"),
    ("tinkerpug_turns",       "wallet_address"),
    ("share_card_art",        "wallet"),
    ("keeper_announcements",  "wallet_address"),
    # Companion tokens: the wallet field is populated only when a token
    # has been claimed. Unclaimed rows have no wallet and no user_id.
    ("companion_tokens",      "wallet_claimed"),
    # daily_drops and Archive-related rows may also live under `user_key`
    # (the ai_chat code path). Add a secondary pass below for that.
]

# Secondary key: some Archive rows are written with `user_key` (a legacy
# alias). We backfill user_id for any row that carries `user_key` starting
# with `wallet:` — the ai_chat pipeline occasionally uses that prefix.
LEGACY_USER_KEY_PREFIXES = ("wallet:",)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_user_id(wallet: str) -> str:
    return f"wallet_{wallet}"


async def _upsert_users_row(db, wallet: str, dry_run: bool) -> bool:
    """Ensure a `users` document exists for this wallet. Returns True if
    a new row was created (or would be, in dry-run mode)."""
    user_id = _derive_user_id(wallet)
    existing = await db.users.find_one({"user_id": user_id}, {"_id": 0, "user_id": 1})
    if existing:
        return False
    if dry_run:
        return True
    now = _now_iso()
    await db.users.insert_one({
        "user_id": user_id,
        "email": None,
        "email_verified": False,
        "wallet_address": wallet,
        "auth_type": "wallet",
        "created_at": now,
        "last_active": now,
        "newsletter_opt_in": False,
    })
    return True


async def _backfill_collection(db, name: str, wallet_field: str, dry_run: bool) -> Dict[str, int]:
    """Add `user_id` to every doc in `name` that has `wallet_field` set
    but no `user_id` yet. Idempotent — repeat runs find nothing."""
    coll = db[name]
    # Docs that carry the wallet field with a real value AND don't yet
    # have a user_id. This is what makes the script idempotent.
    query = {
        wallet_field: {"$exists": True, "$ne": None, "$nin": [""]},
        "user_id": {"$exists": False},
    }
    total = await coll.count_documents(query)
    if total == 0:
        return {"matched": 0, "wallets_new": 0, "docs_written": 0}

    wallets_seen: set = set()
    docs_written = 0

    cursor = coll.find(query, {"_id": 1, wallet_field: 1})
    async for doc in cursor:
        wallet = doc[wallet_field]
        wallets_seen.add(wallet)
        user_id = _derive_user_id(wallet)
        if dry_run:
            docs_written += 1
            continue
        await coll.update_one(
            {"_id": doc["_id"]},
            {"$set": {"user_id": user_id, "user_id_source": "migration_v1"}},
        )
        docs_written += 1

    wallets_new = 0
    for w in wallets_seen:
        created = await _upsert_users_row(db, w, dry_run)
        if created:
            wallets_new += 1

    return {"matched": total, "wallets_new": wallets_new, "docs_written": docs_written}


async def _backfill_user_key_rows(db, dry_run: bool) -> Dict[str, int]:
    """Some Archive rows carry `user_key = "wallet:<addr>"` from an older
    codepath. Extract the wallet and backfill user_id for those too."""
    stats = {"matched": 0, "wallets_new": 0, "docs_written": 0}
    for name in ("daily_drops", "tinkerpug_turns", "chat_history"):
        coll = db[name]
        query = {
            "user_key": {"$regex": "^wallet:"},
            "user_id": {"$exists": False},
        }
        total = await coll.count_documents(query)
        if total == 0:
            continue
        stats["matched"] += total
        cursor = coll.find(query, {"_id": 1, "user_key": 1})
        seen = set()
        async for doc in cursor:
            wallet = doc["user_key"].split(":", 1)[1]
            seen.add(wallet)
            if not dry_run:
                await coll.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {
                        "user_id": _derive_user_id(wallet),
                        "user_id_source": "migration_v1_userkey",
                    }},
                )
            stats["docs_written"] += 1
        for w in seen:
            if await _upsert_users_row(db, w, dry_run):
                stats["wallets_new"] += 1
    return stats


async def _verify(db) -> Dict[str, dict]:
    """Post-migration audit. For every target collection report:
      • total wallet-bearing docs
      • docs still missing user_id (should be 0)
      • unique wallets covered vs unique user_ids in `users`
    Also spot-check a handful of before/after examples per collection.
    """
    report: Dict[str, dict] = {}
    all_wallets: set = set()
    for name, field in COLLECTIONS:
        coll = db[name]
        total_with_wallet = await coll.count_documents({
            field: {"$exists": True, "$ne": None, "$nin": [""]},
        })
        missing = await coll.count_documents({
            field: {"$exists": True, "$ne": None, "$nin": [""]},
            "user_id": {"$exists": False},
        })
        # sample 3 docs to eyeball
        sample: List[dict] = []
        async for d in coll.find(
            {field: {"$exists": True, "$ne": None}},
            {"_id": 0, field: 1, "user_id": 1},
        ).limit(3):
            sample.append(d)
        # collect wallets covered
        async for d in coll.find(
            {field: {"$exists": True, "$ne": None}},
            {"_id": 0, field: 1},
        ):
            all_wallets.add(d[field])
        report[name] = {
            "total_with_wallet": total_with_wallet,
            "still_missing_user_id": missing,
            "sample": sample,
        }
    users_count = await db.users.count_documents({"auth_type": {"$in": ["wallet", "linked"]}})
    report["_summary"] = {
        "distinct_wallets_across_all_collections": len(all_wallets),
        "users_rows_with_wallet": users_count,
    }
    return report


async def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Print planned writes without touching Mongo.")
    ap.add_argument("--verify-only", action="store_true", help="Skip writes; just print the post-migration audit report.")
    args = ap.parse_args()

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        print("ERROR: MONGO_URL and DB_NAME must be set (backend/.env).", file=sys.stderr)
        sys.exit(2)

    print(f"→ Mongo: {mongo_url.split('@')[-1]}  db={db_name}")
    print(f"→ Mode:  {'DRY-RUN' if args.dry_run else 'VERIFY-ONLY' if args.verify_only else 'APPLY'}\n")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    if not args.verify_only:
        # 1. Ensure the users collection + indexes exist. Safe to re-run.
        # PARTIAL indexes (not sparse) so multiple null-email rows can
        # coexist — MongoDB's sparse-unique still conflicts on nulls.
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index(
            "email",
            unique=True,
            partialFilterExpression={"email": {"$type": "string"}},
        )
        await db.users.create_index(
            "wallet_address",
            unique=True,
            partialFilterExpression={"wallet_address": {"$type": "string"}},
        )

        # 2. Backfill each identity collection.
        totals = {"matched": 0, "wallets_new": 0, "docs_written": 0}
        for name, field in COLLECTIONS:
            stats = await _backfill_collection(db, name, field, args.dry_run)
            print(f"  {name:<24s}  matched={stats['matched']:>5}  wrote={stats['docs_written']:>5}  new users={stats['wallets_new']}")
            for k, v in stats.items():
                totals[k] = totals.get(k, 0) + v

        # 3. Secondary pass for legacy `user_key` rows.
        legacy = await _backfill_user_key_rows(db, args.dry_run)
        print(f"  {'(legacy user_key rows)':<24s}  matched={legacy['matched']:>5}  wrote={legacy['docs_written']:>5}  new users={legacy['wallets_new']}")
        for k, v in legacy.items():
            totals[k] = totals.get(k, 0) + v

        # 4. Reconciliation pass: any `wallet_<addr>` user_id that
        # already lives on a doc but has no corresponding users row.
        # This covers the case where a previous run was interrupted
        # between "backfill doc" and "upsert users row" — otherwise
        # those wallets would be permanently orphaned.
        reconciled = 0
        seen_from_docs: set = set()
        for name, _field in COLLECTIONS:
            async for d in db[name].find(
                {"user_id": {"$regex": "^wallet_"}},
                {"_id": 0, "user_id": 1},
            ):
                seen_from_docs.add(d["user_id"])
        for user_id in seen_from_docs:
            exists = await db.users.find_one({"user_id": user_id}, {"_id": 0, "user_id": 1})
            if exists:
                continue
            wallet = user_id[len("wallet_"):]
            if await _upsert_users_row(db, wallet, args.dry_run):
                reconciled += 1
        if reconciled:
            print(f"  {'(reconciled orphan users)':<24s}  wallets_upserted={reconciled}")
        totals["wallets_new"] = totals.get("wallets_new", 0) + reconciled

        print(f"\n  TOTAL matched={totals['matched']}  docs_written={totals['docs_written']}  wallets_upserted={totals['wallets_new']}")
        if args.dry_run:
            print("\n  (dry-run — no changes committed)")

    # 4. Audit report.
    print("\n=== Post-migration audit ===")
    report = await _verify(db)
    for name, r in report.items():
        if name == "_summary":
            continue
        flag = "" if r["still_missing_user_id"] == 0 else "  ⚠ MISSING"
        print(f"  {name:<24s}  wallet_docs={r['total_with_wallet']:>5}  missing_user_id={r['still_missing_user_id']:>5}{flag}")
    s = report["_summary"]
    print(f"\n  distinct wallets seen:  {s['distinct_wallets_across_all_collections']}")
    print(f"  users rows created:     {s['users_rows_with_wallet']}")

    # Non-zero exit if any collection still has holes — CI-friendly.
    holes = sum(r["still_missing_user_id"] for k, r in report.items() if k != "_summary")
    if holes > 0 and not args.dry_run:
        print(f"\n  ✗ {holes} document(s) still missing user_id.")
        sys.exit(1)
    print("\n  ✓ Audit clean.")


if __name__ == "__main__":
    asyncio.run(main())
