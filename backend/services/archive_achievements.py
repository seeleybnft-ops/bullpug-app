"""Bullpug Archive — lore achievement + rank progression system.

This module owns everything about the per-wallet lore ledger:

  • MASTER_ENTRIES — the canonical 61-entry list across three tiers
                     (16 Tier 1, 25 Tier 2, 20 Tier 3)
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

import asyncio
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
# 61 entries: 16 Tier 1 (incl. first-drop), 25 Tier 2, 20 Tier 3.
# Order matters — the frontend Ledger renders in this order within each
# tier so the layout stays stable between locked and unlocked states.
#
# `unlock_trigger` is the semantic condition the classifier LLM uses to
# decide whether a given exchange substantively revealed this entry.
# Keep triggers short and unambiguous — the classifier reads them all
# every call, so terseness = accuracy.
MASTER_ENTRIES: List[Dict] = [
    # ── TIER 1 — SEEKER (16 entries incl. first-drop) ───────────────────
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
    # New Tier 1 additions
    {"slug": "between-nature", "tier": 1, "name": "The Nature of the Between",
     "locked_desc": "The territory that exists between minds. How it works and what it holds.",
     "unlock_trigger": "The Between explained substantively (what it is, how minds meet in it, what it holds)"},
    {"slug": "genesis-vault", "tier": 1, "name": "The Genesis Vault",
     "locked_desc": "Below the city. Below the substrate. One key.",
     "unlock_trigger": "Genesis Vault described (its location, what it holds, the single key)"},
    {"slug": "snout-scanner", "tier": 1, "name": "The Snout Scanner",
     "locked_desc": "The tool that detects what cannot be hidden.",
     "unlock_trigger": "Snout Scanner mechanics explained (how it detects, what it catches)"},
    {"slug": "bullpug-personality", "tier": 1, "name": "The Guardian's Nature",
     "locked_desc": "What Bullpug is actually like. Not the legend. The being.",
     "unlock_trigger": "Bullpug's personality and nature discussed (the being, not the legend)"},
    {"slug": "daily-life", "tier": 1, "name": "Daily Life in CryptoCanis",
     "locked_desc": "What an ordinary day actually looks like.",
     "unlock_trigger": "Bullpughan daily life described (morning routines, districts, streetfood, sports)"},
    {"slug": "moon-cheese", "tier": 1, "name": "Moon Cheese",
     "locked_desc": "The favourite snack of a cosmic guardian. Yes, really.",
     "unlock_trigger": "Moon cheese discussed with context (why Bullpug likes it, where it comes from)"},
    {"slug": "social-contract", "tier": 1, "name": "The Social Contract",
     "locked_desc": "Unwritten. Universally understood. Self-enforcing.",
     "unlock_trigger": "The Bullpughan social contract explained (what you build is yours while you build it, belongs to everyone when done)"},

    # ── TIER 2 — ARCHIVIST (25 entries) ─────────────────────────────────
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
    # New Tier 2 additions
    {"slug": "enlightenment-nebula", "tier": 2, "name": "The Enlightenment Nebula",
     "locked_desc": "Where memes are born. Where Bullpug found his purpose.",
     "unlock_trigger": "Enlightenment Nebula described with the three illusions"},
    {"slug": "three-illusions", "tier": 2, "name": "The Three Illusions",
     "locked_desc": "What the Nebula showed him. What he chose.",
     "unlock_trigger": "All three illusions recounted (protection-of-self, heroism-alone, the open question)"},
    {"slug": "elder-moons", "tier": 2, "name": "The Elder Moons",
     "locked_desc": "Ancient. Slow. They gave him one phrase.",
     "unlock_trigger": "Elder Moons and the phrase discussed ('Believe in the moon, but build the rocket together')"},
    # NOTE: This T2 entry uses slug `ledger-private` — the spec proposed
    # `the-ledger` here but that slug is already taken by the existing
    # T3 entry below (kept for migration safety of existing user
    # unlocks + visual_canon rows).
    {"slug": "ledger-private", "tier": 2, "name": "The Ledger",
     "locked_desc": "Tinkerpug's private record. Not the public one. The real one.",
     "unlock_trigger": "The Ledger distinguished from Genesis Vault in depth (private record vs public vault)"},
    {"slug": "ruffus-consortium", "tier": 2, "name": "The Consortium",
     "locked_desc": "Seventeen identities. Seventeen runes. All gone.",
     "unlock_trigger": "The Consortium operation recounted in detail (seventeen identities, seventeen runes)"},
    {"slug": "margin-edge", "tier": 2, "name": "Margin's Edge",
     "locked_desc": "Where Ruffus came from. What happened to it.",
     "unlock_trigger": "Margin's Edge and the Great Dip Wars detailed (Ruffus' origin district)"},
    {"slug": "luna-coat", "tier": 2, "name": "Luna's Coat",
     "locked_desc": "Each light is a future she has already seen.",
     "unlock_trigger": "Luna's coat and what each light represents explained"},
    {"slug": "luna-convergence", "tier": 2, "name": "What Luna Saw",
     "locked_desc": "She has not told anyone. She would not say whether it was bad.",
     "unlock_trigger": "Luna's Convergence vision discussed (what she saw remains sealed)"},
    {"slug": "chargebull-trial", "tier": 2, "name": "The Trial of Temptation",
     "locked_desc": "What the illusion showed him. What it cost him to walk through it.",
     "unlock_trigger": "Chargebull's Trial of Temptation recounted"},
    {"slug": "tinkerpug-parents", "tier": 2, "name": "The Substrate Layer",
     "locked_desc": "Where he grew up. What they built. What was done to it.",
     "unlock_trigger": "Tinkerpug's parents' workshop and its liquidation discussed"},
    {"slug": "festival-deep", "tier": 2, "name": "The Festival's Meaning",
     "locked_desc": "Not just a celebration. A radical act of not forgetting.",
     "unlock_trigger": "The Festival of Barks' deeper significance explained (radical act of not forgetting)"},
    {"slug": "pugchain-architecture", "tier": 2, "name": "How the PugChain Works",
     "locked_desc": "Owned by everyone. Controlled by none. Corruption cannot hide inside it.",
     "unlock_trigger": "PugChain architecture explained in depth (ownership, verification, why corruption can't hide)"},
    {"slug": "crossing-mechanics", "tier": 2, "name": "How a Crossing Works",
     "locked_desc": "You don't find Bullpug. He finds you. What that actually means.",
     "unlock_trigger": "The crossing mechanic explained in depth (Bullpug finds the crosser, not the other way round)"},
    {"slug": "bark-ball-rivalries", "tier": 2, "name": "The District Rivalries",
     "locked_desc": "Named after feats. Taken more seriously than most things.",
     "unlock_trigger": "Bark Ball district rivalries and team naming discussed"},
    {"slug": "street-art", "tier": 2, "name": "The Canvas",
     "locked_desc": "The city's surfaces belong to everyone. The oldest pieces are landmarks.",
     "unlock_trigger": "Street art culture and its protection explained (oldest pieces treated as landmarks)"},

    # ── TIER 3 — KEEPER'S CIRCLE (20 entries) ───────────────────────────
    {"slug": "grizzlor-origin", "tier": 3, "name": "Gideon's Fall",
     "locked_desc": "The full story of what was done to Grizzlor.",
     "unlock_trigger": "Grizzlor's Architect-targeted origin fully told (Gideon → Grizzlor transformation)"},
    {"slug": "architect-exists", "tier": 3, "name": "The Architect",
     "locked_desc": "Something operates in the Between. It has never been seen.",
     "unlock_trigger": "The Architect's existence acknowledged (the unseen operator in the Between)"},
    {"slug": "the-ledger", "tier": 3, "name": "The Ledger (Full)",
     "locked_desc": "Tinkerpug's private record. Not the public one.",
     "unlock_trigger": "The Ledger distinguished from the Genesis Vault (private vs public record, full context)"},
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
    # New Tier 3 additions
    {"slug": "gideon-equilibrium", "tier": 3, "name": "The Original Alliance",
     "locked_desc": "Before the betrayal. What Bullpug and Gideon built together.",
     "unlock_trigger": "Bullpug-Gideon equilibrium period recounted (before the Architect's engineering)"},
    {"slug": "architect-method", "tier": 3, "name": "How It Works",
     "locked_desc": "It doesn't rug. It edits. Information curated to remove every recovery.",
     "unlock_trigger": "The Architect's method explained in full (data curation, selection-as-seam, withdrawal)"},
    {"slug": "shadow-bear-ops", "tier": 3, "name": "The Shadow Bear Campaign",
     "locked_desc": "What they actually did. How long it ran. What the Architect got from it.",
     "unlock_trigger": "Shadow Bear campaign recounted as Architect distraction"},
    {"slug": "s1-signature", "tier": 3, "name": "S-1: The Lending Collapse",
     "locked_desc": "Every disclosure technically true. Every rebuild invisible to its victims.",
     "unlock_trigger": "S-1 Architect signature recounted in detail (the lending collapse, true disclosures, invisible rebuild)"},
    {"slug": "s2-signature", "tier": 3, "name": "S-2: The Scheduled Emotion",
     "locked_desc": "Someone had scheduled an emotion. The sentiment was real. The sequencing was not.",
     "unlock_trigger": "S-2 recounted in detail (the scheduled emotion, real sentiment, engineered sequencing)"},
    {"slug": "s3-signature", "tier": 3, "name": "S-3: The Quiet One",
     "locked_desc": "No attack at all. A settlement that simply stopped believing.",
     "unlock_trigger": "S-3 recounted in full (the settlement that simply stopped believing)"},
    {"slug": "owl-oracles", "tier": 3, "name": "The Owl of Oracles",
     "locked_desc": "Born of the want for wisdom. The oldest sibling. Still listening.",
     "unlock_trigger": "Owl of Oracles described in depth (oldest dormant sibling, born of want for wisdom)"},
    {"slug": "fox-forks", "tier": 3, "name": "The Fox of Forks",
     "locked_desc": "Born of the want for adaptability. The most misunderstood sibling.",
     "unlock_trigger": "Fox of Forks described in depth (dormant sibling, want for adaptability)"},
    {"slug": "cat-moved-once", "tier": 3, "name": "The Cat Moved Once",
     "locked_desc": "It has never done this before. It has never done it since.",
     "unlock_trigger": "The Cat of Catalysts' single intervention recounted"},
    {"slug": "ledger-847", "tier": 3, "name": "The Night Itself",
     "locked_desc": "The lattice attack. The most elegant thing Tinkerpug has ever hated.",
     "unlock_trigger": "The Night the PugChain Held recounted from inside the substrate layer (Ledger 0847 full narrative)"},
    {"slug": "first-block", "tier": 3, "name": "The First Block",
     "locked_desc": "The single building that appeared. The first node that anchored beneath it.",
     "unlock_trigger": "The First Crossing aftermath and first structure discussed (the single building, the first anchoring node)"},
    {"slug": "tinkerpug-piece", "tier": 3, "name": "The Unmarked Piece",
     "locked_desc": "He has never pointed it out. It is still there.",
     "unlock_trigger": "Tinkerpug's substrate layer street art piece discussed (sublevel nine, junction 7-C, the consensus-failure diagram)"},

    # ── SPECIAL — companion-linked (unlockable only via /companion) ─────
    # Tier is the string "special" so the classifier never targets it
    # and rank progression never gates on it. Rendered in its own
    # section below Tier 3 in the ledger UI (gold paw print).
    {"slug": "companions-secret", "tier": "special", "name": "The Companion's Secret",
     "locked_desc": (
         "Some records can only be found in the physical world. "
         "This one requires a companion."
     ),
     "unlock_trigger": (
         "COMPANION-ONLY — fired by the /companion?key=… claim flow when a "
         "wallet redeems a Bullpug plushie token. NEVER classify from chat text."
     )},
]

# Entry content shown inside the Ledger card once unlocked (long-form).
COMPANIONS_SECRET_ENTRY_TEXT = (
    "keeper's log — filed under: things the chain knows that most people don't.\n\n"
    "Bullpug did not begin in the Between. He began in the physical world — in "
    "the specific frustration of millions of people who had been taken from and "
    "refused to stop believing anyway. The Between is where that want cohered. "
    "But the want was always physical first.\n\n"
    "This is not a distinction most Bullpughans think about. The city is digital. "
    "The chain is digital. The Archive is digital. It is easy to assume the "
    "physical world is just where you sit while you access these things.\n\n"
    "But the child who carries a companion to bed is doing something the Between "
    "cannot do. She is believing in something with her hands. With the specific "
    "physical conviction of holding something and knowing it is real. That is the "
    "oldest signal the Between has ever responded to. That is how Bullpug was born.\n\n"
    "I keep this entry in The Ledger because I think it is the most important "
    "thing in here that nobody asks about. Everyone wants to know about the "
    "Architect. Everyone wants to know what Luna saw. Nobody asks about the "
    "relationship between a child's favourite toy and a cosmic guardian.\n\n"
    "They should.\n\n"
    "keeper's note: if you are reading this, you found the physical thing first. "
    "That matters. The chain noticed."
)

# Streamed celebration message from Tinkerpug on claim.
COMPANIONS_SECRET_CELEBRATION_TEXT = (
    "keeper's log — unexpected signal. Not from the chain. From the physical world.\n\n"
    "You found a companion. That's not nothing — most people who come to the "
    "Archive find it through a screen. You found it through something you can "
    "hold.\n\n"
    "There's an entry for that. Not many have it.\n\n"
    "keeper's note: take care of the companion. It knows where the Archive is."
)

# Fast lookup helpers
_BY_SLUG: Dict[str, Dict] = {e["slug"]: e for e in MASTER_ENTRIES}
_TIER1_SLUGS = {e["slug"] for e in MASTER_ENTRIES if e["tier"] == 1}
_TIER2_SLUGS = {e["slug"] for e in MASTER_ENTRIES if e["tier"] == 2}
_TIER3_SLUGS = {e["slug"] for e in MASTER_ENTRIES if e["tier"] == 3}
_SPECIAL_SLUGS = {e["slug"] for e in MASTER_ENTRIES if e["tier"] == "special"}

# Slugs the classifier is allowed to return. Event-only entries are
# excluded so a chat exchange can never accidentally unlock them:
#   • `first-drop`         — fired by daily_drop.py
#   • `companions-secret`  — fired by the /companion claim flow
_EVENT_ONLY_SLUGS = {"first-drop"} | _SPECIAL_SLUGS
_CLASSIFIER_SLUGS = [
    e["slug"] for e in MASTER_ENTRIES if e["slug"] not in _EVENT_ONLY_SLUGS
]


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

TOTAL_ENTRIES = len(MASTER_ENTRIES) - len(_SPECIAL_SLUGS)  # 61 (excludes special)
TOTAL_TIER1 = len(_TIER1_SLUGS)      # 16 (incl. first-drop)
TOTAL_TIER2 = len(_TIER2_SLUGS)      # 25
TOTAL_TIER3 = len(_TIER3_SLUGS)      # 20
TOTAL_SPECIAL = len(_SPECIAL_SLUGS)  # 1 (companions-secret)
# The grand total exposed on user-facing share surfaces — includes the
# special companion entry so returning users see "X of 62" once the
# companion path exists in the Ledger. Never hardcode this number
# anywhere — always read from MASTER_ENTRIES via this constant.
GRAND_TOTAL_ENTRIES = len(MASTER_ENTRIES)  # 62 (regular + special)


def compute_rank(unlocked_slugs: set) -> Optional[str]:
    """Pure function — return the highest rank warranted by the unlock set.

    Rules (per Fix 6 spec):
      • Seeker          — all 16 Tier 1 entries
      • Archivist       — Seeker + all 25 Tier 2 entries
      • Keeper's Circle — Archivist + all 20 Tier 3 entries
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
    # `unlocked_count` and `total` count regular-tier progress only —
    # the special companion entry is a separate rail so it never
    # confuses the "n of N discovered" line in the header.
    regular_slugs = slugs - _SPECIAL_SLUGS
    return {
        "rank": rank,
        "rank_title": RANK_TITLES.get(rank) if rank else None,
        "unlocked_count": len(regular_slugs),
        "total": TOTAL_ENTRIES,
        "tier_progress": {
            "tier_1": {"unlocked": len(slugs & _TIER1_SLUGS), "total": TOTAL_TIER1},
            "tier_2": {"unlocked": len(slugs & _TIER2_SLUGS), "total": TOTAL_TIER2},
            "tier_3": {"unlocked": len(slugs & _TIER3_SLUGS), "total": TOTAL_TIER3},
            "special": {"unlocked": len(slugs & _SPECIAL_SLUGS), "total": TOTAL_SPECIAL},
        },
    }


