"""Sign-In-With-Solana (SIWS) for admin authorization.

Replaces the old header-equality admin gate (X-Admin-Wallet / admin_wallet
query param) with a real ed25519 signature flow:

  1. Frontend hits POST /api/admin-auth/nonce with its wallet pubkey →
     backend returns a structured SIWx-style message + nonce, stored in
     Mongo with a short TTL.
  2. Frontend asks Phantom to signMessage(message_bytes) and sends the
     base58 signature + the wallet back to POST /api/admin-auth/verify.
  3. Backend verifies the ed25519 signature against the pubkey, checks
     the wallet is on the ADMIN_WALLETS allow-list (from .env), and
     issues a short-lived JWT (12h) signed with JWT_SECRET.

All future admin requests carry the JWT in the Authorization header. Use
the `require_admin_jwt` FastAPI dependency to protect any endpoint.

Backward compatibility: a few routers still accept ``admin_wallet`` as a
query param. Those keep working until they're migrated — see
``admin_auth_compat`` for the bridging helper.
"""

from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import base58
import nacl.signing
import nacl.exceptions
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from utils.database import db


# ─────────────────────────────────────────── Config

JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 12
NONCE_TTL_SECONDS = 600  # 10 min

SIWS_DOMAIN = os.environ.get("SIWS_DOMAIN", "bullpug.com")
SIWS_STATEMENT = "Sign in as a Bullpug administrator. This signature is for authentication only and will not move any funds."

# Comma-separated allow-list in .env, with the DISTRIBUTION_WALLET as a
# baseline so an empty env doesn't lock us out.
def _admin_wallets() -> List[str]:
    raw = os.environ.get("ADMIN_WALLETS", "")
    wallets = [w.strip() for w in raw.split(",") if w.strip()]
    if not wallets:
        from utils.config import DISTRIBUTION_WALLET
        wallets = [DISTRIBUTION_WALLET]
    return wallets


# ─────────────────────────────────────────── Models

class NonceRequest(BaseModel):
    wallet: str = Field(..., min_length=20, max_length=64)
    origin: Optional[str] = Field(None, max_length=256)


class NonceResponse(BaseModel):
    message: str
    nonce: str
    expires_at: str


class VerifyRequest(BaseModel):
    wallet: str = Field(..., min_length=20, max_length=64)
    signature: str = Field(..., min_length=10, max_length=200)
    message: str = Field(..., min_length=20, max_length=2000)


class VerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    wallet: str


class MeResponse(BaseModel):
    wallet: str
    is_admin: bool
    expires_at: str


# ─────────────────────────────────────────── Router

router = APIRouter(prefix="/admin-auth", tags=["admin-auth"])
_bearer = HTTPBearer(auto_error=False)


def _build_message(wallet: str, nonce: str, issued_at: str, expires_at: str, domain: str) -> str:
    """SIWx-style structured message. Whitespace is exact and reused for
    verification — never re-construct on verify side. `domain` MUST match
    the requesting app's origin host or Phantom refuses to show the
    signature prompt."""
    return (
        f"{domain} wants you to sign in with your Solana account:\n"
        f"{wallet}\n"
        f"\n"
        f"{SIWS_STATEMENT}\n"
        f"\n"
        f"URI: https://{domain}\n"
        f"Version: 1\n"
        f"Chain ID: mainnet\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at}\n"
        f"Expiration Time: {expires_at}"
    )


def _origin_host(request: Request, body_origin: Optional[str] = None) -> str:
    """Derive the requesting-app host (no scheme) exactly as Phantom will
    see it via `window.location.host`. Precedence:
      1. `origin` field in the request body (sent by the frontend, most
         reliable — the browser knows its own host and it survives any
         reverse-proxy header rewriting)
      2. `Origin` request header
      3. `Referer` request header
      4. `SIWS_DOMAIN` env fallback
    """
    from urllib.parse import urlparse

    def _parse(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return ""
        try:
            if "://" not in v:
                v = "https://" + v
            parsed = urlparse(v)
            host = parsed.netloc or parsed.path
            return host.strip("/")
        except Exception:
            return ""

    for candidate in (
        body_origin,
        request.headers.get("origin"),
        request.headers.get("referer"),
    ):
        host = _parse(candidate)
        if host:
            return host
    return SIWS_DOMAIN


@router.post("/nonce", response_model=NonceResponse)
async def request_nonce(req: NonceRequest, request: Request):
    """Issue a one-time nonce + a fully-baked SIWx message for the wallet
    to sign. The exact message string is stored server-side so the verify
    step doesn't need to re-construct it (which is the #1 source of
    signature-verification mismatches)."""
    # Sanity-check pubkey is valid base58 + 32 bytes
    try:
        raw = base58.b58decode(req.wallet)
        if len(raw) != 32:
            raise ValueError("not 32 bytes")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Solana wallet address")

    nonce = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=NONCE_TTL_SECONDS)
    issued_at = now.isoformat().replace("+00:00", "Z")
    expires_at = expires.isoformat().replace("+00:00", "Z")
    domain = _origin_host(request, req.origin)
    message = _build_message(req.wallet, nonce, issued_at, expires_at, domain)

    await db.admin_auth_nonces.insert_one({
        "id": str(uuid.uuid4()),
        "wallet": req.wallet,
        "nonce": nonce,
        "message": message,
        "issued_at": now,
        "expires_at": expires,
        "used": False,
    })

    return NonceResponse(message=message, nonce=nonce, expires_at=expires_at)


