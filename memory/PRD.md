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
  - **Breakout Strategy (NEW)** - Detects price breaking through support/resistance levels
  - Combined (all three strategies)
- **Token Categories**:
  - Safer: SOL, USDC, USDT, JUP, PYTH, RNDR
  - High Risk: BONK, WIF, RAY, ORCA
  - User chooses which risk level to trade
- **Tokens Tab Features**:
  - Safe Picks: 5 low-risk tokens
  - Volatile Picks: 5 high-risk/high-reward tokens
  - New Pairs: 5 recently bonded tokens (on Raydium/Orca/Meteora)
  - **HOT Badge**: Tokens with >$100K 24h volume
  - **TRENDING Badge**: Tokens with >50% 24h price change
- **Risk Management**:
  - Min position: 0.05 SOL
  - Max position: 1 SOL
  - User-configurable stop-loss (5-50%)
  - User-configurable take-profit (10-100%)
- **Social Sharing** (NEW):
  - Share Trade Results with P/L on X (Twitter)
  - Share AI Signals with custom formatting
  - Share Portfolio Performance (weekly/monthly)
  - Share Leaderboard Rankings
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

## Completed This Session (Dec 2025 - Latest)
- [x] **PugBurn Page** - New Solana account cleanup service at `/pugburn`
  - Bullpug branding with flame icon and orange/red styling
  - Feature cards: Reclaim SOL, Clean Wallet, Safe & Secure
  - Scans for empty token accounts and displays reclaimable SOL
  - Backend endpoint `/api/pugburn/scan/{wallet}` uses Solana RPC
  - Sol-Incinerator API key stored securely in backend/.env
  - Supports both SPL Token and Token-2022 program accounts
  - Backend RPC proxy for reliable transaction submission
- [x] **Enhanced P/L Display in Positions Tab**
  - Shows unrealized P/L in percentage, SOL, and USD
  - Displays entry price, current price, and current value
  - Backend fetches live SOL price for USD conversions
- [x] **Instant UI Update on Quick Sell**
  - Position removed immediately from UI (optimistic update)
  - Uses setPositions() filter before API call completes
  - No page refresh required after selling
- [x] **Tokens Tab Enhancement (December 2025)**
  - Fixed to display 15 pairs total: 5 Safe, 5 Volatile, 5 New Pairs
  - New Pairs now only shows BONDED tokens (graduated to Raydium/Orca/Meteora)
  - Excludes pump.fun tokens - must be on major DEXes
  - Criteria: Created within 14 days, min $15K liquidity, min $10K volume
  - Backend endpoint `/api/ai-trader/new-pairs` returns bonded pairs only
- [x] **Breakout Trading Strategy (March 2026)**
  - New strategy detecting price breaking through support/resistance levels
  - Uses Bollinger Bands and Moving Averages for S/R detection
  - Integrated into combined_strategy for multi-strategy analysis
  - False breakout detection reduces confidence when RSI extreme
- [x] **HOT & TRENDING Badges (March 2026)**
  - HOT badge (🔥) for tokens with >$100K 24h volume
  - TRENDING badge (📈) for tokens with >50% price change
  - Displayed on TopPickCard in Tokens tab
- [x] **Social Sharing Features (March 2026)**
  - Share Trade Results on X with P/L branding
  - Share AI Signals with entry/target/stop prices
  - Share Portfolio Performance (weekly/monthly summaries)
  - Share Leaderboard Rankings with stats
  - New `/app/frontend/src/components/SocialShare.js` component
- [x] **Mobile Responsiveness (March 2026)**
  - Comprehensive mobile CSS in index.css
  - Horizontal scrolling tabs on mobile
  - Stacked layouts for cards and forms
  - Touch-friendly tap targets
  - Safe area padding for notched phones
  - Responsive text sizing utilities
- [x] **Real-Time Price Alerts (March 2026)**
  - New Alerts tab in AI Trading Bot
  - Breakout scanner auto-creates alerts for promising tokens
  - Browser notifications for triggered alerts
  - 5 API endpoints: create, get, delete, check, breakout-scan
  - Triggers on: >10% 1h price change with high volume
- [x] **Footer Ecosystem Links (March 2026)**
  - Added 7 ecosystem pages: My Journal, AI Trading Bot, PugBurn, P2P Arena, Cosmic Runner, Skin Store, Forum
- [x] **Bullpug AI Image Upload Fix (March 2026)**
  - Fixed ImagePart import error by using FileContent from emergentintegrations
  - AI chat now correctly analyzes uploaded images
- [x] **Telegram Bot Integration (March 2026)**
  - Bot username: @Bullpugbot
  - Users link Telegram via 6-character code
  - Receives breakout and price alerts in Telegram
  - Webhook configured for real-time message handling
  - Frontend UI in Alerts tab with modal for linking
