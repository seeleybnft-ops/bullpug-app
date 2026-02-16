"""Wallet signature verification service."""

import logging
import base58
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from typing import Optional

logger = logging.getLogger(__name__)


def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    """
    Verify a Solana wallet signature to ensure the user owns the wallet.
    This prevents impersonation attacks where someone uses another user's wallet address.
    """
    try:
        # Decode the wallet public key
        public_key_bytes = base58.b58decode(wallet_address)
        verify_key = VerifyKey(public_key_bytes)
        
        # Decode the signature
        signature_bytes = base58.b58decode(signature)
        
        # Encode the message
        message_bytes = message.encode('utf-8')
        
        # Verify the signature
        verify_key.verify(message_bytes, signature_bytes)
        return True
    except BadSignatureError:
        logger.warning(f"Invalid signature for wallet {wallet_address[:8]}...")
        return False
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def verify_request_signature(
    wallet_address: str, 
    signature: Optional[str], 
    message: Optional[str], 
    strict: bool = False
) -> bool:
    """
    Helper to verify request signature. If strict=True, reject if signature is missing.
    If strict=False, allow requests without signature (backward compatible).
    """
    if not signature or not message:
        if strict:
            return False
        return True  # Allow unsigned requests in non-strict mode
    
    return verify_wallet_signature(wallet_address, message, signature)
