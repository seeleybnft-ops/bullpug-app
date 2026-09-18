# /archived — Parked Features Vault

This directory holds every feature that has been **temporarily removed
from the live Bullpug site** but is still worth preserving in-repo for a
future re-launch. Nothing here has been deleted — every file is one
`git mv` away from being live again.

## Archival Policy

A feature moves to `/archived/` when **all three** are true:

1. Its user-facing route/UI is not linked anywhere on the live site
2. It is not called by any active production pipeline (scheduler,
   webhook, cron, other feature)
3. Its long-term product intent is "park, don't kill" — either awaiting
   a launch (Kennel, Cosmic Runner) or awaiting a strategy call
   (Trading Journal, Portfolio)

If a feature meets (1) + (2) but its long-term intent is "kill", it
gets deleted instead — not archived. Archival is a *pause*, not a
graveyard.

## Reverse Move Convention

Every archived file preserves its original path relative to `/app/`.
Restoring is always `git mv archived/<same-path> <same-path>`. Example:

```bash
git mv archived/frontend/src/pages/BettingArena.js frontend/src/pages/BettingArena.js
```

The imports and routes that used to reference the moved file have been
commented out (not deleted) in `App.js`, `HomePage.js`, and
`backend/routers/__init__.py` — search for the string "archived" in
those files to see the exact spot to restore each entry.

## Feature Archive Log

### 🐷 Pug Pit — parked 10 Sep 2026 (pre-launch)

The on-chain P2P coin-flip + jackpot betting product. Parked during the
private-testing period. All routes/UI removed; some backend modules
retained in-tree as **orphans** because active pipelines still call
them.

**Frontend archived:**
- `pages/BettingArena.js` — main Pug Pit arena page
- `components/BigWinToast.js` — big-win notification toast
- `components/JackpotTicker.js` — homepage jackpot header
- `components/JackpotDisplay.js` — in-arena jackpot widget
- `components/PugPitFaceOff.js` — head-to-head opponent card
- `components/PackRingAvatar.js` — bettor avatar frame
- `components/RakeJackpotCard.js` — rake earnings admin card

**Backend archived:**
- `routers/betting.py` — P2P challenge endpoints
- `routers/escrow.py` — deposit/refund endpoints
- `routers/ledger.py` — betting history endpoints
- `services/` — no dedicated services moved (all shared)

**Backend retained as orphans** (functions called by active code, HTTP
endpoints unmounted):
- `routers/pot.py` — `scheduler.py` calls `draw_pot_winner()`
- `routers/prize_pool.py` — `skins.py` + `scheduler.py` call payout logic
- `routers/big_wins.py` — `pot.py` calls `record_big_win()`
- `services/escrow_alerts.py` — admin.py + scheduler.py call `check_escrow_and_alert()`
- `services/rake_withdrawal.py` — admin.py calls `get_rake_stats()`

**Admin endpoints trimmed from `routers/admin.py`** (18 Sep 2026):
- `GET  /admin/challenges` — list P2P challenges
- `POST /admin/challenge/cancel` — cancel + refund
- `POST /admin/pot/draw` — force jackpot draw
- `GET  /admin/bets` — recent betting activity
- `GET  /admin/escrow` — escrow stats
- `POST /admin/escrow-alert-test` — test Telegram alert
- `GET  /admin/escrow-status` — on-chain balance + headroom
- `GET  /admin/rake-summary` — SIWS-gated lifetime rollup

**Route to restore:** `/betting` — was mounted in `App.js`

**To restore this stack:**
```bash
# 1. Move frontend files back
git mv archived/frontend/src/pages/BettingArena.js frontend/src/pages/
git mv archived/frontend/src/components/BigWinToast.js frontend/src/components/
git mv archived/frontend/src/components/JackpotTicker.js frontend/src/components/
git mv archived/frontend/src/components/JackpotDisplay.js frontend/src/components/
git mv archived/frontend/src/components/PugPitFaceOff.js frontend/src/components/
git mv archived/frontend/src/components/PackRingAvatar.js frontend/src/components/
git mv archived/frontend/src/components/RakeJackpotCard.js frontend/src/components/
# 2. Move backend routers
git mv archived/backend/routers/betting.py backend/routers/
git mv archived/backend/routers/escrow.py backend/routers/
git mv archived/backend/routers/ledger.py backend/routers/
# 3. Re-add the imports + Route in App.js (search for "Archived routes")
# 4. Re-add router imports + ALL_ROUTERS entries in routers/__init__.py
# 5. Restore admin endpoints via: git log --diff-filter=D -p -- backend/routers/admin.py
```

---

### 🏃 Cosmic Runner — parked 10 Sep 2026 (pre-launch)

The endless-runner memecoin game with skin store, achievements,
leaderboard, and a 3D variant. Parked pending a game-focused launch.

**Frontend archived:**
- `pages/SpeedRunGame.js` — main runner page (2D)
- `pages/Phase1Runner3D.js` — 3D variant
- `components/GameAchievements.js` — achievement chip stack
- `components/GameGuide.js` — how-to-play modal
- `components/SkinStore.js` — in-game skin store
- `components/SkinPreview3D.js` — 3D skin preview
- `components/LeaderboardPanel.js` — game-only leaderboard
- `game_lib/` — entire engine directory (`GameEngine.js`, `constants.js`, `useGameState.js`, `index.js`)

