# Bullpug — Changelog

> PRD.md is large and historical. This file tracks recent feature additions / bug fixes per session.

---

## 2026-05-12 — Cosmic Runner 3D · Phase 1 polish + Phase 2 enhancements

**Scope**: User asked to (A) polish the Phase 1 3D runner gameplay and (B) layer in Phase 2 (better env, power-ups, mobile tuning, 3D pug polish).

### Implemented
- **HUD relocation**: Distance/Coins/Best now sit at `top-20` (below navbar) instead of `top-4` (was hidden behind the logo).
- **Backend score wiring**: `Phase1Runner3D` auto-submits to `POST /api/leaderboard/submit` on game over with `{player_name, score=floor(distance)+coins*5, moonCheese=coins}`. UI displays returned rank via `data-testid="runner-3d-rank"`.
- **Power-up system** (3 types, ~8% spawn rate):
  - **Shield** (◇ green octahedron) — absorbs the next obstacle hit and breaks with a sfx burst.
  - **Magnet** (⌬ orange torus) — for 6s, all coins within track range lerp toward the player.
  - **2× Multiplier** (× purple icosahedron) — doubles coin pickup value for 8s.
  - HUD chips show active power-ups with live countdown (`runner-3d-hud-powerups`).
  - Start screen has a 3-chip legend explaining each.
- **Environment depth**: 3 distant planets (one ringed Saturn-like), 5 parallax-scrolling nebula bands behind the track at varying depths, retained Stars + Sparkles.
- **Speed milestones**: every 250m, a centered toast (`runner-3d-milestone`) fades in for 1.6s with an upward arpeggio sfx.
- **Mobile**: swipe threshold dropped from 30 → 18 px (more responsive); on-screen tap buttons (←/↓/↑/→) auto-render on touch devices only.
- **Pug polish**: wireframe shield bubble appears around the pug when shielded.
- **Game-over screen**: now also links to the global Leaderboard page.

### Backend changes
- `routers/leaderboard.py` — fixed insert field name from `mooncakes` → `moonCheese` for shape consistency with the update path and request schema.

### Testing
- **Test report**: `/app/test_reports/iteration_99.json`
- **Backend**: 9/9 pytest pass — covers submit happy-path, upgrade-on-higher-score, no-overwrite-on-lower-score, default-name, 422-on-missing-field, leaderboard GET, pot/active and prize-pool smoke.
- **Frontend**: 100% — full game loop (access gate → start → run → keyboard input → game-over → auto-submit → restart) plus regression on `/`, `/arena`, `/leaderboard`.

### Files touched
- `/app/frontend/src/pages/Phase1Runner3D.js` (full rewrite, 707 → 1062 lines)
- `/app/backend/routers/leaderboard.py` (1-line field rename)
- `/app/memory/test_credentials.md` (created)
- `/app/backend/tests/test_leaderboard_iteration99.py` (created by testing agent)

### Known advisory notes (not blocking)
- `Phase1Runner3D.js` is 1062 lines — beyond the 700-line guideline. Suggested split next time it's touched: hooks (`useGameAudio`, `useRunnerInput`), components folder (`Bullpug`, `Track`, `NebulaBand`, `Planet`, `Obstacle`, `Coin`, `PowerUp`), and a `useRunnerLoop` hook for the per-frame logic.
- `leaderboard.py` submit endpoint does not propagate Mongo write errors — succeeds even if persistence fails. Low risk; cycle resets every 3 days.