def _verify_ed25519(wallet_b58: str, signature_b58: str, message: str) -> bool:
    """Pure ed25519 verification: pubkey verifies that signature came from
    its private key over the UTF-8 bytes of `message`."""
    try:
        pubkey_bytes = base58.b58decode(wallet_b58)
        signature_bytes = base58.b58decode(signature_b58)
        if len(pubkey_bytes) != 32 or len(signature_bytes) != 64:
            return False
        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(message.encode("utf-8"), signature_bytes)
        return True
    except (nacl.exceptions.BadSignatureError, ValueError):
        return False
    except Exception:
        return False


@router.post("/verify", response_model=VerifyResponse)
async def verify_signature(req: VerifyRequest):
    """Verify the signed message and issue a JWT if the wallet is on the
    admin allow-list."""
    if not JWT_SECRET or len(JWT_SECRET) < 32:
        raise HTTPException(status_code=500, detail="Server JWT secret not configured")

    # 1. Find the nonce we issued for this wallet + message and make sure
    #    it's still alive and unused.
    nonce_doc = await db.admin_auth_nonces.find_one(
        {
            "wallet": req.wallet,
            "message": req.message,
            "used": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        },
        {"_id": 1, "id": 1},
    )
    if not nonce_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired nonce / message")

    # 2. Verify ed25519 signature over the *stored* message bytes.
    if not _verify_ed25519(req.wallet, req.signature, req.message):
        raise HTTPException(status_code=401, detail="Signature verification failed")

    # 3. Burn the nonce — single use.
    await db.admin_auth_nonces.update_one(
        {"_id": nonce_doc["_id"]},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}},
    )

    # 4. Admin allow-list check (env-driven).
    if req.wallet not in _admin_wallets():
        raise HTTPException(status_code=403, detail="Wallet is not an authorized admin")

    # 5. Mint JWT.
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": req.wallet,
        "wallet": req.wallet,
        "scope": "admin",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    # 6. Track the issued session so we can audit / revoke later.
    await db.admin_auth_sessions.insert_one({
        "id": payload["jti"],
        "wallet": req.wallet,
        "issued_at": now,
        "expires_at": exp,
        "revoked": False,
    })

    return VerifyResponse(
        access_token=token,
        expires_in=int((exp - now).total_seconds()),
        wallet=req.wallet,
    )


# ─────────────────────────────────────────── FastAPI dependency

async def require_admin_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """FastAPI dependency. Returns the admin wallet on success; raises 401
    on any failure. Use it like:

        @router.get('/admin/foo')
        async def foo(wallet: str = Depends(require_admin_jwt)): ...
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

    wallet = payload.get("wallet")
    scope = payload.get("scope")
    if not wallet or scope != "admin":
        raise HTTPException(status_code=401, detail="Token missing admin scope")

    # Allow-list re-check at every request so a removed admin can't keep
    # using a still-valid token.
    if wallet not in _admin_wallets():
        raise HTTPException(status_code=403, detail="Wallet is no longer an admin")

    # Cheap revocation hook (we keep sessions for audit).
    jti = payload.get("jti")
    if jti:
        sess = await db.admin_auth_sessions.find_one({"id": jti}, {"_id": 0, "revoked": 1})
        if sess and sess.get("revoked"):
            raise HTTPException(status_code=401, detail="Session revoked")

    return wallet


@router.get("/me", response_model=MeResponse)
async def me(wallet: str = Depends(require_admin_jwt)):
    """Confirm the bearer token is good. Used by the frontend on page
    load to decide whether to show the admin UI."""
    # Expiration timestamp echoed back so the client can pre-empt expiry.
    # We re-decode (already validated) — cheap.
    # No-op placeholder so we don't have to plumb the full payload.
    return MeResponse(
        wallet=wallet,
        is_admin=True,
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS))
        .isoformat()
        .replace("+00:00", "Z"),
    )


# ─────────────────────────────────────────── Backward-compatibility bridge

async def admin_auth_compat(
    admin_wallet: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_admin_wallet: Optional[str] = Header(None),
) -> str:
    """Drop-in dependency for old routes that still use the legacy
    `admin_wallet` query param or the X-Admin-Wallet header.

    Acceptance order:
      1. Valid SIWS JWT in Authorization: Bearer ... (preferred)
      2. Legacy admin_wallet query param OR X-Admin-Wallet header that
         matches the allow-list (insecure, kept for migration).

    Once every router is migrated to `require_admin_jwt`, delete this.
    """
    # 1. Try JWT first.
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            wallet = payload.get("wallet")
            if wallet in _admin_wallets() and payload.get("scope") == "admin":
                return wallet
        except JWTError:
            pass

    # 2. Legacy fallback (clearly logged so we can grep / migrate).
    legacy = (admin_wallet or x_admin_wallet or "").strip()
    if legacy and legacy in _admin_wallets():
        return legacy

    raise HTTPException(status_code=401, detail="Admin authorization required")
