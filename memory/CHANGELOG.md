# Bullpug — Changelog

> PRD.md is large and historical. This file tracks recent feature additions / bug fixes per session.

---

## 2026-05-13 (b) — 3D skins + higher-quality assets + Moon Cheese

User asks:
1. 3D model every skin from the Skin Store and reflect on the in-game pug.
2. Improve quality of in-game models to better match the 2D legend.
3. The collectible is **Moon Cheese**, not generic coins.

### Implemented
- **Skin → 3D pipeline**: added a `SKIN_VISUALS` map keyed by skin ID
  (`default`, `ethereal`, `diamond`, `gold`, `silver`, `heatmap`,
  `radioactive`, `zombie`, `water`, `fire`, `robot`, `skeletal`) returning
  `{body, belly, dark, metalness, roughness, emissive, emissiveIntensity,
  extra}`. `<Bullpug skinId={...} />` applies them to body / head / jowls /
  legs / tail + recolors muzzle and ears. Eyes pick up a subtle skin-glow
  emissive too.
- **Per-skin extras**:
  - `ethereal` → glowing halo ring above the head.
  - `radioactive` / `fire` → drei `<Sparkles />` aura around the pug.
  - `robot` → small antenna sticking out the top of the head.
  - `skeletal` → faint rib hint behind the head.
- `SpeedRunGame.js` and the standalone `/game/3d` both pass the active
  `currentSkinId` / `localStorage.bullpugSkin` to the scene, so equipping a
  skin in the existing Skin Store instantly applies in the new 3D mode.
- **Moon Cheese**: removed the cylinder `Coin` component, added
  `<MoonCheese />` — flattened sphere body with bronze rim band, three
  crater dimples, soft yellow halo ring, +25 score per pickup (matches the
  2D guide's "Collect for +25 points"). HUD label switched from "Coins"
  to "Moon Cheese · 🥮".
- **Improved obstacles** (aligned with the in-app legend):
  - `meteor` (was `asteroid`) → flat-shaded icosahedron + emissive lava
    cracks + spinning heat halo.
  - `debris` (was `crystal`) → cluster of three rotated octahedra with a
    hot-orange exhaust `<pointLight>`.
  - `ring` → thicker torus + inner glow disk + downward beam cone hint.

### Files touched
- `/app/frontend/src/pages/Phase1Runner3D.js` — added `SKIN_VISUALS`,
  `skinId` prop pipeline (`CosmicRunner3DScene` → `World` → `Bullpug`),
  replaced `Coin` with `MoonCheese`, redesigned all three obstacles,
  +25 score per cheese, HUD label changes, default-skin lookup via
  `localStorage.bullpugSkin`.
- `/app/frontend/src/pages/SpeedRunGame.js` — pass `skinId={currentSkinId}`
  into the embedded scene so the Skin Store selection drives the model.

### Verification
- Visual smoke-tested 5 skins via `localStorage.bullpugSkin` →
  `default / gold / radioactive / skeletal / ethereal` — each pug body
  re-materialised with the correct colors, emissives and extras
  (ethereal halo visible, skeletal bone-white, radioactive glowing green).
- Score row now reads "Moon Cheese N" with the 🥮 icon in the standalone
  HUD; SpeedRunGame's existing "Moon Cheese 0" counter ticks from the
  same source.
- Frontend lint clean on both files.

---

## 2026-05-13 (a) — Cosmic Runner 3D bugfix + panel restoration

(Preserved — see prior entry.)

---

## 2026-05-12 — Cosmic Runner 3D · Phase 1 polish + Phase 2 enhancements

(Preserved.)
