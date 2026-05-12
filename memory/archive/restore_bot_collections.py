#!/usr/bin/env python3
"""Restore script for the bot collections archived on 2026-05-12.

Usage (from anywhere on the pod):
    python3 /app/memory/archive/restore_bot_collections.py

It will:
  1. Untar `bot_collections_2026-05-12.tar.gz` to a temp dir
  2. For each .jsonl.gz inside, re-insert all docs into MongoDB under
     the same collection name (skipping if the collection is non-empty
     to avoid clobbering live data).
"""

import asyncio
import base64
import gzip
import json
import sys
import tarfile
import tempfile
from pathlib import Path
from datetime import datetime

ARCHIVE_PATH = Path("/app/memory/archive/bot_collections_2026-05-12.tar.gz")


def _restore_value(v):
    if isinstance(v, dict):
        if "$oid" in v and len(v) == 1:
            from bson import ObjectId
            return ObjectId(v["$oid"])
        if "$date" in v and len(v) == 1:
            try:
                return datetime.fromisoformat(v["$date"].replace("Z", "+00:00"))
            except Exception:
                return v["$date"]
        if "$binary" in v and len(v) == 1:
            return base64.b64decode(v["$binary"])
        return {k: _restore_value(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_restore_value(x) for x in v]
    return v


async def main():
    sys.path.insert(0, "/app/backend")
    from utils.database import db  # noqa

    if not ARCHIVE_PATH.exists():
        print(f"❌ Archive not found at {ARCHIVE_PATH}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(ARCHIVE_PATH) as tf:
            tf.extractall(tmp)
        root = next(Path(tmp).iterdir())
        manifest = json.loads((root / "MANIFEST.json").read_text())
        print(f"Restoring {manifest['total_docs']} docs across "
              f"{len(manifest['collections'])} collections "
              f"(archived {manifest['created_at']})")

        for entry in manifest["collections"]:
            name = entry["collection"]
            existing = await db[name].count_documents({})
            if existing:
                print(f"  ⚠  {name} already has {existing} docs — skipping (delete first to force)")
                continue
            path = root / f"{name}.jsonl.gz"
            if not path.exists():
                print(f"  ⚠  {name}: archive file missing — skipping")
                continue
            docs = []
            with gzip.open(path, "rt", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        docs.append(_restore_value(json.loads(line)))
            if docs:
                await db[name].insert_many(docs)
            print(f"  ✅ {name:35s} restored {len(docs)} docs")

    print("\nRestore complete.")


if __name__ == "__main__":
    asyncio.run(main())
