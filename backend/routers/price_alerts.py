"""
Price Alerts Router

Manages price alerts and breakout scanning for tokens.
Extracted from ai_trader.py for modularity.
"""

import uuid
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from utils.database import db
from services.token_price import TOKENS, get_token_price_by_mint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-trader", tags=["price-alerts"])


class PriceAlert(BaseModel):
    wallet_address: str
    symbol: str
    token_mint: Optional[str] = None
    alert_type: str  # "breakout_up", "breakout_down", "price_above", "price_below"
    target_price: Optional[float] = None
    created_at: Optional[str] = None
    triggered: bool = False
    triggered_at: Optional[str] = None


class CreateAlertRequest(BaseModel):
    wallet_address: str
    symbol: str
    token_mint: Optional[str] = None
    alert_type: str = "breakout_up"
    target_price: Optional[float] = None


@router.post("/alerts/create")
async def create_price_alert(request: CreateAlertRequest):
    """Create a new price alert for breakout signals or price targets."""
    try:
        alert_id = str(uuid.uuid4())[:8]

        alert_doc = {
            "alert_id": alert_id,
            "wallet_address": request.wallet_address,
            "symbol": request.symbol.upper(),
            "token_mint": request.token_mint,
            "alert_type": request.alert_type,
            "target_price": request.target_price,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "triggered": False,
            "triggered_at": None,
            "active": True,
        }

        await db.price_alerts.insert_one(alert_doc)

        return {
            "success": True,
            "alert_id": alert_id,
            "message": f"Alert created for {request.symbol.upper()}",
        }
    except Exception as e:
        logger.error(f"Create alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{wallet_address}")
async def get_price_alerts(wallet_address: str):
    """Get all price alerts for a wallet."""
    try:
        alerts = (
            await db.price_alerts.find(
                {"wallet_address": wallet_address, "active": True}, {"_id": 0}
            )
            .sort("created_at", -1)
            .to_list(50)
        )

        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return {"alerts": [], "count": 0, "error": str(e)}


@router.delete("/alerts/{alert_id}")
async def delete_price_alert(alert_id: str):
    """Delete a price alert."""
    try:
        result = await db.price_alerts.update_one(
            {"alert_id": alert_id}, {"$set": {"active": False}}
        )

        return {
            "success": result.modified_count > 0,
            "message": (
                "Alert deleted" if result.modified_count > 0 else "Alert not found"
            ),
        }
    except Exception as e:
        logger.error(f"Delete alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/check/{wallet_address}")
