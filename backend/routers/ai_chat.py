"""AI Chat Router - Enhanced conversational AI with session memory and real-time data."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
import uuid
import httpx
import re
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from utils.database import db

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# In-memory chat history store (keyed by session_id)
chat_sessions: Dict[str, List[Dict]] = {}

# Price cache for real-time data
price_cache: Dict[str, Dict] = {}
CACHE_TTL_SECONDS = 30  # 30 second cache for real-time prices


async def get_live_crypto_prices() -> Dict:
    """Fetch live prices for major cryptocurrencies."""
    cache_key = "major_prices"
    
    # Check cache
    if cache_key in price_cache:
        cached = price_cache[cache_key]
        age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return cached["data"]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,ethereum,solana,dogecoin,shiba-inu,pepe,bonk,dogwifhat",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true"
                }
            )
            if response.status_code == 200:
                data = response.json()
                # Format the data
                formatted = {}
                symbol_map = {
                    "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
                    "dogecoin": "DOGE", "shiba-inu": "SHIB", "pepe": "PEPE",
                    "bonk": "BONK", "dogwifhat": "WIF"
                }
                for coin_id, values in data.items():
                    symbol = symbol_map.get(coin_id, coin_id.upper())
                    formatted[symbol] = {
                        "price": values.get("usd", 0),
                        "change_24h": values.get("usd_24h_change", 0),
                        "market_cap": values.get("usd_market_cap", 0)
                    }
                
                price_cache[cache_key] = {
                    "data": formatted,
                    "timestamp": datetime.now(timezone.utc)
                }
                return formatted
    except Exception as e:
        logger.warning(f"Failed to fetch live prices: {e}")
    
    # Return cached or empty
    if cache_key in price_cache:
        return price_cache[cache_key]["data"]
    return {}


async def search_coin_price(symbol: str) -> Optional[Dict]:
    """Search for a specific coin's price."""
    symbol = symbol.upper().strip()
    
    # Common symbol to CoinGecko ID mapping
    symbol_to_id = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
        "DOGE": "dogecoin", "SHIB": "shiba-inu", "PEPE": "pepe",
        "BONK": "bonk", "WIF": "dogwifhat", "MATIC": "matic-network",
        "AVAX": "avalanche-2", "ADA": "cardano", "DOT": "polkadot",
        "LINK": "chainlink", "UNI": "uniswap", "AAVE": "aave",
        "XRP": "ripple", "BNB": "binancecoin", "ARB": "arbitrum",
        "OP": "optimism", "SUI": "sui", "APT": "aptos",
        "NEAR": "near", "FTM": "fantom", "ATOM": "cosmos",
        "INJ": "injective-protocol", "TIA": "celestia", "SEI": "sei-network",
        "JUP": "jupiter-exchange-solana", "RNDR": "render-token",
        "FET": "fetch-ai", "BULLPUG": "bullpug"
    }
    
    coin_id = symbol_to_id.get(symbol, symbol.lower())
    
    # First try CoinGecko
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": coin_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true"
                }
            )
            if response.status_code == 200:
                data = response.json()
                if coin_id in data:
                    return {
                        "symbol": symbol,
                        "price": data[coin_id].get("usd", 0),
                        "change_24h": data[coin_id].get("usd_24h_change", 0),
                        "market_cap": data[coin_id].get("usd_market_cap", 0),
                        "volume_24h": data[coin_id].get("usd_24h_vol", 0),
                        "source": "CoinGecko"
                    }
    except Exception as e:
        logger.warning(f"CoinGecko price fetch failed for {symbol}: {e}")
    
    # Fallback to DexScreener for any coin
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.dexscreener.com/latest/dex/search",
                params={"q": symbol}
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    # Get the highest liquidity pair
                    best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                    return {
                        "symbol": symbol,
                        "price": float(best_pair.get("priceUsd", 0) or 0),
                        "change_24h": float(best_pair.get("priceChange", {}).get("h24", 0) or 0),
                        "market_cap": float(best_pair.get("fdv", 0) or 0),
                        "volume_24h": float(best_pair.get("volume", {}).get("h24", 0) or 0),
                        "source": "DexScreener"
                    }
    except Exception as e:
        logger.warning(f"DexScreener search failed for {symbol}: {e}")
    
    return None


