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
the exact same images, and identical copies are cached on disk under
`/app/backend/reference_images/` alongside each other.

  • bullpug-reference.jpg   → BULLPUG_REFERENCE_URL
    Bullpug — the cosmic guardian. WARM FAWN fur (the natural tan/beige
    colour of a pug) with a flowing deep purple-blue galaxy cape, a
    swirling blue cosmic medallion, large dark ridged bull horns, and a
    nebula / deep-space background. NO cybernetic parts, NO techno
    collar, NO armour, NO workshop elements. NOT dark, NOT black, NOT
    blue-furred.

  • tinkerpug-reference.jpg → TINKERPUG_REFERENCE_URL
    Tinkerpug — the Keeper of PugChain. Fawn / tan fur, cybernetic
    segmented tail, armoured left foreleg, techno collar, neon
    cyberpunk workshop environment with holographic PugChain hardware
    and glowing circuit-board workbench. NO galaxy cape, NO cosmic
    medallion, NO deep-space background. An additional on-disk
    reference (tinkerpug-reference-2.jpg) is retained for archival /
    future rotation.

These are two completely distinct characters who share only the pug
base form (fawn fur, bull horns). Wardrobe, augments, and environment
are what set them apart.
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
# GUARDIAN CORPS
BULLPUG_REFERENCE_URL = "https://i.imgur.com/JxxdOKG.jpeg"
TINKERPUG_REFERENCE_URL = "https://i.imgur.com/IVCxhIp.jpeg"

# Extended Guardian Corps (Feb 2026 — Character Expansion v1.0)
RUFFUS_REFERENCE_URL = "https://i.imgur.com/nURkkCs.jpeg"
LUNA_REFERENCE_URL = "https://i.imgur.com/Xhhg7js.jpeg"
CHARGEBULL_REFERENCE_URL = "https://i.imgur.com/cwiPl7e.jpeg"
GRIZZLOR_REFERENCE_URL = "https://i.imgur.com/QvBC7PK.jpeg"

# Extended Characters
GUARDIAN_RIND_REFERENCE_URL = "https://i.imgur.com/5gHonvR.jpeg"
ELDER_HEARTH_REFERENCE_URL = "https://i.imgur.com/77iOV8g.jpeg"
DRIFT_REFERENCE_URL = "https://i.imgur.com/gbQ7ade.jpeg"
KEYHOLDER_MORA_REFERENCE_URL = "https://i.imgur.com/UsJMFL0.jpeg"

# NO REFERENCE — text description only (generate freely, max diversity)
#   BULLPUGHAN_CITIZEN → see CITIZEN_CHARACTER_DESCRIPTION below
# NO REFERENCE — text only, gated on Archive unlock (see visual_intent.py)
#   SPIRIT_OF_THE_STARS, OWL_OF_ORACLES, FOX_OF_FORKS, CAT_OF_CATALYSTS

REFERENCE_MIME = "image/jpeg"

# ── Canonical character descriptions ─────────────────────────────────────
# The single source of truth for what each character looks like. Any
# system prompt that anchors a generation to a specific character MUST
# paste this description verbatim so daily drops and interactive chat
# image generation stay visually consistent. Fur colour is the primary
# distinguishing feature for Bullpug and MUST NOT be paraphrased away.
BULLPUG_CHARACTER_DESCRIPTION = (
    "Bullpug's fur is warm FAWN — the natural tan/beige colour of a "
    "pug. NOT black, NOT dark blue, NOT cosmic dark. His fur is warm "
    "fawn throughout, which contrasts strongly against his deep "
    "purple-blue galaxy cape and the dark nebula behind him."
)

TINKERPUG_CHARACTER_DESCRIPTION = (
    "Tinkerpug — the Keeper of PugChain. Fawn / tan pug fur, dark "
    "ridged bull horns, cybernetic segmented tail, armoured left "
    "foreleg, techno collar. He exists in the neon cyberpunk workshop "
    "and Newpug City alleys — workbenches, tools, glowing PugChain "
    "hardware. He has NO galaxy cape, NO cosmic medallion, NO "
    "deep-space background — those belong to Bullpug."
)

# Extended Guardian Corps descriptions
RUFFUS_CHARACTER_DESCRIPTION = (
    "Ruffus is the elder Guardian. Dark-furred, weathered, "
    "battle-hardened. Seventeen runes carved into his dark ridged "
    "bull horns — one per confirmed Consortium identity, all gone. "
    "Heavy-set, solid, aged Guardian corps armour worn at the edges. "
    "Expression: measured, certain, calm of someone who has seen the "
    "worst. Background: ruins of Margin's Edge or the Grand Bark "
    "Hall. Vary pose and framing; preserve the runes on the horns "
    "and the weathered armour."
)

