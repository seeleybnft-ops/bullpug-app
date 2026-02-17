"""Direct messaging routes for user-to-user communication."""

from fastapi import APIRouter, HTTPException
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel

from utils.database import db
from utils.notifications import send_notification

router = APIRouter(prefix="/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    to_wallet: str
    content: str
    from_wallet: str
    from_name: str = "Anonymous"


@router.post("/send")
async def send_message(data: SendMessageRequest):
    """Send a direct message to another user."""
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Message content required")
    if not data.from_wallet or not data.to_wallet:
        raise HTTPException(status_code=400, detail="Wallet addresses required")
    if data.from_wallet == data.to_wallet:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    
    message = {
        "id": str(uuid.uuid4()),
        "from_wallet": data.from_wallet,
        "from_name": data.from_name[:30],
        "to_wallet": data.to_wallet,
        "content": data.content.strip()[:1000],
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.direct_messages.insert_one(message)
    
    # Send notification
    await send_notification(
        data.to_wallet,
        f"New Message from {data.from_name[:15]}",
        data.content[:50] + "..." if len(data.content) > 50 else data.content,
        "message"
    )
    
    return {"message": "Message sent", "message_id": message["id"]}


@router.get("/inbox/{wallet_address}")
async def get_inbox(wallet_address: str, limit: int = 50):
    """Get messages received by a wallet."""
    messages = await db.direct_messages.find(
        {"to_wallet": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    unread_count = await db.direct_messages.count_documents({
        "to_wallet": wallet_address,
        "read": False
    })
    
    return {"messages": messages, "unread_count": unread_count}


@router.get("/sent/{wallet_address}")
async def get_sent_messages(wallet_address: str, limit: int = 50):
    """Get messages sent by a wallet."""
    messages = await db.direct_messages.find(
        {"from_wallet": wallet_address},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return {"messages": messages}


@router.get("/conversation/{wallet1}/{wallet2}")
async def get_conversation(wallet1: str, wallet2: str, limit: int = 100):
    """Get conversation between two wallets."""
    messages = await db.direct_messages.find(
        {
            "$or": [
                {"from_wallet": wallet1, "to_wallet": wallet2},
                {"from_wallet": wallet2, "to_wallet": wallet1}
            ]
        },
        {"_id": 0}
    ).sort("created_at", 1).to_list(limit)
    
    return {"messages": messages}


@router.get("/conversations/{wallet_address}")
async def get_conversations(wallet_address: str):
    """Get list of conversations for a wallet."""
    # Find unique conversation partners
    sent_to = await db.direct_messages.distinct("to_wallet", {"from_wallet": wallet_address})
    received_from = await db.direct_messages.distinct("from_wallet", {"to_wallet": wallet_address})
    
    partners = list(set(sent_to + received_from))
    conversations = []
    
    for partner in partners:
        last_message = await db.direct_messages.find_one(
            {
                "$or": [
                    {"from_wallet": wallet_address, "to_wallet": partner},
                    {"from_wallet": partner, "to_wallet": wallet_address}
                ]
            },
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        unread_count = await db.direct_messages.count_documents({
            "from_wallet": partner,
            "to_wallet": wallet_address,
            "read": False
        })
        
        if last_message:
            conversations.append({
                "partner_wallet": partner,
                "last_message": last_message,
                "unread_count": unread_count
            })
    
    # Sort by most recent
    conversations.sort(key=lambda x: x["last_message"]["created_at"], reverse=True)
    
    return {"conversations": conversations}


@router.post("/read/{message_id}")
async def mark_message_read(message_id: str, wallet_address: str):
    """Mark a message as read."""
    result = await db.direct_messages.update_one(
        {"id": message_id, "to_wallet": wallet_address},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found or not recipient")
    
    return {"message": "Message marked as read"}


@router.post("/read-all/{wallet_address}")
async def mark_all_read(wallet_address: str):
    """Mark all messages as read for a wallet."""
    result = await db.direct_messages.update_many(
        {"to_wallet": wallet_address, "read": False},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": f"Marked {result.modified_count} messages as read"}


@router.delete("/message/{message_id}")
async def delete_message(message_id: str, wallet_address: str):
    """Delete a message (sender or recipient can delete)."""
    message = await db.direct_messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message["from_wallet"] != wallet_address and message["to_wallet"] != wallet_address:
        raise HTTPException(status_code=403, detail="Not authorized to delete this message")
    
    await db.direct_messages.delete_one({"id": message_id})
    return {"message": "Message deleted"}
