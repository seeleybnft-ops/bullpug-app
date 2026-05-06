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
- **Lore expansion (Origins page)** — user will provide additional lore text; also train AI chatbot with full lore so users can Q&A.
- **Escrow operating capital top-up** — User to send ~0.5–1 SOL to `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT` so payouts have buffer for tx fees and timing-skew before flow self-funds. Current balance ~0.02 SOL.
- Plushie Sales & interactive NFT Gallery

### P2 - Future
- Web/Mobile Push Notifications
- Achievement badges & "Share on X"
- Trading Competitions with leaderboards

### Administrative
- Remove private access gate when user confirms testing is complete

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

