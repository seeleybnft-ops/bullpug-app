"""Configuration settings for the Bullpug application."""

import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Stripe
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# SendGrid
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@bullpug.com')

# P2P Betting
RAKE_PERCENT = 2.5
DISTRIBUTION_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"
ESCROW_WALLET = DISTRIBUTION_WALLET

# Admin wallets
ADMIN_WALLETS = [
    "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT",  # Fee wallet
    "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"   # Personal wallet
]

# CORS
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
