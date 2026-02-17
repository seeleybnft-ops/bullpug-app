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
from routers.pot import router as pot_router
from routers.simulator import router as simulator_router
from routers.reflections import router as reflections_router
from routers.notifications import router as notifications_router
from routers.admin import router as admin_router

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
    'pot_router',
    'simulator_router',
    'reflections_router',
    'notifications_router',
    'admin_router'
]
