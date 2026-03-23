"""
Runner Alerts Service

Monitors for new high-potential runner tokens and sends real-time alerts
via Telegram and Push Notifications.

Features:
- Periodic scanning for new runner tokens
- Alert deduplication (don't spam same token)
- User-configurable alert thresholds
- Multi-channel delivery (Telegram + Push)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from utils.database import db
from services.runner_detector import RunnerDetector

logger = logging.getLogger(__name__)

# Default alert thresholds
DEFAULT_MIN_RUNNER_SCORE = 50  # Minimum score to trigger alert
DEFAULT_MIN_PRICE_CHANGE_1H = 10  # Minimum 1h price change %
DEFAULT_MIN_VOLUME_24H = 100000  # Minimum 24h volume in USD
ALERT_COOLDOWN_HOURS = 6  # Don't re-alert same token within this period


class RunnerAlertService:
    """
    Service for managing and sending runner token alerts.
    """
    
    @staticmethod
    async def get_user_preferences(wallet_address: str) -> Dict[str, Any]:
        """Get user's runner alert preferences."""
        prefs = await db.runner_alert_preferences.find_one(
            {"wallet_address": wallet_address},
            {"_id": 0}
        )
        
        if not prefs:
            return {
                "wallet_address": wallet_address,
                "enabled": False,
                "telegram_enabled": True,
                "push_enabled": True,
                "min_runner_score": DEFAULT_MIN_RUNNER_SCORE,
                "min_price_change_1h": DEFAULT_MIN_PRICE_CHANGE_1H,
                "min_volume_24h": DEFAULT_MIN_VOLUME_24H,
                "alert_categories": ["high_momentum", "new_runner", "breakout"]
            }
        
        return prefs
    
    @staticmethod
    async def update_user_preferences(
        wallet_address: str,
        enabled: Optional[bool] = None,
        telegram_enabled: Optional[bool] = None,
        push_enabled: Optional[bool] = None,
        min_runner_score: Optional[int] = None,
        min_price_change_1h: Optional[float] = None,
        min_volume_24h: Optional[float] = None,
        alert_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update user's runner alert preferences."""
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        
        if enabled is not None:
            update_data["enabled"] = enabled
        if telegram_enabled is not None:
            update_data["telegram_enabled"] = telegram_enabled
        if push_enabled is not None:
            update_data["push_enabled"] = push_enabled
        if min_runner_score is not None:
            update_data["min_runner_score"] = max(30, min(90, min_runner_score))
        if min_price_change_1h is not None:
            update_data["min_price_change_1h"] = max(5, min(50, min_price_change_1h))
        if min_volume_24h is not None:
            update_data["min_volume_24h"] = max(10000, min(1000000, min_volume_24h))
        if alert_categories is not None:
            valid_categories = ["high_momentum", "new_runner", "breakout", "volume_surge"]
            update_data["alert_categories"] = [c for c in alert_categories if c in valid_categories]
        
        await db.runner_alert_preferences.update_one(
            {"wallet_address": wallet_address},
            {
                "$set": update_data,
                "$setOnInsert": {
                    "wallet_address": wallet_address,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        return await RunnerAlertService.get_user_preferences(wallet_address)
    
    @staticmethod
    async def check_alert_cooldown(wallet_address: str, token_address: str) -> bool:
        """
        Check if we can send an alert for this token (respects cooldown).
        Returns True if alert can be sent, False if in cooldown.
        """
        cooldown_cutoff = (datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)).isoformat()
        
        recent_alert = await db.runner_alerts_sent.find_one({
            "wallet_address": wallet_address,
            "token_address": token_address,
            "sent_at": {"$gte": cooldown_cutoff}
        })
        
        return recent_alert is None
    
    @staticmethod
    async def record_alert_sent(
        wallet_address: str,
        token_address: str,
        symbol: str,
        alert_type: str,
        channel: str
    ):
        """Record that an alert was sent to avoid duplicates."""
        await db.runner_alerts_sent.insert_one({
            "wallet_address": wallet_address,
            "token_address": token_address,
            "symbol": symbol,
            "alert_type": alert_type,
            "channel": channel,
            "sent_at": datetime.now(timezone.utc).isoformat()
        })
    
    @staticmethod
    async def get_subscribed_users() -> List[Dict[str, Any]]:
        """Get all users who have runner alerts enabled."""
        users = await db.runner_alert_preferences.find(
            {"enabled": True},
            {"_id": 0}
        ).to_list(1000)
        
        return users
    
    @staticmethod
    async def scan_and_alert():
        """
        Main scanner function - checks for new runners and sends alerts.
        This should be called periodically (e.g., every 5 minutes).
        """
        logger.info("Starting runner alert scan...")
        
        try:
            # Get current runners
            runners = await RunnerDetector.fetch_trending_pairs(limit=20)
            
            if not runners:
                logger.info("No runners found in scan")
                return {"alerts_sent": 0, "runners_found": 0}
            
            logger.info(f"Found {len(runners)} potential runners")
            
            # Get all subscribed users
            subscribed_users = await RunnerAlertService.get_subscribed_users()
            
            if not subscribed_users:
                logger.info("No users subscribed to runner alerts")
                return {"alerts_sent": 0, "runners_found": len(runners), "users_checked": 0}
            
            alerts_sent = 0
            
            for user in subscribed_users:
                wallet_address = user.get("wallet_address")
                min_score = user.get("min_runner_score", DEFAULT_MIN_RUNNER_SCORE)
                min_change = user.get("min_price_change_1h", DEFAULT_MIN_PRICE_CHANGE_1H)
                min_volume = user.get("min_volume_24h", DEFAULT_MIN_VOLUME_24H)
                categories = user.get("alert_categories", ["high_momentum", "new_runner"])
                
                for runner in runners:
                    # Check if runner meets user's thresholds
                    if runner.get("runner_score", 0) < min_score:
                        continue
                    if runner.get("price_change_1h", 0) < min_change:
                        continue
                    if runner.get("volume_24h", 0) < min_volume:
                        continue
                    
                    # Check cooldown
                    can_alert = await RunnerAlertService.check_alert_cooldown(
                        wallet_address, runner["token_address"]
                    )
                    
                    if not can_alert:
                        continue
                    
                    # Determine alert type
                    alert_type = RunnerAlertService._classify_alert_type(runner)
                    
                    if alert_type not in categories:
                        continue
                    
                    # Send alerts
                    sent = await RunnerAlertService.send_runner_alert(
                        wallet_address=wallet_address,
                        runner=runner,
                        alert_type=alert_type,
                        telegram_enabled=user.get("telegram_enabled", True),
                        push_enabled=user.get("push_enabled", True)
                    )
                    
                    if sent:
                        alerts_sent += 1
            
            logger.info(f"Runner alert scan complete: {alerts_sent} alerts sent")
            return {
                "alerts_sent": alerts_sent,
                "runners_found": len(runners),
                "users_checked": len(subscribed_users)
            }
        
        except Exception as e:
            logger.error(f"Runner alert scan error: {e}")
            return {"alerts_sent": 0, "error": str(e)}
    
    @staticmethod
    def _classify_alert_type(runner: Dict[str, Any]) -> str:
        """Classify the type of runner alert based on metrics."""
        score = runner.get("runner_score", 0)
        price_change = runner.get("price_change_1h", 0)
        hours_old = runner.get("hours_since_creation", 999)
        
        # New runner (< 24 hours old with decent score)
        if hours_old < 24 and score >= 40:
            return "new_runner"
        
        # High momentum (strong 1h price movement)
        if price_change >= 20:
            return "high_momentum"
        
        # Breakout (high score indicating multiple bullish factors)
        if score >= 70:
            return "breakout"
        
        # Volume surge (high volume relative to liquidity)
        volume = runner.get("volume_24h", 0)
        liquidity = runner.get("liquidity_usd", 1)
        if volume / liquidity > 5:  # Volume 5x liquidity
            return "volume_surge"
        
        return "high_momentum"  # Default category
    
    @staticmethod
    async def send_runner_alert(
        wallet_address: str,
        runner: Dict[str, Any],
        alert_type: str,
        telegram_enabled: bool = True,
        push_enabled: bool = True
    ) -> bool:
        """
        Send runner alert via configured channels.
        Returns True if at least one channel succeeded.
        """
        symbol = runner.get("symbol", "???")
        token_address = runner.get("token_address", "")
        score = runner.get("runner_score", 0)
        price = runner.get("price_usd", 0)
        price_change_1h = runner.get("price_change_1h", 0)
        volume = runner.get("volume_24h", 0)
        hours_old = runner.get("hours_since_creation", 0)
        buy_ratio = runner.get("buy_ratio", 0.5)
        dex = runner.get("dex", "unknown")
        
        success = False
        
        # Send Telegram alert
        if telegram_enabled:
            try:
                from routers.telegram import send_telegram_message
                
                account = await db.telegram_accounts.find_one({
                    "wallet_address": wallet_address,
                    "active": True,
                    "alerts_enabled": True
                })
                
                if account and account.get("chat_id"):
                    # Format message based on alert type
                    alert_emoji = {
                        "new_runner": "🆕",
                        "high_momentum": "🚀",
                        "breakout": "💥",
                        "volume_surge": "📊"
                    }.get(alert_type, "🔔")
                    
                    alert_title = {
                        "new_runner": "New Runner Detected!",
                        "high_momentum": "High Momentum Alert!",
                        "breakout": "Breakout Signal!",
                        "volume_surge": "Volume Surge!"
                    }.get(alert_type, "Runner Alert")
                    
                    # Format price nicely
                    if price < 0.00001:
                        price_str = f"${price:.10f}"
                    elif price < 0.01:
                        price_str = f"${price:.6f}"
                    else:
                        price_str = f"${price:.4f}"
                    
                    msg = f"""
{alert_emoji} <b>{alert_title}</b>

<b>{symbol}</b> on {dex.capitalize()}
Score: <b>{score}/100</b>

📈 1H Change: <code>{price_change_1h:+.1f}%</code>
💰 Price: <code>{price_str}</code>
📊 24H Volume: <code>${volume:,.0f}</code>
⏱️ Age: {hours_old:.1f}h
🟢 Buy Ratio: {buy_ratio*100:.0f}%

<a href="https://dexscreener.com/solana/{token_address}">📊 View Chart</a>

<b>Quick Actions:</b>
<code>/buy {symbol} 0.1</code>
<code>/price {symbol}</code>

<i>Runner alerts powered by Bullpug AI</i>
"""
                    
                    sent = await send_telegram_message(account["chat_id"], msg)
                    if sent:
                        await RunnerAlertService.record_alert_sent(
                            wallet_address, token_address, symbol, alert_type, "telegram"
                        )
                        success = True
                        logger.info(f"Telegram runner alert sent: {symbol} to {wallet_address[:8]}...")
            
            except Exception as e:
                logger.error(f"Failed to send Telegram runner alert: {e}")
        
        # Send Push notification
        if push_enabled:
            try:
                from routers.push_notifications import send_push_notification
                
                result = await send_push_notification(
                    wallet_address=wallet_address,
                    notification_type="runner_alert",
                    title=f"🚀 Runner: {symbol} +{price_change_1h:.0f}%",
                    body=f"Score {score}/100 • Vol ${volume/1000:.0f}K • {dex.capitalize()}",
                    data={
                        "symbol": symbol,
                        "token_address": token_address,
                        "runner_score": score,
                        "alert_type": alert_type
                    },
                    url=f"/ai-trader?tab=tokens&highlight={token_address}"
                )
                
                if result.get("success"):
                    await RunnerAlertService.record_alert_sent(
                        wallet_address, token_address, symbol, alert_type, "push"
                    )
                    success = True
                    logger.info(f"Push runner alert sent: {symbol} to {wallet_address[:8]}...")
            
            except Exception as e:
                logger.error(f"Failed to send Push runner alert: {e}")
        
        return success
    
    @staticmethod
    async def get_recent_alerts(wallet_address: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent runner alerts sent to a user."""
        alerts = await db.runner_alerts_sent.find(
            {"wallet_address": wallet_address},
            {"_id": 0}
        ).sort("sent_at", -1).limit(limit).to_list(limit)
        
        return alerts
    
    @staticmethod
    async def cleanup_old_alerts(days: int = 7):
        """Clean up alert records older than specified days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        result = await db.runner_alerts_sent.delete_many({
            "sent_at": {"$lt": cutoff}
        })
        
        logger.info(f"Cleaned up {result.deleted_count} old alert records")
        return result.deleted_count
