"""Shareable Archive card generator — 1200×630 PNG (X/Twitter OG format).

Server-side so link previews on X, Discord, Telegram etc. all resolve
to a rendered card image instead of a blank preview. Uses PIL and the
Liberation font family shipped with the container image.

Contents are intentionally SPOILER-FREE — every renderable element is
about the wallet's own progress, never about specific lore entries:
  • rank badge (SignalGlyph in the wallet's rank colour)
  • rank title (only when earned; otherwise "Unranked")
  • progress count ("X of N discovered")
  • AI-generated abstract cosmic art unique to this wallet
The AI art is cached per (wallet, rank, unlocked_count) so re-shares at
the same progress point don't hit the LLM, but any change to rank or
count regenerates.

Called from `routers/archive.py`'s POST /share endpoint.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from services import archive_achievements
from utils.database import db

logger = logging.getLogger(__name__)

W, H = 1200, 630
BG = (5, 7, 18)
CARD_BG = (10, 15, 30)

RANK_COLORS = {
    archive_achievements.RANK_SEEKER: (0, 255, 163),
    archive_achievements.RANK_ARCHIVIST: (180, 124, 255),
    archive_achievements.RANK_KEEPERS_CIRCLE: (245, 211, 0),
    None: (150, 160, 190),
}

RANK_HEADLINE = {
    archive_achievements.RANK_SEEKER:
        "Seeker rank in the Bullpug Archive",
    archive_achievements.RANK_ARCHIVIST:
        "Archivist rank in the Bullpug Archive",
    archive_achievements.RANK_KEEPERS_CIRCLE:
        "Keeper's Circle · the full record",
    None: "Building the Archive record",
}

# ── Font loader ─────────────────────────────────────────────────────────
_LIB_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
_LIB_SANS_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
_LIB_SANS_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"
_LIB_MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"

_SHARE_ART_COLLECTION = "share_card_art"


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ── SignalGlyph drawing ────────────────────────────────────────────────
def _draw_signal_glyph(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
                       color: tuple[int, int, int]):
    """Chain-link ring + ember centre. Rendered flat (no glow) at 1200×630."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (255,), width=3)
    draw.ellipse((cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8),
                 outline=color + (140,), width=1)
    er = max(6, r // 4)
    draw.ellipse((cx - er, cy - er, cx + er, cy + er), fill=color + (255,))
    for dx, dy in ((0, -r), (r, 0), (0, r), (-r, 0)):
        draw.ellipse((cx + dx - 3, cy + dy - 3, cx + dx + 3, cy + dy + 3),
                     fill=color + (255,))


def _draw_grid(base: Image.Image, color=(0, 255, 163, 18), step=48):
    """Faint grid overlay, radial-masked so edges fade out."""
    grid = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, base.size[0], step):
        gd.line([(x, 0), (x, base.size[1])], fill=color, width=1)
    for y in range(0, base.size[1], step):
        gd.line([(0, y), (base.size[0], y)], fill=color, width=1)
    mask = Image.new("L", base.size, 0)
    md = ImageDraw.Draw(mask)
    cx, cy = base.size[0] // 2, base.size[1] // 2
    for i in range(50, 0, -1):
        radius = int(min(base.size) * (i / 50) * 0.6)
        alpha = int(255 * (i / 50))
        md.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                   fill=alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(30))
    grid.putalpha(Image.eval(mask, lambda a: min(a, 255)))
    base.alpha_composite(grid)


# ── AI art generation + cache ──────────────────────────────────────────
def _share_art_prompt(rank: Optional[str], unlocked_count: int, total: int) -> str:
    """Compose an abstract cosmic prompt from rank + progress.

    Deliberately spoiler-free — no character names, no lore entries, no
    scene subjects. Just an abstract cosmic mood that visualises how
    far the wallet has come.
    """
    percent = int(round((unlocked_count / max(1, total)) * 100))
    if rank == archive_achievements.RANK_KEEPERS_CIRCLE:
        mood = (
            "a golden constellation forming an intricate chain-link mandala, "
            "warm amber and gold light bleeding across a deep indigo starfield, "
            "sense of completion and quiet mastery, sacred geometry"
        )
    elif rank == archive_achievements.RANK_ARCHIVIST:
        mood = (
            "violet nebulae weaving through a dense star field, luminous purple "
            "and magenta ribbons braiding across cosmic dust, sense of depth "
            "and hidden knowledge, layered translucent forms"
        )
    elif rank == archive_achievements.RANK_SEEKER:
        mood = (
            "an aurora of cyan and teal light rippling across a dark cosmic "
            "horizon, first threshold crossed, sense of arrival and wonder, "
            "clean atmospheric glow"
        )
    else:
        mood = (
            "faint cosmic dust drifting in a deep indigo void, a single distant "
            "signal pulsing softly, sense of anticipation and quiet beginning, "
            "sparse and atmospheric"
        )
    variation = (
        f"Composition seeded by progress level {percent}% — vary particle "
        "density and light intensity accordingly."
    )
    return (
        f"{mood}. {variation} Abstract cosmic art, cinematic hyperdetailed "
        "digital painting, single cohesive scene, no characters, no "
        "creatures, no figures, no buildings, no logos, no text or "
        "typography of any kind. Wide 1.9:1 aspect. Deep space palette "
        "with atmospheric depth."
    )


