"""Daily job — purge test-wallet rows across Archive collections.

The regex is defined once in `utils.test_wallet_filter` so this task
uses the same definition the leaderboard filter uses. Invoked from
`utils/scheduler.py` at 03:15 UTC each day.
"""

from __future__ import annotations

import logging
from typing import Dict

from utils.database import db
from utils.test_wallet_filter import TEST_WALLET_REGEX

logger = logging.getLogger(__name__)

# (collection, field-that-holds-the-wallet). Every collection listed
# stores exactly one wallet-like identifier per row; the field varies.
_TARGETS = (
    ("archive_ranks",   "wallet_address"),
    ("archive_unlocks", "wallet_address"),
    ("chat_history",    "wallet_address"),
    ("daily_drops",     "user_key"),
    ("share_card_art",  "wallet"),
    ("tinkerpug_turns", "wallet_address"),
)


async def purge_test_wallet_data() -> Dict[str, int]:
    """Delete every row whose wallet-field matches TEST_WALLET_REGEX.

    Returns a `{collection: deleted_count}` mapping. Never touches real
    user rows (regex is anchored at both ends, matches only known
    testing prefixes).
    """
    results: Dict[str, int] = {}
    collections = await db.list_collection_names()
    for name, field in _TARGETS:
        if name not in collections:
            results[name] = 0
            continue
        try:
            r = await db[name].delete_many({field: {"$regex": TEST_WALLET_REGEX}})
            results[name] = r.deleted_count
        except Exception as e:
            logger.warning("test-wallet purge failed for %s: %s", name, e)
            results[name] = 0
    return results