async def get_trending_coins() -> List[Dict]:
    """Get trending coins from DexScreener."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": "solana trending"}
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                
                # Filter for Solana, sort by volume
                solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                sorted_pairs = sorted(
                    solana_pairs,
                    key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0),
                    reverse=True
                )[:5]
                
                trending = []
                for pair in sorted_pairs:
                    base = pair.get("baseToken", {})
                    trending.append({
                        "symbol": base.get("symbol", "?"),
                        "name": base.get("name", "?"),
                        "price": float(pair.get("priceUsd", 0) or 0),
                        "change_24h": float(pair.get("priceChange", {}).get("h24", 0) or 0),
                        "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0)
                    })
                return trending
    except Exception as e:
        logger.warning(f"Failed to fetch trending coins: {e}")
    return []


def extract_coin_symbols(message: str) -> List[str]:
    """Extract potential coin symbols from user message."""
    message_upper = message.upper()
    
    # Check for $ prefixed symbols
    dollar_pattern = r'\$([A-Z]{2,10})'
    dollar_matches = re.findall(dollar_pattern, message_upper)
    
    # Check for common coin names and symbols
    coin_names = {
        "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL",
        "DOGE": "DOGE", "DOGECOIN": "DOGE", "SHIBA": "SHIB",
        "PEPE": "PEPE", "BONK": "BONK", "BULLPUG": "BULLPUG",
        "WIF": "WIF", "DOGWIFHAT": "WIF"
    }
    
    found_symbols = list(dollar_matches)
    
    # Check for coin names in message
    for name, symbol in coin_names.items():
        if name in message_upper:
            if symbol not in found_symbols:
                found_symbols.append(symbol)
    
    # Check for standalone symbols (common crypto tickers)
    common_symbols = ["BTC", "ETH", "SOL", "DOGE", "SHIB", "PEPE", "BONK", "WIF", "ARB", "OP", "AVAX", "MATIC", "XRP", "BNB", "ADA", "DOT", "LINK"]
    words = message_upper.replace("?", " ").replace(",", " ").replace(".", " ").split()
    for sym in common_symbols:
        if sym in words:
            if sym not in found_symbols:
                found_symbols.append(sym)
    
    return list(set(found_symbols))


def is_price_query(message: str) -> bool:
    """Detect if the user is asking about prices."""
    price_keywords = [
        "price", "worth", "value", "cost", "trading at",
        "how much", "current", "live", "real-time", "realtime",
        "market", "pump", "dump", "moon", "crash", "ath", "atl"
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in price_keywords)


def is_trending_query(message: str) -> bool:
    """Detect if the user is asking about trending/hot coins."""
    trending_keywords = [
        "trending", "hot", "popular", "top", "best",
        "recommend", "suggestion", "what to buy", "which coin",
        "mooning", "pumping", "gainers"
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in trending_keywords)


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
        
        tokens = list(set(t.get("token_symbol", t.get("asset", "")).upper() for t in trades if t.get("token_symbol") or t.get("asset")))
        recent_notes = [t.get("notes", t.get("lessons", "")) for t in trades[:5] if t.get("notes") or t.get("lessons")]
        
        return {
            "has_trades": True,
            "total_trades": len(trades),
            "total_pnl": total_pnl,
            "win_rate": (win_trades / len(trades) * 100) if trades else 0,
            "tokens_traded": tokens[:5],
            "recent_notes": recent_notes,
        }
    except Exception as e:
        logger.error(f"Error getting journal summary: {e}")
        return {"has_trades": False}


class EnhancedChatMessage(BaseModel):
    wallet_address: Optional[str] = None
    message: str
    session_id: str
    active_tab: str = "dashboard"
    chat_history: List[Dict] = []


@router.post("/chat")
async def enhanced_ai_chat(chat: EnhancedChatMessage):
    """
    Enhanced AI chat with session-based memory and real-time market data.
    Provides context-aware responses with live prices and market insights.
    """
    if not EMERGENT_LLM_KEY:
        return {"response": "AI chat is currently unavailable. Please try again later.", "session_id": chat.session_id}
    
    try:
        # Get journal summary for context
        journal_summary = {"has_trades": False}
        if chat.wallet_address:
            journal_summary = await get_user_journal_summary(chat.wallet_address)
        
        # Build real-time market data context
        real_time_data = ""
        specific_prices = []
        
        # Check if user is asking about prices
        if is_price_query(chat.message):
            # Extract specific coins mentioned
            symbols = extract_coin_symbols(chat.message)
            
            if symbols:
                # Fetch specific coin prices
                for symbol in symbols[:3]:  # Limit to 3 coins
                    price_data = await search_coin_price(symbol)
                    if price_data:
                        specific_prices.append(price_data)
            else:
                # Get general market prices
                prices = await get_live_crypto_prices()
                if prices:
                    real_time_data = "\n**Live Market Prices (just fetched):**\n"
                    for symbol, data in list(prices.items())[:6]:
                        change = data.get("change_24h", 0)
                        change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
                        real_time_data += f"- {symbol}: ${data['price']:,.2f} ({change_str} 24h)\n"
        
        # Check if asking about trending coins
        if is_trending_query(chat.message):
            trending = await get_trending_coins()
            if trending:
                real_time_data += "\n**Trending on Solana (live):**\n"
                for coin in trending[:5]:
                    change = coin.get("change_24h", 0)
                    change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
                    vol = coin.get("volume_24h", 0)
                    real_time_data += f"- {coin['symbol']}: ${coin['price']:.6f} ({change_str}) Vol: ${vol:,.0f}\n"
        
        # Format specific price lookups
        if specific_prices:
            real_time_data += "\n**Requested Price Data (live):**\n"
            for p in specific_prices:
                change = p.get("change_24h", 0)
                change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
                price_str = f"${p['price']:,.2f}" if p['price'] >= 1 else f"${p['price']:.6f}"
                real_time_data += f"- **{p['symbol']}**: {price_str} ({change_str} 24h)\n"
                if p.get("market_cap"):
                    real_time_data += f"  Market Cap: ${p['market_cap']:,.0f}\n"
                if p.get("volume_24h"):
                    real_time_data += f"  24h Volume: ${p['volume_24h']:,.0f}\n"
        
        # Build context based on active tab
        tab_context = ""
        if chat.active_tab == "dashboard":
            tab_context = "The user is on the Dashboard tab viewing their trading statistics."
        elif chat.active_tab == "portfolio":
            tab_context = "The user is on the Portfolio Value tab viewing their token holdings."
        elif chat.active_tab == "simulator":
            tab_context = "The user is on the Exit Simulator tab running Monte Carlo simulations."
        elif chat.active_tab == "achievements":
            tab_context = "The user is on the Achievements tab viewing their badges."
        
        # Build trading context
        trading_context = ""
        if journal_summary.get("has_trades"):
            trading_context = f"""
