"""Portfolio Router - Unified portfolio view across Solana and EVM chains.

Provides endpoints to fetch token balances and portfolio values across
multiple blockchain networks.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import httpx
import os
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

ALCHEMY_API_KEY = os.environ.get("ALCHEMY_API_KEY", "")

# Chain configurations
CHAIN_CONFIG = {
    "ethereum": {
        "name": "Ethereum",
        "symbol": "ETH",
        "alchemy_url": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "chain_id": 1,
        "native_decimals": 18,
        "icon": "⟠",
        "color": "#627EEA"
    },
    "base": {
        "name": "Base",
        "symbol": "ETH",
        "alchemy_url": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "chain_id": 8453,
        "native_decimals": 18,
        "icon": "🔵",
        "color": "#0052FF"
    },
    "arbitrum": {
        "name": "Arbitrum",
        "symbol": "ETH",
        "alchemy_url": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
        "chain_id": 42161,
        "native_decimals": 18,
        "icon": "🔷",
        "color": "#28A0F0"
    }
}

# Stablecoin addresses to identify (for better categorization)
STABLECOINS = {
    # Ethereum
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
    "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
    "0x6b175474e89094c44da98b954eedeac495271d0f": "DAI",
    # Base
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC",
    # Arbitrum
    "0xaf88d065e77c8cc2239327c5edb3a432268e5831": "USDC",
    "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9": "USDT",
}


class TokenBalance(BaseModel):
    """Model for a token balance."""
    chain: str
    chain_name: str
    chain_icon: str
    contract_address: Optional[str] = None
    symbol: str
    name: str
    balance: float
    decimals: int
    is_native: bool = False
    is_stablecoin: bool = False
    logo_url: Optional[str] = None
    price_usd: Optional[float] = None
    value_usd: Optional[float] = None
    change_24h: Optional[float] = None


class ChainPortfolio(BaseModel):
    """Portfolio for a single chain."""
    chain: str
    chain_name: str
    chain_icon: str
    chain_color: str
    address: str
    native_balance: float
    native_symbol: str
    native_value_usd: Optional[float] = None
    tokens: List[TokenBalance]
    total_value_usd: float
    token_count: int


class PortfolioResponse(BaseModel):
    """Complete portfolio response."""
    total_value_usd: float
    total_tokens: int
    chains: List[ChainPortfolio]
    solana: Optional[ChainPortfolio] = None
    last_updated: str


async def get_eth_price() -> float:
    """Fetch current ETH price from CoinGecko."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "ethereum", "vs_currencies": "usd", "include_24hr_change": "true"}
            )
            data = response.json()
            return data.get("ethereum", {}).get("usd", 0)
    except Exception as e:
        logger.warning(f"Failed to fetch ETH price: {e}")
        return 0


