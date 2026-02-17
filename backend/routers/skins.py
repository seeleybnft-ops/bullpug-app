"""Skin store routes for the Speed Run game."""

from fastapi import APIRouter, HTTPException
import uuid
import logging
from datetime import datetime, timezone

from utils.database import db

router = APIRouter(prefix="/skins", tags=["skins"])
logger = logging.getLogger(__name__)

# Skin definitions with pricing
SKINS_CATALOG = {
    "diamond": {"name": "Diamond", "bonus_percent": 5, "price_sol": 0.05, "rarity": "legendary"},
    "gold": {"name": "Gold", "bonus_percent": 5, "price_sol": 0.05, "rarity": "legendary"},
    "silver": {"name": "Silver", "bonus_percent": 4, "price_sol": 0.04, "rarity": "epic"},
    "heatmap": {"name": "Heatmap", "bonus_percent": 3, "price_sol": 0.03, "rarity": "rare"},
    "radioactive": {"name": "Radioactive", "bonus_percent": 3, "price_sol": 0.03, "rarity": "rare"},
    "zombie": {"name": "Zombie", "bonus_percent": 3, "price_sol": 0.03, "rarity": "rare"},
    "water": {"name": "Water", "bonus_percent": 2, "price_sol": 0.02, "rarity": "uncommon"},
    "fire": {"name": "Fire", "bonus_percent": 2, "price_sol": 0.02, "rarity": "uncommon"},
    "robot": {"name": "Robot", "bonus_percent": 1, "price_sol": 0.01, "rarity": "common"},
    "skeletal": {"name": "Skeletal", "bonus_percent": 1, "price_sol": 0.01, "rarity": "common"},
}

# Achievement skin - unlocked by owning all purchasable skins
ACHIEVEMENT_SKIN = {
    "ethereal": {
        "name": "Ethereal",
        "bonus_percent": 10,
        "price_sol": 0,
        "rarity": "mythic",
        "achievement": True,
        "unlock_requirement": "Own all 10 purchasable skins"
    }
}

PURCHASABLE_SKIN_IDS = list(SKINS_CATALOG.keys())


# Helper function for achievement unlock
async def check_and_unlock_ethereal(wallet_address: str, owned_skin_ids: list) -> bool:
    """Check if user owns all purchasable skins and auto-unlock Ethereal."""
    if "ethereal" in owned_skin_ids:
        return True
    
    owned_purchasable = set(owned_skin_ids) & set(PURCHASABLE_SKIN_IDS)
    
    if len(owned_purchasable) >= len(PURCHASABLE_SKIN_IDS):
        achievement_record = {
            "id": str(uuid.uuid4()),
            "wallet_address": wallet_address,
            "skin_id": "ethereal",
            "skin_name": "Ethereal",
            "amount_sol": 0,
            "tx_signature": "ACHIEVEMENT_UNLOCK",
            "status": "completed",
            "achievement": True,
            "purchased_at": datetime.now(timezone.utc).isoformat(),
            "unlock_reason": "Collected all 10 purchasable skins"
        }
        
        await db.skin_purchases.insert_one(achievement_record)
        
        # Import send_notification at call time to avoid circular imports
        from utils.notifications import send_notification
        await send_notification(
            wallet_address,
            "Achievement Unlocked: Ethereal!",
            "Congratulations! You've collected all skins and unlocked the mythic Ethereal skin with +10% bonus points!",
            "achievement"
        )
        
        logger.info(f"Ethereal achievement unlocked for wallet {wallet_address[:8]}...")
        return True
    
    return False


@router.get("/catalog")
async def get_skins_catalog():
    """Get all available skins including achievement skins."""
    all_skins = {**SKINS_CATALOG}
    for skin_id, skin_data in ACHIEVEMENT_SKIN.items():
        all_skins[skin_id] = skin_data
    return {"skins": all_skins, "achievement_skins": ACHIEVEMENT_SKIN}


@router.get("/owned/{wallet_address}")
async def get_owned_skins(wallet_address: str):
    """Get skins owned by a wallet, including achievement skins."""
    owned = await db.skin_purchases.find(
        {"wallet_address": wallet_address, "status": "completed"},
        {"_id": 0, "skin_id": 1}
    ).to_list(100)
    
    skin_ids = [p["skin_id"] for p in owned]
    
    # Check and auto-unlock Ethereal
    ethereal_unlocked = await check_and_unlock_ethereal(wallet_address, skin_ids)
    if ethereal_unlocked and "ethereal" not in skin_ids:
        skin_ids.append("ethereal")
    
    return {"skins": skin_ids, "wallet": wallet_address}


@router.get("/achievement-status/{wallet_address}")
async def get_achievement_status(wallet_address: str):
    """Get achievement skin unlock status for a wallet."""
    owned = await db.skin_purchases.find(
        {"wallet_address": wallet_address, "status": "completed"},
        {"_id": 0, "skin_id": 1}
    ).to_list(100)
    
    owned_skin_ids = [p["skin_id"] for p in owned]
    owned_purchasable = set(owned_skin_ids) & set(PURCHASABLE_SKIN_IDS)
    
    ethereal_unlocked = "ethereal" in owned_skin_ids
    if not ethereal_unlocked:
        ethereal_unlocked = await check_and_unlock_ethereal(wallet_address, owned_skin_ids)
    
    return {
        "ethereal": {
            "unlocked": ethereal_unlocked,
            "progress": len(owned_purchasable),
            "required": len(PURCHASABLE_SKIN_IDS),
            "missing_skins": list(set(PURCHASABLE_SKIN_IDS) - owned_purchasable) if not ethereal_unlocked else [],
            "bonus_percent": 10,
            "rarity": "mythic"
        }
    }


