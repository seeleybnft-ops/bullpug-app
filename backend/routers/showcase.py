"""Skin showcase routes for displaying user collections."""

from fastapi import APIRouter, HTTPException
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional, List

from utils.database import db

router = APIRouter(prefix="/showcase", tags=["showcase"])

# Skin catalog for reference
SKINS_CATALOG = {
    "default": {"name": "Guardian", "bonus_percent": 0, "rarity": "common"},
    "ethereal": {"name": "Ethereal", "bonus_percent": 10, "rarity": "mythic"},
    "diamond": {"name": "Diamond", "bonus_percent": 5, "rarity": "legendary"},
    "gold": {"name": "Gold", "bonus_percent": 5, "rarity": "legendary"},
    "silver": {"name": "Silver", "bonus_percent": 4, "rarity": "epic"},
    "heatmap": {"name": "Heatmap", "bonus_percent": 3, "rarity": "rare"},
    "radioactive": {"name": "Radioactive", "bonus_percent": 3, "rarity": "rare"},
    "zombie": {"name": "Zombie", "bonus_percent": 3, "rarity": "rare"},
    "water": {"name": "Water", "bonus_percent": 2, "rarity": "uncommon"},
    "fire": {"name": "Fire", "bonus_percent": 2, "rarity": "uncommon"},
    "robot": {"name": "Robot", "bonus_percent": 1, "rarity": "common"},
    "skeletal": {"name": "Skeletal", "bonus_percent": 1, "rarity": "common"},
}

PURCHASABLE_SKIN_IDS = ["diamond", "gold", "silver", "heatmap", "radioactive", "zombie", "water", "fire", "robot", "skeletal"]


class ShowcaseSettings(BaseModel):
    wallet_address: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    featured_skins: Optional[List[str]] = []
    show_stats: bool = True
    is_public: bool = True


@router.get("/leaderboard/collectors")
async def get_collector_leaderboard(limit: int = 20):
    """Get top skin collectors leaderboard."""
    # Aggregate skin purchases to find top collectors
    pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$wallet_address",
            "skin_count": {"$sum": 1},
            "skins": {"$addToSet": "$skin_id"}
        }},
        {"$sort": {"skin_count": -1}},
        {"$limit": limit}
    ]
    
    collectors = await db.skin_purchases.aggregate(pipeline).to_list(limit)
    
    leaderboard = []
    for i, collector in enumerate(collectors):
        wallet = collector["_id"]
        skins = collector["skins"]
        
        # Get showcase settings for display name
        settings = await db.showcases.find_one(
            {"wallet_address": wallet},
            {"_id": 0, "display_name": 1}
        )
        
        # Calculate rarity score
        rarity_score = 0
        rarity_points = {"mythic": 100, "legendary": 50, "epic": 30, "rare": 20, "uncommon": 10, "common": 5}
        for skin_id in skins:
            if skin_id in SKINS_CATALOG:
                rarity = SKINS_CATALOG[skin_id]["rarity"]
                rarity_score += rarity_points.get(rarity, 0)
        
        leaderboard.append({
            "rank": i + 1,
            "wallet_address": wallet,
            "display_name": settings.get("display_name", f"Collector_{wallet[:6]}") if settings else f"Collector_{wallet[:6]}",
            "skin_count": collector["skin_count"],
            "has_ethereal": "ethereal" in skins,
            "rarity_score": rarity_score,
            "completion_percent": round((len(skins) / len(SKINS_CATALOG)) * 100, 1)
        })
    
    return {"leaderboard": leaderboard}


