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

## Completed Features (as of March 2026)
- Full AI Trading Bot with A-Tier features (signal intelligence, MEV protection, trailing stops, DCA exits, sniper mode)
- Internal Fund Ledger with per-user virtual balance tracking
- Rake Back system (2.5% on profitable trades)
- Deposit auto-detection (on-chain balance comparison)
- Withdrawal modal with ledger balance validation
- Admin Reconciliation Dashboard (on-chain vs virtual balance, drift detection, per-user breakdown)
- Trading Mode Selector (conservative/normal/aggressive/sniper)
- Private Access Gate for testing period
- Bot Performance Scorecard
- Community Spotlight section
- Clipboard copy with async error handling
- Custom branding with user-provided images
- Deployment-ready (no native dependencies, cleaned requirements.txt)

## Key Architecture
- **Fund Ledger:** `user_ledger` collection is source of truth for per-user balances
- **Platform Rake:** Pre-existing on-chain balance (0.008767 SOL) attributed to `__platform__` wallet as rake
- **Deposit Flow:** User sends SOL to custodial address → clicks "Confirm Deposit" → `detect-deposit` endpoint compares on-chain vs stored balance → records difference in ledger
- **Withdrawal Flow:** User requests withdrawal → validated against virtual `available_sol` → on-chain transfer + ledger debit

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
