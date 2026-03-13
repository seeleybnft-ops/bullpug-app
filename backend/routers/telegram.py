"""
Telegram Bot Integration for Bullpug Price Alerts
- Users link their Telegram account via a unique code
- Receives breakout and price alerts directly in Telegram
"""

import os
import uuid
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


class LinkTelegramRequest(BaseModel):
    wallet_address: str


class VerifyCodeRequest(BaseModel):
    wallet_address: str
    code: str


class TelegramMessage(BaseModel):
    chat_id: int
    message: str
    parse_mode: str = "HTML"


# ============================================================================
# TELEGRAM BOT API HELPERS
# ============================================================================

async def send_telegram_message(chat_id: int, message: str, parse_mode: str = "HTML") -> bool:
    """Send a message to a Telegram chat."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Telegram message sent to {chat_id}")
                return True
            else:
                logger.error(f"Telegram send failed: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False


async def get_bot_info() -> dict:
    """Get information about the bot."""
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "Bot token not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{TELEGRAM_API_URL}/getMe")
            if response.status_code == 200:
                return response.json().get("result", {})
    except Exception as e:
        logger.error(f"Get bot info error: {e}")
    return {}


# ============================================================================
# LINKING ENDPOINTS
# ============================================================================

@router.get("/bot-info")
async def telegram_bot_info():
    """Get the bot username for users to message."""
    bot_info = await get_bot_info()
    if bot_info.get("username"):
        return {
            "success": True,
            "bot_username": bot_info.get("username"),
            "bot_name": bot_info.get("first_name", "Bullpug Alerts"),
            "link": f"https://t.me/{bot_info.get('username')}"
        }
    return {
        "success": False,
        "error": "Bot not configured"
    }


@router.post("/generate-link-code")
async def generate_link_code(request: LinkTelegramRequest):
    """Generate a unique code for linking Telegram account."""
    try:
        # Generate a 6-character code
        code = str(uuid.uuid4())[:6].upper()
        
        # Store the code with expiration (15 minutes)
        await db.telegram_link_codes.update_one(
            {"wallet_address": request.wallet_address},
            {
                "$set": {
                    "code": code,
                    "wallet_address": request.wallet_address,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": datetime.now(timezone.utc).timestamp() + 900,  # 15 min
                    "used": False
                }
            },
            upsert=True
        )
        
        bot_info = await get_bot_info()
        bot_username = bot_info.get("username", "BullpugAlertsBot")
        
        return {
            "success": True,
            "code": code,
            "bot_username": bot_username,
            "bot_link": f"https://t.me/{bot_username}",
            "instructions": f"1. Open Telegram and message @{bot_username}\n2. Send the code: {code}\n3. Your account will be linked automatically!",
            "expires_in_minutes": 15
        }
    except Exception as e:
        logger.error(f"Generate link code error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-code")
async def verify_link_code(request: VerifyCodeRequest):
    """Verify a link code (called by webhook when user sends code to bot)."""
    try:
        # Find the code
        link_doc = await db.telegram_link_codes.find_one({
            "wallet_address": request.wallet_address,
            "code": request.code.upper(),
            "used": False
        })
        
        if not link_doc:
            return {"success": False, "error": "Invalid or expired code"}
        
        # Check expiration
        if datetime.now(timezone.utc).timestamp() > link_doc.get("expires_at", 0):
            return {"success": False, "error": "Code has expired"}
        
        return {"success": True, "message": "Code is valid"}
    except Exception as e:
        logger.error(f"Verify code error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/link-account")
async def link_telegram_account(wallet_address: str, chat_id: int, telegram_username: str = None):
    """Link a Telegram chat_id to a wallet address (internal use)."""
    try:
        await db.telegram_accounts.update_one(
            {"wallet_address": wallet_address},
            {
                "$set": {
                    "wallet_address": wallet_address,
                    "chat_id": chat_id,
                    "telegram_username": telegram_username,
                    "linked_at": datetime.now(timezone.utc).isoformat(),
                    "active": True,
                    "alerts_enabled": True
                }
            },
            upsert=True
        )
        
        # Mark the link code as used
        await db.telegram_link_codes.update_one(
            {"wallet_address": wallet_address, "used": False},
            {"$set": {"used": True}}
        )
        
        # Send welcome message
        welcome_msg = """
