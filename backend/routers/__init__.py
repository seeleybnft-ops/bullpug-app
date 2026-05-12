"""Routers package — single import point for all API routers."""
from routers.betting import router as betting_router
from routers.auth import router as auth_router
from routers.email import router as email_router
from routers.leaderboard import router as leaderboard_router
from routers.skins import router as skins_router
from routers.forum import router as forum_router
from routers.messages import router as messages_router
from routers.journal import router as journal_router
from routers.showcase import router as showcase_router
from routers.notifications import router as notifications_router
from routers.reflections import router as reflections_router
from routers.pot import router as pot_router
from routers.admin import router as admin_router
from routers.newsletter import router as newsletter_router
from routers.checkout import router as checkout_router
from routers.governance import router as governance_router
from routers.staking import router as staking_router
from routers.wallet import router as wallet_router
from routers.escrow import router as escrow_router
from routers.tokenomics import router as tokenomics_router
from routers.prize_pool import router as prize_pool_router
from routers.profile import router as profile_router
from routers.ai_suggestions import router as ai_suggestions_router
from routers.badges import router as badges_router
from routers.wallet_trades import router as wallet_trades_router
from routers.portfolio import router as portfolio_router
from routers.achievements import router as achievements_router
from routers.ai_chat import router as ai_chat_router
from routers.watchlist import router as watchlist_router
from routers.ai_trader import router as ai_trader_router
from routers.pugburn import router as pugburn_router
from routers.simulator import router as simulator_router
from routers.telegram import router as telegram_router
from routers.custodial_wallet import router as custodial_wallet_router
from routers.social_trading import router as social_trading_router
from routers.push_notifications import router as push_notifications_router
from routers.signal_analytics import router as signal_analytics_router
from routers.multichain_copy import router as multichain_copy_router
from routers.runner_alerts import router as runner_alerts_router
from routers.trading_competitions import router as trading_competitions_router
from routers.ledger import router as ledger_router
from routers.price_alerts import router as price_alerts_router
from routers.big_wins import router as big_wins_router

ALL_ROUTERS = [
    betting_router, auth_router, email_router, leaderboard_router,
    skins_router, forum_router, messages_router, journal_router,
    showcase_router, notifications_router, reflections_router, pot_router,
    admin_router, newsletter_router, checkout_router, governance_router,
    staking_router, wallet_router, escrow_router, tokenomics_router,
    prize_pool_router, profile_router, ai_suggestions_router, badges_router,
    wallet_trades_router, portfolio_router, achievements_router, ai_chat_router,
    watchlist_router, ai_trader_router, pugburn_router, simulator_router,
    telegram_router, custodial_wallet_router, social_trading_router,
    push_notifications_router, signal_analytics_router, multichain_copy_router,
    runner_alerts_router, trading_competitions_router, ledger_router,
    price_alerts_router, big_wins_router,
]
