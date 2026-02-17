"""Reflections calculator routes for token fee distribution."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/reflections", tags=["reflections"])


class ReflectionsCalcRequest(BaseModel):
    token_holdings: float
    volume_24h: float = 89000
    reflection_rate: float = 2.0


@router.post("/calculate")
async def calculate_reflections(data: ReflectionsCalcRequest):
    """Calculate reflections based on Blowfish fee structure."""
    # Tokenomics constants
    total_supply = 1_000_000_000
    circulating_supply = 800_000_000
    
    # Calculate holder's share of circulating supply
    holder_share = data.token_holdings / circulating_supply
    
    # Reflections are distributed from all transactions
    daily_volume = data.volume_24h
    daily_reflections_pool = daily_volume * (data.reflection_rate / 100)
    
    # Holder's daily reflections based on their share
    daily_reflections_usd = daily_reflections_pool * holder_share
    weekly_reflections_usd = daily_reflections_usd * 7
    monthly_reflections_usd = daily_reflections_usd * 30
    yearly_reflections_usd = daily_reflections_usd * 365
    
    # Calculate in tokens (assuming current price)
    price_usd = 0.00042
    daily_reflections_tokens = daily_reflections_usd / price_usd if price_usd > 0 else 0
    weekly_reflections_tokens = weekly_reflections_usd / price_usd if price_usd > 0 else 0
    monthly_reflections_tokens = monthly_reflections_usd / price_usd if price_usd > 0 else 0
    yearly_reflections_tokens = yearly_reflections_usd / price_usd if price_usd > 0 else 0
    
    # APY calculation
    initial_value = data.token_holdings * price_usd
    apy = (yearly_reflections_usd / initial_value * 100) if initial_value > 0 else 0
    
    return {
        "holdings": data.token_holdings,
        "holder_share_percent": round(holder_share * 100, 6),
        "volume_24h": data.volume_24h,
        "reflection_rate": data.reflection_rate,
        "daily": {"usd": round(daily_reflections_usd, 4), "tokens": round(daily_reflections_tokens, 2)},
        "weekly": {"usd": round(weekly_reflections_usd, 4), "tokens": round(weekly_reflections_tokens, 2)},
        "monthly": {"usd": round(monthly_reflections_usd, 4), "tokens": round(monthly_reflections_tokens, 2)},
        "yearly": {"usd": round(yearly_reflections_usd, 2), "tokens": round(yearly_reflections_tokens, 2)},
        "estimated_apy": round(apy, 2),
        "price_usd": price_usd
    }