🐕 <b>Bullpug Alerts Connected!</b>

Your wallet is now linked. You'll receive:
• 🚨 Breakout alerts when tokens surge
• 📈 Price target notifications
• 💰 Position updates

<i>Trade smarter with Bullpug AI!</i>

Commands:
/status - Check connection status
/alerts - View active alerts
/disable - Pause notifications
/enable - Resume notifications
"""
        await send_telegram_message(chat_id, welcome_msg)
        
        return {"success": True, "message": "Account linked successfully"}
    except Exception as e:
        logger.error(f"Link account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{wallet_address}")
async def get_telegram_status(wallet_address: str):
    """Check if a wallet has Telegram linked."""
    try:
        account = await db.telegram_accounts.find_one(
            {"wallet_address": wallet_address, "active": True},
            {"_id": 0}
        )
        
        if account:
            return {
                "linked": True,
                "telegram_username": account.get("telegram_username"),
                "alerts_enabled": account.get("alerts_enabled", True),
                "linked_at": account.get("linked_at")
            }
        return {"linked": False}
    except Exception as e:
        logger.error(f"Get status error: {e}")
        return {"linked": False, "error": str(e)}


@router.post("/unlink/{wallet_address}")
async def unlink_telegram(wallet_address: str):
    """Unlink Telegram from a wallet."""
    try:
        result = await db.telegram_accounts.update_one(
            {"wallet_address": wallet_address},
            {"$set": {"active": False}}
        )
        
        return {
            "success": result.modified_count > 0,
            "message": "Telegram unlinked" if result.modified_count > 0 else "No linked account found"
        }
    except Exception as e:
        logger.error(f"Unlink error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle-alerts/{wallet_address}")
async def toggle_alerts(wallet_address: str, enabled: bool = True):
    """Enable or disable alerts for a wallet."""
    try:
        result = await db.telegram_accounts.update_one(
            {"wallet_address": wallet_address, "active": True},
            {"$set": {"alerts_enabled": enabled}}
        )
        
        return {
            "success": result.modified_count > 0,
            "alerts_enabled": enabled
        }
    except Exception as e:
        logger.error(f"Toggle alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBHOOK FOR RECEIVING TELEGRAM MESSAGES
# ============================================================================

@router.post("/webhook")
async def telegram_webhook(update: dict):
    """Handle incoming Telegram messages (for linking and commands)."""
    try:
        message = update.get("message", {})
        if not message:
            return {"ok": True}
        
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        username = message.get("from", {}).get("username", "")
        
        if not chat_id or not text:
            return {"ok": True}
        
        # Handle commands
        if text.startswith("/"):
            await handle_command(chat_id, text, username)
            return {"ok": True}
        
        # Check if this is a link code (6 alphanumeric characters)
        if len(text) == 6 and text.isalnum():
            code = text.upper()
            
            # Find the pending link code
            link_doc = await db.telegram_link_codes.find_one({
                "code": code,
                "used": False
            })
            
            if link_doc:
                # Check expiration
                if datetime.now(timezone.utc).timestamp() <= link_doc.get("expires_at", 0):
                    # Link the account
                    wallet_address = link_doc.get("wallet_address")
                    await link_telegram_account(wallet_address, chat_id, username)
                    return {"ok": True}
                else:
                    await send_telegram_message(
                        chat_id,
                        "❌ This code has expired. Please generate a new one from the Bullpug app."
                    )
            else:
                await send_telegram_message(
                    chat_id,
                    "❓ Invalid code. Please check and try again, or generate a new code from the Bullpug app."
                )
        else:
            # Unknown message
            await send_telegram_message(
                chat_id,
                "🐕 <b>Bullpug Alerts Bot</b>\n\nTo link your wallet, enter the 6-character code from the Bullpug app.\n\nCommands:\n/help - Show available commands"
            )
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": True}


async def handle_command(chat_id: int, command: str, username: str):
    """Handle bot commands."""
    cmd = command.split()[0].lower()
    
    if cmd == "/start":
        msg = """