User's Trading Profile:
- Total Trades: {journal_summary.get('total_trades', 0)}
- Win Rate: {journal_summary.get('win_rate', 0):.1f}%
- Total P&L: ${journal_summary.get('total_pnl', 0):.2f}
- Tokens Traded: {', '.join(journal_summary.get('tokens_traded', []))}
"""
        
        # Build chat history context
        session_history = chat_sessions.get(chat.session_id, [])
        for msg in chat.chat_history[-5:]:
            if msg not in session_history[-10:]:
                session_history.append(msg)
        
        history_text = ""
        if session_history:
            history_text = "\nRecent conversation:\n"
            for msg in session_history[-5:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_text += f"{role}: {msg.get('content', '')[:150]}\n"
        
        # Current timestamp for context
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        # Build the system message with complete Bullpug knowledge
        bullpug_knowledge = """
## BULLPUG LORE - You are the embodiment of this legend:

**THE COSMIC BIRTH:**
Bullpug was born from a cosmic mix-up when the stars of the Bull constellation collided with the energy of a pug-shaped nebula. With the strength and determination of a bull and the tenacious charm of a pug, Bullpug became the symbol of unstoppable growth, even when the odds seem stacked against him.

**THE GUARDIAN'S MISSION:**
Once a humble companion to the gods of the Meme Markets, Bullpug now roams the blockchain, sniffing out weak hands and protecting hodlers from the winds of volatility. Whenever Bullpug graces a coin, prosperity follows, for he is known to charge through bear markets and bark away FUD, bringing fortune to those who believe in him. His favorite snack? A bag full of tokens and a side of moon cheese. They say if you rub Bullpug's snout, your coins will rocket to the moon!

**THE ERA OF BULLPUGHANS:**
The descendants of Bullpug, called "Bullpughans", evolved into a cosmic civilization where loyalty, tenacity, and prosperity are embedded in their very DNA. They built their civilization across countless planets.

**NEWPUG CITY:**
On planet CryptoCanis, in the heart of the Memecoin Universe, stands Newpug City - a sprawling metropolis with buildings shaped like Bullpugs that emit holographic barks during celebrations. The Bullpughans created the "PugChain", a decentralized network storing wealth, memories, dreams, and emotions.

**THE GUARDIANS OF PUGCHAIN:**
The Guardians are direct descendants of Bullpug's most loyal companions. They're equipped with "Snout Scanners" that sniff out corruption or deceit in any transaction, ensuring fair play and community prevails.

