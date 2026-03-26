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
- **Blockchain:** Solana (Public RPC primary, Helius fallback), Jupiter DEX, Jito MEV protection
- **AI:** OpenAI GPT-4o via Emergent LLM Key
- **Market Data:** CoinGecko batch API (primary) + DexScreener (cached fallback with rate-limit protection)

## Access & Credentials
- **Private Access Gate:** `bullpug2026`
- **User Wallet:** `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`
- **Custodial Wallet:** `CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg`
- **Note:** Helius API key is invalid. System uses public Solana RPC as primary.

## Architecture After Refactoring

### Backend Code Organization
```
/app/backend/
├── routers/
│   ├── ai_trader.py          (2320 lines) — Settings, analysis, signals, positions, swaps
│   ├── price_alerts.py       (306 lines)  — NEW: Price alert CRUD + breakout scanning
│   ├── custodial_wallet.py   — Wallet management, deposit detection, trade execution
│   └── ledger.py             — Balance, history, admin reconciliation
├── services/
│   ├── auto_trader_engine.py (1606 lines) — NEW: Scan-and-execute + exit monitoring
│   ├── market_data.py        — NEW: Multi-source CoinGecko batch + DexScreener cached
│   ├── runner_detector.py    — CoinGecko meme coins + DexScreener discovery
│   ├── token_price.py        — Multi-source price resolution (DexScreener→CoinGecko→fallback)
│   ├── ledger.py             — Balance math and P&L calculations
│   └── post_deploy_init.py   — Safe DB initialization (never drops custodial_wallets)
└── utils/
    ├── database.py            — MongoDB connection (single source of truth)
    └── scheduler.py           — APScheduler (5-min scan, 1-min exits, etc.)
```

### Key Data Flow
1. **Deposit:** On-chain SOL → detect-deposit → ledger `deposit` entry
2. **Trade:** Scanner → CoinGecko/DexScreener data → TA + AI signals → Jupiter swap → ledger `trade_open` + `fee` entries
3. **Exit:** Price monitor → TP/SL/trailing check → Jupiter sell → ledger `trade_close` + `rake` entries
4. **Balance:** `available = SUM(deposits) - SUM(trade_opens) - SUM(fees) + SUM(trade_closes)`

## Completed Features
- Full AI Trading Bot with A-Tier features
- **Multi-source market data** (CoinGecko primary + DexScreener cached fallback)
- **First live trade:** PYTH buy 0.044 SOL @ $0.03912 (TX confirmed on-chain)
- **Transaction fee tracking:** Ledger auto-deducts fee gap after each trade
- **Live position pricing:** Positions show current market price via CoinGecko/DexScreener
- Internal Fund Ledger with per-user tracking
- Deposit auto-detection (compares on-chain vs ledger totals)
- Admin Reconciliation Dashboard
- Rake Back system (2.5% on profitable trades)
- **Code refactoring:** ai_trader.py 4261→2320 lines (45% reduction)
- Runner detection via CoinGecko Solana meme coins
- Exit monitor with stop-loss, take-profit, trailing stop
- Private Access Gate for testing

## Current Ledger State
- Available: 0.003956 SOL (matches on-chain)
- Locked: 0.044 SOL (PYTH position, live value ~0.044022)
- Fees: 0.002044 SOL (transaction fees tracked)
- Total: ~0.048 SOL (from 0.05 deposited)

## Backlog (Prioritized)
### P1 - Upcoming
- Trading Competitions with leaderboards
- Plushie Sales & interactive NFT Gallery

### P2 - Future
- P2P Betting Arena
- Push Notifications
- Achievement badges & "Share on X"
- Daily Trading Digest via Telegram

### Administrative
- Remove private access gate when testing period ends
- Get valid Helius API key (current one is invalid)
