# Bullpug — Changelog

> PRD.md is large and historical. This file tracks recent feature additions / bug fixes per session.

---

## 2026-05-13 — Cosmic Runner 3D bugfix + panel restoration

User-reported regressions on `/game`:
1. Bullpug was facing the camera (eyes showing) instead of running away from it.
2. Pug was too low-poly / boxy.
3. Lane navigation skipped the middle lane (jumped left→right).
4. Slide did nothing visually and the model clipped through the floor.
5. All side panels (achievements, skin store, leaderboard, jackpot, stage badge) had been replaced by a full-screen 3D canvas.

### Fixes
- **Embedded mode**: extracted a controlled `<CosmicRunner3DScene />` from
  `Phase1Runner3D.js`. The page `/game` is now back on `SpeedRunGame.js`
  (kept all surrounding UI panels) and renders the new 3D scene inside its
  canvas slot in place of the legacy 2D canvas. The 2D animation loop is
  retained but never kicked off (the `requestAnimationFrame` boot call is
  replaced with `scene3DRef.reset()`).
- **Pug orientation**: wrapped the entire model in `rotation={[0, π, 0]}` so
  the camera now sees his back, curly tail and horns from behind.
- **Pug quality**: replaced box geometries with sphere body (squashed
  barrel), sphere head + two jowl spheres, sphere muzzle + nose + eye
  glints, sphere ears, capsule legs, partial-torus curly tail.
- **Lane de-dup**: `useGameAudio()` now returns a stable memoised object,
  and the controlState `useEffect` ignores any tick whose `ts` matches the
  previous one. Each keypress moves exactly one lane.
- **Slide fix**: removed the negative `Y` offset on the pug group. The
  slide now only compresses scale Y (and stretches Z), keeping the model
  anchored on the track surface.
- **Grace period**: spawn pointer starts 12m ahead and the first 2.5s of a
  run will never spawn an obstacle in the player's current lane.

### Files touched
- `/app/frontend/src/pages/Phase1Runner3D.js` — bugfixes + new
  `CosmicRunner3DScene` named export (forwardRef + imperative `reset()` /
  `fireAction()`).
- `/app/frontend/src/pages/SpeedRunGame.js` — import the new scene,
  replace the 2D `<canvas>` slot with the scene, wire `handle3DScoreTick`
  and `handle3DDeath` callbacks (death triggers existing
  `submitScore` + high-score localStorage + win/gameover SFX).
- `/app/frontend/src/App.js` — `/game` route now points to `SpeedRunGame`
  again; `/game/3d` keeps the standalone full-screen variant.

### Verification
- Visual: pug back facing camera, middle lane reachable, slide compresses
  without clipping, score 23 after ~3s in lane 2 → no instant death.
- Backend: existing `/api/leaderboard/submit` is called by SpeedRunGame's
  `submitScore` on death. Achievements panel ticked from 0/21 → 1/21
  ("First Steps!") on first run end.

---

## 2026-05-12 — Cosmic Runner 3D · Phase 1 polish + Phase 2 enhancements

(Preserved — see prior version of this file.)
