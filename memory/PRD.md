# Bullpug - Memecoin Universe Platform

## Original Problem Statement
Full-stack, responsive website for the memecoin "Bullpug" featuring:
- AI Trading Bot (custodial wallet, on-chain execution)
- Trading Journal with P/L tracking and sentiment analysis
- Cosmic Runner game with prize pool
- P2P Betting Arena
- PugBurn (Solana account cleanup)
- Social/Copy Trading
- Trading Competitions
- Push Notifications
- Gamification (badges, achievements)

## Architecture
- **Frontend:** React (CRA) + TailwindCSS + Shadcn/UI
- **Backend:** FastAPI + MongoDB (Motor) — shared DB via `utils/database.py`
- **Blockchain:** Solana (Jupiter DEX, Helius/Alchemy RPC, Jito)
- **AI:** OpenAI GPT-4o via Emergent LLM Key
- **Integrations:** DexScreener, CoinGecko, Telegram, Jito Block Engine

## What's Implemented

### Core Features
- Homepage with hero, BotQuickStats widget, social links
- AI Trading Bot (multi-strategy, TP/SL, auto-trade, auto-burn)
- Trading Journal (dashboard, P&L charts, sentiment, CSV/JSON export)
- Cosmic Runner game (5 stages, leaderboard jackpot, 21 achievements)
- PugBurn (Solana account cleanup)
- Forum with categories
- Social Trading leaderboard
- Trading Competitions (router registered)
- Profile system
- Notification system (WebSocket + Telegram)
- Skin Store & Showcase

### Bot Intelligence (B-Tier + A-Tier)
- Real OHLCV Price Data (5-min candles)
- Smart Money Tracking (56 wallets, 3-tier scoring)
- GPT-4o Sentiment Analysis
- Jito MEV-Protected Execution
- Conviction-Based Position Sizing
- Multi-Timeframe Confirmation
- DCA Exit Strategy
- Token Sniping Mode
- Trading Mode Selector (conservative/normal/aggressive/sniper)
- Trailing Stop-Losses

### UI Restructure — Fund Ledger at Top (March 25, 2026)
- **Fund Ledger moved to top** of AI Trader page, replacing the 4 stat cards (Win Rate, Total P&L, etc.)
- **Persistent across all tabs** — always visible regardless of which tab is active
- **Wallet address shown** in Fund Ledger header with copy-to-clipboard button
- **Deposit/Withdraw buttons** integrated into Fund Ledger (deposit modal lifted to AITrader.js)
- **"Trading Wallet" section removed** from Auto Trade Engine controls tab
- **Horizontal layout** — Total Balance | Breakdown Grid | Deposit/Withdraw buttons
- **Test data cleaned up** — Removed all TEST/RAKETEST positions, history, and ledger entries from DB

### Rake Back System (March 25, 2026)
- **2.5% platform rake on profitable trades** — only applied to the profit portion, never the original investment
- **`apply_rake()` helper** in `ai_trader.py` — calculates rake and records `fee` ledger entry
- **Integrated into all close paths:** close_position, manual_close_position, auto_trade_check_exits (including DCA partial exits)
- **Close responses include rake object:** `{ applied: bool, amount_sol: float, percent: 2.5 }`
- **Rake stats endpoint:** `GET /api/ledger/rake-stats/{wallet}` — total rake collected, gross profit, count
- **Fee entries in ledger** — stored with `reference_type: "rake"` and metadata including `gross_pnl_sol`, `rake_percent`, `rake_sol`

### Internal Fund Ledger (March 25, 2026)
- **New `services/ledger.py`** — Core double-entry bookkeeping service
- **New `routers/ledger.py`** — API endpoints: `/ledger/balance/{wallet}`, `/ledger/history/{wallet}`, `/ledger/reconciliation`, `/ledger/migrate`
- **DB collection:** `user_ledger` with indexes on `(user_wallet, created_at)` and `(user_wallet, entry_type)`
- **Entry types:** deposit (credit), withdrawal (debit), trade_open (debit/lock), trade_close (credit/unlock), fee, adjustment
- **Balance computed from ledger:** `available_sol = SUM(all entries)`, `locked_in_trades = trade_opens - trade_closes`
- **Integrated into:** `custodial_wallet.py` (deposits/withdrawals), `ai_trader.py` (all position opens/closes including auto-trade, manual, runner, sniper)
- **Withdrawal validation:** Now checks against ledger balance before on-chain withdrawal
- **Migration endpoint:** One-time migration from existing custodial wallet records and open positions
- **Frontend:** `FundLedger.js` component on AI Trader page showing balance breakdown + transaction history
- **Reconciliation endpoint:** Compares total virtual balances vs. custodial wallet records for admin auditing

