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
- **Helius API Key:** `c7c37557-61df-4b9d-9661-b3d9c5be3aa8` (valid, free tier)

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

## Current Ledger State
- Available: ~0.129 SOL
- Positions: WIF, JUP, RAY, PYTH (4 open, all with valid entry prices)
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
- Fix Helius API key on production (currently expired)
- Remove private access gate when user confirms testing is complete
