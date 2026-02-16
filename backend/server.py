from fastapi import FastAPI, APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import hashlib
import secrets
import httpx
import asyncio
import numpy as np
import json as jsonlib
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ['DB_NAME']]

stripe_api_key = os.environ.get('STRIPE_API_KEY')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========== Models ==========
class NewsletterSubscribe(BaseModel):
    email: str

class CheckoutRequest(BaseModel):
    product_id: str
    quantity: int = 1
    origin_url: str

class CoinTossFlip(BaseModel):
    client_seed: str
    bet_amount: float
    choice: str
    wallet_address: Optional[str] = None

class PotJoinRequest(BaseModel):
    bet_amount: float
    wallet_address: Optional[str] = None
    display_name: str = "Anonymous Guardian"

class VoteRequest(BaseModel):
    proposal_id: str
    vote: str
    wallet_address: Optional[str] = None

class StakingSimRequest(BaseModel):
    amount: float
    duration_days: int
    apy: float = 12.0

class ExitSimRequest(BaseModel):
    token_amount: float
    entry_price: float
    exit_prices: List[float]
    tax_rate: float = 15.0

class MonteCarloRequest(BaseModel):
    token_amount: float
    entry_price: float
    volatility: float = 0.8
    drift: float = 0.1
    days: int = 180
    simulations: int = 1000
    tax_rate: float = 15.0


# ========== WebSocket Manager ==========
class PotWSManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

pot_ws_manager = PotWSManager()


# ========== Products ==========
PRODUCTS = {
    "guardian-plush": {
        "id": "guardian-plush",
        "name": "Bullpug Guardian Plushie",
        "description": "The ultimate cosmic guardian in plush form! Cape, bull horns, and glow-in-the-dark eyes.",
        "price": 29.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/7x0weeyi_download%20-%202026-02-17T063439.078.png",
        "category": "plushie"
    },
    "space-pug-plush": {
        "id": "space-pug-plush",
        "name": "Cyber Bullpug Plushie",
        "description": "Bullpug in full cyber armor! LED visor included. Ready to patrol the blockchain.",
        "price": 34.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/kynwxxke_image%20-%202026-02-17T063523.593.jpg",
        "category": "plushie"
    },
    "mini-pug-pack": {
        "id": "mini-pug-pack",
        "name": "Mini Bullpug Pack (Set of 3)",
        "description": "Three adorable mini Bullpugs: Guardian, Cosmic, and Golden Bull variants.",
        "price": 19.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/5w17pptk__eda5997e-289f-4f2c-916b-329017a171d6.jfif",
        "category": "plushie"
    },
    "cape-edition": {
        "id": "cape-edition",
        "name": "Bullpug Maid Edition (XL)",
        "description": "Deluxe oversized Bullpug in maid outfit. The ultimate collector's item with real fabric accessories.",
        "price": 49.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/2sae826h_25.10.2024_17.06.12_REC.png",
        "category": "plushie"
    }
}

