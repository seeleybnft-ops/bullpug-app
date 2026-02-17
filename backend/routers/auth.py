"""Authentication routes for wallet verification."""

from fastapi import APIRouter
import secrets
from datetime import datetime, timezone, timedelta

from utils.database import db
from services.auth_service import verify_wallet_signature

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/sign-message/{wallet_address}")
async def get_sign_message(wallet_address: str, action: str = "general"):
    """Generate a message for wallet signature verification."""
    nonce = secrets.token_hex(16)
    timestamp = datetime.now(timezone.utc).isoformat()
    message = f"Bullpug Action: {action}\nWallet: {wallet_address}\nNonce: {nonce}\nTimestamp: {timestamp}"
    
    await db.auth_nonces.insert_one({
        "nonce": nonce,
        "wallet_address": wallet_address,
        "action": action,
        "created_at": timestamp,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    })
    
    return {"message": message, "nonce": nonce}


@router.post("/verify-signature")
async def verify_signature_endpoint(wallet_address: str, message: str, signature: str):
    """Verify a wallet signature."""
    is_valid = verify_wallet_signature(wallet_address, message, signature)
    return {"valid": is_valid, "wallet": wallet_address}
