# Bullpug.com - PRD & Implementation Tracker

## Original Problem Statement
Build a full-stack website for the memecoin "Bullpug" with space-themed cosmic guardian lore.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Solana Web3.js, react-i18next
- **Backend:** FastAPI, WebSockets, Pydantic, slowapi
- **Database:** MongoDB
- **Email:** SendGrid

---

## ✅ Latest Update: Feb 17, 2026 - Cosmic Runner V2

### 🎮 Major Game Improvements

#### 1. Obstacle Movement (FIXED)
- Obstacles now spawn at **horizon** (top/far) and move **DOWN toward player**
- Proper 3D perspective - obstacles start small and grow as they approach
- Depth-based rendering (depth=0 at horizon, depth=1 at player level)

#### 2. Animated 3D Character
- **Running animation:** Vertical bob motion when moving
- **Jump animation:** Stretch when jumping up, squash when landing
- Character glow effect based on skin color
- Running particles trail when moving

#### 3. Unique Skin Store Images
Each skin now has its own unique character artwork from the library:

| Skin | Image File | Description |
|------|-----------|-------------|
| Guardian | bullpug_sprite.png | Original Bullpug |
| Ethereal | ethereal.jpg | Glowing mystical character |
| Diamond | diamond.jpg | Crystal themed character |
| Gold | gold.jpg | Golden themed character |
| Silver | silver.jpg | Metallic character |
| Heatmap | heatmap.jpg | Thermal vision character |
| Radioactive | radioactive.jpg | Nuclear glow character |
| Zombie | zombie.jpg | Undead themed character |
| Aqua | water.jpg | Ocean/water themed |
| Inferno | fire.jpg | Fire/flame themed |
| Cyber | robot.jpg | Mechanical character |
| Phantom | skeletal.jpg | Ghostly character |

---

## 🕹️ Game Features

### Gameplay
- **3-Lane System:** A/D or Arrow keys to switch lanes
- **Jump:** Space or ArrowUp to jump over obstacles
- **5 Stages:** Progressive difficulty with new obstacle types

### Obstacle Types
| Stage | Score | New Obstacles |
|-------|-------|---------------|
| 1 | 0+ | Meteors (fiery, with fire trail pointing up) |
| 2 | 500+ | Space Debris (rocky chunks) |
| 3 | 1000+ | Black Holes (swirling vortex) |
| 4 | 2000+ | Satellites (with solar panels) |
| 5 | 3000+ | Alien Ships (UFOs with beam) |

### Visual Design
- **Deep space background** with nebulas and twinkling stars
- **3D perspective track** with converging lane lines
- **Glowing edge borders** in teal/green
- **Grid lines** moving toward player for speed effect

---

## ✅ Backend Architecture (Complete)

### server.py: 212 lines
All business logic in 20 modular routers:
- betting, auth, email, leaderboard, skins, forum
- messages, journal, showcase, notifications
- reflections, pot, admin, newsletter
- checkout, governance, staking, wallet, escrow, tokenomics

---

## 📊 Testing Status

### Latest: iteration_19.json - 100% pass rate
All features verified:
- Obstacles move DOWN from horizon ✅
- Character animation (bob/stretch/squash) ✅
- Unique skin images in store ✅
- 3-lane system + jump mechanics ✅
- Collision detection ✅
- Score/leaderboard integration ✅

---

## 📁 Key Files

```
/app/frontend/
├── public/images/
│   ├── bullpug_sprite.png    # Guardian character
│   ├── ethereal.jpg          # Mythic skin
│   ├── diamond.jpg           # Legendary skin
│   ├── gold.jpg              # Legendary skin
│   ├── silver.jpg            # Epic skin
│   ├── heatmap.jpg           # Rare skin
│   ├── radioactive.jpg       # Rare skin
│   ├── zombie.jpg            # Rare skin
│   ├── water.jpg             # Uncommon (Aqua)
│   ├── fire.jpg              # Uncommon (Inferno)
│   ├── robot.jpg             # Common (Cyber)
│   └── skeletal.jpg          # Common (Phantom)
├── src/
│   ├── pages/SpeedRunGame.js # Main game (rewritten)
│   ├── config/skins.js       # Skin configuration
│   └── components/SkinStore.js
```

---

## 📋 Task Status

### ✅ Completed
1. Obstacles coming from horizon DOWN the track
2. Animated 3D character (run bob, jump stretch/squash)
3. Unique skin images from library
4. Complete server.py refactoring (86% reduction)

### 📋 Future/Backlog
- Deployment to bullpug.com
- Re-enable Plushie Sales
- Power-ups implementation (Shield, Magnet, 2x Score)
- Mobile swipe controls

---

## 🔑 Admin Wallets
- `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`
- `qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs`
