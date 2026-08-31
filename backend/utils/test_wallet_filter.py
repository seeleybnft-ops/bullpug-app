"""Test-wallet detection — one place, one regex.

Testing agents follow deterministic naming for the ephemeral wallets
they generate. This module recognises those patterns so:
  • production collections (leaderboard, admin stats) can filter them
    out at query time — no user-facing surface ever shows them
  • cleanup scripts can locate and delete them safely

Never write to this file lightly — the regex is the source of truth
for what counts as "test data". Add a new prefix only when a testing
agent adopts a new naming convention.
"""

from __future__ import annotations

import re
from typing import Optional

# Prefixes and shapes the testing agents (and manual smoke curl runs)
# have historically used. Case-sensitive on the deliberate ones and
# case-insensitive on the generic "TEST"/"test" catch-all.
_TEST_WALLET_RE = re.compile(
    r"^("
    r"TEST[^\s]*"                # TESTWALLET_*, TEST_CHAT_*, TESTwallet_*, TESTWALLET_IDEM_$
    r"|test[_-][^\s]*"           # test_wallet_*, test-foo, etc.
    r"|Test[^\s]*"               # TestWallet_*, TestFoo_*
    r"|ARCH_FRESH_[^\s]*"
    r"|DropTest[^\s]*"
    r"|Classifier(Neg|Block)Test[^\s]*"
    r"|LoreTest_[^\s]*"
    r"|RecordTest[^\s]*"
    r"|ShareTest[^\s]*"
    r"|CompanionTest[^\s]*"
    r"|siwsprobe[^\s]*"          # SIWS smoke-test wallets
    r"|reftest-[^\s]*"           # visual-reference regression wallets
    r"|anon-[^\s]*"              # daily_drop.py convention for pre-connect sessions
    r"|0x[a-fA-F0-9]{40}"        # Bullpug is Solana — any EVM-format address is a test artefact
    r")$"
)


def is_test_wallet(addr: Optional[str]) -> bool:
    """Return True if `addr` matches any known testing pattern.

    Empty / None returns False so callers can safely pass whatever
    they've got.
    """
    if not addr:
        return False
    return bool(_TEST_WALLET_RE.match(str(addr).strip()))


# Regex string for use inside Mongo `$regex` filters. Callers embed
# this so a single `find({wallet: {"$not": {"$regex": TEST_WALLET_REGEX}}})`
# excludes test rows at the DB level.
TEST_WALLET_REGEX = _TEST_WALLET_RE.pattern