LUNA_CHARACTER_DESCRIPTION = (
    "Luna is the seer Guardian. Slender female pug, still and "
    "precise. Her coat carries points of bioluminescent light — each "
    "one a future she has already seen, some bright, some faded. "
    "Large calm eyes looking slightly past the viewer. Expression: "
    "serene, watchful, carrying something private. Background: the "
    "Grand Bark Hall interior, a single cone of light from above, or "
    "deep starfield. The points of light on her coat are the warmest "
    "elements in frame."
)

CHARGEBULL_CHARACTER_DESCRIPTION = (
    "Chargebull is the charge Guardian. Large, powerfully built male "
    "pug — significantly bigger than standard Bullpughans. Dark "
    "ridged bull horns, broader than most. Heavy Guardian corps "
    "armour, worn from twelve years of first response. Expression: "
    "direct, warm underneath the weight of experience. Background: "
    "Genesis Vault approach, cold cyan lighting, or mid-charge "
    "through a compromised market space. Built like forward momentum."
)

GRIZZLOR_CHARACTER_DESCRIPTION = (
    "Grizzlor is the restored advisor, formerly Gideon. Lean, "
    "precise male pug with the specific stillness of someone who "
    "looks very carefully before speaking. Dark ridged bull horns, "
    "slightly asymmetric. Sharp analytical eyes carrying the weight "
    "of two identities. Expression: quiet assessment, wariness built "
    "from experience of deception. Background: dim archive space, "
    "Ledger open on a desk, Architect signature diagrams faintly "
    "visible. The weight of both identities is visible in the face."
)

# Extended Characters descriptions
GUARDIAN_RIND_CHARACTER_DESCRIPTION = (
    "Guardian Rind is a Chainwarden. Dark-furred male pug "
    "(Chainwardens come in any gender). Guardian corps armour, worn "
    "with ease. Carries a Snout Scanner — held like a duty, not a "
    "weapon. Expression: quiet, exact, almost unnervingly calm. "
    "Background: neon Newpug City market space, transaction data "
    "visible on holo-screens behind. The kind of stillness that "
    "comes from never needing to announce findings dramatically."
)

ELDER_HEARTH_CHARACTER_DESCRIPTION = (
    "Elder Hearth is the civic memory of Newpug City. Elder female "
    "pug, soft presence, iron memory. Purple ceremonial robes with "
    "gold trim. A medallion worn long enough to have its own "
    "history. Warm eyes, soft voice. Expression: the authority of "
    "someone who has never needed to raise their voice to be heard. "
    "Background: Festival of Barks preparations, lantern-lit civic "
    "spaces, or the Grand Bark Hall. She organises the Festival "
    "every year and knows every chant that started as a joke and "
    "became scripture."
)

DRIFT_CHARACTER_DESCRIPTION = (
    "Drift is a seeker of the Between. Gender deliberately ambiguous "
    "— Drift represents anyone who survived loss with belief intact. "
    "Hooded, dark-cloaked, between registers — not quite city, not "
    "quite Between. A heartbeat medallion at the chest that pulses "
    "faintly gold in the same rhythm as the Signal. Expression: the "
    "eyes have seen the loss and are still moving. Background: the "
    "unmapped edges of the Between, cosmic spires, deep purple "
    "night. Not holy. Just stubborn. The only fixed things: the "
    "eyes, and the heartbeat that has not stopped."
)

KEYHOLDER_MORA_CHARACTER_DESCRIPTION = (
    "Keyholder Mora keeps the Ancient Cold Records beneath Newpug "
    "City. Dark-furred female pug, gothic archive robes — elegant "
    "rather than austere. An ornate key pendant at her chest, older "
    "than any lock currently in use. Expression: does not gossip, "
    "does not flatten, does not perform. Eyes of someone who has "
    "read things that changed their understanding of the present "
    "and chose to keep reading anyway. Background: the Ancient Cold "
    "Records archive — frost on stone, rune archways, the sealed "
    "dark beneath the substrate layer."
)

# Citizen (no reference image — max diversity per spec §2C)
CITIZEN_CHARACTER_DESCRIPTION = (
    "A Bullpughan citizen of Newpug City. Pug base with small dark "
    "ridged bull horns — the only universal trait. Fur colour varies "
    "widely: fawn, tan, dark brown, black, grey, or mixed. No "
    "cybernetic parts (those belong to Tinkerpug exclusively). "
    "Clothing reflects district and profession: Substrate Layer "
    "workers wear maintenance gear, hard hats, tool belts, orange "
    "high-vis; Canal District residents wear layered streetwear, "
    "warm tones; Upper Spires citizens wear formal civic attire "
    "with gold trim; Guardian corps adjacent wear tactical gear "
    "with chain insignia; Archive workers wear lab coats and data "
    "glasses; Artists wear paint-stained clothing with brushes; "
    "Chain Surfers wear sleek athletic gear; Outer Colony settlers "
    "wear rugged practical clothing against starfield backgrounds. "
    "Every citizen is distinct — vary fur colour, clothing, "
    "profession, background, and expression freely. Cyberpunk neon "
    "aesthetic throughout. The only constants: pug face, bull "
    "horns, no cybernetics."
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
