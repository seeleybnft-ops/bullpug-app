"""Daily Bullpug Drop — one AI-generated Bullpughan universe image per USER per UTC day.

Each user (wallet OR anonymous session) gets a unique drop deterministically
seeded from `(user_key, date_utc)`. Variety comes from a hybrid prompt pool:
30 canonical scenes + a dynamic word-bank assembler that generates fresh canon
combinations on the fly (the Bullpughan universe is constantly expanding).

Every generation is persisted to MongoDB (`db.daily_drops`) for creator/admin
reference — keyed by `(user_key, date_utc)`, indexed for fast pagination.
"""

import asyncio
import hashlib
import logging
import os
import random
from datetime import datetime, timezone
from typing import Optional, Dict

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent

from utils.database import db
from services.image_references import (
    BULLPUG_REFERENCE_URL as _BULLPUG_REFERENCE_URL,
    TINKERPUG_REFERENCE_URL as _TINKERPUG_REFERENCE_URL,
    REFERENCE_MIME as _REFERENCE_MIME,
    load_reference_b64 as _load_reference_b64,
    BULLPUG_CHARACTER_DESCRIPTION,
    TINKERPUG_CHARACTER_DESCRIPTION,
)

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# ----- Canonical themed prompts -----
THEMED_DROPS = [
    ("Cometside Vigil", "Guardian Bullpug riding a celestial comet through the rings of CryptoCanis, fur blowing back, eyes locked forward"),
    ("Moon-Cheese Float", "Bullpug presiding over a Festival of Barks parade float made entirely of glowing moon cheese, bone-shaped fireworks overhead"),
    ("Alarm Red", "A Snout Scanner pulsing alarm-red as it detects a corrupt holographic blockchain transaction, magenta sparks crackling"),
    ("Dawn Over Newpug", "Newpug City skyline at dawn, holographic green soundwaves rippling like aurora through the pug-faced skyscrapers"),
    ("The Bull Constellation", "Bullpug forming as a constellation of stars in the night sky, golden lines connecting to reveal his silhouette"),
    ("PugChain Memory", "A Bullpughan family gathered around a glowing PugChain memory crystal, faces lit in mint green"),
    ("Surfing Soundwaves", "Bullpug surfing a wave of emerald soundwaves over an ocean of floating SOL tokens"),
    ("Corruption Detected", "A Guardian's snout scanner glowing magenta during a corruption alert, fingers tightening on the grip"),
    ("Megaphone Nebula", "Bullpug barking through a megaphone-shaped nebula, visible soundwaves spreading like light across the stars"),
    ("Pug Skull Float", "A massive festival float shaped like a stylised pug skull, golden fireworks bursting overhead, crowds cheering below"),
    ("Born of Stars", "Bullpug emerging from the heart of the Bull constellation, cascading golden light wrapping him in cosmic fur"),
    ("Magenta River", "A PugChain transaction visualised as a glowing river of magenta light flowing through a futuristic data centre"),
    ("Lunar Flag", "Bullpug astronaut planting a holographic flag on a moon made of cheese, Earth-like blue planet in the distance"),
    ("Guardian Gate", "Two Guardians flanking the entrance to a Newpug City PugChain hub, snout scanners drawn"),
    ("Token Meditation", "Bullpug in a serene meditation pose, surrounded by slowly orbiting glowing SOL coins"),
    ("Heartbeat in the Noise", "A heartbeat pulse cutting through visual static, the rhythm forming Bullpug's silhouette as it crescendos"),
    ("Neon Skater", "Bullpug riding a holographic skateboard through a neon-lit Newpug City alley, motion blur trailing"),
    ("First Scanner", "A young Bullpughan receiving their first Snout Scanner as a coming-of-age gift, awe lighting their face"),
    ("Market DJ", "Bullpug at a holographic DJ booth, mixing live market signals and candlestick waveforms"),
    ("The Statue", "A colossal Bullpug statue in the heart of Newpug City, twilight glow bathing the metropolis below"),
    ("Chasing FUD", "Bullpug chasing shadowy FUD demons through a foggy market floor, scanner beams cutting the mist"),
    ("Lantern Parade", "A Festival of Barks parade with pug-shaped paper lanterns floating gently into a starlit sky"),
    ("Cheese Sunset", "Bullpug's silhouette against a setting sun rendered as a wedge of glowing moon cheese"),
    ("Smart Contract Disarm", "A Guardian disarming a malicious smart contract with a precisely targeted snout-scanner beam, sparks flying"),
    ("Throne of Bags", "Bullpug curled up on a throne built from glowing token bags, regal and content"),
    ("PugChain Core", "Newpug City's PugChain core — a colossal glowing crystal pulsing with rhythmic green light"),
    ("The Elder's Scroll", "A Bullpughan elder reading the canon from a holographic scroll to a gathered audience"),
    ("Mountain Watch", "Bullpug standing watch on a mountaintop overlooking CryptoCanis at dawn, mist coiling below"),
    ("Defenders of Newpug", "A team of Bullpughans defending Newpug City from shadowy bad-actor forces, Snout Scanners active"),
    ("The Address", "Bullpug giving a speech to a vast crowd of Bullpughans, holographic stars and barks of prosperity overhead"),
]

