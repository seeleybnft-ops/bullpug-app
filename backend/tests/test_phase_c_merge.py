"""Phase C — wallet-link + account-merge backend contract tests.

Covers:
  * POST /api/auth/wallet/link  → merge_required=true when the wallet
    already has its own users row.
  * POST /api/auth/merge (keep='email')   → moves rows to email uid.
  * POST /api/auth/merge (keep='wallet')  → moves rows to wallet uid.
"""

import os
import sys
import time
import asyncio
from datetime import datetime, timezone, timedelta

import bcrypt
import pytest
import requests
import base58
from nacl.signing import SigningKey
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get(
    "REACT_APP_BACKEND_URL"
) else "https://cosmic-runner-hub.preview.emergentagent.com"
# Frontend .env carries the public URL — but python only sees backend .env.
# Hard-load frontend .env too.
from dotenv import dotenv_values
_fe = dotenv_values("/app/frontend/.env")
if _fe.get("REACT_APP_BACKEND_URL"):
    BASE_URL = _fe["REACT_APP_BACKEND_URL"].rstrip("/")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


# ─── Helpers ────────────────────────────────────────────────────────
def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _db():
    return AsyncIOMotorClient(MONGO_URL)[DB_NAME]


def _make_solana_keypair():
    """Generate an ed25519 keypair; return (base58_pubkey, SigningKey)."""
    sk = SigningKey.generate()
    pub_bytes = sk.verify_key.encode()
    return base58.b58encode(pub_bytes).decode(), sk


def _sign_siws(sk: SigningKey, message: str) -> str:
    sig = sk.sign(message.encode("utf-8")).signature
    return base58.b58encode(sig).decode()


def _seed_otp_sync(email: str, code: str = "313131"):
    email = email.strip().lower()  # endpoint lowercases before lookup
    async def go():
        d = _db()
        now = datetime.now(timezone.utc)
        await d.auth_otps.delete_many({"email": email})
        await d.auth_otps.insert_one({
            "email": email,
            "otp_hash": bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode(),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
            "used": False,
            "verify_attempts": 0,
        })
    _run(go())


def _seed_wallet_user(wallet: str):
    """Create a wallet-only users row (matches resolve_or_create_wallet_user)."""
    async def go():
        d = _db()
        uid = f"wallet_{wallet}"
        await d.users.delete_one({"user_id": uid})
        await d.users.insert_one({
            "user_id": uid,
            "email": None,
            "email_verified": False,
            "wallet_address": wallet,
            "auth_type": "wallet",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return uid
    return _run(go())


def _seed_archive_unlock(user_id: str, slug: str):
    """Insert with a unique wallet_address/entry_id so the compound index passes."""
    async def go():
        d = _db()
        await d.archive_unlocks.insert_one({
            "user_id": user_id,
            "chapter_slug": slug,
            "wallet_address": f"testwallet_{slug}",
            "entry_id": slug,
            "unlocked_at": datetime.now(timezone.utc).isoformat(),
        })
    _run(go())


def _get_archive_unlock_uid(slug: str):
    async def go():
        d = _db()
        doc = await d.archive_unlocks.find_one({"chapter_slug": slug}, {"_id": 0})
        return (doc or {}).get("user_id")
    return _run(go())


def _cleanup(user_ids, wallets, slugs, emails):
    async def go():
        d = _db()
        for uid in user_ids:
            await d.users.delete_many({"user_id": uid})
            await d.archive_unlocks.delete_many({"user_id": uid})
        for s in slugs:
            await d.archive_unlocks.delete_many({"chapter_slug": s})
        for w in wallets:
            await d.admin_auth_nonces.delete_many({"wallet": w})
        for e in emails:
            await d.auth_otps.delete_many({"email": e})
            await d.users.delete_many({"email": e})
    _run(go())


# ─── Session-scoped fixtures ────────────────────────────────────────
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "X-Bullpug-CSRF": "1"})
    return s


@pytest.fixture(scope="module")
def email_jwt(session):
    """Seed OTP → verify → return email JWT + user_id + email."""
    email = f"test_phasec_{int(time.time())}@mailinator.com"
    code = "313131"
    _seed_otp_sync(email, code)
    r = session.post(
        f"{BASE_URL}/api/auth/email/verify",
        json={"email": email, "otp": code},
        headers={"X-Bullpug-CSRF": "1"},
    )
    assert r.status_code == 200, f"OTP verify failed: {r.status_code} {r.text}"
    data = r.json()
    yield {
        "token": data["token"],
        "user_id": data["user_id"],
        "email": email,
    }
    # teardown
    _cleanup([data["user_id"]], [], [], [email])


# ─── Tests ──────────────────────────────────────────────────────────
class TestWalletLinkMergeRequired:
    """POST /auth/wallet/link returns merge_required when wallet already has a user row."""

    def test_link_returns_merge_required(self, session, email_jwt):
        pub_b58, sk = _make_solana_keypair()
        wallet_uid = _seed_wallet_user(pub_b58)
        slug = f"TEST_slug_{int(time.time())}"
        _seed_archive_unlock(wallet_uid, slug)

        # 1. nonce
        n = session.post(f"{BASE_URL}/api/admin-auth/nonce", json={"wallet": pub_b58})
        assert n.status_code == 200, f"nonce failed: {n.text}"
        message = n.json()["message"]

        # 2. sign + link
        sig = _sign_siws(sk, message)
        r = session.post(
            f"{BASE_URL}/api/auth/wallet/link",
            json={"wallet": pub_b58, "message": message, "signature": sig},
            headers={"Authorization": f"Bearer {email_jwt['token']}"},
        )
        assert r.status_code == 200, f"link failed: {r.status_code} {r.text}"
        body = r.json()
        assert body.get("merge_required") is True
        assert body.get("email_user_id") == email_jwt["user_id"]
        assert body.get("wallet_user_id") == wallet_uid
        assert body.get("email") == email_jwt["email"]
        assert body.get("wallet") == pub_b58

        # cleanup
        _cleanup([wallet_uid], [pub_b58], [slug], [])


