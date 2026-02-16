# Bullpug.com - PRD & Implementation Tracker

## Original Problem Statement
Build a full-stack, responsive website for the memecoin "Bullpug" (bullpug.com), based on a detailed whitepaper. The website should be space-themed and embody the lore of Bullpug as a cosmic guardian.

## User Personas
- **Crypto Traders**: Users who want to bet with SOL and track their trades
- **Gamers**: Users who enjoy casual games and leaderboards
- **Community Members**: Users who want to discuss and interact via forum and DMs
- **Admins**: Wallet-authorized administrators who manage the platform

## Core Requirements
- **Lore Integration:** Immersive storytelling through animations and interactive elements
- **Tokenomics:** Interactive display of token details, supply distribution, and reflections calculator
- **Solana Wallet Integration:** Connect to Solana blockchain for staking, balance display, and real SOL betting
- **P2P Betting Arena:** Player-vs-Player Coin Flip and Pot games using real SOL, with 2.5% house rake
- **Speed-Run Game:** Endless runner with weekly leaderboard and "Share to X" feature
- **Trading Journal:** Comprehensive tool for logging trades with dashboard, CSV/PDF export, and cloud backup
- **Community Forum:** Section for users to create posts, reply, and filter by category
- **Direct Messaging:** Real-time chat between users via WebSockets
- **Admin Panel:** Restricted page for wallet-authorized admins
- **Multi-Language Support:** Internationalization with i18next (English/Spanish)
- **Email Notifications:** SendGrid integration for welcome emails and weekly summaries
- **Security:** Rate limiting and wallet signature verification

## Tech Stack
- **Frontend:** React, Tailwind CSS, Solana Web3.js & Wallet-Adapter, react-i18next
- **Backend:** FastAPI, WebSockets, Pydantic, slowapi (rate limiting)
- **Database:** MongoDB (pymongo/motor)
- **Email:** SendGrid (pending API key configuration)
- **Blockchain:** Solana network integration

---

## What's Been Implemented

### December 2025

#### P0 Features (Completed)
1. **Multi-Language Support (i18next)**
   - ✅ Language switcher in navbar with globe icon
   - ✅ English and Spanish translations
   - ✅ BettingArena page fully translated
   - ✅ SpeedRunGame page fully translated
   - ✅ Navbar links translated
   - ✅ LocalStorage persistence (bullpugLang key)

2. **Email Notifications (SendGrid)**
   - ✅ Email subscription endpoints (subscribe, unsubscribe, status)
   - ✅ Welcome email template (HTML formatted)
   - ✅ Weekly summary email template
   - ⚠️ SENDGRID_API_KEY not configured (endpoints work but emails not sent)

#### P1 Features (Completed)
3. **Backend Rate Limiting**
   - ✅ slowapi integration
   - ✅ /api/betting/challenge/create - 10/minute limit
   - ✅ /api/betting/pot/join - 10/minute limit

4. **Wallet Security Enhancement**
   - ✅ Signature verification utility using nacl
   - ✅ GET /api/auth/sign-message/{wallet} endpoint
   - ✅ POST /api/auth/verify-signature endpoint
   - ✅ Nonce storage with 5-minute expiry

### Earlier Implementations
- ✅ P2P Betting Arena (Coin Flip & Pot with real SOL logic)
- ✅ Speed-Run Game with weekly leaderboard
- ✅ Trading Journal with CSV/PDF export and cloud backup
- ✅ Community Forum with categories
- ✅ Direct Messaging via WebSockets
- ✅ Admin Panel (wallet-restricted)
- ✅ Push Notifications infrastructure
- ✅ Reflections Calculator

---

## API Endpoints

### Email
- `POST /api/email/subscribe` - Subscribe wallet to emails
- `POST /api/email/welcome` - Send welcome email
- `GET /api/email/subscription/{wallet}` - Get subscription status
- `DELETE /api/email/unsubscribe/{wallet}` - Unsubscribe
- `POST /api/email/test` - Check SendGrid configuration

### Auth/Security
- `GET /api/auth/sign-message/{wallet}` - Generate signing message
- `POST /api/auth/verify-signature` - Verify wallet signature

### Betting (Rate Limited)
- `GET /api/betting/config` - Get betting configuration
- `POST /api/betting/challenge/create` - Create P2P challenge (10/min)
- `POST /api/betting/challenge/accept` - Accept challenge (20/min)
- `POST /api/betting/pot/join` - Join pot (10/min)
- `GET /api/betting/challenges` - List open challenges
- `GET /api/betting/pot` - Get pot status
- `GET /api/betting/history` - Get bet history

---

## Prioritized Backlog

### P0 - Critical (None remaining)
All P0 features implemented

### P1 - Important
- ⬜ UX Improvements - Visual feedback (animations, sound effects) on Betting/Game pages

### P2 - Nice to Have
- ⬜ Re-enable Plushie Sales (Shop.js placeholder exists)
- ⬜ Re-enable NFT Gallery (NFTGallery.js placeholder exists)
- ⬜ Refactor backend/server.py into modular structure (routers/, models/, services/)
- ⬜ Add global state management (Redux Toolkit or Zustand)

---

## Configuration Required

### SendGrid (Email)
To enable email notifications, add to `/app/backend/.env`:
```
SENDGRID_API_KEY=your_sendgrid_api_key
SENDER_EMAIL=noreply@bullpug.com
```

### Admin Wallets
Configured in Navbar.js and server.py:
- `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT` (Fee Wallet)
- `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs` (Personal)

---

## File Structure
```
/app/
├── backend/
│   ├── server.py           # Main FastAPI app (~2400 lines)
│   ├── requirements.txt    # Python dependencies
│   ├── .env                # Environment variables
│   └── tests/              # Pytest tests
├── frontend/
│   ├── src/
│   │   ├── i18n/config.js      # i18next configuration
│   │   ├── components/
│   │   │   ├── Navbar.js       # With LanguageSwitcher
│   │   │   ├── LanguageSwitcher.js  # Language dropdown
│   │   │   └── ...
│   │   └── pages/
│   │       ├── BettingArena.js # With i18n translations
│   │       ├── SpeedRunGame.js # With i18n translations
│   │       └── ...
│   └── package.json
└── memory/
    └── PRD.md
```

---

## Testing Reports
- `/app/test_reports/iteration_6.json` - Latest (100% pass rate)
- Previous: iteration_2.json through iteration_5.json

## Known Issues
- SendGrid API key not configured (emails won't send until configured)
- Backend server.py is large (~2400 lines) - needs modularization
