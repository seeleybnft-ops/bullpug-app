"""Visual-intent classifier + supplemental image generator.

Runs after Tinkerpug produces a text response. If the user's question
was clearly asking about the *appearance* of a Bullpughan location /
object / scene (e.g. "what does Newpug City look like"), we look up
the visual canon for that subject and attach the canonical image to
the response — framed as "Direct from the Archive".

Design constraints (spec):
  • Additive — never replaces the text response
  • Conservative — never fires for character questions (Bullpug /
    Tinkerpug already have their own image generation path)
  • Cheap — most messages are NOT visual, so a fast regex pre-filter
    skips both the classifier AND the image generation. Chat latency
    is only impacted for messages that pass the pre-filter.
  • Feeds the visual canon ledger automatically via `record_generation`
    (first gen → pending; third gen → canon).
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from services import visual_canon

logger = logging.getLogger(__name__)


# ── Cheap pre-filter ────────────────────────────────────────────────
# Messages that don't match ANY of these patterns skip both the
# classifier LLM call AND the image generation entirely. The wording
# is deliberately narrow — the spec is explicit that visual-intent
# should be OBVIOUS from the question phrasing. False positives cost
# ~11s of latency (classifier + Nano Banana); false negatives cost
# nothing user-visible.
_VISUAL_INTENT_PATTERNS = [
    r"\blook(s|ed)?\s+like\b",
    r"\bwhat\s+(does|do|did)\s+.{2,80}\s+look\b",
    r"\bhow\s+(does|do|did)\s+.{2,80}\s+look\b",
    r"\bshow\s+me\s+(the|a|an|some)?\b",
    r"\bpicture\s+of\b",
    r"\bimage\s+of\b",
    r"\bwhat\s+does\s+.{2,80}\s+appear\b",
    r"\bhow\s+(does|do|did)\s+.{2,80}\s+appear\b",
    r"\bdescribe\s+(the|its)\s+(look|appearance|visuals?)\b",
    r"\bdescribe\b.{1,80}\bvisually\b",
    r"\bvisual(ly)?\s+(describe|show)\b",
    r"\bwhat\s+do(es)?\s+.{2,80}\s+resemble\b",
]
_VISUAL_INTENT_RE = re.compile("|".join(_VISUAL_INTENT_PATTERNS), re.IGNORECASE)

# ── Character-guard list (Phase B — never trigger on these) ─────────
# The character image path is handled elsewhere in ai_chat.py. Any tag
# that maps to a canonical character is dropped after the classifier.
_CHARACTER_KEYWORDS = {
    "bullpug", "tinkerpug", "seer-pug", "ruffus", "wolfpug",
    "pupster", "mama-nova",
}


def message_has_visual_intent(user_message: str) -> bool:
    """Fast regex pre-filter. Returns True if the message *might* be
    asking about the visual appearance of something."""
    if not user_message:
        return False
    if len(user_message) > 500:  # Cap for regex safety
        user_message = user_message[:500]
    return bool(_VISUAL_INTENT_RE.search(user_message))


# ── Classifier prompt ───────────────────────────────────────────────
_CLASSIFIER_SYSTEM = (
    "You classify whether a user's question is asking about the VISUAL "
    "APPEARANCE of a location, object, environment, event, or scene in "
    "the Bullpug universe (a memecoin/lore setting with locations like "
    "Newpug City, the Genesis Vault, the substrate layer, the Festival "
    "of Barks).\n\n"
    "RULES — return exactly ONE line:\n"
    "  1. If the question is asking to SEE / VISUALIZE / DESCRIBE THE LOOK OF "
    "     a location, object, environment, or event → return a short "
    "     kebab-case subject tag (2-4 words). Examples:\n"
    "        \"what does newpug city look like\" → newpug-city\n"
    "        \"describe the genesis vault\" (visually) → genesis-vault\n"
    "        \"show me the substrate layer\" → substrate-layer\n"
    "        \"what does the festival of barks look like\" → festival-of-barks\n"
    "  2. If the question is a LORE / HISTORY / EXPLANATION question "
    "     ('what is X', 'why is X', 'who is X', 'how does X work') "
    "     → return: none\n"
    "  3. If the question is about a CHARACTER (Bullpug, Tinkerpug, "
    "     Seer-Pug, Ruffus, Wolfpug, Pupster, Mama Nova, or any pug-named "
    "     individual) → return: none\n"
    "  4. If the question is about token prices, market data, chart, or "
    "     anything real-world / off-lore → return: none\n"
    "  5. If ambiguous — return: none. Prefer under-triggering.\n\n"
    "Return ONLY the tag or 'none'. No other text, no punctuation, no "
    "quotes, no explanation."
)


async def classify_visual_subject(
    user_message: str,
    api_key: str,
    session_id: str,
) -> Optional[str]:
    """Return a subject tag (kebab-case) or None.

    Precondition: `message_has_visual_intent(user_message) is True`.
    Caller is responsible for gating on the pre-filter so we never
    burn an LLM call on a message that clearly isn't visual.
    """
    if not user_message or not api_key:
        return None
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=_CLASSIFIER_SYSTEM,
        ).with_model("openai", "gpt-4o-mini")
        raw = await chat.send_message(UserMessage(text=user_message))
    except Exception as e:
        logger.warning("visual-intent classifier crashed: %s", e)
        return None

    tag = (raw or "").strip().lower()
    # Strip anything after the first line and drop punctuation.
    tag = tag.splitlines()[0].strip().strip('"\'.,;:').strip()
    if not tag or tag == "none":
        return None
    # Enforce kebab-case sanity — same normaliser used in
    # `visual_canon.normalise_subject` so we don't diverge on formatting.
    tag = re.sub(r"[^a-z0-9-]+", "-", tag).strip("-")
    if not tag or "-" not in tag and len(tag) < 4:
        # Reject single-token, no-hyphen tags — they're almost always
        # a hallucinated one-word reply rather than a real subject.
        return None
    parts = tag.split("-")
    if len(parts) > 5:
        tag = "-".join(parts[:5])
    if tag in _CHARACTER_KEYWORDS or any(p in _CHARACTER_KEYWORDS for p in parts):
        return None
    if visual_canon.is_character_subject(tag):
        return None
    return tag


# ── Character routing (Feb 2026 — Character Expansion v1.0) ─────────
# Named characters have dedicated reference images that must be attached
# directly rather than going through the visual canon pipeline. Import
# lazily so we don't tie module load to reference registration.
from services import image_references as _ir

_CHARACTER_APPEARANCE_MAP: Dict[str, str] = {
    "bullpug":         _ir.BULLPUG_REFERENCE_URL,
    "tinkerpug":       _ir.TINKERPUG_REFERENCE_URL,
    "ruffus":          _ir.RUFFUS_REFERENCE_URL,
    "luna":            _ir.LUNA_REFERENCE_URL,
    "chargebull":      _ir.CHARGEBULL_REFERENCE_URL,
    "grizzlor":        _ir.GRIZZLOR_REFERENCE_URL,
    "gideon":          _ir.GRIZZLOR_REFERENCE_URL,  # pre-restoration name
    "guardian rind":   _ir.GUARDIAN_RIND_REFERENCE_URL,
    "rind":            _ir.GUARDIAN_RIND_REFERENCE_URL,
    "elder hearth":    _ir.ELDER_HEARTH_REFERENCE_URL,
    "hearth":          _ir.ELDER_HEARTH_REFERENCE_URL,
    "drift":           _ir.DRIFT_REFERENCE_URL,
    "keyholder mora":  _ir.KEYHOLDER_MORA_REFERENCE_URL,
    "mora":            _ir.KEYHOLDER_MORA_REFERENCE_URL,
}

# Dormant Siblings + Spirit of the Stars — only reveal a supplemental
# image if the requesting wallet has unlocked their specific Archive
# entry AND we have a reference image. Currently no reference exists
# for any of them (per spec — text-only until arcs activate), so this
# map is here for the routing decision only; it always ends with None.
_RESTRICTED_CHARACTER_ENTRIES: Dict[str, Optional[str]] = {
    "owl of oracles":        "owl-oracles",
    "owl":                   "owl-oracles",
    "fox of forks":          "fox-forks",
    "fox":                   "fox-forks",
    "cat of catalysts":      "cat-moved-once",
    "cat":                   "cat-moved-once",
    "spirit of the stars":   None,  # no entry — always text only
}

# Citizen queries — never attach a supplemental image (spec §2C
# demands maximum diversity, no anchor).
_CITIZEN_TRIGGERS = {
    "bullpughan", "bullpughans", "citizen", "citizens",
    "people of newpug city", "people in newpug city",
}


def _detect_named_character(user_message: str) -> Optional[str]:
    """Longest-match search for a named character in the message.

    Returns the canonical lookup key (e.g. `"guardian rind"`) or None.
    Case-insensitive, whole-word aware. Longer keys are checked before
    shorter ones so `"guardian rind"` wins over the bare `"rind"`.
    """
    if not user_message:
        return None
    text = f" {user_message.lower()} "
    # Sort keys by length desc — multi-word aliases take precedence.
    all_keys = list(_CHARACTER_APPEARANCE_MAP.keys()) + list(_RESTRICTED_CHARACTER_ENTRIES.keys())
    for key in sorted(all_keys, key=len, reverse=True):
        needle = f" {key} "
        if needle in text:
            return key
    # Citizen detection is separate — those are class terms, not names.
    for cz in _CITIZEN_TRIGGERS:
        if f" {cz} " in text or text.startswith(f" {cz}") or text.endswith(f"{cz} "):
            return "__citizen__"
    return None


def _is_character_intent(user_message: str) -> bool:
    """True when the phrasing looks like an appearance question at all —
    same pre-filter as the location intent but keyed off characters
    like "describe X" or "what does X look like"."""
    if not user_message:
        return False
    lower = user_message.lower()
    return (
        "look like" in lower
        or "show me" in lower
        or "describe" in lower
        or "picture of" in lower
        or "image of" in lower
        or "appear" in lower
    )


# ── Image assembly ──────────────────────────────────────────────────
_SUPPLEMENTAL_CAPTION = "Direct from the Archive. \U0001F43E"


def _character_caption(character_name: str) -> str:
    display = " ".join(w.capitalize() for w in character_name.split(" "))
    return f"Direct from the Archive — {display}. The record holds. \U0001F43E"


def _readable_from_tag(tag: str) -> str:
    """`newpug-city` → `Newpug City` for the display prompt / seed
    caption when we need a natural-language handle on the subject."""
    return " ".join(w.capitalize() for w in tag.split("-"))


async def build_supplemental_image(
    subject_tag: str,
    api_key: str,
    session_id: str,
) -> Optional[Dict]:
    """Return the supplemental_image payload, or None on failure.

    Cache-first: if a canonical image already exists for this subject,
    we return it INSTANTLY (single Mongo lookup). Otherwise we call
    the same Nano Banana generation path used by `/image`, then
    record the fresh generation as a pending candidate — first gen →
    pending, third gen (from independent callers) → promoted to canon.
    """
    # 1. Fast path — an admin_override or canon image already exists.
    canon_doc = await visual_canon.lookup_canon(subject_tag)
    if canon_doc and canon_doc.get("image_base64"):
        mime = canon_doc.get("image_mime") or "image/png"
        b64 = canon_doc["image_base64"]
        image_url = b64 if b64.startswith("data:") else f"data:{mime};base64,{b64}"
        return {
            "subject": subject_tag,
            "image_base64": image_url,
            "caption": _SUPPLEMENTAL_CAPTION,
            "source": "canon",
        }

    # 2. Cache miss — generate a fresh image via the visual canon
    # pipeline. Lazily import ai_chat helpers to avoid a circular
    # import at module load time.
    try:
        from routers.ai_chat import _generate_image_response
    except Exception as e:
        logger.warning("could not import image-gen helper: %s", e)
        return None

    display = _readable_from_tag(subject_tag)
    # Prompt phrased as a wide, establishing view — best fit for a
    # "what does X look like" question. No SUBJECT: tag so the visual
    # canon branch is taken (not the character-reference branch).
    prompt = f"A wide cinematic establishing view of {display} in the Bullpug universe."

    try:
        gen = await _generate_image_response(prompt, session_id=session_id)
    except Exception as e:
        logger.warning("supplemental image generation failed for %s: %s", subject_tag, e)
        return None

    image_b64 = gen.get("image_base64")
    if not image_b64:
        return None

    return {
        "subject": subject_tag,
        "image_base64": image_b64,
        "caption": _SUPPLEMENTAL_CAPTION,
        "source": gen.get("canon_status") or "pending",
    }


async def _build_named_character_supplemental(
    character_key: str,
    user_id_for_gating: Optional[str] = None,
) -> Optional[Dict]:
    """Build a supplemental_image payload for a named character.

    • Regular characters (Guardian Corps + Extended) → direct reference URL
    • Restricted characters (Dormant Siblings + Spirit of the Stars) →
      gated on the requesting `user_id` having unlocked the linked
      Archive entry. Currently no reference image exists for any
      restricted character, so this always returns None until arcs
      activate (per spec § 2B).
    • Citizen — always None (spec § 2C — max diversity, no anchor)
    """
    if character_key == "__citizen__":
        return None

    if character_key in _RESTRICTED_CHARACTER_ENTRIES:
        entry_slug = _RESTRICTED_CHARACTER_ENTRIES[character_key]
        if not entry_slug or not user_id_for_gating:
            return None
        # Check unlock — if not unlocked, silently return None (spec:
        # "no image, no hint that an image exists").
        from utils.database import db  # lazy import — matches other lazy helpers
        unlocked = await db.archive_unlocks.find_one({
            "$or": [
                {"user_id": user_id_for_gating, "entry_id": entry_slug},
                {"wallet_address": user_id_for_gating, "entry_id": entry_slug},
            ]
        })
        if not unlocked:
            return None
        # Reference image exists yet? — no, per spec. Return None.
        return None

    ref_url = _CHARACTER_APPEARANCE_MAP.get(character_key)
    if not ref_url:
        return None
    # The frontend can render the Imgur URL directly — no need to
    # pass it through the Nano Banana pipeline. The chat response
    # includes the reference URL verbatim; the client fetches it.
    return {
        "subject": character_key.replace(" ", "-"),
        "image_base64": ref_url,
        "caption": _character_caption(character_key),
        "source": "character-reference",
    }


async def maybe_attach_supplemental_image(
    user_message: str,
    api_key: str,
    session_id: str,
    user_id: Optional[str] = None,
) -> Optional[Dict]:
    """End-to-end: character routing → location pipeline → None.

    Priority order (spec §2A):
      1. Named character detected + appearance intent → reference URL
         (or None if restricted-and-not-unlocked)
      2. Location / object / scene → visual canon pipeline (existing)
      3. Otherwise → None

    Never raises — all failure modes fall back to None so a
    supplemental-image outage never breaks the chat response.
    """
    if not user_message:
        return None

    # 1. Character path — check FIRST so a "what does Tinkerpug look
    # like" question routes to the canonical Tinkerpug reference
    # rather than accidentally getting classified as a location.
    if _is_character_intent(user_message):
        char_key = _detect_named_character(user_message)
        if char_key:
            char_payload = await _build_named_character_supplemental(char_key, user_id)
            if char_payload:
                return char_payload
            # If character was named but blocked (restricted-and-locked,
            # or citizen), do NOT fall through to the location pipeline —
            # the user asked about a person, not a place.
            if char_key in _RESTRICTED_CHARACTER_ENTRIES or char_key == "__citizen__":
                return None

    # 2. Location / object / scene path (existing).
    if not message_has_visual_intent(user_message):
        return None
    subject = await classify_visual_subject(user_message, api_key, session_id)
    if not subject:
        return None
    return await build_supplemental_image(
        subject_tag=subject,
        api_key=api_key,
        session_id=f"supplemental-{session_id}",
    )
