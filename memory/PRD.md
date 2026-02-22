# Bullpug.com - PRD & Implementation Tracker

## Original Problem Statement
Build a full-stack website for the memecoin "Bullpug" with space-themed cosmic guardian lore.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Solana Web3.js, Wagmi/Viem (EVM), react-i18next, html-to-image
- **Backend:** FastAPI, WebSockets, Pydantic, slowapi, emergentintegrations (LLM)
- **Database:** MongoDB
- **Blockchain:** Solana (Anchor framework), EVM chains (Ethereum, Base, Arbitrum via Alchemy)

---

## Latest Update: Feb 22, 2026 - UI Restructure + Features

### Changes Made This Session

#### 1. Journal Tab Restructure (COMPLETE)
New tab order:
1. **Dashboard** - Trading stats and charts
2. **Portfolio Value** - Multi-chain holdings with price tracker
3. **Import** - Auto-detect DEX trades from wallets
4. **Trades** - Trade log with CRUD
5. **Exit Sim** - Monte Carlo exit simulator (moved to own tab)
6. **Achievements** - Badge system and community benchmarks
7. **Backup** - Cloud backup/restore

#### 2. Portfolio Holdings List (COMPLETE)
- Shows all tokens across connected wallets
- Displays: Token symbol, chain, balance, USD value
- Native tokens labeled with "NATIVE" badge
- Stablecoins labeled with "STABLE" badge
- Sorted by USD value (highest first)
- Chain breakdown cards with totals

#### 3. Unified Wallet Connector (COMPLETE)
- Single "Connect Wallet" button in navbar
- Modal shows both Solana and EVM options
- Supports simultaneous wallet connections
- Chain switcher for EVM (Ethereum, Base, Arbitrum)
- Shows connected status with masked addresses

#### 4. Achievement Badges System (COMPLETE)
- 17 soulbound-style badges across 5 categories
- Auto-awards when requirements met
- Share on X with generated image card
- Community benchmarks with opt-in stats
- Leaderboard with multiple sort options

---

## Code Architecture

```
/app/
├── backend/
│   ├── routers/
│   │   ├── achievements.py      # Badges, benchmarks, leaderboard
│   │   ├── portfolio.py         # Multi-chain balances + prices
│   │   ├── wallet_trades.py     # Auto trade fetching
│   │   └── ...
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UnifiedWalletButton.js   # Combined wallet connector
│   │   │   ├── AchievementBadges.js     # Badges + share + benchmarks
│   │   │   ├── PortfolioSummary.js      # Holdings list + prices
│   │   │   └── DetectedTrades.js        # Auto-import trades
│   │   ├── pages/
│   │   │   └── TradingJournal.js        # 7 tabs including Exit Sim
│   │   └── providers/
│   │       └── EVMWalletProvider.js     # EVM wallet state
│   └── package.json
└── solana-program/
    └── README.md                        # Deployment guide
```

---

## Tab Order Reference

| Tab | Icon | Color | Function |
|-----|------|-------|----------|
| Dashboard | BarChart3 | #00C2FF | Stats overview |
| Portfolio Value | DollarSign | #9945FF | Holdings list |
| Import | Download | #627EEA | Trade detection |
| Trades | BookOpen | #00FFA3 | Trade log |
| Exit Sim | Calculator | #D946EF | Monte Carlo sim |
| Achievements | Trophy | #F5D300 | Badges & leaderboard |
| Backup | Activity | #FF6B6B | Cloud backup |

---

## Known Limitations

1. **CoinGecko Rate Limiting**: Free tier has aggressive rate limits. Prices may show $0 when rate limited. Consider adding a CoinGecko API key for production.

2. **Alchemy API**: The provided key appears shortened. Full Alchemy keys are typically 32+ characters. EVM portfolio fetching may not work without a valid key.

3. **Solana Deployment**: Blocked due to disk space constraints in cloud environment. Use local deployment guide at `/app/solana-program/README.md`.

---

## API Endpoints

### Portfolio
- `GET /api/portfolio/prices` - ETH/SOL prices
- `GET /api/portfolio/combined` - Multi-chain portfolio
- `GET /api/portfolio/evm/{address}` - EVM holdings
- `GET /api/portfolio/solana/{address}` - Solana holdings

### Achievements
- `GET /api/achievements/badges` - All 17 badges
- `GET /api/achievements/user/{wallet}` - User stats + earned badges
- `GET /api/achievements/share-data/{wallet}` - Share card data
- `GET /api/achievements/community/benchmarks` - Community stats
- `POST /api/achievements/opt-in` - Toggle sharing
- `GET /api/achievements/leaderboard` - Rankings

---

## Testing Status

- All tabs render correctly
- Exit Simulator works in dedicated tab
- Portfolio shows holdings list when wallet connected
- Unified wallet modal works for both Solana/EVM
- Achievement badges auto-award on eligibility

---

## Backlog

- Deploy Solana smart contract (requires local machine)
- Add CoinGecko API key for reliable pricing
- Verify Alchemy API key format
- NFT Gallery page
- Plushie Sales shop

---

## License
MIT License - Bullpug 2025
