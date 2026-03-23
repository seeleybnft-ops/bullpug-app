"""
Runner Alerts Router

API endpoints for managing runner token alerts via Telegram and Push notifications.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from services.runner_alerts import RunnerAlertService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runner-alerts", tags=["Runner Alerts"])


# ============== Models ==============

class RunnerAlertPreferencesUpdate(BaseModel):
    """Request to update runner alert preferences"""
    enabled: Optional[bool] = None
    telegram_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    min_runner_score: Optional[int] = Field(None, ge=30, le=90)
    min_price_change_1h: Optional[float] = Field(None, ge=5, le=50)
    min_volume_24h: Optional[float] = Field(None, ge=10000, le=1000000)
    alert_categories: Optional[List[str]] = None


# ============== Endpoints ==============

@router.get("/preferences/{wallet_address}")
async def get_runner_alert_preferences(wallet_address: str):
    """Get runner alert preferences for a wallet."""
    return await RunnerAlertService.get_user_preferences(wallet_address)


@router.put("/preferences/{wallet_address}")
async def update_runner_alert_preferences(
    wallet_address: str,
    preferences: RunnerAlertPreferencesUpdate
):
    """Update runner alert preferences."""
    return await RunnerAlertService.update_user_preferences(
        wallet_address=wallet_address,
        enabled=preferences.enabled,
        telegram_enabled=preferences.telegram_enabled,
        push_enabled=preferences.push_enabled,
        min_runner_score=preferences.min_runner_score,
        min_price_change_1h=preferences.min_price_change_1h,
        min_volume_24h=preferences.min_volume_24h,
        alert_categories=preferences.alert_categories
    )


@router.post("/enable/{wallet_address}")
async def enable_runner_alerts(wallet_address: str):
    """Quick enable runner alerts with default settings."""
    return await RunnerAlertService.update_user_preferences(
        wallet_address=wallet_address,
        enabled=True
    )


@router.post("/disable/{wallet_address}")
async def disable_runner_alerts(wallet_address: str):
    """Disable runner alerts."""
    return await RunnerAlertService.update_user_preferences(
        wallet_address=wallet_address,
        enabled=False
    )


@router.get("/history/{wallet_address}")
async def get_runner_alert_history(
    wallet_address: str,
    limit: int = Query(20, ge=1, le=100)
):
    """Get recent runner alerts sent to a wallet."""
    alerts = await RunnerAlertService.get_recent_alerts(wallet_address, limit)
    return {
        "alerts": alerts,
        "count": len(alerts)
    }


@router.post("/scan")
async def trigger_runner_scan(background_tasks: BackgroundTasks):
    """
    Manually trigger a runner alert scan.
    Scans for new runners and sends alerts to subscribed users.
    """
    background_tasks.add_task(RunnerAlertService.scan_and_alert)
    return {
        "success": True,
        "message": "Runner alert scan started in background"
    }


@router.post("/test/{wallet_address}")
async def send_test_runner_alert(wallet_address: str):
    """
    Send a test runner alert to verify the notification setup.
    """
    # Create a mock runner for testing
    mock_runner = {
        "symbol": "TEST",
        "token_address": "test123456789",
        "price_usd": 0.00001234,
        "runner_score": 75,
        "price_change_1h": 25.5,
        "volume_24h": 150000,
        "hours_since_creation": 12,
        "buy_ratio": 0.65,
        "dex": "raydium"
    }
    
    prefs = await RunnerAlertService.get_user_preferences(wallet_address)
    
    success = await RunnerAlertService.send_runner_alert(
        wallet_address=wallet_address,
        runner=mock_runner,
        alert_type="high_momentum",
        telegram_enabled=prefs.get("telegram_enabled", True),
        push_enabled=prefs.get("push_enabled", True)
    )
    
    return {
        "success": success,
        "message": "Test alert sent" if success else "Failed to send test alert - check Telegram/Push setup"
    }


@router.get("/status")
async def get_runner_alert_status():
    """Get overall runner alert system status."""
    subscribed_users = await RunnerAlertService.get_subscribed_users()
    
    return {
        "active": True,
        "subscribed_users": len(subscribed_users),
        "scan_interval_minutes": 5,
        "alert_categories": ["high_momentum", "new_runner", "breakout", "volume_surge"]
    }