async def get_master_entries_for_wallet(wallet_address: Optional[str]) -> List[Dict]:
    """Return the full master list annotated with per-wallet unlock state.

    Every entry gets `{unlocked: bool, unlocked_at, tinkerpug_excerpt, has_image}`
    merged in when this wallet has unlocked it. `has_image` is true when the
    Visual Canon Ledger has ANY document for the entry's slug (pending, canon,
    or admin_override) — the lore card will fetch it lazily via
    `/api/archive/entry-image/{slug}`. Order matches MASTER_ENTRIES.
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

    # Query visual_canon once for every slug that has any stored image —
    # a single roundtrip beats one lookup per card. Never treat this as
    # required; if the collection query fails we just render without
    # thumbnails.
    image_slugs: set = set()
    try:
        canon_cursor = db["visual_canon"].find(
            {"subject_tag": {"$in": [e["slug"] for e in MASTER_ENTRIES]},
             "image_base64": {"$exists": True, "$ne": None}},
            {"subject_tag": 1, "_id": 0},
        )
        for doc in await canon_cursor.to_list(length=TOTAL_ENTRIES + 10):
            image_slugs.add(doc.get("subject_tag"))
    except Exception as e:
        logger.warning("has_image lookup failed: %s", e)

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
            "has_image": entry["slug"] in image_slugs,
        })
    return annotated


# ── Detection classifier ────────────────────────────────────────────────
# Strict prompt per spec. The classifier defaults to null; only clear,
# substantive, primary-subject explanations unlock an entry.
_CLASSIFIER_SYSTEM = (
    "You are an unlock detector for the Bullpughan Archive achievement system.\n"
    "You are STRICT. Most exchanges should return {\"unlocked\": null}.\n\n"
    "Rules:\n"
    "- Tier 1 unlocks: the entry was the PRIMARY subject and Tinkerpug gave a "
    "substantive explanation (more than 2 sentences of actual content about it)\n"
    "- Tier 2 unlocks: the entry was the PRIMARY subject AND Tinkerpug provided "
    "specific named details (character names, specific events, specific mechanics) "
    "— a general overview is NOT enough\n"
    "- Tier 3 unlocks: the entry was the PRIMARY subject AND the core narrative "
    "of the entry was told in full — the who, what, why, and consequence\n"
    "- A passing mention, a one-sentence reference, or a tangential connection "
    "NEVER unlocks any tier\n"
    "- If in doubt, return {\"unlocked\": null}\n\n"
    "Return ONLY {\"unlocked\": \"entry-slug\"} or {\"unlocked\": null}\n\n"
    "CANDIDATE ENTRIES (tier — slug — trigger):\n"
    + "\n".join(
        f"  T{e['tier']} — {e['slug']} — {e['unlock_trigger']}"
        for e in MASTER_ENTRIES
        if e["slug"] in _CLASSIFIER_SLUGS
    )
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
        if isinstance(slug, str) and slug in _BY_SLUG and slug not in _EVENT_ONLY_SLUGS:
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
        # Only bump `rank_reached_at` when the rank actually changes so
        # the leaderboard can show "date they reached their current rank".
        set_fields = {
            "wallet_address": w,
            "rank": new_rank,
            "rank_title": RANK_TITLES.get(new_rank) if new_rank else None,
            "unlocked_count": len(unlocked_slugs),
            "updated_at": now,
        }
        if is_rank_up:
            set_fields["rank_reached_at"] = now
        await db[RANKS_COLLECTION].update_one(
            {"wallet_address": w},
            {"$set": set_fields},
            upsert=True,
        )
    except Exception as e:
        logger.warning("record_unlock rank upsert failed for %s: %s", w, e)

    logger.info(
        "Archive unlock: wallet=%s entry=%s tier=%s rank=%s rank_up=%s",
        w[:12] + "…", entry_id, entry["tier"], new_rank, is_rank_up,
    )

    # Fire-and-forget: ensure the Visual Canon Ledger has an image for
    # this entry. If canon already exists (chat has generated it before)
    # this is a cheap DB read + return. Otherwise the background task
    # generates a fresh image and stores it as pending. The unlock
    # celebration never blocks on this — the lore card fetches the
    # thumbnail lazily on next render.
    import asyncio as _asyncio
    try:
        _asyncio.create_task(ensure_entry_image(entry_id))
    except Exception as _e:
        logger.warning("failed to schedule ensure_entry_image for %s: %s", entry_id, _e)

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


# ── The Record (public leaderboard) ────────────────────────────────────
async def get_record_leaderboard(page: int = 1, limit: int = 10) -> Dict:
    """Paginated public leaderboard of wallets by unlock count.

    Privacy: wallets are NOT filtered/shortened here — that's the
    frontend's job (a wallet's address is public on-chain anyway, but
    the UI truncates to `abcd…wxyz` so the leaderboard never
    inadvertently emphasises a full address).

    Sort order (per spec):
      1. unlocked_count DESC — how deep they've gone
      2. rank_reached_at ASC — earlier rank-ups break ties

    Rank-less wallets (never earned Seeker) are included at the bottom
    so someone with 15 unlocks still appears — the leaderboard is about
    the deepest signals, not just the ranked ones.
    """
    page = max(1, int(page or 1))
    limit = max(1, min(50, int(limit or 10)))
    skip = (page - 1) * limit

    projection = {
        "_id": 0,
        "wallet_address": 1,
        "rank": 1,
        "rank_title": 1,
        "unlocked_count": 1,
        "rank_reached_at": 1,
        "updated_at": 1,
    }
    try:
        # Filter out any wallet address matching a known testing-agent
        # naming pattern so QA runs never pollute the public
        # leaderboard. `TEST_WALLET_REGEX` is the single source of
        # truth for what counts as test data.
        from utils.test_wallet_filter import TEST_WALLET_REGEX
        base_filter = {
            "unlocked_count": {"$gt": 0},
            "wallet_address": {"$not": {"$regex": TEST_WALLET_REGEX}},
        }
        total = await db[RANKS_COLLECTION].count_documents(base_filter)
        cursor = (
            db[RANKS_COLLECTION]
            .find(base_filter, projection)
            .sort([("unlocked_count", -1), ("rank_reached_at", 1), ("updated_at", 1)])
            .skip(skip)
            .limit(limit)
        )
        rows = await cursor.to_list(length=limit)
    except Exception as e:
        logger.warning("get_record_leaderboard failed: %s", e)
        return {"total": 0, "page": page, "limit": limit, "entries": []}

    entries = []
    for i, r in enumerate(rows):
        entries.append({
            "position": skip + i + 1,
            "wallet": r.get("wallet_address"),
            "rank": r.get("rank"),
            "rank_title": r.get("rank_title"),
            "unlocked_count": r.get("unlocked_count", 0),
            # `rank_reached_at` may be missing on rows created before we
            # started tracking it — fall back to `updated_at` so the UI
            # always has something to render.
            "rank_reached_at": r.get("rank_reached_at") or r.get("updated_at"),
        })
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": (skip + len(entries)) < total,
        "entries": entries,
    }


# ── Visual Canon integration (Phase E) ─────────────────────────────────
# On unlock we ensure the Visual Canon Ledger holds an image for the
# subject the entry describes. The canon collection is the SINGLE source
# of truth for entry thumbnails — we never store a second copy on the
# archive_unlocks doc. LoreCards fetch the image lazily by slug via
# `GET /api/archive/entry-image/{slug}` when they render in unlocked
# state.
#
# The entry-slug IS the canon subject_tag. If canon already exists
# (chat has generated this subject before), we return immediately. If
# not, we fire a Gemini generation with a prompt derived from the entry's
# name + locked description, storing the result as `status: pending`
# using visual_canon.record_generation — which means the next community
# member to ask about the same subject in chat gets our generation as
# their reference too. Both systems benefit.

# One-shot lock per slug so parallel unlocks of the same entry (unlikely
# but possible if two wallets classify it simultaneously) don't race on
# the same Gemini call.
_ENTRY_IMAGE_LOCKS: Dict[str, "asyncio.Lock"] = {}


async def get_entry_image(slug: str) -> Optional[Dict]:
    """Return `{image_base64, image_mime, status}` from the canon collection
    for this entry slug, or None if nothing is stored yet. Any status is
    acceptable — we render pending generations as thumbnails so users see
    art appear as soon as it's generated, not only after promotion."""
    if not slug or slug not in _BY_SLUG:
        return None
    try:
        doc = await db["visual_canon"].find_one(
            {"subject_tag": slug, "image_base64": {"$exists": True, "$ne": None}},
            {"image_base64": 1, "image_mime": 1, "status": 1, "_id": 0},
        )
        return doc or None
    except Exception as e:
        logger.warning("get_entry_image failed for %s: %s", slug, e)
        return None


