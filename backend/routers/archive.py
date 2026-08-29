"""Archive API — lore ledger, rank, and admin stats.

Endpoints exposed under `/api/archive`:

    GET  /api/archive/unlocks?wallet=...    — full unlock list (newest first)
    GET  /api/archive/rank?wallet=...       — current rank snapshot
    GET  /api/archive/entries?wallet=...    — master list annotated per-wallet
    GET  /api/archive/admin/stats           — admin-only aggregate stats

Auth model (Phase A): a wallet address is passed as a query param. The
only user-visible data any wallet's ledger exposes is (a) which lore
entries they've unlocked and (b) their rank — no PII, no keys, no
tokens. A "view someone else's ledger by pasting their wallet" flow is
actually desirable later (shareable Archive cards, community
leaderboard). If we ever gate this behind a signed SIWS session, the
change is a single dependency swap.

The admin stats endpoint uses the existing `require_admin_jwt` guard
from `utils.admin_auth`.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from services import archive_achievements as archive
from utils.admin_auth import require_admin_jwt

router = APIRouter(prefix="/archive", tags=["archive"])


def _clean_wallet(w: Optional[str]) -> str:
    if not w:
        raise HTTPException(status_code=400, detail="wallet parameter is required")
    w = w.strip()
    if not w:
        raise HTTPException(status_code=400, detail="wallet parameter is required")
    if len(w) > 96:
        raise HTTPException(status_code=400, detail="wallet parameter too long")
    return w


@router.get("/unlocks")
async def list_unlocks(wallet: Optional[str] = Query(None, description="Solana wallet address")):
    """Return every unlock this wallet has earned, newest first.

    Response shape:
      {
        "wallet": "...",
        "unlocks": [
          { "entry_id": "...", "entry_tier": 1, "unlocked_at": "...",
            "tinkerpug_excerpt": "...", "unlock_prompt": "..." },
          ...
        ],
        "count": N
      }
    """
    w = _clean_wallet(wallet)
    unlocks = await archive.get_unlocks(w)
    return {
        "wallet": w,
        "unlocks": unlocks,
        "count": len(unlocks),
    }


@router.get("/rank")
async def get_rank(wallet: Optional[str] = Query(None, description="Solana wallet address")):
    """Return the current rank snapshot for this wallet.

    Response shape:
      {
        "wallet": "...",
        "rank": "seeker" | "archivist" | "keepers_circle" | null,
        "rank_title": "Seeker" | "Archivist" | "Keeper's Circle" | null,
        "unlocked_count": N,
        "total": 27,
        "tier_progress": {
          "tier_1": {"unlocked": X, "total": 9},
          "tier_2": {"unlocked": X, "total": 10},
          "tier_3": {"unlocked": X, "total": 8},
        }
      }
    """
    w = _clean_wallet(wallet)
    snapshot = await archive.get_rank_snapshot(w)
    return {"wallet": w, **snapshot}


@router.get("/entries")
async def list_entries(wallet: Optional[str] = Query(None, description="Solana wallet address (optional)")):
    """Return the full master entry list, annotated with unlock state for
    this wallet.

    If `wallet` is omitted the response still contains every entry in the
    correct display order — every entry marked `unlocked: false`. Useful
    for showing the Ledger before wallet-connect.
    """
    if wallet is not None:
        wallet = wallet.strip() or None
    entries = await archive.get_master_entries_for_wallet(wallet)
    return {
        "wallet": wallet,
        "entries": entries,
        "total": archive.TOTAL_ENTRIES,
    }


@router.get("/drops")
async def list_drops(
    wallet: Optional[str] = Query(None, description="Solana wallet address"),
    page: int = Query(1, ge=1, description="Page number, 1-indexed"),
    limit: int = Query(12, ge=1, le=48, description="Cards per page"),
):
    """Paginated daily-drop vault for a wallet, newest first.

    Response:
      {
        "wallet": "...",
        "page": 1,
        "limit": 12,
        "total": N,
        "has_more": bool,
        "drops": [
          { "day_number", "date_utc", "scene_title", "caption",
            "image_base64", "theme", "scene" },
          ...
        ]
      }
    """
    w = _clean_wallet(wallet)
    from utils.database import db as _db
    try:
        skip = (page - 1) * limit
        total = await _db.daily_drops.count_documents({"user_key": w})
        cursor = (
            _db.daily_drops
            .find({"user_key": w},
                  {"_id": 0, "user_key": 0})
            .sort("date_utc", -1)
            .skip(skip)
            .limit(limit)
        )
        drops = await cursor.to_list(length=limit)
    except Exception:
        drops = []
        total = 0
    return {
        "wallet": w,
        "page": page,
        "limit": limit,
        "total": total,
        "has_more": (page * limit) < total,
        "drops": drops,
    }


@router.get("/admin/stats", dependencies=[Depends(require_admin_jwt)])
async def admin_archive_stats():
    """Aggregate stats — unlock counts per entry, rank distribution."""
    return await archive.admin_stats()
