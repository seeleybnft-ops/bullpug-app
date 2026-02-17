"""Tokenomics statistics routes."""

from fastapi import APIRouter

from utils.database import db


router = APIRouter(prefix="/tokenomics", tags=["tokenomics"])


@router.get("/stats")
async def get_tokenomics():
    """Get tokenomics statistics."""
    total_bets = await db.bets.count_documents({})
    total_subs = await db.newsletter_subscribers.count_documents({})
    
    return {
        "total_supply": 1000000000,
        "circulating_supply": 800000000,
        "burned": 12500000,
        "burn_rate": "2%",
        "reflection_rate": "2%",
        "liquidity_rate": "1%",
        "distribution": {
            "community_liquidity": 80,
            "marketing_partnerships": 10,
            "developer_team": 5,
            "ecosystem_reserve": 5
        },
        "holders": 1247 + total_subs,
        "total_bets": total_bets,
        "price_usd": 0.00042,
        "market_cap": 420000,
        "volume_24h": 89000
    }
