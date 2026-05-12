"""P2P Arena live chat — lightweight HTTP-polling chat room.

No WebSocket (K8s ingress times them out). Stores last 200 messages in MongoDB.
Anyone can post; wallet-linked posts show their truncated address, anonymous
posts show as "Anon-XXXX".
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from utils.database import db

router = APIRouter(prefix="/arena-chat", tags=["arena-chat"])
logger = logging.getLogger(__name__)

# Anti-spam (per-wallet/session minimum gap between posts in seconds)
MIN_POST_GAP_SECONDS = 2
# Hard cap of stored chat history
MAX_HISTORY = 200
# Hard cap of message body
MAX_BODY_LEN = 240

# Simple banned-word filter — keeps the room family-friendly
_BANNED = re.compile(r"\b(fuck|shit|cunt|nigger|fag|kike|chink|spic|rape)\w*\b", re.IGNORECASE)


def _short_wallet(addr: Optional[str]) -> str:
    if not addr or len(addr) <= 8:
        return addr or "Anon"
    return f"{addr[:4]}…{addr[-4:]}"


def _sanitise(text: str) -> str:
    text = text.strip().replace("\n\n\n", "\n\n")
    if len(text) > MAX_BODY_LEN:
        text = text[:MAX_BODY_LEN]
    # Replace banned words with stars
    return _BANNED.sub(lambda m: "*" * len(m.group(0)), text)


class PostMessageIn(BaseModel):
    body: str = Field(..., min_length=1, max_length=MAX_BODY_LEN)
    wallet_address: Optional[str] = None
    session_id: Optional[str] = None  # client-side stable id for anon throttling


class ChatMessage(BaseModel):
    id: str
    body: str
    author: str
    wallet_address: Optional[str] = None
    session_id: Optional[str] = None
    is_system: bool = False
    created_at: str


@router.get("/messages")
async def get_messages(limit: int = 50, since: Optional[str] = None):
    """Return chat messages newest-first by default. With `since=<ISO>` only newer."""
    if limit > 100:
        limit = 100
    query: dict = {}
    if since:
        query["created_at"] = {"$gt": since}
    rows = await db.arena_chat.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    rows.reverse()  # oldest → newest for natural rendering
    return {"messages": rows, "count": len(rows)}


@router.post("/post")
async def post_message(data: PostMessageIn):
    body = _sanitise(data.body)
    if not body:
        raise HTTPException(status_code=400, detail="Message is empty after sanitisation")

    # Throttle by wallet OR session — but NOT match unrelated anonymous posters
    cutoff = (datetime.now(timezone.utc).timestamp() - MIN_POST_GAP_SECONDS)
    or_clauses = []
    if data.wallet_address:
        or_clauses.append({"wallet_address": data.wallet_address})
    if data.session_id:
        or_clauses.append({"session_id": data.session_id})
    last = None
    if or_clauses:
        last = await db.arena_chat.find_one({"$or": or_clauses}, sort=[("created_at", -1)])
    if last:
        try:
            last_ts = datetime.fromisoformat(last["created_at"].replace("Z", "+00:00")).timestamp()
            if last_ts > cutoff:
                raise HTTPException(status_code=429, detail="You're posting too fast")
        except HTTPException:
            raise
        except Exception:
            pass

    author = _short_wallet(data.wallet_address) if data.wallet_address else f"Anon-{(data.session_id or uuid.uuid4().hex)[-4:].upper()}"

    msg = {
        "id": uuid.uuid4().hex[:12],
        "body": body,
        "author": author,
        "wallet_address": data.wallet_address,
        "session_id": data.session_id,
        "is_system": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.arena_chat.insert_one(msg)

    # Prune: keep only the most recent MAX_HISTORY
    total = await db.arena_chat.count_documents({})
    if total > MAX_HISTORY:
        oldest = await db.arena_chat.find({}, {"_id": 1, "created_at": 1}).sort("created_at", 1).limit(total - MAX_HISTORY).to_list(total)
        ids = [d["_id"] for d in oldest]
        if ids:
            await db.arena_chat.delete_many({"_id": {"$in": ids}})

    msg.pop("_id", None)
    return {"ok": True, "message": msg}


async def post_system_message(body: str) -> None:
    """Internal helper for system-emitted chat (e.g. countdown announcements)."""
    try:
        await db.arena_chat.insert_one({
            "id": uuid.uuid4().hex[:12],
            "body": body,
            "author": "Bullpug",
            "wallet_address": None,
            "session_id": None,
            "is_system": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        logger.exception("Failed to post system message")
