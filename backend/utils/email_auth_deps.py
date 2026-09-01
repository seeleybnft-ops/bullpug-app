"""FastAPI dependency for email-JWT authentication.

Scoped narrowly: only new email-auth endpoints use this. Existing
wallet routes continue to accept `wallet_address` as a query/body
param (see spec Part 8 — hybrid strategy). When we're ready to
migrate wallet routes to JWT in a follow-up, this dependency will
be extended to decode wallet-scope JWTs too.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from utils.config import RESEND_API_KEY  # noqa: F401 — ensure config loaded
from utils.database import db
from utils.email_auth_config import JWT_ALGORITHM, JWT_SECRET

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """Resolve the current email-authenticated user from a Bearer JWT.

    Returns the full `users` document. Raises 401 on any failure.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="Server JWT secret not configured")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

    if payload.get("scope") != "user":
        raise HTTPException(status_code=401, detail="Token missing user scope")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user id")

    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        # Token references a user that has been deleted (see DELETE
        # /api/auth/account). Reject cleanly so the frontend can force
        # a fresh sign-in instead of silently 500ing on downstream reads.
        raise HTTPException(status_code=401, detail="User no longer exists")
    if user.get("auth_type") not in ("email", "linked"):
        # A wallet-only user should not be arriving here via an email JWT.
        raise HTTPException(status_code=401, detail="Token/user auth type mismatch")

    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[dict]:
    """Same as `get_current_user` but returns None instead of raising.

    Useful for endpoints that behave differently for guests vs signed-in
    users (e.g. Archive read endpoints during Phase B).
    """
    if not credentials:
        return None
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None
