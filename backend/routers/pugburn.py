"""
PugBurn - Solana Account Cleanup & SOL Reclaim Service
Scans for empty token accounts and allows users to close them to reclaim rent SOL.

Uses the Sol-Incinerator API if available, falls back to direct Solana RPC queries.
"""

import os
import httpx
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pugburn", tags=["PugBurn"])

# Sol-Incinerator API configuration
SOL_INCINERATOR_API_KEY = os.environ.get("SOL_INCINERATOR_API_KEY", "")
SOL_INCINERATOR_BASE_URL = "https://api.sol-incinerator.com"

# Multiple Solana RPC endpoints for reliability
ALCHEMY_API_KEY = os.environ.get("ALCHEMY_API_KEY", "")
SOLANA_RPC_URLS = [
    f"https://solana-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}" if ALCHEMY_API_KEY else None,
    "https://api.mainnet-beta.solana.com",
    "https://rpc.ankr.com/solana",
]
# Filter out None values
SOLANA_RPC_URLS = [url for url in SOLANA_RPC_URLS if url]

# Rent per token account (approximately 0.00203928 SOL for an ATA)
RENT_PER_ACCOUNT_SOL = 0.00203928


class VacantAccount(BaseModel):
    """Represents an empty token account that can be closed"""
    address: str
    mint: str
    symbol: Optional[str] = None
    balance: float = 0
    rent_recoverable: float = RENT_PER_ACCOUNT_SOL
    program_id: str = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # SPL Token by default


class ScanResult(BaseModel):
    """Result of scanning for vacant accounts"""
    wallet_address: str
    vacant_accounts: List[VacantAccount]
    total_accounts_scanned: int
    total_reclaimable_sol: float
    scan_timestamp: str


class CloseAccountsRequest(BaseModel):
    """Request to generate close transaction"""
    wallet_address: str
    account_addresses: List[str]


async def get_token_accounts_via_rpc(wallet_address: str) -> List[Dict[str, Any]]:
    """Fetch all token accounts for a wallet using Solana RPC with multiple fallbacks"""
    
    # Scan both SPL Token and Token-2022 programs
    token_programs = [
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token
        "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",  # Token-2022
    ]
    
    all_accounts = []
    
    for program_id in token_programs:
        for rpc_url in SOLANA_RPC_URLS:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        rpc_url,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getTokenAccountsByOwner",
                            "params": [
                                wallet_address,
                                {"programId": program_id},
                                {"encoding": "jsonParsed"}
                            ]
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "result" in data and "value" in data["result"]:
                            accounts = data["result"]["value"]
                            # Tag accounts with their program type
                            for acc in accounts:
                                acc["_program_id"] = program_id
                            all_accounts.extend(accounts)
                            logger.info(f"Found {len(accounts)} accounts from {program_id[:8]}... via {rpc_url}")
                            break  # Success, move to next program
                        elif "error" in data:
                            logger.warning(f"RPC {rpc_url} error for {program_id[:8]}: {data['error']}")
                            continue
                    
            except Exception as e:
                logger.warning(f"RPC {rpc_url} failed for {program_id[:8]}: {e}")
                continue
    
    if not all_accounts:
        logger.error("All RPC endpoints failed for all programs")
    
    return all_accounts