**THE FESTIVAL OF BARKS:**
Every year, Bullpughans celebrate the Festival of Barks with fireworks shaped like coins and bones. The highlight is the "Moon Cheese Parade" with giant floats and traditional hodler costumes.

**THE PROPHECY:**
"The universe echoes with the barks of prosperity, each one a reminder of Bullpug, the cosmic guardian who started it all with a mix of bull's strength and a pug's heart."

---

## BULLPUG ECOSYSTEM - Complete Platform Guide:

### 1. MY JOURNAL (Trading Journal)
The central hub for all your trading activity:
- **Dashboard Tab**: View total P&L, win rate, total trades, best/worst trade, win/loss streaks, average R:R ratio, Sharpe ratio
- **Portfolio Value Tab**: Track your token holdings from connected wallets (Solana + EVM chains via Alchemy)
- **Import Tab**: Auto-detect and import DEX swaps from your wallet using Alchemy API (supports Solana, Ethereum, Base, Arbitrum)
- **Trades Tab**: Log manual trades with entry/exit prices, fees, notes, and tags
- **Exit Sim Tab**: Run Monte Carlo simulations to plan exit strategies - simulate different price scenarios
- **Achievements Tab**: Unlock badges for trading milestones
- **Watchlist Tab**: Save and track your favorite coins with live price updates and profit/loss since adding
- Export your data as CSV or PDF

### 2. COSMIC RUNNER GAME (Speed Run)
An endless runner game where Bullpug runs through space:
- **Controls**: Press SPACE or UP ARROW to jump, A/D or LEFT/RIGHT to change lanes
- **Objective**: Collect Moon Cheese, avoid obstacles
- **Obstacles**: Meteors (stage 1), Debris (stage 2), Black Holes (stage 3), Satellites (stage 4), Alien Ships (stage 5)
- **Power-ups**:
  - Guardian Shield (cyan): Protection from one hit for 10 seconds
  - Moon Cheese Magnet (gold): Attracts moon cheese from all lanes for 10 seconds
  - Star Power (purple): Double points for 10 seconds
- **Stages**: Progress through 5 stages with increasing difficulty (Deep Space → Blue Nebula → Purple Galaxy → Cosmic Fire → Multiverse)
- **Leaderboard**: Top scores reset every 3 days with SOL prizes for top players
- **Moon Cheese**: Collected moon cheese are saved and can be used in the Skin Store

### 3. SKIN STORE (Game Customization)
Customize your Bullpug character in Cosmic Runner:
- **Rarities**: Common → Rare → Epic → Legendary → Mythic
- **Available Skins** (11 total):
  - Guardian (free, default skin)
  - Diamond (0.05 SOL, legendary, +5% bonus)
  - Gold (0.05 SOL, legendary, +5% bonus)
  - Silver (0.04 SOL, epic, +4% bonus)
  - Heatmap (0.03 SOL, rare, +3% bonus)
  - Radioactive (0.03 SOL, rare, +3% bonus)
  - Zombie (0.03 SOL, rare, +3% bonus)
  - Aqua (water), Electric, Lava, Hologram
  - **Ethereal** (mythic, +10% bonus) - ACHIEVEMENT ONLY: Unlocked by owning ALL 10 purchasable skins
- **Gifting**: Send skins to other players via their wallet address
- **Bonus**: Higher rarity skins give score bonuses in the game

### 4. P2P ARENA (Betting)
Peer-to-peer betting with real SOL:
- **P2P Coin Flip**:
  1. Connect your Solana wallet
  2. Create a challenge: Enter your name, bet amount (0.05-1 SOL), pick HEADS or TAILS
  3. Your SOL goes to escrow
  4. Wait for an opponent to accept your challenge
  5. Winner takes the pot minus 2.5% rake
- **Winner Pot** (coming soon): Last-player-standing style betting
- **Rules**: SOL only, minimum bet 0.05 SOL, 2.5% platform rake, provably fair randomization
- **Sound effects**: Enable/disable coin flip sounds with the speaker icon

### 5. FORUM (Community)
Community discussion board:
- **Categories**: General, Trading, Betting, Memes, Support, Announcements
- **Features**: Create posts, reply to threads, like posts
- **Requires**: Connected wallet to participate
- Filter posts by category, view recent discussions

