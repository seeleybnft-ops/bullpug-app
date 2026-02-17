"""Shared pot game state module.

This module provides a centralized state for the pot game that can be
accessed by multiple routers (pot, admin) and WebSocket handlers.
"""

import uuid
from datetime import datetime, timezone

# Configuration
RAKE_PERCENT = 2.5
DISTRIBUTION_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"


def create_fresh_pot():
    """Create a new pot with default values."""
    return {
        "id": str(uuid.uuid4()),
        "total_amount_sol": 0,
        "entries": [],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "draw_at": None,
        "countdown_started": False,
        "countdown_seconds": 60,
        "rake_percent": RAKE_PERCENT,
        "winner": None
    }


# Active pot stored in memory (resets on server restart)
active_pot = create_fresh_pot()


def reset_pot():
    """Reset the pot to initial state."""
    global active_pot
    active_pot = create_fresh_pot()


def get_pot():
    """Get the current pot state."""
    return active_pot


def update_pot(updates: dict):
    """Update the pot with given values."""
    global active_pot
    active_pot.update(updates)
