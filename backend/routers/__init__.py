"""Routers package — single import point for all API routers.

ARCHIVED ROUTERS (10 Sep 2026 + 18 Sep 2026):
The following router modules have been moved to /archived/backend/routers/
along with their frontend surfaces. They are NOT imported here and their
endpoints will return 404. Restore the files + re-add the import lines +
list entries below to re-enable:
  • betting        — Pug Pit coin-flip / P2P betting arena
  • escrow         — Pug Pit escrow deposits + rake
  • ledger         — Betting ledger + rake ledger
  • showcase       — Skin showcase (parked with skin store)
  • journal        — Trading Journal (parked)
  • portfolio      — Portfolio value (parked)
  • reflections    — Reflections calc (parked)

ORPHAN MODULES — retained in-tree but NOT mounted in ALL_ROUTERS:
The router files stay because active production code imports specific
functions from them; only the HTTP endpoints are unreachable:
  • pot            — routes 404; scheduler.py calls draw_pot_winner()
  • prize_pool     — routes 404; skins.py + scheduler.py call add_to_prize_pool / execute_prize_payout / get_or_create_prize_pool
  • big_wins       — routes 404; pot.py calls record_big_win()
  • staking        — /staking + /exit-simulator 404 (parked)
  • trading_competitions — /competitions 404 (parked)

The AI Trading Bot stack (ai_trader / wallet_trades / social_trading /
multichain_copy / runner_alerts / price_alerts / watchlist / simulator /
checkout) remains mounted but dormant (no scheduler, no UI surface).
"""
from routers.auth import router as auth_router
from routers.email_auth import router as email_auth_router
from routers.email import router as email_router
from routers.leaderboard import router as leaderboard_router
from routers.skins import router as skins_router
from routers.forum import router as forum_router
from routers.messages import router as messages_router
from routers.notifications import router as notifications_router
from routers.pot import router as pot_router  # noqa: F401 — orphan (functions used by scheduler)
from routers.big_wins import router as big_wins_router  # noqa: F401 — orphan (functions used by pot.py)
from routers.admin import router as admin_router
from routers.newsletter import router as newsletter_router
from routers.checkout import router as checkout_router
from routers.governance import router as governance_router
from routers.staking import router as staking_router  # noqa: F401 — orphan
from routers.wallet import router as wallet_router
from routers.tokenomics import router as tokenomics_router
from routers.prize_pool import router as prize_pool_router  # noqa: F401 — orphan (functions used by skins/scheduler)
from routers.profile import router as profile_router
from routers.ai_suggestions import router as ai_suggestions_router
from routers.badges import router as badges_router
from routers.wallet_trades import router as wallet_trades_router
from routers.achievements import router as achievements_router
from routers.ai_chat import router as ai_chat_router
from routers.watchlist import router as watchlist_router
from routers.pugburn import router as pugburn_router
from routers.simulator import router as simulator_router
from routers.telegram import router as telegram_router
from routers.custodial_wallet import router as custodial_wallet_router
from routers.social_trading import router as social_trading_router
from routers.push_notifications import router as push_notifications_router
from routers.multichain_copy import router as multichain_copy_router
from routers.runner_alerts import router as runner_alerts_router
from routers.trading_competitions import router as trading_competitions_router  # noqa: F401 — orphan
from routers.price_alerts import router as price_alerts_router
from routers.arena_chat import router as arena_chat_router
from routers.client_errors import router as client_errors_router
from routers.analytics import router as analytics_router
from routers.archive import router as archive_router
from routers.companion import router as companion_router, admin_router as companion_admin_router
from utils.admin_auth import router as admin_auth_router

# Orphan routers — imported above for code preservation, intentionally NOT
# included in ALL_ROUTERS so their user-facing endpoints return 404.
ALL_ROUTERS = [
    auth_router, email_router, leaderboard_router,
    skins_router, forum_router, messages_router,
    notifications_router,
    admin_router, newsletter_router, checkout_router, governance_router,
    wallet_router, tokenomics_router,
    profile_router, ai_suggestions_router, badges_router,
    wallet_trades_router, achievements_router, ai_chat_router,
    watchlist_router, pugburn_router, simulator_router,
    telegram_router, custodial_wallet_router, social_trading_router,
    push_notifications_router, multichain_copy_router,
    runner_alerts_router,
    price_alerts_router, arena_chat_router,
    client_errors_router,
    analytics_router,
    archive_router,
    companion_router,
    companion_admin_router,
    admin_auth_router,
    email_auth_router,
]
