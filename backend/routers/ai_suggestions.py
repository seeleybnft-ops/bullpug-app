"""AI-powered suggestions for trading insights using LLM."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import httpx
import os
import uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from emergentintegrations.llm.chat import LlmChat, UserMessage
from utils.database import db

load_dotenv()

router = APIRouter(prefix="/ai-suggestions", tags=["ai-suggestions"])
logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


class SimulationContext(BaseModel):
    token_symbol: str
    entry_price: float
    current_price: Optional[float] = None
    volatility: float
    simulated_outcomes: Dict  # Results from Monte Carlo
    wallet_address: Optional[str] = None


class JournalContext(BaseModel):
    wallet_address: str


async def get_live_crypto_price(symbol: str) -> Optional[Dict]:
    """Fetch live price from CoinGecko."""
    try:
        symbol_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
            "DOGE": "dogecoin", "SHIB": "shiba-inu", "PEPE": "pepe",
            "BULLPUG": "solana",
        }
        
        coin_id = symbol_map.get(symbol.upper(), symbol.lower())
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                if coin_id in data:
                    return {
                        "price": data[coin_id].get("usd", 0),
                        "change_24h": data[coin_id].get("usd_24h_change", 0)
                    }
    except Exception as e:
        logger.error(f"Error fetching price: {e}")
    
    return None


async def get_user_journal_summary(wallet_address: str) -> Dict:
    """Get summary of user's journal entries."""
    try:
        trades = await db.journal_trades.find(
            {"wallet_address": wallet_address},
            {"_id": 0}
        ).sort("entry_date", -1).limit(20).to_list(20)
        
        if not trades:
            return {"has_trades": False}
        
        total_pnl = sum(t.get("realized_pnl", 0) or t.get("pnl", 0) for t in trades if t.get("realized_pnl") or t.get("pnl"))
        win_trades = len([t for t in trades if (t.get("realized_pnl", 0) or t.get("pnl", 0)) > 0])
        loss_trades = len([t for t in trades if (t.get("realized_pnl", 0) or t.get("pnl", 0)) < 0])
        
        tokens = list(set(t.get("token_symbol", t.get("asset", "")).upper() for t in trades if t.get("token_symbol") or t.get("asset")))
        recent_notes = [t.get("notes", t.get("lessons", "")) for t in trades[:5] if t.get("notes") or t.get("lessons")]
        
        recent_trades_summary = []
        for t in trades[:5]:
            recent_trades_summary.append({
                "asset": t.get("asset", t.get("token_symbol", "?")),
                "type": t.get("trade_type", "?"),
                "pnl": t.get("pnl", t.get("realized_pnl", 0)),
                "strategy": t.get("strategy", "?"),
                "grade": t.get("trade_grade", "?")
            })
        
        return {
            "has_trades": True,
            "total_trades": len(trades),
            "total_pnl": total_pnl,
            "win_rate": (win_trades / len(trades) * 100) if trades else 0,
            "tokens_traded": tokens[:5],
            "recent_notes": recent_notes,
            "recent_trades": recent_trades_summary,
            "win_trades": win_trades,
            "loss_trades": loss_trades,
        }
    except Exception as e:
        logger.error(f"Error getting journal summary: {e}")
        return {"has_trades": False}


