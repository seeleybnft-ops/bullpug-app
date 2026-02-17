"""Reflections calculator routes for token fee distribution."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/reflections", tags=["reflections"])

# Token constants (can be moved to config if needed)
TOTAL_SUPPLY = 100_000_000_000  # 100B tokens
TOKEN_PRICE_USD = 0.000001  # Default placeholder price


class ReflectionsCalculateRequest(BaseModel):
    token_holdings: float
    volume_24h: float = 100000
    reflection_rate: float = 0.8  # Blowfish: 1% fee × 80% to holders = 0.8%
    token_price: Optional[float] = None


@router.post("/calculate")
async def calculate_reflections(data: ReflectionsCalculateRequest):
    """Calculate reflections based on Blowfish fee structure."""
    if data.token_holdings <= 0:
        return {
            "holdings": 0,
            "holder_share_percent": 0,
            "daily": {"tokens": 0, "usd": 0},
            "weekly": {"tokens": 0, "usd": 0},
            "monthly": {"tokens": 0, "usd": 0},
            "yearly": {"tokens": 0, "usd": 0},
            "estimated_apy": 0,
            "volume_24h": data.volume_24h,
            "reflection_rate": data.reflection_rate,
            "price_usd": data.token_price or TOKEN_PRICE_USD
        }
    
    price = data.token_price or TOKEN_PRICE_USD
    holder_share = data.token_holdings / TOTAL_SUPPLY
    
    # Daily reflection pool based on volume and reflection rate
    daily_pool_usd = data.volume_24h * (data.reflection_rate / 100)
    daily_reflections_usd = daily_pool_usd * holder_share
    daily_reflections_tokens = daily_reflections_usd / price if price > 0 else 0
    
    # Time projections
    weekly_usd = daily_reflections_usd * 7
    monthly_usd = daily_reflections_usd * 30
    yearly_usd = daily_reflections_usd * 365
    
    weekly_tokens = daily_reflections_tokens * 7
    monthly_tokens = daily_reflections_tokens * 30
    yearly_tokens = daily_reflections_tokens * 365
    
    # APY calculation
    holdings_value = data.token_holdings * price
    estimated_apy = (yearly_usd / holdings_value * 100) if holdings_value > 0 else 0
    
    return {
        "holdings": data.token_holdings,
        "holder_share_percent": round(holder_share * 100, 6),
        "daily": {
            "tokens": round(daily_reflections_tokens, 2),
            "usd": round(daily_reflections_usd, 4)
        },
        "weekly": {
            "tokens": round(weekly_tokens, 2),
            "usd": round(weekly_usd, 4)
        },
        "monthly": {
            "tokens": round(monthly_tokens, 2),
            "usd": round(monthly_usd, 4)
        },
        "yearly": {
            "tokens": round(yearly_tokens, 2),
            "usd": round(yearly_usd, 4)
        },
        "estimated_apy": round(estimated_apy, 2),
        "volume_24h": data.volume_24h,
        "reflection_rate": data.reflection_rate,
        "price_usd": price
    }
