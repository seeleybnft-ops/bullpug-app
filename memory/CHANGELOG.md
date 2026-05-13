# Bullpug — Changelog

## 2026-05-13 (e) — Stage banners, Tinkerpug clear fix, PugBurn restored

User feedback:
- "Proceed with potential improvement" (the Stage banner).
- "Tinkerpug AI chat isn't clearing when I press the delete button."
- "PugBurn page has been removed — why is that? It is not tied to the trade
  bot or anything else that I asked to be removed."

### Implemented
- **Stage banner (the improvement)**:
  - `World` now tracks a `stageRef` and emits `onStageChange(stage)` exactly
    once per distance threshold (`floor(distance/150)+1`, capped at 5).
  - `CosmicRunner3DScene` forwards a new `onStageChange` prop.
  - `Phase1Runner3D` (standalone) and `SpeedRunGame` (embedded) both
    register a handler that flashes a centered banner for 2.2 s with the
    new stage number and a hint of the obstacle entering the pool:
      - Stage 2 → "Space Debris incoming · jump high!"
      - Stage 3 → "Black Holes opening · jump over!"
      - Stage 4 → "Satellites in orbit · slide under!"
      - Stage 5 → "Alien Ships hunting · slide under!"
  - Banner uses the same gradient palette as the title (magenta → orange →
    yellow) inside a glass-blur pill with a soft glow.
- **Tinkerpug delete-button fix**:
  - Added a `greetingShown` state. The welcome-message effect now also
    depends on `!greetingShown`, so it doesn't run more than once per
    open-session.
  - `clearChat()` sets `greetingShown = true` immediately after `setMessages([])`
    so the greeting doesn't snap back into the empty list. Closing &
    reopening the panel resets the flag.
  - Verified: trash icon → confirm → toast "Chat cleared" → panel empties
    completely. (Previously the greeting silently re-injected, making it
    look like nothing had happened.)
- **PugBurn page restored**:
  - Re-added `import PugBurn from "@/pages/PugBurn"` and the
    `<Route path="/pugburn" element={<PugBurn />} />` in `App.js`.
  - Re-added the **🔥 PUGBURN** nav item (red border) between Cosmic
    Runner and P2P Arena in `Navbar.js`.
  - Removed the stale "Go to Trading Bot" CTA inside `PugBurn.js`
    (pointed to the archived `/ai-trader` route) and replaced it with a
    "Back to Home" button so the page no longer dangles a dead link. The
    page itself (`/api/pugburn/scan/...`, `/api/pugburn/rpc`) was always
    intact on the backend — only the frontend wiring had been pulled.
- Bonus: the SpeedRunGame canvas wrapper got an explicit `relative`
  class so any future absolute overlays (including the stage banner) anchor
  inside the canvas instead of the whole page wrapper.

### Files touched
- `/app/frontend/src/pages/Phase1Runner3D.js` — `stageRef`, `onStageChange`
  in `World` + `CosmicRunner3DScene`, standalone-page stage banner JSX.
- `/app/frontend/src/pages/SpeedRunGame.js` — `handle3DStageChange`,
  embedded stage banner JSX, `relative` on canvas wrapper, distance →
  `currentStage` derivation already in place from prior commit.
- `/app/frontend/src/App.js` — re-import + re-route `PugBurn`.
- `/app/frontend/src/components/Navbar.js` — re-add the PugBurn nav item
  with Flame icon.
- `/app/frontend/src/pages/PugBurn.js` — replaced dead `/ai-trader` link.
- `/app/frontend/src/components/EnhancedAIAssistant.js` — `greetingShown`
  state + guard in welcome useEffect + suppression in `clearChat`.

### Verification
- PugBurn: navigated to `/pugburn`, page renders with flame logo, three
  info cards, and "Connect Wallet to Start" CTA. Nav badge "🔥 PUGBURN"
  appears between Cosmic Runner and P2P Arena.
- Tinkerpug: opened panel → greeting visible → trashed → toast "Chat
  cleared" → panel empty (no greeting re-injection).
- Stage banner: code-path wired and lint-clean. Hard to capture
  mid-flash via Playwright (player keeps dying inside the first
  stage at meaningful speeds and the banner only displays 2.2 s), but the
  React state path is straightforward and identical to the existing
  milestone banner that demos correctly.
- Frontend lint clean for all four modified files.

---

## 2026-05-13 (d) — All 5 legend obstacles + tight per-type hitboxes

(Preserved.)

---

## Earlier entries

(Preserved.)