- [x] **Enhanced Alert Cards (March 2026)**
  - DexScreener link button on each alert
  - Watchlist star to add/remove from watchlist
  - Quick Buy panel with amount input and buy button
  - Token address validation for quick buy
- [x] **Telegram Trading Commands (March 2026)**
  - `/trade` - Opens trading menu with quick actions
  - `/buy SYMBOL AMOUNT` - Buy tokens (e.g., /buy BONK 0.5)
  - `/sell SYMBOL %` - Sell position percentage (e.g., /sell BONK 50)
  - `/price SYMBOL` - Check current token price
  - `/trending` - View trending Solana tokens
  - `/positions` - View open trading positions
  - Orders stored in telegram_pending_orders collection
  - Updated /help with all trading commands

## Future Tasks (P2)
- Deploy P2P Arena smart contract (from local machine) and connect to app
- Re-enable Plushie Sales shop
- Re-enable NFT Gallery
- ~~AI Trading Bot - Phase 3: Fully automated trading mode~~ ✅ Done (March 2026)
- ~~Refactor TradingJournal.js into smaller components~~ ✅ Done

## P2P Arena - Coming Soon Page (March 2026)
- Replaced full betting functionality with "Coming Soon" landing page
- Features preview cards: P2P Coin Flip, Community Jackpot, Reputation System
- Explanation of smart contract-based trustless betting
- Email notification signup for launch alerts
- Links to other features (AI Trading Bot, Cosmic Runner, PugBurn)
- **Next Step**: Deploy Solana smart contract locally, then update app with program ID

## Recently Completed (March 2026)

### AI Trading Bot Phase 3 - Auto-Trade Settings
- New "Auto-Trade" tab in AI Trading Bot
- Toggle switch to enable/disable automated trading
- Configurable settings:
  - Trading Mode (Conservative/Moderate/Aggressive)
  - Min confidence threshold (50-90%)
  - Max position size (0.05-1 SOL)
  - Daily SOL limit (0.1-5 SOL)
  - Max daily trades (1-10)
  - Cooldown between trades (5-120 minutes)
  - Require multiple strategy agreement
  - Pause on loss option
- Activity log showing all auto-trade actions
- Real-time status display (active/paused)
- Today's statistics (trades executed, SOL used)
- Backend endpoints:
  - `GET /api/ai-trader/auto-trade/status/{wallet}`
  - `POST /api/ai-trader/auto-trade/toggle/{wallet}`
  - `PUT /api/ai-trader/auto-trade/settings/{wallet}`
  - `GET /api/ai-trader/auto-trade/logs/{wallet}`
  - `POST /api/ai-trader/auto-trade/scan-and-execute/{wallet}`

### Enhanced Cosmic Runner Game (Subway Surfers Style)
- **Background Music**: Procedurally generated cosmic ambient music with toggleable on/off
- **Enhanced Environmental Graphics**:
  - Floating asteroids in mid-distance with rocky textures
  - Space station silhouettes with blinking lights
  - Cosmic dust particles for depth
  - Comets with glowing trails
  - Enhanced nebulas with swirl effects
  - More star types (blue, yellow, white) with glow
  - Spiral galaxies with arm details
  - Ring planets (Saturn-like)
  - Distant suns with solar flares
- **Track Lights**: Glowing edge lights (green left, magenta right) that pulse and move with depth
- **Horizon Glow**: Pulsing glow effect at vanishing point
- **Enhanced Speed Lines**: Multiple colors (cyan, magenta, white) for dramatic warp effect
- **Music toggle button** in game header

### Gamification - Game Achievement Badges
- 21 achievement badges across multiple categories:
  - Score-based: First Steps, Space Cadet, Cosmic Explorer, Star Navigator, Galactic Legend
  - Stage-based: Level Up, Going Deep, Near the Edge, Multiverse Master
  - Moon Cheese: Cheese Nibbler, Cheese Hunter, Cheese Master, Moon Cheese Baron
  - Power-ups: Power Up!, Shield Master, Magnetic Personality, Star Collector
  - Special: Survivor, Perfectionist, Daily Player, Weekly Warrior
- Four rarity levels: Common, Rare, Epic, Legendary
- Achievement panel in game sidebar showing:
  - Quick stats (high score, moon cheese, max stage, total runs)
  - Visual badge grid with lock/unlock state
  - Progress bars for next milestones
  - Share on X button for game stats
- Achievements persist to localStorage
- Toast notifications when achievements unlock
- Compact view mode for in-game display

### Custodial Wallet for Automated Trading (March 2026)
- **Hybrid Model**: Server-side hot wallet for automated trade execution
- **Security Features**:
  - Fernet symmetric encryption for private keys
  - Encryption key stored in `CUSTODIAL_ENCRYPTION_KEY` environment variable
  - Keys never exposed in API responses