@router.post("/settings")
async def update_showcase_settings(data: ShowcaseSettings):
    """Update showcase settings for a user."""
    settings = {
        "wallet_address": data.wallet_address,
        "display_name": (data.display_name or f"Collector_{data.wallet_address[:6]}")[:30],
        "bio": (data.bio or "")[:200],
        "featured_skins": data.featured_skins[:6] if data.featured_skins else [],
        "show_stats": data.show_stats,
        "is_public": data.is_public,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.showcases.update_one(
        {"wallet_address": data.wallet_address},
        {"$set": settings},
        upsert=True
    )
    
    return {"message": "Showcase settings updated", "settings": settings}


@router.get("/recent-acquisitions")
async def get_recent_acquisitions(limit: int = 10):
    """Get recent skin acquisitions across all users."""
    recent = await db.skin_purchases.find(
        {"status": "completed"},
        {"_id": 0, "wallet_address": 1, "skin_id": 1, "skin_name": 1, "purchased_at": 1, "gift_from": 1, "achievement": 1}
    ).sort("purchased_at", -1).to_list(limit)
    
    acquisitions = []
    for purchase in recent:
        wallet = purchase["wallet_address"]
        settings = await db.showcases.find_one(
            {"wallet_address": wallet},
            {"_id": 0, "display_name": 1}
        )
        
        acquisition_type = "purchase"
        if purchase.get("achievement"):
            acquisition_type = "achievement"
        elif purchase.get("gift_from"):
            acquisition_type = "gift"
        
        acquisitions.append({
            "wallet_address": wallet,
            "display_name": settings.get("display_name", f"Collector_{wallet[:6]}") if settings else f"Collector_{wallet[:6]}",
            "skin_id": purchase["skin_id"],
            "skin_name": purchase.get("skin_name", SKINS_CATALOG.get(purchase["skin_id"], {}).get("name", "Unknown")),
            "rarity": SKINS_CATALOG.get(purchase["skin_id"], {}).get("rarity", "common"),
            "acquired_at": purchase["purchased_at"],
            "acquisition_type": acquisition_type
        })
    
    return {"acquisitions": acquisitions}


@router.post("/share/{wallet_address}")
async def generate_share_link(wallet_address: str):
    """Generate a shareable link for a showcase."""
    # Check if showcase is public
    settings = await db.showcases.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0, "is_public": 1}
    )
    
    if settings and not settings.get("is_public", True):
        raise HTTPException(status_code=403, detail="This showcase is private")
    
    # Generate share token
    share_token = str(uuid.uuid4())[:8]
    
    await db.showcase_shares.insert_one({
        "id": str(uuid.uuid4()),
        "wallet_address": wallet_address,
        "share_token": share_token,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "views": 0
    })
    
    return {
        "share_token": share_token,
        "share_url": f"/showcase/{wallet_address}?ref={share_token}"
    }


@router.get("/{wallet_address}")
async def get_showcase(wallet_address: str):
    """Get a user's skin showcase/collection."""
    # Get showcase settings
    settings = await db.showcases.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    
    if not settings:
        settings = {
            "wallet_address": wallet_address,
            "display_name": f"Collector_{wallet_address[:6]}",
            "bio": "",
            "featured_skins": [],
            "show_stats": True,
            "is_public": True
        }
    
    # Get owned skins
    owned = await db.skin_purchases.find(
        {"wallet_address": wallet_address, "status": "completed"},
        {"_id": 0, "skin_id": 1, "purchased_at": 1, "gift_from": 1, "achievement": 1}
    ).to_list(100)
    
    owned_skin_ids = [p["skin_id"] for p in owned]
    
    # Build collection data
    collection = []
    for skin_id, skin_data in SKINS_CATALOG.items():
        is_owned = skin_id in owned_skin_ids or skin_id == "default"
        purchase_info = next((p for p in owned if p["skin_id"] == skin_id), None)
        
        collection.append({
            "id": skin_id,
            "name": skin_data["name"],
            "rarity": skin_data["rarity"],
            "bonus_percent": skin_data["bonus_percent"],
            "owned": is_owned,
            "acquired_at": purchase_info.get("purchased_at") if purchase_info else None,
            "is_gift": purchase_info.get("gift_from") is not None if purchase_info else False,
            "is_achievement": purchase_info.get("achievement", False) if purchase_info else (skin_id == "ethereal" and is_owned)
        })
    
    # Calculate stats
    total_owned = len([s for s in collection if s["owned"]])
    total_skins = len(SKINS_CATALOG)
    completion_percent = (total_owned / total_skins) * 100
    
    # Count by rarity
    rarity_counts = {"mythic": 0, "legendary": 0, "epic": 0, "rare": 0, "uncommon": 0, "common": 0}
    for skin in collection:
        if skin["owned"]:
            rarity_counts[skin["rarity"]] = rarity_counts.get(skin["rarity"], 0) + 1
    
    # Calculate total bonus
    total_bonus = sum(s["bonus_percent"] for s in collection if s["owned"])
    
    # Get equipped skin
    equipped = await db.skin_equipped.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0, "skin_id": 1}
    )
    equipped_skin = equipped.get("skin_id", "default") if equipped else "default"
    
    return {
        "wallet_address": wallet_address,
        "display_name": settings.get("display_name", f"Collector_{wallet_address[:6]}"),
        "bio": settings.get("bio", ""),
        "featured_skins": settings.get("featured_skins", []),
        "show_stats": settings.get("show_stats", True),
        "is_public": settings.get("is_public", True),
        "equipped_skin": equipped_skin,
        "collection": collection,
        "stats": {
            "total_owned": total_owned,
            "total_skins": total_skins,
            "completion_percent": round(completion_percent, 1),
            "rarity_counts": rarity_counts,
            "total_bonus": total_bonus,
            "has_ethereal": "ethereal" in owned_skin_ids,
            "missing_for_ethereal": len(PURCHASABLE_SKIN_IDS) - len(set(owned_skin_ids) & set(PURCHASABLE_SKIN_IDS))
        }
    }