# ----- Fresh-canon word banks for procedurally-assembled scenes -----
# Combining these yields ~30 × 28 × 24 × 18 × 14 ≈ 5 million unique scenes,
# more than enough variety for every user every day for years.
_FRESH_SUBJECTS = [
    "Bullpug", "a Guardian Bullpug", "a pack of Bullpughans", "an elder Bullpughan",
    "a young Bullpughan acolyte", "the cosmic guardian Bullpug", "Bullpug himself",
    "a robed Bullpughan oracle", "a courier Bullpughan with a token satchel",
    "twin Guardian Bullpugs", "a Bullpug pup with oversized scanner ears",
    "a Bullpughan rogue cloaked in static", "a champion Bullpug astronaut",
    "a meditating Bullpug monk", "a Bullpug skywriter", "a holographic projection of Bullpug",
    "an ancient Bullpughan ancestor", "a Bullpug bard with a soundwave lute",
    "a Bullpughan engineer", "a Bullpughan archivist", "Bullpug, eyes closed in focus",
    "a Bullpughan racer crouched at a starting line", "a Bullpug-shaped drone swarm",
    "a Bullpughan dreamer asleep on a token throne", "Bullpug mid-bark",
    "a stargazing Bullpughan child", "a Bullpughan gardener tending crypto-flora",
    "Bullpug atop a moon-cheese boulder", "a Bullpug hologram phasing into reality",
    "a courier Bullpughan delivering a glowing wallet",
]
_FRESH_ACTIONS = [
    "barking sound-waves at", "leaping over", "shielding", "guarding", "racing across",
    "meditating beside", "dancing around", "scanning", "decoding", "blessing",
    "racing toward", "diving into", "summoning", "negotiating with", "challenging",
    "saluting", "studying", "untangling", "weaving through", "exhaling smoke that becomes",
    "hovering above", "watching over", "casting starlight onto", "reflecting in",
    "carving symbols into", "leading a procession toward", "playing fetch with",
    "sniffing out",
]
_FRESH_OBJECTS = [
    "a swirling pug-shaped nebula", "the PugChain core crystal",
    "a falling moon-cheese asteroid", "a rogue smart contract dripping ink",
    "a shoal of mooncheese fish", "a holographic ledger floating in mid-air",
    "a cluster of orbiting SOL coins", "a colossal stone pug-arch",
    "a forest of token-blossom trees", "a ribbon of magenta liquidity",
    "the Between's heartbeat signal", "a fleet of Shadow Bear forces shadows",
    "a candle-lit Festival lantern", "a glowing token vault",
    "a wave of green soundwaves", "an obsidian Snout Scanner",
    "a Newpug City rooftop garden", "a constellation map written in starlight",
    "a wind-up bone-shaped firework", "a static-cloaked rug-pull artifact",
    "a hovering courier bag", "a swirling vortex of stale FUD",
    "a moon-cheese geyser",  "a Bullpug-shaped weather cloud",
]
_FRESH_LOCATIONS = [
    "in the heart of Newpug City", "above CryptoCanis' icy rings",
    "deep in the unmapped the Between", "atop the Bull constellation",
    "inside a holographic PugChain ledger", "on the rooftop of the PugChain Tower",
    "in the catacombs beneath the Festival grounds", "across the mooncheese plains",
    "at the edge of the the Between map", "inside a frozen moment of trading time",
    "below a sky raining moon-cheese crumbs", "in a hidden Newpug alley",
    "on the steps of the Guardians' Hall", "above a glowing token reef",
    "inside a memory crystal", "in a cosmic library of canon scrolls",
    "atop the city's tallest pug-faced spire", "in the centre of a starlit plaza",
]
_FRESH_MOODS = [
    "at twilight", "under a meteor shower", "during the Festival of Barks",
    "at the crescendo of the 152 BPM signal", "with a pug nebula on the horizon",
    "while green aurora ripples overhead", "amid floating golden ember-coins",
    "at the exact moment of a market reversal", "in a hush of pre-dawn quiet",
    "with confetti made of moon-cheese flakes drifting down", "during a Guardian's vigil",
    "as midnight UTC strikes", "as a glitch ripples across the sky",
    "as the PugChain core syncs",
]


