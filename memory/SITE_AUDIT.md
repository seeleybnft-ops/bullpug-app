# Bullpug — Full Site Audit

_Generated 16 May 2026. Source: live codebase under `/app/`. No secrets / env keys / wallet addresses / API tokens reproduced in this document._

This is a non-sensitive structural audit covering the public app, backend API surface, data model, integrations, game systems, and admin controls. Use it to spot gaps, missing UI, orphan endpoints, dormant features.

---

## 1 · Public Routes (Frontend SPA)

All routes are gated by a temporary access code (`PrivateAccessGate`) which must be removed before public launch.

| Path | Component | Status | Notes |
|---|---|---|---|
| `/` | `HomePage` | Live | Hero, Origins trailer, Daily Drop widget, Tinkerpug floating chat, PugBurn promo card |
| `/lore` | `Lore` | Live | Static lore page — Bullpug origin, Guardians, Newpug City |
| `/game` | `SpeedRunGame` | Live | Cosmic Runner UI shell — embeds the 3D game, leaderboard, achievements, skin store |
| `/game/3d` | `Phase1Runner3D` | Live | Standalone 3D game canvas (legacy direct mount, can also be reached from `/game`) |
| `/pugburn` | `PugBurn` | Live | Token burn tracker / live promo card |
| `/betting` | `BettingArena` | Live | P2P coin-flip arena + winner-pot pool with 60s countdowns, rake accounting, tip-the-pot |
| `/forum` | `Forum` | Live | Forum posts, replies, likes (no moderation tooling yet) |
| `/shop` | `Shop` | Live | Plushie + merch checkout (Stripe). **P2 — sales flow not wired end-to-end** |
| `/nft` | `NFTGallery` | Live | Interactive NFT gallery. **P2 — display only, no mint flow** |
| `/wallet` | `WalletDashboard` | Live | Connected-wallet view + escrow balance |
| `/messages` | `Messages` | Live | Direct messages between wallets |
| `/showcase` | `Showcase` | Live | Public showcase profile feed |
| `/showcase/:walletAddress` | `Showcase` | Live | Individual wallet showcase |
| `/profile` | `ProfilePage` | Live | Profile editing |
| `/admin` | `AdminPanel` (gated) | Live | SIWS-gated operator console |
| `/admin/drops` | `AdminDropVault` (gated) | Live | Daily-drop publishing UI |

### Removed / archived pages (no longer in router)
- AI Trading Bot dashboard (hibernated)
- Trading Journal page (data preserved, UI removed)
- Reflections Calculator (route returns 404 — backend unmounted 16 May 2026)
- Exit Simulator (route returns 404 — backend unmounted 16 May 2026)
- Portfolio (route returns 404 — backend unmounted 16 May 2026)
- Trading Competitions (route returns 404 — backend unmounted 16 May 2026)

> **Audit note:** the orphan routers — `/journal`, `/portfolio`, `/reflections`, `/staking`, `/competitions` — are now **disabled at the router level** (unmounted from `ALL_ROUTERS`). All endpoints under those prefixes return 404. The router files remain on disk for a future relaunch; see policy comment at the top of `/app/backend/routers/__init__.py`.

---

## 2 · Backend API — All Mounted Routers

Base path is `/api`. Every endpoint listed below already lives behind that prefix. Auth columns: `Public` = no auth, `Wallet` = requires wallet address payload (no signature), `SIWS-JWT` = requires signed admin session, `On-chain` = validates a real Solana transaction signature.

### 2.1 Core game / identity
| Prefix | Auth | Purpose |
|---|---|---|
| `/api/auth` | Public + Wallet | Wallet-signed login nonce/verify for user sessions |
| `/api/admin-auth` | Public + Wallet sig | SIWS — admin nonce, verify, `me`. Issues 12hr JWT |
| `/api/profile` | Wallet | Profile CRUD, equipped skin |
| `/api/showcase` | Wallet | Public showcase share + retrieval |
| `/api/leaderboard` | Wallet | Cosmic Runner score submission + linking + retrieval |
| `/api/achievements` | Wallet | Achievement unlocks |
| `/api/badges` | Wallet | Badge issuance + display |
| `/api/skins` | Wallet + On-chain | Catalog, owned, purchase (on-chain verified), gift, achievement-status, stats |
| `/api/ledger` | Wallet | User ledger / activity log |

