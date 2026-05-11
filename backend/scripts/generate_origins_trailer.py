"""One-shot Origins Trailer generator.

Creates a 15-second vertical (720x1280) MP4 stitching the 3 lore hero images
together with a Ken Burns zoom-in/pan effect and crossfade transitions.

Output: /app/frontend/public/lore/origins-trailer.mp4
Run once:  python3 /app/backend/scripts/generate_origins_trailer.py
"""

import subprocess
from pathlib import Path
from PIL import Image, ImageFilter
import imageio_ffmpeg

LORE_DIR = Path("/app/frontend/public/lore")
OUT = LORE_DIR / "origins-trailer.mp4"
OUT_WEBM = LORE_DIR / "origins-trailer.webm"

W, H = 720, 1280           # vertical 9:16
FPS = 30
SCENE_SECS = 5             # seconds per scene
CROSSFADE_SECS = 0.5
TOTAL_SECS = SCENE_SECS * 3
TOTAL_FRAMES = TOTAL_SECS * FPS

SCENES = [
    {"file": "newpug-city.png",      "zoom_start": 1.0,  "zoom_end": 1.15, "pan": "right"},
    {"file": "snout-scanner.png",    "zoom_start": 1.15, "zoom_end": 1.0,  "pan": "center"},
    {"file": "festival-of-barks.png","zoom_start": 1.0,  "zoom_end": 1.15, "pan": "left"},
]


def prepare_scene_image(path: Path) -> Image.Image:
    """Load + crop to vertical 9:16 aspect, oversized so we can zoom/pan."""
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    target_ratio = W / H               # 0.5625
    src_ratio = iw / ih

    # We want a tall slice from the centre of a wider image. Crop to 9:16
    # at the LARGEST size that fits inside the source.
    if src_ratio > target_ratio:
        # Source is wider — crop horizontal sides
        new_w = int(ih * target_ratio)
        new_h = ih
        left = (iw - new_w) // 2
        top = 0
    else:
        new_w = iw
        new_h = int(iw / target_ratio)
        left = 0
        top = (ih - new_h) // 2

    cropped = img.crop((left, top, left + new_w, top + new_h))
    # Upscale so subsequent zoom-in still looks crisp at output size
    upscaled = cropped.resize((W * 2, H * 2), Image.LANCZOS)
    return upscaled


def render_scene_frame(base: Image.Image, t01: float, zoom_start: float, zoom_end: float, pan: str) -> Image.Image:
    """Return a single W×H RGB frame for fraction t01 ∈ [0,1] of a scene."""
    z = zoom_start + (zoom_end - zoom_start) * t01
    # Base is 2W × 2H, we crop a sub-rect at zoom z, then resize back to W×H
    src_w = int(W * 2 / z)
    src_h = int(H * 2 / z)
    bw, bh = base.size
    # pan: shift the crop window horizontally a bit over time
    if pan == "right":
        x_shift = int((bw - src_w) * (0.4 + 0.2 * t01))
    elif pan == "left":
        x_shift = int((bw - src_w) * (0.6 - 0.2 * t01))
    else:
        x_shift = (bw - src_w) // 2
    y_shift = (bh - src_h) // 2

    crop = base.crop((x_shift, y_shift, x_shift + src_w, y_shift + src_h))
    frame = crop.resize((W, H), Image.LANCZOS)
    return frame


def crossfade(a: Image.Image, b: Image.Image, alpha: float) -> Image.Image:
    return Image.blend(a, b, alpha)


def main():
    scenes = [{**s, "base": prepare_scene_image(LORE_DIR / s["file"])} for s in SCENES]

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    # Render frames once → tee into TWO encoders (MP4 H.264 + WebM VP9) for max
    # browser compatibility. The MP4 is the canonical asset; WebM is the fallback
    # for browsers (and Chromium headless builds) without H.264 licensing.
    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        # MP4 (H.264 Constrained Baseline for max compatibility)
        "-map", "0:v", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "baseline", "-level", "3.0",
        "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        str(OUT),
        # WebM (VP9 — universally supported by Chromium without licensed codecs)
        "-map", "0:v", "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
        "-b:v", "0", "-crf", "32", "-row-mt", "1",
        "-deadline", "good", "-cpu-used", "4",
        str(OUT_WEBM),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    crossfade_frames = int(CROSSFADE_SECS * FPS)
    scene_frames = SCENE_SECS * FPS

    for f in range(TOTAL_FRAMES):
        scene_idx = min(f // scene_frames, len(scenes) - 1)
        frame_in_scene = f - scene_idx * scene_frames
        t01 = frame_in_scene / scene_frames

        s = scenes[scene_idx]
        frame = render_scene_frame(s["base"], t01, s["zoom_start"], s["zoom_end"], s["pan"])

        # Crossfade with the next scene during the LAST crossfade_frames of each scene
        if scene_idx < len(scenes) - 1 and frame_in_scene >= scene_frames - crossfade_frames:
            next_s = scenes[scene_idx + 1]
            blend_alpha = (frame_in_scene - (scene_frames - crossfade_frames)) / crossfade_frames
            next_frame = render_scene_frame(next_s["base"], 0.0, next_s["zoom_start"], next_s["zoom_end"], next_s["pan"])
            frame = crossfade(frame, next_frame, blend_alpha)

        # Fade-in / fade-out on the whole video
        if f < FPS // 2:
            alpha = f / (FPS // 2)
            frame = Image.blend(Image.new("RGB", (W, H), "black"), frame, alpha)
        elif f > TOTAL_FRAMES - FPS // 2:
            alpha = (TOTAL_FRAMES - f) / (FPS // 2)
            frame = Image.blend(Image.new("RGB", (W, H), "black"), frame, alpha)

        proc.stdin.write(frame.tobytes())
        if f % 30 == 0:
            print(f"[trailer] frame {f}/{TOTAL_FRAMES}")

    proc.stdin.close()
    stderr = proc.stderr.read().decode(errors="ignore")
    rc = proc.wait()
    if rc != 0:
        print("[trailer] ffmpeg stderr:\n" + stderr[-1500:])
        raise SystemExit(f"ffmpeg exited with {rc}")
    size_kb = OUT.stat().st_size // 1024
    webm_kb = OUT_WEBM.stat().st_size // 1024 if OUT_WEBM.exists() else 0
    print(f"[trailer] ✓ wrote {OUT} ({size_kb} KB) and {OUT_WEBM} ({webm_kb} KB)")


if __name__ == "__main__":
    main()