def _build_entry_prompt(entry: Dict) -> str:
    """Compose the Gemini prompt for a lore-entry image.

    Uses the entry name + locked description so the generated image
    frames the subject the same way visitors are teased about it. The
    Bullpughan universe style guardrails come from the LLM system
    message; here we just describe the SUBJECT.
    """
    name = entry.get("name") or entry.get("slug")
    tease = entry.get("locked_desc") or ""
    return (
        f"Archive entry: {name}. {tease} "
        "Cinematic hyperdetailed digital art, single cohesive scene, "
        "the Bullpug universe aesthetic. Do NOT include any text, "
        "letters, words, captions, or typography anywhere in the image."
    ).strip()


async def _generate_entry_image(entry: Dict) -> Optional[Dict]:
    """Generate + cache the visual_canon image for an entry.

    Returns `{image_base64, image_mime}` on success, None on any failure
    (network hiccup, model refusal, missing key, …). Failures are
    swallowed — the LoreCard just renders without a thumbnail and the
    next unlock or admin action can retry. Never raises.
    """
    # Imports kept local to avoid pulling the Gemini SDK into cold
    # startup paths (subject-only chat text responses shouldn't need it).
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent
        from services.image_references import (
            BULLPUG_REFERENCE_URL,
            TINKERPUG_REFERENCE_URL,
            REFERENCE_MIME,
            load_reference_b64,
        )
    except Exception as e:
        logger.warning("Entry image gen: SDK import failed: %s", e)
        return None

    api_key = _os_env("EMERGENT_LLM_KEY")
    if not api_key:
        logger.info("Entry image gen: EMERGENT_LLM_KEY missing — skipping")
        return None

    prompt = _build_entry_prompt(entry)
    # Attach the character reference for the two entries that ARE named
    # characters at Tier 2 (`ruffus-deep`, `tinkerpug-patches`) — using
    # the same character canon the chat pipeline uses so the record
    # stays visually consistent.
    ref_url = None
    if entry["slug"] == "tinkerpug-patches":
        ref_url = TINKERPUG_REFERENCE_URL
    # (Bullpug isn't a subject_tag in MASTER_ENTRIES — character-named
    # subjects are excluded from the canon ledger by spec.)
    file_contents = None
    if ref_url:
        b64 = await load_reference_b64(ref_url)
        if b64:
            file_contents = [FileContent(content_type=REFERENCE_MIME,
                                         file_content_base64=b64)]

    try:
        chat = (
            LlmChat(
                api_key=api_key,
                session_id=f"archive-entry-{entry['slug']}",
                system_message=(
                    "You are Tinkerpug, Keeper of the Archive. Retrieve "
                    "ONE cinematic image matching the described Archive "
                    "record in the Bullpug universe style. Never include "
                    "gold coins, currency symbols, price imagery, or any "
                    "financial iconography — the Bullpug universe is a "
                    "story world, imagery is narrative not financial."
                ),
            )
            .with_model("gemini", "gemini-3.1-flash-image-preview")
            .with_params(modalities=["image", "text"])
        )
        msg = UserMessage(text=prompt, file_contents=file_contents)
        _, images = await chat.send_message_multimodal_response(msg)
        if not images:
            return None
        img = images[0]
        b64 = img.get("data") or ""
        mime = img.get("mime_type") or "image/png"
        if not b64:
            return None
        # Store in visual_canon so subsequent lookups (from both the
        # Archive and the chat pipeline) get the same reference.
        from services import visual_canon
        await visual_canon.record_generation(
            subject_tag=entry["slug"],
            subject_display=entry.get("name") or entry["slug"],
            first_prompt=prompt,
            image_base64=b64,
            image_mime=mime,
        )
        return {"image_base64": b64, "image_mime": mime}
    except Exception as e:
        logger.warning("Entry image gen failed for %s: %s", entry["slug"], e)
        return None


