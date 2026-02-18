"""Badge routes for Bullpug achievements."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict
import logging

from utils.badges import (
    get_user_badges,
    check_and_award_achievements,
    get_all_badges,
    get_badge_info,
    BADGES
)

router = APIRouter(prefix="/badges", tags=["badges"])
logger = logging.getLogger(__name__)


@router.get("/all")
async def list_all_badges():
    """Get list of all available badges."""
    badges = []
    for badge_id, badge in BADGES.items():
        badges.append({
            "id": badge_id,
            "name": badge["name"],
            "description": badge["description"],
            "emoji": badge["emoji"],
            "color": badge["color"],
            "tier": badge["tier"]
        })
    
    # Sort by tier
    tier_order = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}
    badges.sort(key=lambda b: tier_order.get(b["tier"], 99))
    
    return {"badges": badges}


@router.get("/user/{wallet_address}")
async def get_badges_for_user(wallet_address: str):
    """Get all badges a user has earned."""
    badges = await get_user_badges(wallet_address)
    return {
        "wallet_address": wallet_address,
        "badges": badges,
        "count": len(badges)
    }


@router.post("/check/{wallet_address}")
async def check_user_achievements(wallet_address: str):
    """Check and award any achievements the user qualifies for."""
    awarded = await check_and_award_achievements(wallet_address)
    
    if awarded:
        logger.info(f"Awarded badges to {wallet_address[:8]}: {awarded}")
    
    return {
        "wallet_address": wallet_address,
        "newly_awarded": awarded,
        "count": len(awarded)
    }


@router.get("/info/{badge_id}")
async def get_badge_details(badge_id: str):
    """Get details about a specific badge."""
    badge = get_badge_info(badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    
    return badge
