"""Forum routes for community discussions."""

from fastapi import APIRouter, HTTPException
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional

from ..utils.database import db

router = APIRouter(prefix="/forum", tags=["forum"])


class CreatePostRequest(BaseModel):
    title: str
    content: str
    author_wallet: str
    author_name: str = "Anonymous"
    category: str = "general"


class CreateReplyRequest(BaseModel):
    post_id: str
    content: str
    author_wallet: str
    author_name: str = "Anonymous"


@router.get("/posts")
async def get_forum_posts(category: Optional[str] = None, limit: int = 50):
    """Get all forum posts, optionally filtered by category."""
    query = {}
    if category:
        query["category"] = category
    
    posts = await db.forum_posts.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    for post in posts:
        post["reply_count"] = await db.forum_replies.count_documents({"post_id": post["id"]})
    
    return {"posts": posts}


@router.get("/post/{post_id}")
async def get_forum_post(post_id: str):
    """Get a single forum post with replies."""
    post = await db.forum_posts.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    replies = await db.forum_replies.find({"post_id": post_id}, {"_id": 0}).sort("created_at", 1).to_list(100)
    post["replies"] = replies
    post["reply_count"] = len(replies)
    
    return post


@router.post("/post")
async def create_forum_post(data: CreatePostRequest):
    """Create a new forum post."""
    if not data.title.strip() or not data.content.strip():
        raise HTTPException(status_code=400, detail="Title and content required")
    if not data.author_wallet:
        raise HTTPException(status_code=400, detail="Wallet address required")
    
    post = {
        "id": str(uuid.uuid4()),
        "title": data.title.strip()[:200],
        "content": data.content.strip()[:5000],
        "author_wallet": data.author_wallet,
        "author_name": data.author_name[:30],
        "category": data.category,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "likes": 0,
        "views": 0
    }
    
    await db.forum_posts.insert_one(post)
    return {"message": "Post created", "post_id": post["id"]}


@router.post("/reply")
async def create_forum_reply(data: CreateReplyRequest):
    """Create a reply to a forum post."""
    post = await db.forum_posts.find_one({"id": data.post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Content required")
    if not data.author_wallet:
        raise HTTPException(status_code=400, detail="Wallet address required")
    
    reply = {
        "id": str(uuid.uuid4()),
        "post_id": data.post_id,
        "content": data.content.strip()[:2000],
        "author_wallet": data.author_wallet,
        "author_name": data.author_name[:30],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "likes": 0
    }
    
    await db.forum_replies.insert_one(reply)
    
    await db.forum_posts.update_one(
        {"id": data.post_id},
        {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Reply posted", "reply_id": reply["id"]}


@router.post("/like/{item_type}/{item_id}")
async def like_item(item_type: str, item_id: str, wallet_address: str):
    """Like a post or reply."""
    if item_type not in ["post", "reply"]:
        raise HTTPException(status_code=400, detail="Invalid item type")
    
    collection = db.forum_posts if item_type == "post" else db.forum_replies
    item = await collection.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail=f"{item_type.capitalize()} not found")
    
    existing_like = await db.forum_likes.find_one({
        "item_type": item_type,
        "item_id": item_id,
        "wallet_address": wallet_address
    })
    
    if existing_like:
        await db.forum_likes.delete_one({"_id": existing_like["_id"]})
        await collection.update_one({"id": item_id}, {"$inc": {"likes": -1}})
        return {"message": "Like removed", "likes": item.get("likes", 0) - 1}
    else:
        await db.forum_likes.insert_one({
            "id": str(uuid.uuid4()),
            "item_type": item_type,
            "item_id": item_id,
            "wallet_address": wallet_address,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        await collection.update_one({"id": item_id}, {"$inc": {"likes": 1}})
        return {"message": "Liked", "likes": item.get("likes", 0) + 1}


@router.delete("/post/{post_id}")
async def delete_forum_post(post_id: str, wallet_address: str):
    """Delete a forum post (author only)."""
    post = await db.forum_posts.find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["author_wallet"] != wallet_address:
        raise HTTPException(status_code=403, detail="Only author can delete")
    
    await db.forum_posts.delete_one({"id": post_id})
    await db.forum_replies.delete_many({"post_id": post_id})
    
    return {"message": "Post deleted"}


@router.get("/categories")
async def get_forum_categories():
    """Get available forum categories."""
    return {
        "categories": [
            {"id": "general", "name": "General Discussion"},
            {"id": "trading", "name": "Trading Talk"},
            {"id": "strategies", "name": "Strategies"},
            {"id": "announcements", "name": "Announcements"},
            {"id": "offtopic", "name": "Off Topic"}
        ]
    }