### 2.2 Betting & escrow
| Prefix | Auth | Purpose |
|---|---|---|
| `/api/escrow` | Wallet + On-chain | Deposit (validates tx), balance, wallet address, manual-payout |
| `/api/betting` | Wallet | P2P bet challenges, match-making, history |
| `/api/betting/pot` | Wallet | Winner-pot pool — current pot, entries, payouts |
| `/api/prize-pool` | Wallet + On-chain | Tip the pot (validates tx), top tippers spotlight |
| `/api/big-wins` | Public | Big-win broadcast feed for arena |
| `/api/arena-chat` | Wallet | Arena chat channel |
| `/api/custodial-wallet` | SIWS-JWT | Custodial wallet info for arena settlement |

### 2.3 AI Tinkerpug
| Prefix | Auth | Purpose |
|---|---|---|
| `/api/ai/chat` | Wallet (or anon) | Chat with Tinkerpug. Lore-first priority, then prices, then trending. Trading-bot context stripped |
| `/api/ai/prices`, `/price/{sym}`, `/trending`, `/sentiment`, `/market`, `/news` | Public | Live market data passthrough |
| `/api/ai/history/{wallet}` | Wallet | Get / save / delete chat history |
| `/api/ai/daily-drops/*` | Public + SIWS-JWT | Daily drop content (read public, admin-pin/unpin) |
| `/api/ai/tradeable-assets` | Public | Asset list for autocomplete |
| `/api/ai-suggestions` | Wallet | Tinkerpug-side suggestion bubbles |

### 2.4 Tokenomics & burn
| Prefix | Auth | Purpose |
|---|---|---|
| `/api/tokenomics` | Public | $BULLPUG supply / distribution data |
| `/api/pugburn` | Public | Live burn tracker, total burned, recent burns |

### 2.5 Social & community
| Prefix | Auth | Purpose |
|---|---|---|
| `/api/forum` | Wallet | Posts, replies, likes |
| `/api/messages` | Wallet | Direct messages |
| `/api/governance` | Wallet | Governance proposals + votes |
| `/api/notifications` | Wallet | In-app notification feed |
| `/api/push-notifications` | Wallet | VAPID web-push subscription + preferences |
| `/api/newsletter` | Public | Newsletter signup |
| `/api/email` | Wallet | Email subscription mgmt |
| `/api/telegram` | Wallet | Telegram bot account linking + alerts |

### 2.6 Archived / dormant (still served, no UI)
| Prefix | Status | Why kept |
|---|---|---|
| `/api/ai-trader/*` | Hibernated | Historical trading bot data preserved, scheduler off |
| `/api/wallet-trades` | Hibernated | Detected trades archive |
| `/api/social-trading` | Hibernated | Copy-trading follow graph |
| `/api/multichain-copy` | Hibernated | Multichain copy-trading follow graph |
| `/api/runner-alerts` | Hibernated | Token-runner alerts |
| `/api/watchlist` | Hibernated | Token watchlists |
| `/api/checkout` (Stripe) | Wired but unsurfaced | Plushie/merch endpoints exist, frontend Shop is partial |

### 2.7 Unmounted / 404 (router files preserved for relaunch)
| Prefix | Mount status |
|---|---|
| `/api/journal` | **UNMOUNTED — returns 404** |
| `/api/portfolio` | **UNMOUNTED — returns 404** |
| `/api/reflections` | **UNMOUNTED — returns 404** |
| `/api/staking` + `/exit-simulator` | **UNMOUNTED — returns 404** |
| `/api/competitions` | **UNMOUNTED — returns 404** |

---

## 3 · MongoDB Collections — Live Inventory

Pulled directly from code analysis. Grouped by domain.

### Active collections (in-use)
- **Identity & profile:** `profiles`, `user_profiles`, `auth_nonces`, `admin_nonces`, `user_badges`
- **Game:** `leaderboard`, `game_leaderboard`, `skin_purchases`, `skin_equipped`, `skin_gifts`
- **Betting:** `bets`, `betting_challenges`, `betting_history`, `escrow_deposits`, `escrow_withdrawals`, `active_pot`, `pot_results`, `pot_tips`, `prize_pool`, `prize_payouts`, `big_wins`, `arena_chat`, `rake_events`, `rake_tracker`, `rake_withdrawals`, `custodial_wallets`
- **AI / Tinkerpug:** `chat_history`, `daily_drops`, `sentiment_cache`
- **Social:** `forum_posts`, `forum_replies`, `forum_likes`, `direct_messages`, `messages`, `community_opt_in`
- **Notifications:** `notifications`, `push_subscriptions`, `push_notification_preferences`, `push_notification_log`
- **Tokenomics:** `system_state`, `user_ledger`
- **Telegram / email:** `telegram_accounts`, `telegram_link_codes`, `telegram_pending_orders`, `email_subscriptions`, `newsletter_subscribers`
- **Showcase:** `showcases`, `showcase_shares`
- **Governance:** `votes`