- **Deposit/Withdraw System**:
  - Max deposit limit: 0.5 SOL (for safety)
  - Deposit via direct transfer to custodial address
  - Withdraw returns funds to user's main wallet
  - Transaction fee buffer (10000 lamports) reserved
- **UI Components**:
  - Trading Wallet card in Auto-Trade tab
  - Balance display with available deposit space
  - Deposit address with copy button
  - Deposit/Withdraw action buttons
  - Deposit modal with instructions
- **Backend Endpoints**:
  - `GET /api/custodial-wallet/info/{wallet}` - Get/create wallet info
  - `GET /api/custodial-wallet/address/{wallet}` - Get deposit address
  - `POST /api/custodial-wallet/prepare-deposit` - Validate deposit
  - `POST /api/custodial-wallet/withdraw` - Process withdrawal
  - `GET /api/custodial-wallet/transactions/{wallet}` - Transaction history
- **Auto-Trade Integration**:
  - Auto-trade scanner checks custodial wallet balance before execution
  - Trades execute via Jupiter API using custodial wallet
  - Execution status tracked in position records and logs

### Multi-Chain Wallet Integration for Journal (March 2026)
- **NEW** MultiChainWalletManager component integrated into Journal Import tab
- Supports 4 chains: Solana, Ethereum, Base, Arbitrum
- Auto-scan feature scans all connected wallets on connect
- Chain selection checkboxes to filter which chains to scan
- Portfolio value display aggregated across chains
- Trade summary grouped by chain with recent trade preview
- **Quick Import All Button**: One-click import of all detected trades across all chains
  - Shows trade count in button label
  - Handles duplicate detection (skips already imported trades)
  - Success message shows imported count
  - Clears trades list after successful import
- **Backend Endpoints**:
  - `GET /api/wallet-trades/supported-chains` - Returns all supported chain configurations
  - `GET /api/wallet-trades/multi-chain` - Fetch trades from multiple chains in single request
  - `GET /api/wallet-trades/solana/{address}` - Fetch Solana DEX swaps
  - `GET /api/wallet-trades/evm/{address}?chain=ethereum|base|arbitrum` - Fetch EVM trades
  - `POST /api/wallet-trades/import-to-journal` - Import detected trades to journal

### Enhanced Cosmic Runner Game Graphics (March 2026)
- **Player Character Enhancements**:
  - Cyan/green rim light glow for better visibility
  - Enhanced golden warm glow around Bullpug character
  - Multi-layer shadow effect (outer blur + core shadow)
  - Gradient speed lines with varying widths (4 lines instead of 3)
- **Music System Fix**:
  - Audio preloading on page load for instant playback
  - Music preference persists in localStorage (bullpugMusicEnabled)
  - Auto-starts when game begins (if enabled) - satisfies browser autoplay policy
  - Improved error handling for autoplay restrictions
- **All existing enhancements preserved**:
  - Parallax star fields with nebulas
  - Floating asteroids with rocky textures
  - Space station silhouettes with blinking lights
  - Track edge lights (green/magenta)
  - Custom MP3 background music support

### Game Leaderboard Rewards Integration (March 2026)
- **NEW** LeaderboardPanel component with wallet linking for prize eligibility
- Features:
  - Connect wallet to player name for automatic prize payouts
  - Prize distribution preview showing potential winnings per rank
  - User rank highlighting with personalized prize estimate
  - Recent winners display from last payout
  - Real-time prize pool total synced with JackpotDisplay
- **Backend Endpoints**:
  - `GET /api/leaderboard` - Returns leaderboard with wallet_address field
  - `GET /api/leaderboard/wallet-link/{player_name}` - Check wallet link status
  - `POST /api/leaderboard/link-wallet` - Link wallet to player name
  - `POST /api/leaderboard/unlink-wallet` - Remove wallet link
- Prize payouts execute every 3 days to top 10 linked wallets

### Fully Automated Trading Mode Refinements (March 2026)
- **Trailing Stop-Loss**: 
  - Auto-raise stop-loss as price increases
  - Configurable trail distance (1-20%)
  - Endpoint: `POST /api/ai-trader/auto-trade/update-trailing-stops/{wallet}`
- **DCA on Dip (Scale-In)**:
  - Automatically add to position when price drops
  - Configurable dip threshold (2-15%)
  - Max scale-in additions (1-5)
  - Endpoint: `POST /api/ai-trader/auto-trade/check-scale-in/{wallet}`
- **Additional Settings**:
  - `auto_avoid_volatile_hours` - Skip trades during high volatility (default: true)
  - `auto_profit_target_alert` - Send alerts when profit targets hit (default: true)
