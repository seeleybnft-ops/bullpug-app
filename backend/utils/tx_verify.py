"""On-chain Solana transaction verification.

Used by user-supplied tx-signature endpoints (tip the pot, escrow deposit,
skin purchase) to make sure the claim is real: that the signature is
confirmed on mainnet, that the funds actually went to the expected escrow
wallet, and that the amount matches what the client claims.

Uses HELIUS_RPC_URL when set (paid tier, way higher rate limits than the
public mainnet beta RPC). Falls back to api.mainnet-beta.solana.com.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

LAMPORTS_PER_SOL = 1_000_000_000


def _rpc_url() -> str:
    return os.environ.get("HELIUS_RPC_URL") or "https://api.mainnet-beta.solana.com"


async def verify_sol_transfer(
    tx_signature: str,
    expected_recipient: str,
    expected_amount_sol: float,
    *,
    expected_sender: Optional[str] = None,
    tolerance_lamports: int = 0,
) -> tuple[bool, str]:
    """Confirm a Solana tx actually transferred ``expected_amount_sol`` to
    ``expected_recipient``.

    Returns ``(ok, reason)``. ``reason`` is empty on success and a short
    human-readable string on failure (e.g. ``"recipient mismatch"``).

    The check is balance-delta based: we read ``pre`` / ``post`` lamport
    balances of the recipient account in the tx and require that the
    increase equals the expected amount (within ``tolerance_lamports``).
    This is robust against transfer-with-memo, jito-bundle envelopes, etc.
    """
    if not tx_signature or len(tx_signature) < 16:
        return False, "missing or malformed signature"

    expected_lamports = int(round(expected_amount_sol * LAMPORTS_PER_SOL))
    if expected_lamports <= 0:
        return False, "non-positive amount"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            tx_signature,
            {"encoding": "jsonParsed", "commitment": "confirmed", "maxSupportedTransactionVersion": 0},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(_rpc_url(), json=payload)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("RPC error verifying %s: %s", tx_signature, e)
        return False, "rpc error"

    if data.get("error"):
        return False, f"rpc: {data['error'].get('message', 'unknown')}"

    result = data.get("result")
    if not result:
        return False, "tx not found / not confirmed yet"
    if result.get("meta", {}).get("err"):
        return False, "tx failed on-chain"

    # Pull every account key from the message (covers both legacy and v0).
    msg = result.get("transaction", {}).get("message", {}) or {}
    account_keys = []
    for key in msg.get("accountKeys", []) or []:
        if isinstance(key, dict):
            account_keys.append(key.get("pubkey"))
        else:
            account_keys.append(key)
    # Include lookup-table loaded addresses for v0 messages.
    loaded = result.get("meta", {}).get("loadedAddresses") or {}
    account_keys.extend(loaded.get("writable", []) or [])
    account_keys.extend(loaded.get("readonly", []) or [])

    if expected_recipient not in account_keys:
        return False, "recipient mismatch"

    pre_balances = result.get("meta", {}).get("preBalances", []) or []
    post_balances = result.get("meta", {}).get("postBalances", []) or []
    try:
        idx = account_keys.index(expected_recipient)
        delta = int(post_balances[idx]) - int(pre_balances[idx])
    except (ValueError, IndexError, TypeError):
        return False, "balance read failed"

    if delta < expected_lamports - tolerance_lamports:
        return False, f"amount mismatch: delta {delta} < expected {expected_lamports}"

    if expected_sender:
        # Sender doesn't have to be the fee payer (delegations, etc.), but for
        # our flows the user is always the fee payer + signer of the transfer.
        signers = msg.get("accountKeys", [])
        signer_keys = []
        for k in signers:
            if isinstance(k, dict) and k.get("signer"):
                signer_keys.append(k.get("pubkey"))
        if signer_keys and expected_sender not in signer_keys:
            return False, "sender mismatch"

    return True, ""