async def scan_with_sol_incinerator(wallet_address: str) -> Optional[Dict]:
    """Try to use Sol-Incinerator API if key is available"""
    if not SOL_INCINERATOR_API_KEY:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try the Sol-Incinerator API endpoint
            response = await client.get(
                f"{SOL_INCINERATOR_BASE_URL}/v1/scan/{wallet_address}",
                headers={
                    "Authorization": f"Bearer {SOL_INCINERATOR_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Sol-Incinerator API returned {response.status_code}")
                return None
                
    except Exception as e:
        logger.warning(f"Sol-Incinerator API error: {e}")
        return None


@router.get("/scan/{wallet_address}")
async def scan_vacant_accounts(wallet_address: str) -> ScanResult:
    """
    Scan a wallet for empty/vacant token accounts that can be closed to reclaim SOL.
    
    Returns list of accounts with zero balance and the total reclaimable SOL.
    """
    try:
        # Try Sol-Incinerator API first
        incinerator_result = await scan_with_sol_incinerator(wallet_address)
        
        if incinerator_result and "accounts" in incinerator_result:
            # Use Sol-Incinerator response
            vacant_accounts = [
                VacantAccount(
                    address=acc["address"],
                    mint=acc.get("mint", ""),
                    symbol=acc.get("symbol"),
                    balance=float(acc.get("balance", 0)),
                    rent_recoverable=float(acc.get("rent", RENT_PER_ACCOUNT_SOL))
                )
                for acc in incinerator_result.get("accounts", [])
                if float(acc.get("balance", 0)) == 0
            ]
            
            return ScanResult(
                wallet_address=wallet_address,
                vacant_accounts=vacant_accounts,
                total_accounts_scanned=incinerator_result.get("total_scanned", len(vacant_accounts)),
                total_reclaimable_sol=sum(a.rent_recoverable for a in vacant_accounts),
                scan_timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        # Fallback: Direct Solana RPC query
        token_accounts = await get_token_accounts_via_rpc(wallet_address)
        
        vacant_accounts = []
        for account in token_accounts:
            try:
                pubkey = account.get("pubkey", "")
                account_info = account.get("account", {})
                parsed_info = account_info.get("data", {}).get("parsed", {}).get("info", {})
                program_id = account.get("_program_id", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
                
                token_amount = parsed_info.get("tokenAmount", {})
                balance = float(token_amount.get("uiAmount") or 0)
                mint = parsed_info.get("mint", "")
                
                # Only include empty accounts
                if balance == 0:
                    vacant_accounts.append(VacantAccount(
                        address=pubkey,
                        mint=mint,
                        symbol=None,  # Would need additional lookup
                        balance=balance,
                        rent_recoverable=RENT_PER_ACCOUNT_SOL,
                        program_id=program_id
                    ))
            except Exception as e:
                logger.warning(f"Error parsing account: {e}")
                continue
        
        total_reclaimable = len(vacant_accounts) * RENT_PER_ACCOUNT_SOL
        
        return ScanResult(
            wallet_address=wallet_address,
            vacant_accounts=vacant_accounts,
            total_accounts_scanned=len(token_accounts),
            total_reclaimable_sol=round(total_reclaimable, 6),
            scan_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scan wallet: {str(e)}")


@router.post("/close-instruction")
async def get_close_instruction(request: CloseAccountsRequest):
    """
    Generate transaction instructions for closing token accounts.
    
    The frontend will use these to build and sign the transaction.
    Returns the accounts and instruction data needed to close them.
    """
    if not request.account_addresses:
        raise HTTPException(status_code=400, detail="No accounts to close")
    
    if len(request.account_addresses) > 20:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 20 accounts per transaction to avoid size limits"
        )
    
    try:
        # Return the accounts that need to be closed
        # The frontend will build the actual transaction using @solana/spl-token
        estimated_sol = len(request.account_addresses) * RENT_PER_ACCOUNT_SOL
        
        return {
            "success": True,
            "wallet_address": request.wallet_address,
            "accounts_to_close": request.account_addresses,
            "estimated_reclaim_sol": round(estimated_sol, 6),
            "instruction_type": "closeAccount",
            "program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "message": f"Ready to close {len(request.account_addresses)} accounts and reclaim ~{estimated_sol:.4f} SOL"
        }
        
    except Exception as e:
        logger.error(f"Close instruction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{wallet_address}")
async def get_cleanup_stats(wallet_address: str):
    """Get cleanup statistics for a wallet"""
    try:
        scan_result = await scan_vacant_accounts(wallet_address)
        
        return {
            "wallet_address": wallet_address,
            "empty_accounts": len(scan_result.vacant_accounts),
            "total_accounts": scan_result.total_accounts_scanned,
            "reclaimable_sol": scan_result.total_reclaimable_sol,
            "rent_per_account": RENT_PER_ACCOUNT_SOL,
            "scan_timestamp": scan_result.scan_timestamp
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



class RpcRequest(BaseModel):
    method: str
    params: List[Any] = []


@router.post("/rpc")
async def proxy_rpc_call(request: RpcRequest):
    """
    Proxy RPC calls to Solana to avoid CORS issues.
    Used for getLatestBlockhash, sendTransaction, getSignatureStatuses
    """
    rpc_url = SOLANA_RPC_URLS[0] if SOLANA_RPC_URLS else "https://api.mainnet-beta.solana.com"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": request.method,
                    "params": request.params
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    raise HTTPException(status_code=400, detail=data["error"].get("message", "RPC Error"))
                return data.get("result")
            else:
                raise HTTPException(status_code=response.status_code, detail="RPC request failed")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RPC proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