### Dormant collections (data preserved, no live writes)
- **AI Trading Bot:** `ai_trader_positions`, `ai_trader_settings`, `auto_trade_logs`, `journal_trades`, `journal_backups`, `trading_journal`, `payment_transactions`, `performance_fees`
- **Smart-money / sniper:** `smart_money_signals`, `sniper_history`, `whale_dynamic_weights`, `whale_trade_history`
- **Copy trading:** `copied_trades`, `copy_trading_follows`, `copy_trade_notifications`, `copy_trade_notification_settings`, `multichain_copied_trades`, `multichain_follows`, `multichain_wallets`, `trader_profiles`, `trader_settings`
- **Runner alerts:** `runner_alert_preferences`, `runner_alerts_sent`, `price_alerts`, `price_candles`
- **Other:** `competition_entries`, `trading_competitions`, `watchlists`

> **Audit note:** the dormant collections are ~50% of total Mongo footprint. If $BULLPUG token-only path is the production direction, these should either be archived to S3 / cold storage or deleted with one backup snapshot.

---

## 4 · 3D Game — Cosmic Runner

Architecture: React Three Fiber + drei + react-three/postprocessing.

### Skins (12 total)
| ID | Display name | Rarity | Price (SOL) | Surface treatment |
|---|---|---|---|---|
| `default` | Guardian | Common | 0 | Procedural fur tufts |
| `ethereal` | Ethereal | Mythic | Achievement | Halo + cosmic fur strands |
| `diamond` | Diamond | Legendary | 0.05 | **Physical transmission** material + HDR refraction + faceted shells |
| `gold` | Gold | Legendary | 0.05 | Mirror metallic + rotating shine ring + facet pinpoints |
| `silver` | Silver | Epic | 0.04 | Reflective metallic + specks |
| `heatmap` | Heatmap | Rare | 0.03 | Pulsing thermal rings + hot patches |
| `radioactive` | Radioactive | Rare | 0.03 | Glowing veins + pulsing aura |
| `zombie` | Zombie | Rare | 0.03 | Torn flesh patches + stitches |
| `water` | Aqua | Uncommon | 0.02 | Ripple ring + droplet sparkles |
| `fire` | Inferno | Uncommon | 0.02 | Animated flame plume + lava cracks |
| `robot` | Cyber | Common | 0.01 | LED data ring + armor seams |
| `skeletal` | Phantom | Common | 0.01 | Spectral aura + bone wisps |

### Game systems
- **Bull horns** universal across all skins (5-segment ivory→bronze)
- **Stages** 1-5, gated at 375m intervals (2.5× original cadence)
- **Obstacles** 5 legend types with per-type hitboxes, above-ground spawning
- **Collectibles** 3D Moon Cheese, ring power-ups (magnet, multiplier, shield)
- **Bloom** EffectComposer with selective luminance threshold 0.22
- **HDR env** drei `Environment preset="city"` — IBL reflections for all metals + Diamond refraction
- **Player shadow** arcade-style blob that scales with jump height
- **Skin preview** standalone 160×160 3D viewport in SkinStore, idle auto-rotate, full bloom pipeline

### Known gaps
- No camera shake on near-miss
- No screen-flash on power-up pickup
- HDR loading is silent on cold start (no shimmer)
- Skin preview is auto-rotate only, no drag-to-rotate

---

## 5 · Tinkerpug AI

Model: OpenAI GPT-4o via Emergent LLM key. Image-aware variant for slash-command image inputs.

