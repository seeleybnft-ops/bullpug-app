"""Bullpug Archive — lore achievement + rank progression system.

This module owns everything about the per-wallet lore ledger:

  • MASTER_ENTRIES — the canonical 27-entry list across three tiers
  • detect_unlock()  — lightweight LLM classifier: given an exchange,
                       returns the entry slug that was substantively
                       revealed (or None). Runs as an async background
                       task after the main Tinkerpug response is sent,
                       so it never adds latency to the visitor's chat.
  • record_unlock()  — idempotent write into `archive_unlocks` +
                       `archive_ranks`, handles the rank-up promotion.
  • compute_rank()   — pure function over an unlock list
  • Rank + entry queries used by both the /api/archive/* endpoints
    and the shareable-card generator.

Nothing here reaches out to the frontend. The frontend polls
`/api/archive/unlocks` after each chat response to pick up any newly
recorded unlocks (an unlock also lands on the response envelope when
the classifier finishes before the next request, but the endpoint is
the source of truth).

Two MongoDB collections back this system:

    archive_unlocks    — one document per (wallet, entry) unlock
    archive_ranks      — denormalised current-rank snapshot per wallet
                          (fast lookup for the Ledger panel header)

Indexes are declared in `server.py`'s startup hook.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from emergentintegrations.llm.chat import LlmChat, UserMessage

from utils.database import db

logger = logging.getLogger(__name__)

# ── Collections ─────────────────────────────────────────────────────────
UNLOCKS_COLLECTION = "archive_unlocks"
RANKS_COLLECTION = "archive_ranks"


# ── Master entry list ───────────────────────────────────────────────────
# 27 entries: 9 Tier 1, 10 Tier 2, 8 Tier 3.
# Order matters — the frontend Ledger renders in this order within each
# tier so the layout stays stable between locked and unlocked states.
#
# `unlock_trigger` is the semantic condition the classifier LLM uses to
# decide whether a given exchange substantively revealed this entry.
# Keep triggers short and unambiguous — the classifier reads them all
# every call, so terseness = accuracy.
MASTER_ENTRIES: List[Dict] = [
    # ── TIER 1 — SEEKER (9 entries incl. first-drop) ────────────────────
    {"slug": "cosmic-birth", "tier": 1, "name": "The Cosmic Birth",
     "locked_desc": "How Bullpug came to exist. The beginning of everything.",
     "unlock_trigger": "Bullpug's origin story discussed (the cosmic mix-up / bull-constellation / pug-nebula)"},
    {"slug": "cryptocanis", "tier": 1, "name": "CryptoCanis",
     "locked_desc": "The world Bullpug built from collective want.",
     "unlock_trigger": "CryptoCanis (the universe / world) described substantively"},
    {"slug": "newpug-city", "tier": 1, "name": "Newpug City",
     "locked_desc": "The city at the heart of CryptoCanis.",
     "unlock_trigger": "Newpug City described (districts / substrate / node pillars)"},
    {"slug": "pugchain", "tier": 1, "name": "The PugChain",
     "locked_desc": "The network that makes it all possible.",
     "unlock_trigger": "PugChain (the network / its function) explained"},
    {"slug": "bullpughans", "tier": 1, "name": "The Bullpughans",
     "locked_desc": "The people of CryptoCanis.",
     "unlock_trigger": "Bullpughans as a people described (culture, work, community)"},
    {"slug": "guardians", "tier": 1, "name": "The Guardians",
     "locked_desc": "The four who protect the chain.",
     "unlock_trigger": "The four Guardians introduced as a group (Bullpug, Ruffus, Luna, Chargebull) or the corps discussed"},
    {"slug": "festival-of-barks", "tier": 1, "name": "The Festival of Barks",
     "locked_desc": "The ritual of remembrance.",
     "unlock_trigger": "Festival of Barks explained (what it is, when, why)"},
    {"slug": "signal-in-noise", "tier": 1, "name": "The Signal in the Noise",
     "locked_desc": "Something is moving in the Between.",
     "unlock_trigger": "The Signal in the Noise (the anomaly in the Between) discussed"},
    {"slug": "first-drop", "tier": 1, "name": "Your First Drop",
     "locked_desc": "The Archive generates a new record every day. This is where yours begins.",
     "unlock_trigger": "EVENT-ONLY — fired by daily_drop.py when the user's first drop is generated. NEVER classify this from chat text."},

    # ── TIER 2 — ARCHIVIST (10 entries) ─────────────────────────────────
    {"slug": "signal-of-worthy", "tier": 2, "name": "The Signal of the Worthy",
     "locked_desc": "How Bullpug finds those who deserve to cross.",
     "unlock_trigger": "Signal of the Worthy mechanic explained (how Bullpug selects who crosses)"},
    {"slug": "ruffus-deep", "tier": 2, "name": "Ruffus and the Runes",
     "locked_desc": "What the runes actually mean.",
     "unlock_trigger": "Ruffus' Dip Wars backstory / rune interpretation explained at depth"},
    {"slug": "luna-price", "tier": 2, "name": "Luna's Price",
     "locked_desc": "What the seer pays for what she sees.",
     "unlock_trigger": "Luna's memory-trade / cost of foresight explained"},
    {"slug": "chargebull-years", "tier": 2, "name": "The Twelve Years",
     "locked_desc": "What Chargebull did before the Guardian corps.",
     "unlock_trigger": "Chargebull's twelve-year first-responder / pre-Guardian period told"},
    {"slug": "tinkerpug-patches", "tier": 2, "name": "The Forty-Seven Patches",
     "locked_desc": "How the Keeper first came to be noticed.",
     "unlock_trigger": "Tinkerpug's own origin — the forty-seven silent chain patches — told"},
    {"slug": "shadow-bears", "tier": 2, "name": "The Shadow Bears",
     "locked_desc": "Where they came from and what they became.",
     "unlock_trigger": "Shadow Bears origin discussed (what they were, what they are now)"},
    {"slug": "grand-convergence", "tier": 2, "name": "The Grand Convergence",
     "locked_desc": "What the scrolls say. What the scrolls don't say.",
     "unlock_trigger": "Grand Convergence discussed at depth (not just named)"},
    {"slug": "chain-surf", "tier": 2, "name": "Chain Surf",
     "locked_desc": "The sport of riding the chain itself.",
     "unlock_trigger": "Chain Surf explained (riding data-streams, surge reading)"},
    {"slug": "bark-ball", "tier": 2, "name": "Bark Ball",
     "locked_desc": "The youth sport of CryptoCanis.",
     "unlock_trigger": "Bark Ball explained (sonic-projectile courtyard sport)"},
    {"slug": "long-sniff", "tier": 2, "name": "The Long Sniff",
     "locked_desc": "Tinkerpug's accidental legacy.",
     "unlock_trigger": "The Long Sniff origin told (Tinkerpug's training exercise turned annual event)"},

    # ── TIER 3 — KEEPER'S CIRCLE (8 entries) ────────────────────────────
    {"slug": "grizzlor-origin", "tier": 3, "name": "Gideon's Fall",
     "locked_desc": "The full story of what was done to Grizzlor.",
     "unlock_trigger": "Grizzlor's Architect-targeted origin fully told (Gideon → Grizzlor transformation)"},
    {"slug": "architect-exists", "tier": 3, "name": "The Architect",
     "locked_desc": "Something operates in the Between. It has never been seen.",
     "unlock_trigger": "The Architect's existence acknowledged (the unseen operator in the Between)"},
    {"slug": "the-ledger", "tier": 3, "name": "The Ledger",
     "locked_desc": "Tinkerpug's private record. Not the public one.",
     "unlock_trigger": "The Ledger distinguished from the Genesis Vault (private vs public record)"},
    {"slug": "first-crossing", "tier": 3, "name": "Entry One",
     "locked_desc": "The oldest entry. The one without a name.",
     "unlock_trigger": "First Crossing / Entry One discussed at depth (oldest nameless entry)"},
    {"slug": "dormant-siblings", "tier": 3, "name": "The Dormant Siblings",
     "locked_desc": "Three others born from the same want. Not yet awake.",
     "unlock_trigger": "The three Dormant Siblings introduced (born of the same collective want)"},
    {"slug": "night-pugchain-held", "tier": 3, "name": "The Night the PugChain Held",
     "locked_desc": "The attack nobody talks about. The chain that didn't fall.",
     "unlock_trigger": "The Night the PugChain Held recounted (the attack that never made the public record)"},
    {"slug": "keepers-appointment", "tier": 3, "name": "The Keeper's Appointment",
     "locked_desc": "How Tinkerpug became the Keeper. The key. The conversation.",
     "unlock_trigger": "Tinkerpug's Keeper appointment story told (the key handover, the conversation)"},
    {"slug": "architect-s4", "tier": 3, "name": "The Mark in the Margin",
     "locked_desc": "Something predates the Guardians. Something left a mark.",
     "unlock_trigger": "S-4 signature / dark mark in the margin discussed (predates the Guardians)"},
]

# Fast lookup helpers
_BY_SLUG: Dict[str, Dict] = {e["slug"]: e for e in MASTER_ENTRIES}
_TIER1_SLUGS = {e["slug"] for e in MASTER_ENTRIES if e["tier"] == 1}
_TIER2_SLUGS = {e["slug"] for e in MASTER_ENTRIES if e["tier"] == 2}
_TIER3_SLUGS = {e["slug"] for e in MASTER_ENTRIES if e["tier"] == 3}

# Slugs the classifier is allowed to return. `first-drop` is EVENT-ONLY
# (fired from `daily_drop.py`) — we exclude it from the classifier's
# candidate set so a chat exchange can never accidentally unlock it.
_CLASSIFIER_SLUGS = [e["slug"] for e in MASTER_ENTRIES if e["slug"] != "first-drop"]


# ── Rank ────────────────────────────────────────────────────────────────
RANK_NONE = None
RANK_SEEKER = "seeker"
RANK_ARCHIVIST = "archivist"
RANK_KEEPERS_CIRCLE = "keepers_circle"

RANK_TITLES = {
    RANK_SEEKER: "Seeker",
    RANK_ARCHIVIST: "Archivist",
    RANK_KEEPERS_CIRCLE: "Keeper's Circle",
}

TOTAL_ENTRIES = len(MASTER_ENTRIES)  # 27
TOTAL_TIER1 = len(_TIER1_SLUGS)      # 9
TOTAL_TIER2 = len(_TIER2_SLUGS)      # 10
TOTAL_TIER3 = len(_TIER3_SLUGS)      # 8


def compute_rank(unlocked_slugs: set) -> Optional[str]:
    """Pure function — return the highest rank warranted by the unlock set.

    Rules (from spec §3.1):
      • Seeker          — all 9 Tier 1 entries
      • Archivist       — Seeker + all 10 Tier 2 entries
      • Keeper's Circle — Archivist + all 8 Tier 3 entries
    """
    has_all_t1 = _TIER1_SLUGS.issubset(unlocked_slugs)
    has_all_t2 = _TIER2_SLUGS.issubset(unlocked_slugs)
    has_all_t3 = _TIER3_SLUGS.issubset(unlocked_slugs)
    if has_all_t1 and has_all_t2 and has_all_t3:
        return RANK_KEEPERS_CIRCLE
    if has_all_t1 and has_all_t2:
        return RANK_ARCHIVIST
    if has_all_t1:
        return RANK_SEEKER
    return RANK_NONE


# ── Queries ─────────────────────────────────────────────────────────────
def _norm_wallet(wallet_address: Optional[str]) -> Optional[str]:
    """Normalise a wallet string. Empty → None (no persistence for
    anonymous visitors — no ledger without a wallet)."""
    if not wallet_address:
        return None
    w = wallet_address.strip()
    return w[:96] if w else None


async def get_unlocked_slugs(wallet_address: str) -> set:
    """Return the set of slugs this wallet has already unlocked."""
    w = _norm_wallet(wallet_address)
    if not w:
        return set()
    try:
        cursor = db[UNLOCKS_COLLECTION].find(
            {"wallet_address": w}, {"entry_id": 1, "_id": 0}
        )
        docs = await cursor.to_list(length=TOTAL_ENTRIES + 10)
        return {d["entry_id"] for d in docs if d.get("entry_id") in _BY_SLUG}
    except Exception as e:
        logger.warning("get_unlocked_slugs failed for %s: %s", w, e)
        return set()


async def get_unlocks(wallet_address: str) -> List[Dict]:
    """Return all unlock documents for a wallet, newest first."""
    w = _norm_wallet(wallet_address)
    if not w:
        return []
    try:
        cursor = (
            db[UNLOCKS_COLLECTION]
            .find({"wallet_address": w},
                  {"_id": 0, "wallet_address": 0, "image_base64": 0})
            .sort("unlocked_at", -1)
        )
        return await cursor.to_list(length=TOTAL_ENTRIES + 10)
    except Exception as e:
        logger.warning("get_unlocks failed for %s: %s", w, e)
        return []


async def get_rank_snapshot(wallet_address: str) -> Dict:
    """Return {rank, rank_title, unlocked_count, total} for the Ledger header."""
    slugs = await get_unlocked_slugs(wallet_address)
    rank = compute_rank(slugs)
    return {
        "rank": rank,
        "rank_title": RANK_TITLES.get(rank) if rank else None,
        "unlocked_count": len(slugs),
        "total": TOTAL_ENTRIES,
        "tier_progress": {
            "tier_1": {"unlocked": len(slugs & _TIER1_SLUGS), "total": TOTAL_TIER1},
            "tier_2": {"unlocked": len(slugs & _TIER2_SLUGS), "total": TOTAL_TIER2},
            "tier_3": {"unlocked": len(slugs & _TIER3_SLUGS), "total": TOTAL_TIER3},
        },
    }


async def get_master_entries_for_wallet(wallet_address: Optional[str]) -> List[Dict]:
    """Return the full master list annotated with per-wallet unlock state.

    Every entry gets `{unlocked: bool, unlocked_at, tinkerpug_excerpt}` merged
    in when this wallet has unlocked it. Order matches MASTER_ENTRIES (tier
    ascending, then original insertion order within a tier).
    """
    w = _norm_wallet(wallet_address)
    unlocks_by_slug: Dict[str, Dict] = {}
    if w:
        try:
            cursor = db[UNLOCKS_COLLECTION].find(
                {"wallet_address": w},
                {"_id": 0, "wallet_address": 0, "image_base64": 0},
            )
            for doc in await cursor.to_list(length=TOTAL_ENTRIES + 10):
                unlocks_by_slug[doc.get("entry_id")] = doc
        except Exception as e:
            logger.warning("get_master_entries_for_wallet failed for %s: %s", w, e)

    annotated: List[Dict] = []
    for entry in MASTER_ENTRIES:
        u = unlocks_by_slug.get(entry["slug"])
        annotated.append({
            "slug": entry["slug"],
            "tier": entry["tier"],
            "name": entry["name"],
            "locked_desc": entry["locked_desc"],
            "unlocked": bool(u),
            "unlocked_at": u.get("unlocked_at") if u else None,
            "tinkerpug_excerpt": u.get("tinkerpug_excerpt") if u else None,
            "unlock_prompt": u.get("unlock_prompt") if u else None,
        })
    return annotated


# ── Detection classifier ────────────────────────────────────────────────
_CLASSIFIER_SYSTEM = (
    "You are an unlock detector for the Bullpughan Archive achievement "
    "system. Given a conversation exchange, determine whether Tinkerpug "
    "SUBSTANTIVELY revealed one of the tracked lore entries. "
    "'Substantively' means the core content of the entry was explained — "
    "more than a passing mention or a single sentence.\n\n"
    "Return ONLY a JSON object of the form:\n"
    '  {"unlocked": "entry-slug"}  ← if one entry was substantively revealed\n'
    '  {"unlocked": null}          ← otherwise\n\n'
    "Never invent slugs. Choose from the candidate list only. If multiple "
    "entries could apply, choose the one Tinkerpug's response focused on "
    "most. If nothing was substantively revealed, return null.\n\n"
    "CANDIDATE ENTRIES (slug — trigger):\n"
    + "\n".join(f"  {e['slug']} — {e['unlock_trigger']}" for e in MASTER_ENTRIES if e["slug"] in _CLASSIFIER_SLUGS)
)

# Robust JSON extractor — the model sometimes wraps in ``` fences or adds
# trailing prose despite the "return ONLY" instruction. Never blow up on
# a malformed response; treat it as "no unlock".
_JSON_OBJ = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _parse_classifier_output(raw: str) -> Optional[str]:
    if not raw:
        return None
    text = raw.strip()
    # Strip ``` fences if present
    if text.startswith("```"):
        text = text.strip("`")
        # Remove optional "json" language hint
        text = re.sub(r"^json\s*", "", text, flags=re.IGNORECASE).strip()
    # Try direct parse first; fall back to first {} object in the string
    candidates: List[str] = [text]
    for m in _JSON_OBJ.finditer(text):
        candidates.append(m.group(0))
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        slug = obj.get("unlocked")
        if slug is None:
            return None
        if isinstance(slug, str) and slug in _BY_SLUG and slug != "first-drop":
            return slug
    return None


async def classify_exchange(
    api_key: str,
    session_id: str,
    user_message: str,
    tinkerpug_response: str,
    already_unlocked: Optional[set] = None,
) -> Optional[str]:
    """LLM-classify a single (user_message, tinkerpug_response) exchange.

    Returns the slug of a newly unlockable entry or None. `already_unlocked`
    is used to short-circuit: if every classifier-eligible slug is already
    unlocked for this wallet, we skip the call entirely.
    """
    if not api_key or not user_message or not tinkerpug_response:
        return None
    already_unlocked = already_unlocked or set()
    remaining = set(_CLASSIFIER_SLUGS) - already_unlocked
    if not remaining:
        return None
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=_CLASSIFIER_SYSTEM,
        ).with_model("openai", "gpt-4o")
        payload = (
            f"USER MESSAGE:\n{(user_message or '')[:800]}\n\n"
            f"TINKERPUG RESPONSE:\n{(tinkerpug_response or '')[-1500:]}\n\n"
            "Return ONLY the JSON."
        )
        raw = await chat.send_message(UserMessage(text=payload))
        slug = _parse_classifier_output(raw or "")
        if slug and slug in remaining:
            return slug
        # Log at debug when classifier picks an already-unlocked slug so
        # we can tune the trigger phrasing later.
        if slug and slug not in remaining:
            logger.debug("classifier picked already-unlocked slug %s", slug)
        return None
    except Exception as e:
        logger.warning("Archive classifier failed: %s", e)
        return None


# ── Recording + rank update ─────────────────────────────────────────────
async def record_unlock(
    wallet_address: str,
    entry_id: str,
    unlock_prompt: str = "",
    tinkerpug_excerpt: str = "",
    image_base64: Optional[str] = None,
    image_mime: Optional[str] = None,
) -> Optional[Dict]:
    """Idempotently record an unlock and refresh the rank snapshot.

    Returns the unlock envelope in the shape the chat API sends back to
    the frontend, or None if:
      • wallet is empty
      • entry_id is unknown
      • the entry was already unlocked for this wallet
    """
    w = _norm_wallet(wallet_address)
    if not w or entry_id not in _BY_SLUG:
        return None

    entry = _BY_SLUG[entry_id]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "wallet_address": w,
        "entry_id": entry_id,
        "entry_tier": entry["tier"],
        "unlocked_at": now,
        "unlock_prompt": (unlock_prompt or "")[:400],
        "tinkerpug_excerpt": (tinkerpug_excerpt or "")[:400],
        "image_base64": image_base64 or None,
        "image_mime": image_mime or None,
        "image_generated_at": now if image_base64 else None,
    }
    try:
        # Rely on the unique compound index (wallet_address, entry_id).
        # A duplicate write returns a DuplicateKeyError → we treat that as
        # "already unlocked, nothing to do".
        await db[UNLOCKS_COLLECTION].insert_one(doc)
    except Exception as e:
        # Idempotency path — an existing unlock is not an error.
        if "duplicate" in str(e).lower() or "E11000" in str(e):
            return None
        logger.warning("record_unlock insert failed for %s/%s: %s", w, entry_id, e)
        return None

    # Refresh the rank snapshot. Compute BEFORE looking up the previous rank
    # so we can detect rank-up transitions.
    unlocked_slugs = await get_unlocked_slugs(w)
    new_rank = compute_rank(unlocked_slugs)
    prev_rank = await _get_stored_rank(w)
    is_rank_up = (prev_rank != new_rank) and new_rank is not None

    try:
        await db[RANKS_COLLECTION].update_one(
            {"wallet_address": w},
            {"$set": {
                "wallet_address": w,
                "rank": new_rank,
                "rank_title": RANK_TITLES.get(new_rank) if new_rank else None,
                "unlocked_count": len(unlocked_slugs),
                "updated_at": now,
            }},
            upsert=True,
        )
    except Exception as e:
        logger.warning("record_unlock rank upsert failed for %s: %s", w, e)

    logger.info(
        "Archive unlock: wallet=%s entry=%s tier=%s rank=%s rank_up=%s",
        w[:12] + "…", entry_id, entry["tier"], new_rank, is_rank_up,
    )

    return {
        "entry_id": entry_id,
        "entry_name": entry["name"],
        "entry_tier": entry["tier"],
        "is_rank_up": is_rank_up,
        "new_rank": new_rank if is_rank_up else None,
        "new_rank_title": RANK_TITLES.get(new_rank) if (is_rank_up and new_rank) else None,
        "unlocked_at": now,
    }


async def _get_stored_rank(wallet_address: str) -> Optional[str]:
    """Read the last-persisted rank for this wallet (may be None)."""
    try:
        doc = await db[RANKS_COLLECTION].find_one(
            {"wallet_address": wallet_address}, {"rank": 1, "_id": 0}
        )
        return doc.get("rank") if doc else None
    except Exception:
        return None


# ── Fire-and-forget wrapper for the chat pipeline ───────────────────────
async def detect_and_record_unlock(
    wallet_address: Optional[str],
    user_message: str,
    tinkerpug_response: str,
    api_key: str,
    session_id: str,
) -> Optional[Dict]:
    """Full pipeline: classify → record if novel. Safe to `asyncio.create_task`
    from the chat endpoint — swallows all exceptions and returns None on any
    failure. Returns the unlock envelope on success (also persisted to DB so
    the frontend can poll for it independently)."""
    w = _norm_wallet(wallet_address)
    if not w:
        return None  # no wallet → no ledger
    if not user_message or not tinkerpug_response:
        return None
    try:
        already = await get_unlocked_slugs(w)
        slug = await classify_exchange(
            api_key=api_key,
            session_id=session_id,
            user_message=user_message,
            tinkerpug_response=tinkerpug_response,
            already_unlocked=already,
        )
        if not slug:
            return None
        # Trim excerpt from the assistant's own response (first ~200 chars
        # is what the Ledger card displays).
        excerpt = (tinkerpug_response or "").strip()
        # Strip markdown bold/italic markers for a cleaner card excerpt.
        excerpt = re.sub(r"[*_`]+", "", excerpt)[:220]
        return await record_unlock(
            wallet_address=w,
            entry_id=slug,
            unlock_prompt=user_message,
            tinkerpug_excerpt=excerpt,
        )
    except Exception as e:
        logger.warning("detect_and_record_unlock failed: %s", e)
        return None


# ── Admin queries ───────────────────────────────────────────────────────
async def admin_stats() -> Dict:
    """Aggregate stats for the admin panel — unlock counts per entry and
    the overall rank distribution."""
    try:
        # Per-entry counts
        pipeline = [
            {"$group": {"_id": "$entry_id", "count": {"$sum": 1}}},
        ]
        per_entry_docs = await db[UNLOCKS_COLLECTION].aggregate(pipeline).to_list(length=100)
        per_entry = {d["_id"]: d["count"] for d in per_entry_docs if d.get("_id") in _BY_SLUG}
        entries_out = []
        for e in MASTER_ENTRIES:
            entries_out.append({
                "slug": e["slug"],
                "name": e["name"],
                "tier": e["tier"],
                "unlock_count": per_entry.get(e["slug"], 0),
            })

        # Rank distribution — count wallets at each rank tier
        rank_docs = await db[RANKS_COLLECTION].find(
            {}, {"rank": 1, "_id": 0}
        ).to_list(length=10000)
        rank_dist: Dict[str, int] = {"none": 0, RANK_SEEKER: 0,
                                     RANK_ARCHIVIST: 0, RANK_KEEPERS_CIRCLE: 0}
        for r in rank_docs:
            key = r.get("rank") or "none"
            rank_dist[key] = rank_dist.get(key, 0) + 1

        return {
            "total_entries": TOTAL_ENTRIES,
            "total_wallets": len(rank_docs),
            "entries": entries_out,
            "rank_distribution": rank_dist,
        }
    except Exception as e:
        logger.warning("admin_stats failed: %s", e)
        return {
            "total_entries": TOTAL_ENTRIES,
            "total_wallets": 0,
            "entries": [],
            "rank_distribution": {},
        }
