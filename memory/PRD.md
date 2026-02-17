# Bullpug.com - PRD & Implementation Tracker

## Original Problem Statement
Build a full-stack website for the memecoin "Bullpug" with space-themed cosmic guardian lore.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Solana Web3.js, react-i18next
- **Backend:** FastAPI, WebSockets, Pydantic, slowapi
- **Database:** MongoDB
- **Email:** SendGrid

---

## Latest Update: Feb 17, 2026 - Skin Images, Speed & Animation Updates

### Changes Implemented This Session

#### 1. Original Library Images for Skins (COMPLETE)
All 12 skins now use original library images instead of generated ones:

| Skin | Image File |
|------|------------|
| Guardian | bullpug_default.png |
| Ethereal | ethereal.jpg |
| Diamond | diamond.jpg |
| Gold | gold.jpg |
| Silver | silver.jpg |
| Heatmap | heatmap.jpg |
| Radioactive | radioactive.jpg |
| Zombie | zombie.jpg |
| Aqua | water.jpg |
| Inferno | fire.jpg |
| Cyber | robot.jpg |
| Phantom | skeletal.jpg |

#### 2. Speed Reduction (COMPLETE)
- **minSpeed:** 1.25 (was 2.5 - halved)
- **maxSpeed:** 4.8 (was 12, now 20% less then halved: 12 * 0.8 * 0.5)
- **Progression:** Still over 120 seconds
- Game feels more manageable and less frantic

#### 3. Subway Surfers Style Animation (COMPLETE)
Full character animation system implemented:

**Running Animation:**
- Legs pump back and forth with `legSwing` amplitude
- Upper and lower leg segments with knee bend
- Arms pump opposite to legs using `armCycle`
- Body bounce synchronized with leg movement

**Jump Animation:**
- Legs tuck up based on jump velocity
- Arms raise during jump
- Squash/stretch effects on rising/falling

**Code Location:** SpeedRunGame.js lines 914-1170

---

## Previous Session Features

### Obstacle/Mooncake Improvements
- `isPositionClear()` prevents spawning overlap
- Fiery obstacles with glowing auras
- Cake-shaped mooncakes (distinct from obstacles)

### Game Mechanics
- 3-lane system (A/D to switch)
- Jump (Space/ArrowUp)
- 5 progressive stages
- 120-second speed progression

---

## Backend Architecture

### server.py: 212 lines
All business logic in 20 modular routers:
- betting, auth, email, leaderboard, skins, forum
- messages, journal, showcase, notifications
- reflections, pot, admin, newsletter
- checkout, governance, staking, wallet, escrow, tokenomics

---

## Testing Status

### Latest: iteration_21.json - 100% pass rate
- Original library images verified
- Speed reduction verified (1.25 to 4.8)
- Subway Surfers animation verified
- All game mechanics working

---

## Key Files

```
/app/frontend/
├── public/images/
│   ├── bullpug_default.png  # Guardian (original)
│   ├── *.jpg                # Original library skins
│   └── mooncake.png
├── src/
│   ├── pages/SpeedRunGame.js  # Game + animation (~1200 lines)
│   ├── config/skins.js        # Uses original .jpg images
│   └── components/SkinStore.js
```

---

## Task Status

### COMPLETED (This Session)
1. Skins use original library images
2. Speed halved, top speed -20%
3. Subway Surfers animation (legs/arms pumping)

### Upcoming (P1)
- Deployment to bullpug.com

### Backlog (P2)
- Re-enable Plushie Sales shop page
- Re-enable NFT Gallery page
- Power-ups (Shield, Magnet, 2x Score)
- Mobile swipe controls
- P2P Betting Arena
- Exit Simulator
- Trading Journal
- Forum, DMs

---

## Admin Wallets
- `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`
- `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`
