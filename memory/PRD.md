# Bullpug.com - PRD & Implementation Tracker

## Original Problem Statement
Build a full-stack website for the memecoin "Bullpug" with space-themed cosmic guardian lore.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Solana Web3.js, react-i18next
- **Backend:** FastAPI, WebSockets, Pydantic, slowapi
- **Database:** MongoDB
- **Email:** SendGrid

---

## Latest Update: Feb 17, 2026 - Game Guide & Enhanced Mooncakes + Refactoring

### New Features Implemented

#### 1. Game Guide Section (COMPLETE)
Below the game canvas, a comprehensive guide displays:
- **COLLECTIBLES**: Mooncake (🥮) - +25 points each
- **POWER-UPS**: Guardian Shield (🛡️), Mooncake Magnet (🧲), Star Power (⭐)
- **OBSTACLES**: Meteor (☄️), Space Debris (🪨), Black Hole (🕳️), Satellite (🛰️), Alien Ship (🛸)
- **CONTROLS**: A/←, D/→, SPACE/↑, Mobile Swipe

#### 2. Enhanced Mooncake Visuals (COMPLETE)
Made mooncakes shinier and brighter with:
- **Larger Outer Glow**: 2.8x size with pulsing animation
- **Star-burst Rays**: 8 rays emanating outward with animation
- **Orbiting Sparkles**: 8 sparkles with individual glow effects
- **Brighter Golden Core**: #FFFFD0 → #E0A040 gradient
- **Multiple Highlights**: Main shine (0.8 alpha) + secondary shine (0.5 alpha)
- **Animated Shimmer Spot**: Circular motion based on glow phase
- **Double-ring Pulsing Outline**: Inner + outer glow rings

#### 3. Code Refactoring Foundation (COMPLETE)
Created modular files for future refactoring:
- `/app/frontend/src/game/constants.js` - All game constants
- `/app/frontend/src/hooks/usePlayerControls.js` - Input handling hook
- `/app/frontend/src/components/GameGuide.js` - Extracted guide component

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
│   │   ├── betting.py       # P2P betting (coin flip, pot)
│   │   ├── forum.py         # Community forum
│   │   ├── journal.py       # Trading journal
│   │   ├── messages.py      # Direct messages (DMs)
│   │   ├── simulator.py     # Exit simulator (Monte Carlo)
│   │   └── ...
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── game/
│   │   │   └── constants.js    # Game constants (NEW)
│   │   ├── hooks/
│   │   │   └── usePlayerControls.js  # Input handling (NEW)
│   │   ├── components/
│   │   │   ├── GameGuide.js    # Guide component (NEW)
│   │   │   └── SkinStore.js
│   │   ├── pages/
│   │   │   ├── SpeedRunGame.js    # Main game (2032 lines)
│   │   │   ├── BettingArena.js    # P2P betting
│   │   │   ├── ExitSimulator.js   # Monte Carlo sim
│   │   │   ├── TradingJournal.js  # Trade logging
│   │   │   ├── Forum.js           # Community posts
│   │   │   └── Messages.js        # DMs
│   │   └── config/
│   │       └── skins.js
│   └── package.json
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
