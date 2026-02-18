"""Badge system for Bullpug users - awards and achievements."""

from typing import List, Dict, Optional
from datetime import datetime, timezone
import logging

from utils.database import db

logger = logging.getLogger(__name__)

# Badge definitions
BADGES = {
    # Leaderboard badges (awarded weekly)
    "gold_champion": {
        "id": "gold_champion",
        "name": "Gold Champion",
        "description": "Top 1 weekly leaderboard",
        "emoji": "🥇",
        "color": "#FFD700",
        "tier": "legendary"
    },
    "silver_elite": {
        "id": "silver_elite",
        "name": "Silver Elite",
        "description": "Top 2-3 weekly leaderboard",
        "emoji": "🥈",
        "color": "#C0C0C0",
        "tier": "epic"
    },
    "bronze_star": {
        "id": "bronze_star",
        "name": "Bronze Star",
        "description": "Top 4-10 weekly leaderboard",
        "emoji": "🥉",
        "color": "#CD7F32",
        "tier": "rare"
    },
    
    # Achievement badges
    "game_master": {
        "id": "game_master",
        "name": "Game Master",
        "description": "Played 100+ games",
        "emoji": "🎮",
        "color": "#00FFA3",
        "tier": "epic",
        "requirement": {"type": "games_played", "count": 100}
    },
    "jackpot_winner": {
        "id": "jackpot_winner",
        "name": "Jackpot Winner",
        "description": "Won a prize pool jackpot",
        "emoji": "🏆",
        "color": "#F5D300",
        "tier": "legendary"
    },
    "whale": {
        "id": "whale",
        "name": "Whale",
        "description": "Bet 10+ SOL total",
        "emoji": "💎",
        "color": "#00C2FF",
        "tier": "epic",
        "requirement": {"type": "total_bet", "amount": 10.0}
    },
    "win_streak": {
        "id": "win_streak",
        "name": "On Fire",
        "description": "10+ consecutive wins",
        "emoji": "🔥",
        "color": "#FF6B35",
        "tier": "rare",
        "requirement": {"type": "win_streak", "count": 10}
    },
    "mooncake_hunter": {
        "id": "mooncake_hunter",
        "name": "Mooncake Hunter",
        "description": "Collected 1000+ mooncakes",
        "emoji": "🥮",
        "color": "#FFB347",
        "tier": "rare",
        "requirement": {"type": "mooncakes", "count": 1000}
    },
    "high_roller": {
        "id": "high_roller",
        "name": "High Roller",
        "description": "Won 5+ SOL in a single bet",
        "emoji": "💰",
        "color": "#9B59B6",
        "tier": "epic",
        "requirement": {"type": "single_win", "amount": 5.0}
    },
    "early_adopter": {
        "id": "early_adopter",
        "name": "Early Adopter",
        "description": "Joined in the first month",
        "emoji": "🚀",
        "color": "#E91E63",
        "tier": "rare"
    },
    "social_butterfly": {
        "id": "social_butterfly",
        "name": "Social Butterfly",
        "description": "50+ forum posts",
        "emoji": "🦋",
        "color": "#9C27B0",
        "tier": "common",
        "requirement": {"type": "forum_posts", "count": 50}
    },
    "skin_collector": {
        "id": "skin_collector",
        "name": "Skin Collector",
        "description": "Own 5+ skins",
        "emoji": "👕",
        "color": "#3F51B5",
        "tier": "common",
        "requirement": {"type": "skins_owned", "count": 5}
    }
}

# Tier order for sorting
TIER_ORDER = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}