- **Advanced Settings UI**:
  - Collapsible "Advanced Settings" section in Auto-Trade tab
  - Toggle switches for all new features
  - Sliders for percentage configurations
  - Real-time settings persistence

### Moon Cheese CORS Fix (March 2026)
- Generated new moon cheese collectible image using AI image generation
- Saved locally to `/frontend/public/moon-cheese.png` (885KB PNG)
- Updated `SpeedRunGame.js` and `GameGuide.js` to use local `/moon-cheese.png` path
- Eliminates CORS errors from external customer-assets URLs

### AI Signal Confidence Tuning (March 2026)
- **NEW** MarketConditionAnalyzer class in `ai_trader.py`
- Dynamically adjusts signal confidence based on:
  - **Volatility**: Extreme (-40%), High (-20%), Low (+5%)
  - **Market Trend**: Strong Bull (+20%), Bull (+10%), Bear (-15%), Strong Bear (-30%)
  - **Fear/Greed Index**: Extreme fear (+5% opportunity), Extreme greed (-10% caution)
- Fetches real-time BTC/SOL prices from CoinGecko
- Methods: `get_market_conditions()`, `adjust_confidence()`, `get_confidence_reason()`
- Trading recommendations pause during extreme volatility or strong bear markets

### Social Trading - Copy Trades (March 2026)
- **NEW** Complete copy trading system for following top traders
- **Trader Leaderboard**:
  - Ranks traders by PnL with configurable time periods (24h, 7d, 30d, all)
  - Shows win rate, total trades, best/worst trade, followers count
- **Follow/Unfollow Traders**:
  - Configurable copy percentage (10-100%)
  - Max position per trade (0.01-1.0 SOL)
  - Auto-copy toggle
- **Trader Profile Management**:
  - Enable/disable copy trading for your account
  - Set max copiers limit
  - Future: Performance fee on profits
- **Backend Endpoints**:
  - `GET /api/social-trading/leaderboard` - Top traders ranking
  - `GET /api/social-trading/profile/{wallet}` - Trader profile & stats
  - `POST /api/social-trading/profile/enable-copy-trading/{wallet}` - Toggle copy trading
  - `POST /api/social-trading/follow` - Follow a trader
  - `POST /api/social-trading/unfollow` - Unfollow a trader
  - `GET /api/social-trading/following/{wallet}` - Traders you follow
  - `GET /api/social-trading/followers/{wallet}` - Your followers
  - `PUT /api/social-trading/follow/settings` - Update copy settings
  - `GET /api/social-trading/copied-trades/{wallet}` - Copied trades history
- **Frontend Component**: `SocialTrading.js` with three tabs (Top Traders, Following, Copied Trades)
- **Integration**: New "Copy Trade" tab in Trading Bot page

### Copy Trade Execution Integration (March 2026)
- **Automatic Trade Copying**: When a trader adds a position via `add_position` endpoint, the trade is automatically copied to all active followers
- **Integration Point**: `backend/routers/ai_trader.py` line ~1455 calls `copy_trade_to_followers()`
- **Trade Copy Logic**:
  - Calculates copied position size based on follower's `copy_percentage` and `max_position_sol`
  - Skips positions below 0.01 SOL minimum
  - Records copied trade in `copied_trades` collection
  - Increments follower's `trades_copied` counter
- **Non-blocking**: Copy trading errors are caught and logged but don't break the main trade execution

### Advanced Copy Trading Notifications (March 2026)
- **NEW** Comprehensive notification system for copy trading events
- **Notification Types**:
  - `trade_copied` - When your position is copied from a followed trader
  - `new_follower` - When someone starts following you
  - `profit_alert` - When a position reaches 10%/25%/50%+ profit
  - `loss_alert` - For significant losses
  - `stop_loss_triggered` - When stop loss executes
- **Backend Endpoints**:
  - `GET /api/social-trading/notifications/{wallet}` - Fetch notifications with unread count
  - `GET /api/social-trading/notifications/settings/{wallet}` - Get notification preferences
  - `PUT /api/social-trading/notifications/settings/{wallet}` - Update preferences
  - `POST /api/social-trading/notifications/mark-read/{wallet}` - Mark as read (single or all)
  - `DELETE /api/social-trading/notifications/{wallet}/{notification_id}` - Delete notification
- **Notification Settings**:
  - Toggle each notification type on/off
  - `min_profit_alert_percent` (5-100%) - Minimum profit to trigger alert
  - `min_loss_alert_percent` (2-50%) - Minimum loss to trigger alert
- **Frontend Component**: `CopyTradeNotifications.js`
  - Real-time polling every 30 seconds
  - Unread badge count
  - Mark as read on click
  - Delete notifications
  - Collapsible settings panel