🐕 <b>Welcome to Bullpug Alerts!</b>

Get real-time price alerts and breakout notifications directly in Telegram.

<b>To link your wallet:</b>
1. Go to the Bullpug AI Trading Bot
2. Open the Alerts tab
3. Click "Link Telegram"
4. Send the code here

<b>Commands:</b>
/status - Check connection
/alerts - View active alerts
/help - Show this message
"""
        await send_telegram_message(chat_id, msg)
    
    elif cmd == "/help":
        msg = """
🐕 <b>Bullpug Alerts - Commands</b>

<b>Account:</b>
/status - Check if your wallet is linked
/alerts - View your active price alerts
/disable - Pause alert notifications
/enable - Resume alert notifications
/unlink - Disconnect your wallet

<b>Trading:</b>
/trade - Open trading menu
/buy [SYMBOL] [SOL] - Buy a token
/sell [SYMBOL] [%] - Sell position
/positions - View open positions
/price [SYMBOL] - Check token price
/trending - View trending tokens

<b>Examples:</b>
<code>/buy BONK 0.5</code> - Buy 0.5 SOL of BONK
<code>/sell BONK 50</code> - Sell 50% of BONK
<code>/price SOL</code> - Check SOL price

<i>Need help? Visit bullpug.com</i>
"""
        await send_telegram_message(chat_id, msg)
    
    elif cmd == "/status":
        # Find account by chat_id
        account = await db.telegram_accounts.find_one(
            {"chat_id": chat_id, "active": True}
        )
        
        if account:
            wallet = account.get("wallet_address", "")[:8] + "..."
            alerts_status = "✅ Enabled" if account.get("alerts_enabled", True) else "⏸️ Paused"
            msg = f"""
✅ <b>Account Connected</b>

Wallet: <code>{wallet}</code>
Alerts: {alerts_status}
Linked: {account.get("linked_at", "Unknown")[:10]}
"""
        else:
            msg = "❌ No wallet linked. Please link your wallet from the Bullpug app."
        
        await send_telegram_message(chat_id, msg)
    
    elif cmd == "/alerts":
        account = await db.telegram_accounts.find_one(
            {"chat_id": chat_id, "active": True}
        )
        
        if not account:
            await send_telegram_message(chat_id, "❌ No wallet linked.")
            return
        
        wallet = account.get("wallet_address")
        alerts = await db.price_alerts.find(
            {"wallet_address": wallet, "active": True, "triggered": False},
            {"_id": 0}
        ).to_list(10)
        
        if alerts:
            msg = "📊 <b>Your Active Alerts</b>\n\n"
            for a in alerts:
                alert_type = "🔺" if "up" in a.get("alert_type", "") else "🔻"
                msg += f"{alert_type} <b>{a.get('symbol')}</b> - {a.get('alert_type')}\n"
            msg += f"\n<i>Total: {len(alerts)} alerts</i>"
        else:
            msg = "📭 No active alerts. Create alerts from the Bullpug Trading Bot!"
        
        await send_telegram_message(chat_id, msg)
    
    elif cmd == "/disable":
        result = await db.telegram_accounts.update_one(
            {"chat_id": chat_id, "active": True},
            {"$set": {"alerts_enabled": False}}
        )
        
        if result.modified_count > 0:
            await send_telegram_message(chat_id, "⏸️ Alerts paused. Use /enable to resume.")
        else:
            await send_telegram_message(chat_id, "❌ No linked account found.")
    
    elif cmd == "/enable":
        result = await db.telegram_accounts.update_one(
            {"chat_id": chat_id, "active": True},
            {"$set": {"alerts_enabled": True}}
        )
        
        if result.modified_count > 0:
            await send_telegram_message(chat_id, "✅ Alerts enabled! You'll receive notifications again.")
        else:
            await send_telegram_message(chat_id, "❌ No linked account found.")
    
    elif cmd == "/unlink":
        result = await db.telegram_accounts.update_one(
            {"chat_id": chat_id, "active": True},
            {"$set": {"active": False}}
        )
        
        if result.modified_count > 0:
            await send_telegram_message(chat_id, "👋 Wallet unlinked. You won't receive alerts anymore.")
        else:
            await send_telegram_message(chat_id, "❌ No linked account found.")
    
    elif cmd == "/trade":
        await handle_trade_command(chat_id, command)
    
    elif cmd == "/buy":
        await handle_buy_command(chat_id, command)
    
    elif cmd == "/sell":
        await handle_sell_command(chat_id, command)
    
    elif cmd == "/positions":
        await handle_positions_command(chat_id)
    
    elif cmd == "/price":
        await handle_price_command(chat_id, command)
    
    elif cmd == "/trending":
        await handle_trending_command(chat_id)
    
    else:
        await send_telegram_message(chat_id, "❓ Unknown command. Use /help to see available commands.")


# ============================================================================
# TRADING COMMANDS
# ============================================================================

async def handle_trade_command(chat_id: int, command: str):
    """Show trading menu with quick actions."""
    account = await db.telegram_accounts.find_one({"chat_id": chat_id, "active": True})
    
    if not account:
        await send_telegram_message(chat_id, "❌ No linked wallet. Please link your wallet from the Bullpug app first.")
        return
    
    msg = """