PROPOSALS = [
    {"id": "prop-1", "title": "Increase Burn Rate to 3%", "description": "Increase the burn rate from 2% to 3% per transaction to accelerate deflation.", "status": "active", "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()},
    {"id": "prop-2", "title": "Launch Bullpug Game Season 2", "description": "Allocate 2% of ecosystem reserve for Game Season 2 with new cosmic levels.", "status": "active", "end_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()},
    {"id": "prop-3", "title": "Partner with CosmicDogs DAO", "description": "Cross-promote with CosmicDogs DAO for joint NFT drops and shared liquidity.", "status": "active", "end_date": (datetime.now(timezone.utc) + timedelta(days=21)).isoformat()},
]

active_pot = {
    "id": str(uuid.uuid4()),
    "total_amount": 0,
    "entries": [],
    "status": "open",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "draw_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    "house_fee_percent": 7,
    "winner": None
}


# ========== Routes ==========
@api_router.get("/")
async def root():
    return {"message": "Bullpug API - Guardian of the Memecoin Universe"}


@api_router.post("/newsletter/subscribe")
async def subscribe_newsletter(data: NewsletterSubscribe):
    existing = await db.newsletter_subscribers.find_one({"email": data.email}, {"_id": 0})
    if existing:
        return {"message": "Already subscribed!", "status": "existing"}
    doc = {"id": str(uuid.uuid4()), "email": data.email, "subscribed_at": datetime.now(timezone.utc).isoformat(), "active": True}
    await db.newsletter_subscribers.insert_one(doc)
    return {"message": "Welcome to the Guardian newsletter!", "status": "success"}


@api_router.get("/products")
async def get_products():
    return {"products": list(PRODUCTS.values())}


@api_router.post("/checkout/session")
async def create_checkout_session(request: Request, data: CheckoutRequest):
    if data.product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    product = PRODUCTS[data.product_id]
    amount = product["price"] * data.quantity

    success_url = f"{data.origin_url}/shop?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/shop"

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)

    checkout_req = CheckoutSessionRequest(
        amount=float(amount), currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"product_id": data.product_id, "product_name": product["name"], "quantity": str(data.quantity)}
    )
    session = await stripe_checkout.create_checkout_session(checkout_req)

    tx = {"id": str(uuid.uuid4()), "session_id": session.session_id, "amount": float(amount), "currency": "usd",
          "product_id": data.product_id, "quantity": data.quantity, "payment_status": "initiated", "status": "pending",
          "created_at": datetime.now(timezone.utc).isoformat()}
    await db.payment_transactions.insert_one(tx)
    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/checkout/status/{session_id}")
async def get_checkout_status(request: Request, session_id: str):
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    status = await stripe_checkout.get_checkout_status(session_id)
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status.payment_status,
                  "status": "completed" if status.payment_status == "paid" else status.status,
                  "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"status": status.status, "payment_status": status.payment_status,
            "amount_total": status.amount_total, "currency": status.currency}


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        if webhook_response and webhook_response.session_id:
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {"payment_status": webhook_response.payment_status,
                          "status": "completed" if webhook_response.payment_status == "paid" else "failed",
                          "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error"}


