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
- **Blockchain:** Solana (Public RPC + Helius fallback, Jupiter DEX, Jito MEV protection)
- **AI:** OpenAI GPT-4o via Emergent LLM Key
- **Market Data:** CoinGecko (primary) + DexScreener (fallback with rate-limit protection)

## Access & Credentials
- **Private Access Gate:** `bullpug2026`
- **User Wallet:** `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`
- **Custodial Wallet:** `CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg` (NEW - generated after previous key loss)
- **Note:** Helius API key is invalid. System uses public Solana RPC as primary.

## Completed Features (as of March 27, 2026)
- Full AI Trading Bot with A-Tier features (multi-layer signals, trailing stops, DCA, MEV protection)
- **Multi-source market data:** CoinGecko batch API (primary) + DexScreener (cached fallback with rate limit protection)
- **Auto-trade scan scheduler** — scans every 5 minutes via APScheduler
- **First live trade executed:** PYTH buy 0.044 SOL @ $0.03912 (TX: 4h7E6PJm...)
- Internal Fund Ledger with per-user virtual balance tracking
- **Deposit detection fixed:** Compares on-chain vs ledger totals (not stored balance_lamports)
- **Position sizing capped** to available balance minus 0.006 SOL reserve (covers sell reserve + tx fees)
- Live pricing on locked-in-trades positions
- Deposit auto-detection with 5-second polling
- Admin Reconciliation Dashboard
- Post-deploy initialization script (idempotent)
- Rake Back system (2.5% on profitable trades)
- Trading Mode Selector (conservative/normal/aggressive/sniper)
- Private Access Gate for testing period
- Runner detection via CoinGecko Solana meme coins category
- Exit monitor with stop-loss, take-profit, and trailing stop

## Key Architecture
- **Market Data Service:** `services/market_data.py` — CoinGecko batch prefetch (single API call for all known tokens) + DexScreener with 2-min backoff on 429
- **Runner Detector:** `services/runner_detector.py` — CoinGecko meme coins + DexScreener boosted tokens (with shared rate limit backoff)
- **Fund Ledger:** `user_ledger` collection is source of truth for per-user balances
- **Balance Check Chain:** Position sizing caps → Ledger balance check → Custodial balance check → Execute
- **RPC Fallback:** Public Solana RPC (primary) → Helius (secondary, currently invalid key)

## Current Ledger State (qdegDg...7Rjs)
- Available: 0.006 SOL
- Locked in trades: 0.044 SOL (PYTH position)
- Total balance: 0.05 SOL
- On-chain: ~0.004 SOL + 97.73 PYTH tokens

## Backlog (Prioritized)
### P0 - Immediate
- Refactor `ai_trader.py` (4200+ lines → modular services)

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