💹 <b>Bullpug Trading Menu</b>

<b>Quick Commands:</b>
• /buy [SYMBOL] [SOL_AMOUNT] - Buy a token
  Example: <code>/buy BONK 0.5</code>

• /sell [SYMBOL] [PERCENTAGE] - Sell a position
  Example: <code>/sell BONK 50</code> (sells 50%)

• /positions - View your open positions

• /price [SYMBOL] - Check current price
  Example: <code>/price SOL</code>

• /trending - View trending tokens

<b>Quick Buy Buttons:</b>
"""
    
    # Add inline keyboard for quick buys (we'll send as text commands for simplicity)
    msg += """
🟢 <code>/buy BONK 0.1</code>
🟢 <code>/buy WIF 0.1</code>
🟢 <code>/buy SOL 0.1</code>

⚠️ <i>Trading involves risk. Only trade what you can afford to lose.</i>
"""
    
    await send_telegram_message(chat_id, msg)


async def handle_buy_command(chat_id: int, command: str):
    """Handle buy command: /buy SYMBOL AMOUNT"""
    account = await db.telegram_accounts.find_one({"chat_id": chat_id, "active": True})
    
    if not account:
        await send_telegram_message(chat_id, "❌ No linked wallet. Please link your wallet first.")
        return
    
    parts = command.split()
    if len(parts) < 3:
        await send_telegram_message(
            chat_id, 
            "❌ Invalid format.\n\nUsage: <code>/buy SYMBOL SOL_AMOUNT</code>\nExample: <code>/buy BONK 0.5</code>"
        )
        return
    
    symbol = parts[1].upper()
    try:
        amount = float(parts[2])
        if amount < 0.01 or amount > 10:
            await send_telegram_message(chat_id, "❌ Amount must be between 0.01 and 10 SOL")
            return
    except ValueError:
        await send_telegram_message(chat_id, "❌ Invalid amount. Please enter a number.")
        return
    
    wallet_address = account.get("wallet_address")
    
    # Fetch current price
    await send_telegram_message(chat_id, f"🔄 Fetching price for {symbol}...")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Get token info from DexScreener
        try:
            response = await client.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": f"{symbol} solana"}
            )
            
            if response.status_code != 200:
                await send_telegram_message(chat_id, "❌ Failed to fetch price. Please try again.")
                return
            
            pairs = response.json().get("pairs", [])
            solana_pairs = [p for p in pairs if p.get("chainId") == "solana" and p.get("baseToken", {}).get("symbol", "").upper() == symbol]
            
            if not solana_pairs:
                await send_telegram_message(chat_id, f"❌ Token {symbol} not found on Solana DEXes.")
                return
            
            # Get the pair with highest liquidity
            best_pair = max(solana_pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
            current_price = float(best_pair.get("priceUsd", 0))
            token_address = best_pair.get("baseToken", {}).get("address", "")
            
            if not token_address:
                await send_telegram_message(chat_id, "❌ Token address not found.")
                return
            
            # Create a pending trade order
            order_id = str(uuid.uuid4())[:8]
            
            await db.telegram_pending_orders.insert_one({
                "order_id": order_id,
                "chat_id": chat_id,
                "wallet_address": wallet_address,
                "order_type": "buy",
                "symbol": symbol,
                "token_address": token_address,
                "amount_sol": amount,
                "price_at_order": current_price,
                "status": "pending_confirmation",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            # Send confirmation message
            msg = f"""
