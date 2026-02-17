"""Staking simulation routes."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import numpy as np


router = APIRouter(tags=["staking"])


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


@router.post("/staking/simulate")
async def simulate_staking(data: StakingSimRequest):
    """Simulate staking rewards."""
    daily_rate = data.apy / 100 / 365
    balance = data.amount
    total_rewards = 0
    chart_data = []
    
    for day in range(1, data.duration_days + 1):
        reward = balance * daily_rate
        total_rewards += reward
        balance += reward
        if day % max(1, data.duration_days // 30) == 0 or day == data.duration_days:
            chart_data.append({
                "day": day,
                "balance": round(balance, 2),
                "rewards": round(total_rewards, 2)
            })
    
    return {
        "initial": data.amount,
        "final_balance": round(balance, 2),
        "total_rewards": round(total_rewards, 2),
        "apy": data.apy,
        "duration_days": data.duration_days,
        "guardian_points": int(data.amount * data.duration_days / 100),
        "chart_data": chart_data
    }


@router.post("/exit-simulator")
async def simulate_exit(data: ExitSimRequest):
    """Simulate exit scenarios at different price points."""
    results = []
    for exit_price in data.exit_prices:
        investment = data.token_amount * data.entry_price
        value = data.token_amount * exit_price
        pnl = value - investment
        pnl_pct = ((exit_price - data.entry_price) / data.entry_price) * 100 if data.entry_price > 0 else 0
        tax = max(0, pnl * data.tax_rate / 100)
        net_pnl = pnl - tax
        results.append({
            "exit_price": exit_price,
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
            "tax": round(tax, 2),
            "net_pnl": round(net_pnl, 2)
        })
    best = max(results, key=lambda r: r["net_pnl"])
    return {
        "investment": round(data.token_amount * data.entry_price, 2),
        "results": results,
        "optimal_exit": best,
        "token_amount": data.token_amount,
        "entry_price": data.entry_price
    }


@router.post("/exit-simulator/monte-carlo")
async def monte_carlo_simulation(data: MonteCarloRequest):
    """Monte Carlo simulation using Geometric Brownian Motion."""
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

    # Sample paths for chart
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
    histogram = [
        {"min": float(round(hist_edges[i], 6)), "max": float(round(hist_edges[i + 1], 6)), "count": int(hist_counts[i])}
        for i in range(len(hist_counts))
    ]

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
