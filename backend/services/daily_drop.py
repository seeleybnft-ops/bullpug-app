"""Daily Bullpug Drop — one AI-generated Neuko-universe image rotated every UTC day.

Cached in MongoDB so we only generate ONCE per day no matter how many users
request it; an in-process asyncio lock prevents thundering-herd races on the
first call of the day.
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict

from emergentintegrations.llm.chat import LlmChat, UserMessage

from utils.database import db

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# (theme_label, scene_prompt) — keep prompts evocative, on-canon, no text/logos.
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
    ("Defenders of Newpug", "A team of Bullpughans defending Newpug City from shadowy MITER-Corp surveillance drones, holographic shields up"),
    ("The Address", "Bullpug giving a speech to a vast crowd of Bullpughans, holographic stars and barks of prosperity overhead"),
]

_BULLPUG_STYLE_SUFFIX = (
    "Cinematic, hyperdetailed digital art in the Bullpug / Neuko universe aesthetic. "
    "Vivid neon-on-dark color palette with mint green (#00FFA3), magenta (#D946EF), "
    "and gold (#FFD700) accents against deep midnight backgrounds. No readable text, "
    "no logos, no watermarks. Wide cinematic composition."
)

# Per-date asyncio locks so concurrent first-callers don't all trigger an LLM call.
_generation_locks: Dict[str, asyncio.Lock] = {}
_meta_lock = asyncio.Lock()


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _select_theme_for(date_utc: str):
    """Deterministically pick today's theme from the date string."""
    h = int(hashlib.sha256(date_utc.encode()).hexdigest(), 16)
    idx = h % len(THEMED_DROPS)
    return idx, THEMED_DROPS[idx]


async def _lock_for(date_utc: str) -> asyncio.Lock:
    async with _meta_lock:
        lock = _generation_locks.get(date_utc)
        if lock is None:
            lock = asyncio.Lock()
            _generation_locks[date_utc] = lock
        return lock


async def get_todays_drop() -> Optional[Dict]:
    """Return today's drop dict, generating it if no cached row exists."""
    date_utc = _today_utc()

    # Fast path — check cache without acquiring any lock.
    cached = await db.daily_drops.find_one({"date_utc": date_utc}, {"_id": 0})
    if cached:
        return cached

    if not EMERGENT_LLM_KEY:
        logger.warning("EMERGENT_LLM_KEY missing — cannot generate daily drop")
        return None

    lock = await _lock_for(date_utc)
    async with lock:
        # Re-check after acquiring the lock — another coroutine may have generated.
        cached = await db.daily_drops.find_one({"date_utc": date_utc}, {"_id": 0})
        if cached:
            return cached

        idx, (theme, scene) = _select_theme_for(date_utc)
        full_prompt = f"{scene}. {_BULLPUG_STYLE_SUFFIX}"
        try:
            chat = (
                LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"daily-drop-{date_utc}",
                    system_message=(
                        "You are Bullpug, the cosmic guardian. Generate ONE cinematic image "
                        "matching the user's scene description in the Neuko universe style."
                    ),
                )
                .with_model("gemini", "gemini-3.1-flash-image-preview")
                .with_params(modalities=["image", "text"])
            )
            msg = UserMessage(text=full_prompt)
            text, images = await chat.send_message_multimodal_response(msg)
            if not images:
                logger.error("Daily drop returned no images")
                return None
            img = images[0]
            mime = img.get("mime_type") or "image/png"
            data = img.get("data") or ""
            drop = {
                "date_utc": date_utc,
                "theme": theme,
                "scene": scene,
                "theme_index": idx,
                "image_base64": f"data:{mime};base64,{data}",
                "caption": (text or "").strip() or None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.daily_drops.update_one(
                {"date_utc": date_utc},
                {"$setOnInsert": drop},
                upsert=True,
            )
            # Re-fetch (returns the persisted row whichever coroutine wrote first)
            return await db.daily_drops.find_one({"date_utc": date_utc}, {"_id": 0})
        except Exception:
            logger.exception("Daily drop generation failed")
            return None
