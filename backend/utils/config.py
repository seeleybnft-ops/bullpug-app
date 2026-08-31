"""Configuration settings for the Bullpug application."""

import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Stripe
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# SendGrid (legacy — kept for any callers that still reference it, but
# `send_email()` now dispatches via Resend.)
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

# Resend (primary transactional email provider)
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')

SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@bullpug.com')

# P2P Betting
RAKE_PERCENT = 2.5
DISTRIBUTION_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"
ESCROW_WALLET = DISTRIBUTION_WALLET

# Store wallet for skin purchases
STORE_WALLET = DISTRIBUTION_WALLET

# Admin wallets — env-driven with a code default so the app boots even
# without ADMIN_WALLETS set. ALL admin auth (SIWS + legacy compat) reads
# from this list.
_admin_env = os.environ.get("ADMIN_WALLETS", "").strip()
if _admin_env:
    ADMIN_WALLETS = [w.strip() for w in _admin_env.split(",") if w.strip()]
else:
    ADMIN_WALLETS = [
        "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT",  # Fee wallet
        "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"   # Personal wallet
    ]

# CORS
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

# Helper function
def is_admin(wallet_address: str) -> bool:
    """Check if a wallet address is an admin."""
    return wallet_address in ADMIN_WALLETS
