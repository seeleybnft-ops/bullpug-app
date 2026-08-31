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
from pydantic import BaseModel

from services import archive_achievements as archive
from services import archive_share_card
from utils.admin_auth import require_admin_jwt

router = APIRouter(prefix="/archive", tags=["archive"])


class ShareRequest(BaseModel):
    wallet: str


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
        "total": 61,
        "tier_progress": {
          "tier_1": {"unlocked": X, "total": 16},
          "tier_2": {"unlocked": X, "total": 25},
          "tier_3": {"unlocked": X, "total": 20},
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


# ── Visual Canon admin endpoints ─────────────────────────────────────
@router.get("/admin/canon", dependencies=[Depends(require_admin_jwt)])
async def admin_list_canon(
    status: Optional[str] = Query(None, description="'canon' | 'pending' | 'retired' | None (all)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Admin — paginated Visual Canon list with status filter.

    Delegates to `visual_canon.get_all_canon` / `get_pending` for the
    two most common cases and falls back to a direct query for the
    'retired' + 'all' cases.
    """
    from services import visual_canon
    from utils.database import db as _db

    if status == "pending":
        items = await visual_canon.get_pending(skip=skip, limit=limit)
    elif status == "canon":
        items = await visual_canon.get_all_canon(skip=skip, limit=limit)
    else:
        # Retired or "all" — hand-rolled query
        q: dict = {}
        if status == "retired":
            q["status"] = "retired"
        # ordering: canon+admin_override newest first, then pending by
        # request_count, retired last. Simplest impl: sort by
        # promoted_at DESC nulls last, break by created_at.
        cursor = _db[visual_canon.CANON_COLLECTION].find(
            q, visual_canon._LIST_PROJECTION
        ).sort([("promoted_at", -1), ("created_at", -1)]).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)

    total = await _db[visual_canon.CANON_COLLECTION].count_documents(
        {"status": status} if status else {}
    )
    # Defensive: projection already excludes _id, but strip anyway so
    # the response is provably free of ObjectIds.
    safe_items = [{k: v for k, v in it.items() if k != "_id"} for it in items]
    return {"total": total, "skip": skip, "limit": limit, "items": safe_items}


class CanonPromoteRequest(BaseModel):
    subject_tag: str
    image_base64: Optional[str] = None
    image_mime: Optional[str] = None


@router.post("/admin/canon/promote", dependencies=[Depends(require_admin_jwt)])
async def admin_canon_promote(payload: CanonPromoteRequest):
    """Promote pending → canon, or replace the image via admin_override."""
    from services import visual_canon
    doc = await visual_canon.admin_override(
        subject_tag=payload.subject_tag,
        image_base64=payload.image_base64,
        image_mime=payload.image_mime,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="subject_tag not found or image too large")
    return doc


class CanonRetireRequest(BaseModel):
    subject_tag: str


@router.post("/admin/canon/retire", dependencies=[Depends(require_admin_jwt)])
async def admin_canon_retire(payload: CanonRetireRequest):
    """Retire a canon entry (status → retired, kept in DB)."""
    from services import visual_canon
    doc = await visual_canon.retire(payload.subject_tag)
    if not doc:
        raise HTTPException(status_code=404, detail="subject_tag not found")
    return doc


@router.get("/admin/canon/image/{subject_tag}", dependencies=[Depends(require_admin_jwt)])
async def admin_canon_image(subject_tag: str):
    """Return the full-resolution image bytes for one canon entry."""
    from services import visual_canon
    from utils.database import db as _db
    doc = await _db[visual_canon.CANON_COLLECTION].find_one(
        {"subject_tag": subject_tag},
        {"_id": 0, "image_base64": 1, "image_mime": 1},
    )
    if not doc or not doc.get("image_base64"):
        raise HTTPException(status_code=404, detail="not found")
    return {
        "subject_tag": subject_tag,
        "image_base64": doc["image_base64"],
        "image_mime": doc.get("image_mime", "image/png"),
    }


@router.get("/entry-image/{slug}")
async def get_entry_image(slug: str):
    """Return the Visual-Canon-stored image for a single lore entry.

    Any status (pending, canon, admin_override) counts — visitors see
    the art as soon as it's been generated, not only after promotion.
    Missing image → 404 so the LoreCard can quietly render without a
    thumbnail and retry on next load.
    """
    if not slug:
        raise HTTPException(status_code=404, detail="not found")
    doc = await archive.get_entry_image(slug)
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "slug": slug,
        "image_base64": doc.get("image_base64"),
        "image_mime": doc.get("image_mime") or "image/png",
        "status": doc.get("status"),
    }


@router.post("/entry-image/{slug}/generate")
async def regen_entry_image(slug: str):
    """Force (re-)generation of an entry's image. Useful when a first
    generation was rejected or the visitor wants a re-roll before it's
    promoted. Blocks until the generation finishes — kept behind an
    explicit user click, not a passive load."""
    if not slug:
        raise HTTPException(status_code=404, detail="not found")
    doc = await archive.ensure_entry_image(slug)
    if not doc:
        raise HTTPException(status_code=502, detail="generation failed")
    return {"slug": slug, "status": doc.get("status", "pending")}


@router.get("/record")
async def get_record(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    """Public leaderboard — 'The Record'.

    Wallets ranked by unlock count (desc). Privacy-safe: the raw wallet
    address is returned so the frontend can shorten it, and no other
    identifying info is exposed. See `archive.get_record_leaderboard`.
    """
    return await archive.get_record_leaderboard(page=page, limit=limit)


@router.get("/announcements")
async def get_announcements(limit: int = Query(10, ge=1, le=25)):
    """Public feed — last N Keeper's Circle rank-up announcements.

    Newest first. Test wallets are filtered server-side so QA rank-ups
    never surface in the live UI.
    """
    items = await archive.get_keeper_announcements(limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/share")
async def generate_share(payload: ShareRequest):
    """Generate the 1200×630 shareable Archive card PNG.

    Returns `{ image_base64, mime, wallet, rank, rank_title, unlocked_count }`.
    Base64 has no data-URL prefix — the client prepends it when rendering.
    """
    w = _clean_wallet(payload.wallet)
    b64 = await archive_share_card.generate_share_card(w)
    if not b64:
        raise HTTPException(status_code=500, detail="failed to render share card")
    snap = await archive.get_rank_snapshot(w)
    return {
        "wallet": w,
        "image_base64": b64,
        "mime": "image/png",
        "rank": snap.get("rank"),
        "rank_title": snap.get("rank_title"),
        "unlocked_count": snap.get("unlocked_count"),
        "total": snap.get("total"),
        # Grand total including the Special companion entry — the
        # share text and card should reflect the full Archive surface
        # so returning users understand the record is bigger than the
        # rank-gated tiers alone.
        "grand_total": archive.GRAND_TOTAL_ENTRIES,
    }