_BULLPUG_STYLE_SUFFIX = (
    "MANDATORY CHARACTER DESIGN — every Bullpug and Bullpughan is a pug-faced "
    "creature with prominent curved bull horns rising from the top of the head. "
    "Horns are non-negotiable: thick, polished, ivory-to-bronze, curving upward "
    "and slightly outward like a young bull's, anchored just behind the brow. "
    "The face is unmistakably a pug — squashed muzzle, wrinkled forehead, large "
    "expressive round eyes, floppy ears, short jaw. Fur can be ANY color or "
    "pattern (fawn, black, white, mint-green, magenta, gold, brindle, cosmic "
    "iridescent, etc.) — embrace bold variety. "
    "Cinematic, hyperdetailed digital art in the Bullpug universe aesthetic — "
    "neon-lit, cyberpunk, warm gold against deep indigo, rich fur and machine texture. "
    "No readable text, no logos, no watermarks. "
    "Wide cinematic composition."
)

# Per-(user, date) asyncio locks so concurrent first-callers don't all trigger an LLM call.
_generation_locks: Dict[str, asyncio.Lock] = {}
_meta_lock = asyncio.Lock()


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _seed_rng(user_key: str, date_utc: str) -> random.Random:
    """Stable per-(user, date) random.Random instance."""
    seed = int(hashlib.sha256(f"{user_key}|{date_utc}".encode()).hexdigest(), 16)
    return random.Random(seed)


def _select_prompt_for(user_key: str, date_utc: str):
    """Return (theme_label, scene_prompt, kind) for the given user+date.

    50% chance: pick one of the canonical themed drops.
    50% chance: procedurally assemble a 'fresh canon' scene from word banks —
    universe-expansion variety so users see something new most days.
    """
    rng = _seed_rng(user_key, date_utc)
    if rng.random() < 0.5:
        idx = rng.randrange(len(THEMED_DROPS))
        theme, scene = THEMED_DROPS[idx]
        return theme, scene, "canonical"

    # Fresh-canon assembler
    subject = rng.choice(_FRESH_SUBJECTS)
    action = rng.choice(_FRESH_ACTIONS)
    obj = rng.choice(_FRESH_OBJECTS)
    location = rng.choice(_FRESH_LOCATIONS)
    mood = rng.choice(_FRESH_MOODS)
    scene = f"{subject} {action} {obj} {location}, {mood}"
    # Generate a short evocative theme label from the subject + a key noun in the object
    key_noun = obj.split()[-1].rstrip(",.")
    theme = f"{subject.split()[0].capitalize()} & the {key_noun.capitalize()}"
    return theme, scene, "fresh"


async def _lock_for(user_key: str, date_utc: str) -> asyncio.Lock:
    key = f"{user_key}|{date_utc}"
    async with _meta_lock:
        lock = _generation_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _generation_locks[key] = lock
        return lock


# ── Character reference images ────────────────────────────────────────────
# Reference URLs, mime type, cache and loader all live in
# `services.image_references` — imported at the top of this module.
# This function picks WHICH of the two references matches a given scene.


def _pick_reference_for_scene(theme: str, scene: str) -> Optional[str]:
    """Return the character reference URL that matches the drop's subject.

    Rules:
      • Any mention of "tinkerpug" in theme or scene → Tinkerpug reference.
      • Otherwise (explicit Bullpug or unnamed) → Bullpug reference.
      • Returns None only if both text fields are empty (shouldn't happen
        for real drops but keeps the fallback path clean).
    """
    haystack = f"{theme or ''} {scene or ''}".lower()
    if not haystack.strip():
        return None
    if "tinkerpug" in haystack:
        return _TINKERPUG_REFERENCE_URL
    return _BULLPUG_REFERENCE_URL


