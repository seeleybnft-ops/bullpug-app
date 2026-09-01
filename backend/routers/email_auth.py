"""Email OTP authentication.

Flow (spec Part 2):
  1. POST /email/request { email } → 6-digit OTP, bcrypt-hashed, stored
     in `auth_otps`, sent via Resend. Rate-limited 3/hr/email.
  2. POST /email/verify { email, otp } → verifies, mints 7-day JWT with
     scope="user". First-time verifier creates a `users` row.
  3. GET  /me   → returns { user_id, auth_type, email?, wallet_address?,
     rank, unlocked_count }. Requires user JWT.
  4. DELETE /account → GDPR-style hard delete of everything keyed by
     user_id (see spec Compliance Note). Requires user JWT.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel, EmailStr

from services.email_service import send_email
from utils.database import db
from utils.email_auth_config import (
    JWT_ALGORITHM,
    JWT_SECRET,
    OTP_LENGTH,
    OTP_MAX_VERIFY_ATTEMPTS,
    OTP_REQUESTS_PER_HOUR,
    OTP_TTL_MINUTES,
    USER_JWT_EXPIRATION_DAYS,
)
from utils.email_auth_deps import get_current_user
from utils.user_identity import create_email_user, resolve_email_user, touch_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Models ─────────────────────────────────────────────────────────
class EmailRequestBody(BaseModel):
    email: EmailStr


class EmailVerifyBody(BaseModel):
    email: EmailStr
    otp: str


class TokenResponse(BaseModel):
    token: str
    user_id: str
    is_new_user: bool
    email: str


# ─── Copy (Tinkerpug voice, per spec) ───────────────────────────────
_OTP_SUBJECT = "your access code"


def _otp_body(code: str) -> str:
    """Plain-text-feel body (<pre> wrapper) — same styling as the Act I
    confirmation email so the "keeper's log" identity stays consistent
    across every transactional Bullpug email."""
    text = (
        "keeper's log — access code requested.\n"
        "\n"
        f"Your code: {code}\n"
        "\n"
        f"Valid for {OTP_TTL_MINUTES} minutes. Single use.\n"
        "\n"
        "keeper's note: if you didn't request this, ignore it. The Archive will be here when you're ready.\n"
        "\n"
        "bullpug.com/archive"
    )
    return (
        "<pre style=\"font-family: ui-monospace, SFMono-Regular, Menlo, monospace; "
        "background: #0a0a12; color: #dce2f0; padding: 24px; border-radius: 12px; "
        "line-height: 1.6; margin: 0; white-space: pre-wrap; font-size: 14px;\">"
        f"{text}"
        "</pre>"
    )


# ─── Helpers ────────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_otp(code: str) -> str:
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_otp(code: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _generate_otp() -> str:
    # secrets.randbelow(10**OTP_LENGTH) is uniform; zero-pad to length.
    n = secrets.randbelow(10 ** OTP_LENGTH)
    return str(n).zfill(OTP_LENGTH)


def _mint_user_jwt(user_id: str, email: str) -> tuple[str, datetime]:
    now = _now()
    exp = now + timedelta(days=USER_JWT_EXPIRATION_DAYS)
    payload = {
        "sub": user_id,
        "email": email,
        "scope": "user",
        "auth_type": "email",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM), exp


# ─── Endpoints ──────────────────────────────────────────────────────
@router.post("/email/request")
async def request_email_otp(body: EmailRequestBody):
    """Generate + email a fresh OTP. Rate-limited per email."""
    email = body.email.strip().lower()

    # Rate limit: max 3 requests per email per rolling hour.
    an_hour_ago = _now() - timedelta(hours=1)
    recent_count = await db.auth_otps.count_documents({
        "email": email,
        "created_at": {"$gte": an_hour_ago.isoformat()},
    })
    if recent_count >= OTP_REQUESTS_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Too many codes requested. Try again in an hour.",
        )

    # Invalidate any previous unused codes for this email — one active
    # OTP at a time is a much cleaner UX.
    await db.auth_otps.update_many(
        {"email": email, "used": False},
        {"$set": {"used": True, "invalidated_at": _now().isoformat()}},
    )

    code = _generate_otp()
    otp_row = {
        "email": email,
        "otp_hash": _hash_otp(code),
        "created_at": _now().isoformat(),
        "expires_at": (_now() + timedelta(minutes=OTP_TTL_MINUTES)).isoformat(),
        "used": False,
        "verify_attempts": 0,
    }
    await db.auth_otps.insert_one(otp_row)

    # Dispatch (blocking send is fine here — the caller waits so we can
    # surface Resend failures as 500s and the user knows to retry). The
    # send function is already async / non-blocking on the loop.
    try:
        sent = await send_email(email, _OTP_SUBJECT, _otp_body(code))
    except Exception:
        logger.exception("otp send crashed for %s", email)
        sent = False
    if not sent:
        # Delete the row so we don't waste a rate-limit slot on a failed send.
        await db.auth_otps.delete_one({"email": email, "otp_hash": otp_row["otp_hash"]})
        raise HTTPException(status_code=502, detail="Could not send access code. Please try again.")

    return {"success": True, "expires_in": OTP_TTL_MINUTES * 60}


@router.post("/email/verify", response_model=TokenResponse)
async def verify_email_otp(body: EmailVerifyBody):
    """Validate OTP, mint 7-day JWT, create user row if first sign-in."""
    email = body.email.strip().lower()
    code = body.otp.strip()

    if not code.isdigit() or len(code) != OTP_LENGTH:
        raise HTTPException(status_code=400, detail="Invalid code format")

    # Fetch the most recent unused, unexpired OTP for this email.
    otp_row = await db.auth_otps.find_one(
        {
            "email": email,
            "used": False,
            "expires_at": {"$gte": _now().isoformat()},
        },
        sort=[("created_at", -1)],
    )
    if not otp_row:
        raise HTTPException(status_code=400, detail="Code expired or not found. Request a new one.")

    # Track attempts so brute-forcing a 6-digit space (1M combos) is
    # infeasible: after 5 wrong guesses this OTP row is dead.
    if otp_row.get("verify_attempts", 0) >= OTP_MAX_VERIFY_ATTEMPTS:
        await db.auth_otps.update_one(
            {"_id": otp_row["_id"]},
            {"$set": {"used": True, "invalidated_at": _now().isoformat()}},
        )
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

    if not _verify_otp(code, otp_row["otp_hash"]):
        await db.auth_otps.update_one(
            {"_id": otp_row["_id"]},
            {"$inc": {"verify_attempts": 1}},
        )
        raise HTTPException(status_code=400, detail="Incorrect code.")

    # Success — burn the OTP.
    await db.auth_otps.update_one(
        {"_id": otp_row["_id"]},
        {"$set": {"used": True, "verified_at": _now().isoformat()}},
    )

    # Resolve or create the users row.
    existing = await resolve_email_user(email)
    is_new_user = existing is None
    user = existing if existing else await create_email_user(email)
    await touch_user(user["user_id"])

    token, _exp = _mint_user_jwt(user["user_id"], user["email"])
    return TokenResponse(
        token=token,
        user_id=user["user_id"],
        is_new_user=is_new_user,
        email=user["email"],
    )


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return the signed-in user's profile + top-level Archive stats.

    Phase A note: `rank` and `unlocked_count` are best-effort — they
    look up the Archive collections by user_id, which will only find
    rows once Phase B routes start writing them. Zero-defaults are safe
    (a brand-new email user always starts with rank=None, unlocks=0).
    """
    user_id = user["user_id"]
    rank_doc = await db.archive_ranks.find_one({"user_id": user_id}, {"_id": 0})
    unlocked_count = await db.archive_unlocks.count_documents({"user_id": user_id})

    return {
        "user_id": user_id,
        "auth_type": user.get("auth_type"),
        "email": user.get("email"),
        "wallet_address": user.get("wallet_address"),
        "rank": (rank_doc or {}).get("rank"),
        "rank_title": (rank_doc or {}).get("rank_title"),
        "unlocked_count": unlocked_count,
    }


