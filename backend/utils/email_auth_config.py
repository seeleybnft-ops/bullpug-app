"""Shared JWT config for the new user (email) auth path.

Kept separate from `utils/admin_auth.py` so admin sessions and user
sessions are logically distinct even though they share a secret. The
JWT's `scope` field ("admin" vs "user") is what actually separates
them at the dependency layer.
"""

import os

JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
# 7 days per spec — matches the wallet SIWS session length.
USER_JWT_EXPIRATION_DAYS = 7

# OTP policy
OTP_LENGTH = 6
OTP_TTL_MINUTES = 10
OTP_REQUESTS_PER_HOUR = 3
OTP_MAX_VERIFY_ATTEMPTS = 5  # per OTP row before it self-invalidates
