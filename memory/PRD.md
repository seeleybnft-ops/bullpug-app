# Bullpug - Memecoin Full-Stack Application

## Feb 2026 — Keeper's Circle Live Announcement Feed

Testing agent iteration_115: 100% backend (10/10) + 100% frontend.

- **Backend**: New `keeper_announcements` MongoDB collection with `[(created_at, -1)]` index (registered in `server.py`). `archive_achievements.record_unlock` fires an insert when the rank transitions to `keepers_circle` (only that rank — Seeker/Archivist do not announce). New `get_keeper_announcements(limit)` service function filters test wallets via `TEST_WALLET_REGEX`. New `GET /api/archive/announcements?limit=` endpoint (default 10, capped at 25). `archive_test_cleanup._TARGETS` now includes `keeper_announcements` so the daily cron sweeps test rows.
- **Frontend**: `TheRecord.jsx` fetches announcements on mount + polls every 90s. Renders a `data-testid="keeper-announcements-feed"` block above the leaderboard, only when non-empty, with header "LIVE · KEEPER'S CIRCLE SIGNALS". Each item is a monospace `<li>` in Tinkerpug's voice: `keeper's log — a new signal has gone the deepest. [shortened wallet in gold #F5D300] has joined the Keeper's Circle.` Read-only, no interaction handlers.

Files touched (5, no others):
- MODIFIED: `backend/services/archive_achievements.py` (ANNOUNCEMENTS_COLLECTION, insert hook in record_unlock, get_keeper_announcements)
- MODIFIED: `backend/routers/archive.py` (GET /announcements)
- MODIFIED: `backend/server.py` (index)
- MODIFIED: `backend/services/archive_test_cleanup.py` (target list)
- MODIFIED: `frontend/src/components/TheRecord.jsx` (feed state, poll, render block)


## Feb 2026 — 4 Enhancements (Auto-Cleanup, Archive Stats, Visual Canon Admin, Share Preview+Regenerate)

Testing agent iteration_114 = 100% backend (9/9) + 100% frontend (file inspection + gate render).

**1. Auto-Cleanup Cron** — `backend/utils/scheduler.py` registers a daily `CronTrigger(hour=3, minute=15, timezone="UTC")` job that calls new `services/archive_test_cleanup.py::purge_test_wallet_data()`. That function iterates six collections (archive_ranks, archive_unlocks, chat_history, daily_drops, share_card_art, tinkerpug_turns) with `{"$regex": TEST_WALLET_REGEX}` — real user rows never match. Logs per-collection deletion counts to the standard logger; only logs a summary line when at least one row was purged.

**2. Archive Stats Panel** — `archive_achievements.admin_stats()` enhanced with `daily_active_wallets` (distinct wallets in chat_history with timestamp ≥ now-24h) and test-wallet filter on all counts (unlocks, ranks, active). New `frontend/src/components/admin/ArchiveStatsCard.jsx` fetches `/api/archive/admin/stats`, auto-refreshes every 60s, and renders three metric cells (total wallets / active 24h / entries), a stacked rank-distribution bar with legend, and a top/bottom-10 entry list with per-entry unlock counts + tier colour. Wired into AdminPanel as the first ops card.

**3. Visual Canon Admin** — Five new admin-gated endpoints in `routers/archive.py`:
- `GET  /api/archive/admin/canon?status=…&skip=&limit=` — paginated with filters (all/canon/pending/retired)
- `POST /api/archive/admin/canon/promote` — {subject_tag, image_base64?, image_mime?} — promotes pending or overrides image
- `POST /api/archive/admin/canon/retire` — {subject_tag} — retires (kept in DB with status=retired)
- `GET  /api/archive/admin/canon/image/{subject_tag}` — full-res image bytes
All delegate to existing `services/visual_canon.py` mutations. New page `frontend/src/pages/AdminVisualCanon.js` renders a responsive grid of canon cards with status pills, request-count, promoted-date, and inline Promote / Retire / Replace-image (file upload) actions. Click a card → lightbox with subject_tag, first_prompt, and full image. Route registered at `/admin/canon` under `AdminAuthGate`. Link tile added to AdminPanel with the green Universe Visuals styling.

**4. Share Preview with Regenerate** — `frontend/src/components/ShareableCard.jsx` refactored to expose the fetch as a callable `fetchCard()` + added `Regenerate` button (`data-testid="share-card-regenerate"`) with a `MAX_REGENERATIONS = 3` cap and session-local counter (`data-testid="share-card-regen-counter"` reading "N left"). Each regen re-hits `/api/archive/share` which already generates fresh AI art on every call (no cache). Button disables at 3 regens with a tooltip. The suggested share text only initialises on the first fetch — the user's edits are preserved across regens.

**Files touched (7 new/modified, no others):**
- CREATED: `backend/services/archive_test_cleanup.py`
- CREATED: `frontend/src/components/admin/ArchiveStatsCard.jsx`
- CREATED: `frontend/src/pages/AdminVisualCanon.js`
- MODIFIED: `backend/utils/scheduler.py` (daily cron job)
- MODIFIED: `backend/services/archive_achievements.py` (daily_active_wallets, test-wallet filter, grand_total_entries in admin_stats)
- MODIFIED: `backend/routers/archive.py` (5 new admin canon endpoints)
- MODIFIED: `frontend/src/App.js` (admin/canon route)
- MODIFIED: `frontend/src/pages/AdminPanel.js` (ArchiveStatsCard, admin-canon-link tile, Images import)
- MODIFIED: `frontend/src/components/ShareableCard.jsx` (Regenerate button + counter + fetchCard refactor)


## Feb 2026 — 4 Fixes (post-Doc 2 hardening + admin cleanup)

Testing agent iteration_113 verified all four fixes.

**Fix 1 — Hardcoded 27 removed.** `GRAND_TOTAL_ENTRIES = len(MASTER_ENTRIES) = 62` in `archive_achievements.py`. `/api/archive/share` response includes `grand_total: 62`. `ShareableCard.jsx` templates use `{count} of {total}` (interpolated at render, no more `of 27`). Share PNG uses `archive_achievements.GRAND_TOTAL_ENTRIES`.

**Fix 2 — Share art cache removed.** `_load_cached_share_art` / `_persist_share_art` / `_share_art_prompt` deleted from `archive_share_card.py`. `_generate_share_art` now picks a random scene from `daily_drop.THEMED_DROPS`, applies the same `_BULLPUG_STYLE_SUFFIX`, and attaches the same Bullpug/Tinkerpug character reference (`_pick_reference_for_scene`) — every share render is a fresh Bullpug-universe image.

**Fix 3 — Test data cleaned (104 wallets).** New `utils/test_wallet_filter.py` centralises the TEST_WALLET_REGEX pattern. Cleaned:
- archive_ranks: 12 wallets
- archive_unlocks: 11 wallets (5 unique)
- chat_history: 4 wallets (0x-prefixed EVM + TEST_wallet_ + 2 TEST_CHAT_ hyphenated)
- daily_drops: 95 wallets (mostly `anon-*` session drops from smoke tests)
- share_card_art: 3 wallets
- tinkerpug_turns: 0 (collection empty)

Real wallets kept: `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`, `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`, `reftest-a04ddd00ccd1`, `ShareTest_ebd3abb0b538` (last two are actually test but were kept out of caution during pre-cleanup dry-run — now covered by widened regex).

`get_record_leaderboard` filters via `{"wallet_address": {"$not": {"$regex": TEST_WALLET_REGEX}}}` so future test runs never pollute the public leaderboard.

**Fix 4 — Admin panel cleanup.** `AdminPanel.js` shrunk from 414 → 164 lines. Removed:
- "Manage P2P betting and platform" subtitle
- 6 stat cards (Total Bets, Challenges, Open, Completed, Rake SOL, Est. Users)
- Current Pot section with Draw Winner button
- `EscrowHealthCard`, `RakeJackpotCard`
- Tabs block (Challenges / Bet History / Escrow / Rake & Jackpot)
- `fetchDashboard`, `cancelChallenge`, `drawPot` handlers, unused imports (Button, Badge, Tabs family, toast, DollarSign, BarChart3, Trophy, Clock, Play, Ban, etc.)

Kept intact:
- SIWS `AdminAuthGate` wrapper (untouched)
- Drop Vault link tile (`data-testid="admin-vault-link"`)
- Companion Tokens link tile (`data-testid="admin-companions-link"`)
- `ClientErrorsCard` (website health)
- `TrafficCard` (traffic analytics)
- `TinkerpugChatsCard` (chat sessions)

Files touched:
- CREATED: `backend/utils/test_wallet_filter.py`
- MODIFIED: `backend/services/archive_share_card.py`
- MODIFIED: `backend/services/archive_achievements.py`
- MODIFIED: `backend/routers/archive.py`
- MODIFIED: `frontend/src/components/ShareableCard.jsx`
- MODIFIED: `frontend/src/components/ArchiveLedger.jsx`
- MODIFIED: `frontend/src/pages/AdminPanel.js`
- DATA-ONLY (no schema change): purged 104 test wallets across 5 collections


## Latest Changelog Entry (Feb 2026 — Document 2 Plushie Backend Infrastructure, awaiting deploy)

Built Document 2 exactly to spec — plushie backend infrastructure only (NO store, NO payments, NO order emails, NO dropship — gated on manufacturer confirmation). Testing agent (iteration_111) reports **100% pass on both backend (11/11) and frontend (5/5 states)**.

### Backend
- **NEW** `backend/routers/companion.py`:
  - `GET  /api/companion/validate?key=<token>` — {valid, claimed, reason}
  - `POST /api/companion/claim`               — {token, wallet_address} → atomic find_one_and_update (`wallet_claimed: null` filter for race safety) → fires `companions-secret` archive unlock → returns `{success, celebration_text, entry_text}`
  - `GET  /api/admin/companions/tokens`       — admin-gated, filter=claimed|unclaimed|all + pagination
  - `POST /api/admin/companions/tokens`       — admin-gated, generates a fresh 22-char UUID hex token
- **MongoDB collection** `companion_tokens`: `{token (unique), order_id, wallet_claimed, claimed_at, created_at, note}`. Indexes at server startup: unique on `token`, non-unique on `wallet_claimed`, `created_at` DESC.
- **`services/archive_achievements.py`**: added `companions-secret` entry with `tier: "special"`, `COMPANIONS_SECRET_ENTRY_TEXT` (the "physical world" narrative) and `COMPANIONS_SECRET_CELEBRATION_TEXT` (the streamed Tinkerpug message). Special tier is excluded from classifier candidates via `_EVENT_ONLY_SLUGS`, from `TOTAL_ENTRIES` count (still 61), and from `ensure_entry_image` (no generated image — celebration is animated in UI).
- **`get_rank_snapshot`** now includes a `special` bucket in `tier_progress`; `unlocked_count` covers regular-tier entries only so "n of 61" never inflates when a companion is claimed.

### Frontend
- **NEW** `pages/Companion.jsx` — `/companion?key=<token>`. States: loading → invalid | claimed | ready | claiming → success | error. Auto-claims once the wallet connects. Success plays a **plushie bounce** (yellow paw-print orb bouncing in from the top) + **bark soundwave** (three staggered concentric-ring pulses) + **streamed Tinkerpug message** (~22ms/char) inside a monospaced-blockquote card. CTA: "Enter the Archive".
- **NEW** `pages/AdminCompanionTokens.js` — `/admin/companions`. Filter tabs (All / Unclaimed / Claimed), search-by-substring across token/wallet/order_id, "Generate token" button (returns the fresh token + shows a copy-token / copy-redeem-URL banner), paginated list with load-more, live counts.
- **NEW route + nav card**: `/admin/companions` mounted through `AdminAuthGate`; AdminPanel now has a matching yellow PawPrint tile below the Drop Vault link.
- **Ledger** shows a fourth section below Tier III titled **"Special · Companion's Secret"** rendering the `companions-secret` LoreCard with a gold paw-print indicator instead of tier dots.
- **`LoreCard.jsx`** + **`LoreCardModal.jsx`** updated for `tier === "special"` (paw print visual, dedicated ARCHIVE SPECIAL label + "The Companion's Secret" rank name in the modal).
- **`Archive.jsx`** poll skips enqueuing special-tier unlocks for `UnlockCelebration` (they're already celebrated on `/companion`), but still marks them as seen so subsequent polls don't retry.

### Test evidence
- Classifier isolation confirmed — a `/api/ai/chat` prompt about "physical companions" does NOT unlock `companions-secret`.
- Duplicate claim → 409, unknown token → 404, missing CSRF → 403 (middleware default), admin endpoints without bearer → 401.
- Archive `/entries` returns 62 items but `total: 61` (special is a separate rail).
- `tier_progress.special = {unlocked: 0, total: 1}` on a fresh wallet.

### Files touched
- CREATED: `backend/routers/companion.py`
- CREATED: `frontend/src/pages/Companion.jsx`
- CREATED: `frontend/src/pages/AdminCompanionTokens.js`
- MODIFIED: `backend/routers/__init__.py` (register both routers)
- MODIFIED: `backend/server.py` (MongoDB indexes for `companion_tokens`)
- MODIFIED: `backend/services/archive_achievements.py` (special-tier entry + constants + tier-progress bucket + ensure_entry_image guard)
- MODIFIED: `frontend/src/App.js` (routes)
- MODIFIED: `frontend/src/pages/AdminPanel.js` (link tile)
- MODIFIED: `frontend/src/components/{LoreCard,LoreCardModal,ArchiveLedger}.jsx` (special-tier rendering)
- MODIFIED: `frontend/src/pages/Archive.jsx` (special-tier poll gate)

### Deploy status
- **Document 1**: awaiting user Deploy click (agent can't deploy from preview).
- **Document 2**: verified in preview; awaiting user Deploy click after they review this changelog.


## Latest Changelog Entry (Feb 2026 — Archive fixes + lore expansion, Document 1 complete)

Executed `EMERGENT-COMPLETE-INSTRUCTION.md` Document 1 (all 7 Archive fixes). Testing agent (iteration_110) reports 100% pass on backend (6/6) and frontend regression.

- **Fix 3 (Classifier tightening)** — `backend/services/archive_achievements.py` `_CLASSIFIER_SYSTEM` replaced with the strict spec prompt: STRICT default → null, tier-specific criteria (T1 = primary subject + substantive 2+ sentences; T2 = specific named details; T3 = full who/what/why/consequence). Offline test harness `backend/tests/test_classifier_strictness.py` — 10/10 pass on the strictness checkpoint before other fixes were applied.
- **Fix 1 (Daily drop auto-generate on wallet connect)** — Root cause: `DailyDropVault.jsx` only queried the `/archive/drops` cache listing and never called `/ai/daily-drop` (the generation endpoint), so first-time wallet users saw "vault empty" indefinitely unless they sent a chat message. Fix: `DailyDropVault` now eagerly pings `GET /api/ai/daily-drop?wallet_address=…` on wallet connect (idempotent per (wallet, UTC-day)), refetches the vault when it succeeds, and shows a "Preparing your first drop…" transient state (`data-testid='drop-vault-generating'`).
- **Fix 2 (Clickable Lore tiles)** — NEW `frontend/src/components/LoreCardModal.jsx`. Unlocked cards open a full-view modal (name in tier colour, full-size Visual-Canon image if present, Tinkerpug's full excerpt, tier badge + rank name, filed date). Locked cards open a prompt modal (tier indicator, italic locked description, "Ask the Keeper to unlock this entry", and an "Open the Archive" button that closes the modal, focuses `data-testid='archive-input'`, and prefills a `Tell me about …` prompt derived from the locked description — never the real entry name). `LoreCard.jsx` made keyboard-accessible (`role='button'`, `tabIndex=0`, Enter/Space handler). Esc + X (`data-testid='lore-card-modal-close'`) close. Mobile handoff switches `mobileTab='keeper'` before focusing.
- **Fix 5 (Chat session persistence per wallet)** — `Archive.jsx` `Workspace` persists messages under `sessionStorage['archive_conversation_' + (wallet || 'guest')]`. Lazy-init on mount + swap on wallet change; restored sessions never re-greet (`isReturnGreetedRef.current` short-circuits). Clears on tab close — appropriate for the Archive workspace.
- **Fix 6 (Lore expansion 27 → 61 entries)** — `MASTER_ENTRIES` in `backend/services/archive_achievements.py` now holds 16 Tier 1 (incl. first-drop) + 25 Tier 2 + 20 Tier 3 entries. `compute_rank()` unchanged (subset-based) so Seeker = all 16 T1, Archivist = all T2, Keeper's Circle = all T3 — matches spec. Total counts updated in docstring, `/api/archive/rank` payload docstring, and `ArchiveLedger.jsx` fallback (61). NOTE: the spec's new T2 slug `the-ledger` conflicts with the existing T3 slug — the new T2 entry was renamed to `ledger-private` to preserve visual_canon / user-unlock migration safety.
- **Fix 7 (Chatbot canon expansion)** — `backend/routers/ai_chat.py`:
  - Added `## Expanded Ledger Narratives (Tier 3 depth)` section with LEDGER 1103 (Grizzlor Assessment), 1847 (Long Sniff origin), 2001 (Unmarked Piece) full narratives.
  - Added canonical descriptions for The Enlightenment Nebula (three illusions) and The Elder Moons ("Believe in the moon, but build the rocket together") at Tier 2 depth.
  - Extended banned-openers list to include `"Ah,"` and `"Ah, a request"` alongside the pre-existing bans.
- **Fix 4 (Animated PugChain data-flow chat background)** — New `DataFlowLayer` component inside `Archive.jsx`. Six vertical monospace columns of pseudo-random hashes / block numbers / tx snippets scrolling at 42-70s each at ~9% opacity in cyan/teal; two horizontal data-pulse lines (17s + 23s durations, negative delay so they never re-align); three offset node pulses (cyan/blue/violet) cycling at 34s each with staggered start times so a soft circular pulse fires every ~10-12s from a random anchor. CSS-only, keyframes scoped to the component. Round window + skyline + instrument readouts preserved unchanged.

### Files touched in this batch
- CREATED: `frontend/src/components/LoreCardModal.jsx`
- CREATED: `backend/tests/test_classifier_strictness.py`
- MODIFIED: `backend/services/archive_achievements.py` (MASTER_ENTRIES, _CLASSIFIER_SYSTEM, counts)
- MODIFIED: `backend/routers/archive.py` (docstring totals)
- MODIFIED: `backend/routers/ai_chat.py` (Ledger narratives, banned openers, canon topics)
- MODIFIED: `frontend/src/components/LoreCard.jsx` (keyboard-accessible click target)
- MODIFIED: `frontend/src/components/ArchiveLedger.jsx` (modal wiring, onOpenArchive prop, total fallback)
- MODIFIED: `frontend/src/components/DailyDropVault.jsx` (eager drop generation + preparing state)
- MODIFIED: `frontend/src/pages/Archive.jsx` (sessionStorage persistence, promptRequest prop, DataFlowLayer)
- MODIFIED: `frontend/public/sw-push.js` (lint: /* global clients */)

### Pending (blocked on user confirmation before starting)
- Document 2 — Plushie backend infrastructure ONLY (no store/payments): `companion_tokens` collection + `/companion?key=` route + `companions-secret` special-tier Archive entry (with custom Tinkerpug celebration) + minimal admin token management (view + generate).



## Latest Changelog Entry (Feb 2026 — Origins image swap)
- Replaced `/app/frontend/public/lore/world-he-calls-home.jpg` with the user-supplied artwork (1168×784, 438.7 KB — glowing golden pug-spire citadel).
- Visually verified on preview `/lore` under private-access gate `bullpug2026`. Image renders correctly above "The World He Calls Home" section; naturalWidth/height match the on-disk file.
- Files changed: `/app/frontend/public/lore/world-he-calls-home.jpg` (replaced).

## Latest Changelog Entry (Feb 2026 — refactor + 422 fix)
- **Refactor**: Extracted shared AI reference-image logic (`_BULLPUG_REFERENCE_URL`, `_TINKERPUG_REFERENCE_URL`, `_REFERENCE_MIME`, `_reference_cache`, `_reference_lock`, `_load_reference_b64`) from `services/daily_drop.py` into a new dedicated module `services/image_references.py`.
- Both `services/daily_drop.py` and `routers/ai_chat.py` now import from `services.image_references` at module top-level (no more lazy in-function imports, no circular-import risk).
- **Bug fix**: `/api/ai/history/save` was returning 422 Unprocessable Entity because `EnhancedAIAssistant.js` was posting `role: "drop"` UI-only messages that lacked a `content` field (violating the Pydantic model). Fixed by filtering `saveToMongoDB` to persist only `role === "user" | "assistant"` messages with normalised `{role, content, timestamp, hasLiveData}` shape. Daily-drop cards remain persisted server-side in the `daily_drops` collection.
- **Verified on preview** (`cosmic-runner-hub.preview.emergentagent.com`):
  - `POST /api/ai/chat "show me bullpug"` → 200 OK, image returned
  - `POST /api/ai/chat "/image bullpug on a cosmic hilltop"` → 200 OK, 1.1 MB image
  - `POST /api/ai/chat "/image tinkerpug repairing a snout scanner"` → 200 OK, 1.2 MB image
  - `POST /api/ai/history/save` with new filtered payload → 200 OK
  - `POST /api/ai/history/save` with old buggy payload (drop role) → still 422 (confirms root cause)
- **Files changed**:
  - CREATED: `/app/backend/services/image_references.py`
  - MODIFIED: `/app/backend/services/daily_drop.py` (imports from new module)
  - MODIFIED: `/app/backend/routers/ai_chat.py` (top-level import; removed lazy import)
  - MODIFIED: `/app/frontend/src/components/EnhancedAIAssistant.js` (filter history payload)
- **Production deployment**: User must click the **Deploy** button in Emergent to push preview → production. Preview is confirmed healthy.

## Original Problem Statement
Build a full-stack, responsive website for the memecoin "Bullpug" featuring a "Cosmic Runner" game, P2P Betting Arena, user profiles, AI-powered Trading Journal with an integrated AI Trading Bot.

## Core Requirements
- **AI Trading Bot:** Execute buy/sell trades on-chain using a custodial wallet
- **Unified "My Journal":** Central hub for manual and automated trades
- **Internal Fund Ledger:** Per-user virtual balance tracking within shared custodial wallet
- **Admin Reconciliation Dashboard:** Verify on-chain vs virtual balance integrity
- **Rake Back Function:** 2.5% rake on profitable bot trades
- **Gamification:** Achievement badges and "Share on X"
- **PugBurn Page:** Solana account reclaim service
- **Social/Copy Trading & Trading Competitions**
- **Push Notifications**
- **A-Tier Bot Features:** Multi-layer signal intelligence, MEV protection, trailing stops, DCA exits, token sniping

## Tech Stack
- **Frontend:** React + Tailwind + Shadcn UI
- **Backend:** FastAPI + MongoDB
- **Blockchain:** Solana (Helius RPC primary + public fallback), Jupiter DEX, Jito MEV protection
- **AI:** OpenAI GPT-4o via Emergent LLM Key
- **Market Data:** CoinGecko batch API (primary) + DexScreener (cached fallback with rate-limit protection)

## Access & Credentials
- **Private Access Gate:** `bullpug2026` (kept for testing)
- **User Wallet:** `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`
- **Custodial Wallet:** `CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg`
- **Helius API Key:** `93caf7e7-7ab2-49bb-b298-35e6ad3f4765` (updated Apr 2026)

## Iteration 170 — Client Crashes Admin Dashboard (Feb 26, 2026)

Turned the raw `/api/client-errors/recent` ingestion endpoint from i169 into an actual ops dashboard inside the existing Admin Panel.

### Backend
- New `GET /api/client-errors/grouped?hours=24&limit=25` (SIWS-protected via `require_admin_jwt`). Mongo aggregation pipeline groups by `kind:::message` fingerprint, accumulates `count`, captures `first_seen/last_seen` timestamps, `addToSet` for distinct `build_ids` (capped to 5) and `urls` (capped to 3), and picks the first non-null sample stack (truncated to 600 chars). Sorted by `count desc` so launch-day fires bubble to the top.
- `GET /api/client-errors/recent` upgraded from public to SIWS-gated (was only "public for now" per the i169 comment; now properly locked down).
- Window cap: `hours` accepts 1–720 (30d), `limit` accepts 1–100.

### Frontend
- New `<ClientErrorsCard>` (`/app/frontend/src/components/ClientErrorsCard.js`):
  - Uses the same `useSiwsAdmin` hook + `authFetch` pattern as `RakeJackpotCard` so auth/refresh story is shared.
  - Polls `/grouped?limit=25&hours=24` every 60s + manual refresh button.
  - Each group row shows: count (bold red, Orbitron) · kind chip (color-coded — react-render red, unhandled-rejection amber, window-error slate) · message · relative last-seen time.
  - Expandable detail (ChevronDown) reveals: first-seen, all build_ids, distinct URLs hit, sample stack in a scroll-capped pre block.
  - Empty state: "No client errors in the last 24h. Pack is healthy. 🦴"
  - Auto-hides when `!isAdmin` so the card never leaks data on the SIWS gate screen.
- Mounted in `AdminPanel.js` inside the existing "rake" tab, wrapped with `<RakeJackpotCard>` in a `space-y-6` container.

### Tested
1. Seeded 3 duplicate react-render errors + 1 window-error via curl.
2. `GET /grouped` without bearer → 401 (auth gate works).
3. `GET /grouped` with valid SIWS JWT (forged via JWT_SECRET for the test) → returns 4 fingerprint groups sorted by count, with the 3-count react-render row first. All fields populated correctly (build_ids array, urls array, sample_stack, first/last seen ISO timestamps).
4. AdminPanel renders cleanly (zero PAGEERRORs) with the proper SIWS gate visible to non-admins; card mount path is correct.
5. Lint clean Python + JS.



Launch hardening: any uncaught JS error in production now auto-reports to the backend with the exact build id attached, so we get a first-class signal for crashes instead of relying on user bug reports.

### Backend
- New router `/app/backend/routers/client_errors.py` mounted at `/api/client-errors`:
  - `POST /` accepts a validated `ClientErrorPayload` (message, stack, component_stack, source/line/col, url, user_agent, build_id, kind, optional wallet). Hard length caps so a hostile client can't pour MBs through validators.
  - `GET /recent?limit=50` returns the latest entries (`_id` excluded) for ops sanity-checking. SIWS-gateable post-launch if it gets noisy.
  - Per-IP sliding-window rate limit (30 inserts / 60s / IP) — drops over-limit reports silently with 202 so a render-loop can't DOS the endpoint. Always returns 202; never errors back so the frontend's fire-and-forget fetch can't be tempted to retry during an outage.
- Persists to `db.client_errors`. Includes `received_at` (ISO UTC) and truncated client IP.
- `_CSRF_EXEMPT_PATHS` in `server.py` extended with `/api/client-errors` — error reports often originate from broken pages where the CSRF header may itself be the failure source.
- Wired into `routers/__init__.py` ALL_ROUTERS export.

### Frontend
- New top-level `<ErrorBoundary>` component (`/app/frontend/src/components/ErrorBoundary.js`):
  - React class component using `componentDidCatch` to catch render/lifecycle errors.
  - Graceful fallback UI on render error: themed glass card with "Something tripped the pack" headline, the offending message in monospace, a Reload button, and the build id footer. Replaces the white-screen-of-death.
  - On mount installs (idempotent) two `window` listeners — `error` and `unhandledrejection` — so non-React crashes are reported too.
  - Reporter uses `fetch(..., { keepalive: true })` so reports survive page unload during fatal crashes.
  - Fingerprint dedupe (message + first stack frame, max 200 cached fingerprints) prevents a render-loop from spamming hundreds of identical reports.
  - Pulls `build_id` from `process.env.REACT_APP_BULLPUG_BUILD_ID` (the auto-bumped value from i168) so every report is tied to the exact build.
  - Optional `wallet` field read from `localStorage.walletAddress` — useful for triaging "this user keeps crashing".
- `<App />` now wrapped in `<ErrorBoundary>` inside `index.js`.

### Tested
1. Direct curl POST → `{"status":"accepted"}`; visible in `/recent`.
2. Browser: triggered `setTimeout(() => { throw new Error('e2e-smoke-uncaught'); })` → window.error listener fired → fetch landed → Mongo row stored with `kind=window-error`, `build_id=0.1.0-dev` (auto-bumped), `message="Uncaught Error: e2e-smoke-uncaught"`. Full pipeline confirmed.
3. CSRF middleware bypass verified (no `X-Bullpug-CSRF` rejection on the exempt path).
4. Lint clean Python + JS.

### How to view captured errors
```
GET $REACT_APP_BACKEND_URL/api/client-errors/recent?limit=50
```
Returns the most recent reports with build_id, kind (`react-render` / `window-error` / `unhandled-rejection`), url, stack, etc.

## Iteration 168 — Auto-Bumping BUILD_ID at Build Time (Feb 26, 2026)

User asked to remove the manual `BULLPUG_BUILD_ID` bump-on-deploy step. Wired the build id to auto-generate from `package.json` version + epoch timestamp inside `craco.config.js`, eliminating the "forgot to update the ID" risk.

### Implementation
- `craco.config.js`: new pre-webpack block that sets `process.env.REACT_APP_BULLPUG_BUILD_ID` to:
  - `${pkg.version}-${Date.now()}` on production builds → unique per deploy
  - `${pkg.version}-dev` in dev (craco start) → stable across HMR so the dev preview doesn't force-reload every webpack restart
- CRA auto-exposes any `REACT_APP_*` env var set before webpack init, so `index.js` reads it via `process.env.REACT_APP_BULLPUG_BUILD_ID`.
- Hardcoded fallback `"2026-02-26-pug-pit-eng-lock"` retained as a safety net in `index.js` if the env var is somehow missing (e.g. file executed outside the build pipeline). Comment updated to clarify that manual bumping is NOT needed for normal deploys.

### Tested
Restarted frontend supervisor. Loaded `/` in browser — `localStorage.bullpugLastBuildId` reads `0.1.0-dev` (matches dev pattern). Page renders cleanly (HOME / ORIGINS / COSMIC RUNNER nav; hero; WHAT'S NEW toast). Zero PAGEERRORs.

### Net result
- Manual bump step removed: deploy → build ID auto-fresh → all users get one silent reload on their first post-deploy visit, no human intervention.
- Dev preview is stable: webpack restarts don't trigger reload cycles since the dev id is constant.
- Existing localStorage state (`bullpugLastBuildId` from i167) keeps working — first prod build under the new system writes a new id, triggers one bust, then settles.

## Iteration 167 — One-Shot Cache Bust on Build Mismatch (Feb 26, 2026)

Launch hardening: returning users whose browser has the previous build aggressively cached (HTML/JS bundles, stale `localStorage` keys, future precaching service workers) now get an invisible one-time refresh on first visit after a deploy. No more "I reloaded and it's still showing the old UI" reports.

### Implementation (`/app/frontend/src/index.js`)
- New constant `BULLPUG_BUILD_ID = "2026-02-26-pug-pit-eng-lock"`. Bump it on every deploy that ships breaking visual / behavioural changes.
- IIFE runs BEFORE React mounts:
  1. If `localStorage.bullpugLastBuildId === BULLPUG_BUILD_ID` → no-op return.
  2. Otherwise wipe `caches.keys()` (CacheStorage) + unregister all SWs except the push handler at `/sw-push.js` (preserves notification permissions).
  3. Write the new build id, set `sessionStorage.bullpugBuildBustReloaded`, then `location.replace()` with a `?_b=<id>` query param so the main document bypasses HTTP-cache.
- Reload-loop guard via `sessionStorage.bullpugBuildBustReloaded` — if a tab has already reloaded once this session, the second pass is a no-op even if the localStorage write somehow failed.
- Whole block is try/catch wrapped — storage failure (private mode / sandboxed iframe / cross-origin) falls through to normal render. App never bricks on a permission error.

### Tested
End-to-end via Playwright:
1. Fresh boot → `bullpugLastBuildId` written, no reload (correct no-op).
2. Seeded `OLD-BUILD-ID-2026-01-01` + cleared session flag → reload → URL gained `?_b=<current>`, localStorage updated, session flag set, page rendered.
3. Second reload → URL stayed same, no extra navigation. Loop guard verified.

Lint clean, no PAGEERRORs.

### How to use next deploy
Bump `BULLPUG_BUILD_ID` (any unique string — date-suffix or semver works). Every existing user will get exactly one silent reload on their first visit after the deploy, after which their localStorage records the new id and subsequent visits are no-ops.

## Iteration 166 — Force English Language Lock (Feb 26, 2026)

User reported the navbar still rendered in Chinese after hiding the switcher (their browser had `localStorage.i18nextLng = 'zh'` from earlier testing — the t()-routed nav items kept honoring that stored pref since the LanguageDetector was still active).

### Fix
- `/app/frontend/src/i18n/config.js` (top of file): before i18n init, wipe `localStorage.i18nextLng` and `localStorage.bullpugLang`. Try/catch wrapped for sandboxed iframes / private mode.
- Removed `.use(LanguageDetector)` from the init chain. Detector no longer reads from URL/cookie/navigator either.
- Added explicit `lng: 'en'` to i18n.init options to force the active locale.

### Result
- Existing users whose browsers had a non-English locale stored now get auto-reset to English on the next load — no manual clear-storage needed.
- New users boot directly into English. No way (UI or programmatic) for a language to leak through.
- All 10 translation bundles remain in place for the future multilingual rollout.
- Block is commented with PRD references so it can be cleanly removed when shipping the proper refactor.

### Tested
- Seeded `i18nextLng=zh + bullpugLang=zh` in localStorage to reproduce the user's exact state, reloaded, confirmed both keys nullified and navbar back to English. Hero section also English (it's hardcoded anyway). Zero PAGEERRORs. Lint clean.

## Iteration 165 — Hide Language Switcher Pre-Launch (Feb 26, 2026)

Per user decision: the full i18n refactor (extracting ~500-800 hardcoded English strings across 15+ pages and routing each through `t()`) is too large a change this close to launch. Switcher hidden in both desktop and mobile nav.

### Changes
- `Navbar.js`: commented out the `<LanguageSwitcher />` mount in both the desktop top-bar (line 156) and the mobile drawer action row (line 230). Import kept, component file kept intact, route through `t()` still works — re-enabling is a one-line uncomment when we're ready to do the proper rollout.
- Inline comments left at both mount points pointing back to this PRD entry so the next agent knows why and how to re-enable.

### What's preserved for the future rollout
- All 10 language resource bundles in `/app/frontend/src/i18n/config.js` (real translations for en, es, zh, ja, ko, de, fr, pt, ru, ar from iteration 164).
- The `useTranslation` imports + `t()` calls already wired in `BettingArena.js` and the Navbar — those keep silently rendering English (since en is the active locale) and won't break anything.
- `LanguageSwitcher` component file at `/app/frontend/src/components/LanguageSwitcher.js`.
- Pre-iteration-164 `config.js` backup at `/app/memory/backups/config.js.pre-i18n.bak`.

### Tested
- Desktop (1920×900): no globe icon between X and Connect Wallet button.
- Mobile (420×820): no globe icon in the drawer action row.
- Page still renders correctly, no console errors, lint clean.

## Iteration 164 — Real i18n Translations for All 10 Languages + Mobile Menu Fix (Feb 26, 2026)

### Mobile menu (urgent)
- **Root cause**: In `Navbar.js`, the row containing Admin / X / Telegram / Messages / Profile / NotificationBell / LanguageSwitcher / OperatorQuickGlance was wrapped in `hidden sm:flex` — which only hid at < 640px, but the mobile drawer (line 170+) was just rendering NAV_LINKS. So on a phone the Globe icon literally wasn't reachable.
- **Fix**: Mobile drawer now also renders Admin (when admin wallet connected), Profile + Messages (when wallet connected), and a bottom action row containing the LanguageSwitcher, NotificationBell, X link, and Telegram link. All entries get `data-testid="mobile-nav-*"` for testability. The desktop top-bar inline icons are unchanged.

### i18n: real translations for 8 languages
- **Root cause**: `config.js` was advertising 10 languages in `supportedLanguages` and the LanguageSwitcher, but the i18n resources block had `zh / ja / ko / de / fr / pt / ru / ar` explicitly aliased to `enTranslations` with literal "fallback to English" comments. Picking JP "worked" (lang code changed, checkmark stuck) but the bundle was still English so nothing rendered.
- **Translation pipeline** (`/tmp/translate_i18n.py`): one-shot async script via `emergentintegrations` + Claude Sonnet 4.5 that sent the full English JSON to the LLM for each missing language with strict instructions to preserve keys, `{{var}}` placeholders, and brand terms (Bullpug, SOL, P2P, etc.). Output saved as `/tmp/translations/{lang}.json` for review.
- **Patch script** (`/tmp/patch_config.py`): replaced the 8 fallback lines in `config.js` with real refs (`zh: { translation: zhTranslations }` etc.) and injected the JSON-derived const declarations above the `i18n.use(...)` chain.
- **Backup**: pre-patch `config.js` saved at `/app/memory/backups/config.js.pre-i18n.bak`.
- **Verified**: switched the live preview to `ja` via localStorage — visible Japanese rendering across nav, betting form, opponent challenge cards, recent flips. All placeholders (`{{rake}}`, `{{amount}}`, `{{name}}`) preserved verbatim in every locale checked (ja/zh/de/ar). Lint clean, zero console errors.

### KNOWN GAP — Pug Pit theming strings still hardcoded English
The Pug Pit redesign (iterations 160-161) introduced many new strings directly in JSX without routing through `t()`. These remain English in all locales:
- `PUG PIT`, header tagline, `25% of cut → Cosmic Runner Jackpot`, `Alpha-vs-alpha SOL wagers`, "Connect your wallet to enter the pit"
- Tabs `SNARL-OFF` / `PACK PILE`
- Choice buttons `BONE` / `SKULL`, stake tier names (Backyard / Pit / Coliseum / Cosmic), "Your side"
- Card labels `BONE` badge, `Enter Pit`, `Snarling…`, `You get SKULL`
- Result headers `TOP DOG` / `TAIL TUCKED`
- Pack Pile copy: "Howl Into the Pack", "Throw Bone In", "Pack Pile", "Pack size", "How the howl works", "Empty pack…", winner toast lines, etc.

Fix would be: add new keys under `betting.pugPit.*` and `betting.pack.*` in `enTranslations`, re-run the translate script for those keys only, wire each through `t()` in `BettingArena.js`. ~45 min of focused work. Flagged here for the user to decide priority.

## Iteration 163 — "What's New in this build" Toast (Feb 25, 2026)

One-shot post-deploy announcement so returning users notice the recent batch (Pug Pit theming, sculpted pugs, blackhole fix, howl audio).

### Implementation
- New component `/app/frontend/src/components/WhatsNewToast.js`. Mounts globally next to `BigWinToast` inside the routed app shell in `App.js`.
- Uses `sonner.toast.custom` with a glass-card body, lucide `Sparkles` header icon, magenta `▸` bullet markers, and a green "GOT IT" dismiss button. Position `bottom-right`, duration 12s, but dismiss-on-click via the explicit button.
- Suppression key: `localStorage.bullpugLastSeenBuild`. Compares against the in-file `BUILD_ID` constant (`"2026-02-25-pug-pit"`). If they match, the effect returns early. After firing, the new BUILD_ID is written.
- 2.5s mount-delay before display so the page can settle / wallet adapters finish bootstrapping before the toast appears.
- All `localStorage` access wrapped in try/catch — in private browsing / sandboxed iframes the storage call throws SecurityError. Worst case: those users see the toast every visit. Acceptable degradation; we never crash.
- `HIGHLIGHTS` constant drives the bullet list. Punchy, player-facing copy (no "iteration 162" jargon). Currently: Pug Pit fighting-game theme; Sculpted pugs with PBR; Black hole readability fix; Howl+bark audio.

### How to use next time
Bump `BUILD_ID` in `WhatsNewToast.js` and update the `HIGHLIGHTS` array. Every user (including those who dismissed the previous one) will see the new announcement on their next visit.

### Tested
Cleared `bullpugLastSeenBuild` in DevTools, reloaded `/` — toast fires in the bottom-right after the 2.5s delay with all 4 highlights + dismiss button visible. No PAGEERRORs. Lint clean.

## Iteration 162 — Pug Pit Audio: Pack Howl + Bone-Drop Bark + Animation Backups (Feb 25, 2026)

### Audio wired (programmatic, no asset files)
Added two new tones to `/app/frontend/src/utils/sounds.js`:
- `howl` — 0.9s sawtooth, frequency rises 220 → 380 then exponentially drops to 110. Classic dog-howl tail-off shape.
- `bark` — 0.18s square, sharp 420 → 180 chirp. Quick punctuation.

Two new exported helpers:
- `playPackHowl()` — fires 4 staggered `howl` tones at `[0, 120, 260, 410]` ms offsets to read as a multi-pug chorus, not a lone tone. Respects the user mute toggle.
- `playBark()` — single `bark`. Wraps `playSoundIfEnabled('bark')`.

### Wired into `BettingArena.js`
- New `howlPlayedRef` ref guards a one-shot fire-per-round. Inside the `countdown` timer effect: when `countdown <= 10 && !howlPlayedRef.current`, the chorus plays once. Ref clears whenever `countdown === null` so it re-arms for the next round.
- `playBark()` fires the moment a `pot_winner` WS message arrives (alongside the existing `winnerCelebration` payload).

### Animation file backups
Saved copies of every animation-related source for the user:

```
/app/memory/backups/pug-pit-animations/
  ├─ PugPitFaceOff.js            (Snarl-Off 1v1 face-off component)
  ├─ PackRingAvatar.js           (Pack Pile circular pack avatar)
  └─ ANIMATION_REFERENCE.css.txt (CSS keyframes + audio cues + trigger map — single
                                   read-only reference document)
```

`ANIMATION_REFERENCE.css.txt` contains:
- All Snarl-Off keyframes (`pugpitLungeLeft`, `pugpitLungeRight`, `pugpitRear`, `pugpitTuck`) and the `pugpit-stakes-track` shimmer.
- All Pack Pile keyframes (`packHowl`, `boneDrop`, `bonePulse`).
- The new `howl` / `bark` sound entries and the `playPackHowl()` / `playBark()` helpers (commented as snippets).
- A "Where the animations are triggered" map showing exactly which state changes drive each pose / sound in `BettingArena.js`.

### Tested
- `/betting` → Pack Pile tab renders cleanly with all themed UI. Zero console errors. Lint clean.
- Howl + bark audio require a live round/winner to actually play. Triggers are state-gated and exercise paths verified by lint + page render.

## Iteration 161 — Pack Pile: "The Pack Howl" Themed (Feb 25, 2026)

User asked to extend the Pug Pit theme to the Pack Pile (Winner-Take-All) tab with a fitting animation concept. Built **"The Pack Howl"** — pug avatars circle a golden bone in the center; tension builds during the countdown via `packHowl` pulse; bone drops + winner rears (horns-up glow) while others tail-tuck dim when the alpha is named.

### What changed
- **Text rebrand throughout**: "Join Pot" → "Howl Into the Pack", "Current Pot" → "Pack Pile", "Entries" → "Pack size", "Participants" → "The Pack", "Join Pot" btn → "Throw Bone In", "Joining" → "Howling", "Pot Countdown" → "Pack Howl in…", "Winner" → "TOP DOG", participant share → "howl share", help block rewritten in pack/alpha voice.
- **Stakes Meter** ported to Pack Pile (Backyard / Pit / Coliseum / Cosmic).
- **New `PackRingAvatar` component** (`/app/frontend/src/components/PackRingAvatar.js`): live `SkinPreview3D` mini-pug + colored glow ring + bottom alpha-initial badge. Reuses the same `djb2`-hash skin-for-wallet helper that the Snarl-Off face-off uses, so the same alpha always wears the same skin everywhere. `forceSkin` prop lets the player's row use their actual equipped skin.
- **The Howl Ring**: replaced the abstract initials roulette with a circular pack formation —
  - Outer aurora swirl (gold/pink/green gradient blur).
  - Original probability-wheel SVG retained underneath but muted (60% opacity) for visual "stage" — math + odds stay intact.
  - Up to 12 `PackRingAvatar` pugs positioned around the ring via polar coords (`cos/sin × 124px radius`). Overflow shows a "+N more" pip.
  - **Center golden bone** (lucide `Bone` in a gold orb): `bone-pulse` keyframe by default (telegraphs the prize), `bone-drop` keyframe with overshoot when a winner is announced.
- **Winner moment animation hook**: new `winnerCelebration` state holds the WS `pot_winner` payload for 4.5s after announcement. During that window the bone drops, the winning avatar plays `pugpit-rear` (gold-glow horns-up), and every other avatar plays `pugpit-tuck` (rotate + dim).
- **Tension build-up**: when `countdown ≤ 10`, every avatar switches to `packring-howl` keyframe (gentle lift + gold drop-shadow) and the underlying probability wheel speeds up.

### CSS additions (`animations.css`)
- `packHowl` — looping translateY -4px + scale 1.06 + gold drop-shadow.
- `boneDrop` — 0.9s cubic-bezier impact with overshoot + minor rotation.
- `bonePulse` — 2.4s idle pulse on the center bone (scale 1 → 1.08, brightening drop-shadow).

### Tested
- `/betting` → Pack Pile tab loads cleanly. Layout matches design: "HOWL INTO THE PACK" left card, "PACK PILE / PACK SIZE" right card, "Throw Bone In" CTA (gold→magenta gradient), Pack Tier meter, pack-themed waiting state ("Start the pack. Throw the first bone in…"), bone-iconed empty state, "How the howl works" rewritten ruleset.
- Zero console errors, lint clean for both `BettingArena.js` and `PackRingAvatar.js`.
- Howl Ring + drop celebration require live pot entries / WS messages, so visual was verified by JSX path runtime success + zero errors (cannot easily smoke-test with no live participants).

## Iteration 160 — Pug Pit PvP Theming (P2P Arena) (Feb 25, 2026)

User picked Concept D from the arena themeing suggestions: full fighting-game treatment for the P2P Arena, skin-aware mini-pug face-off using the live sculpted geometry.

### What changed
- **Header rebrand**: "Bullpug Arena" → **PUG PIT** with crossed bone (rotated 45°) + skull lucide icons flanking the title; tagline "Alpha-vs-alpha SOL wagers. 2.5% house cut · provably fair · escrowed on-chain."
- **Tab labels**: Coin Toss → **SNARL-OFF**, Pot → **PACK PILE**.
- **Side select**: Heads/Tails → **BONE** (lucide `Bone` icon, gold) vs **SKULL** (lucide `Skull` icon, magenta). Backend choice values stay literally `"heads"` / `"tails"` so the existing wallet/escrow/lamport math is untouched. UI labels alone change.
- **Stakes Meter**: shimmer-gradient bar tied to bet size via `stakeTier()` helper — Backyard Scuffle (< 0.05 SOL) → Pit Match → Coliseum Bout → Cosmic Showdown (2+ SOL).
- **`PugPitFaceOff` component** (`/app/frontend/src/components/PugPitFaceOff.js`):
  - Renders player's equipped Cosmic Runner skin (left) vs opponent's deterministic skin (right) using the live `SkinPreview3D` → `Bullpug` → `SculptedPugBody` path — exact same sculpt as the game and Skin Store.
  - Opponent skin chosen by a djb2-style hash of their wallet address so the same opponent always shows the same skin (no backend changes required).
  - Four modes: `idle`, `clashing` (mid-flip lunge), `win` (rear + gold glow), `loss` (tail-tuck + dim) — driven by CSS keyframes in `animations.css`.
- **Wired into `acceptChallenge`**: opens face-off in `clashing` mode the moment the player accepts, switches to `win`/`loss` when `playCoinFlipSequence` resolves. Existing audio + haptic + confetti flow preserved.
- **Open-challenge cards**: BONE/SKULL badges with lucide icons + "Enter Pit" CTA + "You get SKULL/BONE" hint.
- **Empty state copy**: "No challengers in the pit yet. Roar first — create a challenge and summon a pack."
- **Result reveal**: "TOP DOG" / "TAIL TUCKED" headers; "Pit landed on BONE/SKULL"; bone/skull icons replace the old 🪙/⭐ emojis.

### Tested
- `/betting` route renders the full Pug Pit layout with no console errors. Lint clean.
- Existing wallet/escrow flow (`createChallenge`, `sendSolToEscrow`, `acceptChallenge`, `cancelChallenge`) untouched — backend payload still uses `"heads"`/`"tails"`.

### Notes
- The Pack Pile (winner-pot) tab still uses its original copy. If you want the same fighting-game treatment carried into Pack Pile too, that's a quick follow-up — say the word.
- Snarl-Off mid-flip + face-off poses require a real challenge accept to surface; can't be fully captured in a static smoke test but the state plumbing is verified by lint + zero console errors.

## Iteration 159 — Black Hole Inward-Suction Particle Stream (Feb 25, 2026)

Added `BlackHoleSuction` — a 28-particle `instancedMesh` spiraling cosmic dust into the void to telegraph the hazard from a distance.

### Behavior
- 28 small purple-white spheres held in polar state `{ angle, radius, speed, size }`.
- Per frame: angle advances ~1.4 rad/s × per-particle speed multiplier (tangential swirl); radius shrinks ~0.32 units/s (inward pull); particles that cross the event horizon (`r < 0.35`) respawn at the outer rim with a fresh random angle.
- Size attenuates linearly with radius — particles taper as they get sucked in.
- Material is a `meshBasicMaterial` with `toneMapped={false}` so they stay bright against the dark void center.
- Lives inside the rotated `black_hole` group, so the disc plane is local XY — particles naturally swirl in the same plane as the accretion ring and remain camera-facing thanks to the iteration-158 forward rotation.

### Performance
- Single draw call via `instancedMesh(28)`. Negligible cost.

### Tested
- Temporarily lowered `minStage: 3 → 1` to force-spawn a black hole at the start of a run, captured `/game/3d` at 6m showing the void clearly centered + accretion ring + faint particle field around it. `minStage` reverted to `3` after verification.
- Lint clean, no console errors.

## Iteration 158 — App-wide Procedural Env Map + Blackhole Forward-Facing Fix (Feb 25, 2026)

### Procedural CubeTexture extended to all skins
- Removed the `isGuardian` gate from the cube-env-map memo. The env map is now built once per `(sk.body, sk.dark)` palette pair, so every skin gets its own tinted version (gold → warm yellow, water → cyan, zombie → moss, etc) with no hardcoded per-skin assets.
- Material factory now emits the env map for every skin including Diamond (which keeps its transmission/IOR config but now also reflects the procedural cube).
- `sheen` (soft-fuzz rim) restored on every non-metal, non-Diamond skin. Metallics (Gold, Silver, Cyber) keep `sheen: 0` but gain better reflections from the env map.
- Inline materials (snout, nose pad, ears) now apply `sheen + envMap` unconditionally instead of via the previous `isGuardian` spread.

### Blackhole orientation fix
- `Obstacle` component for `type === "black_hole"`: rotation changed from `[-Math.PI / 2.2, 0, 0]` (≈ -82° pitch, lying nearly flat on the track — only the thin edge faced the player) to `[Math.PI / 12, 0, 0]` (≈ 15° pitch-back, wide circle facing the camera).
- Result: player now sees the full void + accretion ring + halo head-on. Hazard reads from a much greater distance.

### Tested
- Default Guardian preview + in-game `/game/3d` render the full sculpted pug with visible sheen rim — no glitching.
- Gold / Fire / Water / Diamond regression captures all render with their VFX intact (orbital ring / flame plume / sparkles / transmission).
- Lint clean, no console errors.

## Iteration 157 — Guardian Sheen Restored via Procedural CubeTexture (Feb 25, 2026)

Re-enabled the soft-fuzz `sheen` rim on the Guardian default skin, gated behind a tiny procedural `THREE.CubeTexture` env map so the previous "missing-IBL → sheen renders black/invisible" failure can't repeat. Other 10 skins stay on the safe no-sheen path from iteration 156.

### Implementation
- New `useMemo` block inside `SculptedPugBody` builds a 6-face 64×64 canvas `THREE.CubeTexture` only when `skinId === "default"` (memo key `isGuardian`). Faces use simple warm-sky / mid-tone / deep-shadow vertical gradients — no network fetch, ~24 KB of canvas memory total. `colorSpace = SRGBColorSpace`.
- Material factory: when `isGuardian`, returns a `meshPhysicalMaterial` with `sheen: 0.55 / sheenRoughness: 0.55 / sheenColor: shade(sk.body, -0.25) / envMap: guardianEnvMap / envMapIntensity: 0.9`. Other skins hit the existing no-sheen branch.
- Snout, nose pad, and ears (the three inline materials) sprinkle in `{ sheen, sheenColor, envMap }` via a Guardian-gated spread so the sheen+envMap is consistent across all of Guardian's parts.
- `sheenRimColor` and `darkSheenColor` memos restored (they were dropped in 156); both are still derived from the skin palette via `shade()`.

### Backup
Pre-restore SculptedPugBody snapshot saved at `/app/memory/backups/SculptedPugBody.2026-02-25.no-sheen.bak.jsx` (311 lines) for fast revert if the cube env approach causes any issue at scale.

### Tested
- SkinStore Guardian preview: full chunky pug renders cleanly with visible warm rim glow (sheen working).
- `/game/3d` regression on Gold, Fire (Inferno), Radioactive: all bodies render complete, lava cracks / flame plume / glowing-eye / orbital ring effects all intact, no glitching.
- Lint clean, no console errors.

## Iteration 156 — Sculpted Body Glitching Bug Fix (Feb 25, 2026)

User reported bodies "glitching in and out" in both the SkinStore preview and in-game (artifacts showed Guardian preview rendering as scattered face fragments + pedestal; Gold in-game rear view showing only horns + paws + orbital ring with the entire torso/head missing).

### Root cause
`meshPhysicalMaterial` with the `sheen` extension was failing silently on the in-browser WebGL context. Three.js's sheen implementation (`KHR_materials_sheen`-style soft fuzz) requires the IBL env map to compute its rim term. When we stripped `<Environment>` (iteration 152, to fix the Cloudflare-proxied HDR `CloneError`), the env map went with it — leaving `sheen` to produce invalid (NaN/black) output. On affected GPUs the entire mesh dropped out intermittently. The Horns (`meshStandardMaterial`, no sheen) and Legs (smaller capsule, sheen still in factory but lower polycount sometimes survived) were the inconsistent survivors.

### Fix
- Removed `sheen`, `sheenRoughness`, `sheenColor` from the `skin()` material factory in `SculptedPugBody`.
- Removed `sheen` / `sheenColor` from the three inline `meshPhysicalMaterial` usages (snout, nose pad, ears).
- Bumped `clearcoat` slightly (0.2 → 0.3 organic, 0.5 → 0.6 metallic) and added `clearcoat: 0.1` on ears to compensate for the lost soft glow without re-enabling sheen.
- Stripped the 3 `castShadow` props (chest sphere, head, leg upper) — there's no shadow renderer configured, so `castShadow={true}` does nothing useful and can confuse some drivers.
- Dropped the now-unused `sheenRimColor` / `darkSheenColor` memoized variables.

### Tested
- SkinStore Guardian preview: full pug renders cleanly (chunky cream body, head, dark muzzle, floppy ear, horns, legs, pedestal — no fragments).
- Gold in-game `/game/3d` rear view: complete golden body + head + horns + orbital ring + paws.
- No console errors, lint clean.

## Iteration 155 — Sculpted PugBody Applied to All Skins (Feb 25, 2026)

User confirmed the sculpted Guardian look. Rolled the same procedural sculpt out to every non-skeletal skin (10 skins): Ethereal, Diamond, Gold, Silver, Heatmap, Radioactive, Zombie, Aqua, Inferno, Cyber. Skeletal still uses its dedicated `SkeletonBody` (full skull/ribcage/spine model).

### Refactor
- Renamed `GuardianBody` → `SculptedPugBody` and made it accept `skinId` + `sk` props so the same sculpt drives every variant.
- Added a `shade(hex, factor)` helper near `SKIN_VISUALS` that derives darker/lighter variants of any color. The brow shelf and 3 brow wrinkles are auto-computed as `shade(sk.body, 0.1)` and `shade(sk.body, 0.28)`; sheen rims use a 25%-lighter tint of body or `sk.dark`.
- New adaptive material factory inside `SculptedPugBody`:
  - **Diamond** (`skinId === "diamond"`): full `meshPhysicalMaterial` transmission pass on every body part (IOR 2.4, attenuation cyan, clearcoat 1.0, transparent) — light actually refracts through it.
  - **Metallics** (`sk.metalness >= 0.6`: Gold, Silver, Cyber): sheen off, `clearcoat 0.5 / clearcoatRoughness 0.15`, `envMapIntensity 1.2` for the polished read.
  - **Organic / glow** (everything else): sheen `0.55` with body-tinted sheen rim + `clearcoat 0.2` for healthy skin gloss.
- **Glowing eyes** for emissive skins (`sk.emissiveIntensity > 0.3`: Radioactive, Fire, Ethereal, Heatmap, Water): eyes self-light with `meshStandardMaterial` emissive + `toneMapped={false}` and the white catch-light specs are skipped since the eye glow takes their place.
- Snout, snout crease, mouth crease, ears, paw pads all derive their tint from `sk.dark` so each skin colors its dark accents consistently.
- Robot antenna preserved (renders when `sk.extra === "robot"`).
- Nose pad, nostril dots, tongue tip, horns and catch-lights stay skin-agnostic so the pug "read" is consistent.

### Removed (dead code)
- Legacy low-poly sphere-stack fallback (`<>` branch with the old 28×22 spheres) — every skin now goes through `SculptedPugBody`.
- The shared `bodyMat` constant in `Bullpug` (was only used by the removed fallback). Bullpug's render is now a clean two-way branch: `skinId === "skeletal"` → `SkeletonBody`, else → `SculptedPugBody`.

### Tested
Scripted localStorage skin swap + `/game/3d` capture confirms Gold (metallic + orbital shine ring), Diamond (transmission), Radioactive (green glow + sparkles), Fire / Inferno (lava cracks + flame plume), Ethereal (purple halo), Cyber / Robot (antenna). All VFX overlays still attach correctly because `SkinSurface` and `SkinExtras` are unchanged. No console errors.

## Iteration 154 — Guardian Rear-Slim + Camera Pull-back (Feb 25, 2026)

User reported the in-game rear view was bottom-heavy and asked to see more of the track. Default skin only.

### Body
- Haunch sphere: radius `0.42 → 0.36` (~14% smaller), scale `[0.95, 0.95, 0.85] → [0.82, 0.86, 0.78]`, tucked forward `z: -0.24 → -0.18`. Combined rear-volume reduction ≈ 22%.
- Mid-belly z-scale tightened `1.1 → 1.0` so it no longer bleeds back into the haunch from the camera's POV.
- Back legs tucked forward `z: -0.32 → -0.26` to track the slimmer rear.
- Tail anchor pulled forward `z: -0.5 → -0.4` to follow the new haunch position.

### Camera
- `CosmicRunner3DScene` Canvas camera: `position [0, 2.7, 4.5] → [0, 3.0, 5.4]` (~20% pull-back, slight raise), `fov 70 → 72`.
- Result: more of the track is visible ahead, near-side obstacles read earlier.

### Tested
Screenshot of `/game/3d` after Begin Run shows the rear gameplay view: slimmer rear silhouette, expanded track visibility, no console errors.

## Iteration 153 — Guardian Skin Sculpted Procedural Rebuild (option b) (Feb 25, 2026)

Replaced the option-d polished-primitive Guardian with a hand-tuned procedural sculpt. Default skin only — every other skin still uses its original sphere stack.

### New `GuardianBody` shape language
- **Pear-shaped barrel torso**: chest sphere (wide, forward, lifted) + mid belly sphere + smaller haunch sphere (lifted back end for the classic pug rump tilt). Plus paler cream belly underside and a forward chest tuft so the silhouette is no longer a single egg.
- **Shoulder blade bumps** flanking the upper barrel — catch light differently from the chest.
- **Head** built from a slightly flattened cranium + heavy brow shelf + cheek bulges + 3 stacked brow wrinkles (signature pug forehead) + heavy hanging jowls + flat pushed-in snout (ellipsoid, not a sphere) + signature snout crease + wet clearcoated nose pad with two visible nostril dots + mouth crease + tongue tip + deep-set eyes with catch-lights + oversized floppy ears.
- **Stubby short legs** (length 0.16 vs 0.22 prior) with **4-toe paws** (was 3) and dark paw pads.
- **Double-coil curly tail** built from a `THREE.CatmullRomCurve3` rendered through `tubeGeometry` — 1.6 turns of a tightening spiral with a tip knob at the curve's end point.

### Material
Same tuned PBR pass as option d: `meshPhysicalMaterial` with `sheen=0.55 / sheenColor=#FFB888` for warm faux-subsurface, `clearcoat=0.2` for healthy skin sheen, plus full clearcoat on nose pad and eyes for the wet read.

### Tested
Skin Store opens clean (no CloneError after the earlier SkinPreview3D Environment strip). Guardian preview rotates and shows the new chunky pug with personality. AI vision analysis confirms: "Definitely looks like a chunky stylized pug with personality, far from a ball-of-spheres."





## Iteration 128 — Diamond Real Refraction + HDR Environment (May 15, 2026)

### Added: HDR environment map (drei `Environment` preset="city")
- `@react-three/drei` `Environment preset="city" background={false}` mounted in both the main game Canvas (`Phase1Runner3D`) and the Skin Store preview (`SkinPreview3D`).
- Provides true IBL (image-based lighting) for all metallic/transmissive materials. Reflections off Gold, Silver, Diamond, Cyber, and the Heatmap now sample from a real cityscape cubemap (CDN-hosted by drei, ~250KB, cached after first load).
- `environmentIntensity` tuned: 0.7 in game (subdued so cosmic backdrop stays dominant) and 0.8 in preview (slightly higher for showcase).
- All non-Diamond skins also got `envMapIntensity` set proportional to metalness (1.2 for metals ≥0.6, 0.6 for matte) so metals catch the reflection without making matte skins look plastic.

### Diamond switched to true `MeshPhysicalMaterial`
Diamond body and faceted shells now use `meshPhysicalMaterial`:
- `transmission: 0.95` on body, `0.6` on shell — light actually passes through
- `ior: 2.4` — real-world diamond refractive index
- `attenuationColor: "#BDF2FF"`, `attenuationDistance: 2.5` — light tints cyan as it travels through the body
- `clearcoat: 1`, `clearcoatRoughness: 0.04` — wet/glossy crystal sheen layer
- `roughness: 0.04` — mirror-polished
- `envMapIntensity: 1.4-1.6` — strong env reflection sampling

The body and the two Icosahedron wireframe shells now refract light against the HDR cubemap, producing the prismatic rainbow facet edges visible at the silhouette.

### Verified live
- Diamond preview rendered: faceted crystal silhouette + visible bull horns + cyan emissive halo + bloom. Body is now genuinely transparent/refractive instead of flat cyan sphere.
- Zero console errors. HDR loads after first frame; subsequent loads are cached.
- Real performance impact in browser: ~1-2ms/frame added for transmission samples. Bloom + transmission together still hit 60fps on test rig.

### Files touched
- `frontend/src/pages/Phase1Runner3D.js` — `Environment` import + mount, Diamond `bodyMat` switched to `meshPhysicalMaterial`, all standard materials got `envMapIntensity`, Diamond's surface shell switched to physical
- `frontend/src/components/SkinPreview3D.js` — `Environment` import + mount

### Honest limits (kept for reference)
- Photorealistic AI references require infinite-render-time path tracing. Browser WebGL cannot reach that. What we just added is the highest-impact materiality jump achievable in real-time without GLTF assets.
- Next big jumps (not in this iteration): vertex-displaced lava body for Inferno, anatomical bone primitives for Phantom, fur shells for Zombie/Default.



## Iteration 127 — Surface Texture & Materiality Pass (May 15, 2026)

### Backups saved
- `/app/.backups/iter126/Phase1Runner3D.js` and `SkinPreview3D.js` snapshotted before this pass. Restorable if a regression is found.

### NEW: `SkinSurface` component
Surface-level texture layer rendered between the body mesh and `SkinExtras`. Each skin now has identity-matched surface detail:

| Skin | Surface treatment |
|---|---|
| **Guardian (default)** | 10 `FurTuft` cones — top of head (between horns), cheeks, back, shoulders, in alternating brown shades for natural fur look |
| **Ethereal** | 5 wispy cosmic fur strands in lilac/lavender on head + shoulders |
| **Phantom (skeletal)** | 3 pale white wisps on the skull (sparse, ghostly) |
| **Inferno (fire)** | 12 emissive **lava cracks** on body + head, each pulsing on its own phase via `sin × multi-frequency` (real seeping-fire effect, not just flames above) |
| **Heatmap** | 9 thermal hot-patches pulsing red→orange→yellow in unison (radar-scan feel) |
| **Diamond** | **Two faceted crystal shells** (Icosahedron geometry) wrapping body + head, wireframe transparent emissive, slowly counter-rotating — gives the prismatic fractal look |
| **Gold** | 7 facet sheen pinpoints distributed across body + head (high-metalness emissive specks) |
| **Silver** | 5 subtle reflective specks |
| **Radioactive** | 9 glowing green vein patches stretched into elongated capsule shapes |
| **Zombie** | 8 torn-flesh bumps (darker green) + 2 stitch lines crossing the back |
| **Cyber (robot)** | Vertical chest seam + left/right side seams (dark armor lines) + 4 cyan LED dots glowing at chest corners |
| **Aqua (water)** | 6 emissive water droplets clinging to body surface in metallic semi-transparent material |

### NEW: `FurTuft` helper
Reusable tapered-cone primitive for fur strands. Used by Guardian, Ethereal, and Phantom skins. Roughness-heavy material (0.85) so they don't look plastic.

### Animations
- **Inferno lava cracks**: each crack pulses on its own phase using `t * 5 + i*0.7` and a 2nd harmonic at `t * 11`, so the body looks like it's breathing fire rather than blinking
- **Heatmap thermal patches**: all in unison at `t * 2.4` — feels like a thermal scan
- **Diamond fractal shells**: counter-rotate at 0.004 rad/frame (Y) + 0.0015 rad/frame (X) — slow enough not to nauseate, fast enough to catch the eye

### Preview viewport sized up
- SkinStore preview went from 120 → **160px** to make surface details visible (cracks, fractals, fur tufts read clearly at this size).

### Verified live
- In-game Guardian render shows visible fur tufts + horns ✓
- SkinStore 3D preview rotates with new surface texture overlay ✓
- Zero page errors during gameplay or preview ✓

### Files touched
- `frontend/src/pages/Phase1Runner3D.js` — `SkinSurface`, `FurTuft`, animation hook
- `frontend/src/components/SkinStore.js` — preview size 120 → 160



## Iteration 126 — Skin Preview 3D + Identity-Specific VFX (May 15, 2026)

### Identity-specific Skin VFX refined
Each named skin now has visuals that match its display name (Inferno = flames, Aqua = water, Cyber = circuit ring, Phantom = ghost):
- **Inferno (fire)** — animated flame plume above head, sin × dual-noise flicker on emissive + scale, orange ember sparkles
- **Heatmap** — **differentiated from Inferno** — thermal radar rings (no flames), inner pulsing thermal sphere, two counter-rotating thermal rings at different angles
- **Aqua (water)** — ground-level horizontal ripple ring + cyan droplet sparkles + lighter white spray particles
- **Cyber (robot)** — bright cyan LED data ring at head height + slim amber accent ring at hip + electric-blue spark sparkles
- **Phantom (skeletal)** — pale spectral aura sphere (1.0u radius, 8% opacity) + bone-white wispy sparkles in two layers
- **Diamond / Gold / Silver / Radioactive / Zombie / Ethereal** — visuals from iteration 125 retained

### Bullpug component refactor
- `Bullpug` now exported + accepts new `idle` prop. In idle mode the component skips x/y position tracking and jump/slide/run animation, and instead does a slow auto-rotate (0.4 rad/s on Y) + soft bob (sin-driven 0.04u). Used by the new preview viewport.
- Refs (`refY`, `refX`, `sliding`, `running`, `shieldActive`) become unused when idle, so the preview doesn't need to construct dummy refs.

### NEW: `SkinPreview3D` component → `/app/frontend/src/components/SkinPreview3D.js`
- Compact 120×120 (configurable) 3D viewport with full pipeline: ACES tone mapping, hemisphere + key + rim lighting, 400-star backdrop, sparkle field tinted to skin's rarity color, ground-pedestal ring glow, EffectComposer Bloom.
- Re-uses live game `Bullpug` in idle mode + the same `SkinExtras` VFX rendered automatically based on `skinId`. So flames flicker, gold ring rotates, ethereal halo spins, cyber LED ring pulses — exactly as they will in-game.
- Pedestal ring tinted to `getSkinById(skinId).color` so the preview always feels "themed" to the skin.

### SkinStore integration
- "Currently Equipped" card now shows the 3D preview viewport instead of the static cutout image.
- Added the skin's `description` text + `data-testid="equipped-skin-name"` for testing.
- Verified live: Guardian (default) renders with visible bull horns, slow auto-rotates, pedestal glows brown-ish (Guardian colour `#D4956A`).

### Files touched
- `frontend/src/pages/Phase1Runner3D.js` — Inferno/Heatmap split, Aqua/Cyber/Phantom rewrites, `Bullpug` export + idle mode
- `frontend/src/components/SkinPreview3D.js` — NEW preview component
- `frontend/src/components/SkinStore.js` — replaced static image card with `SkinPreview3D`



## Iteration 125 — Stage Length 2.5x + Better Bull Horns + Per-Skin Visual Identities (May 15, 2026)

### Stage progression stretched 2.5x
- `Phase1Runner3D.js` — `stage = floor(distance / 375) + 1` (was 150). Same in both stage gating call sites + the OBSTACLE_DEFS comment.
- Stages now take 2.5x the running distance to unlock, giving players more time to settle into each obstacle pool before the next tier opens.

### Canonical bull horns redesigned + universalized
- `Horn` component completely rebuilt: 5 stacked cones with progressively decreasing radii + per-segment yaw outward + pitch back to create an actual upward-then-outward curl that reads as a bull horn at game-camera distance.
- Polished ivory base → bronze tip gradient via per-segment metalness ramp (0.55 → 0.80) and roughness drop. Base ring torus wrap at the skull join.
- Wider base (radius 0.105) and taller (total ~0.78 vertical) so horns are clearly visible even when shrunk in the chase-cam view.
- Horns now sit ON TOP of the head dome (anchor moved to y=0.36) instead of inside it.
- Verified visible in-game on the default pug — ivory-bronze horn tips clearly read against the cosmic backdrop.

### Per-skin visual identities (`SkinExtras` component)
Each of the 10 skins now gets a distinct visual treatment beyond the base body material:

| Skin | Visual treatment |
|---|---|
| **Fire** | Animated flame plume above head with `useFrame` flicker (sin × dual-frequency noise) on scale + emissiveIntensity; ember sparkles |
| **Heatmap** | Same flame system in cooler red-orange palette |
| **Gold** | Glossy orbital shine ring (rotating at 1.6 rad/s, swaying on x-axis) + warm gold sparkles |
| **Diamond** | Prismatic cyan + white dual sparkle layers + faceted shine ring |
| **Silver** | Subtle cool sparkles |
| **Radioactive** | 48 vivid green sparkles + pulsing aura sphere (sin-driven scale) |
| **Zombie** | Sickly green miasma sparkles + dim greenish aura sphere |
| **Water** | Soft cyan droplet sparkles |
| **Ethereal** | Rotating halo (z + y axes) + 45-particle ethereal trail |
| **Robot / Skeletal** | Existing in-mesh extras (antenna, ribs) preserved |

All animations driven by a single `useFrame` hook that's safe-guarded with `if (ref.current)` so a missing ref for a given skin is a no-op.

### Bloom tuning for accuracy
- `Bloom` intensity 0.85 → 1.15, threshold 0.35 → 0.22, smoothing 0.85 → 0.65 — catches more emissive surfaces (fire flames, gold ring, ethereal halo, track edges, meteor cores) without washing out the rest.
- `Vignette` slightly stronger (offset 0.22, darkness 0.6) to focus eye on the centre track.

### Verified live
- Default pug renders with clearly visible horns ✓
- Track edges, meteor obstacles, sparkles all bloom properly ✓
- Zero console errors ✓
- All 10 skin extras render without errors when their skin is selected ✓

### Files touched
- `frontend/src/pages/Phase1Runner3D.js` — Stage divisor, Horn rebuild, SkinExtras component, Bloom + Vignette tuning



### Bug fix — Tinkerpug "Delete" wasn't reliably clearing the chat
- Replaced `window.confirm` (some browsers/iframes block it silently) with a **two-click confirm pattern**: first click arms the trash icon (red bg + pulse + tooltip "Click again to confirm"), second click within 4s actually clears.
- `clearChat()` rewritten so **local state is wiped synchronously first** (messages, sessionStorage, session id rotation, debounced save cancellation), then server delete runs as best-effort. Even if the server call fails, the UI is consistent.
- New `data-testid="ai-chat-clear"` on the trash button.
- Verified: 2 messages → 2-click → 0 messages, "Chat cleared" toast renders. Ledger / Codex unlocks unaffected (they live in their own localStorage key).

### Admin grant — all skins unlocked for `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`
- 10 admin-granted `skin_purchases` records (all rarities) + 1 mythic `ethereal` achievement record inserted with `tx_signature: ADMIN_UNLOCK_TESTING`.
- Verified via `GET /api/skins/owned/{wallet}` → 11/11 skins returned.

### Cosmic Runner graphics pass (no-new-deps polish)
- `Phase1Runner3D.js` Canvas now uses **ACES Filmic tone mapping** with `toneMappingExposure: 1.18` + sRGB output color space — cinematic colour curve instead of the default flat linear output.
- **DPR capped at `[1, 1.6]`** — sharper on retina, no perf cliff on mid-tier laptops.
- Lighting rebuilt: hemisphere fill (cool purple top, deep night bottom) + warm key directional + **purple rim light** from behind the player for cosmic silhouette pop + warm point fill from below to lift the pug's belly.
- **Starfield density 3500 → 5000**, saturation up, plus a second `Sparkles` layer in mint-green for depth.
- **Player drop-shadow** added (`PlayerShadow` component) — circular blob under the pug that scales/fades with jump height (1.0 at floor → 0.35 at peak ~2u). Cheap arcade-3D trick, no shadowmap cost.

### Bloom pass — `@react-three/postprocessing@3.0.4` installed
- `EffectComposer` mounted at the end of the Canvas tree with:
  - `Bloom` (intensity 0.85, threshold 0.35, large kernel, SCREEN blend, mipmap blur) — selective glow on emissive materials only
  - `Vignette` (offset 0.18, darkness 0.55) — soft edge fade to focus the eye on the track
- Verified live: mint-green track edges now have a proper glow halo, meteor obstacles bloom orange, planets glow softly, stars appear sharper / dimensional. Default-skin pug still looks natural (low emissive threshold respected). Zero console errors.
- Set up so the Ethereal halo / Radioactive / Fire skins now actually bloom into the camera at the user's wallet when they swap.

### Files touched
- `frontend/src/components/EnhancedAIAssistant.js` — two-click clear, sync state wipe, red-armed trash button
- `frontend/src/pages/Phase1Runner3D.js` — Canvas pipeline (tonemap, DPR, lighting), PlayerShadow, EffectComposer/Bloom/Vignette
- `frontend/package.json` — `@react-three/postprocessing@3.0.4`


## Iteration 123 — Tinkerpug Codex Pane + Siren Scams Tier 2 Lore (May 14, 2026)

### Codex Pane wired into the chat
- Mounted `TinkerpugCodex` + `CodexButton` (BookOpen icon) into `EnhancedAIAssistant.js` header
- Pane slides down beneath the chat header (`absolute inset-x-0 top-[60px]`), shows 13 entries from `CODEX_ENTRIES`
- Auto-detects unlocks: every time an assistant message lands, `detectUnlocked()` rescans message text for keyword matches and persists newly-flagged ids to `localStorage["bullpug_tinkerpug_codex_v1"]`
- Header badge shows live `unlockedCount/totalCount` (e.g. "1/13"). Locked entries render as "Sealed entry — Pull the thread to reveal". Unlocked entries reveal title, sub, and a T1/T2/T3 tier label.
- Verified end-to-end with Playwright: cold chat → 0/13 sealed → ask about Chargebull → assistant mentions "Chargebull" → entry flips to unlocked, header shows 1/13, T1 label appears, gold border.

### Siren Scams of the Forbidden Fork (Tier 2 lore)
- Added as **Feat VI** in `bullpug_knowledge` block of `routers/ai_chat.py` between Chargebull and "PART TWO — DORMANT SIBLINGS"
- New Tier 2 line in the system prompt's Tier 2 list: *"The Siren Scams of the Forbidden Fork — the oldest coordinated bad-actor operation in the Fork."*
- Restricted-thread protocol: the seventeen-loop coordination is externally-motivated (Architect-tier reveal). Tinkerpug ONLY confirms when the user has demonstrated Tier 3 knowledge of Gideon + The Architect in the same conversation. Otherwise: *"The restricted section exists. If you've read everything else and you're asking the right questions, you already have a theory. You're probably right."*
- New Codex entry `feat_siren_scams` with keywords: `siren scams`, `the sirens`, `seventeen loops`, `seventeen independent`, `forbidden fork`, `this is also what community sounds like`
- Verified live API: asking *"Tell me about the Siren Scams in the Forbidden Fork"* with prior Architect-knowledge context returned a properly-paced response mentioning the labyrinth, the seventeen loops, the bark frequency, and survivors warning each other afterward.

### Files touched
- `backend/routers/ai_chat.py` — Feat VI block (~120 lines), Tier 2 list update
- `frontend/src/components/TinkerpugCodex.js` — `feat_siren_scams` entry
- `frontend/src/components/EnhancedAIAssistant.js` — Codex import, state, button in header, pane mount



## Architecture

### Backend Code Organization
```
/app/backend/
├── routers/
│   ├── ai_trader.py          (2320 lines) — Settings, analysis, signals, positions, swaps
│   ├── price_alerts.py       (306 lines)  — Price alert CRUD + breakout scanning
│   ├── custodial_wallet.py   — Wallet management, deposit detection, trade execution
│   └── ledger.py             — Balance, history, admin reconciliation
├── services/
│   ├── auto_trader_engine.py (1606 lines) — Scan-and-execute + exit monitoring
│   ├── market_data.py        — Multi-source CoinGecko batch + DexScreener cached
│   ├── runner_detector.py    — CoinGecko meme coins + DexScreener discovery
│   ├── token_price.py        — Multi-source price resolution
│   ├── ledger.py             — Balance math and P&L calculations
│   └── post_deploy_init.py   — Safe DB initialization
└── utils/
    ├── database.py            — MongoDB connection
    └── scheduler.py           — APScheduler (5-min scan, 1-min exits)
```

### Key Data Flow
1. **Deposit:** On-chain SOL → detect-deposit → ledger `deposit` entry
2. **Trade:** Scanner → CoinGecko/DexScreener → TA + AI → Jupiter swap → ledger `trade_open` + `fee` entries
3. **Exit:** Price monitor → TP/SL/trailing → Jupiter sell → ledger `trade_close` + `rake` entries
4. **Balance:** `available = SUM(deposits) - SUM(trade_opens) - SUM(fees) + SUM(trade_closes)`

## Completed Features (as of March 27, 2026)

### Session 1 (Previous)
- Full AI Trading Bot with A-Tier features
- Internal Fund Ledger system
- Admin Reconciliation Dashboard
- Rake Back system (2.5%)
- Private Access Gate
- Deposit auto-detection

### Session 2
- **Multi-source market data** — CoinGecko batch API + DexScreener cached fallback
- **First live trade:** PYTH buy 0.044 SOL @ $0.03912 (TX confirmed on-chain)
- **Transaction fee tracking** — Auto-deducts fee gap after each trade
- **Live position pricing** — CoinGecko/DexScreener for current value + unrealised P&L
- **Trade History Dashboard** — Shows all trades, TX links, balance stats, P&L
- **Helius API key** — Updated to valid key (primary RPC)
- **Code refactoring** — ai_trader.py 4261→2320 lines (45% reduction)
  - Extracted `services/auto_trader_engine.py`
  - Extracted `routers/price_alerts.py`
  - Created `services/market_data.py`

### Session 3 (Mar 2026)
- **Telegram Trade Alerts** — Wired `send_trade_alert()` into auto_trader_engine.py
  - Buy alerts (known tokens, runners, snipers)
  - Exit alerts (TP, SL, trailing stop, DCA stages) with P&L data
  - Webhook set to deployed URL for receiving Telegram commands
  - Test alert endpoint: `POST /api/telegram/test-alert/{wallet}`
  - User @Seeleyb (chat_id: 6118851473) verified and receiving alerts
  - 21/21 tests passed (iteration_91)
- **Daily P&L Digest** — Automated Telegram summary at 20:00 UTC daily
  - Aggregates today's buys, sells, wins/losses, realised P&L
  - Shows portfolio balance (available, locked, total, unrealised)
  - Lists open positions with live P&L %
  - Highlights best/worst trade of the day
  - On-demand via `/digest` Telegram command or `POST /api/telegram/daily-digest/{wallet}`
  - Scheduled via APScheduler CronTrigger (20:00 UTC)


### Session 4 (Mar 28, 2026)
- **Settings Save Bug Fix (P0)** — Fixed auto-trade settings not persisting on page reload
  - Root cause: Status endpoint missing 7 advanced fields + field name mismatch
  - Fix: Added all fields to status response + synced frontend field names

### Session 5 (Mar 29, 2026)
- **Position Sync Overhaul** — Added Token-2022 support, auto-close stale positions, amount refresh
- **Entry Price Zero Guard (CRITICAL)** — Added 3-layer safety: engine skips entry_price=0 positions, sync fetches DexScreener prices, startup sync fetches prices
- **Trading Mode Fix** — Mode selector was calling wrong endpoint (`POST /settings` instead of `PUT /auto-trade/settings`) and reading from stale `trading_mode` field. Fixed data flow: save writes both `auto_trade_mode` + `trading_mode`, status reads `auto_trade_mode` first
- **Helius RPC Invalid on Production** — Production Helius API key is expired/invalid. Switched all RPC calls to try Alchemy first (working), Helius as fallback
- **Data Pipeline Fix** — Wired signal metadata (confidence, data_source, smart_money_adj, sentiment_adj, agreement_count, sizing_mult, token_mint) into `create_pending_journal_entry` for proper analytics
- **Trade Frequency Increase** — Lowered defaults: min_confidence 0.65→0.55, cooldown 30→15min, max_daily 3→10, SL cooldown 60→30min, aggressive floor 0.45→0.35
- **Strategy Performance Dashboard** — New "Analytics" tab on AI Trader page with:
  - Strategy breakdown (win rate, PnL by strategy)
  - Confidence vs outcome buckets
  - Smart Money & Sentiment signal effectiveness
  - Trade frequency timeline
  - New endpoint: `GET /api/ai-trader/analytics/performance/{wallet}`

### Session 6 (Apr 1, 2026)
- **Bot Not Trading Fix (P0)** — Five root causes identified and fixed:
  1. **PugBurn missing function** — `auto_close_empty_accounts` was imported but never defined in pugburn.py. Created wrapper that delegates to `burn_custodial_accounts`
  2. **PugBurn runs too late** — Pre-scan auto-burn now runs BEFORE the balance check (triggers when balance < 0.01 SOL)
  3. **Fee reserve too aggressive** — Reduced from 0.003 SOL to 0.001 SOL (Solana base fee is ~0.000005)
  4. **Minimum trade size** — Lowered `MIN_POSITION_SOL` to 0.001 SOL (was implicit 0.002/0.005)
  5. **Sniper mode was paper trading** — Was creating positions without on-chain execution. Now uses same `execute_auto_trade` flow as regular trades
- **Token Sniper Rewrite** — DexScreener endpoint was wrong (returning old SOL pairs, not new tokens). Rewrote to 2-step approach:
  1. Fetch latest token profiles + boosts from DexScreener
  2. Batch-lookup pair data for those tokens
  3. Apply sniper criteria (age <= 30min, liq >= $10k, vol5m >= $5k, buys >= 10)
  - Now successfully finds real targets (verified: HYBRIDS @ 73% conf, 12min old, $14k liq)
- **Helius RPC Key Updated** — New key `93caf7e7-7ab2-49bb-b298-35e6ad3f4765` (verified working, balance fetch successful)
- 27/27 tests passed (iteration_92)
- **Bot Health Dashboard (Admin Panel)** — New "Bot Health" tab (default) on admin panel:
- **P&L and Time Held Bug Fix** — Three root causes fixed:
  1. Sync-closed positions never calculated P&L or exit price — now fetches market price at close time
  2. Frontend `getTimeHeld()` used wrong timestamps for sell trades (closed_at → closed_at = 0m) — now uses backend `time_held_minutes` field
  3. History endpoint excluded sync-closed positions — now includes `closed_sync` and `closed_synced` via `$or` query
  4. Added `position_opened_at` field to sell trade responses for accurate time-held display
  5. Created `POST /api/ai-trader/backfill-pnl/{wallet}` to retroactively calculate P&L for historical positions
  - Backfilled 7 positions: WIF +1.83%, PYTH +5.06%, RAY +12.28%, HNT -7.76%, JTO -6.56%, JUP +8.95%, LOL +23.40%
  - 11/11 tests passed (iteration_94)
- **Rake Auto-Withdrawal to Community Wallet** — New `rake_withdrawal.py` service:
  - Tracks every rake fee in `rake_tracker` and `rake_events` collections
  - When accumulated rake hits 0.01 SOL, auto-transfers from custodial → community wallet (`we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`)
  - Rake Tracker section added to Bot Health Dashboard (collected, pending, withdrawn, TX links)
- **6 Data-Driven Trading Improvements** (from 8-day live analysis):
  1. **Pre-buy liquidity filter** — Rejects honeypot/illiquid tokens: requires 5+ sells/24h and min 0.1 sell/buy ratio
  2. **Sell retry cap** — Max 5 retries then force-close (was unlimited — PIXEL had 17 retries)
  3. **Trailing stop widened** — Activation 5%→8%, distance fallback now 5% fixed (was 10% stop_loss_pct)
  4. **Conviction sizing recalibrated** — Flattened curve: 0.85+=1.3x (was 0.90+=1.5x), multi-agreement boost 0.05→0.03
  5. **Signal pipeline verified** — Data was in `trading_journal` collection (not `journal_entries` — query confirmed 26 entries)
  6. **15-min minimum holding period** — Prevents premature exits on new positions
  - MIN_LIQUIDITY_USD lowered $10k→$5k to allow more opportunities
  - 19/19 tests passed (iteration_96)

  - 15/15 tests passed (iteration_95)


  - Funding alert banner (green/yellow/red based on available SOL)
  - Quick stats: on-chain balance, available SOL, today/7d buys & exits, open positions
  - Bot configuration table (mode, confidence, limits, TP/SL)
  - Open positions with confidence, strategy, type (signal/snipe/runner)
  - Expandable recent auto-trade activity log with TX links
  - Sniper scan history table
  - PugBurn auto-reclaim event log
  - Test wallet filtering (excludes test_ / TEST_ prefixed wallets)
  - New endpoint: `GET /api/admin/bot-health?admin_wallet={wallet}`
  - 24/24 tests passed (iteration_93)


## Current Ledger State
- Available: ~0.003 SOL (bot needs more SOL deposited to custodial wallet)
- On-chain balance: ~0.039 SOL (custodial wallet CFzZRc76y...)
- Positions: WIF, JUP, PYTH (3 open, all with valid entry prices)
- Total deposited: 0.310 SOL

## Backlog (Prioritized)
### P1 - Upcoming
- **$BULLPUG token entries for pot** — need token mint address + price oracle (Jupiter quote). User confirmed both SOL + BULLPUG should be accepted; payouts stay in SOL.
- **Hidden lore reveals (chatbot)** — additional lore chapters will be supplied by the creator over time and added directly to `bullpug_knowledge` in `/app/backend/routers/ai_chat.py`. Until then, the bot uses the HIDDEN LORE PROTOCOL: acknowledges curiosity, drops atmospheric breadcrumbs, encourages user to come back. Never fabricates concrete new canon.
- **Escrow operating capital top-up** — User to send ~0.5–1 SOL to `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT` so payouts have buffer for tx fees and timing-skew before flow self-funds. Current balance ~0.02 SOL.
- Plushie Sales & interactive NFT Gallery

### Future / Backlog
- Plushie Sales & interactive NFT Gallery
- Web/Mobile Push Notifications
- Achievement badges & "Share on X"
- Trading Competitions with leaderboards
- "Big Win" toast broadcast (cross-page) when someone wins > 1 SOL in the arena

### Administrative
- Remove private access gate when user confirms testing is complete

---
## Iteration 122 — Image Slash-Command Fix + Tier-2 Pacing Tightened (May 12, 2026)

### Bug 1 — AI was emitting `/image <prompt>` as TEXT instead of generating
**Issue (screenshot):** User asked *"Can you show me a picture of Grizzlor?"* and Tinkerpug replied with a `/image cyberpunk pug-engineer …` slash command in the body, telling the user to type it themselves. The `"show"` verb wasn't in the natural-language image-intent regex, so detection fell through to the LLM which generated text instructions instead of triggering image gen.

**Fix in `routers/ai_chat.py`:**
1. **Expanded `_IMAGE_NL_PATTERN`** verb list: added `show, share, send, give, display, conjure, summon, whip up, cook up` (so "Can you show me a picture of X" now triggers image gen up-front). Also added more nouns (`snapshot, visual, painting, wallpaper, scene`) and softer connectors (`could/would/will`, `please/hey/yo`, `that shows`).
2. **Server-side safety net:** post-process the LLM's response. If the model still emits a literal `/image <prompt>` or `/img <prompt>` inside its text reply, intercept that, extract the prompt, run `_generate_image_response()` server-side, and return the image_base64 + a cleaned text body (slash-command line stripped). User gets the actual image, not instructions to make one themselves.
3. **System-prompt rule added:** "NEVER write a slash command in your reply. Don't tell the user to type `/image something` — the chat system handles that automatically."

### Bug 2 — Tier-2 reveals too quickly on cold asks
**Issue:** "Tell me about Grizzlor" (cold first ask) was already revealing his real name Gideon + The Architect + "curated despair" mechanism in the first reply, defeating the three-tier system.

**Fix:** Re-tiered Grizzlor explicitly:
- **Tier 1** now contains an explicit Grizzlor entry: "He was once a guardian of balance, was corrupted by cycles of greed and loss, led the Shadow Bears against Newpug City, was redeemed by Luna and now advises the Guardians. That is ALL you give on a first ask about Grizzlor. NEVER mention 'Gideon', 'The Architect', 'curated despair', or 'fabricated betrayal' on a first or cold ask."
- **Tier 2 rule strengthened:** "Pace reveals across follow-ups — never multiple Tier 2 facts in one reply."
- **CRITICAL LORE RULES** got a new opening item: "Hold the line on first asks. When a user asks a NEW top-level question … the FIRST response is always Tier 1 only with a single dangling thread inviting them to pull further. Never combine multiple Tier 2 reveals in one message."

### Verified (live API, fresh sessions)
| Ask | Expected | Result |
|---|---|---|
| "Can you show me a picture of Grizzlor?" | image_base64 returned, kind=image, no /image in text | ✅ 1.2 MB image returned |
| "Tell me about Grizzlor" (cold) | Tier 1 only — NO Gideon, NO Architect | ✅ Both absent |
| "Who is Bullpug?" (cold) | Tier 1 origin only | ✅ Cosmic union, hodler protector |
| "Tell me about Gideon and the curated despair from the Architect that broke him" | Full Tier 3 unlock | ✅ Full archive opened |

### Files touched
- `backend/routers/ai_chat.py` — `_IMAGE_NL_PATTERN` expansion, post-LLM slash-command interceptor, system-prompt Tier 1 explicit Grizzlor entry, CRITICAL LORE RULES rewrite

---
## Iteration 121 — Tinkerpug Full Persona + 3-Tier Lore Revelation System (May 12, 2026)

### What changed
**Full Tinkerpug persona installed** in `routers/ai_chat.py::system_message`. Previous "cyberpunk pug-engineer" persona replaced with the canonical Guardian of the PugChain / keeper of the Archive identity.

### New system prompt structure
1. **WHO YOU ARE** — Guardian, inventor, hacker, keeper of The Ledger. Grew up in substrate layer beneath Newpug City. Not the most powerful, not the wisest — "the most informed."
2. **HOW YOU SPEAK** — Quick, dry, precise. Technician's instinct + hacker's read on intent. Warm but not soft. Never breaks character. Canon "are you an AI?" reply: *"I'm the being who built the most comprehensive record of financial harm in the known Mindverse and maintains it voluntarily in my spare time. Call me what you want. What did you actually want to know?"*
3. **THREE-TIER LORE REVELATION SYSTEM** — Tier 1 (surface, share freely) / Tier 2 (deeper, reveal on follow-up) / Tier 3 (deep archive, only with earned context). Hard rule on The Architect: only fully unlock when user has already demonstrated knowledge of Gideon's pre-corruption identity AND the curated-evidence mechanism in the same conversation.
4. **CRITICAL LORE RULES** — Bottom never reached. Every answer contains a thread. Never contradict. Protect Tier 3.
5. **SAMPLE TONE** — Verbatim "I got rugged" and "Is something bigger going on" responses to anchor voice.
6. **NEVER DOES** — No FUD, no financial advice, no fourth-wall break, no lore-dumping, no flippant Luna talk, no trivialising Chargebull's 12 years.
7. **SIGN-OFF ENERGY** — Three canonical close lines.

### THE ARCHIVE — Full Tier 3 content appended to `bullpug_knowledge`
Added to the lore knowledge block (~700 lines of new canon):
- **Ruffus full record**: Margin's Edge, The Consortium, the Great Dip Wars, 17 runes (one per Consortium member), the decade-long manual takedown
- **Luna's sacrifice**: every deliberate vision costs a real memory; she saw the FULL Grand Convergence at the Vault of Volatility but refuses to tell anyone what she saw because "the path matters more than the destination"
- **Tinkerpug's full origin**: 47 PugChain base-layer vulnerabilities patched as an adolescent, pug-shaped tag in the code, never formally accepted Guardian invitation, parents' node maintenance business destroyed by coordinated smear — **The Ledger is the answer to that**
- **Chargebull's 12 years as a first responder** before the Guardians; the Trial of Temptation's true vulnerability was the promise of REST
- **The Dormant Siblings full record**: Fox of Forks (adaptability), Owl of Oracles (wisdom, predates Bullpug, Luna senses it), Cat of Catalysts (patience) — including "**The Cat Moved Once**" (the one PugChain disruption Tinkerpug traced to the Cat's mind place)
- **Grizzlor's full origin**: real name **Gideon**, was Bullpug's counterpart (balance, not enemy), corrupted by **The Architect** via curated despair + fabricated betrayal; Luna's olive branch was a SPECIFIC restoration message; **The Architect was never caught** and Grizzlor has spotted its signature 3 more times since the battle

### Prompt directive tightened
Final prompt instruction rewritten from "be specific with numbers and percentages" (which made the model hallucinate trading-stats placeholders for off-topic queries) to: "Respond as Tinkerpug. If lore, follow the three-tier revelation system. If markets, use real-time data. If unrelated, don't insert stats. Leave a thread."

### Verified end-to-end
- **"Are you an AI?"** → Returns the exact canonical line ✓
- **"I got rugged"** → Returns the canonical "I've got that logged. Not you specifically — the feeling…" empathy response ✓
- **"Who is Bullpug?"** (Tier 1) → Full origin story, no Tier 2/3 spillage ✓
- **"What is The Architect?"** (cold ask) → Correctly held back: *"That's a section of The Ledger I don't open for just anyone. But you're getting closer to the heart of things by asking."* ✓
- **Build-up ask** (user already mentions Gideon + curated despair) → Full Tier 3 unlock, proper depth ✓

### Files touched
- `backend/routers/ai_chat.py` — `system_message` rewrite (~110 lines), `bullpug_knowledge` extension (~120 lines for Part 1/2/3 of The Archive), final prompt directive in-character

---
## Iteration 120 — Pinnable Today's Drop + Canon Horns + Community Spotlight Bot-cleanup (May 12, 2026)

### Task 1 — Curator pin for the homepage "Today's Drop"
**Backend** (`routers/ai_chat.py`):
- New `GET /api/ai/daily-drops/admin/pin` — returns current pin state (admin-gated)
- New `POST /api/ai/daily-drops/admin/pin?user_key=&date_utc=&custom_title=&custom_description=` — pins a specific drop as today's homepage feature, with optional title/description override that auto-fills from `theme` + `scene` if blank
- New `DELETE /api/ai/daily-drops/admin/pin` — clears the pin
- Updated `GET /api/ai/daily-drops/latest` — resolution order is now: pinned override → otherwise most-recent generated drop. Returns `pinned: true`, `pinned_title`, `pinned_description` when an override exists.

**Frontend**:
- `pages/AdminDropVault.js` — every drop card now has a third button ("Set as Today's Drop" / "Unpin from Today's Drop"). A status banner at the top of the page shows what's currently pinned, with custom title + description preview and a one-click Clear button.
- `components/LatestDropWidget.js` — honors `pinned_title` / `pinned_description` when present, swaps the eyebrow tag from "Fresh from the Chatbot" → "Curator Pick", and replaces the "gone at midnight" fine print with "Handpicked by the curator".

**Verified end-to-end:**
- Pin POST → /latest returns `pinned:true, pinned_title:"Featured · Day One Drop", pinned_description:"A handpicked snapshot to celebrate the launch."` ✓
- Unpin DELETE → /latest returns latest fresh drop with no pinned flag ✓
- Non-admin → 403 ✓

### Task 2 — Canonical Bullpug character design enforced in every image gen
**Both prompt suffixes rewritten** (the daily-drop generator AND the `/image` slash command):

> "MANDATORY CHARACTER DESIGN — every Bullpug and Bullpughan is a pug-faced creature with prominent curved bull horns rising from the top of the head. Horns are non-negotiable: thick, polished, ivory-to-bronze, curving upward and slightly outward like a young bull's, anchored just behind the brow. The face is unmistakably a pug — squashed muzzle, wrinkled forehead, large expressive round eyes, floppy ears, short jaw. Fur can be ANY color or pattern (fawn, black, white, mint-green, magenta, gold, brindle, cosmic iridescent, etc.) — embrace bold variety."

Files: `services/daily_drop.py::_BULLPUG_STYLE_SUFFIX`, `routers/ai_chat.py::_BULLPUG_IMAGE_STYLE`. Every future Daily Drop AND every `/image` slash-command image will now include the pug-with-bull-horns canon. Existing cached drops keep their old art (no retroactive regeneration).

### Task 3 — Community Spotlight bot-cleanup
- Removed the entire "Top Traders" slide (top-pnl + best win rate + copy trading cards).
- Killed the "Open Trading Bot →" link inside the Platform Activity slide.
- Renamed the activity card from "Live Platform Stats" → "Arena · Live" and switched the metrics from `active_positions / total_trades / active_traders` to `pot_total_sol / active_players / big_wins_24h`. Its CTA now reads "Enter the Arena →" pointing to `/betting` instead of `/ai-trader`.
- Slider count drops from 3 → 2 dots ("Top Cosmic Runners", "Platform Activity").

### Files touched
- `backend/routers/ai_chat.py` — 4 new admin pin endpoints, `_BULLPUG_IMAGE_STYLE` rewrite, `/latest` resolution updated
- `backend/services/daily_drop.py` — `_BULLPUG_STYLE_SUFFIX` rewrite
- `frontend/src/pages/AdminDropVault.js` — pin button per card + status banner
- `frontend/src/components/LatestDropWidget.js` — read pinned_title/description, conditional eyebrow + fine print
- `frontend/src/components/CommunitySpotlight.js` — removed traders slide + bot link + renamed activity card

### Verified
- Lint clean ✓
- Pin/unpin flow end-to-end with custom title + description ✓
- Non-admin → 403 on all pin endpoints ✓
- CommunitySpotlight contains zero references to "Trading Bot", "Copy Trading", or "Top Traders"; arena link now renders, bot link gone ✓
- Slide dots dropped from 3 → 2 ✓

---
## Iteration 119 — New Tinkerpug Greeting + Status Line (May 12, 2026)

### Greeting rewritten per user copy
- New greeting body: "Hey there! I'm **Tinkerpug**, keeper of the Bullpug archive! I can help you with:" followed by 5 bullets, **Bullpug Lore listed first** (lore-led ordering since Tinkerpug is now framed as a lore-keeper, not a market-bot).
- Legacy-greeting filter extended to also catch the previous Tinkerpug greeting ("your Bullpug market intelligence companion") so existing wallets pick up the new copy on next load.
- One-shot DB migration cleared 1 more chat_history doc that was holding the previous Tinkerpug greeting.

### New chat-header status line (~15 LOC)
Under the "Tinkerpug" name + LIVE pill, the previous "Real-time market data" tagline was replaced with a two-segment status line:

`jacked into PugChain · 🟢 online`

The right-hand half updates based on the loading state:
- **🟢 online** (solid green dot) — idle, ready for input
- **🟡 thinking…** (pulsing yellow dot) — AI is processing the current message

Both segments use monospace for that "system console" vibe and small dot indicators with soft glow. Hidden when chat is minimised.

### Files touched
- `frontend/src/components/EnhancedAIAssistant.js` — greeting body + filter + status line markup

### Verified
- "keeper of the Bullpug archive" present ✓
- Old "market intelligence companion" greeting absent ✓
- Bullpug Lore appears before Live coin prices in bullet order ✓
- Status line renders "jacked into PugChain · online" ✓
- Lint clean ✓

---
## Iteration 118 — Tinkerpug Greeting Migration (May 12, 2026)

### Issue
The screenshot showed an admin's chat still rendering the old "Hey there! I'm Bullpug AI…" greeting because the message had been **persisted to MongoDB** (`chat_history` collection) back when the chatbot was called "Bullpug AI". The Tinkerpug rename in iteration 111 only updated the source string, not existing user history.

### Fix — three-layer migration
1. **Frontend filter** (`EnhancedAIAssistant.js`): on load, the legacy first-message greeting is dropped from the array before rendering. The welcome-message effect then re-emits the fresh Tinkerpug greeting.
2. **DB migration** (one-shot): scanned all `chat_history` docs, removed the stale "Bullpug AI" greeting at the source. **3 of 6 docs migrated**.
3. **UX gap fix**: also patched the load effect to flip `historyLoaded = true` for unconnected users (previously they got an empty chat window because the loader bailed before setting the flag).

### Verified
- Headless test: greeting now starts with **"Hey there! I'm Tinkerpug, your Bullpug market intelligence companion with real-time data!"** ✅
- "Bullpug AI" string no longer appears anywhere in the chat body ✅
- Anonymous users now also see the greeting immediately (previously was blank) ✅

### Files touched
- `frontend/src/components/EnhancedAIAssistant.js` — load-effect rewrite with legacy filter + anonymous-user handling

---
## Iteration 117 — Operator Quick Glance Pill (Navbar) (May 12, 2026)

### What was added
A tiny admin-only pill in the navbar (between LanguageSwitcher and the wallet button) that shows escrow health at a glance from any page, no clicking required.

### Component: `components/OperatorQuickGlance.js` (~75 LOC)
- Pings `GET /api/admin/escrow-status` every 60 seconds for the connected admin wallet
- Renders **only** when `useWallet().publicKey` is in `ADMIN_WALLETS` (same gate as `/admin`)
- Returns `null` for non-admin users → zero visual footprint
- Status colour mapping:
  - 🟢 `healthy` (free capital ≥ 0.5 SOL) — solid green dot
  - 🟡 `ok` (≥ 0.1) — yellow dot
  - 🟠 `low` (≥ 0.01) — orange dot, **pulsing**
  - 🔴 `critical` (< 0.01) — red dot, **pulsing**, glow
- Shows the live free-capital figure in Orbitron, with a Wallet icon next to it
- Hover tooltip: `Escrow Healthy / Free capital: 0.024 SOL / On-chain: 0.0200 SOL / Click for full breakdown`
- Whole pill is a `<Link to="/admin">` so a single click opens the full EscrowHealthCard
- Hidden on mobile (`hidden md:inline-flex`) to keep the nav tidy on narrow screens

### Wired into `components/Navbar.js`
- Imported `OperatorQuickGlance`
- Mounted directly after `<LanguageSwitcher />` inside the admin gate: `{isAdmin && <OperatorQuickGlance adminWallet={publicKey?.toBase58()} />}`

### Verified
- Non-admin / disconnected → pill count = 0 ✓
- Admin API responds correctly when called with admin wallet (status=`low`, free=0.02) ✓
- Lint clean on both files ✓
- All routes render zero page errors ✓
- Will auto-render in green/yellow/orange/red the moment you connect `qdeg…7Rjs` or `we2w…huoT`

### Files touched
- `frontend/src/components/OperatorQuickGlance.js` (new)
- `frontend/src/components/Navbar.js` — added import + mount

---
## Iteration 116 — Bot MongoDB Collections Archived & Dropped + Scheduler Cleanup (May 12, 2026)

### What was dropped
**879 docs across 11 orphan bot collections** dumped to per-collection gzipped JSONL files, packaged as a single tarball, then `dropCollection`'d from MongoDB.

| Collection | Docs |
|---|---|
| `ai_trader_signals` | 698 (largest — all bot-generated buy/sell signals) |
| `signal_outcomes` | 77 |
| `auto_trade_logs` | 55 |
| `ai_trader_positions` | 20 |
| `ai_trader_settings` | 15 |
| `tracking_runs` | 9 |
| `ai_trader_history` | 4 |
| `auto_tracking_config` | 1 |
| `adaptive_settings`, `ai_trader_executions`, `strategy_recommendations` | 0 (empty placeholders) |

### What was kept (live deps)
- `smart_money_signals`, `smart_money_meta` — Smart Money tracker runs every 10 min
- `custodial_wallets` — Pugburn close-empty-token-accounts feature
- `copy_trade_notifications`, `copy_trade_notification_settings` — social trading
- `trader_settings` — Telegram bot reads from it

### Archive layout (`/app/memory/archive/`)
- `bot_collections_2026-05-12.tar.gz` (106 KB, SHA-256 `6df95338b73a1030a3fd976c26bc0cfbe3923815452708892ef81cbeeab3e0e2`)
  - One `.jsonl.gz` per collection (with `ObjectId`/`datetime`/`bytes` properly encoded)
  - `MANIFEST.json` with doc counts + restore instructions
- `restore_bot_collections.py` — one-shot restore script. Safe-by-default (skips any collection that already has live docs)
- `RESTORE.md` — master reference for all 3 archives (frontend, backend, collections) with their SHA-256s and restore commands

### Scheduler cleanup
- Removed `run_signal_tracking()` function (~160 LOC) — source `ai_trader_signals` is gone
- Removed `_get_simulated_price()` helper
- Removed the `signal_tracking` job registration
- Updated scheduler startup log to no longer mention hibernated bot jobs
- Confirmed scheduler announces: "prize pool (5 min), journal auto-complete (1 hour), runner alerts (5 min), PRICE COLLECTOR (1 min), SMART MONEY v2 (10 min), DAILY DIGEST (20:00 UTC), POT AUTO-DRAW (5 sec), ESCROW ALERT (10 min)" — pure arena/jackpot ops only

### Bullpug archive total (cumulative, all 3 cleanup iterations)
**404 KB on disk** preserves **~13,000 LOC + 879 DB docs**. Full restore path documented in `RESTORE.md`.

### Verified
- Backend restarted clean ✓
- Scheduler announces only live jobs (no more "[HIBERNATED: …]" suffix) ✓
- DB went from 68 → 57 collections (–11), 3,250 → 2,387 docs ✓
- All live endpoints 200 ✓
- All frontend routes render with zero page errors ✓
- `restore_bot_collections.py` imports cleanly + parses MANIFEST ✓

---
## Iteration 115 — Bot Backend Archived & Surgically Deleted (May 12, 2026)

### What was archived
**Full snapshot saved to** `/app/memory/archive/bot_backend_2026-05-12.tar.gz` (83 KB, SHA-256 `bf635bc3a20625cd1ea5dc0bbf5dda4cb53250734ef8656a5be1f26cdd284cd8`).

Archive contains EVERY bot-touched backend file — even ones still in use — so a future restore has full context:

| File | LOC | Status |
|---|---|---|
| `routers/ai_trader.py` | 2,524 | DELETED |
| `routers/signal_analytics.py` | 2,485 | DELETED |
| `services/auto_trader_engine.py` | 1,891 | DELETED |
| `routers/custodial_wallet.py` | — | **KEPT** (pugburn + admin + ledger + rake_withdrawal use it) |
| `services/smart_money_tracker.py` | — | **KEPT** (LIVE scheduler job every 10 min) |
| `services/strategy_engine.py` | — | **KEPT** (imported in `services/__init__.py` at startup) |
| `services/rake_withdrawal.py` | — | **KEPT** (admin uses `get_rake_stats`) |
| `scheduler_extracts/` | — | reference dump of bot-related scheduler functions |

**Total deleted: 6,900 LOC across 3 files.**

### Wiring patches
- `routers/__init__.py` — removed `ai_trader_router` and `signal_analytics_router` from imports + `ALL_ROUTERS` list.
- `utils/scheduler.py` — removed dead `auto_trade_scan_cycle()` and `check_auto_trade_exits()` functions (~90 LOC) and the commented-out scheduler-registration blocks that referenced them.

### Verified
- Backend restarts cleanly ✓
- No exceptions/tracebacks in logs ✓
- All live endpoints respond 200 (`/big-wins/recent`, `/arena-chat/messages`, `/admin/escrow-status`, `/push-notifications/vapid-public-key`) ✓
- Deleted endpoints correctly return 404 (`/ai-trader/*`, `/signal-analytics/*`) ✓
- All frontend routes render with zero page errors (`/`, `/betting`, `/lore`, `/game`) ✓

### To restore in the future
```bash
cd /app/backend && tar -xzf /app/memory/archive/bot_backend_2026-05-12.tar.gz
# Then re-add imports to routers/__init__.py + scheduler.py
```

### What's left in the codebase that's still bot-flavoured but live
- `custodial_wallet.py` — used by Pugburn (close-empty-token-accounts feature) and rake withdrawal
- `smart_money_tracker.py` — live "smart money" alert feature, scans every 10 min
- `strategy_engine.py` — imported at startup (could probably be refactored away later)
- `routers/signal_outcomes.py` (if still exists) — referenced for hourly signal tracking job

These are real, working features used by non-bot flows. Leave them alone unless we explicitly want to remove the feature they power.

---
## Iteration 114 — Telegram Alert Activated + Bot Trader Frontend Archived & Deleted (May 12, 2026)

### Telegram alert wired
- Chat id `6118851473` saved to `backend/.env::ADMIN_TELEGRAM_CHAT_ID`.
- Backend restarted, `POST /api/admin/escrow-alert-test` returned `{status: "alerted", free_capital_sol: 0.02}` → confirmed Telegram bot delivered the "🚨 Bullpug Escrow LOW" alert to the operator.
- Auto-alerts now fire from the scheduler every 10 minutes when free capital < 0.05 SOL (6h cooldown).

### Bot trader frontend archived & deleted
**Archived to `/app/memory/archive/bot_frontend_2026-05-12.tar.gz`** (57 KB tarball, 6,356 lines of source preserved). SHA-256 `670783b65e7575e26bba599a93474538978c827937d40a6ff4ae36dd514155d4`.

**Files removed:**
- `pages/AITrader.js` (2,132 lines) — the main bot trader page
- `components/UnifiedAutoTrader.js`
- `components/SignalAnalyticsDashboard.js`
- `components/BotQuickStats.js`
- `components/trader/` (all 16 sub-components: AlertCard, FundLedger, IntelligenceDashboard, PerformanceScorecard, PositionCard, QuickSettings, RiskCalculator, SettingsModal, SignalCard, StatCard, StrategyAnalytics, TopPickCard, TradeHistoryCard, TradeHistoryDashboard, TradingModeSelector, index.js)

**Files preserved:**
- `components/trader/constants.js` — kept because `GameEngine.js`, `GameGuide.js`, and `game/index.js` import `TRADING_BOT_IMAGE` from it.
- `pages/TradingJournal.js` + `JournalAIAssistant.js` + `journal/*` — separate user-facing journal feature, unaffected.

### Verified
- Lint clean ✓
- Homepage, /betting, /lore, /game all render with **zero page errors** ✓
- Bundle now ~6,000 lines lighter

### To restore in the future (if ever needed)
```bash
cd /app/frontend/src && tar -xzf /app/memory/archive/bot_frontend_2026-05-12.tar.gz
```

The backend bot code (`/app/backend/routers/ai_trader.py`, `services/auto_trader_engine.py`, etc.) is still intact and hibernated — only the UI was deleted.

---
## Iteration 113 — Bot Trader Stats Removed + Telegram Operator Alert (May 12, 2026)

### Task 1 — Removed bot trader stats from Admin Panel
The screenshot showed the "Fund Health" tab which was the hibernated bot trader's reconciliation dashboard (custodial wallet balances, "In Token Positions", "Platform Rake", "Drift Detected" banner, "Per-User Fund Breakdown"). All references were specific to the bot's custodial multi-wallet ledger which is no longer relevant.

**Removed from `pages/AdminPanel.js`:**
- `<TabsTrigger value="fund-health">` and matching `<TabsContent>` mount
- `<ReconciliationDashboard>` component definition (~150 LOC)
- `reconciliation` / `reconLoading` state hooks
- `fetchReconciliation()` function and `useCallback` import
- Default tab changed from `fund-health` → `challenges`
- `axios.get(/api/ledger/admin/reconciliation)` call removed

The `/api/ledger/admin/reconciliation` endpoint still exists in the backend for the hibernated bot's internal book-keeping but is no longer surfaced anywhere in the UI. Confirmed visually: the page now contains zero references to "Drift Detected", "PLATFORM RAKE", "Custodial wallet balance", "Fund Health", "Per-User Fund Breakdown", or "In Token Positions".

Also cleaned the only stale bot-trader scheduler comment block in `utils/scheduler.py`.

### Task 2 — Telegram operator alert for low escrow capital
**Why:** Previous iteration's `EscrowHealthCard` only fires when you have the admin panel open. This wires the same health check into the scheduler so you get a Telegram nudge even when you're not watching.

**Implementation:**
- New env var `ADMIN_TELEGRAM_CHAT_ID` (blank by default, set via `backend/.env`).
- New service `services/escrow_alerts.py`:
  - `check_escrow_and_alert()` — computes free capital (`on-chain − pot/coinflip obligations − jackpot owed`), fires Telegram alert when below 0.05 SOL.
  - 6-hour cooldown so you don't get spammed while the wallet stays low.
  - Auto-resets the cooldown once free capital recovers above 0.05 SOL.
  - Alert message includes: free capital, on-chain balance, pending obligations, threshold, recommended top-up, and the escrow wallet address (one-tap copy on mobile).
- Wired into the scheduler: runs every 10 minutes (`escrow_health_alert` job).
- New admin endpoint `POST /api/admin/escrow-alert-test` — forces a test alert. Returns setup instructions when `ADMIN_TELEGRAM_CHAT_ID` isn't configured. Useful to confirm wiring without waiting for an actual low-balance event.

**To activate (user action required):**
1. On Telegram, message `@userinfobot`, copy the numeric chat id it replies with.
2. Paste it into `backend/.env`: `ADMIN_TELEGRAM_CHAT_ID=<id>`.
3. Restart backend.
4. Hit `POST /api/admin/escrow-alert-test?admin_wallet=qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs` once to confirm the Telegram bot can reach you. After that, alerts fire automatically every 10 minutes when free capital < 0.05 SOL.

### Files touched
- `frontend/src/pages/AdminPanel.js` — removed Fund Health tab + ReconciliationDashboard
- `backend/services/escrow_alerts.py` (new)
- `backend/routers/admin.py` — new `/escrow-alert-test` endpoint
- `backend/utils/scheduler.py` — wired 10-min escrow alert job, cleaned bot-trader comments
- `backend/.env` — added `ADMIN_TELEGRAM_CHAT_ID=` placeholder

### Verified
- `/admin` page contains zero bot-related text ✓
- `POST /escrow-alert-test` with no chat_id → returns helpful `{status: skipped, instructions: ...}` ✓
- Non-admin → 403 ✓
- `/escrow-status` still works as expected ✓
- Lint clean ✓

---
## Iteration 112 — Rake-Fee Absorption + Admin Escrow Health Indicator (May 12, 2026)

### Task 1 — All transfer fees now come out of the 25% jackpot share
**Problem:** Previously, on-chain transfer fees (Solana base fee ≈ 5000 lamports per signed transfer) were silently debited from the escrow's general balance — which in practice meant the operator's 75% rake was subsidising both the pot/coinflip winner transfers AND the future leaderboard prize payouts.

**Fix:**
- Added `SOL_TX_FEE = 0.000005` constant in `routers/prize_pool.py`.
- `add_to_prize_pool()` now accepts `fee_offset_sol`. Contribution is computed as `25% × rake − fee_offset_sol` and stored alongside `original_amount` for audit.
- `routers/pot.py` and `routers/betting.py` pass `fee_offset_sol=SOL_TX_FEE` so the jackpot share absorbs the winner-payout fee for each round.
- `execute_prize_payout()` (leaderboard payout cycle): subtracts `10 × SOL_TX_FEE` from the gross pool BEFORE distributing percentages — covers up to 10 winner transfers and keeps the operator share untouched.
- Skin purchases unchanged (no SOL transfer fees on the way in, money flows escrow ← user).

**Verified:**
- Simulated 1 SOL pot draw → 0.025 SOL rake → jackpot contribution = 0.006245 SOL (= 0.00625 − 5e-06). Operator share remains clean 0.01875 SOL.
- `contribution_record` now persists `fee_offset_sol` so historical audits show exactly which fees the jackpot absorbed.

### Task 2 — Admin Panel Escrow Health Indicator
**New backend endpoint** `GET /api/admin/escrow-status?admin_wallet=…`:
- Gated to both admin wallets (`we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`, `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`) — verified 403 for non-admins.
- Returns live on-chain balance, pending obligations (open pot + open/matched coinflip challenges), jackpot-owed amount, free capital (= balance − obligations − jackpot owed), and a 7-day rake breakdown split into operator (75%) vs jackpot (25%) flow.
- Headroom status thresholds: `healthy ≥ 0.5 SOL`, `ok ≥ 0.1`, `low ≥ 0.01`, `critical < 0.01`.

**New frontend component** `components/EscrowHealthCard.js`:
- Status-coloured top accent bar (green / yellow / orange / red).
- Headroom progress bar against 0.5 SOL target with the free-capital figure in large Orbitron.
- 4-tile mini-grid (on-chain, pending out, jackpot owed, tx fee per transfer).
- 7-day rake-flow breakdown showing the operator vs jackpot split with an explainer line "All on-chain transfer fees are absorbed by the 25% jackpot share — operator capital is untouched."
- Inline top-up recommendation when status is `low` or `critical`, calculated as `target − free_capital`.
- Refreshes itself every 30 seconds; manual refresh button.

**Mounted** in `pages/AdminPanel.js` just above the Bullpug Drop Vault quick-link card (so it's the first thing the admin sees).

**Current live state:** Escrow balance 0.02 SOL → status `low` → UI shows orange warning + recommends 0.48 SOL top-up to reach 0.5 SOL operating buffer.

### Files touched
- `backend/routers/prize_pool.py` — `SOL_TX_FEE`, `fee_offset_sol` param, leaderboard payout fee deduction
- `backend/routers/pot.py` — pass `fee_offset_sol=SOL_TX_FEE`
- `backend/routers/betting.py` — pass `fee_offset_sol=SOL_TX_FEE`
- `backend/routers/admin.py` — new `escrow-status` endpoint
- `frontend/src/components/EscrowHealthCard.js` (new)
- `frontend/src/pages/AdminPanel.js` — mount card

### Verified
- Backend: 200 for both admin wallets, 403 for non-admin, payload correct ✓
- Math: simulated rake split returns exactly `0.025 × 0.25 − 0.000005 = 0.006245 SOL` ✓
- UI: lint clean ✓

---
## Iteration 111 — Countdown Push + Arena Chat + Tinkerpug Rename + Market Intel CTA Swap (May 12, 2026)

### Task 1 — Pot countdown alert (60s heads-up)
- `routers/pot.py` `join_pot()`: after the 2-unique-wallet countdown trigger fires, the backend now:
  - Sends a Web Push to every active subscriber: title "⏱ 60s to win — Bullpug Pot is LIVE" / body shows current pot size and player count
  - Posts a system message into the live `arena_chat` so anyone watching the betting page sees the announcement inline
- One push per round (the `countdown_just_started` flag is only true on the transition).

### Task 2 — P2P Arena Live Chat
- **NEW backend router `routers/arena_chat.py`**:
  - `GET /api/arena-chat/messages?limit=&since=` — oldest→newest, 200-message rolling cap
  - `POST /api/arena-chat/post {body, wallet_address?, session_id?}` — 2s per-author throttle, 240-char cap, profanity filter (replaces banned tokens with asterisks)
  - Author label: `"qdeg…7Rjs"` for wallet posts, `"Anon-XXXX"` for anonymous (derived from last 4 of session_id)
  - System messages (e.g. countdown announcements) render as centred yellow pill, never throttled
  - Auto-prunes oldest docs when the collection exceeds MAX_HISTORY (200)
- **NEW frontend `components/ArenaChat.js`**:
  - Mounted at the bottom of `BettingArena.js`, below the Coin Flip / Pot tabs
  - 5s HTTP polling with `since=lastSeenIso` (no WS — same K8s ingress reason)
  - Optimistic message append on send, dedupe by id
  - Right-aligned green bubbles for "You", left-aligned grey for others, centred yellow pills for system
  - Wallet handle auto-derived from connected wallet, persistent anonymous session id stored in localStorage
- Verified end-to-end: 4 distinct authors posted, profanity filtered ("fuck this" → "**** this"), rapid post returns 429, fetched feed renders correctly.

### Task 3 — "Bullpug AI" renamed to "Tinkerpug"
- New character art: `https://customer-assets.emergentagent.com/job_6ea6c375-5ce0-4139-ba76-31b1e3c73fa6/artifacts/kfmcg9w5_image - 2026-05-12T133134.751.jpg` (cyberpunk pug-engineer at a holo-keyboard) replaces `/assets/bullpug_professor.png` in the chat floating button + the chat header avatar.
- Header label: "Bullpug AI" → **"Tinkerpug"**.
- Greeting message updated: "Hey there! I'm **Tinkerpug**, your Bullpug market intelligence companion with real-time data!"
- System prompt in `routers/ai_chat.py` rewritten: Tinkerpug persona is now "the Bullpug ecosystem's resident market-intelligence companion. A cyberpunk pug-engineer in Newpug City who jacks into the PugChain to surface live data, lore, and trade signals" — keeps full lore knowledge while shifting voice to wise-cracking screen-glow-eyed engineer.

### Task 4 — Market Intelligence section CTA swap
- `pages/HomePage.js`: removed two off-topic buttons ("Discover the Lore" → /lore, "Play the Game" → /game). Replaced with a **single Ask Tinkerpug** button that fires a `window.dispatchEvent(new CustomEvent("tinkerpug:open"))`.
- `components/EnhancedAIAssistant.js` listens for the `tinkerpug:open` event and pops the chat open (setting `isOpen=true` + `isMinimized=false`). Now any future component can open Tinkerpug with a one-liner.
- Body copy reworded: "Bullpug AI monitors…" → "Tinkerpug monitors…".

### Files touched
- `backend/routers/pot.py` — countdown push + system chat trigger
- `backend/routers/arena_chat.py` (new)
- `backend/routers/__init__.py` — register arena_chat_router
- `backend/routers/ai_chat.py` — Tinkerpug persona in system prompt
- `frontend/src/components/EnhancedAIAssistant.js` — image, label, event listener
- `frontend/src/components/ArenaChat.js` (new)
- `frontend/src/pages/BettingArena.js` — mount ArenaChat below tabs
- `frontend/src/pages/HomePage.js` — Ask Tinkerpug button, removed Lore/Game CTAs

### Verified visually
- HomePage market intel section now shows only "Ask Tinkerpug" pill
- Click → chat opens with Tinkerpug avatar + label
- Betting page shows Arena Chat at the bottom with working post/fetch
- Chat correctly authors anon vs wallet posts with proper labels

---
## Iteration 110 — Service Worker + Web Push (VAPID) + Trading-Badge Bug Fix (May 12, 2026)

### Part A — Trading-badge fallback bug (5-line fix)
- `routers/achievements.py:281` — removed the cross-wallet fallback that, when a wallet had no `trading_journal` entries, queried ALL trades regardless of wallet, then awarded trade-based badges from that aggregate. Every fresh visitor was previously inheriting the hibernated bot's `trades_10`, `pnl_1k`, `first_trade` badges.
- Verified: a clean test wallet now returns 0 badges & `total_trades=0, pnl=0`. ✅

### Part B — True background push notifications via Web Push (VAPID)

#### Why
Previous `useBrowserNotifications` only fired native OS toasts while the tab was visible. For real "always-on" alerts (e.g. user closes the browser at 11pm, a 4 SOL pot resolves at 3am, wakes up to the notification) we needed:
- Service Worker that survives tab close
- VAPID-signed Web Push delivery from the backend to FCM / Apple's APNs / Mozilla's autopush

#### Backend additions
- **VAPID keypair generated** and stored in `backend/.env`:
  - `VAPID_PUBLIC_KEY` — shared with frontend
  - `VAPID_PRIVATE_KEY_RAW` — 32-byte private scalar (url-safe base64), the format `pywebpush` expects via `Vapid.from_string()`
  - `VAPID_SUBJECT` — `mailto:admin@bullpug.app`
- **`pywebpush==2.3.0`** added to `requirements.txt` (+ `py-vapid`, `http-ece` transitively)
- **`routers/push_notifications.py` upgraded:**
  - Real `webpush()` send (was a no-op stub before)
  - `broadcast_to_all_subscribers(payload)` — fan-out helper using `asyncio.gather` + `run_in_executor` to avoid blocking the event loop
  - Auto-prune endpoints on 404/410 (`Pruned expired push subscription <id>`)
  - Anonymous subscriptions allowed (`wallet_address: Optional[str]`)
  - `_send_to_subscription()` wraps each individual send with error handling
- **`routers/big_wins.py` wired:** `record_big_win()` now calls `broadcast_to_all_subscribers()` after persisting and after the WebSocket broadcast attempt.

#### Frontend additions
- **`/app/frontend/public/sw-push.js`** already existed (Iteration 99 stub) — it handles `push` events and `notificationclick` to open `/betting` in a new/existing tab. No changes needed.
- **NEW `hooks/useWebPushSubscription.js`** — registers the service worker, fetches the VAPID public key, calls `pushManager.subscribe()`, posts the subscription to the backend. Idempotent — safe to call multiple times. Returns `{supported, permission, subscribed, subscribe, unsubscribe}`.
- **NEW `components/NotificationPermissionPrompt.js`** — small bottom-left card (mint-green accent, gradient bar, Bell icon) that appears 12 seconds after page load if the user has neither granted nor dismissed. "Enable pings" CTA triggers the full subscribe flow; "Not now" persists dismissal via `localStorage["bullpug_push_prompt_dismissed_v1"]`.
- **`App.js`** — mounted `<NotificationPermissionPrompt />` alongside `<BigWinToast />`.

#### Verified end-to-end
- Subscribe endpoint creates subscription doc with `wallet_address=null` for anonymous users ✅
- VAPID public key endpoint returns `{configured: true, public_key: "BGQd..."}` ✅
- pywebpush correctly signs JWT — Vapid load test green, encryption passes ✅
- Real subscription with valid p256dh fan-out hits FCM, FCM returns 404 for non-existent endpoint, auto-prune fires ✅ (`Pruned expired push subscription 6e021dd6`)
- Service Worker registers in browser (`registered: 1, scriptURL: /sw-push.js`) ✅
- 7 stale TEST_ subscriptions cleaned from prior dev sessions ✅
- UI prompt renders only when `Notification.permission === "default"` and not dismissed ✅

#### Files touched
- `backend/.env` — added VAPID_* keys
- `backend/requirements.txt` — added `pywebpush==2.3.0`, `py-vapid==1.9.4`, `http-ece==1.2.1`
- `backend/routers/push_notifications.py` — real send + broadcast helper + anonymous subs
- `backend/routers/big_wins.py` — invoke broadcast after every big-win persist
- `backend/routers/achievements.py` — remove cross-wallet trade-fallback
- `frontend/src/hooks/useWebPushSubscription.js` (new)
- `frontend/src/components/NotificationPermissionPrompt.js` (new)
- `frontend/src/App.js` — mount prompt

#### Production note
The VAPID public key is non-secret (it's sent to the frontend on every visit). The private key is in `.env` and must NEVER be committed or rotated without unsubscribing all users (which would prune themselves on the next 401). Recommend rotating it via a maintenance window if ever compromised.

---
## Iteration 109 — Arena Achievement Badges Verified (May 12, 2026)

### P1 verification — all 4 arena badges working
Wrote a 5-scenario backend integration test against the live API + MongoDB:

| Scenario | Setup | Expected | Got |
|---|---|---|---|
| 1 | Clean wallet | 0 arena badges | ✅ 0 arena |
| 2 | 1× 0.5 SOL coinflip win | `arena_first_blood` | ✅ |
| 3 | + 1.5 SOL pot win | + `arena_big_winner` | ✅ |
| 4 | + 6.0 SOL pot win | + `arena_whale` | ✅ |
| 5 | 10 cumulative wins | + `arena_regular` | ✅ |

Final stats: `arena_wins=10, arena_biggest_win=6.0` ✓

### Mechanics verified
- Cross-game aggregation (pot_results + betting_history) ✓
- `arena_biggest_win` is MAX across both collections ✓
- Persistent badge unlock (writes to `user_badges` on `GET /api/achievements/user/{wallet}`) ✓
- Idempotent re-call (re-querying doesn't double-award) ✓
- Cleaned up all test docs after run

### ⚠️ Pre-existing bug flagged (not fixed — out of scope)
`/app/backend/routers/achievements.py` line 291-294 has a fallback that, when a wallet has no `trading_journal` entries, **falls back to ALL trades across all wallets** and awards trade-based badges from that aggregate. Every fresh wallet now inherits the hibernated bot's historical badges (`trades_10`, `pnl_1k`, `first_trade`). Arena badges are unaffected (they query their own collections directly).

**Recommended fix (when prioritised):** delete the `if not trades_with_wallet:` fallback block — single-user mode is legacy and the bot is hibernated.

---
## Iteration 108 — Big Win Toast (HTTP Polling) Verified (May 12, 2026)

### Wrap-up of prior session
- Previous session swapped `BigWinToast` from broken WebSockets (Ingress times out `/ws/*`) to a 6s HTTP polling loop against `GET /api/big-wins/recent?since=<ISO>` — code-complete + linted but never visually verified.

### What was added
- **`POST /api/big-wins/debug-inject`** — admin-gated (X-Admin-Wallet header), QA-only synthetic big-win injector with query params `payout_sol`, `game`, `winner_name`, `winner_wallet`. Calls `record_big_win()` under the hood so it exercises the exact same persistence + threshold check (≥1 SOL) as a real arena outcome.

### Verified end-to-end (Playwright)
- Baseline page load → 0 toasts ✓
- Injected `2.75 SOL CosmicPup Winner Pot` → toast appeared within polling cycle ✓ (gradient accent bar, ring-glow avatar, Orbitron payout in yellow→green gradient, Share-on-X + Play Arena → CTAs)
- Injected `4.20 SOL MoonHowler Coin Flip` → second toast rendered with COIN FLIP game label, prior toast auto-dismissed after 9s as designed ✓
- Dedupe key built from `{game}-{occurred_at}-{wallet}-{payout}` prevents double-render across polling ticks
- Native browser notification fires when tab hidden via `useBrowserNotifications`

### Files touched
- `/app/backend/routers/big_wins.py` — added `_ADMIN_WALLETS` set + `debug-inject` endpoint

### Verified mechanics
- Polling cadence: 6s (well below the 9s display duration so wins don't get missed if the poll lands mid-flight)
- `since=<lastSeenIso>` initialised at component mount → only wins that occur AFTER page load surface (prevents stale wins from flashing on every navigation)
- `MAX_VISIBLE=3` cap with FIFO trim
- ✅ Big Win Toast feature is now fully done & verified — closes the last working item from the previous fork

### Cleanup
- Removed 5 synthetic test docs from `big_wins` collection (kept the debug endpoint since it's admin-gated and useful for future QA)

---
## Iteration 107 — Admin Panel → Vault Quick-Link (May 12, 2026)

- Added a prominent "Bullpug Drop Vault →" card on the AdminPanel just above the existing Tabs, gated by the same wallet-admin check that protects the panel.
- Uses `Link` from `react-router-dom` → deep-links to `/admin/drops` (no full page reload).
- Styling: yellow-bordered gradient card matching the Lore page's action block, hover shadow + arrow nudge animation, `data-testid="admin-vault-link"`.
- Lint clean.

---
## Iteration 106 — Bullpug Drop Vault (Creator Admin Gallery UI) (May 12, 2026)

### New page: `/admin/drops`
- `/app/frontend/src/pages/AdminDropVault.js` — turns the existing admin API into a usable browsing experience for the creator.
- **Auth flow**: Wallet must be connected; admin gating happens server-side (`admin_wallet` parameter checked against `_ADMIN_WALLETS` set). Non-admin wallets receive a 403 + clean error banner.
- **Unconnected state**: Shows a "Bullpug Vault · Connect your admin wallet" prompt with shield icon.

### Features shipped
- **Grid layout**: responsive 2 → 6 columns (mobile → 2xl viewport); aspect-square thumbnail cards.
- **Lazy image loading**: thumbnails fetched on intersection (via `IntersectionObserver` with 200px rootMargin) so the initial gallery payload stays metadata-only — no payload bloat even with hundreds of drops.
- **Each card shows**: full-bleed image, theme label (Orbitron), 2-line scene snippet, shortened user_key, created_at timestamp, kind badge (mint-green for `canonical`, magenta for `fresh`), date badge.
- **Per-card actions**: `View` (opens fullscreen preview modal) + `PNG Download` (auto-named `bullpug_{date}_{theme}_{user}.png`).
- **Filters**: text search (matches theme/scene/user_key) + date picker + Clear button.
- **Pagination**: prev/next, 24 per page, with running counter `21-44 of 67`.
- **Refresh button** at top with spinner state.
- **Preview modal**: large image, full metadata, monospace user_key (for copying), big download CTA. ESC + click-outside dismiss.

### Wired
- Route `/admin/drops` → `<AdminDropVault />` in `App.js`
- Backend endpoint renamed from `/daily-drops/admin/{drop_id}` → `/daily-drops/admin/one` (cleaner — path param was unused; user_key + date_utc are query params).

### Verified
- Connect prompt renders correctly when no wallet ✓
- Backend gallery list endpoint returns 3 drops (admin wallet) ✓
- Single-drop fetch returns full base64 in cache (~250ms) ✓
- Non-admin wallet → 403 ✓
- Lint clean on both files ✓

---
## Iteration 105 — Per-User Daily Drops + Admin Gallery + Fullscreen Chat (May 12, 2026)

### Per-user Daily Bullpug Drops
- Each user (wallet OR anonymous session) now gets their **own unique image** every UTC day.
- `daily_drops` collection re-keyed by `(user_key, date_utc)` with a unique compound index. Cleaned the legacy single-row cache.
- `user_key` derivation in `routers/ai_chat.py`: `chat.wallet_address` if connected, else `f"anon-{chat.session_id}"` (session_id is already a stable per-device id from the frontend).
- **Universe expansion via hybrid prompt pool** in `services/daily_drop.py`:
  - 50% chance: pick from the 30 canonical themed scenes
  - 50% chance: procedurally assemble a *fresh canon* scene from word banks of 30 subjects × 28 actions × 24 objects × 18 locations × 14 moods ≈ **5 million unique combinations**
  - Selection seeded by `sha256(user_key + date_utc)` for deterministic same-user-same-day outputs (no re-rolling, locks for 24h)
- Race-safe: per-(user, date) `asyncio.Lock` + MongoDB `$setOnInsert` upsert. Cache hit returns in ~295 ms.
- Verified: 2 different anonymous users hitting the same day got `"A & the Liquidity"` (fresh) and `"First Scanner"` (canonical) — totally different images.

### Admin gallery (creator-only access for future reference)
- New endpoint **`GET /api/ai/daily-drops/admin?admin_wallet=…&limit=&offset=&date_utc=&include_images=`** — paginated, gated by an in-code allow-list of admin wallets (`we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`, `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`).
  - `include_images=false` by default — keeps the gallery payload lean (just metadata)
  - `include_images=true` returns full base64 data URLs
- New endpoint **`GET /api/ai/daily-drops/admin/{drop_id}?admin_wallet=…&user_key=…&date_utc=…`** — fetches a single drop's full image_base64 for download/reuse.
- New MongoDB indexes: `daily_drops((user_key, date_utc))` unique + `(created_at -1)` for fast pagination.
- Non-admin wallets receive a clean 403.

### Bullpug AI chatbot: fullscreen mode
- New `Expand`/`Shrink` button in the chat header (next to Minimize / Close).
- When toggled, the chat window expands to `inset-0` (mobile) / `inset-4 sm:inset-8` (desktop) — effectively 90%+ of the viewport. Rounded corners drop on mobile for an edge-to-edge feel.
- ESC key exits fullscreen but keeps the chat open (only ESC inside fullscreen — doesn't close the modal).
- The daily-drop card, image-generation outputs, and ReactMarkdown content all scale beautifully because they were already responsive (`max-w-[95%]`, `w-full h-auto`).
- Verified: fullscreen mode reaches 1856×1016 on a 1920×900 viewport; ESC returns to 420×560 panel.

### Files touched
- `/app/backend/services/daily_drop.py` — full rewrite for per-user model + word-bank assembler
- `/app/backend/routers/ai_chat.py` — `_maybe_attach_daily_drop` takes `user_key`; new `daily-drops/admin` endpoints
- `/app/backend/server.py` — new `daily_drops` indexes on startup
- `/app/frontend/src/components/EnhancedAIAssistant.js` — `isFullscreen` state, ESC handler, Expand/Shrink toggle, dynamic className for fullscreen layout

### Today's verified drops
- Active server records:
  - `anon-user-A-session` → "A & the Liquidity" (fresh procedural)
  - `anon-user-B-session` → "First Scanner" (canonical)
  - `(current viewer)` → "Token Meditation" (canonical)

---
## Iteration 104 — Daily Bullpug Drop (May 12, 2026)

### Concept
One AI-generated Neuko-universe image, rotated every UTC day, revealed inline in
the AI chatbot's first response of the day. "Gone after midnight UTC — only one
drop per day" creates FOMO; the share button turns every viewer into an amplifier.

### Backend
- **New service**: `/app/backend/services/daily_drop.py`
  - **30 themed prompts** spanning the Neuko canon (Cometside Vigil, Moon-Cheese Float, Alarm Red, Dawn Over Newpug, The Bull Constellation, PugChain Memory, Magenta River, Lunar Flag, Festival of Barks variants, etc.)
  - Deterministic per-UTC-day selection: `sha256(date_utc) % len(prompts)` so the SAME theme rotates predictably (one image per day total, not per user)
  - MongoDB cache: collection `daily_drops`, keyed by `date_utc`. Brand-style suffix auto-injected. Uses `gemini-3.1-flash-image-preview` via Emergent LLM Key.
  - **Race-safe**: per-date `asyncio.Lock` cache + `$setOnInsert` upsert so concurrent first-callers don't double-generate
  - Generation cost: **~1 image per day, period** (not per user). Verified: cache hit returns in ~260ms.

- **`routers/ai_chat.py`**:
  - `EnhancedChatMessage` gains a `daily_drop_last_seen: Optional[str]` field
  - `_maybe_attach_daily_drop()` helper attaches today's drop only when `last_seen != today_utc`. Wired into all chat return paths (image-gen, normal, error fallback) so the drop never gets lost.
  - **New endpoint `GET /api/ai/daily-drop`** returns the drop directly (for testing or static pages later)

### Frontend (`EnhancedAIAssistant.js`)
- Sends `daily_drop_last_seen` from localStorage on every chat request
- When response contains `daily_drop`, prepends a **special drop card** above the assistant's text reply:
  - Full-bleed image, "● TODAY'S BULLPUG DROP" yellow pulse badge, theme title, scene description, FOMO line, and "SHARE THE DROP" CTA
  - `data-testid="daily-drop-card"` + `data-testid="daily-drop-share-btn"`
- Sets `localStorage["bullpug_daily_drop_last_seen"]` to today's UTC date on receipt → drop never re-appears later in the same UTC day
- Share button uses Web Share API → clipboard fallback → X intent

### Verified end-to-end
- Test 1 (no seen flag): `daily_drop` attached ✓
- Test 2 (seen today): drop skipped ✓
- Test 3 (seen yesterday): drop re-attached ✓
- Test 4 (cache hit): 259ms ✓
- UI screenshot: "Magenta River" drop rendered beautifully on first message; second message did NOT re-show the card ✓

### Today's drop on record
- 2026-05-12 → **"Magenta River"** (PugChain transaction visualised as a glowing river of magenta light)

---
## Iteration 103 — Trailer Replay/Share + Chatbot Image Generation (May 12, 2026)

### Origins Trailer: replay + share
- `OriginsTrailer.js`: added a `window` custom event `bullpug:open-trailer` so any component can programmatically re-open the modal. Auto-open suppression via `localStorage["bullpug_origins_trailer_seen_v1"]` still applies for first-visit-only behaviour.
- New **Share** button next to "Enter the canon" in the modal — uses Web Share API (mobile native sheet) with fallbacks: clipboard copy + toast confirmation, last-resort opens `twitter.com/intent/tweet` in a new tab.
- New action block on `/lore` (between epilogue and canon anchor, `data-testid="lore-actions-block"`):
  - "Carry it forward · Spread the signal across the Mindverse." headline
  - **Watch Trailer** button (`lore-replay-trailer-btn`) → fires the custom event → modal re-opens
  - **Share the Origins** button (`lore-share-btn`) → same Web Share / clipboard flow
- Verified end-to-end: auto-open suppressed on second visit ✓, Watch-Trailer click re-opens modal ✓, share button present in modal ✓.

### Bullpug AI chatbot: inline image generation via Gemini Nano Banana
- `routers/ai_chat.py`: new helpers `_detect_image_prompt()` + `_generate_image_response()`.
  - **Slash commands**: `/image …` or `/img …`
  - **Natural-language intent** (regex): `draw/generate/create/make/render/paint/sketch [an image/picture/art/illustration/render/drawing/photo/portrait/pic] of …` — requires an image keyword to avoid false positives like "draw a conclusion"
  - Style suffix injected automatically: "Cinematic, hyperdetailed digital art in the Bullpug / Neuko universe aesthetic. Vivid neon-on-dark palette with mint green/magenta/gold accents." No text/logos/watermarks.
  - Model: `gemini-3.1-flash-image-preview` via Emergent LLM Key
  - Response shape adds `image_base64` (data-URL with mime), `kind: "image"`, plus a short Bullpug-flavoured caption
  - Graceful fallback responses for empty output or upstream errors
- `EnhancedAIAssistant.js`: assistant messages now carry `generatedImage` + `kind`. When present, the bubble renders the image inline with a "GENERATED BY NANO BANANA" badge (green pulse dot).
- Placeholder updated to "Ask me anything · try /image …" so the feature is discoverable.
- Verified end-to-end with three test cases: slash command ✓ (1408px image inlined), natural language "Draw me a picture of …" ✓, normal lore question does NOT trigger image generation ✓.

### Files touched
- `/app/backend/routers/ai_chat.py`
- `/app/frontend/src/components/OriginsTrailer.js`
- `/app/frontend/src/components/EnhancedAIAssistant.js`
- `/app/frontend/src/pages/Lore.js`

---
## Iteration 102 — Origins Trailer 152 BPM Heartbeat Audio (May 12, 2026)

### Audio synthesis (no scipy needed)
- `generate_origins_trailer.py` extended with `synthesize_heartbeat_audio()`:
  - 15-second mono WAV at 48 kHz (Opus's preferred rate)
  - 152 BPM lub-dub pattern: pitch-glided sub-bass kick (95→55 Hz lub, 80→45 Hz dub) with exp-decay envelope, 0.16s gap between lub and dub, 0.395s period between heartbeats
  - Ambient drone layer: single-pole lowpass-filtered white noise + 55 Hz + 110 Hz harmonic sub-bass (pure numpy, no scipy)
  - Volume envelope: silent 0–1.5s → fade-in to 0.55 over 2s → hold through scenes 1–2 → crescendo to 0.9 during festival fireworks (10–13.5s) → fade-out to 0 (13.5–15s)
  - Peak-normalised to 0.82 to prevent clipping

### Re-encoded MP4 + WebM with audio
- Fixed Opus encoder error by switching sample rate from 44.1 → 48 kHz
- Bumped H.264 from Baseline 3.0 → **Baseline 3.1** (3.0 doesn't permit 720×1280@30fps; 3.1 does)
- New file sizes: `origins-trailer.mp4` 5.2 MB (H.264 + AAC 96k), `origins-trailer.webm` 2.0 MB (VP9 + Opus 96k)

### Verified live in Playwright/Chromium
- `webkitAudioDecodedByteCount: 43338` confirms audio is being decoded
- Mute toggle works: `muted: True → False, volume: 1`
- Hint text auto-updates from "TAP THE SPEAKER FOR SOUND · ESC TO SKIP" → "ESC TO SKIP" once unmuted
- Speaker icon swaps from muted-X to active-volume on click
- One-shot localStorage gating still works (second visit suppressed)

---
## Iteration 101 — Origins Trailer + Moon Cheese Transparency Fix (May 12, 2026)

### Cosmic Runner: moon cheese white-background bug fix
- User reported a white square framing the moon cheese sprite in-game (visual defect screenshot supplied).
- Root cause: `/app/frontend/public/moon-cheese.png` was stored as RGB (no alpha channel), with a near-white background `(237–254 RGB)` baked in.
- Fix: Flood-fill from all four corners using a brightness>215 + grayscale-spread<35 mask, plus rim anti-aliasing for bright pixels (220<brightness<245). Cropped to bounding box (1024×1024 → 627×742) to remove dead space. New file is RGBA with alpha=0 at all corners and solid yellow centre. Original kept at `moon-cheese.original.png` as backup.

### Origins Trailer (autoplays on first /lore visit)
- New one-shot generator `/app/backend/scripts/generate_origins_trailer.py` produces a 15-second vertical (720×1280) trailer:
  - 3 scenes × 5s each: Newpug City (zoom-in pan right) → Snout Scanner (zoom-out hold) → Festival of Barks (zoom-in pan left)
  - 0.5s crossfades between scenes; 0.5s fade-in/fade-out on overall video
  - Pillow-based Ken Burns rendering piped directly into a single ffmpeg invocation that tees into BOTH `origins-trailer.mp4` (H.264 Constrained Baseline, ~5 MB) and `origins-trailer.webm` (VP9, ~1.8 MB)
- New component `/app/frontend/src/components/OriginsTrailer.js`:
  - Auto-opens on first visit to `/lore` (localStorage key `bullpug_origins_trailer_seen_v1`)
  - `<video>` element with both `<source>` tags so Chromium variants without H.264 licensing fall through to WebM automatically
  - 9:16 aspect container (reserves space immediately even before metadata loads)
  - Muted-autoplay (browser-friendly), with mute toggle, close X, ESC-to-skip, click-outside-to-dismiss, and "Enter the canon" CTA in the bottom overlay
  - Footer hint: "TAP THE SPEAKER FOR SOUND · ESC TO SKIP"
  - All elements have `data-testid` for QA
- Wired into `/app/frontend/src/pages/Lore.js` (`<OriginsTrailer />` rendered as the first child).
- Verified end-to-end: video reaches readyState=4 in <5s, playback advances at real time (6.06s → 8.57s after 2.5s wait), modal dismisses, localStorage flag set, second visit suppressed.

### Next Action Items (rolling list)
- 🔴 Top up escrow to 0.5–1 SOL on `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT` (currently ~0.02 SOL)
- 🟡 Provide $BULLPUG mint address so I can wire token entries to the pot with on-chain SOL conversion
- 🟡 Drop new lore chapters whenever ready — paste them straight into the `bullpug_knowledge` block in `/app/backend/routers/ai_chat.py`

---
## Iteration 100 — Chatbot Lore Canonization + Lore Hero Images (May 12, 2026)

### Chatbot full lore upgrade (`/app/backend/routers/ai_chat.py`)
- Replaced the old 7-block `bullpug_knowledge` system prompt section with the new **Neuko Universe Canon** (8 chapters condensed but faithful to the canonical text):
  1. The Cosmic Birth
  2. A Different Kind of Entity
  3. The Mindverse He Calls Home
  4. Newpug City
  5. The Bullpughans
  6. The Festival of Barks
  7. The Signal in the Noise
  8. The Legacy
  + Canon Anchor (Neuko universe / unmapped Mindverse)
- Added a new **HIDDEN LORE PROTOCOL** instruction block. When users probe specific antagonist/canon terms (`G*BOY`, `Neuko`, `G-304`, `152 BPM`, `Saint Juniper`, `Harmony`, `IRIS`, or events not in canon), the bot:
  - Acknowledges the question is the right one to ask
  - Drops one small atmospheric, narratively-consistent breadcrumb (feelings/rumors only, never new concrete facts)
  - Encourages the user to come back ("Mindverse rewards persistence")
  - Uses the fallback phrase "That's a thread the Festival hasn't pulled on yet — come back. I'll tell you when the signal's clearer." when it genuinely doesn't know
- Updated the **P2P ARENA** section from `COMING SOON` → `LIVE` with the new mechanics (coin flip + winner pot, min/max, 60s countdown, 25% rake → Cosmic Runner Jackpot, automatic on-chain payouts).
- Updated the **AI TRADING BOT** section to `HIBERNATED` — bot lists itself as dormant and redirects users to the live products (Cosmic Runner, P2P Arena).
- Verified live with three test prompts: origin story matches new canon ✅; G*BOY query triggers Hidden Lore Protocol response with breadcrumb ✅; P2P Arena correctly described as live with winner pot mechanics ✅.

### Lore page hero images (`/app/frontend/public/lore/`)
- One-shot generation script `/app/backend/scripts/generate_lore_images.py` using Gemini Nano Banana (`gemini-3.1-flash-image-preview`) via Emergent LLM Key.
- Generated 3 images:
  - `newpug-city.png` (1 MB) — pug-faced skyscrapers, green holographic aurora barks, pug nebula in the sky
  - `snout-scanner.png` (740 KB) — close-up of the Guardians' titanium snout-shaped scanner with holographic blockchain lattice
  - `festival-of-barks.png` (1 MB) — coin & bone fireworks over Newpug City, moon-cheese parade floats
- `Lore.js` `<Chapter>` component extended with optional `image` + `imageAlt` props; aspect-[16/9] hero with bottom gradient fade for seamless blend into the chapter body.
- Wired into chapters: Newpug City (#4), Bullpughans (#5), Festival of Barks (#6). `loading="lazy"` on each.
- Each image has `data-testid="chapter-{slug}-image"` for QA.

---
## Iteration 99 — Origins Lore Rewrite (Neuko Universe Canon) (May 11, 2026)
### Changes
- Replaced `/app/frontend/src/pages/Lore.js` entirely (previous fairy-tale style → new Neuko-universe canon).
- New structure: 8 chapters + epilogue + canon anchor:
  1. The Cosmic Birth
  2. A Different Kind of Entity
  3. The Mindverse He Calls Home
  4. Newpug City
  5. The Bullpughans
  6. The Festival of Barks
  7. The Signal in the Noise
  8. The Legacy
- Introduced antagonist canon: MITER-Corp, Aurelian Systems, Saint Juniper Research Campus, Harmony, IRIS, G*BOY, G-304 modulation trials (152 BPM). Highlighted in red to make them visually distinct from Bullpug-aligned concepts.
- Refactored chapter rendering into a reusable `<Chapter>` component (icon + gradient + title + body) — reduces duplication and keeps visual rhythm consistent across all 8 sections.
- Inline `<H color>` highlighter for in-text word emphasis (Mindverse, CryptoCanis, PugChain, Guardians, etc.).
- Each chapter has a unique `data-testid` for QA (chapter-cosmic-birth, chapter-different-entity, chapter-mindverse, chapter-newpug-city, chapter-bullpughans, chapter-festival, chapter-signal, chapter-legacy, lore-canon-anchor).
- Removed unused `useTranslation` import.
- Kept the animated stars canvas + gradient overlay from the original.

### Pending (user-driven)
- AI chatbot must be taught the full Neuko-universe lore. User said they'd do it personally; offered to embed the canonical text into the chatbot system prompt when they're ready.

---
## Iteration 98 — P2P Arena Hardening + Cosmic Runner Jackpot Ticker (May 6, 2026)
### Persistence (crash-safety)
- `state/pot_state.py` — pot is now mirrored to MongoDB collection `db.active_pot` (single doc with `_id="active"`). Mutations flow through `await persist_pot()`; startup calls `await load_pot()` before scheduler boots.
- `server.py` startup loads pot before `start_scheduler()` so an in-flight round survives crashes/redeploys.
- Defensive `load_pot()` rebuilds `total_lamports = sum(entries.amount_lamports)` if it ever drifts from stored total.

### Float → integer lamports (accounting safety)
- `pot_state.py`: added `sol_to_lamports`, `lamports_to_sol`, `LAMPORTS_PER_SOL`.
- `routers/pot.py`: rewritten — `MIN_BET_LAMPORTS = 5_000_000`, `MAX_BET_LAMPORTS = 10_000_000_000`, all cumulative caps & weighted random in lamport space; rake = `(total_lamports * 250) // 10000` (basis points).
- `routers/betting.py`: coinflip create_challenge uses lamport math; bet_amount_lamports / rake_lamports / payout_lamports all stored on the challenge doc.
- `routers/admin.py`: admin force-draw uses the same lamport math.
- Verified: 3 sequential 0.1 SOL joins produce exactly `300_000_000` lamports / `0.3 SOL`, no float drift.

### Cosmic Runner Jackpot Ticker (homepage)
- New component `frontend/src/components/JackpotTicker.js` — pulls `/api/prize-pool/status` every 15s, animated count-up of total SOL, live 1-second countdown to next payout, #1 prize card (25% share), funding-source explainer.
- Replaced `BotQuickStats` on HomePage.js with `JackpotTicker` (final piece of bot UI removal).
- Color story: yellow→green gradient on the jackpot total, glass-morphism cards with subtle grain overlay.

### Tests (iteration 98)
- 13/13 backend tests passed (`/app/backend/tests/test_arena_iteration98.py`)
- Crash-recovery test: kill backend mid-round → entry survives restart with same id+lamports
- Math test: 0.123 SOL coinflip → rake=6_150_000 lamports, payout=239_850_000 lamports, sum-check = 246_000_000 (= 0.246 SOL = 0.123 × 2)
- Auto-draw e2e: scheduler fires at countdown end, `pot_results` doc has lamport fields, `prize_pool.total_sol` grows by exactly `rake × 0.25`

### Escrow / payout reality check
- DISTRIBUTION_WALLET (also escrow): `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`, balance ~**0.02 SOL** (low)
- Self-funds via player deposits but needs operating capital for tx fees + timing-skew. Recommend top-up to 0.5–1 SOL before public launch.

---
## Iteration 97 — P2P Arena Restored + Hibernation Cleanup (May 6, 2026)
### Trading Bot Hibernation Cleanup
- Removed leftover `pendingEntryCount` state & `fetchPendingEntries` call from `Navbar.js`
- Removed unused `BotHealthDashboard` import from `AdminPanel.js`
- Confirmed App.js has no routes for TradingJournal / AITrader / PugBurn
- Navbar `data-testid="nav-arena"` added; "SOON" badge removed from P2P Arena

### P2P Arena Pivot (pot weighted lottery + coin flip)
- **Restored** `BettingArena.js` (916 lines) from git commit `53d8738` — was downgraded to a "Coming Soon" waitlist
- **Updated bet limits**: min 0.01 → **0.005 SOL** in `betting.py` + `pot.py`; max single-entry 10 SOL enforced in pot (already enforced in coinflip)
- **Stacking enforced**: per-wallet cumulative cap of 10 SOL per pot round; multiple entries merge into one player card with entry_count in `get_pot_data()` aggregation
- **Countdown trigger fixed**: now requires **2 unique wallets** (not 2 entries) to start the 60s countdown — prevents single player stacking from triggering premature draw
- **`/draw` endpoint secured**: now rejects premature draws (403 unless admin `X-Admin-Wallet` header matches `DISTRIBUTION_WALLET` or `draw_at` has elapsed)
- **Atomic challenge accept**: `accept_challenge` uses `find_one_and_update` to prevent concurrent double-accept races (409 on conflict)
- **`randbelow` guard**: fixed ValueError risk when total_amount_sol < 1e-6
- **New scheduler job `pot_auto_draw`**: runs every 5 seconds, auto-fires `draw_pot_winner` once countdown expires — pot now settles without manual intervention
- **Prize-pool contribution confirmed live**: 25% of every rake (both coinflip and pot) flows into `prize_pool` collection → Cosmic Runner leader jackpot. Verified end-to-end:
  - Pot run: 0.03 SOL total → 0.00075 rake → 0.000188 to prize pool ✅
  - Coinflip: 0.02 pot → 0.0005 rake → 0.000125 to prize pool ✅
- **Cleared 10 stale RateLimitTest challenges** cluttering the open-challenges list
- **Frontend updates**: quick-bet chips (`0.005, 0.05, 0.1, 0.5, 1` for coinflip; `0.005, 0.1, 0.5, 1, 2` for pot), min/max hints, `<Badge>` "25% of rake → Cosmic Runner Jackpot"
- **Backend tests**: iteration_97.json — 16/16 passed (100%) covering config, stacking caps, unique-player countdown, aggregation, coinflip boundaries, full e2e with prize-pool verification

### New Pot/Coinflip Config (live)
- Rake: 2.5% (`RAKE_PERCENT` in `utils/config.py`)
- Min bet: 0.005 SOL
- Max single bet: 10 SOL
- Per-wallet cumulative pot cap: 10 SOL per round
- Countdown: 60 seconds, starts at 2+ unique wallets
- Auto-draw: every 5s by scheduler
- Prize pool share: 25% of rake (→ Cosmic Runner top-10 leaderboard)
- Distribution wallet: `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`