### Lore tier system
- **Tier 0** — public facts. Newpug City, Bullpug origin, the Guardians.
- **Tier 1** — earned by basic questions. Specific Guardian names, the feats list.
- **Tier 2** — gated by specific keywords. Enlightenment Nebula, First Crossing, Siren Scams, Forbidden Fork.
- **Tier 3** — restricted. Gideon (Grizzlor's origin), The Architect, the seventeen-loop coordination connection.

### Codex pane
- 13 entries in `TinkerpugCodex.js` keyword-detected from assistant messages
- Auto-unlocks on keyword hits, persists to `localStorage["bullpug_tinkerpug_codex_v1"]`
- Live unlock counter in header badge

### Chat UX
- Two-click confirm Delete (re-emits greeting on confirm)
- Smart auto-scroll (follows on at-bottom, holds on scrolled-up)
- "Scroll to bottom" pill on demand only
- Codex slide-down pane in header
- Greeting prioritizes Lore → Live prices → Trending coins

### Hibernated capabilities (stripped from prompt)
- Trading bot insights, P&L, win rate, dashboard cues — all removed from `tab_context` + `trading_context`
- Will never lead with "Reviewing your trading stats today?" or chart commentary

---

## 6 · P2P Arena

Two products on the same arena page:
- **Coin Flip** — 1v1 challenge, escrow-held, instant settlement
- **Winner Pot** — entry-fee pool with 60s countdowns, multiple winners, rake fee absorbed into pot

### Settlement
- All deposits validated **on-chain** via `tx_verify.py` (Solana RPC `getTransaction`)
- Rake events logged to `rake_events` + `rake_tracker`
- Rake withdrawals signed via custodial wallet
- Big wins (> 1 SOL) broadcast to `big_wins` feed (toast not wired yet)

### Tip-the-Pot
- Live with on-chain validation
- Top Tippers spotlight slide
- Tip amount goes directly to current pot

### Known gaps
- Big Win toast broadcast not wired in UI
- No camera/audio celebration on win
- Escrow operating capital top-up tracker (~0.5-1 SOL minimum) not surfaced to admin

---

## 7 · Admin

Auth: SIWS (Sign-In With Solana) → ed25519 signature verification → 12-hour PyJWT session.

### Protected routes
- `/admin` — Operator Console
- `/admin/drops` — Drop Vault (daily drop content pinning)

### Admin endpoints
- Daily drop publish + pin/unpin (`/api/ai/daily-drops/admin/*`)
- Escrow manual payout (`/api/escrow/manual-payout`)
- All admin-prefixed routers protected with `Depends(require_admin)`

### Known gaps
- No admin dashboard for rake withdrawal history (data exists, no UI)
- No admin moderation tools for forum / arena chat
- No admin user-ban / wallet-blacklist functionality

---

## 8 · Integrations

| Service | Use | Status |
|---|---|---|
| **OpenAI GPT-4o** | Tinkerpug chat (text + vision) | Live via Emergent LLM key |
| **Gemini Nano Banana** | Image generation | Live via Emergent LLM key |
| **Solana Web3 / Jupiter / Helius / Alchemy** | RPC, swaps, transaction verification | Live |
| **Stripe** | Plushie / merch checkout | Wired backend, UI partial |
| **Telegram Bot API** | Account linking + alerts | Live |
| **Web Push (VAPID)** | In-browser push notifications | Live |
| **CoinGecko / market data** | Live coin prices, trending | Live |
| **Resend / SendGrid** | Email subscriptions | Wired |

---

## 9 · Security Posture

- ✅ All money-moving endpoints (deposits, skin purchases, pot tips) validate the Solana tx server-side
- ✅ Admin endpoints behind SIWS JWT
- ✅ Private keys / API tokens stored in `.env`, never exposed to frontend
- ✅ MongoDB `_id` excluded from all response payloads
- ✅ **Image attachment size cap on `/api/ai/chat`** — 5 MB hard limit on decoded image, 8000 char limit on message, 60000 char limit on chat_history. Returns HTTP 413 above limit, preventing OpenAI vision-API cost blowups
- ✅ **CSRF protection middleware** on all state-changing requests (POST/PUT/DELETE/PATCH) to `/api/*`. Two-layer defence tuned for our Cloudflare-fronted infra:
  - **Layer 1 (always-on):** custom `X-Bullpug-CSRF: 1` header required — browsers cannot forge custom headers cross-origin without successful CORS preflight, which our CORS allowlist gates. This is the OWASP-recommended pattern.
  - **Layer 2 (when CORS_ORIGINS is non-wildcard):** `Referer` header must match the allowlist when present. The `Origin` header is intentionally **NOT** checked because the Cloudflare Worker fronting the cluster rewrites Origin to an internal cluster URL before it reaches FastAPI. `X-Forwarded-Host` is also NOT used because the ingress sets it to our own hostname regardless of who's calling, making it useless as a CSRF signal.
  - All axios + fetch calls auto-attach the CSRF header via `/app/frontend/src/index.js`
  - Verified: POST without header → 403, POST with header from evil.com Referer → 403, POST with valid Referer → passes
- ✅ **Rate limiting handled at the Cloudflare edge** (confirmed via `cf-ray` / `server: cloudflare` response headers on both preview and bullpug.com). FastAPI does NOT need a separate rate-limit layer. WAF rules / rate-limit thresholds managed in the Cloudflare dashboard. If you ever move off Cloudflare, install `slowapi` rate limits inline at the FastAPI layer (`slowapi` is already imported in `server.py` but unused per-route)
- ✅ **Strict CORS allowlist** set in `/app/backend/.env`: `CORS_ORIGINS=https://bullpug.com,https://cosmic-runner-hub.preview.emergentagent.com`. Will be picked up by production on next redeploy.

---

## 10 · Test Coverage

- `/app/backend/tests/` — pytest suite covering iteration-specific regressions
- `/app/test_reports/` — JSON test reports from testing agent runs
- No frontend e2e suite beyond manual Playwright via testing agent

---

## 11 · Known Gaps & Decisions Required

Priority-ordered.

### P0 — production blockers
1. ~~**Remove `bullpug2026` access gate** before public launch~~ — _deliberately kept active per user 16 May 2026_
2. ~~Decide what to do with hibernated AI Trading Bot routes (delete vs. keep)~~ — _resolved: 5 orphan routers unmounted (404), AI Trading Bot stack remains imported but dormant_
3. ~~Confirm `HELIUS_RPC_URL` is explicitly set in production~~ — _set in preview `.env`. Production env requires manual verification by operator on the deployment dashboard_

### P1 — security & ops
4. ~~Image attachment size cap on `/api/ai/chat`~~ — **DONE** (5MB image / 8000 char message / 60000 char history, HTTP 413)
5. ~~Explicit CSRF protection on POST endpoints~~ — **DONE** (Origin allowlist + `X-Bullpug-CSRF` header middleware)
6. ~~Rate limiting~~ — **handled at Cloudflare edge** (confirmed via response headers)

### P1 — visible UX gaps
7. ~~Big-win toast broadcast not wired into UI~~ — **DONE & UPGRADED** (now includes multi-note arpeggio fanfare + confetti burst + amplified entry animation + halo shimmer for wins ≥ 1 SOL)
8. Shop checkout flow partial — **PARKED — do not action**
9. NFT Gallery is display-only — **PARKED — do not action**

### P2 — backlog
10. Tinkerpug progression bar (parked)
11. Camera shake on near-miss + screen-flash on power-up pickup
12. HDR-loading shimmer for skin preview viewport
13. Mouse-drag rotation on skin preview
14. Inferno lava body shader (vertex-displaced)
15. Phantom anatomical bone skeleton rebuild

### Backlog — admin / ops
16. Admin rake-withdrawal history UI
17. Forum + arena-chat moderation tools
18. Wallet ban / blacklist mechanism
19. Production `CORS_ORIGINS` should be set to `https://bullpug.com` (currently `*` in preview — works because Cloudflare WAF handles edge, but explicit allowlist is defence-in-depth)

### Backlog — features
20. $BULLPUG token entries for pot (mint + Jupiter quote)
21. Escrow operating capital top-up monitor

---

## 12 · File / Module Map

```
/app/
├── backend/
│   ├── routers/              # 39 active routers (mounted via __init__.py)
│   ├── services/             # 18 background / utility services
│   │   ├── post_deploy_init.py   # Wallet seed restore + position sync
│   │   ├── daily_drop.py         # Tinkerpug daily-drop generator
│   │   ├── market_data.py        # Cached coin price / trending fetcher
│   │   ├── price_collector.py    # 1-min candle aggregation
│   │   └── …
│   ├── utils/                # Cross-cutting helpers
│   │   ├── admin_auth.py         # SIWS JWT auth + /admin-auth router
│   │   ├── tx_verify.py          # On-chain Solana TX validation
│   │   ├── solana_payout.py      # Custodial payouts
│   │   ├── notifications.py      # Push / email dispatch
│   │   └── …
│   ├── server.py             # FastAPI app entry
│   └── tests/                # pytest regression suite
├── frontend/
│   ├── src/
│   │   ├── pages/            # 16 active page components
│   │   ├── components/       # 40+ shared components
│   │   │   ├── ui/              # Shadcn primitives
│   │   │   ├── admin/           # Admin-only sub-tree
│   │   │   ├── journal/         # Hibernated journal sub-tree
│   │   │   └── trader/          # Hibernated trader sub-tree
│   │   ├── config/           # Skin catalog, constants
│   │   ├── hooks/            # SIWS hook, wallet hooks
│   │   ├── game/             # Game engine state (legacy 2D)
│   │   └── App.js            # Route table
│   └── package.json
├── memory/
│   ├── PRD.md                # Source of truth for product requirements
│   ├── CHANGELOG.md          # Historical iterations
│   ├── ROADMAP.md            # Prioritized backlog
│   ├── test_credentials.md   # Test wallet IDs
│   ├── PRODUCTION_READINESS.md
│   └── SITE_AUDIT.md         # ← this document
└── .backups/                 # Versioned rollback snapshots (iter126 etc.)
```

---

_End of audit. If a section feels thin, ask and I'll dig deeper into that subsystem._
