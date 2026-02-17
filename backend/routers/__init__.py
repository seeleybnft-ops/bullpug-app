"""Routers package."""
from routers.betting import router as betting_router
from routers.auth import router as auth_router
from routers.email import router as email_router
from routers.leaderboard import router as leaderboard_router
from routers.skins import router as skins_router
from routers.forum import router as forum_router
from routers.messages import router as messages_router
from routers.journal import router as journal_router

__all__ = [
    'betting_router', 
    'auth_router', 
    'email_router', 
    'leaderboard_router',
    'skins_router',
    'forum_router',
    'messages_router',
    'journal_router'
]
