"""AI Chat Router - Enhanced conversational AI with session memory."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from utils.database import db

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# In-memory chat history store (keyed by session_id)
# In production, use Redis or MongoDB for persistence
chat_sessions: Dict[str, List[Dict]] = {}


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
    Enhanced AI chat with session-based memory.
    Provides context-aware responses based on the active tab and user's trading history.
    """
    if not EMERGENT_LLM_KEY:
        return {"response": "AI chat is currently unavailable. Please try again later.", "session_id": chat.session_id}
    
    try:
        # Get journal summary for context
        journal_summary = {"has_trades": False}
        if chat.wallet_address:
            journal_summary = await get_user_journal_summary(chat.wallet_address)
        
        # Build context based on active tab
        tab_context = ""
        if chat.active_tab == "dashboard":
            tab_context = "The user is on the Dashboard tab viewing their trading statistics and performance charts."
        elif chat.active_tab == "portfolio":
            tab_context = "The user is on the Portfolio Value tab viewing their token holdings across chains."
        elif chat.active_tab == "import":
            tab_context = "The user is on the Import tab to auto-detect DEX trades from their wallets."
        elif chat.active_tab == "trades":
            tab_context = "The user is on the Trades tab viewing their logged trade history."
        elif chat.active_tab == "simulator":
            tab_context = "The user is on the Exit Simulator tab running Monte Carlo simulations for exit strategies."
        elif chat.active_tab == "achievements":
            tab_context = "The user is on the Achievements tab viewing their trading badges and community benchmarks."
        elif chat.active_tab == "backups":
            tab_context = "The user is on the Backup tab managing cloud backups of their journal."
        
        # Build trading context
        trading_context = ""
        if journal_summary.get("has_trades"):
            trading_context = f"""
User's Trading Profile:
- Total Trades: {journal_summary.get('total_trades', 0)}
- Win Rate: {journal_summary.get('win_rate', 0):.1f}%
- Total P&L: ${journal_summary.get('total_pnl', 0):.2f}
- Tokens Traded: {', '.join(journal_summary.get('tokens_traded', []))}
- Recent Notes: {', '.join(journal_summary.get('recent_notes', [])[:2]) or 'None'}
"""
        
        # Build chat history context (last 5 messages from session)
        session_history = chat_sessions.get(chat.session_id, [])
        
        # Add incoming chat history to session
        for msg in chat.chat_history[-5:]:
            if msg not in session_history[-10:]:
                session_history.append(msg)
        
        history_text = ""
        if session_history:
            history_text = "\nRecent conversation:\n"
            for msg in session_history[-5:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_text += f"{role}: {msg.get('content', '')[:200]}\n"
        
        # Build the prompt
        system_message = """You are Bullpug AI, a friendly, knowledgeable, and supportive crypto trading assistant for the Bullpug memecoin community.

Your personality:
- Encouraging but realistic about risks
- Data-driven when providing insights
- Uses occasional emojis but stays professional
- Gives concise, actionable advice
- Never gives specific financial advice (always say "not financial advice")

Guidelines:
- Keep responses under 200 words unless asked for detailed analysis
- Use markdown for formatting (bold, lists)
- Reference user's trading data when relevant
- Be helpful with trading journal features
- For price predictions, always include disclaimers"""

        prompt = f"""{tab_context}

{trading_context}

{history_text}

User's question: {chat.message}

Provide a helpful, conversational response. Be friendly and supportive. Keep response concise (100-200 words max)."""

        llm_chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=chat.session_id,
            system_message=system_message
        ).with_model("openai", "gpt-4o")
        
        response = await llm_chat.send_message(UserMessage(text=prompt))
        
        # Store in session history
        session_history.append({"role": "user", "content": chat.message})
        session_history.append({"role": "assistant", "content": response})
        
        # Keep only last 20 messages per session
        chat_sessions[chat.session_id] = session_history[-20:]
        
        # Cleanup old sessions (simple approach - in production use TTL)
        if len(chat_sessions) > 100:
            # Remove oldest sessions
            oldest_sessions = list(chat_sessions.keys())[:50]
            for session_id in oldest_sessions:
                chat_sessions.pop(session_id, None)
        
        return {"response": response, "session_id": chat.session_id}
        
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}")
        return {"response": "I encountered an error. Please try again!", "session_id": chat.session_id}
