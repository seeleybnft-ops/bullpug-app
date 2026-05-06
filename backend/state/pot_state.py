"""Shared pot game state module.

In-memory cache mirrors a single MongoDB document at ``db.active_pot``. Every
mutation goes through ``persist_pot()`` so a crash mid-round does not vaporize
player entries.

All amount math is done in **lamports** (integers) to avoid float drift.
The float ``*_sol`` fields are kept for backwards-compatible API responses
and are derived from the canonical ``*_lamports`` fields.
"""

import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Configuration
RAKE_PERCENT = 2.5
DISTRIBUTION_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"

LAMPORTS_PER_SOL = 1_000_000_000
ACTIVE_POT_DOC_ID = "active"


def sol_to_lamports(sol: float) -> int:
    """Convert SOL float → lamports int (round to nearest)."""
    return int(round(float(sol) * LAMPORTS_PER_SOL))


def lamports_to_sol(lamports: int) -> float:
    """Convert lamports int → SOL float."""
    return round(int(lamports) / LAMPORTS_PER_SOL, 9)


def create_fresh_pot():
    """Create a new pot with default values."""
    return {
        "id": str(uuid.uuid4()),
        "total_lamports": 0,
        "total_amount_sol": 0.0,
        "entries": [],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "draw_at": None,
        "countdown_started": False,
        "countdown_seconds": 60,
        "rake_percent": RAKE_PERCENT,
        "winner": None
    }


# Active pot in-memory cache. Initialised from DB at startup via load_pot().
active_pot = create_fresh_pot()


def get_pot():
    """Get the current pot state (in-memory cache)."""
    return active_pot


async def persist_pot():
    """Write the in-memory pot to MongoDB so a crash doesn't lose entries."""
    try:
        from utils.database import db
        doc = {**active_pot, "_id": ACTIVE_POT_DOC_ID, "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.active_pot.replace_one({"_id": ACTIVE_POT_DOC_ID}, doc, upsert=True)
    except Exception as e:
        logger.error(f"persist_pot failed: {e}")


async def load_pot():
    """Load pot state from MongoDB on startup. If none, create a fresh pot."""
    global active_pot
    try:
        from utils.database import db
        doc = await db.active_pot.find_one({"_id": ACTIVE_POT_DOC_ID})
        if doc:
            doc.pop("_id", None)
            doc.pop("updated_at", None)
            # Backfill lamport totals if loading from older format
            if "total_lamports" not in doc:
                doc["total_lamports"] = sol_to_lamports(doc.get("total_amount_sol", 0))
            for e in doc.get("entries", []):
                if "amount_lamports" not in e:
                    e["amount_lamports"] = sol_to_lamports(e.get("amount_sol", 0))
            active_pot = doc
            logger.info(
                f"Loaded persisted pot {active_pot['id'][:8]} from DB: "
                f"{active_pot['total_amount_sol']} SOL across {len(active_pot['entries'])} entries"
            )
        else:
            active_pot = create_fresh_pot()
            await persist_pot()
            logger.info(f"No persisted pot found — created fresh pot {active_pot['id'][:8]}")
    except Exception as e:
        logger.error(f"load_pot failed (using in-memory fresh pot): {e}")
        active_pot = create_fresh_pot()


async def reset_pot():
    """Reset the pot to initial state and persist."""
    global active_pot
    active_pot = create_fresh_pot()
    await persist_pot()