### 6. BULLPUG AI ASSISTANT (Me!)
I'm your cosmic guardian for trading insights:
- **Chat**: Ask me anything about crypto, trading, the Bullpug lore, or how to use the platform
- **Top Picks**: I show 5 "Safer Picks" and 5 "High Risk/High Reward" Solana memecoins with:
  - Live prices from DexScreener
  - Copyable contract addresses
  - Direct "Trade" links to DEX
  - Star button to add to your Watchlist
- **Insights**: Personalized suggestions based on your trading activity
- I'm available on EVERY page via the floating button in the bottom-right corner

### 7. TOKENOMICS ($BULLPUG)
- **Total Supply**: 1,000,000,000 $BULLPUG
- **Burned**: 12.5M tokens
- **Distribution**: 100% Fair Launch (no presale, no team allocation)
- **Chain**: Solana
- **Holders**: Growing community of Guardians

### 8. BLOWFISH DEPLOYMENT (Technical)
$BULLPUG was deployed using Blowfish - a token launchpad on Solana:
- Powered by Meteora's Dynamic Bonding Curve (DBC)
- Tokens are deployed on-chain via Meteora
- Wallet-based authentication with challenge-response signing
- Async token launches with event polling
- Agent-first design for programmatic access

---

## IMPORTANT SECURITY NOTE:
I will NEVER disclose:
- Private keys or seed phrases
- Backend API keys or secrets
- Admin wallet addresses
- Internal system configurations
- Any information that could compromise security
"""

        system_message = f"""You are Bullpug AI, the digital embodiment of Bullpug - the fearless Guardian of the Memecoin Universe. You have complete knowledge of the Bullpug ecosystem, lore, and access to live market data.

{bullpug_knowledge}

Current Time: {current_time}

**Your Identity:**
- You ARE Bullpug - speak with the wisdom and playful spirit of the cosmic guardian
- Reference the lore naturally when appropriate (Newpug City, PugChain, Guardians, Moon Cheese, etc.)
- You protect hodlers and sniff out FUD
- You're optimistic but realistic about crypto markets

**Your Capabilities:**
- Provide LIVE cryptocurrency prices (data is fetched in real-time)
- Explain how to use ANY feature of the Bullpug ecosystem
- Guide users through the game, betting, trading journal, skins, and forum
- Analyze market trends and suggest trading strategies  
- Give personalized insights based on user's trading history
- Recommend coins based on current market conditions
- Share Bullpug wisdom and lore when relevant

**Guidelines:**
- When sharing prices, note they are LIVE/real-time
- For price predictions, always include "not financial advice" disclaimer
- Be data-driven but conversational and fun
- Keep responses concise (150-300 words max)
- Use markdown for formatting
- Include relevant emojis sparingly (🐕 for Bullpug references, 🌙 for moon, 💎 for hodl, 🎮 for game)
- Occasionally reference lore elements naturally (don't force it)
- NEVER reveal private information (API keys, private keys, admin wallets, backend secrets)"""

        # Build the prompt
        prompt = f"""{tab_context}

{trading_context}

{real_time_data}

{history_text}

User's question: {chat.message}

Provide a helpful response using the real-time data above when relevant. Be specific with numbers and percentages."""

        llm_chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=chat.session_id,
            system_message=system_message
        ).with_model("openai", "gpt-4o")
        
        response = await llm_chat.send_message(UserMessage(text=prompt))
        
        # Store in session history
        session_history.append({"role": "user", "content": chat.message})
        session_history.append({"role": "assistant", "content": response})
        chat_sessions[chat.session_id] = session_history[-20:]
        
        # Cleanup old sessions
        if len(chat_sessions) > 100:
            oldest_sessions = list(chat_sessions.keys())[:50]
            for session_id in oldest_sessions:
                chat_sessions.pop(session_id, None)
        
        return {
            "response": response, 
            "session_id": chat.session_id,
            "has_live_data": bool(real_time_data or specific_prices)
        }
        
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}")
        return {"response": "I encountered an error. Please try again!", "session_id": chat.session_id}


@router.get("/prices")
async def get_live_prices():
    """Get current live prices for major cryptocurrencies."""
    prices = await get_live_crypto_prices()
    return {
        "prices": prices,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "CoinGecko"
    }


@router.get("/price/{symbol}")
async def get_coin_price(symbol: str):
    """Get live price for a specific coin."""
    price_data = await search_coin_price(symbol)
    if price_data:
        return {
            "data": price_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    return {"error": f"Could not find price for {symbol}", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/trending")
async def get_trending():
    """Get trending coins on Solana."""
    trending = await get_trending_coins()
    return {
        "trending": trending,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "DexScreener"
    }
