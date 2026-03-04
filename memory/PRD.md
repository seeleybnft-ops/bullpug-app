# Bullpug - Trading Journal & Memecoin Platform

## Original Problem Statement
Build a full-stack, responsive website for the memecoin "Bullpug". The application includes a "Cosmic Runner" game, a P2P Betting Arena, user profiles, and an AI-powered Trading Journal with multi-chain wallet support.

## Core Features

### 0. AI Trading Bot (NEW - Phase 2: Semi-Automated)
- **Route**: `/ai-trader`
- **Custody**: Delegated wallet system (program-controlled)
- **DEX Integration**: Jupiter Aggregator API for best swap routes
- **Technical Analysis Engine**:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
  - Moving Averages (7, 14, 21, 50 day)
- **Strategies**:
  - Momentum/Trend Following
  - Mean Reversion
  - Combined (both strategies)
- **Token Categories**:
  - Safer: SOL, USDC, USDT, JUP, PYTH, RNDR
  - High Risk: BONK, WIF, RAY, ORCA
  - User chooses which risk level to trade
- **Risk Management**:
  - Min position: 0.05 SOL
  - Max position: 1 SOL
  - User-configurable stop-loss (5-50%)
  - User-configurable take-profit (10-100%)
- **Workflow**:
  1. User connects wallet and accepts disclaimer
  2. AI scans markets for signals
  3. Signals displayed with entry/SL/TP prices
  4. User approves/rejects each trade
  5. On approval, wallet signs transaction
- **Disclaimer**: Clear risk warnings, no responsibility for losses
- **Future**: Fully automated mode (Phase 3)

### 1. My Journal (Trading Journal)
- **Dashboard Tab**: Trading statistics, P&L charts, win rate, best/worst trades
- **Portfolio Value Tab**: Multi-chain token holdings grouped by chain (Solana, Ethereum, Base, Arbitrum)
  - Token name displayed as main title
  - Contract address with copy-to-clipboard button
  - "Add to Watchlist" button for each token
  - "View on Explorer" link for each token
- **Import Tab**: Auto-detect DEX trades from connected wallets
- **Trades Tab**: Manual trade logging and history
- **Exit Simulator Tab**: Monte Carlo simulations for exit strategies
- **Achievements Tab**: Trading badges, community benchmarks, social sharing
- **Watchlist Tab**: Track favorite tokens with price alerts
- **Backup Tab**: Cloud backup and restore functionality

### 2. Enhanced AI Assistant - "Bullpug AI" (LIVE)
- **Identity**: Bullpug AI embodies the cosmic guardian from the lore
- **Bullpug Professor Icon**: Custom professor avatar for AI assistant trigger and chat header
- **Image Analysis**: Users can upload images for AI analysis (charts, token screenshots, etc.)
  - Supports JPG, PNG, WebP up to 5MB
  - AI identifies tokens, charts, prices, and references live market data
- **Lore Knowledge**: Full knowledge of Bullpug origins, Newpug City, PugChain, Guardians, Snout Scanners, Festival of Barks, Bullpughans
- **Real-time market data**: 
  - Live prices from DexScreener (primary) and CoinGecko (fallback)
  - **Fear & Greed Index** - Real-time market sentiment
  - **Global Market Data** - Total market cap, 24h volume, BTC/ETH dominance
  - **Solana Ecosystem** - Top gainers, highest volume tokens
  - **Crypto News** - Latest events and trending topics
- **Market Intelligence**: Understands price movements, trading volumes, global events affecting crypto
- **Persistent MongoDB Memory**: Chat history saved to MongoDB, not cleared until user manually clears
  - `GET /api/ai/history/{wallet}` - Retrieve chat history
  - `POST /api/ai/history/save` - Save chat history
  - `DELETE /api/ai/history/{wallet}` - Clear chat history (manual only)
- **Tab-aware context**: Provides relevant suggestions based on active tab
- **Trending coins**: Shows trending Solana tokens with volumes
- **Price queries**: Ask about any crypto price with 24h change, market cap, volume
- **No auto-scroll**: Manual scroll with "Scroll to bottom" button
- **Tabs**: Chat, Top Picks, Insights (Holdings tab removed)
- **Top Picks**: Auto-refreshes every HOUR with fresh recommendations
  - Safe Picks: >$100K volume, >$100K liquidity, FDV >$1M, -20% to +50% change
  - Volatile Picks: >$50K volume, >$20K liquidity, >30% or <-20% change (momentum)
  - **Contract Addresses**: Clickable to copy, shown for each coin
  - **DEX Trade Links**: Direct links to DexScreener for each coin
  - **Add to Watchlist**: Star button to save coins directly from Top Picks