🛒 <b>Buy Order Preview</b>

Token: <b>{symbol}</b>
Amount: <b>{amount} SOL</b>
Price: <code>${current_price:.8f}</code>
Estimated tokens: ~{(amount * 180 / current_price):.2f} {symbol}

<a href="https://dexscreener.com/solana/{token_address}">📊 View Chart</a>

⚠️ To confirm this trade, you must approve it in the Bullpug app.

Order ID: <code>{order_id}</code>
<i>This order will expire in 5 minutes.</i>

To execute:
1. Open Bullpug AI Trading Bot
2. Go to Signals tab
3. Approve the pending order

Or reply <code>/confirm {order_id}</code> to queue for next app approval.
"""
            await send_telegram_message(chat_id, msg)
            
        except Exception as e:
            logger.error(f"Buy command error: {e}")
            await send_telegram_message(chat_id, f"❌ Error processing buy order: {str(e)[:100]}")


async def handle_sell_command(chat_id: int, command: str):
    """Handle sell command: /sell SYMBOL PERCENTAGE"""
    account = await db.telegram_accounts.find_one({"chat_id": chat_id, "active": True})
    
    if not account:
        await send_telegram_message(chat_id, "❌ No linked wallet. Please link your wallet first.")
        return
    
    parts = command.split()
    if len(parts) < 2:
        await send_telegram_message(
            chat_id, 
            "❌ Invalid format.\n\nUsage: <code>/sell SYMBOL [PERCENTAGE]</code>\nExample: <code>/sell BONK 50</code> (sells 50%)\n\nOmit percentage to sell 100%"
        )
        return
    
    symbol = parts[1].upper()
    percentage = 100  # Default to 100%
    
    if len(parts) >= 3:
        try:
            percentage = float(parts[2])
            if percentage < 1 or percentage > 100:
                await send_telegram_message(chat_id, "❌ Percentage must be between 1 and 100")
                return
        except ValueError:
            await send_telegram_message(chat_id, "❌ Invalid percentage. Please enter a number.")
            return
    
    wallet_address = account.get("wallet_address")
    
    # Check if user has a position in this token
    position = await db.ai_trader_positions.find_one({
        "wallet_address": wallet_address,
        "symbol": symbol
    })
    
    if not position:
        await send_telegram_message(chat_id, f"❌ You don't have an open position in {symbol}")
        return
    
    # Create pending sell order
    order_id = str(uuid.uuid4())[:8]
    
    await db.telegram_pending_orders.insert_one({
        "order_id": order_id,
        "chat_id": chat_id,
        "wallet_address": wallet_address,
        "order_type": "sell",
        "symbol": symbol,
        "token_address": position.get("token_mint"),
        "percentage": percentage,
        "position_amount": position.get("amount"),
        "entry_price": position.get("entry_price"),
        "status": "pending_confirmation",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    msg = f"""
💰 <b>Sell Order Preview</b>

Token: <b>{symbol}</b>
Selling: <b>{percentage}%</b> of position
Amount: ~{position.get('amount', 0) * percentage / 100:.6f} {symbol}
Entry Price: <code>${position.get('entry_price', 0):.8f}</code>

Order ID: <code>{order_id}</code>
<i>This order will expire in 5 minutes.</i>

