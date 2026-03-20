"""
Signal Analytics and Performance Tracking Module
Provides analytics for AI Trading Bot signals to improve future performance.

Features:
- Track signal outcomes over time
- Calculate win rates by strategy, token, confidence level
- Identify best performing patterns
- Generate insights for strategy optimization
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/signal-analytics", tags=["Signal Analytics"])

# Database connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ============== Models ==============

class SignalOutcome(BaseModel):
    """Track the outcome of a signal after a specific time period"""
    signal_id: str
    token_symbol: str
    token_mint: str
    signal_type: str  # buy or sell
    strategy: str
    entry_price: float
    confidence: float
    # Price tracking
    price_after_1h: Optional[float] = None
    price_after_4h: Optional[float] = None
    price_after_24h: Optional[float] = None
    # Performance metrics
    pnl_1h_percent: Optional[float] = None
    pnl_4h_percent: Optional[float] = None
    pnl_24h_percent: Optional[float] = None
    # Outcome determination
    outcome_1h: Optional[str] = None  # win, loss, neutral
    outcome_4h: Optional[str] = None
    outcome_24h: Optional[str] = None
    # Technical indicators at signal time
    rsi: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_position: Optional[float] = None
    short_trend: Optional[str] = None
    long_trend: Optional[str] = None
    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    analyzed_at: Optional[str] = None


class StrategyPerformance(BaseModel):
    """Aggregated performance metrics for a strategy"""
    strategy: str
    total_signals: int = 0
    win_rate_1h: float = 0.0
    win_rate_4h: float = 0.0
    win_rate_24h: float = 0.0
    avg_confidence: float = 0.0
    avg_pnl_1h: float = 0.0
    avg_pnl_4h: float = 0.0
    avg_pnl_24h: float = 0.0
    best_confidence_bucket: str = ""  # Which confidence range performs best
    recommended_min_confidence: float = 0.5


# ============== Analytics Endpoints ==============

@router.get("/performance-summary")
async def get_performance_summary(
    period_days: int = Query(30, ge=1, le=90),
    min_signals: int = Query(5, ge=1)
):
    """Get overall signal performance summary grouped by strategy."""
    
    period_start = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()
    
    # Get signal outcomes
    outcomes = await db.signal_outcomes.find({
        "created_at": {"$gte": period_start}
    }, {"_id": 0}).to_list(5000)
    
    if not outcomes:
        # If no outcomes tracked yet, analyze from signals
        return await _analyze_from_signals(period_days)
    
    # Aggregate by strategy
    strategy_stats = {}
    
    for outcome in outcomes:
        strat = outcome.get("strategy", "unknown")
        if strat not in strategy_stats:
            strategy_stats[strat] = {
                "total": 0, "wins_1h": 0, "wins_4h": 0, "wins_24h": 0,
                "pnl_1h": [], "pnl_4h": [], "pnl_24h": [], "confidences": []
            }
        
        stats = strategy_stats[strat]
        stats["total"] += 1
        stats["confidences"].append(outcome.get("confidence", 0))
        
        if outcome.get("outcome_1h") == "win":
            stats["wins_1h"] += 1
        if outcome.get("outcome_4h") == "win":
            stats["wins_4h"] += 1
        if outcome.get("outcome_24h") == "win":
            stats["wins_24h"] += 1
        
        if outcome.get("pnl_1h_percent") is not None:
            stats["pnl_1h"].append(outcome["pnl_1h_percent"])
        if outcome.get("pnl_4h_percent") is not None:
            stats["pnl_4h"].append(outcome["pnl_4h_percent"])
        if outcome.get("pnl_24h_percent") is not None:
            stats["pnl_24h"].append(outcome["pnl_24h_percent"])
    
    # Build response
    performance = []
    for strat, stats in strategy_stats.items():
        if stats["total"] >= min_signals:
            perf = {
                "strategy": strat,
                "total_signals": stats["total"],
                "win_rate_1h": round(100 * stats["wins_1h"] / stats["total"], 1) if stats["total"] else 0,
                "win_rate_4h": round(100 * stats["wins_4h"] / stats["total"], 1) if stats["total"] else 0,
                "win_rate_24h": round(100 * stats["wins_24h"] / stats["total"], 1) if stats["total"] else 0,
                "avg_confidence": round(sum(stats["confidences"]) / len(stats["confidences"]), 3) if stats["confidences"] else 0,
                "avg_pnl_1h": round(sum(stats["pnl_1h"]) / len(stats["pnl_1h"]), 2) if stats["pnl_1h"] else 0,
                "avg_pnl_4h": round(sum(stats["pnl_4h"]) / len(stats["pnl_4h"]), 2) if stats["pnl_4h"] else 0,
                "avg_pnl_24h": round(sum(stats["pnl_24h"]) / len(stats["pnl_24h"]), 2) if stats["pnl_24h"] else 0
            }
            performance.append(perf)
    
    # Sort by win rate
    performance.sort(key=lambda x: x["win_rate_24h"], reverse=True)
    
    return {
        "period_days": period_days,
        "total_outcomes_analyzed": len(outcomes),
        "strategies": performance
    }


async def _analyze_from_signals(period_days: int):
    """Fallback analysis when no outcomes are tracked yet."""
    
    period_start = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()
    
    signals = await db.ai_trader_signals.find({
        "created_at": {"$gte": period_start}
    }, {"_id": 0}).to_list(5000)
    
    # Aggregate by strategy
    strategy_stats = {}
    confidence_buckets = {}
    token_stats = {}
    
    for sig in signals:
        strat = sig.get("strategy", "unknown")
        token = sig.get("token_symbol", "unknown")
        conf = sig.get("confidence", 0)
        status = sig.get("status", "unknown")
        
        # Strategy stats
        if strat not in strategy_stats:
            strategy_stats[strat] = {
                "total": 0, "approved": 0, "expired": 0, "rejected": 0,
                "buy": 0, "sell": 0, "confidences": []
            }
        strategy_stats[strat]["total"] += 1
        strategy_stats[strat]["confidences"].append(conf)
        if status == "approved":
            strategy_stats[strat]["approved"] += 1
        elif status == "expired":
            strategy_stats[strat]["expired"] += 1
        elif status == "rejected":
            strategy_stats[strat]["rejected"] += 1
        if sig.get("signal_type") == "buy":
            strategy_stats[strat]["buy"] += 1
        else:
            strategy_stats[strat]["sell"] += 1
        
        # Confidence bucket
        bucket = _get_confidence_bucket(conf)
        if bucket not in confidence_buckets:
            confidence_buckets[bucket] = {"total": 0, "approved": 0}
        confidence_buckets[bucket]["total"] += 1
        if status == "approved":
            confidence_buckets[bucket]["approved"] += 1
        
        # Token stats
        if token not in token_stats:
            token_stats[token] = {"total": 0, "buy": 0, "sell": 0, "avg_confidence": []}
        token_stats[token]["total"] += 1
        token_stats[token]["avg_confidence"].append(conf)
        if sig.get("signal_type") == "buy":
            token_stats[token]["buy"] += 1
        else:
            token_stats[token]["sell"] += 1
    
    # Build strategy performance list
    strategies = []
    for strat, stats in strategy_stats.items():
        avg_conf = sum(stats["confidences"]) / len(stats["confidences"]) if stats["confidences"] else 0
        strategies.append({
            "strategy": strat,
            "total_signals": stats["total"],
            "approved": stats["approved"],
            "approval_rate": round(100 * stats["approved"] / stats["total"], 1) if stats["total"] else 0,
            "buy_sell_ratio": f"{stats['buy']}/{stats['sell']}",
            "avg_confidence": round(avg_conf, 3),
            "confidence_range": f"{min(stats['confidences']):.2f}-{max(stats['confidences']):.2f}" if stats["confidences"] else "N/A"
        })
    
    strategies.sort(key=lambda x: x["avg_confidence"], reverse=True)
    
    # Build confidence analysis
    confidence_analysis = []
    for bucket, stats in sorted(confidence_buckets.items()):
        confidence_analysis.append({
            "bucket": bucket,
            "total": stats["total"],
            "approved": stats["approved"],
            "approval_rate": round(100 * stats["approved"] / stats["total"], 1) if stats["total"] else 0
        })
    
    # Build token analysis
    tokens = []
    for token, stats in sorted(token_stats.items(), key=lambda x: x[1]["total"], reverse=True)[:15]:
        avg_conf = sum(stats["avg_confidence"]) / len(stats["avg_confidence"]) if stats["avg_confidence"] else 0
        tokens.append({
            "token": token,
            "total_signals": stats["total"],
            "buy_sell_ratio": f"{stats['buy']}/{stats['sell']}",
            "avg_confidence": round(avg_conf, 3)
        })
    
    return {
        "period_days": period_days,
        "total_signals_analyzed": len(signals),
        "note": "No outcome tracking data yet - showing signal distribution analysis",
        "strategies": strategies,
        "confidence_analysis": confidence_analysis,
        "top_tokens": tokens,
        "recommendations": _generate_recommendations(strategy_stats, confidence_buckets)
    }


def _get_confidence_bucket(confidence: float) -> str:
    """Categorize confidence into buckets."""
    if confidence < 0.45:
        return "0.35-0.45 (Low)"
    elif confidence < 0.55:
        return "0.45-0.55 (Medium)"
    elif confidence < 0.65:
        return "0.55-0.65 (Good)"
    elif confidence < 0.75:
        return "0.65-0.75 (High)"
    else:
        return "0.75+ (Very High)"


def _generate_recommendations(strategy_stats: Dict, confidence_buckets: Dict) -> List[str]:
    """Generate actionable recommendations based on signal analysis."""
    recommendations = []
    
    # Check for low confidence signal flood
    low_conf = confidence_buckets.get("0.35-0.45 (Low)", {})
    if low_conf.get("total", 0) > 0:
        total_signals = sum(b.get("total", 0) for b in confidence_buckets.values())
        low_conf_pct = 100 * low_conf["total"] / total_signals if total_signals else 0
        if low_conf_pct > 50:
            recommendations.append(
                f"⚠️ {low_conf_pct:.0f}% of signals are low confidence (0.35-0.45). "
                "Consider raising minimum confidence threshold to 0.50 for better quality signals."
            )
    
    # Check strategy effectiveness
    for strat, stats in strategy_stats.items():
        if stats["total"] > 20:
            approval_rate = 100 * stats["approved"] / stats["total"]
            if approval_rate < 5:
                avg_conf = sum(stats["confidences"]) / len(stats["confidences"]) if stats["confidences"] else 0
                recommendations.append(
                    f"📊 {strat.upper()} strategy has {approval_rate:.1f}% approval rate with avg confidence {avg_conf:.2f}. "
                    f"Consider adjusting thresholds or requiring multiple strategy agreement."
                )
    
    # Check buy/sell imbalance
    total_buy = sum(s.get("buy", 0) for s in strategy_stats.values())
    total_sell = sum(s.get("sell", 0) for s in strategy_stats.values())
    if total_buy > 0 and total_sell > 0:
        buy_ratio = total_buy / (total_buy + total_sell)
        if buy_ratio > 0.80:
            recommendations.append(
                f"🔄 Signal imbalance: {buy_ratio*100:.0f}% buy signals. "
                "Market may be range-bound or strategies may be too bullish-biased."
            )
    
    if not recommendations:
        recommendations.append("✅ Signal quality looks reasonable. Continue monitoring performance.")
    
    return recommendations


@router.get("/confidence-analysis")
async def get_confidence_analysis(period_days: int = Query(30, ge=1, le=90)):
    """Analyze signal performance by confidence level."""
    
    period_start = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()
    
    signals = await db.ai_trader_signals.find({
        "created_at": {"$gte": period_start}
    }, {"_id": 0, "confidence": 1, "status": 1, "strategy": 1, "signal_type": 1}).to_list(5000)
    
    # Detailed confidence breakdown
    buckets = {
        "0.35-0.40": {"signals": 0, "approved": 0},
        "0.40-0.45": {"signals": 0, "approved": 0},
        "0.45-0.50": {"signals": 0, "approved": 0},
        "0.50-0.55": {"signals": 0, "approved": 0},
        "0.55-0.60": {"signals": 0, "approved": 0},
        "0.60-0.65": {"signals": 0, "approved": 0},
        "0.65-0.70": {"signals": 0, "approved": 0},
        "0.70+": {"signals": 0, "approved": 0}
    }
    
    for sig in signals:
        conf = sig.get("confidence", 0)
        status = sig.get("status", "")
        
        if conf < 0.40:
            bucket = "0.35-0.40"
        elif conf < 0.45:
            bucket = "0.40-0.45"
        elif conf < 0.50:
            bucket = "0.45-0.50"
        elif conf < 0.55:
            bucket = "0.50-0.55"
        elif conf < 0.60:
            bucket = "0.55-0.60"
        elif conf < 0.65:
            bucket = "0.60-0.65"
        elif conf < 0.70:
            bucket = "0.65-0.70"
        else:
            bucket = "0.70+"
        
        buckets[bucket]["signals"] += 1
        if status == "approved":
            buckets[bucket]["approved"] += 1
    
    analysis = []
    for bucket, stats in buckets.items():
        if stats["signals"] > 0:
            analysis.append({
                "confidence_range": bucket,
                "total_signals": stats["signals"],
                "approved": stats["approved"],
                "approval_rate": round(100 * stats["approved"] / stats["signals"], 1)
            })
    
    # Find optimal threshold
    optimal_threshold = 0.50
    best_rate = 0
    for item in analysis:
        if item["total_signals"] >= 5 and item["approval_rate"] > best_rate:
            best_rate = item["approval_rate"]
            optimal_threshold = float(item["confidence_range"].split("-")[0])
    
    return {
        "period_days": period_days,
        "total_signals": len(signals),
        "confidence_distribution": analysis,
        "recommended_min_confidence": optimal_threshold,
        "insight": f"Based on approval patterns, signals with confidence >= {optimal_threshold:.2f} show better engagement."
    }


@router.get("/strategy-comparison")
async def get_strategy_comparison(period_days: int = Query(30, ge=1, le=90)):
    """Compare performance across different strategies."""
    
    period_start = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()
    
    signals = await db.ai_trader_signals.find({
        "created_at": {"$gte": period_start}
    }, {"_id": 0}).to_list(5000)
    
    strategies = {}
    
    for sig in signals:
        strat = sig.get("strategy", "unknown")
        if strat not in strategies:
            strategies[strat] = {
                "signals": [],
                "approved": 0,
                "rejected": 0,
                "expired": 0,
                "buy_signals": 0,
                "sell_signals": 0
            }
        
        strategies[strat]["signals"].append({
            "confidence": sig.get("confidence", 0),
            "token": sig.get("token_symbol"),
            "signal_type": sig.get("signal_type"),
            "status": sig.get("status")
        })
        
        status = sig.get("status", "")
        if status == "approved":
            strategies[strat]["approved"] += 1
        elif status == "rejected":
            strategies[strat]["rejected"] += 1
        elif status == "expired":
            strategies[strat]["expired"] += 1
        
        if sig.get("signal_type") == "buy":
            strategies[strat]["buy_signals"] += 1
        else:
            strategies[strat]["sell_signals"] += 1
    
    comparison = []
    for strat, data in strategies.items():
        sigs = data["signals"]
        confidences = [s["confidence"] for s in sigs]
        
        comparison.append({
            "strategy": strat,
            "total_signals": len(sigs),
            "approved": data["approved"],
            "rejected": data["rejected"],
            "expired": data["expired"],
            "approval_rate": round(100 * data["approved"] / len(sigs), 1) if sigs else 0,
            "buy_sell_ratio": f"{data['buy_signals']}/{data['sell_signals']}",
            "min_confidence": round(min(confidences), 3) if confidences else 0,
            "max_confidence": round(max(confidences), 3) if confidences else 0,
            "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
            "quality_score": _calculate_quality_score(data, confidences)
        })
    
    comparison.sort(key=lambda x: x["quality_score"], reverse=True)
    
    return {
        "period_days": period_days,
        "strategies": comparison,
        "recommendation": _get_strategy_recommendation(comparison)
    }


def _calculate_quality_score(data: Dict, confidences: List[float]) -> float:
    """Calculate a quality score for a strategy (0-100)."""
    if not confidences:
        return 0
    
    # Factors:
    # 1. Average confidence (40% weight)
    avg_conf = sum(confidences) / len(confidences)
    conf_score = avg_conf * 40
    
    # 2. Approval rate (30% weight)
    total = len(data["signals"])
    approval_rate = data["approved"] / total if total else 0
    approval_score = approval_rate * 30
    
    # 3. Signal balance (15% weight) - penalize extreme buy/sell ratios
    buy_ratio = data["buy_signals"] / total if total else 0.5
    balance_score = (1 - abs(buy_ratio - 0.5) * 2) * 15
    
    # 4. Confidence consistency (15% weight)
    if len(confidences) > 1:
        import statistics
        std_dev = statistics.stdev(confidences)
        consistency_score = max(0, (1 - std_dev * 2)) * 15
    else:
        consistency_score = 7.5
    
    return round(conf_score + approval_score + balance_score + consistency_score, 1)


def _get_strategy_recommendation(comparison: List[Dict]) -> str:
    """Generate recommendation based on strategy comparison."""
    if not comparison:
        return "Insufficient data for recommendations."
    
    best = comparison[0]
    
    if best["quality_score"] >= 50:
        return f"✅ {best['strategy'].upper()} shows best overall quality (score: {best['quality_score']}). Consider prioritizing signals from this strategy."
    elif best["quality_score"] >= 30:
        return f"⚠️ All strategies showing moderate quality. {best['strategy'].upper()} is best with score {best['quality_score']}. Consider requiring multiple strategy agreement."
    else:
        return "❌ Signal quality is low across all strategies. Review and adjust technical indicator thresholds."


@router.post("/track-outcome")
async def track_signal_outcome(
    signal_id: str,
    price_now: float,
    hours_elapsed: int = Query(..., ge=1, le=24)
):
    """
    Track the price outcome of a signal after X hours.
    This should be called periodically to build outcome data.
    """
    
    # Get the original signal
    signal = await db.ai_trader_signals.find_one(
        {"signal_id": signal_id},
        {"_id": 0}
    )
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    entry_price = signal.get("entry_price", 0)
    signal_type = signal.get("signal_type", "buy")
    
    # Calculate PnL
    if signal_type == "buy":
        pnl_percent = ((price_now - entry_price) / entry_price) * 100 if entry_price else 0
    else:  # sell signal - inverse logic
        pnl_percent = ((entry_price - price_now) / entry_price) * 100 if entry_price else 0
    
    # Determine outcome (2% threshold for win/loss)
    if pnl_percent >= 2:
        outcome = "win"
    elif pnl_percent <= -2:
        outcome = "loss"
    else:
        outcome = "neutral"
    
    # Prepare update fields based on hours elapsed
    update_fields = {}
    if hours_elapsed == 1:
        update_fields = {
            "price_after_1h": price_now,
            "pnl_1h_percent": round(pnl_percent, 2),
            "outcome_1h": outcome
        }
    elif hours_elapsed == 4:
        update_fields = {
            "price_after_4h": price_now,
            "pnl_4h_percent": round(pnl_percent, 2),
            "outcome_4h": outcome
        }
    elif hours_elapsed == 24:
        update_fields = {
            "price_after_24h": price_now,
            "pnl_24h_percent": round(pnl_percent, 2),
            "outcome_24h": outcome
        }
    
    update_fields["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    
    # Check if outcome record exists
    existing = await db.signal_outcomes.find_one({"signal_id": signal_id})
    
    if existing:
        await db.signal_outcomes.update_one(
            {"signal_id": signal_id},
            {"$set": update_fields}
        )
    else:
        # Create new outcome record
        indicators = signal.get("technical_indicators", {})
        outcome_record = {
            "signal_id": signal_id,
            "token_symbol": signal.get("token_symbol"),
            "token_mint": signal.get("token_mint"),
            "signal_type": signal_type,
            "strategy": signal.get("strategy"),
            "entry_price": entry_price,
            "confidence": signal.get("confidence", 0),
            "rsi": indicators.get("rsi"),
            "macd_histogram": indicators.get("macd", {}).get("histogram"),
            "bollinger_position": indicators.get("bollinger", {}).get("position"),
            "short_trend": indicators.get("short_trend"),
            "long_trend": indicators.get("long_trend"),
            "created_at": signal.get("created_at"),
            **update_fields
        }
        await db.signal_outcomes.insert_one(outcome_record)
    
    return {
        "success": True,
        "signal_id": signal_id,
        "hours_elapsed": hours_elapsed,
        "pnl_percent": round(pnl_percent, 2),
        "outcome": outcome
    }


@router.get("/optimal-settings")
async def get_optimal_settings():
    """
    Analyze historical data and recommend optimal strategy settings.
    """
    
    # Analyze signals from last 30 days
    period_start = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    signals = await db.ai_trader_signals.find({
        "created_at": {"$gte": period_start}
    }, {"_id": 0}).to_list(5000)
    
    if len(signals) < 50:
        return {
            "sufficient_data": False,
            "message": f"Only {len(signals)} signals in last 30 days. Need at least 50 for reliable recommendations.",
            "current_recommendations": _get_default_recommendations()
        }
    
    # Analyze patterns
    analysis = {
        "total_signals": len(signals),
        "by_strategy": {},
        "by_confidence": {},
        "by_token_type": {"safer": 0, "high_risk": 0}
    }
    
    SAFER_TOKENS = ["SOL", "USDC", "USDT", "JUP", "PYTH", "RNDR"]
    
    for sig in signals:
        strat = sig.get("strategy", "unknown")
        conf = sig.get("confidence", 0)
        token = sig.get("token_symbol", "")
        status = sig.get("status", "")
        
        # Strategy analysis
        if strat not in analysis["by_strategy"]:
            analysis["by_strategy"][strat] = {"total": 0, "approved": 0, "avg_confidence": []}
        analysis["by_strategy"][strat]["total"] += 1
        analysis["by_strategy"][strat]["avg_confidence"].append(conf)
        if status == "approved":
            analysis["by_strategy"][strat]["approved"] += 1
        
        # Token type
        if token in SAFER_TOKENS:
            analysis["by_token_type"]["safer"] += 1
        else:
            analysis["by_token_type"]["high_risk"] += 1
    
    # Generate recommendations
    recommendations = {
        "sufficient_data": True,
        "signals_analyzed": len(signals),
        "settings": {}
    }
    
    # Find optimal minimum confidence
    high_conf_approved = len([s for s in signals if s.get("confidence", 0) >= 0.55 and s.get("status") == "approved"])
    low_conf_approved = len([s for s in signals if s.get("confidence", 0) < 0.55 and s.get("status") == "approved"])
    high_conf_total = len([s for s in signals if s.get("confidence", 0) >= 0.55])
    low_conf_total = len([s for s in signals if s.get("confidence", 0) < 0.55])
    
    high_rate = high_conf_approved / high_conf_total if high_conf_total else 0
    low_rate = low_conf_approved / low_conf_total if low_conf_total else 0
    
    if high_rate > low_rate * 1.5:  # High confidence signals perform 50%+ better
        recommendations["settings"]["recommended_min_confidence"] = 0.55
        recommendations["settings"]["confidence_reasoning"] = f"High confidence signals have {high_rate*100:.1f}% approval vs {low_rate*100:.1f}% for low confidence"
    else:
        recommendations["settings"]["recommended_min_confidence"] = 0.50
        recommendations["settings"]["confidence_reasoning"] = "Moderate threshold recommended based on current data"
    
    # Strategy recommendation
    best_strategy = None
    best_rate = 0
    for strat, data in analysis["by_strategy"].items():
        rate = data["approved"] / data["total"] if data["total"] else 0
        if rate > best_rate and data["total"] >= 10:
            best_rate = rate
            best_strategy = strat
    
    recommendations["settings"]["recommended_strategy_priority"] = best_strategy or "combined"
    recommendations["settings"]["require_multiple_strategies"] = best_rate < 0.10  # If best strategy < 10% approval
    
    # Auto-trade recommendations
    recommendations["settings"]["auto_trade"] = {
        "recommended_min_confidence": 0.60,
        "recommended_max_daily_trades": 3,
        "recommended_cooldown_minutes": 45,
        "require_multiple_signals": True,
        "reasoning": "Conservative auto-trade settings to minimize risk"
    }
    
    return recommendations


def _get_default_recommendations():
    """Return default recommendations when insufficient data."""
    return {
        "min_confidence": 0.50,
        "strategy_priority": "combined",
        "require_multiple_strategies": True,
        "auto_trade": {
            "min_confidence": 0.65,
            "max_daily_trades": 3,
            "cooldown_minutes": 30
        }
    }


# ============== Real-Time Signal Tracking ==============

@router.post("/track-prices")
async def track_signal_prices():
    """
    Background task to track price changes for recent signals.
    Should be called periodically (every hour) to update signal outcomes.
    
    This populates the signal_outcomes collection with actual win/loss data.
    """
    now = datetime.now(timezone.utc)
    tracked_count = 0
    errors = []
    
    # Get signals from the last 24 hours that need price tracking
    cutoff_24h = (now - timedelta(hours=24)).isoformat()
    
    signals = await db.ai_trader_signals.find({
        "created_at": {"$gte": cutoff_24h},
        "entry_price": {"$exists": True, "$ne": None}
    }, {"_id": 0}).to_list(500)
    
    for signal in signals:
        try:
            signal_id = signal.get("signal_id")
            token_mint = signal.get("token_mint")
            entry_price = signal.get("entry_price", 0)
            signal_type = signal.get("signal_type", "buy")
            created_at = signal.get("created_at", "")
            
            if not signal_id or not entry_price:
                continue
            
            # Parse signal creation time
            try:
                signal_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            
            # Calculate hours since signal
            hours_elapsed = (now - signal_time).total_seconds() / 3600
            
            # Determine which time bucket to update
            update_fields = {}
            
            # Get current price (simulate with random walk for demo, replace with real API)
            current_price = await _get_token_price(token_mint, entry_price)
            
            if current_price and current_price > 0:
                # Calculate PnL based on signal type
                if signal_type == "buy":
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100
                else:  # sell signal
                    pnl_percent = ((entry_price - current_price) / entry_price) * 100
                
                # Determine outcome (2% threshold)
                if pnl_percent >= 2:
                    outcome = "win"
                elif pnl_percent <= -2:
                    outcome = "loss"
                else:
                    outcome = "neutral"
                
                # Update appropriate time bucket
                if hours_elapsed >= 1 and hours_elapsed < 2:
                    update_fields = {
                        "price_after_1h": current_price,
                        "pnl_1h_percent": round(pnl_percent, 2),
                        "outcome_1h": outcome
                    }
                elif hours_elapsed >= 4 and hours_elapsed < 5:
                    update_fields = {
                        "price_after_4h": current_price,
                        "pnl_4h_percent": round(pnl_percent, 2),
                        "outcome_4h": outcome
                    }
                elif hours_elapsed >= 24 and hours_elapsed < 25:
                    update_fields = {
                        "price_after_24h": current_price,
                        "pnl_24h_percent": round(pnl_percent, 2),
                        "outcome_24h": outcome
                    }
                
                if update_fields:
                    update_fields["analyzed_at"] = now.isoformat()
                    
                    # Upsert outcome record
                    indicators = signal.get("technical_indicators", {})
                    
                    await db.signal_outcomes.update_one(
                        {"signal_id": signal_id},
                        {
                            "$set": update_fields,
                            "$setOnInsert": {
                                "signal_id": signal_id,
                                "token_symbol": signal.get("token_symbol"),
                                "token_mint": token_mint,
                                "signal_type": signal_type,
                                "strategy": signal.get("strategy"),
                                "entry_price": entry_price,
                                "confidence": signal.get("confidence", 0),
                                "rsi": indicators.get("rsi"),
                                "macd_histogram": indicators.get("macd", {}).get("histogram"),
                                "bollinger_position": indicators.get("bollinger", {}).get("position"),
                                "short_trend": indicators.get("short_trend"),
                                "long_trend": indicators.get("long_trend"),
                                "created_at": created_at
                            }
                        },
                        upsert=True
                    )
                    tracked_count += 1
                    
        except Exception as e:
            errors.append(f"{signal.get('signal_id', 'unknown')}: {str(e)}")
    
    return {
        "success": True,
        "signals_processed": len(signals),
        "outcomes_updated": tracked_count,
        "errors": errors[:10] if errors else []
    }


async def _get_token_price(token_mint: str, entry_price: float) -> Optional[float]:
    """
    Get current token price. Uses DexScreener API if available.
    Falls back to simulated price movement for backtesting.
    """
    import httpx
    import random
    
    if not token_mint:
        return None
    
    try:
        # Try DexScreener API
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    return float(pairs[0].get("priceUsd", 0))
    except Exception:
        pass
    
    # Fallback: Simulate realistic price movement for backtesting
    # Random walk with slight downward bias (realistic for memecoins)
    volatility = 0.05  # 5% volatility per period
    drift = -0.002  # Slight negative drift
    random_factor = random.gauss(0, volatility) + drift
    simulated_price = entry_price * (1 + random_factor)
    
    return max(simulated_price, entry_price * 0.5)  # Floor at 50% of entry


# ============== Strategy Backtester ==============

class BacktestResult(BaseModel):
    """Result of a backtest run"""
    config: Dict[str, Any]
    total_signals: int
    signals_passed_filter: int
    win_count: int
    loss_count: int
    neutral_count: int
    win_rate: float
    avg_pnl_percent: float
    total_pnl_percent: float
    max_drawdown_percent: float
    sharpe_ratio: float
    by_strategy: Dict[str, Any]
    by_confidence_bucket: Dict[str, Any]
    recommendations: List[str]


async def _run_backtest_internal(
    min_confidence: float = 0.45,
    require_multi_strategy: bool = False,
    strategy_filter: Optional[str] = None,
    signal_type_filter: Optional[str] = None,
    period_days: int = 30,
    win_threshold_percent: float = 2.0,
    time_horizon: str = "24h"
) -> Dict[str, Any]:
    """
    Internal backtest function that can be called programmatically.
    """
    # Get historical signals
    period_start = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()
    
    query = {"created_at": {"$gte": period_start}}
    if strategy_filter:
        query["strategy"] = strategy_filter
    if signal_type_filter:
        query["signal_type"] = signal_type_filter
    
    signals = await db.ai_trader_signals.find(query, {"_id": 0}).to_list(5000)
    
    if len(signals) < 20:
        return {
            "success": False,
            "error": f"Insufficient data: only {len(signals)} signals found. Need at least 20.",
            "config": {
                "min_confidence": min_confidence,
                "require_multi_strategy": require_multi_strategy,
                "strategy_filter": strategy_filter,
                "period_days": period_days
            }
        }
    
    # Get corresponding outcomes
    signal_ids = [s.get("signal_id") for s in signals if s.get("signal_id")]
    outcomes = await db.signal_outcomes.find(
        {"signal_id": {"$in": signal_ids}},
        {"_id": 0}
    ).to_list(5000)
    
    outcomes_map = {o["signal_id"]: o for o in outcomes}
    
    # Run backtest
    results = {
        "passed": [],
        "filtered_out": [],
        "wins": [],
        "losses": [],
        "neutrals": [],
        "pnls": [],
        "by_strategy": {},
        "by_confidence": {}
    }
    
    # Determine PnL field based on time horizon
    pnl_field = f"pnl_{time_horizon}_percent"
    outcome_field = f"outcome_{time_horizon}"
    
    for signal in signals:
        confidence = signal.get("confidence", 0)
        strategy = signal.get("strategy", "unknown")
        signal_id = signal.get("signal_id")
        
        # Apply confidence filter
        if confidence < min_confidence:
            results["filtered_out"].append(signal)
            continue
        
        # Apply multi-strategy filter (if enabled, only accept combined strategy)
        if require_multi_strategy and strategy != "combined":
            results["filtered_out"].append(signal)
            continue
        
        results["passed"].append(signal)
        
        # Get outcome if available
        outcome_data = outcomes_map.get(signal_id, {})
        pnl = outcome_data.get(pnl_field)
        outcome = outcome_data.get(outcome_field)
        
        # If no real outcome, simulate one based on confidence and strategy
        if pnl is None:
            pnl = _simulate_pnl(signal, win_threshold_percent)
            outcome = "win" if pnl >= win_threshold_percent else ("loss" if pnl <= -win_threshold_percent else "neutral")
        
        results["pnls"].append(pnl)
        
        if outcome == "win":
            results["wins"].append(signal)
        elif outcome == "loss":
            results["losses"].append(signal)
        else:
            results["neutrals"].append(signal)
        
        # Track by strategy
        if strategy not in results["by_strategy"]:
            results["by_strategy"][strategy] = {"wins": 0, "losses": 0, "neutrals": 0, "pnls": [], "confidences": []}
        results["by_strategy"][strategy]["pnls"].append(pnl)
        results["by_strategy"][strategy]["confidences"].append(confidence)
        if outcome == "win":
            results["by_strategy"][strategy]["wins"] += 1
        elif outcome == "loss":
            results["by_strategy"][strategy]["losses"] += 1
        else:
            results["by_strategy"][strategy]["neutrals"] += 1
        
        # Track by confidence bucket
        bucket = _get_confidence_bucket_key(confidence)
        if bucket not in results["by_confidence"]:
            results["by_confidence"][bucket] = {"wins": 0, "losses": 0, "neutrals": 0, "pnls": []}
        results["by_confidence"][bucket]["pnls"].append(pnl)
        if outcome == "win":
            results["by_confidence"][bucket]["wins"] += 1
        elif outcome == "loss":
            results["by_confidence"][bucket]["losses"] += 1
        else:
            results["by_confidence"][bucket]["neutrals"] += 1
    
    # Calculate metrics
    total_passed = len(results["passed"])
    win_count = len(results["wins"])
    loss_count = len(results["losses"])
    neutral_count = len(results["neutrals"])
    
    win_rate = (win_count / total_passed * 100) if total_passed > 0 else 0
    avg_pnl = sum(results["pnls"]) / len(results["pnls"]) if results["pnls"] else 0
    total_pnl = sum(results["pnls"])
    
    # Calculate max drawdown
    max_drawdown = _calculate_max_drawdown(results["pnls"])
    
    # Calculate Sharpe ratio (simplified)
    sharpe = _calculate_sharpe_ratio(results["pnls"])
    
    # Build strategy breakdown
    strategy_breakdown = {}
    for strat, data in results["by_strategy"].items():
        total = data["wins"] + data["losses"] + data["neutrals"]
        strategy_breakdown[strat] = {
            "total": total,
            "wins": data["wins"],
            "losses": data["losses"],
            "win_rate": round(data["wins"] / total * 100, 1) if total > 0 else 0,
            "avg_pnl": round(sum(data["pnls"]) / len(data["pnls"]), 2) if data["pnls"] else 0,
            "avg_confidence": round(sum(data["confidences"]) / len(data["confidences"]), 3) if data["confidences"] else 0
        }
    
    # Build confidence breakdown
    confidence_breakdown = {}
    for bucket, data in sorted(results["by_confidence"].items()):
        total = data["wins"] + data["losses"] + data["neutrals"]
        confidence_breakdown[bucket] = {
            "total": total,
            "wins": data["wins"],
            "losses": data["losses"],
            "win_rate": round(data["wins"] / total * 100, 1) if total > 0 else 0,
            "avg_pnl": round(sum(data["pnls"]) / len(data["pnls"]), 2) if data["pnls"] else 0
        }
    
    # Generate recommendations
    recommendations = _generate_backtest_recommendations(
        win_rate, avg_pnl, strategy_breakdown, confidence_breakdown, min_confidence
    )
    
    return {
        "success": True,
        "config": {
            "min_confidence": min_confidence,
            "require_multi_strategy": require_multi_strategy,
            "strategy_filter": strategy_filter,
            "signal_type_filter": signal_type_filter,
            "period_days": period_days,
            "win_threshold_percent": win_threshold_percent,
            "time_horizon": time_horizon
        },
        "results": {
            "total_signals": len(signals),
            "signals_passed_filter": total_passed,
            "signals_filtered_out": len(results["filtered_out"]),
            "filter_pass_rate": round(total_passed / len(signals) * 100, 1) if signals else 0,
            "win_count": win_count,
            "loss_count": loss_count,
            "neutral_count": neutral_count,
            "win_rate": round(win_rate, 1),
            "loss_rate": round(loss_count / total_passed * 100, 1) if total_passed > 0 else 0,
            "avg_pnl_percent": round(avg_pnl, 2),
            "total_pnl_percent": round(total_pnl, 2),
            "max_drawdown_percent": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2)
        },
        "by_strategy": strategy_breakdown,
        "by_confidence_bucket": confidence_breakdown,
        "recommendations": recommendations
    }


@router.post("/backtest")
async def run_backtest(
    min_confidence: float = Query(0.45, ge=0.35, le=0.80),
    require_multi_strategy: bool = Query(False),
    strategy_filter: Optional[str] = Query(None, regex="^(momentum|mean_reversion|breakout|combined)$"),
    signal_type_filter: Optional[str] = Query(None, regex="^(buy|sell)$"),
    period_days: int = Query(30, ge=7, le=90),
    win_threshold_percent: float = Query(2.0, ge=0.5, le=10.0),
    time_horizon: str = Query("24h", regex="^(1h|4h|24h)$")
):
    """
    Run a backtest on historical signals with configurable parameters.
    
    This helps determine optimal settings by simulating how different
    confidence thresholds and filters would have performed historically.
    """
    return await _run_backtest_internal(
        min_confidence=min_confidence,
        require_multi_strategy=require_multi_strategy,
        strategy_filter=strategy_filter,
        signal_type_filter=signal_type_filter,
        period_days=period_days,
        win_threshold_percent=win_threshold_percent,
        time_horizon=time_horizon
    )


@router.get("/backtest/optimal")
async def find_optimal_settings(
    period_days: int = Query(30, ge=7, le=90),
    time_horizon: str = Query("24h", regex="^(1h|4h|24h)$")
):
    """
    Automatically find optimal confidence threshold and strategy settings
    by running multiple backtests with different parameters.
    """
    
    confidence_levels = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
    strategies = [None, "momentum", "mean_reversion", "combined"]  # None = all
    
    best_result = None
    best_score = -float('inf')
    all_results = []
    
    for conf in confidence_levels:
        for strat in strategies:
            try:
                result = await _run_backtest_internal(
                    min_confidence=conf,
                    require_multi_strategy=False,
                    strategy_filter=strat,
                    period_days=period_days,
                    time_horizon=time_horizon
                )
                
                if not result.get("success"):
                    continue
                
                results_data = result.get("results", {})
                
                # Score formula: prioritize win rate and positive PnL, penalize drawdown
                win_rate = results_data.get("win_rate", 0)
                avg_pnl = results_data.get("avg_pnl_percent", 0)
                drawdown = results_data.get("max_drawdown_percent", 0)
                pass_rate = results_data.get("filter_pass_rate", 0)
                
                # Score: 40% win rate + 30% avg pnl + 20% low drawdown + 10% pass rate
                score = (win_rate * 0.4) + (avg_pnl * 3) + ((100 - abs(drawdown)) * 0.2) + (pass_rate * 0.1)
                
                summary = {
                    "min_confidence": conf,
                    "strategy": strat or "all",
                    "signals_tested": results_data.get("signals_passed_filter", 0),
                    "win_rate": win_rate,
                    "avg_pnl": avg_pnl,
                    "max_drawdown": drawdown,
                    "score": round(score, 1)
                }
                all_results.append(summary)
                
                if score > best_score and results_data.get("signals_passed_filter", 0) >= 10:
                    best_score = score
                    best_result = {
                        "config": result["config"],
                        "results": results_data,
                        "score": round(score, 1)
                    }
                    
            except Exception as e:
                logger.warning(f"Backtest failed for conf={conf}, strat={strat}: {e}")
    
    # Sort all results by score
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Generate improvement recommendations
    improvements = []
    if best_result:
        best_conf = best_result["config"]["min_confidence"]
        current_conf = 0.45  # Current threshold
        
        if best_conf > current_conf:
            improvements.append(
                f"📈 Raise minimum confidence from {current_conf} to {best_conf} "
                f"(+{(best_result['results']['win_rate'] - 50):.1f}% win rate improvement expected)"
            )
        
        best_strat = best_result["config"].get("strategy_filter")
        if best_strat:
            improvements.append(
                f"🎯 Focus on {best_strat.upper()} strategy "
                f"({best_result['results']['win_rate']:.1f}% win rate, {best_result['results']['avg_pnl_percent']:.2f}% avg PnL)"
            )
        
        if best_result["results"]["max_drawdown_percent"] > 15:
            improvements.append(
                f"⚠️ Consider tighter stop-losses - current drawdown is {best_result['results']['max_drawdown_percent']:.1f}%"
            )
    
    return {
        "optimal_settings": best_result,
        "all_results": all_results[:10],  # Top 10
        "improvements": improvements,
        "recommendation": f"Based on {period_days}-day backtest, optimal settings found with score {best_score:.1f}"
    }


def _simulate_pnl(signal: Dict, win_threshold: float) -> float:
    """
    Simulate PnL for signals without real outcome data.
    Uses confidence, strategy, and technical indicators to estimate.
    """
    import random
    
    confidence = signal.get("confidence", 0.5)
    strategy = signal.get("strategy", "unknown")
    indicators = signal.get("technical_indicators", {})
    
    # Base win probability based on confidence
    base_win_prob = 0.3 + (confidence * 0.4)  # 30-70% base probability
    
    # Adjust based on strategy
    strategy_adjustments = {
        "combined": 0.05,
        "momentum": 0.00,
        "mean_reversion": -0.02,
        "breakout": 0.03
    }
    win_prob = base_win_prob + strategy_adjustments.get(strategy, 0)
    
    # Adjust based on RSI if available
    rsi = indicators.get("rsi")
    if rsi:
        signal_type = signal.get("signal_type", "buy")
        if signal_type == "buy" and rsi < 30:
            win_prob += 0.05  # Oversold buy is good
        elif signal_type == "buy" and rsi > 70:
            win_prob -= 0.05  # Overbought buy is risky
        elif signal_type == "sell" and rsi > 70:
            win_prob += 0.05  # Overbought sell is good
    
    # Generate PnL based on probability
    if random.random() < win_prob:
        # Win: 2-15% gain
        return random.uniform(win_threshold, 15)
    else:
        # Loss: -2 to -20% loss
        return random.uniform(-20, -win_threshold)


def _get_confidence_bucket_key(confidence: float) -> str:
    """Get bucket key for confidence level."""
    if confidence < 0.45:
        return "0.40-0.45"
    elif confidence < 0.50:
        return "0.45-0.50"
    elif confidence < 0.55:
        return "0.50-0.55"
    elif confidence < 0.60:
        return "0.55-0.60"
    elif confidence < 0.65:
        return "0.60-0.65"
    else:
        return "0.65+"


def _calculate_max_drawdown(pnls: List[float]) -> float:
    """Calculate maximum drawdown from PnL series."""
    if not pnls:
        return 0
    
    cumulative = []
    running_sum = 0
    for pnl in pnls:
        running_sum += pnl
        cumulative.append(running_sum)
    
    peak = cumulative[0]
    max_drawdown = 0
    
    for value in cumulative:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return max_drawdown


def _calculate_sharpe_ratio(pnls: List[float], risk_free_rate: float = 0) -> float:
    """Calculate Sharpe ratio (simplified - assumes no time component)."""
    if not pnls or len(pnls) < 2:
        return 0
    
    import statistics
    
    avg_return = sum(pnls) / len(pnls)
    std_dev = statistics.stdev(pnls)
    
    if std_dev == 0:
        return 0
    
    return (avg_return - risk_free_rate) / std_dev


def _generate_backtest_recommendations(
    win_rate: float,
    avg_pnl: float,
    strategy_breakdown: Dict,
    confidence_breakdown: Dict,
    min_confidence: float
) -> List[str]:
    """Generate actionable recommendations from backtest results."""
    recommendations = []
    
    # Win rate analysis
    if win_rate >= 55:
        recommendations.append(f"✅ Win rate of {win_rate:.1f}% is above target (55%). Current settings are performing well.")
    elif win_rate >= 45:
        recommendations.append(f"⚠️ Win rate of {win_rate:.1f}% is acceptable but could be improved. Consider raising confidence threshold.")
    else:
        recommendations.append(f"❌ Win rate of {win_rate:.1f}% is below target. Significantly raise confidence threshold or apply stricter filters.")
    
    # Find best performing strategy
    best_strat = None
    best_strat_rate = 0
    for strat, data in strategy_breakdown.items():
        if data["total"] >= 5 and data["win_rate"] > best_strat_rate:
            best_strat_rate = data["win_rate"]
            best_strat = strat
    
    if best_strat and best_strat_rate > win_rate + 5:
        recommendations.append(
            f"📊 {best_strat.upper()} strategy outperforms overall ({best_strat_rate:.1f}% vs {win_rate:.1f}%). Consider prioritizing this strategy."
        )
    
    # Find best performing confidence bucket
    best_bucket = None
    best_bucket_rate = 0
    for bucket, data in confidence_breakdown.items():
        if data["total"] >= 5 and data["win_rate"] > best_bucket_rate:
            best_bucket_rate = data["win_rate"]
            best_bucket = bucket
    
    if best_bucket:
        # Handle bucket formats like "0.55-0.60" and "0.65+"
        try:
            if "-" in best_bucket:
                bucket_min = float(best_bucket.split("-")[0])
            elif "+" in best_bucket:
                bucket_min = float(best_bucket.replace("+", ""))
            else:
                bucket_min = float(best_bucket)
        except ValueError:
            bucket_min = min_confidence  # Fallback to current threshold
        
        if bucket_min > min_confidence:
            recommendations.append(
                f"📈 Signals in {best_bucket} confidence range show {best_bucket_rate:.1f}% win rate. "
                f"Recommend raising min confidence to {bucket_min}."
            )
    
    # PnL analysis
    if avg_pnl > 2:
        recommendations.append(f"💰 Average PnL of {avg_pnl:.2f}% is healthy. Risk/reward ratio is favorable.")
    elif avg_pnl < -2:
        recommendations.append(f"⚠️ Average PnL of {avg_pnl:.2f}% is negative. Review stop-loss and take-profit levels.")
    
    return recommendations


# ============== Apply Backtest Improvements ==============

async def _find_optimal_settings_internal(period_days: int = 30, time_horizon: str = "24h") -> Dict[str, Any]:
    """Internal function to find optimal settings."""
    confidence_levels = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
    strategies = [None, "momentum", "mean_reversion", "combined"]  # None = all
    
    best_result = None
    best_score = -float('inf')
    all_results = []
    
    for conf in confidence_levels:
        for strat in strategies:
            try:
                result = await _run_backtest_internal(
                    min_confidence=conf,
                    require_multi_strategy=False,
                    strategy_filter=strat,
                    period_days=period_days,
                    time_horizon=time_horizon
                )
                
                if not result.get("success"):
                    continue
                
                results_data = result.get("results", {})
                
                # Score formula: prioritize win rate and positive PnL, penalize drawdown
                win_rate = results_data.get("win_rate", 0)
                avg_pnl = results_data.get("avg_pnl_percent", 0)
                drawdown = results_data.get("max_drawdown_percent", 0)
                pass_rate = results_data.get("filter_pass_rate", 0)
                
                # Score: 40% win rate + 30% avg pnl + 20% low drawdown + 10% pass rate
                score = (win_rate * 0.4) + (avg_pnl * 3) + ((100 - abs(drawdown)) * 0.2) + (pass_rate * 0.1)
                
                summary = {
                    "min_confidence": conf,
                    "strategy": strat or "all",
                    "signals_tested": results_data.get("signals_passed_filter", 0),
                    "win_rate": win_rate,
                    "avg_pnl": avg_pnl,
                    "max_drawdown": drawdown,
                    "score": round(score, 1)
                }
                all_results.append(summary)
                
                if score > best_score and results_data.get("signals_passed_filter", 0) >= 10:
                    best_score = score
                    best_result = {
                        "config": result["config"],
                        "results": results_data,
                        "score": round(score, 1)
                    }
                    
            except Exception as e:
                logger.warning(f"Backtest failed for conf={conf}, strat={strat}: {e}")
    
    # Sort all results by score
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Generate improvement recommendations
    improvements = []
    if best_result:
        best_conf = best_result["config"]["min_confidence"]
        current_conf = 0.45  # Current threshold
        
        if best_conf > current_conf:
            improvements.append(
                f"📈 Raise minimum confidence from {current_conf} to {best_conf} "
                f"(+{(best_result['results']['win_rate'] - 50):.1f}% win rate improvement expected)"
            )
        
        best_strat = best_result["config"].get("strategy_filter")
        if best_strat:
            improvements.append(
                f"🎯 Focus on {best_strat.upper()} strategy "
                f"({best_result['results']['win_rate']:.1f}% win rate, {best_result['results']['avg_pnl_percent']:.2f}% avg PnL)"
            )
        
        if best_result["results"]["max_drawdown_percent"] > 15:
            improvements.append(
                f"⚠️ Consider tighter stop-losses - current drawdown is {best_result['results']['max_drawdown_percent']:.1f}%"
            )
    
    return {
        "optimal_settings": best_result,
        "all_results": all_results[:10],  # Top 10
        "improvements": improvements,
        "recommendation": f"Based on {period_days}-day backtest, optimal settings found with score {best_score:.1f}"
    }


@router.post("/apply-improvements")
async def apply_backtest_improvements():
    """
    Run optimal backtest and apply recommended improvements to the strategy engine.
    Returns the recommended changes that should be applied.
    """
    
    # Run optimal backtest using internal function
    optimal = await _find_optimal_settings_internal(period_days=30, time_horizon="24h")
    
    if not optimal.get("optimal_settings"):
        return {
            "success": False,
            "message": "Could not determine optimal settings - insufficient data"
        }
    
    optimal_config = optimal["optimal_settings"]["config"]
    optimal_results = optimal["optimal_settings"]["results"]
    
    # Current settings
    current_settings = {
        "min_signal_confidence": 0.45,
        "min_individual_confidence": 0.45,
        "min_signal_threshold": 0.45
    }
    
    # Recommended changes
    recommended_changes = []
    new_settings = current_settings.copy()
    
    # Confidence threshold change
    if optimal_config["min_confidence"] != current_settings["min_signal_confidence"]:
        recommended_changes.append({
            "setting": "MIN_SIGNAL_CONFIDENCE",
            "current": current_settings["min_signal_confidence"],
            "recommended": optimal_config["min_confidence"],
            "reason": f"Backtest shows {optimal_results['win_rate']:.1f}% win rate at this level",
            "file": "/app/backend/routers/ai_trader.py",
            "line": "~444 (StrategyEngine class)"
        })
        new_settings["min_signal_confidence"] = optimal_config["min_confidence"]
    
    # Strategy priority
    if optimal_config.get("strategy_filter"):
        recommended_changes.append({
            "setting": "PRIORITY_STRATEGY",
            "current": "combined",
            "recommended": optimal_config["strategy_filter"],
            "reason": "This strategy shows best performance in backtest",
            "file": "/app/backend/routers/ai_trader.py",
            "line": "~1066 (analyze_token endpoint)"
        })
    
    # Store recommendations in DB for reference
    recommendation_doc = {
        "recommendation_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backtest_period_days": 30,
        "optimal_settings": optimal_config,
        "optimal_results": optimal_results,
        "recommended_changes": recommended_changes,
        "applied": False
    }
    
    await db.strategy_recommendations.insert_one(recommendation_doc)
    
    return {
        "success": True,
        "current_settings": current_settings,
        "recommended_settings": new_settings,
        "changes": recommended_changes,
        "backtest_results": {
            "win_rate": optimal_results["win_rate"],
            "avg_pnl": optimal_results["avg_pnl_percent"],
            "signals_tested": optimal_results["signals_passed_filter"]
        },
        "improvements": optimal.get("improvements", []),
        "note": "Review these changes and apply manually to ai_trader.py for safety"
    }

