# Bullpug.com - PRD & Implementation Tracker

## Original Problem Statement
Build a full-stack website for the memecoin "Bullpug" with space-themed cosmic guardian lore.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Solana Web3.js, react-i18next, react-markdown
- **Backend:** FastAPI, WebSockets, Pydantic, slowapi, emergentintegrations (LLM)
- **Database:** MongoDB
- **Email:** SendGrid
- **AI/LLM:** GPT-4o via Emergent LLM Key

---

## Latest Update: Feb 18, 2026 - User Profile & AI Suggestions System

### New Features Implemented

#### 1. User Profile System (COMPLETE)
Full profile management with wallet-based authentication:
- **Profile CRUD:** GET/PUT /api/profile/{wallet_address}
- **Profile Fields:** display_name, bio, twitter_handle, telegram_handle, discord_handle, website_url
- **Profile Pictures:** Upload custom image OR select from owned game skins
- **Game Stats Display:** high_score, total_mooncakes, games_played
- **Owned Skins:** Shows all skins available as profile pictures

**API Endpoints:**
- `GET /api/profile/{wallet_address}` - Get or create profile
- `PUT /api/profile/{wallet_address}` - Update profile
- `POST /api/profile/{wallet_address}/upload-image` - Upload custom image
- `GET /api/profile/{wallet_address}/skins` - Get available skins

#### 2. AI-Powered Trading Suggestions (COMPLETE)
Real GPT-4o integration via Emergent LLM Key:

**Exit Simulator AI Insight:**
- Analyzes Monte Carlo simulation results
- Provides personalized trading advice based on:
  - Simulation probability percentiles
  - Live market prices (CoinGecko)
  - User's trading journal history
- Markdown-formatted responses with actionable tips

**Trading Journal Daily Pulse:**
- Daily AI-generated insights for traders
- Analyzes user's trade history for patterns
- Tracks overnight market changes for held assets
- Provides personalized focus areas

**API Endpoints:**
- `POST /api/ai-suggestions/exit-simulator` - Get AI insight after simulation
- `GET /api/ai-suggestions/journal-daily/{wallet_address}` - Daily journal insight

#### 3. Solana Smart Contract (COMPLETE)
Trustless P2P betting smart contract using Anchor framework:
- **Coinflip:** 1v1 provably fair betting with commit-reveal scheme
- **Pot Game:** Winner-takes-all multi-player with slot hash randomness
- **PDAs:** All funds escrowed in Program Derived Addresses
- **Automatic Payouts:** Winners receive SOL directly on-chain
- **2.5% Rake:** Sent to treasury PDA

**Files:**
- `/app/solana-program/programs/bullpug-betting/src/lib.rs`
- `/app/solana-program/client/bullpug-betting-client.ts`
- `/app/solana-program/README.md`

---

## Previous Session Changes
- Power-ups (Shield, Magnet, 2x Score) with spawn/collection/effects
- Dynamic moving background with parallax and stage themes
- Mobile swipe controls
- Bullpug orientation fixed (faces down the lane)
- Original Guardian skin with fluffy pug

---

## Testing Status

### Latest: iteration_23.json - 100% pass rate
All features verified:
- Game Guide section with all items documented
- Enhanced mooncake visuals working
- Star-burst rays, sparkles, shimmer effects confirmed
- Game mechanics (start, lane change, jump, score) all working
- Leaderboard displaying correctly

---

## Code Architecture

```
/app/
├── backend/
│   ├── routers/
│   │   ├── ai_suggestions.py  # GPT-4o AI suggestions (NEW)
│   │   ├── betting.py         # P2P betting + auto-payout
│   │   ├── profile.py         # User profile CRUD (NEW)
│   │   ├── forum.py           # Community forum
│   │   ├── journal.py         # Trading journal
│   │   ├── messages.py        # Direct messages (DMs)
│   │   ├── prize_pool.py      # Jackpot system
│   │   ├── simulator.py       # Exit simulator (Monte Carlo)
│   │   └── ...
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AISuggestionBubble.js  # AI insight component (NEW)
│   │   │   ├── JackpotDisplay.js      # Jackpot UI
│   │   │   ├── RecentWinners.js       # Winners display
│   │   │   └── SkinStore.js
│   │   ├── pages/
│   │   │   ├── ProfilePage.js      # User profile page (NEW)
│   │   │   ├── SpeedRunGame.js     # Main game
│   │   │   ├── BettingArena.js     # P2P betting
│   │   │   ├── ExitSimulator.js    # Monte Carlo sim + AI
│   │   │   ├── TradingJournal.js   # Trade logging + AI
│   │   │   ├── Forum.js            # Community posts
│   │   │   └── Messages.js         # DMs
│   │   └── config/
│   │       └── skins.js
│   └── package.json
├── solana-program/                    # Smart contract (NEW)
│   ├── programs/bullpug-betting/
│   │   └── src/lib.rs               # Anchor program
│   ├── client/
│   │   └── bullpug-betting-client.ts
│   ├── Anchor.toml
│   └── README.md
└── memory/
    └── PRD.md
```