async def generate_llm_exit_suggestion(context: SimulationContext, journal_summary: Dict, live_price: Dict) -> str:
    """Generate AI suggestion using LLM based on simulation results."""
    
    if not EMERGENT_LLM_KEY:
        logger.warning("No EMERGENT_LLM_KEY found, using fallback")
        return generate_fallback_exit_suggestion(context, journal_summary, live_price)
    
    try:
        outcomes = context.simulated_outcomes
        prob_profit = outcomes.get("probability_profit", 50)
        median_price = outcomes.get("median_final_price", context.entry_price)
        pnl_percentiles = outcomes.get("pnl_percentiles", {})
        
        current_price = live_price.get("price", context.entry_price) if live_price else context.entry_price
        change_24h = live_price.get("change_24h", 0) if live_price else 0
        
        journal_context = ""
        if journal_summary.get("has_trades"):
            journal_context = f"""
User's Trading History:
- Total trades: {journal_summary.get('total_trades', 0)}
- Win rate: {journal_summary.get('win_rate', 0):.1f}%
- Total P&L: ${journal_summary.get('total_pnl', 0):.2f}
- Recent notes: {', '.join(journal_summary.get('recent_notes', [])[:2])}
"""
        
        prompt = f"""You are Bullpug AI, a friendly and knowledgeable crypto trading assistant. Analyze this Monte Carlo simulation and provide actionable trading insights.

**Simulation Data:**
- Token: {context.token_symbol}
- Entry Price: ${context.entry_price}
- Current Live Price: ${current_price} ({change_24h:+.1f}% 24h)
- Volatility: {context.volatility * 100:.0f}%
- Probability of Profit: {prob_profit}%
- Median Simulated Price: ${median_price}
- P&L Percentiles: 5th: {pnl_percentiles.get('p5', 'N/A')}%, 95th: {pnl_percentiles.get('p95', 'N/A')}%
{journal_context}

Provide a personalized trading suggestion in 150-200 words. Include:
1. A friendly greeting with an emoji
2. Your assessment of the simulation results (bullish/bearish/neutral)
3. Key risk factors to consider
4. One actionable tip based on the data
5. End with an encouraging note

Use markdown formatting with **bold** for emphasis. Be conversational but data-driven."""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"exit-sim-{uuid.uuid4()}",
            system_message="You are Bullpug AI, a friendly crypto trading assistant that provides data-driven insights while being encouraging and supportive."
        ).with_model("openai", "gpt-4o")
        
        response = await chat.send_message(UserMessage(text=prompt))
        return response
        
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return generate_fallback_exit_suggestion(context, journal_summary, live_price)


async def generate_llm_journal_insight(journal_summary: Dict, holdings_overnight: List[Dict], language: str = "en") -> str:
    """Generate daily insight using LLM for journal dashboard."""
    
    if not EMERGENT_LLM_KEY:
        logger.warning("No EMERGENT_LLM_KEY found, using fallback")
        return generate_fallback_journal_insight(journal_summary, holdings_overnight)
    
    try:
        lang_instruction = f"Respond entirely in {language} language." if language != "en" else ""
        
        if not journal_summary.get("has_trades"):
            welcome_prompt = f"""Generate a welcoming message for a new user of a trading journal app.
{lang_instruction}
Include:
- A warm greeting with emoji
- Brief list of features they can unlock by logging trades
- Encouraging call to action to log their first trade
Keep it under 100 words. Use markdown formatting."""

            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"journal-welcome-{uuid.uuid4()}"
            ).with_model("openai", "gpt-4o")
            
            return await chat.send_message(UserMessage(text=welcome_prompt))

        hour = datetime.now().hour
        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"
        
        holdings_str = ""
        if holdings_overnight:
            holdings_str = "\nOvernight Market Changes:\n"
            for h in holdings_overnight[:5]:
                holdings_str += f"- {h.get('symbol', '?')}: {h.get('change_24h', 0):+.1f}%\n"
        
        recent_trades_str = ""
        if journal_summary.get("recent_trades"):
            recent_trades_str = "\nRecent Trades:\n"
            for t in journal_summary["recent_trades"][:3]:
                recent_trades_str += f"- {t['asset']}: {t['type']}, P&L: ${t['pnl']}, Grade: {t['grade']}\n"
        
        prompt = f"""You are Bullpug AI, a supportive trading coach. Generate a daily insight for a trader's journal dashboard.

**Trader's Data:**
- Time: {time_greeting}
- Total Trades: {journal_summary.get('total_trades', 0)}
- Win Rate: {journal_summary.get('win_rate', 0):.1f}%
- Total P&L: ${journal_summary.get('total_pnl', 0):.2f}
- Winning Trades: {journal_summary.get('win_trades', 0)}
- Losing Trades: {journal_summary.get('loss_trades', 0)}
- Tokens Traded: {', '.join(journal_summary.get('tokens_traded', []))}
{holdings_str}
{recent_trades_str}
Recent Notes/Lessons: {', '.join(journal_summary.get('recent_notes', [])[:2]) or 'None recorded'}

{lang_instruction}

Generate a personalized 100-150 word daily insight that includes:
1. Time-appropriate greeting with emoji
2. Quick portfolio/performance summary
3. One observation about their trading patterns
4. Today's actionable focus area
5. Motivational closing

Use markdown with **bold** for key points. Be encouraging but honest about areas for improvement."""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"journal-daily-{uuid.uuid4()}",
            system_message="You are Bullpug AI, a supportive trading coach that helps traders improve through data-driven insights and positive reinforcement."
        ).with_model("openai", "gpt-4o")
        
        response = await chat.send_message(UserMessage(text=prompt))
        return response
        
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return generate_fallback_journal_insight(journal_summary, holdings_overnight)