- **Integration**: New "Alerts" tab in SocialTrading component

### Performance Fee System for Copied Trades (March 2026)
- **Fee Range**: 5-15% (default 10%) - configurable per trader
- **How It Works**:
  - Traders set their performance fee percentage (5-15%)
  - When a follower's copied trade closes with profit, the fee is automatically calculated
  - Fee = gross_profit × (fee_percent / 100)
  - Follower receives net_profit = gross_profit - fee
  - Trader accumulates fees in total_fees_earned_sol
- **Database Collections**:
  - `performance_fees` - Records every fee transaction with audit trail
  - `trader_profiles.total_fees_earned_sol` - Cumulative fees earned
  - `copy_trading_follows.total_fees_paid_sol` - Fees paid per follow relationship
- **Backend Endpoints**:
  - `PUT /api/social-trading/fees/set-percentage/{wallet}?fee_percent=X` - Set fee (5-15%)
  - `GET /api/social-trading/fees/summary/{wallet}` - Combined earned/paid summary
  - `GET /api/social-trading/fees/earned/{wallet}` - Fees earned as a trader
  - `GET /api/social-trading/fees/paid/{wallet}` - Fees paid as a follower
  - `GET /api/social-trading/fees/leaderboard?period=7d|30d|all` - Top fee earners
- **Fee Calculation Function**: `calculate_and_collect_performance_fee()` in social_trading.py
  - Only charges fee on profitable trades (loss = no fee)
  - Sends "fee_earned" notification to trader
  - Updates profile and follow relationship totals
- **Frontend UI Updates**:
  - Trader cards show "{X}% fee" badge in leaderboard
  - Follow modal displays fee notice with percentage before confirming
  - Fee summary fetched and available in state (feeSummary)

### Push Notifications for Copy Trading (March 2026)
- **Purpose**: Real-time browser notifications for copy trading events
- **Supported Events** (copy trading focused):
  - `trade_copied` - When a trade is copied from followed trader
  - `new_follower` - When someone starts copying your trades
  - `fee_earned` - When you earn a performance fee
  - `profit_alert` - Significant profit on copied trades
  - `loss_alert` - Significant loss on copied trades
  - `stop_loss_triggered` - When stop loss activates on copied trade
- **Backend Endpoints**:
  - `GET /api/push-notifications/vapid-public-key` - Get VAPID key for browser subscription
  - `POST /api/push-notifications/subscribe` - Subscribe to push notifications
  - `POST /api/push-notifications/unsubscribe` - Remove subscription
  - `GET /api/push-notifications/subscriptions/{wallet}` - List active devices
  - `GET /api/push-notifications/preferences/{wallet}` - Get notification preferences
  - `PUT /api/push-notifications/preferences/{wallet}` - Update preferences
  - `POST /api/push-notifications/send-test/{wallet}` - Send test notification
  - `GET /api/push-notifications/history/{wallet}` - Notification history
- **Frontend Component**: `PushNotificationManager.js`
  - Subscribe/unsubscribe toggle
  - Preference toggles for each event type
  - Profit/loss threshold sliders (min_profit_percent, min_loss_percent)
  - Test notification button
  - Active devices display
- **Service Worker**: `sw-push.js` in public folder
  - Handles push events and displays browser notifications
  - Handles notification clicks (opens relevant app page)
- **Note**: Actual browser delivery requires VAPID keys in environment (VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY)

### Signal Analytics & Strategy Improvements (March 2026)
- **Purpose**: Analyze trading bot signal performance to improve confidence and success rates
- **Analysis Findings** (359 signals analyzed):
  - 74.5% of signals were low confidence (0.35-0.45) with only 3% approval rate
  - Momentum strategy generated 252 signals all at exactly 0.40 confidence
  - Combined strategy had highest avg confidence (0.62) but 0% approval
  - Only 8 out of 359 signals were approved (2.2% overall)
- **Improvements Implemented**:
  - Raised minimum signal threshold from 0.35 to 0.45 (~75% noise reduction)
  - Momentum strategy now requires MACD confirmation for all buy signals
  - Mean Reversion: tightened RSI thresholds (oversold < 30 instead of < 35)
  - Combined strategy: individual strategies must meet 0.45 confidence to count
  - Better handling of conflicting signals (returns "no signal" more often)
- **New Analytics Module** (`/api/signal-analytics/`):
  - `GET /performance-summary` - Strategy performance by period
  - `GET /confidence-analysis` - Confidence distribution with recommendations
  - `GET /strategy-comparison` - Compare strategies with quality scores
  - `GET /optimal-settings` - Recommended settings for auto-trading
  - `POST /track-outcome` - Track signal outcome at 1h/4h/24h for performance measurement