async def check_alerts(wallet_address: str):
    """Check if any alerts have been triggered based on current market conditions."""
    try:
        alerts = await db.price_alerts.find(
            {"wallet_address": wallet_address, "active": True, "triggered": False},
            {"_id": 0},
        ).to_list(50)

        if not alerts:
            return {"triggered_alerts": [], "count": 0}

        triggered = []

        # Group alerts by symbol for efficient fetching
        symbols = list(set(a["symbol"] for a in alerts))

        for symbol in symbols:
            symbol_alerts = [a for a in alerts if a["symbol"] == symbol]

            # Fetch current price using multi-source
            token_mint = symbol_alerts[0].get("token_mint") or TOKENS.get(symbol)
            current_price = None
            price_change_1h = 0
            volume_24h = 0

            if token_mint:
                current_price = await get_token_price_by_mint(
                    token_mint, symbol=symbol
                )

                # Try to get price change data from CoinGecko/DexScreener
                try:
                    from services.market_data import get_token_market_data_multi

                    market_data = await get_token_market_data_multi(symbol, token_mint)
                    if market_data:
                        price_change_1h = market_data.get("price_change_1h", 0)
                        volume_24h = market_data.get("volume_24h", 0)
                except Exception:
                    pass

            if current_price is None or current_price == 0:
                continue

            # Check each alert
            for alert in symbol_alerts:
                alert_triggered = False
                trigger_reason = ""

                if (
                    alert["alert_type"] == "price_above"
                    and alert.get("target_price")
                ):
                    if current_price >= alert["target_price"]:
                        alert_triggered = True
                        trigger_reason = f"Price ${current_price:.6f} reached target ${alert['target_price']:.6f}"

                elif (
                    alert["alert_type"] == "price_below"
                    and alert.get("target_price")
                ):
                    if current_price <= alert["target_price"]:
                        alert_triggered = True
                        trigger_reason = f"Price ${current_price:.6f} dropped to target ${alert['target_price']:.6f}"

                elif alert["alert_type"] == "breakout_up":
                    if price_change_1h > 10 and volume_24h > 50000:
                        alert_triggered = True
                        trigger_reason = f"BREAKOUT UP: +{price_change_1h:.1f}% in 1h, Vol: ${volume_24h:,.0f}"

                elif alert["alert_type"] == "breakout_down":
                    if price_change_1h < -10:
                        alert_triggered = True
                        trigger_reason = (
                            f"BREAKDOWN: {price_change_1h:.1f}% in 1h"
                        )

                if alert_triggered:
                    await db.price_alerts.update_one(
                        {"alert_id": alert["alert_id"]},
                        {
                            "$set": {
                                "triggered": True,
                                "triggered_at": datetime.now(
                                    timezone.utc
                                ).isoformat(),
                                "trigger_price": current_price,
                                "trigger_reason": trigger_reason,
                            }
                        },
                    )

                    alert_info = {
                        "alert_id": alert["alert_id"],
                        "symbol": symbol,
                        "alert_type": alert["alert_type"],
                        "current_price": current_price,
                        "target_price": alert.get("target_price"),
                        "trigger_reason": trigger_reason,
                        "triggered_at": datetime.now(timezone.utc).isoformat(),
                        "token_mint": alert.get("token_mint"),
                    }

                    triggered.append(alert_info)

                    # Send Telegram notification
                    try:
                        from routers.telegram import send_breakout_alert

                        await send_breakout_alert(wallet_address, alert_info)
                    except Exception as tg_err:
                        logger.warning(f"Telegram notification failed: {tg_err}")

        return {"triggered_alerts": triggered, "count": len(triggered)}
    except Exception as e:
        logger.error(f"Check alerts error: {e}")
        return {"triggered_alerts": [], "count": 0, "error": str(e)}


@router.post("/alerts/breakout-scan")
async def scan_for_breakouts(wallet_address: str):
    """Scan market for potential breakout candidates and create alerts automatically."""
    try:
        new_alerts = []

        # Use CoinGecko for discovery instead of DexScreener search (rate limit)
        try:
            from services.market_data import discover_trending_solana_tokens

            trending = await discover_trending_solana_tokens(max_tokens=20)

            for token in trending:
                symbol = token.get("symbol", "").upper()

                if symbol in {"USDC", "USDT", "SOL", "WSOL"}:
                    continue

                pc1h = token.get("price_change_1h", 0)
                pc24h = token.get("price_change_24h", 0)
                volume_24h = token.get("volume_24h", 0)

                # Breakout candidate: consolidating (small 1h) but building (24h momentum)
                is_breakout_candidate = (
                    volume_24h > 1_000_000
                    and abs(pc1h) < 5
                    and pc24h > 15
                )

                if is_breakout_candidate:
                    existing = await db.price_alerts.find_one(
                        {
                            "wallet_address": wallet_address,
                            "symbol": symbol,
                            "active": True,
                            "triggered": False,
                        }
                    )

                    if not existing:
                        alert_id = str(uuid.uuid4())[:8]

                        alert_doc = {
                            "alert_id": alert_id,
                            "wallet_address": wallet_address,
                            "symbol": symbol,
                            "token_mint": None,
                            "alert_type": "breakout_up",
                            "target_price": None,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "triggered": False,
                            "active": True,
                            "auto_created": True,
                            "scan_reason": f"Building momentum: +{pc24h:.1f}% (24h), Vol: ${volume_24h:,.0f}",
                        }

                        await db.price_alerts.insert_one(alert_doc)
                        new_alerts.append(
                            {
                                "alert_id": alert_id,
                                "symbol": symbol,
                                "reason": alert_doc["scan_reason"],
                            }
                        )
        except Exception as e:
            logger.warning(f"Breakout scan failed: {e}")

        return {
            "success": True,
            "new_alerts": new_alerts,
            "count": len(new_alerts),
            "message": f"Created {len(new_alerts)} breakout alerts",
        }
    except Exception as e:
        logger.error(f"Breakout scan error: {e}")
        return {"success": False, "new_alerts": [], "error": str(e)}
