"""User profile routes for wallet-based profiles."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import uuid
import logging
import base64
from datetime import datetime, timezone

from utils.database import db

router = APIRouter(prefix="/profile", tags=["profile"])
logger = logging.getLogger(__name__)


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    twitter_handle: Optional[str] = None
    telegram_handle: Optional[str] = None
    discord_handle: Optional[str] = None
    website_url: Optional[str] = None
    profile_skin_id: Optional[str] = None  # Use a Bullpug skin as profile pic


class ProfileCreate(BaseModel):
    wallet_address: str
    display_name: Optional[str] = None


async def get_or_create_profile(wallet_address: str):
    """Get existing profile or create a new one."""
    profile = await db.user_profiles.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    
    if not profile:
        # Create default profile
        profile = {
            "id": str(uuid.uuid4()),
            "wallet_address": wallet_address,
            "display_name": f"Bullpug_{wallet_address[:6]}",
            "bio": "",
            "profile_image_url": None,
            "profile_skin_id": None,
            "twitter_handle": None,
            "telegram_handle": None,
            "discord_handle": None,
            "website_url": None,
            "owned_skins": ["default"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.user_profiles.insert_one(profile)
        profile.pop("_id", None)  # Remove MongoDB _id if present
        logger.info(f"Created new profile for wallet: {wallet_address[:8]}...")
    
    return profile


@router.get("/{wallet_address}")
async def get_profile(wallet_address: str):
    """Get user profile by wallet address."""
    profile = await get_or_create_profile(wallet_address)
    
    # Get owned skins
    skin_purchases = await db.skin_purchases.find(
        {"wallet_address": wallet_address, "status": "completed"},
        {"_id": 0, "skin_id": 1}
    ).to_list(100)
    
    owned_skins = ["default"] + [s["skin_id"] for s in skin_purchases]
    profile["owned_skins"] = list(set(owned_skins))
    
    # Get game stats
    leaderboard_entry = await db.game_leaderboard.find_one(
        {"wallet_address": wallet_address},
        {"_id": 0}
    )
    
    profile["game_stats"] = {
        "high_score": leaderboard_entry.get("high_score", 0) if leaderboard_entry else 0,
        "total_mooncakes": leaderboard_entry.get("total_mooncakes", 0) if leaderboard_entry else 0,
        "games_played": leaderboard_entry.get("games_played", 0) if leaderboard_entry else 0
    }
    
    return profile


@router.post("/create")
async def create_profile(data: ProfileCreate):
    """Create or get existing profile for a wallet."""
    profile = await get_or_create_profile(data.wallet_address)
    
    if data.display_name and data.display_name != profile.get("display_name"):
        await db.user_profiles.update_one(
            {"wallet_address": data.wallet_address},
            {"$set": {
                "display_name": data.display_name,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        profile["display_name"] = data.display_name
    
    return profile


@router.put("/{wallet_address}")
async def update_profile(wallet_address: str, data: ProfileUpdate):
    """Update user profile."""
    profile = await get_or_create_profile(wallet_address)
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if data.display_name is not None:
        update_data["display_name"] = data.display_name[:50]  # Max 50 chars
    
    if data.bio is not None:
        update_data["bio"] = data.bio[:500]  # Max 500 chars
    
    if data.twitter_handle is not None:
        handle = data.twitter_handle.replace("@", "").strip()
        update_data["twitter_handle"] = handle[:50] if handle else None
    
    if data.telegram_handle is not None:
        handle = data.telegram_handle.replace("@", "").strip()
        update_data["telegram_handle"] = handle[:50] if handle else None
    
    if data.discord_handle is not None:
        update_data["discord_handle"] = data.discord_handle[:50] if data.discord_handle else None
    
    if data.website_url is not None:
        update_data["website_url"] = data.website_url[:200] if data.website_url else None
    
    if data.profile_skin_id is not None:
        # Verify user owns this skin
        owned_skins = ["default"]
        skin_purchases = await db.skin_purchases.find(
            {"wallet_address": wallet_address, "status": "completed"},
            {"_id": 0, "skin_id": 1}
        ).to_list(100)
        owned_skins.extend([s["skin_id"] for s in skin_purchases])
        
        if data.profile_skin_id in owned_skins:
            update_data["profile_skin_id"] = data.profile_skin_id
        else:
            raise HTTPException(status_code=400, detail="You don't own this skin")
    
    await db.user_profiles.update_one(
        {"wallet_address": wallet_address},
        {"$set": update_data}
    )
    
    return {"message": "Profile updated", "updated_fields": list(update_data.keys())}


@router.post("/{wallet_address}/upload-image")
async def upload_profile_image(wallet_address: str, file: UploadFile = File(...)):
    """Upload a custom profile image."""
    # Verify file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read and encode image (max 500KB)
    contents = await file.read()
    if len(contents) > 500 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 500KB)")
    
    # Store as base64 data URL
    content_type = file.content_type
    base64_data = base64.b64encode(contents).decode('utf-8')
    data_url = f"data:{content_type};base64,{base64_data}"
    
    await db.user_profiles.update_one(
        {"wallet_address": wallet_address},
        {"$set": {
            "profile_image_url": data_url,
            "profile_skin_id": None,  # Clear skin selection when custom image uploaded
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Profile image uploaded", "image_url": data_url[:100] + "..."}


@router.get("/{wallet_address}/skins")
async def get_available_skins(wallet_address: str):
    """Get skins available for profile picture."""
    # Default skin always available
    owned_skins = ["default"]
    
    # Get purchased skins
    skin_purchases = await db.skin_purchases.find(
        {"wallet_address": wallet_address, "status": "completed"},
        {"_id": 0, "skin_id": 1, "skin_name": 1}
    ).to_list(100)
    
    for s in skin_purchases:
        owned_skins.append(s["skin_id"])
    
    # Skin catalog with image paths
    SKIN_IMAGES = {
        "default": {"name": "Guardian", "image": "/images/guardian_cutout.png"},
        "diamond": {"name": "Diamond", "image": "/images/diamond_cutout.png"},
        "gold": {"name": "Gold", "image": "/images/gold_cutout.png"},
        "silver": {"name": "Silver", "image": "/images/silver_cutout.png"},
        "heatmap": {"name": "Heatmap", "image": "/images/heatmap_cutout.png"},
        "radioactive": {"name": "Radioactive", "image": "/images/radioactive_cutout.png"},
        "zombie": {"name": "Zombie", "image": "/images/zombie_cutout.png"},
        "water": {"name": "Aqua", "image": "/images/water_cutout.png"},
        "fire": {"name": "Inferno", "image": "/images/fire_cutout.png"},
        "robot": {"name": "Cyber", "image": "/images/robot_cutout.png"},
        "skeletal": {"name": "Phantom", "image": "/images/skeletal_cutout.png"},
        "ethereal": {"name": "Ethereal", "image": "/images/ethereal_cutout.png"},
    }
    
    available = []
    for skin_id in set(owned_skins):
        if skin_id in SKIN_IMAGES:
            available.append({
                "id": skin_id,
                "name": SKIN_IMAGES[skin_id]["name"],
                "image": SKIN_IMAGES[skin_id]["image"],
                "owned": True
            })
    
    return {"skins": available}