class TestMergeKeepEmail:
    """POST /auth/merge with keep='email' moves rows onto email user_id."""

    def test_merge_keep_email_moves_archive_unlock(self, session, email_jwt):
        pub_b58, sk = _make_solana_keypair()
        wallet_uid = _seed_wallet_user(pub_b58)
        slug = f"TEST_ke_{int(time.time())}"
        _seed_archive_unlock(wallet_uid, slug)

        # verify pre-condition
        assert _get_archive_unlock_uid(slug) == wallet_uid

        r = session.post(
            f"{BASE_URL}/api/auth/merge",
            json={"keep": "email", "wallet_user_id": wallet_uid},
            headers={"Authorization": f"Bearer {email_jwt['token']}"},
        )
        assert r.status_code == 200, f"merge failed: {r.text}"
        body = r.json()
        assert body["success"] is True
        assert body["primary_user_id"] == email_jwt["user_id"]
        assert body["moved"]["archive_unlocks"] >= 1

        # persistence check: the archive_unlocks row now points at email uid
        assert _get_archive_unlock_uid(slug) == email_jwt["user_id"]

        # discarded wallet row is flagged
        async def check():
            d = _db()
            doc = await d.users.find_one({"user_id": wallet_uid}, {"_id": 0})
            return doc
        discarded = _run(check())
        assert discarded is not None
        assert discarded.get("merged_into") == email_jwt["user_id"]

        _cleanup([wallet_uid], [pub_b58], [slug], [])


class TestMergeKeepWallet:
    """POST /auth/merge with keep='wallet' moves email rows onto wallet user_id."""

    def test_merge_keep_wallet(self, session):
        # Fresh email user for this test so we can dispose of it after
        email = f"test_kw_{int(time.time())}@mailinator.com"
        _seed_otp_sync(email, "313131")
        v = session.post(
            f"{BASE_URL}/api/auth/email/verify",
            json={"email": email, "otp": "313131"},
            headers={"X-Bullpug-CSRF": "1"},
        )
        assert v.status_code == 200
        email_data = v.json()
        email_uid = email_data["user_id"]
        token = email_data["token"]

        # Seed a wallet-only user + a row for the email user we want to move
        pub_b58, _sk = _make_solana_keypair()
        wallet_uid = _seed_wallet_user(pub_b58)
        slug = f"TEST_kwslug_{int(time.time())}"
        _seed_archive_unlock(email_uid, slug)
        assert _get_archive_unlock_uid(slug) == email_uid

        r = session.post(
            f"{BASE_URL}/api/auth/merge",
            json={"keep": "wallet", "wallet_user_id": wallet_uid},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, f"merge failed: {r.text}"
        body = r.json()
        assert body["success"] is True
        assert body["primary_user_id"] == wallet_uid

        # persistence check: row moved from email uid → wallet uid
        assert _get_archive_unlock_uid(slug) == wallet_uid

        # wallet primary row now carries the email
        async def check():
            d = _db()
            return await d.users.find_one({"user_id": wallet_uid}, {"_id": 0})
        primary = _run(check())
        assert primary is not None
        assert primary.get("email") == email
        assert primary.get("auth_type") == "linked"

        _cleanup([wallet_uid, email_uid], [pub_b58], [slug], [email])


class TestMergeValidation:
    def test_merge_bad_keep_value(self, session, email_jwt):
        r = session.post(
            f"{BASE_URL}/api/auth/merge",
            json={"keep": "bogus", "wallet_user_id": "wallet_x"},
            headers={"Authorization": f"Bearer {email_jwt['token']}"},
        )
        assert r.status_code == 400

    def test_merge_missing_discarded_user(self, session, email_jwt):
        r = session.post(
            f"{BASE_URL}/api/auth/merge",
            json={"keep": "email", "wallet_user_id": "wallet_does_not_exist_TEST"},
            headers={"Authorization": f"Bearer {email_jwt['token']}"},
        )
        assert r.status_code == 404

    def test_merge_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/auth/merge",
            json={"keep": "email", "wallet_user_id": "wallet_x"},
        )
        assert r.status_code in (401, 403)


class TestWalletLinkValidation:
    def test_link_bad_signature(self, session, email_jwt):
        pub_b58, _sk = _make_solana_keypair()
        # request nonce (real)
        n = session.post(f"{BASE_URL}/api/admin-auth/nonce", json={"wallet": pub_b58})
        assert n.status_code == 200
        msg = n.json()["message"]
        # sign with a DIFFERENT key
        _pub2, sk2 = _make_solana_keypair()
        bad_sig = _sign_siws(sk2, msg)
        r = session.post(
            f"{BASE_URL}/api/auth/wallet/link",
            json={"wallet": pub_b58, "message": msg, "signature": bad_sig},
            headers={"Authorization": f"Bearer {email_jwt['token']}"},
        )
        assert r.status_code == 401