@router.post("/purchase")
async def purchase_skin(wallet_address: str, skin_id: str, tx_signature: str, amount_sol: float):
    """Record a skin purchase after SOL transaction."""
    if skin_id not in SKINS_CATALOG:
        raise HTTPException(status_code=400, detail="Invalid skin ID")
    
    skin = SKINS_CATALOG[skin_id]
    
    if abs(amount_sol - skin["price_sol"]) > 0.001:
        raise HTTPException(status_code=400, detail="Invalid payment amount")
    
    existing = await db.skin_purchases.find_one({
        "wallet_address": wallet_address,
        "skin_id": skin_id,
        "status": "completed"
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Skin already owned")
    
    purchase = {
        "id": str(uuid.uuid4()),
        "wallet_address": wallet_address,
        "skin_id": skin_id,
        "skin_name": skin["name"],
        "amount_sol": amount_sol,
        "tx_signature": tx_signature,
        "status": "completed",
        "purchased_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.skin_purchases.insert_one(purchase)
    
    from ..utils.notifications import send_notification
    await send_notification(
        wallet_address,
        f"Skin Unlocked: {skin['name']}",
        f"You now have +{skin['bonus_percent']}% bonus points!",
        "purchase"
    )
    
    return {
        "message": f"Successfully purchased {skin['name']} skin!",
        "skin_id": skin_id,
        "bonus_percent": skin["bonus_percent"],
        "tx_signature": tx_signature
    }


@router.post("/gift")
async def gift_skin(sender_wallet: str, recipient_wallet: str, skin_id: str):
    """Gift a skin to another user."""
    if skin_id == "ethereal":
        raise HTTPException(status_code=400, detail="Cannot gift achievement skins")
    
    if skin_id not in SKINS_CATALOG and skin_id != "default":
        raise HTTPException(status_code=400, detail="Invalid skin ID")
    
    if skin_id == "default":
        raise HTTPException(status_code=400, detail="Cannot gift default skin")
    
    sender_ownership = await db.skin_purchases.find_one({
        "wallet_address": sender_wallet,
        "skin_id": skin_id,
        "status": "completed"
    })
    
    if not sender_ownership:
        raise HTTPException(status_code=400, detail="You don't own this skin")
    
    if sender_wallet == recipient_wallet:
        raise HTTPException(status_code=400, detail="Cannot gift to yourself")
    
    skin = SKINS_CATALOG[skin_id]
    
    # Remove from sender
    await db.skin_purchases.update_one(
        {
            "wallet_address": sender_wallet,
            "skin_id": skin_id,
            "status": "completed"
        },
        {"$set": {
            "status": "gifted",
            "gifted_to": recipient_wallet,
            "gifted_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Add to recipient
    recipient_purchase = {
        "id": str(uuid.uuid4()),
        "wallet_address": recipient_wallet,
        "skin_id": skin_id,
        "skin_name": skin["name"],
        "amount_sol": 0,
        "tx_signature": "GIFT",
        "status": "completed",
        "gift_from": sender_wallet,
        "purchased_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.skin_purchases.insert_one(recipient_purchase)
    
    # Record gift
    gift_record = {
        "id": str(uuid.uuid4()),
        "sender_wallet": sender_wallet,
        "recipient_wallet": recipient_wallet,
        "skin_id": skin_id,
        "skin_name": skin["name"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.skin_gifts.insert_one(gift_record)
    
    # Send notifications
    from ..utils.notifications import send_notification
    await send_notification(
        recipient_wallet,
        f"Gift Received: {skin['name']}",
        f"You received a {skin['name']} skin from {sender_wallet[:8]}...!",
        "gift"
    )
    
    await send_notification(
        sender_wallet,
        f"Gift Sent: {skin['name']}",
        f"You gifted {skin['name']} to {recipient_wallet[:8]}...",
        "gift"
    )
    
    return {
        "message": f"Successfully gifted {skin['name']} to {recipient_wallet[:8]}...!",
        "skin_id": skin_id,
        "recipient": recipient_wallet
    }


@router.get("/gifts/{wallet_address}")
async def get_gift_history(wallet_address: str):
    """Get gift history for a wallet."""
    sent = await db.skin_gifts.find(
        {"sender_wallet": wallet_address},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(20)
    
    received = await db.skin_purchases.find(
        {"wallet_address": wallet_address, "gift_from": {"$exists": True}},
        {"_id": 0, "gift_from": 1, "skin_id": 1, "skin_name": 1, "purchased_at": 1}
    ).sort("purchased_at", -1).to_list(20)
    
    gifts = []
    for g in sent:
        gifts.append({
            "type": "sent",
            "skin_id": g["skin_id"],
            "skin_name": g["skin_name"],
            "recipient_wallet": g["recipient_wallet"],
            "timestamp": g["timestamp"]
        })
    for g in received:
        gifts.append({
            "type": "received",
            "skin_id": g["skin_id"],
            "skin_name": g.get("skin_name", ""),
            "sender_wallet": g["gift_from"],
            "timestamp": g["purchased_at"]
        })
    
    gifts.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"gifts": gifts[:20]}


@router.get("/stats")
async def get_skins_stats():
    """Get skin purchase statistics."""
    pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$skin_id",
            "count": {"$sum": 1},
            "total_sol": {"$sum": "$amount_sol"}
        }},
        {"$sort": {"count": -1}}
    ]
    
    stats = await db.skin_purchases.aggregate(pipeline).to_list(20)
    
    total_revenue = sum(s["total_sol"] for s in stats)
    total_sales = sum(s["count"] for s in stats)
    
    return {
        "by_skin": stats,
        "total_sales": total_sales,
        "total_revenue_sol": total_revenue
    }