- Available across ALL My Journal tabs
- **API Endpoints**:
  - `GET /api/ai/sentiment` - Fear & Greed Index
  - `GET /api/ai/market` - Full market overview with sentiment + Solana ecosystem
  - `GET /api/ai/news` - Latest crypto news
  - `GET /api/ai/tradeable-assets` - Live priced assets for trade form dropdown

### 2.1 Trade Form with Live Pricing
- **Asset Dropdown**: Select from trending coins with live prices
- **Fixed Order Major Coins**: SOL, ETH, BTC, BNB, DOGE, XRP (always at top)
- **Contract Address Lookup**: Paste any contract address to find and add a token
  - DexScreener API lookup for token info
  - Auto-populates symbol, name, and current price
  - Tokens added via contract stay in "Your Tokens" section
- **Search**: Filter assets by symbol or name
- **Custom Entry**: Add any custom asset symbol manually
- **Auto-fill Price**: Selecting an asset auto-fills the entry price field
- **Live Data**: Prices and 24h % changes shown for each asset
- **DexScreener Fallback**: If CoinGecko rate-limited, prices fetched from DexScreener

### 3. Auto-Trade Fetching (Import Tab) - P1 COMPLETE
- **Solana**: Fetches transaction history via Alchemy API
- **EVM (Ethereum, Base, Arbitrum)**: Fully functional with Alchemy
- **Trade Detection**: Identifies DEX swaps and token transfers
- **Import to Journal**: One-click import of detected trades as draft entries
- **DetectedTrades Component**: Shows trades grouped by chain with import options
- **P1 UX Enhancements** (Feb 2025):
  - Auto-scan on wallet connect
  - Progress indicator showing which chain is being scanned
  - Better empty states with chain badges
  - Chain filter dropdown with trade counts
  - Help tip explaining import process

### 4. Homepage Market Dashboard Widget - NEW
- **Fear & Greed Index Gauge**: Visual gauge showing market sentiment (0-100)
  - Color-coded: Red (Extreme Fear) to Green (Extreme Greed)
  - Contextual tips: "Market in fear - potential buying opportunity"
- **Top Solana Gainers**: Live top 3 movers with % change
- **Highest Volume**: Top 3 tokens by 24h volume
- **Auto-refresh**: Every 5 minutes
- **LIVE indicator**: Real-time data badge
- **CTA Panel**: "Chat with Bullpug AI" and "Open Journal" buttons

### 5. P2P Betting Arena
- Create and join crypto bets
- Escrow-based wagering
- Solana smart contract (deployment blocked by disk space)

### 6. Cosmic Runner Game
- Endless runner with Bullpug character
- Unlockable skins
- Leaderboard system

### 5. Reflections Calculator
- Calculate passive income from Blowfish trading fees
- Volume slider range: up to $10,000,000

### 6. Watchlist (NEW)
- Track favorite coins with price alerts
- Shows profit/loss since adding to watchlist
- Copy contract address, direct DEX trade links
- Synced with wallet address (Solana or EVM)
- API: GET/POST/DELETE for CRUD operations

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

### February 2025 (Latest)
- [x] **AI Market Data Fix v2** - Added CoinPaprika as reliable fallback for major L1 coins:
  - CoinGecko (primary) → CoinPaprika (fallback for L1s) → DexScreener (memecoins)
  - SOL, BTC, ETH, BNB, XRP, DOGE now show accurate market cap in billions/trillions
  - Memecoins (BONK, WIF) use DexScreener token API for accurate FDV/volume
  - No more incorrect $778K market cap for SOL (now shows $48B correctly)
- [x] **AI Market Data Fix** - Fixed incorrect volume and market cap reporting:
  - Added known token addresses for direct DexScreener lookup (BONK, WIF, PEPE, SHIB, JUP)
  - Improved volume aggregation across all trading pairs
  - Better market cap vs FDV distinction
  - Human-readable formatting (e.g., $517.81M instead of $517810594)
  - Includes liquidity data for DexScreener sources
- [x] **Phantom Wallet Fix** - Resolved wallet connection issues in Phantom's in-app browser:
  - Disabled autoConnect when in Phantom/in-app browsers
  - Direct Phantom provider connection for better compatibility
  - UI hints for Phantom browser users
- [x] **Major Refactoring Completed** - Code maintainability improvements:
  - TradingJournal.js: Reduced from ~1460 lines to 462 lines (68% reduction)
  - JournalAIAssistant.js: Reduced from 1002 lines to 334 lines (67% reduction)
  - Extracted 9 reusable components to `/components/journal/`:
    - Dashboard.js - Trading statistics and charts
    - TradesList.js - Trade list with filters
    - TradeForm.js - Modal for logging trades
    - ExitSimulator.js - Monte Carlo simulation
    - CloudBackup.js - Backup/restore functionality
    - TopPicksSection.js - AI coin recommendations
    - ChatSection.js - AI chat interface
    - InsightsSection.js - AI insights display
    - index.js - Central exports
