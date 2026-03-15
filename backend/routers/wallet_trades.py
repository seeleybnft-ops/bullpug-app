"""Wallet Trades Router - Fetch and parse DEX trades from connected wallets.

This module provides endpoints for:
- Fetching transaction history from EVM chains (Ethereum, Base, Arbitrum)
- Fetching transaction history from Solana
- Parsing DEX swap transactions
- Creating draft journal entries from detected trades
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import httpx
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallet-trades", tags=["wallet-trades"])

# Alchemy API configuration
ALCHEMY_API_KEY = os.environ.get("ALCHEMY_API_KEY", "")

# Chain configurations
CHAIN_CONFIG = {
    "ethereum": {
        "name": "Ethereum",
        "alchemy_url": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "chain_id": 1,
        "explorer": "https://etherscan.io"
    },
    "base": {
        "name": "Base",
        "alchemy_url": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "chain_id": 8453,
        "explorer": "https://basescan.org"
    },
    "arbitrum": {
        "name": "Arbitrum",
        "alchemy_url": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "chain_id": 42161,
        "explorer": "https://arbiscan.io"
    }
}

# Known DEX router addresses for swap identification
DEX_ROUTERS = {
    # Uniswap
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3",
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3 Router 2",
    # SushiSwap
    "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "SushiSwap",
    # 1inch
    "0x1111111254eeb25477b68fb85ed929f73a960582": "1inch V5",
    "0x111111125421ca6dc452d289314280a0f8842a65": "1inch V6",
    # Base specific
    "0x2626664c2603336e57b271c5c0b26f421741e481": "Uniswap V3 (Base)",
    # Aerodrome (Base)
    "0xcf77a3ba9a5ca399b7c97c74d54e5b1beb874e43": "Aerodrome",
}

# Common swap method signatures
SWAP_METHOD_SIGS = [
    "0x38ed1739",  # swapExactTokensForTokens
    "0x7ff36ab5",  # swapExactETHForTokens
    "0x18cbafe5",  # swapExactTokensForETH
    "0x5c11d795",  # swapExactTokensForTokensSupportingFeeOnTransferTokens
    "0xfb3bdb41",  # swapETHForExactTokens
    "0x4a25d94a",  # swapTokensForExactETH
    "0xb6f9de95",  # swapExactETHForTokensSupportingFeeOnTransferTokens
    "0x791ac947",  # swapExactTokensForETHSupportingFeeOnTransferTokens
    "0xc04b8d59",  # exactInput (V3)
    "0xdb3e2198",  # exactInputSingle (V3)
    "0xf28c0498",  # exactOutput (V3)
    "0x414bf389",  # exactInputSingle (V3)
    "0x5ae401dc",  # multicall (V3)
    "0xac9650d8",  # multicall (V3 alternative)
    "0x04e45aaf",  # exactInputSingle (V3 Router 2)
    "0xb858183f",  # exactInput (V3 Router 2)
    "0x09b81346",  # exactOutputSingle (V3 Router 2)
    "0x12210e8a",  # refundETH
]


class DetectedTrade(BaseModel):
    """Model for a detected trade from wallet history."""
    chain: str
    tx_hash: str
    timestamp: datetime
    dex_protocol: str
    token_in_symbol: Optional[str] = None
    token_in_address: str
    token_in_amount: float
    token_out_symbol: Optional[str] = None
    token_out_address: str
    token_out_amount: float
    gas_used: Optional[int] = None
    gas_price_gwei: Optional[float] = None
    tx_fee_usd: Optional[float] = None
    explorer_url: str
    status: str = "detected"


class WalletTradesResponse(BaseModel):
    """Response model for wallet trades fetch."""
    address: str
    chain: str
    trades: List[DetectedTrade]
    total_found: int
    has_more: bool


async def get_token_metadata(token_address: str, chain: str) -> Dict[str, Any]:
    """Fetch token metadata from Alchemy."""
    if not ALCHEMY_API_KEY:
        return {"symbol": token_address[:8], "decimals": 18}
    
    config = CHAIN_CONFIG.get(chain)
    if not config:
        return {"symbol": token_address[:8], "decimals": 18}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                config["alchemy_url"],
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "alchemy_getTokenMetadata",
                    "params": [token_address]
                }
            )
            data = response.json()
            if "result" in data and data["result"]:
                return {
                    "symbol": data["result"].get("symbol", token_address[:8]),
                    "decimals": data["result"].get("decimals", 18),
                    "name": data["result"].get("name", "Unknown")
                }
    except Exception as e:
        logger.warning(f"Failed to get token metadata for {token_address}: {e}")
    
    return {"symbol": token_address[:8], "decimals": 18}


async def fetch_evm_transactions(address: str, chain: str, limit: int = 50) -> List[Dict]:
    """Fetch transactions for an EVM address using Alchemy."""
    if not ALCHEMY_API_KEY:
        logger.warning("ALCHEMY_API_KEY not configured")
        return []
    
    config = CHAIN_CONFIG.get(chain)
    if not config:
        raise ValueError(f"Unsupported chain: {chain}")
    
    transactions = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch asset transfers to this address
            response = await client.post(
                config["alchemy_url"],
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "alchemy_getAssetTransfers",
                    "params": [{
                        "fromAddress": address,
                        "category": ["external", "erc20"],
                        "maxCount": hex(limit),
                        "order": "desc",
                        "withMetadata": True
                    }]
                }
            )
            
            data = response.json()
            
            # Check if we have an error (network not enabled)
            if "error" in data:
                error_msg = data.get("error", {})
                logger.warning(f"Alchemy API error for {chain}: {error_msg}")
                return []  # Return empty list instead of failing
            
            if "result" in data and "transfers" in data["result"]:
                transactions.extend(data["result"]["transfers"])
            
            # Also fetch transfers TO this address
            response = await client.post(
                config["alchemy_url"],
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "alchemy_getAssetTransfers",
                    "params": [{
                        "toAddress": address,
                        "category": ["external", "erc20"],
                        "maxCount": hex(limit),
                        "order": "desc",
                        "withMetadata": True
                    }]
                }
            )
            
            data = response.json()
            if "result" in data and "transfers" in data["result"]:
                transactions.extend(data["result"]["transfers"])
    
    except Exception as e:
        logger.error(f"Error fetching EVM transactions for {address} on {chain}: {e}")
        # Return empty list instead of raising exception
        return []
    
    return transactions


def identify_swap_transactions(transactions: List[Dict], chain: str) -> List[Dict]:
    """Identify swap transactions from a list of transfers."""
    # Group transfers by transaction hash
    tx_groups = {}
    for tx in transactions:
        tx_hash = tx.get("hash", tx.get("uniqueId", ""))
        if tx_hash not in tx_groups:
            tx_groups[tx_hash] = []
        tx_groups[tx_hash].append(tx)
    
    swaps = []
    
    for tx_hash, transfers in tx_groups.items():
        # A swap typically has at least 2 transfers in the same tx (token in, token out)
        if len(transfers) < 2:
            continue
        
        # Check if this looks like a swap (has both incoming and outgoing tokens)
        from_addr = transfers[0].get("from", "").lower()
        # to_addr not used currently, keeping from_addr for potential future use
        _ = transfers[0].get("to", "").lower()
        
        # Look for DEX router involvement
        is_dex_swap = False
        dex_name = "Unknown DEX"
        
        for tx in transfers:
            tx_to = tx.get("to", "").lower()
            tx_from = tx.get("from", "").lower()
            
            for router, name in DEX_ROUTERS.items():
                if router.lower() in [tx_to, tx_from]:
                    is_dex_swap = True
                    dex_name = name
                    break
        
        if is_dex_swap or len(transfers) >= 2:
            # Group transfers by direction
            outgoing = [t for t in transfers if t.get("from", "").lower() == from_addr]
            incoming = [t for t in transfers if t.get("to", "").lower() == from_addr]
            
            if outgoing and incoming:
                swap_data = {
                    "tx_hash": tx_hash,
                    "transfers": transfers,
                    "outgoing": outgoing,
                    "incoming": incoming,
                    "dex_name": dex_name,
                    "metadata": transfers[0].get("metadata", {})
                }
                swaps.append(swap_data)
    
    return swaps


async def parse_swap_to_trade(swap: Dict, chain: str, config: Dict) -> Optional[DetectedTrade]:
    """Parse a swap transaction into a DetectedTrade object."""
    try:
        tx_hash = swap["tx_hash"]
        outgoing = swap["outgoing"]
        incoming = swap["incoming"]
        metadata = swap.get("metadata", {})
        
        if not outgoing or not incoming:
            return None
        
        # Get the main token transfers
        token_out = outgoing[0]  # What user sent
        token_in = incoming[0]   # What user received
        
        # Parse timestamp
        block_timestamp = metadata.get("blockTimestamp")
        if block_timestamp:
            timestamp = datetime.fromisoformat(block_timestamp.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)
        
        # Get token symbols
        out_asset = token_out.get("asset", "")
        in_asset = token_in.get("asset", "")
        
        out_address = token_out.get("rawContract", {}).get("address", "")
        in_address = token_in.get("rawContract", {}).get("address", "")
        
        # Parse amounts
        out_value = float(token_out.get("value", 0) or 0)
        in_value = float(token_in.get("value", 0) or 0)
        
        explorer_url = f"{config['explorer']}/tx/{tx_hash}"
        
        return DetectedTrade(
            chain=chain,
            tx_hash=tx_hash,
            timestamp=timestamp,
            dex_protocol=swap.get("dex_name", "DEX"),
            token_in_symbol=in_asset or None,
            token_in_address=in_address or "native",
            token_in_amount=in_value,
            token_out_symbol=out_asset or None,
            token_out_address=out_address or "native",
            token_out_amount=out_value,
            explorer_url=explorer_url
        )
    
    except Exception as e:
        logger.error(f"Error parsing swap: {e}")
        return None


@router.get("/evm/{address}")
async def get_evm_wallet_trades(
    address: str,
    chain: str = Query("ethereum", description="Chain to fetch from"),
    limit: int = Query(50, ge=1, le=200)
) -> WalletTradesResponse:
    """
    Fetch and parse DEX trades from an EVM wallet.
    
    Supported chains: ethereum, base, arbitrum
    """
    if chain not in CHAIN_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unsupported chain: {chain}. Supported: {list(CHAIN_CONFIG.keys())}")
    
    config = CHAIN_CONFIG[chain]
    
    # Fetch transactions
    transactions = await fetch_evm_transactions(address, chain, limit)
    
    # Identify swaps
    swaps = identify_swap_transactions(transactions, chain)
    
    # Parse swaps to trades
    trades = []
    for swap in swaps:
        trade = await parse_swap_to_trade(swap, chain, config)
        if trade:
            trades.append(trade)
    
    # Remove duplicates and sort by timestamp
    seen_hashes = set()
    unique_trades = []
    for trade in trades:
        if trade.tx_hash not in seen_hashes:
            seen_hashes.add(trade.tx_hash)
            unique_trades.append(trade)
    
    unique_trades.sort(key=lambda t: t.timestamp, reverse=True)
    
    return WalletTradesResponse(
        address=address,
        chain=chain,
        trades=unique_trades[:limit],
        total_found=len(unique_trades),
        has_more=len(unique_trades) > limit
    )


@router.get("/solana/{address}")
async def get_solana_wallet_trades(
    address: str,
    limit: int = Query(50, ge=1, le=200)
) -> WalletTradesResponse:
    """
    Fetch and parse DEX trades from a Solana wallet.
    
    Uses the Solana RPC to fetch recent transactions and identifies Jupiter/Raydium swaps.
    """
    solana_rpc = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    
    trades = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch recent signatures
            response = await client.post(
                solana_rpc,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignaturesForAddress",
                    "params": [
                        address,
                        {"limit": limit, "commitment": "finalized"}
                    ]
                }
            )
            
            data = response.json()
            signatures = data.get("result", [])
            
            # For each signature, try to identify if it's a swap
            # Note: Full swap parsing for Solana requires more complex logic
            # This is a simplified version that detects potential swaps
            
            for sig_data in signatures[:min(limit, 20)]:  # Limit detailed fetching
                signature = sig_data.get("signature")
                block_time = sig_data.get("blockTime")
                
                if not signature:
                    continue
                
                # Fetch transaction details
                tx_response = await client.post(
                    solana_rpc,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [
                            signature,
                            {"encoding": "jsonParsed", "commitment": "finalized"}
                        ]
                    }
                )
                
                tx_data = tx_response.json().get("result")
                if not tx_data:
                    continue
                
                # Check if this involves Jupiter or Raydium
                log_messages = tx_data.get("meta", {}).get("logMessages", [])
                is_swap = any(
                    "Program JUP" in log or 
                    "Program 675kPX" in log or  # Raydium
                    "Swap" in log
                    for log in log_messages
                )
                
                if is_swap:
                    # Parse token balance changes
                    pre_balances = tx_data.get("meta", {}).get("preTokenBalances", [])
                    post_balances = tx_data.get("meta", {}).get("postTokenBalances", [])
                    
                    timestamp = datetime.fromtimestamp(block_time, tz=timezone.utc) if block_time else datetime.now(timezone.utc)
                    
                    # Determine which tokens were swapped
                    token_changes = []
                    for post in post_balances:
                        owner = post.get("owner")
                        if owner == address:
                            mint = post.get("mint")
                            post_amount = float(post.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
                            
                            # Find pre-balance
                            pre_amount = 0
                            for pre in pre_balances:
                                if pre.get("mint") == mint and pre.get("owner") == owner:
                                    pre_amount = float(pre.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
                                    break
                            
                            change = post_amount - pre_amount
                            if abs(change) > 0.0001:
                                token_changes.append({
                                    "mint": mint,
                                    "change": change,
                                    "symbol": post.get("uiTokenAmount", {}).get("uiAmount")
                                })
                    
                    # If we have at least one positive and one negative change, it's a swap
                    positive_changes = [t for t in token_changes if t["change"] > 0]
                    negative_changes = [t for t in token_changes if t["change"] < 0]
                    
                    if positive_changes and negative_changes:
                        token_in = positive_changes[0]
                        token_out = negative_changes[0]
                        
                        trades.append(DetectedTrade(
                            chain="solana",
                            tx_hash=signature,
                            timestamp=timestamp,
                            dex_protocol="Jupiter/Raydium",
                            token_in_address=token_in["mint"],
                            token_in_amount=abs(token_in["change"]),
                            token_out_address=token_out["mint"],
                            token_out_amount=abs(token_out["change"]),
                            explorer_url=f"https://solscan.io/tx/{signature}"
                        ))
    
    except Exception as e:
        logger.error(f"Error fetching Solana trades: {e}")
        # Return empty list on error rather than failing
    
    return WalletTradesResponse(
        address=address,
        chain="solana",
        trades=trades,
        total_found=len(trades),
        has_more=False
    )


@router.get("/supported-chains")
async def get_supported_chains():
    """Get list of supported chains for trade fetching."""
    return {
        "evm_chains": [
            {"id": "ethereum", "name": "Ethereum", "chain_id": 1},
            {"id": "base", "name": "Base", "chain_id": 8453},
            {"id": "arbitrum", "name": "Arbitrum", "chain_id": 42161}
        ],
        "other_chains": [
            {"id": "solana", "name": "Solana"}
        ],
        "alchemy_configured": bool(ALCHEMY_API_KEY)
    }


@router.post("/import-to-journal")
async def import_trades_to_journal(
    trades: List[DetectedTrade],
    wallet_address: str = Query(..., description="User's primary wallet address")
):
    """
    Import detected trades as draft journal entries.
    
    This creates journal entries with status='draft' that the user can review and save.
    """
    from utils.database import db
    
    imported_count = 0
    duplicates = 0
    
    for trade in trades:
        # Check for duplicate
        existing = await db.journal_trades.find_one({
            "tx_hash": trade.tx_hash,
            "chain": trade.chain
        })
        
        if existing:
            duplicates += 1
            continue
        
        # Create journal entry
        journal_entry = {
            "trade_id": f"{trade.chain}_{trade.tx_hash[:16]}",
            "wallet_address": wallet_address,
            "asset": f"{trade.token_in_symbol or trade.token_in_address[:8]}/{trade.token_out_symbol or trade.token_out_address[:8]}",
            "trade_type": "Spot",
            "entry_price": trade.token_out_amount / trade.token_in_amount if trade.token_in_amount > 0 else 0,
            "position_size": trade.token_out_amount,
            "date_entry": trade.timestamp.isoformat(),
            "status": "draft",
            "source": "auto_import",
            "chain": trade.chain,
            "tx_hash": trade.tx_hash,
            "dex_protocol": trade.dex_protocol,
            "token_in_address": trade.token_in_address,
            "token_in_amount": trade.token_in_amount,
            "token_out_address": trade.token_out_address,
            "token_out_amount": trade.token_out_amount,
            "explorer_url": trade.explorer_url,
            "imported_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.journal_trades.insert_one(journal_entry)
        imported_count += 1
    
    return {
        "success": True,
        "imported_count": imported_count,
        "duplicates_skipped": duplicates,
        "message": f"Imported {imported_count} trades to your journal"
    }
