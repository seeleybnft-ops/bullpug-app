"""
Dynamic Whale Profit Scoring

Tracks the actual trade P&L of each smart money wallet over time.
Wallets with higher recent profitability get their signal weight increased,
while underperforming wallets get downgraded.

Self-improving: the system gets smarter as it observes more trades.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict
from utils.database import db

logger = logging.getLogger(__name__)

# Default weight decays toward this baseline
BASELINE_WEIGHT = 0.5

# Weight adjustment per trade outcome
WIN_BOOST = 0.05    # +5% weight per profitable trade
LOSS_PENALTY = 0.03  # -3% weight per losing trade
MAX_WEIGHT = 1.5     # Cap
MIN_WEIGHT = 0.1     # Floor

# How many recent trades to evaluate
EVAL_WINDOW_DAYS = 7


async def record_trade_outcome(wallet_address: str, token_mint: str, action: str, sol_amount: float, price_at_signal: float):
    """
    Record a smart money trade for future profit scoring.
    Called when we detect a whale buy/sell signal.
    """
    await db.whale_trade_history.insert_one({
        "wallet_address": wallet_address,
        "token_mint": token_mint,
        "action": action,
        "sol_amount": sol_amount,
        "price_at_signal": price_at_signal,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "outcome": None,  # Will be filled when we check the price later
        "outcome_checked_at": None
    })


async def evaluate_whale_outcomes():
    """
    Check the outcome of recent whale buy signals.
    If they bought a token and price went up 10%+ within 24h = WIN.
    If price dropped 10%+ = LOSS.
    """
    import httpx

    cutoff = (datetime.now(timezone.utc) - timedelta(days=EVAL_WINDOW_DAYS)).isoformat()

    # Get unscored buy signals from the past week
    pending = await db.whale_trade_history.find({
        "outcome": None,
        "action": "buy",
        "recorded_at": {"$gte": cutoff}
    }).to_list(50)

    if not pending:
        return 0

    scored = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for trade in pending:
            token_mint = trade.get("token_mint")
            entry_price = trade.get("price_at_signal", 0)
            recorded_at = trade.get("recorded_at", "")

            if not token_mint or entry_price <= 0:
                continue

            # Only evaluate trades older than 1 hour (give time for price movement)
            try:
                trade_time = datetime.fromisoformat(recorded_at)
                if (datetime.now(timezone.utc) - trade_time).total_seconds() < 3600:
                    continue
            except Exception:
                continue

            try:
                response = await client.get(
                    f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                )
                if response.status_code != 200:
                    continue

                pairs = response.json().get("pairs", [])
                if not pairs:
                    continue

                best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                current_price = float(best_pair.get("priceUsd", 0) or 0)

                if current_price <= 0:
                    continue

                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                if pnl_pct >= 10:
                    outcome = "win"
                elif pnl_pct <= -10:
                    outcome = "loss"
                else:
                    outcome = "neutral"

                await db.whale_trade_history.update_one(
                    {"_id": trade["_id"]},
                    {"$set": {
                        "outcome": outcome,
                        "outcome_price": current_price,
                        "outcome_pnl_pct": round(pnl_pct, 2),
                        "outcome_checked_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                scored += 1

            except Exception as e:
                logger.debug(f"Error evaluating whale trade: {e}")

    if scored > 0:
        logger.info(f"Evaluated {scored} whale trade outcomes")
    return scored


async def recalculate_wallet_weights() -> Dict[str, float]:
    """
    Recalculate dynamic weights for all whale wallets based on their
    recent trade performance.

    Returns:
        Dict mapping wallet_address -> dynamic_weight
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=EVAL_WINDOW_DAYS)).isoformat()

    # Aggregate wins/losses per wallet
    pipeline = [
        {"$match": {"outcome": {"$in": ["win", "loss"]}, "recorded_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$wallet_address",
            "wins": {"$sum": {"$cond": [{"$eq": ["$outcome", "win"]}, 1, 0]}},
            "losses": {"$sum": {"$cond": [{"$eq": ["$outcome", "loss"]}, 1, 0]}},
            "total_trades": {"$sum": 1},
            "avg_pnl": {"$avg": "$outcome_pnl_pct"}
        }}
    ]

    results = await db.whale_trade_history.aggregate(pipeline).to_list(100)
    dynamic_weights = {}

    for r in results:
        wallet = r["_id"]
        wins = r["wins"]
        losses = r["losses"]
        total = r["total_trades"]

        if total == 0:
            continue

        # Calculate dynamic weight adjustment
        weight = BASELINE_WEIGHT
        weight += wins * WIN_BOOST
        weight -= losses * LOSS_PENALTY

        # Win rate bonus: >70% win rate gets extra boost
        win_rate = wins / total
        if win_rate >= 0.7 and total >= 3:
            weight += 0.1
        elif win_rate <= 0.3 and total >= 3:
            weight -= 0.1

        # Clamp
        weight = max(MIN_WEIGHT, min(MAX_WEIGHT, weight))
        dynamic_weights[wallet] = round(weight, 3)

        logger.debug(f"Whale {wallet[:8]}...: {wins}W/{losses}L ({win_rate:.0%}) -> weight {weight:.3f}")

    # Store dynamic weights in DB for persistence
    if dynamic_weights:
        await db.whale_dynamic_weights.update_one(
            {"key": "weights"},
            {"$set": {
                "weights": dynamic_weights,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "wallets_scored": len(dynamic_weights)
            }},
            upsert=True
        )
        logger.info(f"Recalculated dynamic weights for {len(dynamic_weights)} whale wallets")

    return dynamic_weights


async def get_dynamic_weight(wallet_address: str, static_weight: float) -> float:
    """
    Get the dynamic weight for a wallet, falling back to static weight if no data.
    """
    cached = await db.whale_dynamic_weights.find_one({"key": "weights"})
    if cached and cached.get("weights"):
        return cached["weights"].get(wallet_address, static_weight)
    return static_weight
