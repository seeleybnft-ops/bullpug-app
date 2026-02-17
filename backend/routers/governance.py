"""Governance and voting routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone, timedelta

from utils.database import db


router = APIRouter(prefix="/governance", tags=["governance"])


# Default proposals
PROPOSALS = [
    {
        "id": "prop-1",
        "title": "Increase Burn Rate to 3%",
        "description": "Increase the burn rate from 2% to 3% per transaction to accelerate deflation.",
        "status": "active",
        "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    },
    {
        "id": "prop-2",
        "title": "Launch Bullpug Game Season 2",
        "description": "Allocate 2% of ecosystem reserve for Game Season 2 with new cosmic levels.",
        "status": "active",
        "end_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    },
    {
        "id": "prop-3",
        "title": "Partner with CosmicDogs DAO",
        "description": "Cross-promote with CosmicDogs DAO for joint NFT drops and shared liquidity.",
        "status": "active",
        "end_date": (datetime.now(timezone.utc) + timedelta(days=21)).isoformat()
    },
]


class VoteRequest(BaseModel):
    proposal_id: str
    vote: str
    wallet_address: Optional[str] = None


@router.get("/proposals")
async def get_proposals():
    """Get all governance proposals with vote counts."""
    enriched = []
    for p in PROPOSALS:
        yes_count = await db.votes.count_documents({"proposal_id": p["id"], "vote": "yes"})
        no_count = await db.votes.count_documents({"proposal_id": p["id"], "vote": "no"})
        enriched.append({**p, "yes_votes": yes_count, "no_votes": no_count})
    return {"proposals": enriched}


@router.post("/vote")
async def cast_vote(data: VoteRequest):
    """Cast a vote on a proposal."""
    existing = await db.votes.find_one(
        {"proposal_id": data.proposal_id, "wallet_address": data.wallet_address},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already voted")
    
    doc = {
        "id": str(uuid.uuid4()),
        "proposal_id": data.proposal_id,
        "vote": data.vote,
        "wallet_address": data.wallet_address,
        "voted_at": datetime.now(timezone.utc).isoformat()
    }
    await db.votes.insert_one(doc)
    return {"message": "Vote cast!", "vote": data.vote}
