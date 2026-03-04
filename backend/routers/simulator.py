"""Exit simulator routes for Monte Carlo simulations."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import numpy as np
import uuid


router = APIRouter(prefix="/simulation", tags=["simulator"])


class ExitSimulatorRequest(BaseModel):
    initial_investment: float
    target_exit_multiple: float
    stop_loss_percent: Optional[float] = None
    market_volatility: str = "medium"
    time_horizon_days: int = 30


class MonteCarloRequest(BaseModel):
    token_amount: float
    entry_price: float
    volatility: float  # As decimal (0.5 = 50%)
    drift: float  # As decimal
    days: int
    simulations: int = 1000
    tax_rate: float = 0.15  # As decimal


@router.post("")
async def run_exit_simulation(data: ExitSimulatorRequest):
    """Run a basic exit simulation."""
    volatility_map = {"low": 0.02, "medium": 0.05, "high": 0.10, "extreme": 0.20}
    daily_vol = volatility_map.get(data.market_volatility, 0.05)
    
    simulations = 500
    results = []
    
    for _ in range(simulations):
        price = 1.0
        peak = 1.0
        days = 0
        hit_target = False
        hit_stop = False
        
        for day in range(data.time_horizon_days):
            daily_return = np.random.normal(0.001, daily_vol)
            price *= (1 + daily_return)
            peak = max(peak, price)
            days = day + 1
            
            if price >= data.target_exit_multiple:
                hit_target = True
                break
            if data.stop_loss_percent and price <= (1 - data.stop_loss_percent / 100):
                hit_stop = True
                break
        
        final_value = data.initial_investment * price
        pnl = final_value - data.initial_investment
        
        results.append({
            "final_value": round(final_value, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round((price - 1) * 100, 2),
            "hit_target": hit_target,
            "hit_stop": hit_stop,
            "days_held": days,
            "peak_multiple": round(peak, 4)
        })
    
    # Aggregate stats
    final_values = [r["final_value"] for r in results]
    hit_targets = sum(1 for r in results if r["hit_target"])
    hit_stops = sum(1 for r in results if r["hit_stop"])
    
    return {
        "simulation_id": str(uuid.uuid4())[:8],
        "input": {
            "initial_investment": data.initial_investment,
            "target_exit_multiple": data.target_exit_multiple,
            "stop_loss_percent": data.stop_loss_percent,
            "market_volatility": data.market_volatility,
            "time_horizon_days": data.time_horizon_days
        },
        "summary": {
            "simulations": simulations,
            "avg_final_value": round(sum(final_values) / len(final_values), 2),
            "median_final_value": round(np.median(final_values), 2),
            "min_final_value": round(min(final_values), 2),
            "max_final_value": round(max(final_values), 2),
            "target_hit_rate": round(hit_targets / simulations * 100, 1),
            "stop_hit_rate": round(hit_stops / simulations * 100, 1) if data.stop_loss_percent else None,
            "profitable_rate": round(sum(1 for r in results if r["pnl"] > 0) / simulations * 100, 1)
        },
        "percentiles": {
            "p10": round(np.percentile(final_values, 10), 2),
            "p25": round(np.percentile(final_values, 25), 2),
            "p50": round(np.percentile(final_values, 50), 2),
            "p75": round(np.percentile(final_values, 75), 2),
            "p90": round(np.percentile(final_values, 90), 2)
        }
    }


@router.post("/monte-carlo")
async def run_monte_carlo_simulation(data: MonteCarloRequest):
    """Run Monte Carlo simulation for exit strategy analysis."""
    
    # Initial investment value
    initial_value = data.token_amount * data.entry_price
    
    # Daily parameters (annualized to daily)
    daily_drift = data.drift / 365
    daily_vol = data.volatility / np.sqrt(365)
    
    all_paths = []
    final_prices = []
    final_values = []
    pnl_values = []
    
    # Store all price paths for percentile calculation
    price_paths = []
    
    for sim in range(data.simulations):
        price = data.entry_price
        path = [price]
        
        for day in range(data.days):
            # Geometric Brownian Motion
            random_shock = np.random.normal(0, 1)
            daily_return = daily_drift + daily_vol * random_shock
            price = price * np.exp(daily_return)
            path.append(price)
        
        price_paths.append(path)
        final_price = price
        final_value = data.token_amount * final_price
        pnl = final_value - initial_value
        pnl_after_tax = pnl * (1 - data.tax_rate) if pnl > 0 else pnl
        
        final_prices.append(final_price)
        final_values.append(final_value)
        pnl_values.append(pnl_after_tax)
        
        # Store sample paths
        if len(all_paths) < 10:
            all_paths.append([round(p, 8) for p in path])
    
    # Calculate percentile bands for chart
    price_paths_array = np.array(price_paths)
    days_list = list(range(data.days + 1))
    
    bands = {
        "p5": [round(np.percentile(price_paths_array[:, d], 5), 8) for d in range(data.days + 1)],
        "p25": [round(np.percentile(price_paths_array[:, d], 25), 8) for d in range(data.days + 1)],
        "p50": [round(np.percentile(price_paths_array[:, d], 50), 8) for d in range(data.days + 1)],
        "p75": [round(np.percentile(price_paths_array[:, d], 75), 8) for d in range(data.days + 1)],
        "p95": [round(np.percentile(price_paths_array[:, d], 95), 8) for d in range(data.days + 1)],
    }
    
    # Create histogram data
    num_bins = 20
    min_price = min(final_prices)
    max_price = max(final_prices)
    bin_width = (max_price - min_price) / num_bins if max_price > min_price else 0.0001
    
    histogram = []
    for i in range(num_bins):
        bin_min = min_price + i * bin_width
        bin_max = bin_min + bin_width
        count = sum(1 for p in final_prices if bin_min <= p < bin_max)
        histogram.append({
            "min": round(bin_min, 8),
            "max": round(bin_max, 8),
            "count": count
        })
    
    # Calculate probabilities
    prob_profit = round(sum(1 for p in pnl_values if p > 0) / len(pnl_values) * 100, 1)
    prob_2x = round(sum(1 for v in final_values if v >= initial_value * 2) / len(final_values) * 100, 1)
    prob_5x = round(sum(1 for v in final_values if v >= initial_value * 5) / len(final_values) * 100, 1)
    prob_10x = round(sum(1 for v in final_values if v >= initial_value * 10) / len(final_values) * 100, 1)
    prob_loss50 = round(sum(1 for v in final_values if v <= initial_value * 0.5) / len(final_values) * 100, 1)
    
    return {
        "simulation_id": str(uuid.uuid4())[:8],
        "token_amount": data.token_amount,
        "entry_price": data.entry_price,
        "days": data.days,
        "simulations": data.simulations,
        "volatility": data.volatility,
        "drift": data.drift,
        "tax_rate": data.tax_rate,
        # Direct fields expected by frontend
        "mean_pnl": round(np.mean(pnl_values), 2),
        "median_pnl": round(np.median(pnl_values), 2),
        "max_pnl": round(max(pnl_values), 2),
        "min_pnl": round(min(pnl_values), 2),
        "prob_profit": prob_profit,
        "prob_2x": prob_2x,
        "prob_5x": prob_5x,
        "prob_10x": prob_10x,
        "prob_loss50": prob_loss50,
        "chart": {
            "days": days_list,
            "bands": bands,
            "sample_paths": all_paths[:5]
        },
        "histogram": histogram,
        "statistics": {
            "initial_value": round(initial_value, 2),
            "mean_final_price": round(np.mean(final_prices), 8),
            "median_final_price": round(np.median(final_prices), 8),
            "min_final_price": round(min(final_prices), 8),
            "max_final_price": round(max(final_prices), 8),
            "mean_final_value": round(np.mean(final_values), 2),
            "expected_pnl": round(np.mean(pnl_values), 2),
            "probability_of_profit": prob_profit,
            "best_case_pnl": round(max(pnl_values), 2),
            "worst_case_pnl": round(min(pnl_values), 2),
            "std_dev_pnl": round(np.std(pnl_values), 2)
        },
        "percentiles": {
            "p5": round(np.percentile(final_values, 5), 2),
            "p10": round(np.percentile(final_values, 10), 2),
            "p25": round(np.percentile(final_values, 25), 2),
            "p50": round(np.percentile(final_values, 50), 2),
            "p75": round(np.percentile(final_values, 75), 2),
            "p90": round(np.percentile(final_values, 90), 2),
            "p95": round(np.percentile(final_values, 95), 2)
        },
        "risk_metrics": {
            "var_95": round(np.percentile(pnl_values, 5), 2),
            "upside_potential": round(np.percentile(pnl_values, 95), 2),
            "risk_reward_ratio": round(abs(np.percentile(pnl_values, 95) / np.percentile(pnl_values, 5)), 2) if np.percentile(pnl_values, 5) != 0 else 0
        }
    }
