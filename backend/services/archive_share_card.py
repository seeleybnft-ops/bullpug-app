"""Shareable Archive card generator — 1200×630 PNG (X/Twitter OG format).

Server-side so link previews on X, Discord, Telegram etc. all resolve
to a rendered card image instead of a blank preview. Uses PIL and the
Liberation font family shipped with the container image.

Called from `routers/archive.py`'s POST /share endpoint.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from services import archive_achievements

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


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ── SignalGlyph drawing ────────────────────────────────────────────────
def _draw_signal_glyph(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
                       color: tuple[int, int, int]):
    """Chain-link ring + ember centre. Rendered flat (no glow) at 1200×630."""
    # Outer ring
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (255,), width=3)
    # Inner ring
    draw.ellipse((cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8),
                 outline=color + (140,), width=1)
    # Ember centre
    er = max(6, r // 4)
    draw.ellipse((cx - er, cy - er, cx + er, cy + er), fill=color + (255,))
    # Cardinal nubs
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
    # Radial mask
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


# ── Public generator ───────────────────────────────────────────────────
async def generate_share_card(wallet_address: str) -> Optional[str]:
    """Render the shareable Archive card for a wallet. Returns base64
    string (no data-URL prefix) or None on failure."""
    if not wallet_address:
        return None
    try:
        rank_snap = await archive_achievements.get_rank_snapshot(wallet_address)
        unlocks = await archive_achievements.get_unlocks(wallet_address)
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
    logo_font = _font(_LIB_SANS, 30)
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
    # Auto-shrink so long titles ("Keeper's Circle") never clip the
    # featured card on the right. Available width from x=330 to card
    # start (x=700) with a 20px gutter = 350px.
    while draw.textlength(rank_title, font=title_font) > 350 and title_font.size > 34:
        title_font = _font(_LIB_SANS, title_font.size - 4)
    draw.text((330, 250), rank_title, font=title_font, fill=color + (255,))

    subhead_font = _font(_LIB_SANS_REG, 22)
    subhead_text = f"{unlocked_count} of {total} entries discovered"
    draw.text((330, 328), subhead_text, font=subhead_font,
              fill=(200, 210, 230, 255))

    line_font = _font(_LIB_SANS_REG, 18)
    _wrap_and_draw(draw, headline, 330, 372, 340, line_font,
                   (170, 180, 210, 255), line_h=24, max_lines=3)

    # ── Featured lore card (bottom-right rectangle) ─────────────────
    _draw_featured_entry(draw, unlocks, color)

    # ── Footer bar ──────────────────────────────────────────────────
    foot_font = _font(_LIB_MONO, 12)
    draw.text((60, H - 44), "ASK  TINKERPUG  ·  bullpug.com/archive",
              font=foot_font, fill=(color[0], color[1], color[2], 220))
    # Small SignalGlyph mark bottom-right
    _draw_signal_glyph(draw, W - 60, H - 40, 14, color)

    # ── Encode ──────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _draw_featured_entry(draw: ImageDraw.ImageDraw, unlocks: list, color: tuple):
    """Featured card in the lower-right — most recent Tier 2 or 3 unlock,
    else most recent Tier 1, else a placeholder inviting them to start."""
    x, y, cw, ch = 700, 200, 440, 300

    # Card body
    draw.rounded_rectangle((x, y, x + cw, y + ch), radius=14,
                           fill=CARD_BG + (255,),
                           outline=(color[0], color[1], color[2], 90), width=1)
    # Left tier stripe (uses rank/tier colour of the featured entry itself
    # when we have one, otherwise the rank colour)
    featured = None
    for tier_pref in (3, 2, 1):
        for u in unlocks:
            if u.get("entry_tier") == tier_pref:
                featured = u
                break
        if featured:
            break

    tier_color = color
    if featured:
        t = featured.get("entry_tier")
        if t == 1:
            tier_color = (0, 255, 163)
        elif t == 2:
            tier_color = (180, 124, 255)
        elif t == 3:
            tier_color = (245, 211, 0)

    draw.rectangle((x, y, x + 3, y + ch), fill=tier_color + (255,))

    kf = _font(_LIB_MONO, 11)
    body_font = _font(_LIB_SANS_REG, 15)
    name_font = _font(_LIB_SANS, 26)
    italic_font = _font(_LIB_SANS_ITALIC, 15)

    if featured:
        tier_label = {1: "TIER I · SEEKER", 2: "TIER II · ARCHIVIST",
                      3: "TIER III · KEEPER'S CIRCLE"}[featured.get("entry_tier", 1)]
        draw.text((x + 24, y + 22), tier_label, font=kf,
                  fill=tier_color + (255,))
        # Entry name — resolve from master list for the display name
        slug = featured.get("entry_id")
        name = slug or "Archive record"
        for e in archive_achievements.MASTER_ENTRIES:
            if e["slug"] == slug:
                name = e["name"]
                break
        _wrap_and_draw(draw, name, x + 24, y + 48, cw - 48, name_font,
                       (255, 255, 255, 255), line_h=32, max_lines=2)
        excerpt = (featured.get("tinkerpug_excerpt") or "").strip()
        if excerpt:
            _wrap_and_draw(draw, excerpt, x + 24, y + 130, cw - 48, body_font,
                           (200, 210, 230, 255), line_h=22, max_lines=6)
    else:
        draw.text((x + 24, y + 22), "NEW SIGNAL DETECTED", font=kf,
                  fill=tier_color + (200,))
        draw.text((x + 24, y + 48), "The Archive is open.", font=name_font,
                  fill=(255, 255, 255, 255))
        _wrap_and_draw(draw,
            "Ask Tinkerpug about Bullpug's origin, the Guardians, or the "
            "Signal in the Noise — every substantive answer files a new "
            "entry in your Ledger.",
            x + 24, y + 100, cw - 48, italic_font,
            (180, 190, 210, 255), line_h=22, max_lines=6)


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
