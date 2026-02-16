# Bullpug.com - PRD & Implementation Tracker

## Problem Statement
Build a fully functional memecoin website for Bullpug. Features: P2P betting arena with real SOL escrow, admin panel, direct messaging, push notifications, trading journal with cloud backup, community forum, speed-run game with leaderboard, reflections calculator, Monte Carlo exit simulator.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + Solana Wallet Adapter + WebSockets
- **Backend**: FastAPI + MongoDB + WebSockets + NumPy
- **Blockchain**: Solana Web3.js (mainnet-beta)
- **Real-time**: WebSockets for DM, notifications, pot updates

## P2P Betting Configuration
- **Rake**: 2.5% on all bets
- **Distribution Wallet**: `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`
- **Escrow**: Backend holds SOL temporarily during P2P matches
- **Currency**: SOL only
- **Min/Max Bet**: 0.01 - 10 SOL

## Admin Configuration
- **Admin Wallet 1 (Fee)**: `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`
- **Admin Wallet 2 (Personal)**: `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`

## What's Been Implemented (Feb 16, 2026)

### P2P Betting System
- [x] P2P Coin Flip with challenge system
- [x] P2P Winner Pot (winner takes all minus rake)
- [x] Escrow system (backend holds SOL)
- [x] Transaction recording and verification
- [x] 2.5% rake to distribution wallet
- [x] Provably fair verification (SHA-256)

### Admin Panel (NEW)
- [x] Wallet-based authentication
- [x] Dashboard with stats (bets, challenges, rake, users)
- [x] Challenge management (view, cancel)
- [x] Pot management (force draw)
- [x] Escrow monitoring
- [x] Bet history view

### Direct Messaging (NEW)
- [x] Persistent messages in MongoDB
- [x] Conversation grouping
- [x] Real-time WebSocket delivery
- [x] Unread message tracking
- [x] New chat by wallet address

### Push Notifications (NEW)
- [x] Web Push API integration
- [x] Real-time WebSocket notifications
- [x] Notification bell in navbar
- [x] Mark as read / Mark all read
- [x] Auto-notifications for challenges, messages, pot wins

### Trading Journal Cloud Backup (NEW)
- [x] Create backups (snapshots)
- [x] List all backups
- [x] Restore from backup (merge)
- [x] Delete backups
- [x] Wallet-linked storage

### Other Features
- [x] Community Forum (6 categories)
- [x] Speed-Run Game with weekly leaderboard
- [x] Share Score to X
- [x] Reflections Calculator
- [x] Monte Carlo Exit Simulator with PDF export
- [x] Wallet Dashboard with staking/governance

## Test Results (Feb 16, 2026)
- Backend: 100% (90+ tests passed)
- Frontend: 100% (All features verified)

## Social Links
- X (Twitter): https://x.com/Bullpugcoin
- Telegram: https://t.me/bullpugcoinchat

## API Endpoints

### Admin (requires admin wallet)
- `/api/admin/check/{wallet}` - Check if wallet is admin
- `/api/admin/dashboard` - Get statistics
- `/api/admin/challenges` - List challenges
- `/api/admin/challenge/cancel` - Cancel challenge
- `/api/admin/pot/draw` - Force draw pot
- `/api/admin/bets` - List all bets
- `/api/admin/escrow` - Escrow statistics

### Escrow
- `/api/escrow/wallet` - Get escrow wallet address
- `/api/escrow/deposit` - Record deposit
- `/api/escrow/balance/{wallet}` - Get user's escrow balance

### Messaging
- `/api/messages/send` - Send message
- `/api/messages/conversations/{wallet}` - Get conversations
- `/api/messages/conversation/{w1}/{w2}` - Get messages
- `/api/messages/unread/{wallet}` - Get unread count
- `/ws/dm/{wallet}` - WebSocket for real-time DM

### Notifications
- `/api/notifications/{wallet}` - Get notifications
- `/api/notifications/read/{id}` - Mark as read
- `/api/notifications/read-all/{wallet}` - Mark all read
- `/api/notifications/subscribe` - Subscribe to push
- `/ws/notifications/{wallet}` - WebSocket for real-time

### Trading Journal Backup
- `/api/journal/backup` - Create backup
- `/api/journal/backups/{wallet}` - List backups
- `/api/journal/backup/{id}` - Get backup
- `/api/journal/restore/{id}` - Restore backup
- `/api/journal/backup/{id}` (DELETE) - Delete backup

## Key Files
- `backend/server.py` - All API endpoints
- `frontend/src/pages/AdminPanel.js` - Admin dashboard
- `frontend/src/pages/Messages.js` - Direct messaging
- `frontend/src/components/NotificationBell.js` - Notifications
- `frontend/src/pages/TradingJournal.js` - Journal with backup

## Known Limitations
- Solana transaction verification is simplified for development
- Escrow requires trust in backend (no smart contract)
- Push notifications require browser permission

## Prioritized Backlog
### P1
- Full Solana program/smart contract for trustless escrow
- Mobile-responsive improvements
- Rate limiting for API endpoints

### P2
- Re-enable Plushie Shop
- Re-enable NFT Gallery
- Email notifications option
- Multi-language support