### Community Spotlight (March 25, 2026)
- **New component:** `CommunitySpotlight.js` — auto-rotating carousel on homepage
- Placed below Trading Bot Live Stats section
- Slide 1 (Runners): Cosmic Runner Leaderboard, Top Moon Cheese Collectors, Hall of Fame
- Slide 2 (Activity): Live Platform Stats, Competitions (Coming Soon), Join the Community (X, Telegram, Forum)
- Dynamic slide 3 (Traders): Appears when social trading leaderboard has entries
- Navigation: dot indicators, prev/next arrows, 8-second auto-rotation
- Uses live data from `/api/leaderboard` and `/api/ai-trader/platform-stats`

### Bug Fixes (March 25, 2026 — Session 2)
- **Tab Title & Favicon:** Changed title from "Emergent | Fullstack App" to "Bullpug" and added custom favicon pointing to Bullpug logo
- **"Made with Emergent" badge:** Removed floating badge from bottom-right corner (was in index.html)
- **Trading Mode not reflecting choice:** ROOT CAUSE: `save_settings` saved to `trading_mode` field but auto-trade status endpoint read from `auto_trade_mode` field. FIX: `save_settings` now syncs both fields, and status endpoint reads `trading_mode` first with fallback

### Bug Fixes (March 25, 2026)
- **Gallery Images:** Replaced stock Unsplash/Pexels photos with user's original Bullpug branding images in HomePage.js and NFTGallery.js
- **Logo:** Verified correct display in Navbar and Footer using user's artifact URLs
- **Trading Mode UI:** Stat card reads from `traderSettings?.trading_mode` (confirmed correct)

### Refactoring (March 25, 2026)
- **server.py:** Reduced from 278 to 198 lines by unifying router imports via `ALL_ROUTERS` list in `routers/__init__.py`
- **Router imports:** All 40 routers now imported through a single centralized `ALL_ROUTERS` list
- **Test cleanup:** Archived 29 old iteration-specific test files to `tests/archive/`, keeping 42 active test files
- **Dead files removed:** `server.py.bak`

## File Architecture
```
backend/
  server.py (198 lines, clean)
  models/ai_trader_models.py
  services/
    token_price.py, price_collector.py, smart_money_tracker.py,
    social_sentiment.py, jito_executor.py, token_sniper.py,
    whale_profit_scorer.py, market_quality.py
  routers/
    __init__.py (ALL_ROUTERS — single import point for 40 routers)
    ai_trader.py (core bot + performance-scorecard endpoint)
    custodial_wallet.py, signal_analytics.py, ...
  utils/database.py (shared MongoDB)
  tests/ (42 active test files)
  tests/archive/ (29 archived iteration tests)

frontend/src/
  pages/AITrader.js (dashboard: QuickSettings, Scorecard, RiskCalc, Positions)
  pages/HomePage.js (GALLERY uses user's branding images)
  pages/NFTGallery.js (GALLERY uses user's branding images)
  components/
    Navbar.js (LOGO from user artifact)
    Footer.js (LOGO from user artifact)
    UnifiedAutoTrader.js (Controls + Settings + TradingModeSelector)
    PrivateAccessGate.js (access code: bullpug2026)
    trader/ (TradingModeSelector, IntelligenceDashboard, PerformanceScorecard, etc.)
```

## Backlog
- P1: Trading Competitions with leaderboards
- P2: Plushie Sales & NFT Gallery re-enable
- P3: P2P Betting Arena
- P3: Push Notifications improvements
- P3: Achievement badges & Share on X
- Administrative: Remove private access gate when user confirms testing is over

## Test Coverage
- Backend: 100% (17/17 tests, iteration 79)
- Frontend: 100% (gallery images verified, logo correct, all pages load)
- No regressions detected

## Private Testing
- Access code: `bullpug2026`
- Do NOT remove access gate unless user explicitly instructs
