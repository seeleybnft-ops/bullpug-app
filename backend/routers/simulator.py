"""Exit simulator routes for Monte Carlo simulations."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import numpy as np
import uuid
from datetime import datetime, timezone

from utils.database import db

router = APIRouter(prefix="/exit-simulator", tags=["simulator"])


class ExitSimulatorRequest(BaseModel):
    initial_investment: float
    target_exit_multiple: float
    stop_loss_percent: Optional[float] = None
    market_volatility: str = "medium"
    time_horizon_days: int = 30


class MonteCarloRequest(BaseModel):
    initial_investment: float
    expected_return_percent: float
    volatility_percent: float
    time_horizon_days: int
    num_simulations: int = 1000
    exit_strategy: str = "fixed_target"
    target_return_percent: Optional[float] = 100.0
    stop_loss_percent: Optional[float] = 50.0
    trailing_stop_percent: Optional[float] = None


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
    """Run advanced Monte Carlo simulation with multiple exit strategies."""
    daily_return = data.expected_return_percent / 100 / 252
    daily_vol = data.volatility_percent / 100 / np.sqrt(252)
    
    all_paths = []
    final_values = []
    exit_stats = {"target": 0, "stop_loss": 0, "trailing_stop": 0, "time_expire": 0}
    
    for _ in range(data.num_simulations):
        price = 1.0
        peak_price = 1.0
        path = [1.0]
        exit_day = data.time_horizon_days
        exit_reason = "time_expire"
        
        for day in range(data.time_horizon_days):
            daily_change = np.random.normal(daily_return, daily_vol)
            price *= (1 + daily_change)
            path.append(price)
            peak_price = max(peak_price, price)
            
            current_return_pct = (price - 1) * 100
            
            # Check exit conditions
            if data.exit_strategy in ["fixed_target", "combined"]:
                if data.target_return_percent and current_return_pct >= data.target_return_percent:
                    exit_day = day + 1
                    exit_reason = "target"
                    exit_stats["target"] += 1
                    break
            
            if data.stop_loss_percent and current_return_pct <= -data.stop_loss_percent:
                exit_day = day + 1
                exit_reason = "stop_loss"
                exit_stats["stop_loss"] += 1
                break
            
            if data.trailing_stop_percent:
                drawdown = (peak_price - price) / peak_price * 100
                if drawdown >= data.trailing_stop_percent:
                    exit_day = day + 1
                    exit_reason = "trailing_stop"
                    exit_stats["trailing_stop"] += 1
                    break
        else:
            exit_stats["time_expire"] += 1
        
        final_value = data.initial_investment * price
        final_values.append(final_value)
        
        if len(all_paths) < 50:
            all_paths.append({
                "path": [round(p, 4) for p in path[::max(1, len(path)//50)]],
                "final_value": round(final_value, 2),
                "exit_day": exit_day,
                "exit_reason": exit_reason
            })
    
    # Calculate statistics
    pnl_values = [v - data.initial_investment for v in final_values]
    
    # Risk metrics
    returns = [(final_values[i] / data.initial_investment - 1) for i in range(len(final_values))]
    avg_return = np.mean(returns)
    std_return = np.std(returns) if len(returns) > 1 else 0
    sharpe = (avg_return / std_return * np.sqrt(252 / data.time_horizon_days)) if std_return > 0 else 0
    
    # VaR and CVaR
    var_95 = np.percentile(pnl_values, 5)
    cvar_95 = np.mean([p for p in pnl_values if p <= var_95]) if any(p <= var_95 for p in pnl_values) else var_95
    
    return {
        "simulation_id": str(uuid.uuid4())[:8],
        "config": {
            "initial_investment": data.initial_investment,
            "expected_return_percent": data.expected_return_percent,
            "volatility_percent": data.volatility_percent,
            "time_horizon_days": data.time_horizon_days,
            "num_simulations": data.num_simulations,
            "exit_strategy": data.exit_strategy
        },
        "summary": {
            "avg_final_value": round(np.mean(final_values), 2),
            "median_final_value": round(np.median(final_values), 2),
            "std_dev": round(np.std(final_values), 2),
            "min_value": round(min(final_values), 2),
            "max_value": round(max(final_values), 2),
            "profitable_rate": round(sum(1 for v in final_values if v > data.initial_investment) / len(final_values) * 100, 1),
            "avg_pnl": round(np.mean(pnl_values), 2),
            "total_expected_pnl": round(np.mean(pnl_values) * data.num_simulations, 2)
        },
        "risk_metrics": {
            "sharpe_ratio": round(sharpe, 3),
            "var_95": round(var_95, 2),
            "cvar_95": round(cvar_95, 2),
            "max_drawdown_potential": round((1 - min(final_values) / data.initial_investment) * 100, 1)
        },
        "exit_statistics": {
            "target_exits": exit_stats["target"],
            "stop_loss_exits": exit_stats["stop_loss"],
            "trailing_stop_exits": exit_stats["trailing_stop"],
            "time_expire": exit_stats["time_expire"],
            "target_hit_rate": round(exit_stats["target"] / data.num_simulations * 100, 1),
            "stop_hit_rate": round(exit_stats["stop_loss"] / data.num_simulations * 100, 1)
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
        "sample_paths": all_paths[:20]
    }