async def get_sol_price() -> float:
    """Fetch current SOL price from CoinGecko."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "solana", "vs_currencies": "usd", "include_24hr_change": "true"}
            )
            data = response.json()
            return data.get("solana", {}).get("usd", 0)
    except Exception as e:
        logger.warning(f"Failed to fetch SOL price: {e}")
        return 0


async def get_token_prices(contract_addresses: List[str], chain: str) -> Dict[str, Dict]:
    """Fetch token prices from CoinGecko."""
    if not contract_addresses:
        return {}
    
    platform_map = {
        "ethereum": "ethereum",
        "base": "base",
        "arbitrum": "arbitrum-one"
    }
    platform = platform_map.get(chain, "ethereum")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            addresses = ",".join(contract_addresses[:50])  # Limit to 50
            response = await client.get(
                f"https://api.coingecko.com/api/v3/simple/token_price/{platform}",
                params={
                    "contract_addresses": addresses,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true"
                }
            )
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch token prices: {e}")
        return {}


async def fetch_evm_portfolio(address: str, chain: str) -> ChainPortfolio:
    """Fetch portfolio for an EVM address on a specific chain."""
    config = CHAIN_CONFIG.get(chain)
    if not config:
        raise ValueError(f"Unsupported chain: {chain}")
    
    tokens = []
    native_balance = 0.0
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch native balance
            native_response = await client.post(
                config["alchemy_url"],
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_getBalance",
                    "params": [address, "latest"]
                }
            )
            native_data = native_response.json()
            if "result" in native_data:
                native_balance = int(native_data["result"], 16) / (10 ** config["native_decimals"])
            
            # Fetch token balances
            token_response = await client.post(
                config["alchemy_url"],
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "alchemy_getTokenBalances",
                    "params": [address]
                }
            )
            token_data = token_response.json()
            
            if "result" in token_data and "tokenBalances" in token_data["result"]:
                # Filter non-zero balances
                non_zero = [
                    t for t in token_data["result"]["tokenBalances"]
                    if t.get("tokenBalance") and int(t["tokenBalance"], 16) > 0
                ]
                
                # Get metadata for each token
                for token in non_zero[:20]:  # Limit to 20 tokens
                    contract = token["contractAddress"]
                    raw_balance = int(token["tokenBalance"], 16)
                    
                    # Get token metadata
                    metadata_response = await client.post(
                        config["alchemy_url"],
                        json={
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "alchemy_getTokenMetadata",
                            "params": [contract]
                        }
                    )
                    metadata = metadata_response.json().get("result", {})
                    
                    decimals = metadata.get("decimals", 18)
                    balance = raw_balance / (10 ** decimals)
                    
                    if balance > 0.0001:  # Filter dust
                        is_stable = contract.lower() in STABLECOINS
                        tokens.append(TokenBalance(
                            chain=chain,
                            chain_name=config["name"],
                            chain_icon=config["icon"],
                            contract_address=contract,
                            symbol=metadata.get("symbol", "???"),
                            name=metadata.get("name", "Unknown Token"),
                            balance=balance,
                            decimals=decimals,
                            is_stablecoin=is_stable,
                            logo_url=metadata.get("logo"),
                            price_usd=1.0 if is_stable else None,
                            value_usd=balance if is_stable else None
                        ))
    
    except Exception as e:
        logger.error(f"Error fetching EVM portfolio for {address} on {chain}: {e}")
    
    # Get ETH price
    eth_price = await get_eth_price()
    native_value_usd = native_balance * eth_price if eth_price else None
    
    # Get token prices
    token_addresses = [t.contract_address for t in tokens if t.contract_address and not t.is_stablecoin]
    if token_addresses:
        prices = await get_token_prices(token_addresses, chain)
        for token in tokens:
            if token.contract_address and not token.is_stablecoin:
                price_data = prices.get(token.contract_address.lower(), {})
                token.price_usd = price_data.get("usd")
                token.change_24h = price_data.get("usd_24h_change")
                if token.price_usd:
                    token.value_usd = token.balance * token.price_usd
    
    # Calculate total value
    total_value = native_value_usd or 0
    for token in tokens:
        if token.value_usd:
            total_value += token.value_usd
    
    return ChainPortfolio(
        chain=chain,
        chain_name=config["name"],
        chain_icon=config["icon"],
        chain_color=config["color"],
        address=address,
        native_balance=native_balance,
        native_symbol=config["symbol"],
        native_value_usd=native_value_usd,
        tokens=tokens,
        total_value_usd=total_value,
        token_count=len(tokens)
    )


async def fetch_solana_portfolio(address: str) -> ChainPortfolio:
    """Fetch portfolio for a Solana address."""
    solana_rpc = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    
    tokens = []
    native_balance = 0.0
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch SOL balance
            balance_response = await client.post(
                solana_rpc,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [address, {"commitment": "finalized"}]
                }
            )
            balance_data = balance_response.json()
            if "result" in balance_data and "value" in balance_data["result"]:
                native_balance = balance_data["result"]["value"] / 1_000_000_000  # lamports to SOL
            
            # Fetch SPL token accounts
            token_response = await client.post(
                solana_rpc,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        address,
                        {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                        {"encoding": "jsonParsed"}
                    ]
                }
            )
            token_data = token_response.json()
            
            if "result" in token_data and "value" in token_data["result"]:
                for account in token_data["result"]["value"][:20]:
                    parsed = account.get("account", {}).get("data", {}).get("parsed", {})
                    info = parsed.get("info", {})
                    token_amount = info.get("tokenAmount", {})
                    
                    balance = float(token_amount.get("uiAmount", 0) or 0)
                    if balance > 0.0001:
                        tokens.append(TokenBalance(
                            chain="solana",
                            chain_name="Solana",
                            chain_icon="◎",
                            contract_address=info.get("mint"),
                            symbol=info.get("mint", "???")[:8],
                            name="SPL Token",
                            balance=balance,
                            decimals=token_amount.get("decimals", 9),
                            is_native=False
                        ))
    
    except Exception as e:
        logger.error(f"Error fetching Solana portfolio for {address}: {e}")
    
    # Get SOL price
    sol_price = await get_sol_price()
    native_value_usd = native_balance * sol_price if sol_price else None
    
    return ChainPortfolio(
        chain="solana",
        chain_name="Solana",
        chain_icon="◎",
        chain_color="#9945FF",
        address=address,
        native_balance=native_balance,
        native_symbol="SOL",
        native_value_usd=native_value_usd,
        tokens=tokens,
        total_value_usd=native_value_usd or 0,
        token_count=len(tokens)
    )


@router.get("/evm/{address}")
async def get_evm_portfolio(
    address: str,
    chains: str = Query("ethereum,base,arbitrum", description="Comma-separated chains")
) -> Dict[str, Any]:
    """
    Get portfolio across multiple EVM chains.
    
    Returns token balances and values for the specified chains.
    """
    chain_list = [c.strip() for c in chains.split(",") if c.strip() in CHAIN_CONFIG]
    
    if not chain_list:
        raise HTTPException(status_code=400, detail="No valid chains specified")
    
    # Fetch all chains in parallel
    tasks = [fetch_evm_portfolio(address, chain) for chain in chain_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    chain_portfolios = []
    total_value = 0
    total_tokens = 0
    
    for result in results:
        if isinstance(result, ChainPortfolio):
            chain_portfolios.append(result)
            total_value += result.total_value_usd
            total_tokens += result.token_count + 1  # +1 for native token
    
    return PortfolioResponse(
        total_value_usd=total_value,
        total_tokens=total_tokens,
        chains=chain_portfolios,
        last_updated=datetime.now(timezone.utc).isoformat()
    ).model_dump()


@router.get("/solana/{address}")
async def get_solana_portfolio(address: str) -> Dict[str, Any]:
    """
    Get portfolio for a Solana address.
    
    Returns SOL balance and SPL token holdings.
    """
    portfolio = await fetch_solana_portfolio(address)
    
    return PortfolioResponse(
        total_value_usd=portfolio.total_value_usd,
        total_tokens=portfolio.token_count + 1,
        chains=[],
        solana=portfolio,
        last_updated=datetime.now(timezone.utc).isoformat()
    ).model_dump()


@router.get("/combined")
async def get_combined_portfolio(
    evm_address: Optional[str] = Query(None, description="EVM wallet address"),
    solana_address: Optional[str] = Query(None, description="Solana wallet address"),
    chains: str = Query("ethereum,base,arbitrum", description="EVM chains to include")
) -> PortfolioResponse:
    """
    Get combined portfolio across Solana and EVM chains.
    
    Provide one or both addresses to get a unified portfolio view.
    """
    if not evm_address and not solana_address:
        raise HTTPException(status_code=400, detail="At least one address required")
    
    tasks = []
    chain_list = []
    
    # Add EVM chains
    if evm_address:
        chain_list = [c.strip() for c in chains.split(",") if c.strip() in CHAIN_CONFIG]
        for chain in chain_list:
            tasks.append(fetch_evm_portfolio(evm_address, chain))
    
    # Add Solana
    if solana_address:
        tasks.append(fetch_solana_portfolio(solana_address))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    chain_portfolios = []
    solana_portfolio = None
    total_value = 0
    total_tokens = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Portfolio fetch error: {result}")
            continue
            
        if isinstance(result, ChainPortfolio):
            if result.chain == "solana":
                solana_portfolio = result
            else:
                chain_portfolios.append(result)
            
            total_value += result.total_value_usd
            total_tokens += result.token_count + 1
    
    return PortfolioResponse(
        total_value_usd=total_value,
        total_tokens=total_tokens,
        chains=chain_portfolios,
        solana=solana_portfolio,
        last_updated=datetime.now(timezone.utc).isoformat()
    )


@router.get("/prices")
async def get_current_prices():
    """Get current prices for major assets."""
    eth_price = await get_eth_price()
    sol_price = await get_sol_price()
    
    return {
        "ETH": {"usd": eth_price, "symbol": "ETH", "icon": "⟠"},
        "SOL": {"usd": sol_price, "symbol": "SOL", "icon": "◎"},
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
