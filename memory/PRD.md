# Bullpug - Memecoin Universe Platform

## Original Problem Statement
Full-stack, responsive website for the memecoin "Bullpug" featuring:
- AI Trading Bot (custodial wallet, on-chain execution)
- Trading Journal with P/L tracking and sentiment analysis
- Cosmic Runner game with prize pool
- P2P Betting Arena (BLOCKED - disk space)
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

### B-Tier Competitive Upgrades (March 24, 2026)
1. **Real OHLCV Price Data** - Collects actual candle data every 5 min
2. **Smart Money Tracking (5 wallets)** - Initial whale monitoring
3. **On-chain Sentiment Analysis** - 5-factor market analysis
4. **Jito MEV-Protected Execution** - Bundle-based transaction submission

### A-Tier Competitive Upgrades (March 24, 2026)
1. **Expanded Smart Money (56 wallets, 3-tier profit scoring)**
2. **GPT-Powered Sentiment Analysis** (GPT-4o via Emergent LLM Key)
3. **Trailing Stop-Losses** (dynamic, configurable)
4. **Conviction-Based Position Sizing** (scale by confidence)
5. **Multi-Timeframe Confirmation** (OHLCV + DexScreener alignment)
6. **DCA Exit Strategy** (staged TP1/TP2/trailing)
7. **Token Sniping Mode** (new pair scanning via DexScreener)
8. **Trading Mode Selector** (conservative/normal/aggressive/sniper)

### P0 Stabilization (March 24, 2026)
- Fixed critical `/platform-stats` route bug (decorator had no function body)
- Integrated `TradingModeSelector` into AITrader dashboard
- Added DCA stage + sniper badges to `PositionCard`
- All 31 tests passed (iteration 77)

### Refactoring (March 24, 2026)
- Extracted Pydantic models → `backend/models/ai_trader_models.py`
- Extracted token/price utilities → `backend/services/token_price.py`
- Unified DB connections: `ai_trader.py`, `custodial_wallet.py`, `signal_analytics.py` now use shared `utils/database.py`
- Removed duplicate `AsyncIOMotorClient` connections
- Fixed lint warnings (unused variables)
- `ai_trader.py` reduced from 4217 → 3927 lines

## File Architecture
```
backend/
  models/
    ai_trader_models.py       # Pydantic models (TraderSettings, TradeSignal, etc.)
  services/
    token_price.py            # Token constants, Jupiter, DexScreener price utils
    price_collector.py        # Real OHLCV candle data collection
    smart_money_tracker.py    # 56 whale wallets, 3-tier profit scoring
    social_sentiment.py       # 6-factor sentiment + GPT analysis
    jito_executor.py          # Jito MEV-protected execution
    token_sniper.py           # New pair scanning
    whale_profit_scorer.py    # Whale P/L evaluation
    market_quality.py         # Volume/liquidity quality checks
  routers/
    ai_trader.py              # Core bot logic, routes, auto-trade
    custodial_wallet.py       # Wallet management + Jito execution
    signal_analytics.py       # Performance tracking
  utils/
    database.py               # Shared MongoDB connection

frontend/src/
  pages/AITrader.js           # Main trading bot page
  components/trader/
    TradingModeSelector.js    # Mode switching (conservative/normal/aggressive/sniper)
    IntelligenceDashboard.js  # Intelligence systems UI
    QuickSettings.js          # Trailing stop controls
    PositionCard.js           # Trail/DCA/sniper badges
```

## Backlog
- P1: Create active Trading Competitions with leaderboards
- P2: Plushie Sales & NFT Gallery re-enable
- P3: P2P Betting Arena (BLOCKED by disk space)
- P3: Push Notifications improvements
- P3: Achievement badges & Share on X

## Test Coverage
- Backend: 100% (31/31 tests passed, iteration 77)
- Frontend: 100% (all pages load, components render)
- Bot logic: All A-tier features verified
- No regressions detected
