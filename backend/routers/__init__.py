"""Routers package."""
from .betting import router as betting_router
from .auth import router as auth_router
from .email import router as email_router
from .leaderboard import router as leaderboard_router

__all__ = ['betting_router', 'auth_router', 'email_router', 'leaderboard_router']
