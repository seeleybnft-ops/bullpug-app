"""One-shot Origins Trailer generator.

Creates a 15-second vertical (720x1280) MP4 stitching the 3 lore hero images
together with a Ken Burns zoom-in/pan effect and crossfade transitions.
Audio: a subtle 152 BPM heartbeat track (canonical "G-304 modulation"
reference from the lore) layered with a low ambient drone.

Output: /app/frontend/public/lore/origins-trailer.{mp4,webm}
Run once:  python3 /app/backend/scripts/generate_origins_trailer.py
"""

import subprocess
import tempfile
import wave
from pathlib import Path
import numpy as np
from PIL import Image
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

SR = 48000                 # audio sample rate (Opus's preferred rate)
BPM = 152                  # canonical "G-304 modulation" rhythm

SCENES = [
    {"file": "newpug-city.png",      "zoom_start": 1.0,  "zoom_end": 1.15, "pan": "right"},
    {"file": "snout-scanner.png",    "zoom_start": 1.15, "zoom_end": 1.0,  "pan": "center"},
    {"file": "festival-of-barks.png","zoom_start": 1.0,  "zoom_end": 1.15, "pan": "left"},
]


def synthesize_heartbeat_audio() -> Path:
    """Synthesise a 15s heartbeat + ambient drone soundtrack. Returns path to WAV."""
    n_samples = int(SR * TOTAL_SECS)
    audio = np.zeros(n_samples, dtype=np.float32)

    # ---- Heartbeat pulses (lub-dub pattern @ 152 BPM) ----
    beat_period = 60.0 / BPM           # ~0.395s between heartbeats
    pulse_dur = 0.22                   # decay envelope duration per pulse
    pulse_n = int(pulse_dur * SR)
    pt = np.linspace(0, pulse_dur, pulse_n, dtype=np.float32)

    def kick(freq_start, freq_end, amp):
        # Pitch glides down from freq_start to freq_end with exp-decay envelope.
        env = np.exp(-pt * 14.0)
        freq = freq_start + (freq_end - freq_start) * (1 - np.exp(-pt * 25.0))
        phase = 2 * np.pi * np.cumsum(freq) / SR
        return np.sin(phase, dtype=np.float32) * env * amp

    lub = kick(95, 55, 1.0)             # deeper, fuller first beat
    dub = kick(80, 45, 0.65)            # softer second beat
    lub_dub_gap = 0.16

    t = 0.0
    while t + pulse_dur < TOTAL_SECS:
        i = int(t * SR)
        end = min(i + pulse_n, n_samples)
        audio[i:end] += lub[: end - i]
        j = int((t + lub_dub_gap) * SR)
        end2 = min(j + pulse_n, n_samples)
        if j < n_samples:
            audio[j:end2] += dub[: end2 - j]
        t += beat_period

    # ---- Ambient drone (filtered noise + slow sine) ----
    rng = np.random.default_rng(seed=42)
    noise = rng.standard_normal(n_samples).astype(np.float32) * 0.08
    # Simple single-pole lowpass cascade (no scipy needed)
    alpha = 0.02
    lp = np.zeros_like(noise)
    state = 0.0
    for k in range(n_samples):
        state = state + alpha * (noise[k] - state)
        lp[k] = state
    drone_t = np.linspace(0, TOTAL_SECS, n_samples, dtype=np.float32)
    drone = (
        0.10 * np.sin(2 * np.pi * 55 * drone_t)         # sub
        + 0.05 * np.sin(2 * np.pi * 110 * drone_t)      # octave
    ).astype(np.float32)
    ambient = (lp * 3.5 + drone) * 0.6

    # ---- Volume envelope: silent → fade-in → cresc at fireworks → fade-out ----
    env = np.ones(n_samples, dtype=np.float32)
    # Silent for first 1.5s, fade-in over 2s to 0.55
    fade_in_start = int(1.5 * SR)
    fade_in_end = int(3.5 * SR)
    env[:fade_in_start] = 0.0
    env[fade_in_start:fade_in_end] = np.linspace(0.0, 0.55, fade_in_end - fade_in_start)
    # Hold at 0.55 until the festival scene (~10s), then crescendo to 0.9 by 13.5s
    env[fade_in_end:int(10 * SR)] = 0.55
    cresc_start = int(10 * SR)
    cresc_end = int(13.5 * SR)
    env[cresc_start:cresc_end] = np.linspace(0.55, 0.9, cresc_end - cresc_start)
    # Fade out the last 1.5s
    fade_out_start = int(13.5 * SR)
    env[fade_out_start:] = np.linspace(0.9, 0.0, n_samples - fade_out_start)

    mixed = (audio * 0.7 + ambient * 0.35) * env

    # Normalise to avoid clipping
    peak = float(np.max(np.abs(mixed)))
    if peak > 0:
        mixed = mixed / peak * 0.82

    # Write WAV (16-bit PCM mono)
    wav_path = Path(tempfile.gettempdir()) / "origins_trailer_audio.wav"
    pcm = (mixed * 32767).astype(np.int16).tobytes()
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm)
    print(f"[audio  ] synthesised {wav_path} ({len(pcm) // 1024} KB)")
    return wav_path


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

    audio_path = synthesize_heartbeat_audio()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    # Render frames once → tee into TWO encoders (MP4 H.264 + WebM VP9) for max
    # browser compatibility. The MP4 is the canonical asset; WebM is the fallback
    # for browsers (and Chromium headless builds) without H.264 licensing.
    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-i", str(audio_path),
        # MP4 (H.264 Constrained Baseline + AAC for max compatibility)
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "baseline", "-level", "3.1",
        "-crf", "23", "-preset", "medium",
        "-c:a", "aac", "-b:a", "96k", "-ar", str(SR),
        "-movflags", "+faststart",
        "-shortest",
        str(OUT),
        # WebM (VP9 + Opus — universally supported by Chromium without licensed codecs)
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
        "-b:v", "0", "-crf", "32", "-row-mt", "1",
        "-deadline", "good", "-cpu-used", "4",
        "-c:a", "libopus", "-b:a", "96k", "-ar", str(SR),
        "-shortest",
        str(OUT_WEBM),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"[trailer] ffmpeg cmd: {' '.join(cmd[:8])} ... ({len(cmd)} args)")

    crossfade_frames = int(CROSSFADE_SECS * FPS)
    scene_frames = SCENE_SECS * FPS

    try:
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
    except BrokenPipeError:
        # ffmpeg exited early — capture its stderr to find out why
        pass

    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass
    stderr = proc.stderr.read().decode(errors="ignore")
    rc = proc.wait()
    if rc != 0:
        print("[trailer] ffmpeg stderr:\n" + stderr[-3000:])
        raise SystemExit(f"ffmpeg exited with {rc}")
    size_kb = OUT.stat().st_size // 1024
    webm_kb = OUT_WEBM.stat().st_size // 1024 if OUT_WEBM.exists() else 0
    print(f"[trailer] ✓ wrote {OUT} ({size_kb} KB) and {OUT_WEBM} ({webm_kb} KB)")


if __name__ == "__main__":
    main()
