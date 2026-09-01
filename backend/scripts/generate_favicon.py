"""
Generate Bullpug favicons from the SignalGlyph geometry.

Mirrors `/app/frontend/src/components/RankBadge.jsx` (keeper's-circle
tint — the same gold glyph used on the Origins page ActIPlaceholder):

  • Radial gold glow background
  • Outer chain-link ring
  • Inner chain-link ring (thinner, dimmer)
  • Ember centre (28% of canvas, solid gold)
  • Four small chain-link nubs at N/S/E/W cardinals

Dark indigo background #0d0f1a matches the site aesthetic.

Emits:
  • public/favicon-16x16.png
  • public/favicon-32x32.png
  • public/apple-touch-icon.png (180x180)
  • public/favicon.ico (multi-size: 16, 32, 48)
"""

from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

OUT_DIR = Path("/app/frontend/public")
OUT_DIR.mkdir(exist_ok=True)

BG        = (13, 15, 26, 255)       # #0d0f1a
GOLD_CORE = (245, 211, 0, 255)      # #F5D300
GOLD_RING = (245, 211, 0, 165)      # ring @ 65% alpha
GOLD_GLOW = (245, 211, 0, 100)      # halo @ 40% alpha


def _draw_signal_glyph(size: int) -> Image.Image:
    """Draw the SignalGlyph at native size (in px). Uses 4x supersampling
    for clean edges then downsamples with LANCZOS — the 16x16 icon
    otherwise gets jaggies on the ring stroke."""
    SS = 4
    W = size * SS
    img = Image.new("RGBA", (W, W), BG)

    # ── Radial gold glow (soft halo behind the ring) ────────────────────
    glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # Layered fill circles with decreasing alpha to fake a radial gradient.
    for pct, alpha in [(0.90, 40), (0.75, 55), (0.60, 70), (0.45, 90)]:
        r = int(W * 0.5 * pct)
        cx = cy = W // 2
        gd.ellipse((cx - r, cy - r, cx + r, cy + r),
                   fill=(245, 211, 0, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(2, W // 20)))
    img = Image.alpha_composite(img, glow)

    d = ImageDraw.Draw(img)
    cx = cy = W // 2

    # ── Outer chain-link ring ───────────────────────────────────────────
    outer_r = int(W * 0.46)
    stroke_outer = max(2, int(W * 0.028))
    d.ellipse((cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r),
              outline=GOLD_RING, width=stroke_outer)

    # ── Inner chain-link ring (55% opacity per RankBadge.jsx) ───────────
    inner_r = int(W * 0.38)
    stroke_inner = max(1, int(W * 0.017))
    ring_dim = (245, 211, 0, 92)  # 55% of GOLD_RING alpha ≈ 92
    d.ellipse((cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
              outline=ring_dim, width=stroke_inner)

    # ── Ember centre (28% of canvas, solid gold with soft glow) ─────────
    ember_r = int(W * 0.14)
    # Underlying glow so the ember pops even at 16px.
    ember_glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    egd = ImageDraw.Draw(ember_glow)
    egd.ellipse((cx - ember_r * 2, cy - ember_r * 2,
                 cx + ember_r * 2, cy + ember_r * 2),
                fill=(245, 211, 0, 90))
    ember_glow = ember_glow.filter(ImageFilter.GaussianBlur(radius=max(2, W // 30)))
    img = Image.alpha_composite(img, ember_glow)
    d = ImageDraw.Draw(img)
    d.ellipse((cx - ember_r, cy - ember_r, cx + ember_r, cy + ember_r),
              fill=GOLD_CORE)

    # ── Four chain-link nubs at N/S/E/W (sit on the outer ring) ─────────
    # RankBadge uses `translateY(-(size/2 - 2))` — i.e. the nub centre
    # is 2px inside the badge edge. In our supersampled canvas this
    # maps to `outer_r + stroke_outer/2` on the ring perimeter.
    nub_r = max(2, int(W * 0.035))
    for angle_deg in (0, 90, 180, 270):
        # N=0deg is straight up per the JSX (`rotate(0) translateY(-r)`).
        # Convert to trig space: N is at angle -90° from +x.
        import math
        rad = math.radians(angle_deg - 90)
        nx = cx + int(outer_r * math.cos(rad))
        ny = cy + int(outer_r * math.sin(rad))
        d.ellipse((nx - nub_r, ny - nub_r, nx + nub_r, ny + nub_r),
                  fill=GOLD_RING)

    return img.resize((size, size), Image.LANCZOS)


def _write_png(size: int, name: str):
    im = _draw_signal_glyph(size).convert("RGBA")
    im.save(OUT_DIR / name, format="PNG", optimize=True)
    print(f"  ✓ {name}  ({size}x{size})")


def main():
    print("Generating Bullpug favicons from SignalGlyph geometry…")
    _write_png(16,  "favicon-16x16.png")
    _write_png(32,  "favicon-32x32.png")
    _write_png(180, "apple-touch-icon.png")

    # Multi-size .ico so Windows / IE / legacy tab UIs pick the sharpest.
    ico_sizes = [(16, 16), (32, 32), (48, 48)]
    base = _draw_signal_glyph(64).convert("RGBA")
    base.save(OUT_DIR / "favicon.ico", format="ICO", sizes=ico_sizes)
    print(f"  ✓ favicon.ico  (multi: {ico_sizes})")

    print("Done → /app/frontend/public/")


if __name__ == "__main__":
    main()
