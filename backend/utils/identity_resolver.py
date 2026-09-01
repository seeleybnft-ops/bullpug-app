"""Router-level identity resolver.

Bridges the two Phase A/B auth paths onto a single opaque "identity"
string that Archive services already understand. The service layer
does no crypto/base58 validation — it just stores and queries the
identity by the `wallet_address` field. So for email users we simply
pass their `user_id` UUID as the identity; the service layer neither
knows nor cares that it isn't a real wallet.

Precedence rules:
  1. `Authorization: Bearer <email JWT>` — resolve to user_id, use that
  2. `wallet` / `wallet_address` query param — return as-is
  3. Neither — return None (route decides whether that's a 400)
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from utils.email_auth_config import JWT_ALGORITHM, JWT_SECRET

_bearer_optional = HTTPBearer(auto_error=False)


def _try_decode_user_jwt(token: Optional[str]) -> Optional[dict]:
    """Return the JWT payload if it's a valid *user*-scoped token, else None.

    Silently swallows every failure mode (expired, malformed, wrong
    scope) so the caller can fall through to wallet-param mode
    without leaking an auth error on Archive read routes.
    """
    if not token or not JWT_SECRET:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    if payload.get("scope") != "user":
        return None
    return payload


async def resolve_identity(
    request: Request,
    wallet: Optional[str] = Query(None, description="Wallet address (wallet-auth users)"),
    wallet_address: Optional[str] = Query(None, description="Wallet address (legacy param name)"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_optional),
) -> Optional[str]:
    """FastAPI dependency — returns the opaque identity string or None.

    Handles both `?wallet=` and `?wallet_address=` (some routes use the
    longer form) so callers don't have to think about which one the
    route was originally written against.
    """
    if credentials and credentials.scheme.lower() == "bearer":
        payload = _try_decode_user_jwt(credentials.credentials)
        if payload:
            return payload.get("sub")  # user_id (UUID)

    return (wallet or wallet_address or "").strip() or None


async def require_identity(identity: Optional[str] = Depends(resolve_identity)) -> str:
    """Same as `resolve_identity` but 401 if none was resolvable.

    Used by routes that MUST have an authenticated caller (e.g. daily
    drop generation), as opposed to routes that render a guest state
    when unauthenticated (e.g. /archive/entries).
    """
    if not identity:
        raise HTTPException(status_code=401, detail="Sign in required")
    return identity


def is_email_identity(identity: Optional[str]) -> bool:
    """True when the identity looks like a UUID (email user) rather than
    a Solana wallet. Cheap heuristic — anything with a hyphen at the
    UUID positions is treated as an email user. Wallet addresses are
    Base58 (no hyphens)."""
    if not identity:
        return False
    return len(identity) == 36 and identity.count("-") == 4