⚠️ To confirm, approve in the Bullpug app or reply:
<code>/confirm {order_id}</code>
"""
    
    await send_telegram_message(chat_id, msg)


async def handle_positions_command(chat_id: int):
    """Show user's open positions."""
    account = await db.telegram_accounts.find_one({"chat_id": chat_id, "active": True})
    
    if not account:
        await send_telegram_message(chat_id, "❌ No linked wallet. Please link your wallet first.")
        return
    
    wallet_address = account.get("wallet_address")
    
    positions = await db.ai_trader_positions.find(
        {"wallet_address": wallet_address},
        {"_id": 0}
    ).to_list(20)
    
    if not positions:
        await send_telegram_message(chat_id, "📭 No open positions.\n\nUse /buy SYMBOL AMOUNT to open a position.")
        return
    
    msg = "📊 <b>Your Open Positions</b>\n\n"
    
    for pos in positions:
        symbol = pos.get("symbol", "???")
        amount = pos.get("amount", 0)
        entry_price = pos.get("entry_price", 0)
        
        msg += f"• <b>{symbol}</b>\n"
        msg += f"  Amount: {amount:.6f}\n"
        msg += f"  Entry: ${entry_price:.8f}\n"
        msg += f"  <code>/sell {symbol} 100</code> to close\n\n"
    
    msg += f"<i>Total: {len(positions)} positions</i>"
    
    await send_telegram_message(chat_id, msg)


async def handle_price_command(chat_id: int, command: str):
    """Check current price of a token."""
    parts = command.split()
    if len(parts) < 2:
        await send_telegram_message(
            chat_id, 
            "❌ Invalid format.\n\nUsage: <code>/price SYMBOL</code>\nExample: <code>/price BONK</code>"
        )
        return
    
    symbol = parts[1].upper()
    
    await send_telegram_message(chat_id, f"🔄 Fetching {symbol} price...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": f"{symbol} solana"}
            )
            
            if response.status_code != 200:
                await send_telegram_message(chat_id, "❌ Failed to fetch price.")
                return
            
            pairs = response.json().get("pairs", [])
            solana_pairs = [p for p in pairs if p.get("chainId") == "solana" and p.get("baseToken", {}).get("symbol", "").upper() == symbol]
            
            if not solana_pairs:
                await send_telegram_message(chat_id, f"❌ Token {symbol} not found on Solana.")
                return
            
            best_pair = max(solana_pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
            
            price = float(best_pair.get("priceUsd", 0))
            change_24h = float(best_pair.get("priceChange", {}).get("h24", 0) or 0)
            change_1h = float(best_pair.get("priceChange", {}).get("h1", 0) or 0)
            volume = float(best_pair.get("volume", {}).get("h24", 0) or 0)
            liquidity = float(best_pair.get("liquidity", {}).get("usd", 0) or 0)
            token_address = best_pair.get("baseToken", {}).get("address", "")
            
            emoji_24h = "🟢" if change_24h >= 0 else "🔴"
            emoji_1h = "📈" if change_1h >= 0 else "📉"
            
            msg = f"""
💰 <b>{symbol} Price</b>

Price: <code>${price:.8f}</code>

{emoji_1h} 1H: {'+' if change_1h >= 0 else ''}{change_1h:.2f}%
{emoji_24h} 24H: {'+' if change_24h >= 0 else ''}{change_24h:.2f}%

📊 Volume (24h): ${volume:,.0f}
💧 Liquidity: ${liquidity:,.0f}

<a href="https://dexscreener.com/solana/{token_address}">📊 View Chart</a>

<b>Quick Trade:</b>
<code>/buy {symbol} 0.1</code>
"""
            
            await send_telegram_message(chat_id, msg)
            
        except Exception as e:
            logger.error(f"Price command error: {e}")
            await send_telegram_message(chat_id, "❌ Error fetching price. Please try again.")


async def handle_trending_command(chat_id: int):
    """Show trending tokens on Solana."""
    await send_telegram_message(chat_id, "🔄 Fetching trending tokens...")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": "solana meme trending"}
            )
            
            if response.status_code != 200:
                await send_telegram_message(chat_id, "❌ Failed to fetch trending tokens.")
                return
            
            pairs = response.json().get("pairs", [])
            solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
            
            # Sort by 24h volume
            solana_pairs.sort(key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0), reverse=True)
            
            seen_symbols = set()
            trending = []
            
            for pair in solana_pairs[:20]:
                symbol = pair.get("baseToken", {}).get("symbol", "").upper()
                if symbol in seen_symbols or symbol in ["USDC", "USDT", "SOL", "WSOL"]:
                    continue
                seen_symbols.add(symbol)
                
                price = float(pair.get("priceUsd", 0) or 0)
                change_24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
                volume = float(pair.get("volume", {}).get("h24", 0) or 0)
                
                if volume > 10000:  # Minimum volume filter
                    trending.append({
                        "symbol": symbol,
                        "price": price,
                        "change_24h": change_24h,
                        "volume": volume
                    })
                
                if len(trending) >= 10:
                    break
            
            if not trending:
                await send_telegram_message(chat_id, "❌ No trending tokens found.")
                return
            
            msg = "🔥 <b>Trending on Solana</b>\n\n"
            
            for i, t in enumerate(trending, 1):
                emoji = "🟢" if t["change_24h"] >= 0 else "🔴"
                hot = "🔥" if t["change_24h"] > 50 else ""
                
                msg += f"{i}. <b>{t['symbol']}</b> {hot}\n"
                msg += f"   ${t['price']:.6f} {emoji} {'+' if t['change_24h'] >= 0 else ''}{t['change_24h']:.1f}%\n"
                msg += f"   Vol: ${t['volume']:,.0f}\n\n"
            
            msg += "<b>Quick Buy:</b>\n"
            for t in trending[:3]:
                msg += f"<code>/buy {t['symbol']} 0.1</code>\n"
            
            await send_telegram_message(chat_id, msg)
            
        except Exception as e:
            logger.error(f"Trending command error: {e}")
            await send_telegram_message(chat_id, "❌ Error fetching trending tokens.")


