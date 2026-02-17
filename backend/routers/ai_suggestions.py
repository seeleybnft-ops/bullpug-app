"""AI-powered suggestions for trading insights."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import httpx
from datetime import datetime, timezone, timedelta
import random

from utils.database import db

router = APIRouter(prefix="/ai-suggestions", tags=["ai-suggestions"])
logger = logging.getLogger(__name__)


class SimulationContext(BaseModel):
    token_symbol: str
    entry_price: float
    current_price: Optional[float] = None
    volatility: float
    simulated_outcomes: Dict  # Results from Monte Carlo
    wallet_address: Optional[str] = None


class JournalContext(BaseModel):
    wallet_address: str


async def get_live_crypto_price(symbol: str) -> Optional[float]:
    """Fetch live price from CoinGecko."""
    try:
        # Map common symbols to CoinGecko IDs
        symbol_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
            "DOGE": "dogecoin", "SHIB": "shiba-inu", "PEPE": "pepe",
            "BULLPUG": "solana",  # Placeholder - use SOL as proxy
        }
        
        coin_id = symbol_map.get(symbol.upper(), symbol.lower())
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"}
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
        # Get recent trades
        trades = await db.journal_trades.find(
            {"wallet_address": wallet_address},
            {"_id": 0}
        ).sort("entry_date", -1).limit(20).to_list(20)
        
        if not trades:
            return {"has_trades": False}
        
        # Calculate stats
        total_pnl = sum(t.get("realized_pnl", 0) for t in trades if t.get("realized_pnl"))
        win_trades = len([t for t in trades if t.get("realized_pnl", 0) > 0])
        loss_trades = len([t for t in trades if t.get("realized_pnl", 0) < 0])
        
        # Get unique tokens
        tokens = list(set(t.get("token_symbol", "").upper() for t in trades if t.get("token_symbol")))
        
        # Recent sentiment
        recent_notes = [t.get("notes", "") for t in trades[:5] if t.get("notes")]
        
        return {
            "has_trades": True,
            "total_trades": len(trades),
            "total_pnl": total_pnl,
            "win_rate": (win_trades / len(trades) * 100) if trades else 0,
            "tokens_traded": tokens[:5],
            "recent_notes": recent_notes,
            "avg_hold_time": "N/A",  # Could calculate if exit_date available
        }
    except Exception as e:
        logger.error(f"Error getting journal summary: {e}")
        return {"has_trades": False}


def generate_exit_suggestion(context: SimulationContext, journal_summary: Dict, live_price: Dict) -> str:
    """Generate AI-like suggestion based on simulation results."""
    
    outcomes = context.simulated_outcomes
    median_price = outcomes.get("median_final_price", context.entry_price)
    p5 = outcomes.get("pnl_percentiles", {}).get("p5", 0)
    p95 = outcomes.get("pnl_percentiles", {}).get("p95", 0)
    prob_profit = outcomes.get("probability_profit", 50)
    
    current = live_price.get("price", context.entry_price) if live_price else context.entry_price
    change_24h = live_price.get("change_24h", 0) if live_price else 0
    
    # Determine market condition
    if change_24h > 5:
        market_mood = "bullish momentum"
    elif change_24h < -5:
        market_mood = "bearish pressure"
    else:
        market_mood = "sideways consolidation"
    
    # Volatility assessment
    if context.volatility > 1.0:
        vol_assessment = "extremely volatile"
    elif context.volatility > 0.6:
        vol_assessment = "highly volatile"
    elif context.volatility > 0.3:
        vol_assessment = "moderately volatile"
    else:
        vol_assessment = "relatively stable"
    
    # Build suggestion
    suggestions = []
    
    # Opening friendly greeting
    greetings = [
        f"Hey there! 👋 Based on your {context.token_symbol} simulation...",
        f"I've crunched the numbers on your {context.token_symbol} position! 📊",
        f"Here's my take on your {context.token_symbol} trade setup... 🎯",
    ]
    suggestions.append(random.choice(greetings))
    
    # Market context
    suggestions.append(f"\n\n**Market Vibe:** {context.token_symbol} is showing {market_mood} with {change_24h:+.1f}% in the last 24h. The asset is {vol_assessment} right now.")
    
    # Simulation insights
    if prob_profit > 65:
        suggestions.append(f"\n\n**Outlook:** Looking promising! 🟢 Your simulations show a {prob_profit:.0f}% chance of profit. The median outcome suggests a move to ${median_price:.6f}.")
    elif prob_profit > 45:
        suggestions.append(f"\n\n**Outlook:** It's a coin flip territory. 🟡 {prob_profit:.0f}% profit probability - could go either way. Consider your risk tolerance here.")
    else:
        suggestions.append(f"\n\n**Outlook:** Caution advised! 🔴 Only {prob_profit:.0f}% profit probability in simulations. The odds aren't strongly in your favor.")
    
    # Risk assessment
    suggestions.append(f"\n\n**Risk Range:** Worst case (5th percentile) shows {p5:+.1f}% PnL, while best case (95th) shows {p95:+.1f}%.")
    
    # Journal-informed suggestions
    if journal_summary.get("has_trades"):
        win_rate = journal_summary.get("win_rate", 50)
        if win_rate > 60:
            suggestions.append(f"\n\n**Your Track Record:** You've been crushing it with a {win_rate:.0f}% win rate! Trust your instincts but stay disciplined. 💪")
        elif win_rate < 40:
            suggestions.append(f"\n\n**Friendly Reminder:** Your recent win rate is {win_rate:.0f}%. Maybe consider smaller position sizes until you find your groove again. 🤗")
    
    # Actionable tip
    tips = [
        "\n\n💡 **Tip:** Consider setting a stop-loss at your max acceptable loss to sleep better at night!",
        "\n\n💡 **Tip:** If unsure, scaling in/out of positions can help manage the emotional rollercoaster.",
        "\n\n💡 **Tip:** Remember - the simulation shows possibilities, not certainties. Always DYOR!",
        "\n\n💡 **Tip:** High volatility = high opportunity AND high risk. Size accordingly!",
    ]
    suggestions.append(random.choice(tips))
    
    return "".join(suggestions)


def generate_journal_daily_insight(journal_summary: Dict, holdings_overnight: List[Dict]) -> str:
    """Generate daily insight for journal dashboard."""
    
    insights = []
    
    # Morning greeting based on time
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning! ☀️"
    elif hour < 17:
        greeting = "Good afternoon! 👋"
    else:
        greeting = "Good evening! 🌙"
    
    insights.append(f"{greeting} Here's your daily trading pulse:\n")
    
    if not journal_summary.get("has_trades"):
        insights.append("\n📝 **No trades logged yet!** Start tracking your trades to get personalized insights and improve your strategy over time.")
        return "".join(insights)
    
    # Overall performance
    total_pnl = journal_summary.get("total_pnl", 0)
    win_rate = journal_summary.get("win_rate", 0)
    
    if total_pnl > 0:
        insights.append(f"\n📈 **Portfolio Status:** You're up ${total_pnl:.2f} overall! Great work staying disciplined.")
    elif total_pnl < 0:
        insights.append(f"\n📉 **Portfolio Status:** Down ${abs(total_pnl):.2f} - but remember, every trader has drawdowns. Focus on the process!")
    else:
        insights.append(f"\n📊 **Portfolio Status:** Breaking even - the market's testing your patience!")
    
    # Win rate insight
    if win_rate > 55:
        insights.append(f"\n\n🎯 **Win Rate:** {win_rate:.0f}% - You're reading the market well!")
    elif win_rate < 45:
        insights.append(f"\n\n🎯 **Win Rate:** {win_rate:.0f}% - Consider reviewing your entry criteria or reducing position sizes.")
    
    # Overnight changes simulation
    if holdings_overnight:
        insights.append("\n\n**Overnight Activity:**")
        for holding in holdings_overnight[:3]:
            symbol = holding.get("symbol", "TOKEN")
            change = holding.get("change_24h", 0)
            if change > 0:
                insights.append(f"\n• {symbol}: +{change:.1f}% 📈")
            else:
                insights.append(f"\n• {symbol}: {change:.1f}% 📉")
    
    # Suggested action
    suggestions = [
        "\n\n**Today's Focus:** Review your open positions and set clear exit targets. Preparation beats reaction!",
        "\n\n**Today's Focus:** Great day to journal your recent trades - what worked, what didn't?",
        "\n\n**Today's Focus:** Check your risk exposure. Are you comfortable holding through volatility?",
        "\n\n**Today's Focus:** Take a look at correlation - are all your positions moving the same direction?",
    ]
    insights.append(random.choice(suggestions))
    
    return "".join(insights)


@router.post("/exit-simulator")
async def get_exit_simulation_suggestion(context: SimulationContext):
    """Get AI suggestion after running exit simulation."""
    
    # Get live price
    live_price = await get_live_crypto_price(context.token_symbol)
    
    # Get journal context if wallet provided
    journal_summary = {"has_trades": False}
    if context.wallet_address:
        journal_summary = await get_user_journal_summary(context.wallet_address)
    
    suggestion = generate_exit_suggestion(context, journal_summary, live_price)
    
    return {
        "suggestion": suggestion,
        "live_price": live_price,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/journal-daily/{wallet_address}")
async def get_journal_daily_insight(wallet_address: str):
    """Get daily insight for journal dashboard."""
    
    # Get journal summary
    journal_summary = await get_user_journal_summary(wallet_address)
    
    # Get holdings overnight changes (simulate based on traded tokens)
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
    
    insight = generate_journal_daily_insight(journal_summary, holdings_overnight)
    
    return {
        "insight": insight,
        "holdings_changes": holdings_overnight,
        "journal_stats": journal_summary,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