- **Database Collections**:
  - `signal_outcomes` - Tracks price changes and win/loss at different time intervals
- **Quality Score Formula** (0-100):
  - 40% weight: average confidence
  - 30% weight: approval rate
  - 15% weight: buy/sell balance
  - 15% weight: confidence consistency

### Multi-Chain Copy Trading (March 2026)
- **Purpose**: Extend copy trading to EVM chains (Ethereum, Base, Arbitrum)
- **Supported Chains**:
  - Solana (SOL) - Primary chain
  - Ethereum (ETH) - Chain ID 1
  - Base (ETH) - Chain ID 8453
  - Arbitrum (ETH) - Chain ID 42161
- **Wallet Linking**:
  - Link Solana and EVM wallets to single user identity
  - User ID format: `user_{address[:8]}`
  - Prevents duplicate wallet linking
- **Chain-Specific Copy Settings**:
  - `enabled` - Toggle copying for each chain
  - `copy_percentage` - 10-100% of trader's position
  - `max_position_native` - 0.01-10 in chain's native token
  - `auto_copy` - Automatic vs manual copy
- **Backend Endpoints** (`/api/multichain-copy/`):
  - `GET /supported-chains` - List all supported chains
  - `POST /wallets/link` - Link Solana + EVM wallets
  - `GET /wallets/{address}` - Get linked wallets by any address
  - `POST /follow` - Follow trader with multi-chain settings
  - `GET /following/{user_id}` - Get traders being followed
  - `PUT /chain-settings` - Update per-chain copy settings
  - `GET /leaderboard` - Unified leaderboard (filter by chain/period)
  - `GET /copied-trades/{user_id}` - Copied trades grouped by chain
  - `GET /stats/{user_id}` - Multi-chain stats and PnL
- **Frontend Component**: `MultiChainCopyTrading.js`
  - Wallet linking UI
  - Per-chain toggle switches
  - Unified leaderboard view
  - Copied trades table by chain
- **Database Collections**:
  - `multichain_wallets` - Linked wallets across chains
  - `multichain_follows` - Multi-chain follow relationships
  - `multichain_copied_trades` - Trades copied across chains

### Signal Analytics Dashboard (March 2026)
- **Purpose**: Visualize trading bot signal performance
- **Frontend Component**: `SignalAnalyticsDashboard.js`
- **Visualizations**:
  1. **Token Performance Heatmap**
     - Grid of tokens colored by average confidence
     - Shows signal count and buy/sell ratio per token
     - Color scale: red (<45%) → amber (50%) → green (>65%)
  2. **Confidence vs Approval Rate**
     - Bar chart showing approval rates by confidence bucket
     - Buckets: 0.35-0.40, 0.40-0.45, 0.45-0.50, 0.50-0.55, etc.
     - Helps identify optimal confidence thresholds
  3. **Strategy Quality Scores**
     - Ranked list of strategies by quality score (0-100)
     - Shows total signals, approval rate, buy/sell ratio
     - Recommendation for best strategy to prioritize
- **Tabs**:
  - Overview: Key metrics and strategy performance bars
  - Token Heatmap: Visual grid of token performance
  - Confidence Analysis: Detailed confidence distribution
  - Backtester: Interactive strategy backtesting
  - Recommendations: Optimal settings from analytics
- **API Integration**: Uses `/api/signal-analytics/*` endpoints
- **Period Selection**: 7 days, 30 days, 90 days

### Real-Time Signal Tracking & Backtester (March 2026)
- **Purpose**: Track signal outcomes and optimize strategy settings
- **Signal Tracking** (`POST /api/signal-analytics/track-prices`):
  - Fetches current prices for signals created in last 24 hours
  - Calculates PnL at 1h, 4h, and 24h intervals
  - Populates `signal_outcomes` collection for performance analysis
  - Uses DexScreener API with fallback to simulated prices
- **Strategy Backtester** (`POST /api/signal-analytics/backtest`):
  - Configurable parameters:
    - `min_confidence`: 0.35-0.80 (test different thresholds)
    - `strategy_filter`: momentum, mean_reversion, breakout, combined
    - `time_horizon`: 1h, 4h, 24h
    - `period_days`: 7-90 days of historical data
    - `win_threshold_percent`: 0.5-10% profit threshold
  - Returns comprehensive metrics:
    - Win rate, loss rate, avg PnL
    - Max drawdown, Sharpe ratio
    - Breakdown by strategy and confidence bucket
    - Actionable recommendations
- **Optimal Settings Finder** (`GET /api/signal-analytics/backtest/optimal`):
  - Runs multiple backtests with different configurations
  - Finds best combination of confidence threshold and strategy
  - Returns ranked list of top configurations with scores
