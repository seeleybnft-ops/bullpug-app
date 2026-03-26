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
- **Blockchain:** Solana (Helius/Alchemy RPC, Jupiter DEX, jito MEV protection)
- **AI:** OpenAI GPT-4o via Emergent LLM Key

## Access & Credentials
- **Private Access Gate:** `bullpug2026`
- **User Wallet:** `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`
- **Custodial Wallet:** `B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC`

## Completed Features (as of March 27, 2026)
- Full AI Trading Bot with A-Tier features
- **Auto-trade scan scheduler** — scans every 5 minutes for new trade opportunities
- Internal Fund Ledger with per-user virtual balance tracking
- **Live pricing** on locked-in-trades positions (computed from current_price vs entry_price)
- Deposit auto-detection with 5-second polling in deposit modal
- Withdrawal modal with ledger balance validation
- **Ledger balance check** before executing any trade (prevents overspending)
- **Admin Reconciliation Dashboard** — correctly accounts for SOL in token positions separately from available SOL
- Post-deploy initialization script (idempotent, restores ledger on fresh DB)
- Admin endpoint to sync pre-existing open positions into ledger
- Rake Back system (2.5% on profitable trades)
- Trading Mode Selector (conservative/normal/aggressive/sniper) — all modes work
- Expanded safer token scan list (JUP, PYTH, RNDR, BONK, RAY, WIF, HNT, JITO)
- "Normal" mode correctly uses user's stored confidence threshold without adjustment
- Private Access Gate for testing period

## Key Architecture
- **Fund Ledger:** `user_ledger` collection is source of truth for per-user balances
- **Reconciliation Formula:** drift = on_chain_SOL - available_SOL - platform_rake (token positions excluded since SOL was converted to tokens)
- **Auto-trade Scheduler:** `auto_trade_scan_cycle` runs every 5 min, iterates all wallets with auto_trade_enabled=true
- **Post-deploy Init:** `services/post_deploy_init.py` runs once on fresh DB, restores all known ledger state

## Current User Ledger State (qdegDg...7Rjs)
- Available: 0.05 SOL
- Locked in trades: 0.033049 SOL (4 open positions: RENDER, PYTH, JUP x2)
- Total balance: 0.083049 SOL
- Reconciliation: Healthy (drift = 0)

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
