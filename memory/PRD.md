# Bullpug - Memecoin Full-Stack Application

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