- **Applied Optimizations** (based on backtest results):
  - `MIN_SIGNAL_CONFIDENCE`: 0.45 → 0.55 (72.5% win rate vs 45.6%)
  - `MIN_INDIVIDUAL_CONFIDENCE`: 0.50 (filters weak individual strategies)
  - Priority given to momentum + breakout agreement (historically best combo)
  - Combined strategy at 0.55 conf shows 76.9% win rate, +4.1% avg PnL
- **Frontend Component**: `StrategyBacktester.js`
  - Interactive config panel for backtest parameters
  - Visual results display with metrics and charts
  - "Find Optimal" button for automated optimization
  - Top configurations table

### Automated Signal Tracking System (March 2026)
- **Purpose**: Build real outcome data over time by tracking signal price changes
- **Configuration Endpoints**:
  - `GET /api/signal-analytics/auto-tracking/status` - Get tracking config and stats
  - `PUT /api/signal-analytics/auto-tracking/config` - Update tracking settings
  - `POST /api/signal-analytics/auto-tracking/run` - Execute tracking cycle
- **Configuration Options**:
  - `enabled` - Toggle automated tracking on/off
  - `track_interval_minutes` - How often to run (15-240 minutes)
  - `track_1h`, `track_4h`, `track_24h` - Enable/disable time intervals
- **How It Works**:
  - Fetches signals from last 25 hours
  - Gets current prices (DexScreener API with simulation fallback)
  - Calculates PnL based on signal type (buy/sell)
  - Stores outcomes at appropriate time intervals (1h, 4h, 24h)
  - Populates `signal_outcomes` collection for adaptive learning
- **Database Collections**:
  - `auto_tracking_config` - Tracking configuration
  - `tracking_runs` - History of tracking runs
  - `signal_outcomes` - Tracked outcomes with PnL data

### A/B Testing Mode (March 2026)
- **Purpose**: Run different confidence thresholds in parallel to validate backtest predictions
- **Endpoints**:
  - `POST /api/signal-analytics/ab-test/create` - Create new A/B test
  - `GET /api/signal-analytics/ab-test/list` - List all tests (filter by status)
  - `GET /api/signal-analytics/ab-test/{test_id}` - Get test details with win rates
  - `POST /api/signal-analytics/ab-test/{test_id}/record-outcome` - Record signal outcome
  - `PUT /api/signal-analytics/ab-test/{test_id}/status` - Update test status
- **Configuration**:
  - Two variants (A and B) with different confidence thresholds
  - Optional strategy filters per variant
  - Traffic split percentage (10-90%)
  - Status: active, paused, completed
- **Metrics Tracked Per Variant**:
  - Total signals, wins, losses, neutrals
  - Win rate (calculated)
  - Total PnL and average PnL
  - Statistical significance of winner (0-99% confidence)
- **Database Collection**: `ab_tests`

### Adaptive Learning System (March 2026)
- **Purpose**: Continuously improve win rate using real outcome data
- **Endpoints**:
  - `GET /api/signal-analytics/adaptive/current-settings` - Get recommended settings
  - `POST /api/signal-analytics/adaptive/apply` - Apply learned settings
  - `GET /api/signal-analytics/adaptive/history` - View settings history
- **What It Analyzes**:
  - Win rate by confidence bucket (0.40-0.45, 0.45-0.50, etc.)
  - Win rate by strategy (momentum, combined, mean_reversion)
  - Indicator patterns (RSI oversold/overbought, trend alignment)
- **Recommendations Generated**:
  - Optimal minimum confidence threshold
  - Best performing strategy
  - Whether to require trend alignment
  - Expected improvement over default settings
- **Current Learned Insights** (from 50 outcomes):
  - Combined strategy: **75% win rate**, +8.14% avg PnL (BEST)
  - High confidence (0.65+): **100% win rate** (small sample)
  - 0.60-0.65 confidence: **66.7% win rate**, +8.75% avg PnL
- **Frontend Component**: `AdaptiveLearning.js`
  - Learning tab with confidence/strategy breakdowns
  - Tracking tab showing outcome stats
  - A/B Testing tab for creating and monitoring tests
- **Database Collections**:
  - `signal_outcomes` - Input data for learning
  - `adaptive_settings` - History of applied settings

### Unified Auto-Trade & Analytics UI (March 2026)
- **Purpose**: Merged Signal Analytics and Auto-Trade tabs into a single unified view
- **Component**: `UnifiedAutoTrader.js`
- **Features**:
  - Analytics summary metrics displayed at top (Win Rate 24h, Avg Confidence, Recommended Min, Your Setting)
  - Auto-applies recommended settings from backtester when confidence below optimal
  - Internal tabs: Controls & Wallet, Trade Settings, Performance, Backtester, Adaptive AI
  - Trading wallet management integrated (deposit/withdraw)
  - Activity log showing all auto-trade actions