---

## Key Files Reference

```
/app/frontend/src/pages/SpeedRunGame.js
  - Lines 1064-1233: Enhanced mooncake rendering (shiny effects)
  - Lines 1904-2028: Game Guide section inline
  - Lines 37-74: POWERUP_TYPES, STAGE_BACKGROUNDS constants
  - Lines 268-290: spawnPowerup()
  - Lines 498-550: Background element movement
  - Lines 1592-1660: Mobile touch controls
```

---

## Task Status

### COMPLETED (This Session)
1. ✅ Game Guide section with all items documented
2. ✅ Enhanced mooncake visuals (shinier, brighter)
3. ✅ Refactoring foundation (constants, hooks, components)

### COMPLETED (Previous Sessions)
1. ✅ Power-ups with shiny sparkle effects
2. ✅ Bullpug oriented to face down lane
3. ✅ Dynamic moving background with parallax
4. ✅ Stage-based color themes
5. ✅ Mobile swipe/tap controls
6. ✅ Betting Arena (P2P Coin Flip, Pot System)
7. ✅ Exit Simulator (Monte Carlo GBM)
8. ✅ Trading Journal with dashboard/CSV/PDF export
9. ✅ Community Forum with posts/replies
10. ✅ Direct Messages (DMs) with WebSocket

### Upcoming (P1)
- Deployment to bullpug.com

### Backlog (P2)
- NFT Gallery page
- Plushie Sales shop page
- Further game refactoring (split SpeedRunGame.js into modules)

---

## Admin Wallets
- `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`
- `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`

---

## PRD Feature Completion Status

| Feature | Status | Notes |
|---------|--------|-------|
| Cosmic Runner Game | ✅ Complete | Power-ups, backgrounds, guide, controls |
| P2P Betting Arena | ✅ Complete | Coin flip, pot system, 2.5% rake |
| Exit Simulator | ✅ Complete | Monte Carlo GBM, PDF export |
| Trading Journal | ✅ Complete | Dashboard, CSV/PDF, cloud backup |
| Community Forum | ✅ Complete | Posts, replies, categories |
| Direct Messages | ✅ Complete | Real-time WebSocket DMs |
| Tokenomics Display | ✅ Complete | Token info page |
| Reflections Calculator | ✅ Complete | Calculator tool |
| Wallet Integration | ✅ Complete | Solana wallet adapter |
| NFT Gallery | 🔄 Hidden | Ready for implementation |
| Plushie Shop | 🔄 Hidden | Ready for implementation |
| Deployment | ⏳ Pending | Ready for bullpug.com |

---

## Latest Update: Feb 17, 2026 - Prize Pool Reward System

### Prize Pool System (COMPLETE)
**Revenue Sources (25% each goes to prize pool):**
- P2P Betting rake (coin flip + pot)
- Skin purchases

**Distribution:**
- Every 3 days, top 10 leaderboard players receive SOL prizes
- Prize split:
  1. 1st: 25%
  2. 2nd: 15%
  3. 3rd: 12%
  4. 4th: 10%
  5. 5th: 9%
  6. 6th: 8%
  7. 7th: 7%
  8. 8th: 6%
  9. 9th: 5%
  10. 10th: 3%

**Features Implemented:**
- Live jackpot display on game page with countdown timer
- Prize breakdown showing SOL amounts per rank
- Recent winners section on home page (auto-refreshes)
- Automatic payouts via APScheduler (checks every 5 mins)
- Payout history tracking in database

**New Files:**
- `backend/routers/prize_pool.py` - Prize pool management & payouts
- `backend/utils/scheduler.py` - APScheduler for auto-payouts
- `frontend/src/components/JackpotDisplay.js` - Jackpot UI
- `frontend/src/components/RecentWinners.js` - Winners display

**API Endpoints:**
- `GET /api/prize-pool/status` - Pool total, countdown, breakdown
- `GET /api/prize-pool/recent-winners` - Last payout winners
- `POST /api/prize-pool/execute-payout` - Manual/auto payout trigger
