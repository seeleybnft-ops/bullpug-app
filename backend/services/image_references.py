"""Shared character reference images for AI image generation.

Two Imgur-hosted references — one per canonical character — so that both
the daily drop pipeline (`services.daily_drop`) and the interactive
Tinkerpug chat image tool (`routers.ai_chat`) can attach the correct
visual anchor to Gemini prompts without conflating Bullpug and Tinkerpug.

Kept in its own module so both callers can import safely without any
circular import risk between the router layer and the service layer.

────────────────────────────────────────────────────────────────────────
CANONICAL VISUAL SOURCE OF TRUTH
────────────────────────────────────────────────────────────────────────
Two named reference files, uploaded by the creator, are the ONLY
approved visual source for these characters. The Imgur URLs below host
the exact same images.

  • bullpug-reference.jpg   → BULLPUG_REFERENCE_URL
    Bullpug — the cosmic guardian. DEEP DARK BLUE-BLACK fur (almost
    black) with a faint cosmic shimmer, flowing galaxy cape, swirling
    blue-purple cosmic medallion, large dark ridged bull horns,
    nebula / deep-space background. NO cybernetic parts, NO techno
    collar, NO armour, NO workshop elements, NO fawn / tan / brown fur.

  • tinkerpug-reference.jpg → TINKERPUG_REFERENCE_URL
    Tinkerpug — the Keeper of PugChain. Fawn / tan fur, cybernetic
    segmented tail, armoured left foreleg, techno collar, neon
    cyberpunk workshop environment. NO galaxy cape, NO cosmic medallion,
    NO deep-space background.

These are two completely distinct characters who share only the pug
base form and bull horns. Everything else — fur colour, wardrobe,
augments, environment — is different.
"""

import asyncio
import base64
import logging
from typing import Optional, Dict

import httpx

logger = logging.getLogger(__name__)

# ── Canonical filenames (documented source of truth) ─────────────────────
# The Imgur URLs below host these exact files, uploaded by the creator.
BULLPUG_REFERENCE_FILENAME = "bullpug-reference.jpg"
TINKERPUG_REFERENCE_FILENAME = "tinkerpug-reference.jpg"

# ── Public constants (imported by daily_drop.py and ai_chat.py) ──────────
BULLPUG_REFERENCE_URL = "https://i.imgur.com/XC7pHKW.jpeg"
TINKERPUG_REFERENCE_URL = "https://i.imgur.com/hXukVoJ.jpeg"
REFERENCE_MIME = "image/jpeg"

# ── Canonical character descriptions ─────────────────────────────────────
# The single source of truth for what each character looks like. Any
# system prompt that anchors a generation to a specific character MUST
# paste this description verbatim so daily drops and interactive chat
# image generation stay visually consistent. Fur colour is the primary
# distinguishing feature for Bullpug and MUST NOT be paraphrased away.
BULLPUG_CHARACTER_DESCRIPTION = (
    "Bullpug — the cosmic guardian. Bullpug's fur is DEEP DARK "
    "BLUE-BLACK, almost black, with a faint cosmic shimmer — like "
    "starfield darkness made solid. NOT fawn, NOT tan, NOT brown. His "
    "fur colour is the single most important distinguishing feature. "
    "Dark as deep space with subtle blue-purple iridescence. He has "
    "large dark ridged bull horns, a flowing galaxy cape, and a "
    "swirling blue-purple cosmic medallion. He has NO cybernetic parts, "
    "NO techno collar, NO armour, NO workshop tools — those augments "
    "belong to Tinkerpug. He exists in deep space and nebula "
    "environments — starfields, cosmic dust, the unmapped Between — "
    "not in the neon city and not at any workbench."
)

TINKERPUG_CHARACTER_DESCRIPTION = (
    "Tinkerpug — the Keeper of PugChain. Fawn / tan pug fur, dark "
    "ridged bull horns, cybernetic segmented tail, armoured left "
    "foreleg, techno collar. He exists in the neon cyberpunk workshop "
    "and Newpug City alleys — workbenches, tools, glowing PugChain "
    "hardware. He has NO galaxy cape, NO cosmic medallion, NO "
    "deep-space background — those belong to Bullpug."
)

# Legacy aliases — historically these were underscore-prefixed inside
# daily_drop.py. Keep the same names available so ai_chat.py's existing
# imports continue to resolve without churning every call site.
_BULLPUG_REFERENCE_URL = BULLPUG_REFERENCE_URL
_TINKERPUG_REFERENCE_URL = TINKERPUG_REFERENCE_URL
_REFERENCE_MIME = REFERENCE_MIME

# One in-memory cache entry per URL. Both entries are independent — a
# transient fetch failure for one character never poisons the other.
_reference_cache: Dict[str, Optional[str]] = {
    BULLPUG_REFERENCE_URL: None,
    TINKERPUG_REFERENCE_URL: None,
}
_reference_lock = asyncio.Lock()


async def load_reference_b64(url: str) -> Optional[str]:
    """Fetch + cache a character reference image as base64.

    Resilient pattern: browser-like UA + Referer to avoid Imgur
    throttling, only successful responses cached, transient failures
    retry on the next call instead of poisoning the cache for the
    process lifetime.
    """
    if _reference_cache.get(url):
        return _reference_cache[url]
    async with _reference_lock:
        if _reference_cache.get(url):
            return _reference_cache[url]
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://imgur.com/",
        }
        try:
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=True, headers=headers
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            b64 = base64.b64encode(resp.content).decode("ascii")
            _reference_cache[url] = b64
            logger.info(
                "Loaded reference image %s (%d bytes → %d b64 chars)",
                url, len(resp.content), len(b64),
            )
            return b64
        except Exception as e:
            logger.warning(
                "Could not fetch reference image %s (will retry on next "
                "call): %s", url, e,
            )
            return None


# Legacy alias — kept so ai_chat.py's existing lazy import path continues
# to work during the transition.
_load_reference_b64 = load_reference_b64