def generate_fallback_exit_suggestion(context: SimulationContext, journal_summary: Dict, live_price: Dict) -> str:
    """Fallback suggestion when LLM is unavailable."""
    import random
    
    outcomes = context.simulated_outcomes
    prob_profit = outcomes.get("probability_profit", 50)
    
    change_24h = live_price.get("change_24h", 0) if live_price else 0
    
    if change_24h > 5:
        market_mood = "bullish momentum"
    elif change_24h < -5:
        market_mood = "bearish pressure"
    else:
        market_mood = "sideways consolidation"
    
    suggestions = []
    greetings = [
        f"Hey there! 👋 Based on your {context.token_symbol} simulation...",
        f"I've analyzed your {context.token_symbol} setup! 📊",
    ]
    suggestions.append(random.choice(greetings))
    
    suggestions.append(f"\n\n**Market Vibe:** {context.token_symbol} showing {market_mood} ({change_24h:+.1f}% 24h)")
    
    if prob_profit > 65:
        suggestions.append(f"\n\n**Outlook:** Looking promising! 🟢 {prob_profit:.0f}% profit probability.")
    elif prob_profit > 45:
        suggestions.append(f"\n\n**Outlook:** Neutral zone 🟡 {prob_profit:.0f}% profit probability.")
    else:
        suggestions.append(f"\n\n**Outlook:** Caution advised 🔴 Only {prob_profit:.0f}% profit probability.")
    
    tips = [
        "\n\n💡 **Tip:** Consider setting a stop-loss at your max acceptable loss!",
        "\n\n💡 **Tip:** Scale in/out to manage risk better.",
    ]
    suggestions.append(random.choice(tips))
    
    return "".join(suggestions)


def generate_fallback_journal_insight(journal_summary: Dict, holdings_overnight: List[Dict]) -> str:
    """Fallback insight when LLM is unavailable."""
    import random
    
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning! ☀️"
    elif hour < 17:
        greeting = "Good afternoon! 👋"
    else:
        greeting = "Good evening! 🌙"
    
    insights = [f"{greeting} Here's your daily trading pulse:\n"]
    
    if not journal_summary.get("has_trades"):
        insights.append("\n📝 **No trades logged yet!** Start tracking to get personalized insights.")
        return "".join(insights)
    
    total_pnl = journal_summary.get("total_pnl", 0)
    win_rate = journal_summary.get("win_rate", 0)
    
    if total_pnl > 0:
        insights.append(f"\n📈 **Portfolio Status:** Up ${total_pnl:.2f}! Great work!")
    else:
        insights.append(f"\n📉 **Portfolio Status:** Down ${abs(total_pnl):.2f}. Focus on the process!")
    
    if win_rate > 55:
        insights.append(f"\n\n🎯 **Win Rate:** {win_rate:.0f}% - You're reading the market well!")
    else:
        insights.append(f"\n\n🎯 **Win Rate:** {win_rate:.0f}% - Consider reviewing entry criteria.")
    
    suggestions = [
        "\n\n**Today's Focus:** Review open positions and set clear exit targets.",
        "\n\n**Today's Focus:** Journal your recent trades - what worked, what didn't?",
    ]
    insights.append(random.choice(suggestions))
    
    return "".join(insights)


@router.post("/exit-simulator")
async def get_exit_simulation_suggestion(context: SimulationContext):
    """Get AI suggestion after running exit simulation."""
    
    live_price = await get_live_crypto_price(context.token_symbol)
    
    journal_summary = {"has_trades": False}
    if context.wallet_address:
        journal_summary = await get_user_journal_summary(context.wallet_address)
    
    suggestion = await generate_llm_exit_suggestion(context, journal_summary, live_price)
    
    return {
        "suggestion": suggestion,
        "live_price": live_price,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "powered_by": "GPT-4o" if EMERGENT_LLM_KEY else "Fallback"
    }


@router.get("/journal-daily/{wallet_address}")
async def get_journal_daily_insight(wallet_address: str, language: str = "en"):
    """Get daily insight for journal dashboard."""
    
    journal_summary = await get_user_journal_summary(wallet_address)
    
    holdings_overnight = []
    if journal_summary.get("tokens_traded"):
        for token in journal_summary["tokens_traded"][:5]:
            price_data = await get_live_crypto_price(token)
            if price_data:
                holdings_overnight.append({
                    "symbol": token,
                    "change_24h": price_data.get("change_24h", 0),
                    "price": price_data.get("price", 0)
                })
    
    insight = await generate_llm_journal_insight(journal_summary, holdings_overnight, language)
    
    return {
        "insight": insight,
        "holdings_changes": holdings_overnight,
        "journal_stats": journal_summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "powered_by": "GPT-4o" if EMERGENT_LLM_KEY else "Fallback"
    }


