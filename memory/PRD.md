# Bullpug.com - PRD & Implementation Tracker

## Original Problem Statement
Build a full-stack website for the memecoin "Bullpug" with space-themed cosmic guardian lore.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Solana Web3.js, react-i18next
- **Backend:** FastAPI, WebSockets, Pydantic, slowapi
- **Database:** MongoDB
- **Email:** SendGrid

---

## Latest Update: Feb 17, 2026 - Guardian Skin & Animation Fixes

### Changes This Session

#### 1. Guardian Skin - Correct Original Image (COMPLETE)
- Downloaded and saved user-provided fluffy bullpug image as `guardian_original.png`
- Updated skins.js to use `/images/guardian_original.png` for Guardian skin
- Image shows fluffy brown/orange pug with curved horns running through cosmic clouds

#### 2. Fixed Missing Pixels (COMPLETE)
- Removed clipping-based animation that caused pixel gaps
- Now draws full sprite without any clipping regions
- Uses motion blur overlays for leg movement effect instead

#### 3. Oriented Model to Face Down Lane (COMPLETE)
- Added `ctx.scale(-1, 1)` to flip sprite horizontally
- Bullpug now faces INTO the screen (towards horizon)
- Appropriate for endless runner perspective

#### 4. Animation System (COMPLETE)
- **Running**: Bounce, tilt, breathing/pumping scale effect
- **Leg Motion**: Motion blur overlays simulate galloping
- **Jump**: Stretch/squash with rotation (rising, apex, falling phases)
- **Effects**: Speed lines, motion trail, dust particles, fur wisps

---

## Previous Session Changes
- Original library images for all skins
- Speed halved (minSpeed 1.25, maxSpeed 4.8)
- 120-second speed progression
- Cake-shaped mooncakes distinct from obstacles
- Fiery obstacle visual effects

---

## Key Files

```
/app/frontend/
├── public/images/
│   ├── guardian_original.png  # User-provided fluffy bullpug
│   ├── *.jpg                  # Original library skins
├── src/
│   ├── pages/SpeedRunGame.js  # Game + animation
│   ├── config/skins.js        # Guardian uses guardian_original.png
```

---

## Game Features
- 3-lane endless runner
- Controls: A/D to switch lanes, SPACE to jump
- 5 progressive stages
- 120-second speed progression (1.25 to 4.8)
- Fiery obstacles, cake-shaped mooncakes
- Weekly leaderboard

---

## Task Status

### COMPLETED (This Session)
1. Guardian skin uses correct user-provided image
2. Fixed missing pixels (no clipping)
3. Oriented bullpug to face down the lane

### Upcoming (P1)
- Deployment to bullpug.com

### Backlog (P2)
- Re-enable Plushie Sales, NFT Gallery
- Power-ups (Shield, Magnet, 2x Score)
- Mobile swipe controls
- P2P Betting Arena, Exit Simulator, Trading Journal

---

## Admin Wallets
- `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`
- `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`