**Backend archived:** none (game state was frontend-only; leaderboard
entries live in the shared `leaderboard_router` which stays live)

**Routes to restore:** `/game`, `/game/3d`

**To restore:**
```bash
git mv archived/frontend/src/pages/SpeedRunGame.js frontend/src/pages/
git mv archived/frontend/src/pages/Phase1Runner3D.js frontend/src/pages/
git mv archived/frontend/src/components/GameAchievements.js frontend/src/components/
git mv archived/frontend/src/components/GameGuide.js frontend/src/components/
git mv archived/frontend/src/components/SkinStore.js frontend/src/components/
git mv archived/frontend/src/components/SkinPreview3D.js frontend/src/components/
git mv archived/frontend/src/components/LeaderboardPanel.js frontend/src/components/
git mv archived/frontend/src/game_lib frontend/src/game
# Re-add imports + Routes in App.js (search for "Archived routes")
```

---

### 🖼️ Skin Showcase — parked 10 Sep 2026 (with skin store)

The `/showcase/<wallet>` page — one-click share-card of a user's skin
collection. Parked alongside the skin store; will relaunch when the
store does.

**Frontend archived:** `pages/Showcase.js`
**Backend archived:** `routers/showcase.py`
**Routes to restore:** `/showcase`, `/showcase/:walletAddress`

**To restore:**
```bash
git mv archived/frontend/src/pages/Showcase.js frontend/src/pages/
git mv archived/backend/routers/showcase.py backend/routers/
# Re-add App.js routes + routers/__init__.py entry
```

---

### 📈 NFT Gallery Placeholder — parked 10 Sep 2026

Static Q4-2026 preview page with 6 hardcoded thumbnails and simulated
mint buttons. Not the live Bullpug Gallery on the homepage (that lives
inline in `HomePage.js` and is untouched). Kept for the eventual real
mint page.

**Frontend archived:** `pages/NFTGallery.js`
**Route to restore:** `/nft`

---

### 📓 Trading Journal + Portfolio + Reflections + Exit Simulator — parked 18 Sep 2026

The full trading-journal stack, parked in favour of the Archive-focused
product direction. Routes were already unmounted (May 2026); files moved
to `/archived/` in Sep 2026.

**Frontend archived:**
- `pages/TradingJournal.js`
- `pages/Portfolio.js`
- `pages/ExitSimulator.js` (page — different from the inline component)
- `pages/ReflectionsCalculator.js`
- `components/journal_lib/` (entire subdirectory — `Dashboard.js`,
  `TradesList.js`, `TradeForm.js`, `ExitSimulator.js`, `CloudBackup.js`,
  `ChatSection.js`, `InsightsSection.js`, `TopPicksSection.js`,
  `PendingJournalEntries.js`, `index.js`)
- `components/JournalAIAssistant.js`
- `components/AchievementBadges.js`

**Backend archived:**
- `routers/journal.py`
- `routers/portfolio.py`
- `routers/reflections.py`

**Routes to restore:** none actively mounted (were already unmounted).
The router files can go straight back to `routers/__init__.py` and the
`ALL_ROUTERS` list.

**To restore:**
```bash
git mv archived/frontend/src/pages/TradingJournal.js frontend/src/pages/
git mv archived/frontend/src/pages/Portfolio.js frontend/src/pages/
git mv archived/frontend/src/pages/ExitSimulator.js frontend/src/pages/
git mv archived/frontend/src/pages/ReflectionsCalculator.js frontend/src/pages/
git mv archived/frontend/src/components/journal_lib frontend/src/components/journal
git mv archived/frontend/src/components/JournalAIAssistant.js frontend/src/components/
git mv archived/frontend/src/components/AchievementBadges.js frontend/src/components/
git mv archived/backend/routers/journal.py backend/routers/
git mv archived/backend/routers/portfolio.py backend/routers/
git mv archived/backend/routers/reflections.py backend/routers/
# Add imports back to routers/__init__.py (see "ARCHIVED ROUTERS" header there)
# Add App.js routes if you want the pages mounted
```

---

## Not Archived (Kept Live)

Some things you might expect to be here aren't — keeping this list up
front to save future hunts:

- **`components/CommunitySpotlight.js`** — archived (10 Sep 2026)
- **`components/JackpotDisplay.js`** — archived with Pug Pit
- **`components/LeaderboardPanel.js`** — archived with Cosmic Runner
- **The homepage Bullpug Gallery** — **NOT** archived. Renders inline in
  `HomePage.js` (~line 80) and pulls from `/api/ai/gallery/recent`.
  This is the live daily-drop + user-generated art feed.
- **`services/ledger.py`** — **NOT** archived. Shared custodial-wallet
  ledger used by admin, custodial_wallet, and telegram. Only
  `routers/ledger.py` (betting-history ledger) was archived.
- **`components/PortfolioSummary.js`** — **NOT** archived. Separate from
  the archived `pages/Portfolio.js` — this is the multi-chain wallet
  portfolio widget still used by `WalletDashboard.js`.

## Related Documentation

- **Archival & orphan router policy header** — top of
  `backend/routers/__init__.py`
- **Archived route comment block** — inside `frontend/src/App.js`
  (search for "Archived routes")
- **The Kennel / Companion's Secret narrative** — see
  `backend/services/archive_achievements.py` (search for
  `COMPANIONS_SECRET_ENTRY_TEXT`) — this is the lore hook that will
  invite users into the Pug Pit re-launch when it comes.
