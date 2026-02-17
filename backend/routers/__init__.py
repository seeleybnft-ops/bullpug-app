"""Routers package."""
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

__all__ = [
    'betting_router', 
    'auth_router', 
    'email_router', 
    'leaderboard_router',
    'skins_router',
    'forum_router',
    'messages_router',
    'journal_router',
    'showcase_router',
    'notifications_router',
    'reflections_router',
    'pot_router',
    'admin_router',
    'newsletter_router',
    'checkout_router',
    'governance_router',
    'staking_router',
    'wallet_router',
    'escrow_router',
    'tokenomics_router'
]