- [x] **Watchlist Tab** - Track favorite coins with live price updates, profit/loss tracking
- [x] **Auto-Trade Fetching (Import Tab)** - Fully functional with multi-chain support
- [x] Watchlist CRUD API (add, remove, clear, get with price enrichment)
- [x] Integrated Watchlist as new tab in My Journal
- [x] Watchlist removal button (StarOff icon) working

### December 2025
- [x] Enhanced AI Chat with session memory
- [x] Real-time price fetching (CoinGecko + DexScreener)
- [x] Portfolio holdings grouped by chain
- [x] Homepage footer updated to match navbar
- [x] Reflections volume slider max increased to $10M
- [x] CoinGecko rate limiting workaround (60s cache)
- [x] "LIVE" indicator on AI responses with real-time data
- [x] **Portfolio Value Live Prices** - Unified price service using DexScreener as primary source (no rate limits)

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

### RESOLVED: CoinGecko Rate Limiting
- **Primary source: DexScreener API** (no API key, generous rate limits)
- CoinGecko as fallback when DexScreener unavailable
- 60-second price caching
- Unified price service at `backend/utils/price_service.py`

## Upcoming Tasks (P1)
1. ~~Complete Auto-Trade Fetching (Alchemy Transfers API)~~ ✅ Done
2. Integrate frontend with deployed smart contract (when unblocked)
3. ~~AI Trading Bot - Phase 2: Implement actual trade execution via Jupiter~~ ✅ Done

## Completed This Session (Dec 2025)
- [x] Reverted navbar from dropdown to flat layout with AI Trader standalone link
- [x] Added AI Trading Bot card to Homepage Ecosystem section with "NEW" badge
- [x] Generated custom AI Trading Bot image for homepage
- [x] AI Trader nav link has purple highlight with Bot icon
- [x] Mobile navigation includes AI Trader link
- [x] All AI Trader backend endpoints verified working
- [x] **Moved "Top Picks" from Bullpug AI (Journal) to AI Trading Bot "Tokens" tab**
- [x] **TopPickCard component with Copy CA button, DEX Trade link, Analyze button**
- [x] **New `/api/ai-trader/new-pairs` endpoint for potential runners (new pairs <24h)**
- [x] **Connected Insights tab to logged trades via `/api/journal/trades/{wallet}/stats`**
- [x] **Removed Top Picks tab from Journal AI Assistant**
- [x] **Fixed ai_suggestions to read from correct `trading_journal` collection**
- [x] **Renamed "AI Trading Bot" to "Bullpug Trading Bot" throughout**
- [x] **Updated Trading Bot image to user-provided bull pug with glowing eyes**
- [x] **Reordered Ecosystem section: My Journal, Origins, Bullpug AI Assistant, Bullpug Trading Bot, Cosmic Runner, P2P Arena**
- [x] **Moved Recent Jackpot Winners below Ecosystem section**
- [x] **Changed hero button from "Cosmic Runner" to "My Journal"**
- [x] **Added 5-minute auto-scan feature for signals with countdown timer**
- [x] **Added Quick Trade button on signal cards for one-click trading**
- [x] **P1 COMPLETE: Jupiter DEX swap execution with wallet signing**
- [x] **New `/api/ai-trader/swap-transaction` endpoint using Jupiter lite-api**
- [x] **New `/api/ai-trader/execute-swap` endpoint to record completed trades**
- [x] **Frontend Quick Trade executes real swaps via Jupiter with wallet signature**
- [x] **Updated Origins image to flying bullpug with horns**
- [x] **Editable SOL position in Signals - manual input field for Quick Trade**
- [x] **Removed Approve button from Signals (only Reject + Quick Trade)**
- [x] **Duplicate signal prevention - filters out same-token duplicates**
- [x] **Contradicting signal filtering - keeps higher RSI priority**
- [x] **Fixed Analyze button - now accepts contract_address for unknown tokens**
- [x] **Analyze endpoint looks up tokens via DexScreener when not in known list**
- [x] **Quick Sell from Positions tab with editable amount**
- [x] **Risk Calculator showing Max Loss, Potential Profit, Risk:Reward ratio**
- [x] **Quick Buy from Tokens tab with editable amounts, adds to positions**
- [x] **Tab order: Signals → Tokens → Positions → History**
- [x] **New `/api/ai-trader/add-position` endpoint for direct token purchases**
- [x] **New `/api/ai-trader/close-position` endpoint with P&L calculation**

## Future Tasks (P2)
- Deploy smart contract to Mainnet
- Re-enable Plushie Sales shop
- Re-enable NFT Gallery
- AI Trading Bot - Phase 3: Fully automated trading mode
- ~~Refactor TradingJournal.js into smaller components~~ ✅ Done

## License
MIT License - Bullpug 2025