- **AITrader.js Changes**:
  - Removed separate "analytics" tab
  - "autotrade" tab now uses `UnifiedAutoTrader` component
  - Tab description shows "& Analytics" to indicate merged functionality

### Runner Detection System (March 2026)
- **Purpose**: Catch early momentum on new pairs before they "run"
- **Features**:
  - Fetches trending/boosted tokens from DexScreener
  - Analyzes pairs for runner potential using multiple criteria
  - Calculates a "Runner Score" (0-100) based on momentum, volume, buy pressure, and freshness
  - Integrates with auto-trade scan to include runner tokens alongside known tokens
- **Criteria**:
  - Min liquidity: $10,000
  - Min 24h volume: $50,000
  - Min 1h price change: +5%
  - Max 1h price change: +100% (avoid pump & dumps)
  - Min 1h transactions: 50
  - Max pair age: 72 hours
- **API Endpoint**: `/api/ai-trader/runners` - Lists discovered runner tokens with scores
- **Auto-Trade Integration**:
  - Runners are only scanned when `risk_level` is "high_risk" or "both"
  - Smaller position sizes for runners (max 0.1 SOL or 50% of normal max)
  - More aggressive take profit (100%) and stop loss (20%) for runners
  - Confidence boosted based on runner score and buy ratio

### MACD Calculation Fix (March 2026)
- Fixed MACD calculation to use proper EMA series instead of single values
- MACD histogram now correctly shows momentum divergence
- Added `_ema_series()` helper function for accurate signal line calculation

### Combined Strategy as Primary (March 2026)
- Auto-trade now uses combined strategy as the primary decision maker
- Bypasses multi-strategy requirement while keeping best win rate logic (76.9% backtest)
- Confidence boosted when multiple strategies agree
- Mode-based confidence adjustments: Conservative (0.70-0.75), Moderate (0.55-0.60), Aggressive (0.50)

### Telegram Copy Trading Notifications (March 2026)
- **Purpose**: Extend copy trading notifications to Telegram
- **New Functions in telegram.py**:
  - `send_copy_trade_alert()` - When a followed trader executes a trade
  - `send_new_follower_alert()` - When someone starts following you
  - `send_copy_pnl_update()` - Periodic P&L updates for copy positions
  - `send_trader_milestone_alert()` - Follower, profit, win streak milestones
  - `send_followed_trader_update()` - Hot streaks, big wins, new positions
  - `send_copy_trade_executed_alert()` - On-chain execution confirmation
  - `send_copy_trade_failed_alert()` - Failed copy trade notification
- **Integration in social_trading.py**:
  - `notify_followers_of_trade()` now sends Telegram alerts
  - `notify_trader_of_new_follower()` now sends Telegram alerts
  - Telegram notifications are non-blocking (errors logged but don't break flow)

### Services Refactoring (March 2026)
- **Purpose**: Extract large classes from ai_trader.py for better maintainability
- **Extracted Services** (to `/app/backend/services/`):
  - `MarketConditionAnalyzer` → `services/market_analyzer.py` (145 lines)
  - `RunnerDetector` → `services/runner_detector.py` (239 lines)
  - `TechnicalAnalyzer` → `services/technical_analyzer.py` (152 lines)
  - `StrategyEngine` → `services/strategy_engine.py` (347 lines)
- **Result**: `ai_trader.py` reduced from 3704 to 2866 lines (~23% reduction)
- **Import**: Services exported from `services/__init__.py`

### Runner Tokens UI Tab (March 2026)
- **Purpose**: Display discovered runner tokens in the Trading Bot page
- **Component**: `RunnerTokens.js` in `/app/frontend/src/components/`
- **Features**:
  - Displays trending/new tokens from DexScreener API
  - Score-based ranking (Legendary 90+, Excellent 80+, Good 70+, Moderate 60+, Risky <60)
  - Expandable card view with detailed metrics
  - Buy pressure indicator bar
  - Quick actions: Copy CA, DexScreener link, Solscan link
  - High Risk warning banner
  - Auto-refreshes every 2 minutes
- **Tab**: Added "Runners" tab with HOT badge in AITrader.js

### Custodial Wallet Encryption Fix (March 2026)
- **Issue**: Custodial wallet decryption failing with "Incorrect padding" error
- **Root Cause**: CUSTODIAL_ENCRYPTION_KEY in .env didn't match the key used to encrypt the wallet
- **Solution**: Regenerated custodial wallet with current encryption key
- **New Custodial Wallet**: `B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC`
- **Status**: Decryption working correctly, trades skip due to 0 SOL balance (expected)

## License
MIT License - Bullpug 2025
