# Bullpug - Trading Journal & Memecoin Platform

## Original Problem Statement
Build a full-stack, responsive website for the memecoin "Bullpug". The application includes a "Cosmic Runner" game, a P2P Betting Arena, user profiles, and an AI-powered Trading Journal with multi-chain wallet support.

## Core Features

### 1. My Journal (Trading Journal)
- **Dashboard Tab**: Trading statistics, P&L charts, win rate, best/worst trades
- **Portfolio Value Tab**: Multi-chain token holdings grouped by chain (Solana, Ethereum, Base, Arbitrum)
- **Import Tab**: Auto-detect DEX trades from connected wallets
- **Trades Tab**: Manual trade logging and history
- **Exit Simulator Tab**: Monte Carlo simulations for exit strategies
- **Achievements Tab**: Trading badges, community benchmarks, social sharing
- **Backup Tab**: Cloud backup and restore functionality

### 2. Enhanced AI Assistant (LIVE)
- **Real-time market data**: Fetches live prices from CoinGecko and DexScreener
- **Session-based memory**: Maintains conversation context
- **Tab-aware context**: Provides relevant suggestions based on active tab
- **Trending coins**: Shows trending Solana tokens
- **Price queries**: Ask about any crypto price
- **No auto-scroll**: Manual scroll with "Scroll to bottom" button
- **Top Picks**: Auto-refreshes every HOUR with fresh recommendations
  - Safe Picks: >$100K volume, >$100K liquidity, FDV >$1M, -20% to +50% change
  - Volatile Picks: >$50K volume, >$20K liquidity, >30% or <-20% change (momentum)
- **Wallet Holdings**: Shows live holdings from connected wallets via Alchemy
- Available across ALL My Journal tabs

### 3. P2P Betting Arena
- Create and join crypto bets
- Escrow-based wagering
- Solana smart contract (deployment blocked by disk space)

### 4. Cosmic Runner Game
- Endless runner with Bullpug character
- Unlockable skins
- Leaderboard system

### 5. Reflections Calculator
- Calculate passive income from Blowfish trading fees
- Volume slider range: up to $10,000,000

## Tech Stack
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI, Wagmi, Solana Wallet Adapter
- **Backend**: FastAPI (Python), MongoDB
- **Integrations**: 
  - OpenAI GPT-4o (via Emergent LLM Key)
  - CoinGecko API (with caching)
  - DexScreener API
  - Alchemy SDK (multi-chain)

## API Endpoints

### AI Chat (LIVE)
- `POST /api/ai/chat` - Enhanced chat with real-time data
- `GET /api/ai/prices` - Get live major crypto prices
- `GET /api/ai/price/{symbol}` - Get specific coin price
- `GET /api/ai/trending` - Get trending Solana coins

### Portfolio
- `GET /api/portfolio/combined` - Multi-chain portfolio balances
- `GET /api/portfolio/prices` - ETH/SOL prices (cached)

### Achievements
- `GET /api/achievements/{user_id}` - User badges and stats

## What's Been Implemented

### December 2025
- [x] Enhanced AI Chat with session memory
- [x] Real-time price fetching (CoinGecko + DexScreener)
- [x] Portfolio holdings grouped by chain
- [x] Homepage footer updated to match navbar
- [x] Reflections volume slider max increased to $10M
- [x] CoinGecko rate limiting workaround (60s cache)
- [x] "LIVE" indicator on AI responses with real-time data

### Previous Sessions
- [x] Unified Journal & Portfolio page
- [x] Unified Wallet Connector (single button)
- [x] Achievement badges and social sharing
- [x] Exit Simulator tab
- [x] Multi-chain wallet support (Solana, EVM)

## Known Issues & Blockers

### BLOCKED: Solana Smart Contract Deployment
- Cannot install Solana/Anchor CLI due to disk space
- Workaround: README with local deployment instructions

### MITIGATED: CoinGecko Rate Limiting
- Added 60-second price caching
- Fallback prices when rate limited
- DexScreener as secondary source

## Upcoming Tasks (P1)
1. Complete Auto-Trade Fetching (Alchemy Transfers API)
2. Integrate frontend with deployed smart contract (when unblocked)

## Future Tasks (P2)
- Deploy smart contract to Mainnet
- Re-enable Plushie Sales shop
- Re-enable NFT Gallery
- Refactor TradingJournal.js into smaller components

## License
MIT License - Bullpug 2025
