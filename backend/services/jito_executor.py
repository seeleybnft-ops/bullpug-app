"""
Jito Bundle Executor

Provides MEV-protected transaction execution via Jito bundles.
Transactions are bundled and sent through Jito's block engine for:
- Front-running protection
- Higher landing rate
- Priority execution

Falls back to standard RPC submission if Jito is unavailable.
"""
import os
import logging
import base64
import base58
import httpx
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Jito Block Engine endpoints (regional)
JITO_BLOCK_ENGINES = [
    "https://mainnet.block-engine.jito.wtf",
    "https://ny.mainnet.block-engine.jito.wtf",
    "https://amsterdam.mainnet.block-engine.jito.wtf",
    "https://tokyo.mainnet.block-engine.jito.wtf",
]

# Jito tip accounts (official accounts for priority tips)
JITO_TIP_ACCOUNTS = [
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4bPUBAmNTQVA7yFFxkcZRiH",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSLBTh1mAqD1NLgS7g",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
]

# Default tip amount in lamports (0.0001 SOL = 100,000 lamports)
DEFAULT_TIP_LAMPORTS = 100_000

# High-priority tip for stop-loss orders (0.001 SOL = 1,000,000 lamports)
HIGH_PRIORITY_TIP_LAMPORTS = 1_000_000


async def get_jito_tip_accounts() -> List[str]:
    """Get current Jito tip accounts from the API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{JITO_BLOCK_ENGINES[0]}/api/v1/bundles/tip_accounts"
            )
            if response.status_code == 200:
                accounts = response.json()
                if accounts:
                    return accounts
    except Exception as e:
        logger.warning(f"Failed to fetch Jito tip accounts: {e}")
    return JITO_TIP_ACCOUNTS


async def send_jito_bundle(
    serialized_transactions: List[bytes],
    tip_lamports: int = DEFAULT_TIP_LAMPORTS,
    is_stop_loss: bool = False
) -> Dict:
    """
    Send a bundle of transactions via Jito block engine.

    Args:
        serialized_transactions: List of serialized transaction bytes
        tip_lamports: Tip amount in lamports for Jito validators
        is_stop_loss: If True, use higher tip for priority execution

    Returns:
        Dict with 'success', 'bundle_id', 'error'
    """
    if is_stop_loss:
        tip_lamports = HIGH_PRIORITY_TIP_LAMPORTS

    # Encode transactions to base58
    encoded_txns = []
    for tx_bytes in serialized_transactions:
        encoded_txns.append(base58.b58encode(tx_bytes).decode('ascii'))

    # Try each block engine
    for engine_url in JITO_BLOCK_ENGINES:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendBundle",
                "params": [encoded_txns]
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{engine_url}/api/v1/bundles",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    bundle_id = result.get("result")
                    if bundle_id:
                        logger.info(f"Jito bundle sent: {bundle_id} (tip: {tip_lamports} lamports)")
                        return {
                            "success": True,
                            "bundle_id": bundle_id,
                            "engine": engine_url,
                            "tip_lamports": tip_lamports
                        }

                error_msg = response.text[:200]
                logger.warning(f"Jito engine {engine_url} rejected: {error_msg}")

        except Exception as e:
            logger.warning(f"Jito engine {engine_url} failed: {e}")
            continue

    return {
        "success": False,
        "error": "All Jito block engines failed",
        "tip_lamports": tip_lamports
    }


async def send_transaction_with_jito(
    serialized_tx: bytes,
    is_stop_loss: bool = False
) -> Dict:
    """
    Send a single transaction via Jito for MEV protection.
    Uses sendTransaction endpoint for single transactions.

    Args:
        serialized_tx: Serialized transaction bytes
        is_stop_loss: If True, use higher priority

    Returns:
        Dict with 'success', 'signature', 'method' (jito or fallback)
    """
    # Encode to base58
    encoded_tx = base58.b58encode(serialized_tx).decode('ascii')

    # Try Jito first
    for engine_url in JITO_BLOCK_ENGINES[:2]:  # Try top 2 engines
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [encoded_tx]
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{engine_url}/api/v1/transactions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    signature = result.get("result")
                    if signature:
                        logger.info(f"Transaction sent via Jito: {signature}")
                        return {
                            "success": True,
                            "signature": signature,
                            "method": "jito",
                            "engine": engine_url
                        }

        except Exception as e:
            logger.warning(f"Jito send failed on {engine_url}: {e}")
            continue

    # Fallback to standard RPC
    logger.info("Jito unavailable, falling back to standard RPC")
    return await _fallback_rpc_send(serialized_tx)


async def _fallback_rpc_send(serialized_tx: bytes) -> Dict:
    """
    Fallback: Send transaction via standard Solana RPC.
    """
    rpc_endpoints = [
        os.environ.get("HELIUS_RPC_URL"),
        os.environ.get("ALCHEMY_RPC_URL"),
        "https://api.mainnet-beta.solana.com"
    ]
    rpc_endpoints = [r for r in rpc_endpoints if r]

    encoded_tx = base64.b64encode(serialized_tx).decode('ascii')

    for rpc_url in rpc_endpoints:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    encoded_tx,
                    {
                        "skipPreflight": True,
                        "preflightCommitment": "confirmed",
                        "encoding": "base64",
                        "maxRetries": 3
                    }
                ]
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and not result.get("error"):
                        signature = result["result"]
                        logger.info(f"Transaction sent via RPC fallback: {signature}")
                        return {
                            "success": True,
                            "signature": signature,
                            "method": "rpc_fallback",
                            "rpc": rpc_url[:30] + "..."
                        }

                    error = result.get("error", {})
                    logger.warning(f"RPC error: {error}")

        except Exception as e:
            logger.warning(f"RPC fallback failed on {rpc_url[:30]}...: {e}")
            continue

    return {
        "success": False,
        "error": "All RPC endpoints failed",
        "method": "none"
    }


async def get_bundle_status(bundle_id: str) -> Optional[Dict]:
    """Check the status of a Jito bundle."""
    for engine_url in JITO_BLOCK_ENGINES[:2]:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBundleStatuses",
                "params": [[bundle_id]]
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{engine_url}/api/v1/bundles",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    statuses = result.get("result", {}).get("value", [])
                    if statuses:
                        return statuses[0]

        except Exception:
            continue

    return None
