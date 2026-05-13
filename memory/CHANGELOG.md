# Bullpug — Changelog

## 2026-05-13 (d) — All 5 legend obstacles + tight per-type hitboxes

User feedback:
- "Hitbox sizing should be reflective of how big the obstacles. Even when jumping it is hitting the obstacle."
- "Obstacles must remain above ground."
- "Obstacles should be modelled after the game guide" (5 types: Meteor, Space
  Debris, Black Hole, Satellite, Alien Ship).

### Implemented
- **`OBSTACLE_DEFS` table** — single source of truth for all 5 obstacle
  types:
  - `meteor`     → y 0.55, hz 0.45, clear: py≥0.85           (Stage 1)
  - `debris`     → y 0.95, hz 0.55, clear: py≥1.40           (Stage 2)
  - `black_hole` → y 0.06, hz 0.40, clear: py≥0.50           (Stage 3)
  - `satellite`  → y 1.65, hz 0.50, clear: sliding           (Stage 4)
  - `alien_ship` → y 2.00, hz 0.70, clear: sliding           (Stage 5)
  - Spawn pool filtered by current stage (`floor(distance/150)+1`).
- **Bug fix**: the old collision code still checked `o.type === 'asteroid'`
  even though spawning had been renamed to `meteor`, so meteors fell into
  the "always fatal in-lane" branch (i.e. jumping over them did NOT clear
  them). Replaced the whole `if/else if/else` branch with a single
  `OBSTACLE_DEFS[type].clear(py, sliding)` dispatch.
- **Hit window tightened** — replaced the uniform `Math.abs(z) > 1.2`
  early-out with each type's `def.hz` (0.40 – 0.70 instead of 1.2). Player
  is now only at risk while actually adjacent to the obstacle.
- **Spawn Y per type** — `position: new Vector3(LANES[lane], def.y, spawnZ)`
  so every model floats at its own height (no more clipping into the
  track).
- **New 3D models** matching the 2D legend:
  - Meteor: bright fiery icosahedron + hot wireframe + three nested cone
    trails + heat halo + warm point light.
  - Space Debris: faceted dodecahedron + a smaller offset shard + halo +
    cool point light.
  - Black Hole: flat dark center disk + purple accretion ring + outer
    halo + violet point light.
  - Satellite: small box body + two flat solar panels with grid lines +
    dish antenna + red status blinker + purple soft glow.
  - Alien Ship: squashed sphere saucer + dome + green light ring +
    pulsing yellow tractor beam cone + halo + yellow point light.
- **Stage progression wired**: `SpeedRunGame.handle3DScoreTick` now also
  computes `currentStage = floor(distance / 150) + 1` (capped at 5) so the
  "Stage X/5" badge advances as the player covers distance.

### Files touched
- `/app/frontend/src/pages/Phase1Runner3D.js` — full rewrite of the
  `Obstacle` component + `OBSTACLE_DEFS` table, spawn loop now
  stage-aware, collision loop refactored to type-dispatch.
- `/app/frontend/src/pages/SpeedRunGame.js` — `handle3DScoreTick` now
  receives `distance` and updates `currentStage`.

### Verification
- 0 m run: only meteors spawn. Jumping (Space) clears them — no more
  spurious deaths.
- ~64 m run (test mode at /30 m per stage): meteors, debris, black holes
  and satellites visible together; player survives by alternating jump &
  slide.
- Meteors visibly float above the track (y 0.55) with comet tails reading
  cleanly in dark space.
- Frontend lint clean.

---

## 2026-05-13 (c) — Real skeleton model + brighter debris

(Preserved.)

---

## 2026-05-13 (b) — 3D skins + higher-quality assets + Moon Cheese

(Preserved.)

---

## 2026-05-13 (a) — Cosmic Runner 3D bugfix + panel restoration

(Preserved.)

---

## 2026-05-12 — Cosmic Runner 3D · Phase 1 polish + Phase 2 enhancements

(Preserved.)