@api_router.post("/betting/coin-toss")
async def flip_coin(data: CoinTossFlip):
    server_seed = secrets.token_hex(32)
    server_seed_hash = hashlib.sha256(server_seed.encode()).hexdigest()
    combined = f"{server_seed}{data.client_seed}"
    result_hash = hashlib.sha256(combined.encode()).hexdigest()
    last_digit = int(result_hash[-1], 16)
    outcome = "heads" if last_digit % 2 == 0 else "tails"
    won = outcome == data.choice.lower()

    house_fee_percent = 5
    payout = 0
    if won:
        payout = round(data.bet_amount * 2 * (1 - house_fee_percent / 100), 2)
    else:
        rev = data.bet_amount
        logger.info(f"Revenue: buyback={rev*0.6:.2f}, growth={rev*0.3:.2f}, profit={rev*0.1:.2f}")

    result = {
        "id": str(uuid.uuid4()), "outcome": outcome, "choice": data.choice.lower(), "won": won,
        "bet_amount": data.bet_amount, "payout": payout, "house_fee_percent": house_fee_percent,
        "server_seed": server_seed, "server_seed_hash": server_seed_hash,
        "client_seed": data.client_seed, "result_hash": result_hash,
        "verification": f"SHA256({server_seed} + {data.client_seed}) = {result_hash}",
        "wallet_address": data.wallet_address, "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.bets.insert_one({**result, "type": "coin_toss"})
    return result


@api_router.get("/betting/history")
async def get_bet_history(limit: int = 20):
    history = await db.bets.find({"type": "coin_toss"}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"history": history}


@api_router.get("/betting/pot")
async def get_pot_status():
    global active_pot
    entries_display = []
    for e in active_pot["entries"]:
        prob = round(e["amount"] / active_pot["total_amount"] * 100, 1) if active_pot["total_amount"] > 0 else 0
        entries_display.append({"display_name": e["display_name"], "amount": e["amount"], "probability": prob})
    return {"id": active_pot["id"], "total_amount": active_pot["total_amount"],
            "entry_count": len(active_pot["entries"]), "entries": entries_display,
            "status": active_pot["status"], "draw_at": active_pot["draw_at"],
            "house_fee_percent": active_pot["house_fee_percent"], "winner": active_pot["winner"]}


@api_router.post("/betting/pot/join")
async def join_pot(data: PotJoinRequest):
    global active_pot
    if active_pot["status"] != "open":
        raise HTTPException(status_code=400, detail="Pot is closed")
    if data.bet_amount <= 0:
        raise HTTPException(status_code=400, detail="Bet must be positive")
    entry = {"id": str(uuid.uuid4()), "display_name": data.display_name,
             "amount": data.bet_amount, "wallet_address": data.wallet_address,
             "joined_at": datetime.now(timezone.utc).isoformat()}
    active_pot["entries"].append(entry)
    active_pot["total_amount"] += data.bet_amount
    resp = {"message": f"Joined pot with {data.bet_amount} $BULLPUG!",
            "probability": round(data.bet_amount / active_pot["total_amount"] * 100, 1),
            "total_pot": active_pot["total_amount"], "entry_count": len(active_pot["entries"])}
    await pot_ws_manager.broadcast({"type": "pot_update", "data": await _get_pot_data()})
    return resp


@api_router.post("/betting/pot/draw")
async def draw_pot_winner():
    global active_pot
    if len(active_pot["entries"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries")
    total = active_pot["total_amount"]
    rand_value = secrets.randbelow(int(total * 100)) / 100
    cumulative = 0
    winner = None
    for entry in active_pot["entries"]:
        cumulative += entry["amount"]
        if rand_value <= cumulative:
            winner = entry
            break
    if not winner:
        winner = active_pot["entries"][-1]
    house_fee = round(total * active_pot["house_fee_percent"] / 100, 2)
    payout = round(total - house_fee, 2)
    logger.info(f"Pot Revenue: buyback={house_fee*0.6:.2f}, growth={house_fee*0.3:.2f}, profit={house_fee*0.1:.2f}")
    result = {"winner": winner["display_name"], "winner_wallet": winner.get("wallet_address"),
              "payout": payout, "total_pot": total, "house_fee": house_fee,
              "entry_count": len(active_pot["entries"])}
    active_pot["winner"] = result
    active_pot["status"] = "completed"
    await db.pot_results.insert_one({**result, "pot_id": active_pot["id"], "drawn_at": datetime.now(timezone.utc).isoformat()})
    await pot_ws_manager.broadcast({"type": "pot_winner", "data": result})
    active_pot = {"id": str(uuid.uuid4()), "total_amount": 0, "entries": [], "status": "open",
                  "created_at": datetime.now(timezone.utc).isoformat(),
                  "draw_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                  "house_fee_percent": 7, "winner": None}
    await pot_ws_manager.broadcast({"type": "pot_update", "data": await _get_pot_data()})
    return result


async def _get_pot_data():
    entries_display = []
    for e in active_pot["entries"]:
        prob = round(e["amount"] / active_pot["total_amount"] * 100, 1) if active_pot["total_amount"] > 0 else 0
        entries_display.append({"display_name": e["display_name"], "amount": e["amount"], "probability": prob})
    return {"id": active_pot["id"], "total_amount": active_pot["total_amount"],
            "entry_count": len(active_pot["entries"]), "entries": entries_display,
            "status": active_pot["status"], "draw_at": active_pot["draw_at"],
            "house_fee_percent": active_pot["house_fee_percent"], "winner": active_pot["winner"]}


@api_router.get("/governance/proposals")
async def get_proposals():
    enriched = []
    for p in PROPOSALS:
        yes_count = await db.votes.count_documents({"proposal_id": p["id"], "vote": "yes"})
        no_count = await db.votes.count_documents({"proposal_id": p["id"], "vote": "no"})
        enriched.append({**p, "yes_votes": yes_count, "no_votes": no_count})
    return {"proposals": enriched}


@api_router.post("/governance/vote")
async def cast_vote(data: VoteRequest):
    existing = await db.votes.find_one({"proposal_id": data.proposal_id, "wallet_address": data.wallet_address}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Already voted")
    doc = {"id": str(uuid.uuid4()), "proposal_id": data.proposal_id, "vote": data.vote,
           "wallet_address": data.wallet_address, "voted_at": datetime.now(timezone.utc).isoformat()}
    await db.votes.insert_one(doc)
    return {"message": "Vote cast!", "vote": data.vote}


@api_router.post("/staking/simulate")
async def simulate_staking(data: StakingSimRequest):
    daily_rate = data.apy / 100 / 365
    balance = data.amount
    total_rewards = 0
    chart_data = []
    for day in range(1, data.duration_days + 1):
        reward = balance * daily_rate
        total_rewards += reward
        balance += reward
        if day % max(1, data.duration_days // 30) == 0 or day == data.duration_days:
            chart_data.append({"day": day, "balance": round(balance, 2), "rewards": round(total_rewards, 2)})
    return {"initial": data.amount, "final_balance": round(balance, 2), "total_rewards": round(total_rewards, 2),
            "apy": data.apy, "duration_days": data.duration_days,
            "guardian_points": int(data.amount * data.duration_days / 100), "chart_data": chart_data}


@api_router.post("/exit-simulator")
async def simulate_exit(data: ExitSimRequest):
    results = []
    for exit_price in data.exit_prices:
        investment = data.token_amount * data.entry_price
        value = data.token_amount * exit_price
        pnl = value - investment
        pnl_pct = ((exit_price - data.entry_price) / data.entry_price) * 100 if data.entry_price > 0 else 0
        tax = max(0, pnl * data.tax_rate / 100)
        net_pnl = pnl - tax
        results.append({"exit_price": exit_price, "value": round(value, 2), "pnl": round(pnl, 2),
                         "pnl_percent": round(pnl_pct, 2), "tax": round(tax, 2), "net_pnl": round(net_pnl, 2)})
    best = max(results, key=lambda r: r["net_pnl"])
    return {"investment": round(data.token_amount * data.entry_price, 2), "results": results,
            "optimal_exit": best, "token_amount": data.token_amount, "entry_price": data.entry_price}


@api_router.post("/exit-simulator/monte-carlo")
async def monte_carlo_simulation(data: MonteCarloRequest):
    """Monte Carlo simulation using Geometric Brownian Motion"""
    S0 = data.entry_price
    mu = data.drift
    sigma = data.volatility
    T = data.days / 365.0
    N = data.days
    M = min(data.simulations, 5000)
    dt = T / N

    np.random.seed(None)
    Z = np.random.standard_normal((M, N))
    S = np.zeros((M, N + 1))
    S[:, 0] = S0

    for t in range(1, N + 1):
        S[:, t] = S[:, t - 1] * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * Z[:, t - 1])

    final_prices = S[:, -1]
    investment = data.token_amount * S0
    final_values = data.token_amount * final_prices
    pnl = final_values - investment
    taxes = np.maximum(0, pnl * data.tax_rate / 100)
    net_pnl = pnl - taxes

    percentiles = [5, 10, 25, 50, 75, 90, 95]
    price_pcts = {f"p{p}": float(round(np.percentile(final_prices, p), 6)) for p in percentiles}
    pnl_pcts = {f"p{p}": float(round(np.percentile(net_pnl, p), 2)) for p in percentiles}

    # Sample paths for chart (10 paths + percentile bands)
    sample_idx = np.random.choice(M, min(10, M), replace=False)
    sample_days = list(range(0, N + 1, max(1, N // 60)))
    if N not in sample_days:
        sample_days.append(N)

    sample_paths = []
    for idx in sample_idx:
        sample_paths.append([float(round(S[idx, d], 6)) for d in sample_days])

    band_p5 = [float(round(np.percentile(S[:, d], 5), 6)) for d in sample_days]
    band_p25 = [float(round(np.percentile(S[:, d], 25), 6)) for d in sample_days]
    band_p50 = [float(round(np.percentile(S[:, d], 50), 6)) for d in sample_days]
    band_p75 = [float(round(np.percentile(S[:, d], 75), 6)) for d in sample_days]
    band_p95 = [float(round(np.percentile(S[:, d], 95), 6)) for d in sample_days]

    # Distribution histogram
    hist_counts, hist_edges = np.histogram(final_prices, bins=30)
    histogram = [{"min": float(round(hist_edges[i], 6)), "max": float(round(hist_edges[i + 1], 6)),
                  "count": int(hist_counts[i])} for i in range(len(hist_counts))]

    prob_profit = float(round(np.mean(net_pnl > 0) * 100, 1))
    prob_2x = float(round(np.mean(final_prices >= S0 * 2) * 100, 1))
    prob_5x = float(round(np.mean(final_prices >= S0 * 5) * 100, 1))
    prob_10x = float(round(np.mean(final_prices >= S0 * 10) * 100, 1))
    prob_loss50 = float(round(np.mean(final_prices <= S0 * 0.5) * 100, 1))

    return {
        "investment": round(investment, 2),
        "token_amount": data.token_amount,
        "entry_price": data.entry_price,
        "simulations": M,
        "days": data.days,
        "volatility": data.volatility,
        "drift": data.drift,
        "price_percentiles": price_pcts,
        "pnl_percentiles": pnl_pcts,
        "mean_final_price": float(round(np.mean(final_prices), 6)),
        "mean_pnl": float(round(np.mean(net_pnl), 2)),
        "median_pnl": float(round(np.median(net_pnl), 2)),
        "max_pnl": float(round(np.max(net_pnl), 2)),
        "min_pnl": float(round(np.min(net_pnl), 2)),
        "prob_profit": prob_profit,
        "prob_2x": prob_2x,
        "prob_5x": prob_5x,
        "prob_10x": prob_10x,
        "prob_loss50": prob_loss50,
        "chart": {
            "days": sample_days,
            "sample_paths": sample_paths,
            "bands": {"p5": band_p5, "p25": band_p25, "p50": band_p50, "p75": band_p75, "p95": band_p95},
        },
        "histogram": histogram,
        "tax_rate": data.tax_rate,
    }


@api_router.get("/tokenomics/stats")
async def get_tokenomics():
    total_bets = await db.bets.count_documents({})
    total_subs = await db.newsletter_subscribers.count_documents({})
    return {"total_supply": 1000000000, "circulating_supply": 800000000, "burned": 12500000,
            "burn_rate": "2%", "reflection_rate": "2%", "liquidity_rate": "1%",
            "distribution": {"community_liquidity": 80, "marketing_partnerships": 10, "developer_team": 5, "ecosystem_reserve": 5},
            "holders": 1247 + total_subs, "total_bets": total_bets,
            "price_usd": 0.00042, "market_cap": 420000, "volume_24h": 89000}


@api_router.get("/wallet/balance/{address}")
async def get_wallet_balance(address: str):
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                "https://api.mainnet-beta.solana.com",
                json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]},
                timeout=10.0
            )
            data = resp.json()
            if "result" in data:
                lamports = data["result"]["value"]
                return {"address": address, "balance_lamports": lamports, "balance_sol": lamports / 1e9}
    except Exception as e:
        logger.error(f"Balance error: {e}")
    return {"address": address, "balance_lamports": 0, "balance_sol": 0}


app.include_router(api_router)


# WebSocket for pot real-time updates
@app.websocket("/ws/pot")
async def pot_websocket(ws: WebSocket):
    await pot_ws_manager.connect(ws)
    try:
        await ws.send_json({"type": "pot_update", "data": await _get_pot_data()})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pot_ws_manager.disconnect(ws)
    except Exception:
        pot_ws_manager.disconnect(ws)


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    mongo_client.close()