def _os_env(k: str) -> Optional[str]:
    import os
    return os.environ.get(k)


async def ensure_entry_image(slug: str) -> Optional[Dict]:
    """Idempotent: guarantee visual_canon holds an image for this entry.

    Return shape (or None): `{image_base64, image_mime, status}`.
    Uses a per-slug asyncio.Lock so concurrent unlocks of the same
    entry only trigger one generation call.

    Special-tier entries (companion-linked) are skipped — their
    celebration is animated in the UI (plushie bounce + soundwave)
    rather than a generated scene, so a placeholder is inappropriate.
    """
    if not slug or slug not in _BY_SLUG:
        return None
    if slug in _SPECIAL_SLUGS:
        return None

    # Fast path — already have one
    existing = await get_entry_image(slug)
    if existing:
        return existing

    # Slow path — acquire per-slug lock and generate
    import asyncio as _asyncio
    lock = _ENTRY_IMAGE_LOCKS.get(slug)
    if lock is None:
        lock = _asyncio.Lock()
        _ENTRY_IMAGE_LOCKS[slug] = lock
    async with lock:
        # Re-check inside the lock in case another task filled it
        existing = await get_entry_image(slug)
        if existing:
            return existing
        result = await _generate_entry_image(_BY_SLUG[slug])
        if result:
            return {**result, "status": "pending"}
        return None
