# Bullpug — Changelog

## 2026-05-13 (c) — Real skeleton model + brighter debris

User feedback:
- "Boulders are too dark and cannot be seen properly. make them more illuminated please."
- "The skins are actual themes — the skeleton Bullpug should be a real skeleton."

### Implemented
- **`SkeletonBody` sub-component** for `skinId === 'skeletal'` (Phantom skin).
  Verified the 2D `skeletal_cutout.png` is a fully rendered skeleton; the
  3D model now matches:
  - Bull-horned **skull** with brow ridge, dark eye sockets + phantom cyan
    eye glow, nasal cavity, upper + lower jaw, four small teeth, bony stub
    ears.
  - **Spine** of 7 vertebrae spheres from skull to tail.
  - **Ribcage** of 5 curved half-torus ribs hanging off the spine + a
    sternum block.
  - **Shoulder & pelvis** bony plates.
  - **Leg bones** — each leg is hip joint + upper bone + knee + lower
    bone + paw sphere (refs preserved so the existing run-cycle still
    animates them).
  - **Curly tail** of 5 small vertebrae spheres.
  - Faint cool-blue phantom point light for atmosphere.
- **Brighter debris obstacle**:
  - Shard base colours lifted to `#C7D0DE → #E1E8F2 → #F2F6FC` (warm-tinted
    near-whites) with emissive intensity 0.4 – 0.55.
  - Replaced the single dim 0.4-intensity point light with **two**:
    warm orange 1.3 + cool blue 0.7 + a 0.5-opacity orange halo ring.
- **Brighter meteor** (smaller bump): rock colour lifted slightly,
  emissive intensity raised, added a 0.9-intensity orange point light and
  bumped halo opacity from 0.35 → 0.5.

### Files touched
- `/app/frontend/src/pages/Phase1Runner3D.js` — added `SkeletonBody`,
  branch in `Bullpug` so `skinId === 'skeletal'` renders the skeleton
  instead of the fleshy body, brighter `meteor` + `debris` materials and
  lighting.

### Verification
- Visual: Phantom +1% Bonus badge + on-screen skeleton with skull, horns,
  visible leg bones, phantom aura.
- Visual: debris cluster now reads as a bright metallic shard pile with a
  warm halo at distance — no longer blends into the dark track.
- Frontend lint clean.

---

## 2026-05-13 (b) — 3D skins + higher-quality assets + Moon Cheese

(Preserved.)

---

## 2026-05-13 (a) — Cosmic Runner 3D bugfix + panel restoration

(Preserved.)

---

## 2026-05-12 — Cosmic Runner 3D · Phase 1 polish + Phase 2 enhancements

(Preserved.)