async def get_drop_for_user(user_key: str) -> Optional[Dict]:
    """Return today's drop for the given user_key, generating + caching if missing.

    user_key should be the user's wallet address if available, otherwise the
    anonymous session_id. Each (user_key, date_utc) pair generates exactly one
    image, then locks for 24h until the UTC date rolls over.
    """
    date_utc = _today_utc()

    # Fast path — already cached for this user/day
    cached = await db.daily_drops.find_one(
        {"user_key": user_key, "date_utc": date_utc}, {"_id": 0}
    )
    if cached:
        return cached

    if not EMERGENT_LLM_KEY:
        logger.warning("EMERGENT_LLM_KEY missing — cannot generate daily drop")
        return None

    lock = await _lock_for(user_key, date_utc)
    async with lock:
        # Re-check after acquiring lock
        cached = await db.daily_drops.find_one(
            {"user_key": user_key, "date_utc": date_utc}, {"_id": 0}
        )
        if cached:
            return cached

        theme, scene, kind = _select_prompt_for(user_key, date_utc)
        full_prompt = f"{scene}. {_BULLPUG_STYLE_SUFFIX}"
        # Pick the right character reference per scene, then attach it. If
        # the fetch fails for any reason we fall through to a text-only
        # prompt so a user's daily drop is never blocked by an outage.
        ref_url = _pick_reference_for_scene(theme, scene)
        reference_b64 = await _load_reference_b64(ref_url) if ref_url else None
        file_contents = (
            [FileContent(content_type=_REFERENCE_MIME, file_content_base64=reference_b64)]
            if reference_b64
            else None
        )
        is_tinkerpug = ref_url == _TINKERPUG_REFERENCE_URL
        # Character description is imported from services.image_references
        # so daily drops and interactive chat image generation share ONE
        # source of truth. The reference-anchoring lead sentence stays
        # local because it references the FileContent attachment, which
        # is a per-caller detail.
        if is_tinkerpug:
            character_line = (
                "The attached reference image is Tinkerpug. "
                + TINKERPUG_CHARACTER_DESCRIPTION
                + " Preserve these identifying features exactly; vary "
                "pose, framing, expression, and setting per the prompt."
            )
        else:
            character_line = (
                "The attached reference image is Bullpug. "
                + BULLPUG_CHARACTER_DESCRIPTION
                + " Preserve Bullpug's identifying features exactly — "
                "especially the DEEP DARK BLUE-BLACK fur colour; vary "
                "pose, framing, expression, and setting per the prompt."
            )
        try:
            chat = (
                LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"daily-drop-{date_utc}-{user_key[:12]}",
                    system_message=(
                        "You are Bullpug, the cosmic guardian. Generate ONE cinematic image "
                        "matching the user's scene description in the Bullpug universe aesthetic — "
                        "neon-lit, cyberpunk, warm gold against deep indigo, rich fur and machine texture. "
                        + character_line +
                        " Never include gold coins, currency symbols, price imagery, Ethereum logos, "
                        "Bitcoin symbols, or any financial market iconography in the generated images. "
                        "The Bullpug universe is a story world — scenes should depict characters, "
                        "locations, lore events, and the Between. Keep imagery narrative, not financial."
                    ),
                )
                .with_model("gemini", "gemini-3.1-flash-image-preview")
                .with_params(modalities=["image", "text"])
            )
            msg = UserMessage(text=full_prompt, file_contents=file_contents)
            text, images = await chat.send_message_multimodal_response(msg)
            if not images:
                logger.error(f"Daily drop returned no images for {user_key}/{date_utc}")
                return None
            img = images[0]
            mime = img.get("mime_type") or "image/png"
            data = img.get("data") or ""
            drop = {
                "user_key": user_key,
                "date_utc": date_utc,
                "theme": theme,
                "scene": scene,
                "kind": kind,
                "image_base64": f"data:{mime};base64,{data}",
                "caption": (text or "").strip() or None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.daily_drops.update_one(
                {"user_key": user_key, "date_utc": date_utc},
                {"$setOnInsert": drop},
                upsert=True,
            )
            return await db.daily_drops.find_one(
                {"user_key": user_key, "date_utc": date_utc}, {"_id": 0}
            )
        except Exception:
            logger.exception("Daily drop generation failed")
            return None


# Backwards-compat alias for any callers that still reference the old API.
async def get_todays_drop() -> Optional[Dict]:
    """Legacy: returns a shared 'default' drop. Prefer get_drop_for_user(user_key)."""
    return await get_drop_for_user("default")
