"""Wallet and Solana balance routes."""

from fastapi import APIRouter
import httpx
import logging


router = APIRouter(prefix="/wallet", tags=["wallet"])
logger = logging.getLogger(__name__)


@router.get("/balance/{address}")
async def get_wallet_balance(address: str):
    """Get SOL balance for a wallet address."""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                "https://api.mainnet-beta.solana.com",
                json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]},
                timeout=10.0
            )
            data = resp.json()
            if "result" in data:
                lamports = data["result"]["value"]
                return {
                    "address": address,
                    "balance_lamports": lamports,
                    "balance_sol": lamports / 1e9
                }
    except Exception as e:
        logger.error(f"Balance error: {e}")
    return {"address": address, "balance_lamports": 0, "balance_sol": 0}