# ============================================================================
# ALERT NOTIFICATION FUNCTIONS (Called from ai_trader.py)
# ============================================================================

async def send_breakout_alert(wallet_address: str, alert_data: dict):
    """Send a breakout alert to Telegram if the user has it linked."""
    try:
        account = await db.telegram_accounts.find_one({
            "wallet_address": wallet_address,
            "active": True,
            "alerts_enabled": True
        })
        
        if not account:
            return False
        
        chat_id = account.get("chat_id")
        if not chat_id:
            return False
        
        symbol = alert_data.get("symbol", "???")
        trigger_reason = alert_data.get("trigger_reason", "")
        current_price = alert_data.get("current_price", 0)
        alert_type = alert_data.get("alert_type", "breakout_up")
        
        # Format message
        emoji = "🚀" if "up" in alert_type else "📉"
        
        msg = f"""
{emoji} <b>ALERT: {symbol}</b>

{trigger_reason}

💰 Current Price: <code>${current_price:.8f}</code>

<a href="https://dexscreener.com/solana/{alert_data.get('token_mint', '')}">📊 View Chart</a>

<i>Trade on Bullpug AI Bot</i>
"""
        
        return await send_telegram_message(chat_id, msg)
    except Exception as e:
        logger.error(f"Send breakout alert error: {e}")
        return False


async def send_price_target_alert(wallet_address: str, symbol: str, current_price: float, target_price: float, direction: str):
    """Send a price target reached alert."""
    try:
        account = await db.telegram_accounts.find_one({
            "wallet_address": wallet_address,
            "active": True,
            "alerts_enabled": True
        })
        
        if not account:
            return False
        
        chat_id = account.get("chat_id")
        if not chat_id:
            return False
        
        emoji = "🎯" if direction == "above" else "⚠️"
        direction_text = "reached" if direction == "above" else "dropped to"
        
        msg = f"""
{emoji} <b>Price Target Hit!</b>

<b>{symbol}</b> {direction_text} your target

🎯 Target: <code>${target_price:.8f}</code>
💰 Current: <code>${current_price:.8f}</code>

<i>Time to take action!</i>
"""
        
        return await send_telegram_message(chat_id, msg)
    except Exception as e:
        logger.error(f"Send price target alert error: {e}")
        return False