class ChatMessage(BaseModel):
    wallet_address: str
    message: str
    language: str = "en"
    chat_history: List[Dict] = []


@router.post("/journal-chat")
async def journal_chat(chat: ChatMessage):
    """Interactive chat with AI trading assistant."""
    
    if not EMERGENT_LLM_KEY:
        return {"response": "AI chat is currently unavailable. Please try again later."}
    
    try:
        journal_summary = await get_user_journal_summary(chat.wallet_address)
        
        # Build context from journal
        context_info = ""
        if journal_summary.get("has_trades"):
            context_info = f"""
User's Trading Profile:
- Total Trades: {journal_summary.get('total_trades', 0)}
- Win Rate: {journal_summary.get('win_rate', 0):.1f}%
- Total P&L: ${journal_summary.get('total_pnl', 0):.2f}
- Tokens Traded: {', '.join(journal_summary.get('tokens_traded', []))}
"""
        
        # Build chat history for context
        history_text = ""
        if chat.chat_history:
            for msg in chat.chat_history[-5:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_text += f"{role}: {msg.get('content', '')}\n"
        
        language_instruction = f"Respond in {chat.language} language." if chat.language != "en" else ""
        
        prompt = f"""You are Bullpug AI, a friendly and knowledgeable crypto trading assistant for the Bullpug memecoin community.

{context_info}

Recent conversation:
{history_text}

User's question: {chat.message}

{language_instruction}

Provide a helpful, conversational response. Be friendly and supportive. If discussing trades or strategy, be clear this is not financial advice. Keep response concise (100-200 words max)."""

        llm_chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"journal-chat-{chat.wallet_address[:8]}-{uuid.uuid4()}",
            system_message="You are Bullpug AI, a friendly crypto trading assistant."
        ).with_model("openai", "gpt-4o")
        
        response = await llm_chat.send_message(UserMessage(text=prompt))
        return {"response": response}
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"response": "I encountered an error. Please try again!"}