async def get_user_badges(wallet_address: str) -> List[Dict]:
    """Get all badges for a user."""
    badge_records = await db.user_badges.find(
        {"wallet_address": wallet_address},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with badge details
    enriched = []
    for record in badge_records:
        badge_id = record.get("badge_id")
        if badge_id in BADGES:
            enriched.append({
                **BADGES[badge_id],
                "awarded_at": record.get("awarded_at"),
                "details": record.get("details")
            })
    
    # Sort by tier then by award date
    enriched.sort(key=lambda b: (TIER_ORDER.get(b.get("tier"), 99), b.get("awarded_at", "")))
    
    return enriched


async def award_badge(wallet_address: str, badge_id: str, details: Optional[Dict] = None) -> bool:
    """Award a badge to a user if they don't already have it."""
    if badge_id not in BADGES:
        logger.error(f"Unknown badge: {badge_id}")
        return False
    
    # Check if user already has this badge
    existing = await db.user_badges.find_one({
        "wallet_address": wallet_address,
        "badge_id": badge_id
    })
    
    if existing:
        logger.info(f"User {wallet_address[:8]} already has badge {badge_id}")
        return False
    
    # Award the badge
    badge_record = {
        "wallet_address": wallet_address,
        "badge_id": badge_id,
        "awarded_at": datetime.now(timezone.utc).isoformat(),
        "details": details or {}
    }
    
    await db.user_badges.insert_one(badge_record)
    logger.info(f"Awarded badge {badge_id} to {wallet_address[:8]}")
    
    return True


async def revoke_badge(wallet_address: str, badge_id: str) -> bool:
    """Revoke a badge from a user (for temporary badges like weekly leaderboard)."""
    result = await db.user_badges.delete_one({
        "wallet_address": wallet_address,
        "badge_id": badge_id
    })
    return result.deleted_count > 0


async def check_and_award_achievements(wallet_address: str) -> List[str]:
    """Check if user qualifies for any achievement badges and award them."""
    awarded = []
    
    # Get user stats
    profile = await db.user_profiles.find_one({"wallet_address": wallet_address}, {"_id": 0})
    leaderboard = await db.game_leaderboard.find_one({"wallet_address": wallet_address}, {"_id": 0})
    
    games_played = leaderboard.get("games_played", 0) if leaderboard else 0
    total_mooncakes = leaderboard.get("total_mooncakes", 0) if leaderboard else 0
    
    # Game Master - 100+ games
    if games_played >= 100:
        if await award_badge(wallet_address, "game_master", {"games_played": games_played}):
            awarded.append("game_master")
    
    # Mooncake Hunter - 1000+ mooncakes
    if total_mooncakes >= 1000:
        if await award_badge(wallet_address, "mooncake_hunter", {"total_mooncakes": total_mooncakes}):
            awarded.append("mooncake_hunter")
    
    # Check betting stats
    betting_stats = await db.betting_stats.find_one({"wallet_address": wallet_address}, {"_id": 0})
    if betting_stats:
        total_bet = betting_stats.get("total_bet_sol", 0)
        max_win = betting_stats.get("max_single_win_sol", 0)
        win_streak = betting_stats.get("current_win_streak", 0)
        
        # Whale - 10+ SOL bet total
        if total_bet >= 10.0:
            if await award_badge(wallet_address, "whale", {"total_bet_sol": total_bet}):
                awarded.append("whale")
        
        # High Roller - 5+ SOL single win
        if max_win >= 5.0:
            if await award_badge(wallet_address, "high_roller", {"max_win_sol": max_win}):
                awarded.append("high_roller")
        
        # Win Streak - 10+ consecutive wins
        if win_streak >= 10:
            if await award_badge(wallet_address, "win_streak", {"streak": win_streak}):
                awarded.append("win_streak")
    
    # Check skin ownership
    skin_purchases = await db.skin_purchases.count_documents({
        "wallet_address": wallet_address,
        "status": "completed"
    })
    if skin_purchases >= 5:
        if await award_badge(wallet_address, "skin_collector", {"skins_owned": skin_purchases}):
            awarded.append("skin_collector")
    
    # Check forum posts
    forum_posts = await db.forum_posts.count_documents({"wallet_address": wallet_address})
    if forum_posts >= 50:
        if await award_badge(wallet_address, "social_butterfly", {"forum_posts": forum_posts}):
            awarded.append("social_butterfly")
    
    return awarded


async def award_leaderboard_badges(winners: List[Dict]) -> List[str]:
    """Award leaderboard badges to weekly winners. Returns list of awarded badge IDs."""
    awarded = []
    
    # First, revoke old leaderboard badges from everyone
    await db.user_badges.delete_many({"badge_id": {"$in": ["gold_champion", "silver_elite", "bronze_star"]}})
    
    for i, winner in enumerate(winners):
        wallet = winner.get("wallet_address")
        if not wallet:
            continue
        
        if i == 0:
            # 1st place - Gold Champion
            if await award_badge(wallet, "gold_champion", {"rank": 1, "score": winner.get("high_score")}):
                awarded.append(f"gold_champion:{wallet[:8]}")
        elif i <= 2:
            # 2nd-3rd place - Silver Elite
            if await award_badge(wallet, "silver_elite", {"rank": i + 1, "score": winner.get("high_score")}):
                awarded.append(f"silver_elite:{wallet[:8]}")
        elif i <= 9:
            # 4th-10th place - Bronze Star
            if await award_badge(wallet, "bronze_star", {"rank": i + 1, "score": winner.get("high_score")}):
                awarded.append(f"bronze_star:{wallet[:8]}")
    
    return awarded


async def award_jackpot_badge(wallet_address: str, prize_sol: float, rank: int) -> bool:
    """Award jackpot winner badge."""
    return await award_badge(wallet_address, "jackpot_winner", {
        "prize_sol": prize_sol,
        "rank": rank,
        "won_at": datetime.now(timezone.utc).isoformat()
    })


def get_badge_info(badge_id: str) -> Optional[Dict]:
    """Get badge information by ID."""
    return BADGES.get(badge_id)


def get_all_badges() -> Dict:
    """Get all available badges."""
    return BADGES
