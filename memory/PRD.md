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
- Trading Competitions with leaderboards
- Plushie Sales & interactive NFT Gallery

### P2 - Future
- P2P Betting Arena
- Web/Mobile Push Notifications
- Achievement badges & "Share on X"

### Administrative
- Remove private access gate when user confirms testing is complete
