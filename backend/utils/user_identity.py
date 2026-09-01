"""Unified user identity layer (hybrid strategy).

We keep every existing collection's `wallet_address` field untouched so
the current wallet code paths keep working with zero disruption. On top
of that we add a `user_id` field to every identity-bearing document so
new email-authenticated users have somewhere to sit in the same
collections. A wallet user's `user_id` is deterministic (`wallet_<addr>`)
so the migration is idempotent and reversible.

Public API:
  • `derive_user_id_from_wallet(wallet)`  — pure, deterministic
  • `resolve_or_create_wallet_user(wallet)` — upsert `users` row, return uid
  • `resolve_email_user(email)`             — lookup by email, no create
  • `create_email_user(email)`              — create+return a new email uid
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from utils.database import db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def derive_user_id_from_wallet(wallet_address: str) -> str:
    """Deterministic user_id for wallet-authenticated users.

    Chosen so re-running the migration on the same wallet is a no-op
    and so a wallet route (which still receives `wallet_address` as a
    query param) can locally derive its own user_id without hitting
    Mongo for every request.
    """
    return f"wallet_{wallet_address}"


async def resolve_or_create_wallet_user(wallet_address: str) -> str:
    """Idempotent: ensure a `users` row exists for this wallet, return uid.

    Called from the SIWS login flow and from the migration script. Uses
    `update_one(..., upsert=True)` so concurrent calls converge on a
    single row.
    """
    user_id = derive_user_id_from_wallet(wallet_address)
    now = _now_iso()
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$setOnInsert": {
                "user_id": user_id,
                "email": None,
                "email_verified": False,
                "wallet_address": wallet_address,
                "auth_type": "wallet",
                "created_at": now,
                "newsletter_opt_in": False,
            },
            "$set": {"last_active": now},
        },
        upsert=True,
    )
    return user_id


async def resolve_email_user(email: str) -> Optional[dict]:
    """Return the users row for this email, or None. Case-insensitive."""
    if not email:
        return None
    return await db.users.find_one(
        {"email": email.strip().lower()},
        {"_id": 0},
    )


async def create_email_user(email: str) -> dict:
    """Create a brand-new email-auth user. Caller must have verified OTP.

    Not idempotent on purpose — callers should check `resolve_email_user`
    first and only reach here for genuine new signups.
    """
    normalized = email.strip().lower()
    now = _now_iso()
    doc = {
        "user_id": str(uuid.uuid4()),
        "email": normalized,
        "email_verified": True,
        "wallet_address": None,
        "auth_type": "email",
        "created_at": now,
        "last_active": now,
        "newsletter_opt_in": False,
    }
    await db.users.insert_one(doc)
    return doc


async def touch_user(user_id: str) -> None:
    """Update `last_active` on any auth path. Silent on missing row."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"last_active": _now_iso()}},
    )