async def _load_cached_share_art(
    wallet: str, rank: Optional[str], unlocked_count: int
) -> Optional[bytes]:
    """Return cached PNG bytes for this exact (wallet, rank, count) or None."""
    try:
        doc = await db[_SHARE_ART_COLLECTION].find_one(
            {"wallet": wallet, "rank": rank, "unlocked_count": unlocked_count}
        )
        if not doc or not doc.get("image_base64"):
            return None
        return base64.b64decode(doc["image_base64"])
    except Exception as e:
        logger.debug("share art cache lookup failed: %s", e)
        return None


async def _persist_share_art(
    wallet: str, rank: Optional[str], unlocked_count: int, image_b64: str
):
    try:
        await db[_SHARE_ART_COLLECTION].update_one(
            {"wallet": wallet, "rank": rank, "unlocked_count": unlocked_count},
            {"$set": {
                "wallet": wallet,
                "rank": rank,
                "unlocked_count": unlocked_count,
                "image_base64": image_b64,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.warning("share art cache write failed: %s", e)


async def _generate_share_art(
    wallet: str, rank: Optional[str], unlocked_count: int, total: int
) -> Optional[bytes]:
    """Generate a unique cosmic image via Gemini nano banana.

    Returns raw PNG bytes on success, None on any failure (network,
    model refusal, missing key). The card renderer falls back to a
    procedural gradient panel in that case — never blocks the share.
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        logger.warning("share art: SDK import failed: %s", e)
        return None

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.info("share art: EMERGENT_LLM_KEY missing — falling back to procedural panel")
        return None

    prompt = _share_art_prompt(rank, unlocked_count, total)
    try:
        chat = (
            LlmChat(
                api_key=api_key,
                session_id=f"share-art-{wallet}-{unlocked_count}",
                system_message=(
                    "You produce abstract cosmic art for the Bullpug Archive "
                    "share-card slot. NEVER include text, letters, words, "
                    "captions, typography, characters, creatures, figures, "
                    "buildings, or logos of any kind. Only abstract cosmic "
                    "atmosphere — nebulae, starfields, aurora, particles."
                ),
            )
            .with_model("gemini", "gemini-3.1-flash-image-preview")
            .with_params(modalities=["image", "text"])
        )
        _, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
        if not images:
            return None
        b64 = images[0].get("data") or ""
        if not b64:
            return None
        # Persist and return bytes
        await _persist_share_art(wallet, rank, unlocked_count, b64)
        return base64.b64decode(b64)
    except Exception as e:
        logger.warning("share art generation failed: %s", e)
        return None


def _procedural_art_fallback(color: tuple[int, int, int], w: int, h: int) -> Image.Image:
    """Fallback panel if the AI generation is unavailable.

    Deep indigo base + a soft radial glow in the rank colour + a
    scatter of star-like dots. Never blocks a share.
    """
    panel = Image.new("RGBA", (w, h), (5, 7, 18, 255))
    # Radial glow
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = int(w * 0.55), int(h * 0.45)
    for i in range(60, 0, -1):
        r = int(min(w, h) * (i / 60) * 0.55)
        alpha = int(90 * (i / 60) ** 2)
        gd.ellipse((cx - r, cy - r, cx + r, cy + r),
                   fill=color + (alpha,))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    panel.alpha_composite(glow)
    # Star scatter
    import random
    rng = random.Random(sum(color))
    sd = ImageDraw.Draw(panel)
    for _ in range(120):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        r = rng.choice((1, 1, 1, 2))
        a = rng.randint(80, 220)
        sd.ellipse((x, y, x + r, y + r), fill=(230, 240, 255, a))
    return panel


async def _resolve_share_art(
    wallet: str, rank: Optional[str], unlocked_count: int, total: int,
    color: tuple[int, int, int], panel_size: tuple[int, int]
) -> Image.Image:
    """Return a PIL image sized to `panel_size` for the right-hand slot.

    Order of preference: cached AI → freshly generated AI → procedural fallback.
    """
    pw, ph = panel_size
    raw = await _load_cached_share_art(wallet, rank, unlocked_count)
    if not raw:
        raw = await _generate_share_art(wallet, rank, unlocked_count, total)
    if raw:
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
            # Cover-fit crop so the panel is always filled
            src_ratio = img.size[0] / img.size[1]
            dst_ratio = pw / ph
            if src_ratio > dst_ratio:
                new_h = ph
                new_w = int(ph * src_ratio)
            else:
                new_w = pw
                new_h = int(pw / src_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - pw) // 2
            top = (new_h - ph) // 2
            return img.crop((left, top, left + pw, top + ph))
        except Exception as e:
            logger.warning("share art decode failed, falling back: %s", e)
    return _procedural_art_fallback(color, pw, ph)


# ── Public generator ───────────────────────────────────────────────────
async def generate_share_card(wallet_address: str) -> Optional[str]:
    """Render the shareable Archive card for a wallet. Returns base64
    string (no data-URL prefix) or None on failure.

    The card is intentionally spoiler-free — no entry names, no
    excerpts, no lore details of any kind.
    """
    if not wallet_address:
        return None
    try:
        rank_snap = await archive_achievements.get_rank_snapshot(wallet_address)
    except Exception as e:
        logger.warning("share card data fetch failed: %s", e)
        return None

    rank = rank_snap.get("rank")
    rank_title = rank_snap.get("rank_title") or "Unranked"
    unlocked_count = rank_snap.get("unlocked_count", 0)
    total = rank_snap.get("total", archive_achievements.TOTAL_ENTRIES)
    color = RANK_COLORS.get(rank, RANK_COLORS[None])
    headline = RANK_HEADLINE.get(rank, RANK_HEADLINE[None])

    # ── Base canvas + ambient background ─────────────────────────────
    img = Image.new("RGBA", (W, H), BG + (255,))
    _draw_grid(img)
    draw = ImageDraw.Draw(img, "RGBA")

    # Vertical accent stripe on the left
    draw.rectangle((0, 0, 6, H), fill=color + (255,))

    # ── Top-left brand ───────────────────────────────────────────────
    logo_font_bold = _font(_LIB_SANS, 30)
    draw.text((60, 52), "BULL", font=logo_font_bold, fill=(255, 255, 255, 255))
    bull_w = int(draw.textlength("BULL", font=logo_font_bold))
    draw.text((60 + bull_w, 52), "PUG", font=logo_font_bold, fill=color + (255,))
    tag_font = _font(_LIB_MONO, 11)
    draw.text((60, 92), "THE  ARCHIVE  ·  KEEPER  STATION  001",
              font=tag_font, fill=(color[0], color[1], color[2], 180))

    # ── Rank badge (centre-left) ────────────────────────────────────
    badge_cx, badge_cy = 200, H // 2 + 20
    _draw_signal_glyph(draw, badge_cx, badge_cy, 90, color)

    # ── Headline block (right of badge) ─────────────────────────────
    kicker_font = _font(_LIB_MONO, 14)
    draw.text((330, 220), "ARCHIVE RANK", font=kicker_font,
              fill=(color[0], color[1], color[2], 200))

    title_font = _font(_LIB_SANS, 58)
    # Auto-shrink so long titles ("Keeper's Circle") never clip the art
    # panel on the right. Available width from x=330 to panel start
    # (x=700) with a 20px gutter = 350px.
    while draw.textlength(rank_title, font=title_font) > 350 and title_font.size > 34:
        title_font = _font(_LIB_SANS, title_font.size - 4)
    draw.text((330, 250), rank_title, font=title_font, fill=color + (255,))

    subhead_font = _font(_LIB_SANS_REG, 22)
    subhead_text = f"{unlocked_count} of {total} discovered"
    draw.text((330, 328), subhead_text, font=subhead_font,
              fill=(200, 210, 230, 255))

    line_font = _font(_LIB_SANS_REG, 18)
    _wrap_and_draw(draw, headline, 330, 372, 340, line_font,
                   (170, 180, 210, 255), line_h=24, max_lines=3)

    # ── AI-generated art panel (bottom-right) ────────────────────────
    px, py, pw, ph = 700, 200, 440, 300
    art = await _resolve_share_art(
        wallet_address, rank, unlocked_count, total, color, (pw, ph)
    )
    # Rounded-corner mask so the panel matches the previous card's
    # visual weight (14px radius rounded rectangle).
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw, ph), radius=14, fill=255)
    img.paste(art, (px, py), mask)
    # Thin border in the rank colour
    draw.rounded_rectangle((px, py, px + pw, py + ph), radius=14,
                           outline=(color[0], color[1], color[2], 120), width=1)
    # Left tier stripe in the rank colour (same accent the old card had).
    # Drawn directly on the main canvas so we don't smash the AI art's
    # alpha by re-using a separate mask.
    draw.rectangle((px, py, px + 3, py + ph), fill=color + (255,))

    # ── Footer bar ──────────────────────────────────────────────────
    foot_font = _font(_LIB_MONO, 12)
    draw.text((60, H - 44), "ASK  TINKERPUG  ·  bullpug.com/archive",
              font=foot_font, fill=(color[0], color[1], color[2], 220))
    _draw_signal_glyph(draw, W - 60, H - 40, 14, color)

    # ── Encode ──────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _wrap_and_draw(draw, text: str, x: int, y: int, max_w: int,
                   font: ImageFont.FreeTypeFont, fill, line_h: int = 22,
                   max_lines: int = 8):
    """Naive word-wrap. Good enough for the short strings this card renders."""
    words = (text or "").split()
    line = ""
    lines: list[str] = []
    for w in words:
        candidate = (line + " " + w).strip()
        if draw.textlength(candidate, font=font) <= max_w:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = w
        if len(lines) >= max_lines:
            break
    if line and len(lines) < max_lines:
        lines.append(line)
    for i, ln in enumerate(lines):
        draw.text((x, y + i * line_h), ln, font=font, fill=fill)
