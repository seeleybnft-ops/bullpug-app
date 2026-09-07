"""Companion API — physical-companion token claim + admin management.

The plushie backend infrastructure. Each Bullpug plushie ships (or will
ship) with a printed token. When a customer visits `/companion?key=…`
they connect their wallet and claim the token. The claim atomically:
  • marks the token as claimed (records wallet + timestamp)
  • fires the `companions-secret` Archive unlock for that wallet
  • lets the frontend play the custom celebration

Endpoints under `/api/companion` (public):
  GET  /api/companion/validate?key=…       — validate a token (pre-connect)
  POST /api/companion/claim                — claim {token, wallet_address}

Endpoints under `/api/admin/companions/tokens` (admin auth):
  GET  /api/admin/companions/tokens        — list every token
  POST /api/admin/companions/tokens        — generate a new unclaimed token

Data model — `companion_tokens` collection:
  {
    token          : str  (unique, UUID4 hex string)
    order_id       : str | None  (null until the store is built)
    wallet_claimed : str | None
    claimed_at     : ISO string | None
    created_at     : ISO string
    created_by     : str | None  (admin wallet for auditability)
  }
Indexes are declared in `server.py` startup: unique on `token`,
non-unique on `wallet_claimed`.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services import archive_achievements as archive
from utils.admin_auth import require_admin_jwt
from utils.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companion", tags=["companion"])
admin_router = APIRouter(prefix="/admin/companions", tags=["companion-admin"])

_TOKENS_COLLECTION = "companion_tokens"


# ── Helpers ────────────────────────────────────────────────────────────
def _new_token() -> str:
    """Generate a fresh, unclaimed token string.

    Length ~22 chars — short enough to print on a hang-tag QR link,
    long enough that guessing is impractical (128 bits of entropy).
    """
    return uuid.uuid4().hex[:22]


def _clean(v: Optional[str], maxlen: int = 96) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return s[:maxlen]


def _serialise(doc: dict) -> dict:
    """Drop `_id`, keep everything else. Used by admin listings."""
    if not doc:
        return doc
    return {k: v for k, v in doc.items() if k != "_id"}


# ── Public endpoints ───────────────────────────────────────────────────
class ClaimRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=64)
    wallet_address: str = Field(..., min_length=8, max_length=96)


@router.get("/validate")
async def validate_token(key: Optional[str] = Query(None, description="Companion token")):
    """Check if a companion token is valid (exists + unclaimed).

    Response:
      { "valid": bool, "claimed": bool, "reason": "unknown" | "already_claimed" | null }
    """
    token = _clean(key, maxlen=64)
    if not token:
        return {"valid": False, "claimed": False, "reason": "unknown"}
    doc = await db[_TOKENS_COLLECTION].find_one({"token": token})
    if not doc:
        return {"valid": False, "claimed": False, "reason": "unknown"}
    if doc.get("wallet_claimed"):
        return {"valid": False, "claimed": True, "reason": "already_claimed"}
    return {"valid": True, "claimed": False, "reason": None}


@router.post("/claim")
async def claim_token(payload: ClaimRequest):
    """Atomically claim a companion token to a wallet.

    Uses `find_one_and_update` with a `wallet_claimed: null` filter so
    concurrent claims for the same token race safely — the second
    caller sees the token as already claimed. On success, fires the
    Archive `companions-secret` unlock so the wallet's ledger picks it
    up on the next poll.
    """
    token = _clean(payload.token, maxlen=64)
    wallet = _clean(payload.wallet_address, maxlen=96)
    if not token or not wallet:
        raise HTTPException(status_code=400, detail="token and wallet_address are required")

    now = datetime.now(timezone.utc).isoformat()
    result = await db[_TOKENS_COLLECTION].find_one_and_update(
        {"token": token, "wallet_claimed": None},
        {"$set": {"wallet_claimed": wallet, "claimed_at": now}},
        return_document=True,  # returns AFTER modification
    )
    if not result:
        # Token doesn't exist OR is already claimed. Disambiguate for the UI.
        existing = await db[_TOKENS_COLLECTION].find_one({"token": token})
        if not existing:
            raise HTTPException(status_code=404, detail="token not found")
        raise HTTPException(status_code=409, detail="token already claimed")

    # Record the archive unlock for the physical-only entry. Idempotent:
    # re-claiming the same token by the same wallet returns None here
    # (duplicate key) and the response still reports success — the
    # ledger already reflects it.
    try:
        await archive.record_unlock(
            wallet_address=wallet,
            entry_id="companion-arrived",
            unlock_prompt="COMPANION: physical token redeemed",
            tinkerpug_excerpt=archive.COMPANION_ARRIVED_CELEBRATION_TEXT,
        )
    except Exception as e:
        logger.warning("companion-arrived unlock failed for %s: %s", wallet[:12] + "…", e)

    # First-Pack whitelist. This is the durable, wallet-level record of
    # who redeemed a companion in the launch run — used to gate the
    # future NFT airdrop, the "First Pack" gold badge, and any
    # holder-only surprises. Upsert is idempotent per wallet.
    try:
        await db["first_pack_wallets"].update_one(
            {"wallet": wallet},
            {
                "$setOnInsert": {
                    "wallet": wallet,
                    "user_id": wallet,  # wallet == user_id for wallet-auth users
                    "companion_token": token,
                    "claimed_at": now,
                    "order_run": "run-01",
                    "nft_minted": False,
                    "nft_token_id": None,
                }
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning("first_pack_wallets upsert failed for %s: %s", wallet[:12] + "…", e)

    return {
        "success": True,
        "wallet": wallet,
        "claimed_at": now,
        "celebration_text": archive.COMPANION_ARRIVED_CELEBRATION_TEXT,
        "entry_text": archive.COMPANION_ARRIVED_ENTRY_TEXT,
        "entry_slug": "companion-arrived",
        "first_pack": True,
        "order_run": "run-01",
    }


# ── Admin endpoints ────────────────────────────────────────────────────
@admin_router.get("/tokens", dependencies=[Depends(require_admin_jwt)])
async def list_tokens(
    limit: int = Query(200, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="'claimed' | 'unclaimed' | None (all)"),
):
    """Admin — paginated list of every companion token."""
    q: dict = {}
    if status == "claimed":
        q["wallet_claimed"] = {"$ne": None}
    elif status == "unclaimed":
        q["wallet_claimed"] = None
    total = await db[_TOKENS_COLLECTION].count_documents(q)
    cursor = (
        db[_TOKENS_COLLECTION]
        .find(q)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = [_serialise(d) for d in await cursor.to_list(length=limit)]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "tokens": docs,
        "counts": {
            "claimed": await db[_TOKENS_COLLECTION].count_documents(
                {"wallet_claimed": {"$ne": None}}
            ),
            "unclaimed": await db[_TOKENS_COLLECTION].count_documents(
                {"wallet_claimed": None}
            ),
        },
    }


class GenerateTokenRequest(BaseModel):
    order_id: Optional[str] = Field(None, max_length=128)
    note: Optional[str] = Field(None, max_length=256)


@admin_router.post("/tokens", dependencies=[Depends(require_admin_jwt)])
async def generate_token(payload: Optional[GenerateTokenRequest] = None):
    """Admin — create a new unclaimed companion token.

    For gifts, replacements, or competitions where no formal order
    exists yet. `order_id` and `note` are both optional.
    """
    order_id = _clean(payload.order_id, maxlen=128) if payload else None
    note = _clean(payload.note, maxlen=256) if payload else None

    now = datetime.now(timezone.utc).isoformat()
    # Retry on the astronomically unlikely UUID collision.
    for _ in range(4):
        token = _new_token()
        doc = {
            "token": token,
            "order_id": order_id,
            "wallet_claimed": None,
            "claimed_at": None,
            "created_at": now,
            "note": note,
        }
        try:
            await db[_TOKENS_COLLECTION].insert_one(doc)
            return {"success": True, "token": token, "created_at": now}
        except Exception as e:
            if "duplicate" in str(e).lower() or "E11000" in str(e):
                continue
            logger.exception("companion token insert failed")
            raise HTTPException(status_code=500, detail="failed to create token")
    raise HTTPException(status_code=500, detail="token collision — retry")