@router.delete("/account")
async def delete_account(user: dict = Depends(get_current_user)):
    """GDPR-style hard delete (spec Compliance Note).

    Removes every document keyed on this user_id across all identity
    collections, then removes the users row itself. Wallet-side rows
    (keyed by wallet_address) are also removed if the user was linked.
    Idempotent — running it twice returns zero deletes on the second call.
    """
    user_id = user["user_id"]
    wallet = user.get("wallet_address")

    # Collections that carry user_id (once Phase B writes start).
    id_targets = [
        "archive_unlocks",
        "archive_ranks",
        "archive_announcements",
        "daily_drops",
        "chat_history",
        "tinkerpug_turns",
        "companion_tokens",
        "share_card_art",
        "keeper_announcements",
        "auth_otps",
    ]
    deleted = {}
    for name in id_targets:
        r = await db[name].delete_many({"user_id": user_id})
        deleted[name] = r.deleted_count

    # For linked wallet users, sweep the wallet-keyed rows too.
    if wallet:
        wallet_targets = [
            ("archive_unlocks", "wallet_address"),
            ("archive_ranks", "wallet_address"),
            ("archive_announcements", "wallet_address"),
            ("daily_drops", "wallet_address"),
            ("chat_history", "wallet_address"),
            ("tinkerpug_turns", "wallet_address"),
            ("companion_tokens", "wallet_claimed"),
            ("share_card_art", "wallet"),
            ("keeper_announcements", "wallet_address"),
        ]
        for name, field in wallet_targets:
            r = await db[name].delete_many({field: wallet})
            deleted[f"{name} (wallet)"] = deleted.get(name, 0) + r.deleted_count

    # And finally the users row itself.
    r = await db.users.delete_one({"user_id": user_id})
    deleted["users"] = r.deleted_count

    logger.info("account_delete: user_id=%s totals=%s", user_id, deleted)
    return {"success": True, "deleted": deleted}
