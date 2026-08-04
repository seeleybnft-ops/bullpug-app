"""One-shot lore image generator for the Bullpug Origins page.

Run once:  python3 /app/backend/scripts/generate_lore_images.py

Generates three hero images and saves them to /app/frontend/public/lore/.
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure /app/backend on path so emergentintegrations resolves
sys.path.insert(0, "/app/backend")

load_dotenv("/app/backend/.env")

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

OUT_DIR = Path("/app/frontend/public/lore")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "gemini-3.1-flash-image-preview"

IMAGES = [
    {
        "slug": "newpug-city",
        "prompt": (
            "Sweeping wide-angle establishing shot of Newpug City — a vast "
            "futuristic skyline at twilight where the buildings are stylised "
            "to resemble friendly pug heads with curled tails and wide, "
            "welcoming eyes carved into the architecture. Holographic emerald-"
            "green soundwaves ripple through the air like aurora, depicting "
            "'holographic barks'. Neon accents in mint green (#00FFA3), "
            "magenta (#D946EF), and gold (#FFD700) glow against a deep navy / "
            "midnight purple sky filled with stars and a swirling pug-shaped "
            "nebula in the distance. Cinematic, hyperdetailed, sci-fi metropolis, "
            "dramatic lighting, no human characters, no readable text, no logos. "
            "Wide cinematic 16:9 aspect ratio."
        ),
    },
    {
        "slug": "snout-scanner",
        "prompt": (
            "Macro close-up product shot of a futuristic device called a "
            "'Snout Scanner' — a sleek handheld gadget shaped like a stylised "
            "dog snout made of brushed titanium with glowing emerald-green and "
            "cyan circuitry running along the surface. A holographic blockchain "
            "lattice projects from its tip, with tiny golden particles flowing "
            "through it being analysed. Cinematic studio lighting, shallow "
            "depth of field, dark moody background with subtle nebula bokeh, "
            "premium tech-noir aesthetic, hyperdetailed reflections, no text, "
            "no logos. Square-ish 4:3 aspect."
        ),
    },
    {
        "slug": "festival-of-barks",
        "prompt": (
            "Epic celebration scene: the Festival of Barks in Newpug City. "
            "Night sky exploding with fireworks shaped like coins and bones in "
            "gold, mint green and magenta. Giant parade floats sculpted to "
            "look like wedges of glowing 'moon cheese' float down a wide "
            "boulevard. Bullpughan crowds (small silhouetted figures, no faces) "
            "in traditional hooded hodler robes raise their arms in celebration. "
            "The pug-faced skyscrapers of Newpug City rise in the background, "
            "emitting soft holographic green soundwaves. Cinematic wide shot, "
            "joyful but slightly mythical mood, hyperdetailed, sci-fi festival, "
            "no readable text, no logos. Wide cinematic 16:9."
        ),
    },
]


async def generate_one(item):
    slug = item["slug"]
    out_path = OUT_DIR / f"{slug}.png"
    if out_path.exists():
        print(f"[skip] {slug} already exists at {out_path}")
        return

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY missing from environment")

    print(f"[gen ] {slug} …")
    chat = (
        LlmChat(
            api_key=api_key,
            session_id=f"lore-image-{slug}",
            system_message="You are a cinematic concept artist for the sovereign Bullpughan universe — cyberpunk neon city of Newpug City, its Guardians, the PugChain, and the Between."
        )
        .with_model("gemini", MODEL)
        .with_params(modalities=["image", "text"])
    )

    msg = UserMessage(text=item["prompt"])
    text, images = await chat.send_message_multimodal_response(msg)

    if not images:
        raise RuntimeError(f"No image returned for {slug}: {text[:200]}")

    img = images[0]
    image_bytes = base64.b64decode(img["data"])
    out_path.write_bytes(image_bytes)
    print(f"[ok  ] saved {out_path} ({len(image_bytes)//1024} KB)")


async def main():
    for item in IMAGES:
        try:
            await generate_one(item)
        except Exception as e:
            print(f"[err ] {item['slug']}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