@router.get("/journal-holdings/{wallet_address}")
async def get_journal_holdings(wallet_address: str, language: str = "en"):
    """Get user's holdings from journal with AI suggestions."""
    
    try:
        # Get unique assets from journal trades
        trades = await db.journal_trades.find(
            {"wallet_address": wallet_address},
            {"_id": 0, "asset": 1, "token_symbol": 1, "quantity": 1, "trade_type": 1}
        ).to_list(100)
        
        # Calculate current holdings (simplified - tracks buys/sells)
        holdings_map = {}
        for trade in trades:
            symbol = trade.get("asset", trade.get("token_symbol", "?")).upper()
            qty = trade.get("quantity", 0)
            trade_type = trade.get("trade_type", "buy").lower()
            
            if symbol not in holdings_map:
                holdings_map[symbol] = {"symbol": symbol, "amount": 0}
            
            if trade_type in ["buy", "long"]:
                holdings_map[symbol]["amount"] += qty
            elif trade_type in ["sell", "short"]:
                holdings_map[symbol]["amount"] -= qty
        
        # Filter positive holdings and get prices
        holdings = []
        for symbol, data in holdings_map.items():
            if data["amount"] > 0:
                price_info = await get_live_crypto_price(symbol)
                holdings.append({
                    "symbol": symbol,
                    "amount": data["amount"],
                    "price": price_info.get("price", 0) if price_info else 0,
                    "value": data["amount"] * (price_info.get("price", 0) if price_info else 0),
                    "change_24h": price_info.get("change_24h", 0) if price_info else 0
                })
        
        # Generate AI suggestions for holdings
        suggestions = []
        if holdings and EMERGENT_LLM_KEY:
            try:
                holdings_text = "\n".join([
                    f"- {h['symbol']}: {h['amount']} tokens, ${h['value']:.2f}, {h['change_24h']:+.1f}% 24h"
                    for h in holdings[:5]
                ])
                
                lang_instruction = f"Respond in {language}." if language != "en" else ""
                
                prompt = f"""Analyze these crypto holdings and give 2-3 brief, actionable suggestions:

{holdings_text}

{lang_instruction}
Keep each suggestion to one sentence. Focus on risk management and position sizing."""

                llm_chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"holdings-{uuid.uuid4()}"
                ).with_model("openai", "gpt-4o")
                
                response = await llm_chat.send_message(UserMessage(text=prompt))
                suggestions = [s.strip() for s in response.split("\n") if s.strip() and len(s.strip()) > 10][:3]
            except Exception as e:
                logger.error(f"Holdings suggestion error: {e}")
                # Fallback suggestions based on holdings
                if holdings:
                    top_holding = holdings[0]
                    suggestions = [
                        f"Consider setting stop-losses for your {top_holding['symbol']} position to manage risk.",
                        "Diversify across multiple assets to reduce portfolio volatility.",
                        "Track your entry prices and set clear profit targets."
                    ]
        elif holdings:
            # Provide default suggestions when no LLM available
            top_holding = holdings[0]
            suggestions = [
                f"Your largest position is {top_holding['symbol']} - consider if this aligns with your risk tolerance.",
                "Set price alerts for significant moves in your holdings.",
                "Review positions regularly and adjust based on market conditions."
            ]
        else:
            # Suggestions for users with no holdings
            suggestions = [
                "Start by logging your first trade to track your portfolio performance.",
                "Use the Trading Journal to analyze your trading patterns over time.",
                "Check the Top Picks tab for trending coins with strong fundamentals."
            ]
        
        return {
            "holdings": sorted(holdings, key=lambda x: x["value"], reverse=True)[:10],
            "suggestions": suggestions,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Holdings error: {e}")
        return {"holdings": [], "suggestions": []}


@router.get("/coin-recommendations")
async def get_coin_recommendations(language: str = "en"):
    """Get top 3 Solana memecoin recommendations from specific platforms."""
    
    # Allowed platforms for Solana memecoins
    ALLOWED_PLATFORMS = [
        "pumpfun", "pump.fun", "pump",
        "raydium",
        "orca",
        "meteora",
        "moonshot", "moonit",
        "launchlab",
        "blowfish", "blowfishbot",
        "bags"
    ]
    
    # Platform display names
    PLATFORM_DISPLAY = {
        "pumpfun": "Pump.fun",
        "pump.fun": "Pump.fun",
        "pump": "Pump.fun",
        "raydium": "Raydium",
        "orca": "Orca",
        "meteora": "Meteora",
        "moonshot": "Moonit",
        "moonit": "Moonit",
        "launchlab": "LaunchLab",
        "blowfish": "Blowfishbot",
        "blowfishbot": "Blowfishbot",
        "bags": "Bags"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Fetch trending Solana tokens from DexScreener
            resp = await client.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": "solana"},
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                timeout=15.0
            )
            
            if resp.status_code != 200:
                raise Exception(f"DexScreener API error: {resp.status_code}")
            
            data = resp.json()
            pairs = data.get("pairs", [])
            
            # Filter for Solana chain and allowed platforms
            qualified_coins = []
            seen_symbols = set()
            
            for pair in pairs:
                # Must be Solana chain
                if pair.get("chainId") != "solana":
                    continue
                
                # Get DEX/platform info
                dex_id = (pair.get("dexId", "") or "").lower()
                
                # Check if from allowed platform
                platform_match = None
                for allowed in ALLOWED_PLATFORMS:
                    if allowed in dex_id:
                        platform_match = PLATFORM_DISPLAY.get(allowed, allowed.title())
                        break
                
                if not platform_match:
                    continue
                
                # Get token info
                base_token = pair.get("baseToken", {})
                symbol = base_token.get("symbol", "?").upper()
                
                # Skip duplicates and stablecoins
                if symbol in seen_symbols:
                    continue
                if symbol in ["USDC", "USDT", "SOL", "WSOL", "USD"]:
                    continue
                
                seen_symbols.add(symbol)
                
                # Get metrics
                volume_24h = float(pair.get("volume", {}).get("h24", 0) or 0)
                liquidity_usd = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                price_usd = float(pair.get("priceUsd", 0) or 0)
                price_change_24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
                fdv = float(pair.get("fdv", 0) or 0)
                
                # Criteria: Volume > 50k, has liquidity
                if volume_24h < 50000:
                    continue
                if liquidity_usd < 10000:
                    continue
                
                qualified_coins.append({
                    "symbol": symbol,
                    "name": base_token.get("name", symbol),
                    "price": price_usd,
                    "change_24h": price_change_24h,
                    "volume_24h": volume_24h,
                    "liquidity_usd": liquidity_usd,
                    "fdv": fdv,
                    "liquidity_locked": liquidity_usd > 100000,
                    "bonded": fdv > 500000,
                    "platform": platform_match,
                    "pair_address": pair.get("pairAddress", ""),
                    "token_address": base_token.get("address", ""),
                    "reason": "",
                    "_score": 0
                })
            
            # Score and sort coins
            for coin in qualified_coins:
                coin["_score"] = (
                    (coin["volume_24h"] / 100000) * 0.35 +
                    (max(0, coin["change_24h"]) * 0.25) +
                    (coin["liquidity_usd"] / 50000) * 0.2 +
                    (1 if coin["liquidity_locked"] else 0) * 10 +
                    (1 if coin["bonded"] else 0) * 10
                )
            
            qualified_coins.sort(key=lambda x: x["_score"], reverse=True)
            top_coins = qualified_coins[:3]
            
            # Generate AI reasons for each
            if EMERGENT_LLM_KEY and top_coins:
                try:
                    lang_instruction = f"Respond in {language}." if language != "en" else ""
                    
                    for coin in top_coins:
                        prompt = f"""Give ONE sentence (max 25 words) explaining why {coin['symbol']} ({coin['name']}) on {coin['platform']} is worth watching.
Volume: ${coin['volume_24h']:,.0f}, Liquidity: ${coin['liquidity_usd']:,.0f}, 24h change: {coin['change_24h']:+.1f}%
{lang_instruction}
Focus on the metrics and momentum. This is a Solana memecoin."""

                        llm_chat = LlmChat(
                            api_key=EMERGENT_LLM_KEY,
                            session_id=f"rec-{uuid.uuid4()}"
                        ).with_model("openai", "gpt-4o")
                        
                        reason = await llm_chat.send_message(UserMessage(text=prompt))
                        coin["reason"] = reason.strip()[:150]
                        
                except Exception as e:
                    logger.error(f"Recommendation reason error: {e}")
                    for coin in top_coins:
                        coin["reason"] = f"Strong volume ${coin['volume_24h']/1000:.0f}K on {coin['platform']} with {coin['change_24h']:+.1f}% momentum."
            else:
                for coin in top_coins:
                    coin["reason"] = f"Strong volume ${coin['volume_24h']/1000:.0f}K on {coin['platform']} with {coin['change_24h']:+.1f}% momentum."
            
            # Clean up response
            for coin in top_coins:
                coin.pop("_score", None)
                coin.pop("pair_address", None)
                coin.pop("token_address", None)
            
            return {
                "recommendations": top_coins,
                "source": "DexScreener",
                "platforms": ["Pump.fun", "Raydium", "Orca", "Meteora", "Moonit", "LaunchLab", "Blowfishbot", "Bags"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "disclaimer": "Not financial advice. Always do your own research. Memecoins are highly volatile."
            }
        
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        # Return fallback Solana memecoin recommendations
        fallback_coins = [
            {
                "symbol": "BONK",
                "name": "Bonk",
                "price": 0.000025,
                "change_24h": 8.5,
                "volume_24h": 150000000,
                "liquidity_usd": 5000000,
                "liquidity_locked": True,
                "bonded": True,
                "platform": "Raydium",
                "reason": "Leading Solana memecoin with strong community and deep liquidity on Raydium."
            },
            {
                "symbol": "WIF",
                "name": "dogwifhat",
                "price": 2.50,
                "change_24h": 5.2,
                "volume_24h": 200000000,
                "liquidity_usd": 8000000,
                "liquidity_locked": True,
                "bonded": True,
                "platform": "Raydium",
                "reason": "Top Solana meme with massive volume and established market presence."
            },
            {
                "symbol": "POPCAT",
                "name": "Popcat",
                "price": 1.20,
                "change_24h": 12.3,
                "volume_24h": 80000000,
                "liquidity_usd": 3000000,
                "liquidity_locked": True,
                "bonded": True,
                "platform": "Raydium",
                "reason": "Viral memecoin with consistent volume and strong holder base."
            }
        ]
        return {
            "recommendations": fallback_coins,
            "source": "Fallback",
            "platforms": ["Pump.fun", "Raydium", "Orca", "Meteora", "Moonit", "LaunchLab", "Blowfishbot", "Bags"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "Not financial advice. Always do your own research. Memecoins are highly volatile.",
            "is_fallback": True
        }
