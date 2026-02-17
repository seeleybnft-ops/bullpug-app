"""Routers package."""
from .betting import router as betting_router
from .auth import router as auth_router
from .email import router as email_router
from .leaderboard import router as leaderboard_router
from .skins import router as skins_router
from .forum import router as forum_router
from .messages import router as messages_router
from .journal import router as journal_router

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
