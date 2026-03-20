/**
 * StrategyBacktester Component
 * 
 * Allows users to:
 * - Run backtests with different confidence thresholds
 * - Compare strategy performance
 * - Find optimal settings
 * - Apply improvements to the trading bot
 */

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  FlaskConical, Play, Settings, TrendingUp, TrendingDown,
  Loader2, RefreshCw, Target, AlertCircle, Check, Zap,
  BarChart3, ArrowRight, Sparkles
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategyBacktester() {
  const [loading, setLoading] = useState(false);
  const [findingOptimal, setFindingOptimal] = useState(false);
  
  // Backtest config
  const [config, setConfig] = useState({
    min_confidence: 0.55,
    require_multi_strategy: false,
    strategy_filter: '',
    period_days: 30,
    win_threshold_percent: 2.0,
    time_horizon: '24h'
  });
  
  // Results
  const [backtestResult, setBacktestResult] = useState(null);
  const [optimalResult, setOptimalResult] = useState(null);

  // Run single backtest
  const runBacktest = useCallback(async () => {
    try {
      setLoading(true);
      
      const params = new URLSearchParams({
        min_confidence: config.min_confidence,
        require_multi_strategy: config.require_multi_strategy,
        period_days: config.period_days,
        win_threshold_percent: config.win_threshold_percent,
        time_horizon: config.time_horizon
      });
      
      if (config.strategy_filter) {
        params.append('strategy_filter', config.strategy_filter);
      }
      
      const { data } = await axios.post(`${API}/signal-analytics/backtest?${params}`);
      
      if (data.success) {
        setBacktestResult(data);
        toast.success(`Backtest complete: ${data.results.win_rate}% win rate`);
      } else {
        toast.error(data.error || 'Backtest failed');
      }
    } catch (e) {
      toast.error('Failed to run backtest');
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [config]);

  // Find optimal settings
  const findOptimal = useCallback(async () => {
    try {
      setFindingOptimal(true);
      
      const { data } = await axios.get(
        `${API}/signal-analytics/backtest/optimal?period_days=${config.period_days}&time_horizon=${config.time_horizon}`
      );
      
      setOptimalResult(data);
      
      if (data.optimal_settings) {
        toast.success(`Found optimal settings with ${data.optimal_settings.results.win_rate}% win rate`);
      } else {
        toast.warning('Could not determine optimal settings - try different period');
      }
    } catch (e) {
      toast.error('Failed to find optimal settings');
      console.error(e);
    } finally {
      setFindingOptimal(false);
    }
  }, [config.period_days, config.time_horizon]);

  return (
    <div className="space-y-6" data-testid="strategy-backtester">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-[#D946EF]" />
            Strategy Backtester
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            Test different settings against historical signals
          </p>
        </div>
        
        <Button
          onClick={findOptimal}
          disabled={findingOptimal}
          className="bg-gradient-to-r from-[#D946EF] to-[#00C2FF] text-white"
        >
          {findingOptimal ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4 mr-2" />
          )}
          Find Optimal
        </Button>
      </div>

      {/* Config Panel */}
      <div className="glass-card rounded-xl p-4 border border-white/10">
        <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Backtest Configuration</h4>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {/* Min Confidence */}
          <div>
            <label className="text-xs text-slate-400 block mb-1">Min Confidence</label>
            <select
              value={config.min_confidence}
              onChange={(e) => setConfig(c => ({ ...c, min_confidence: parseFloat(e.target.value) }))}
              className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value={0.40}>40%</option>
              <option value={0.45}>45%</option>
              <option value={0.50}>50%</option>
              <option value={0.55}>55% (Current)</option>
              <option value={0.60}>60%</option>
              <option value={0.65}>65%</option>
            </select>
          </div>

          {/* Strategy Filter */}
          <div>
            <label className="text-xs text-slate-400 block mb-1">Strategy</label>
            <select
              value={config.strategy_filter}
              onChange={(e) => setConfig(c => ({ ...c, strategy_filter: e.target.value }))}
              className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="">All Strategies</option>
              <option value="combined">Combined</option>
              <option value="momentum">Momentum</option>
              <option value="mean_reversion">Mean Reversion</option>
              <option value="breakout">Breakout</option>
            </select>
          </div>

          {/* Period */}
          <div>
            <label className="text-xs text-slate-400 block mb-1">Period</label>
            <select
              value={config.period_days}
              onChange={(e) => setConfig(c => ({ ...c, period_days: parseInt(e.target.value) }))}
              className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
              <option value={60}>60 days</option>
              <option value={90}>90 days</option>
            </select>
          </div>

          {/* Time Horizon */}
          <div>
            <label className="text-xs text-slate-400 block mb-1">Time Horizon</label>
            <select
              value={config.time_horizon}
              onChange={(e) => setConfig(c => ({ ...c, time_horizon: e.target.value }))}
              className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="1h">1 Hour</option>
              <option value="4h">4 Hours</option>
              <option value="24h">24 Hours</option>
            </select>
          </div>

          {/* Win Threshold */}
          <div>
            <label className="text-xs text-slate-400 block mb-1">Win Threshold</label>
            <select
              value={config.win_threshold_percent}
              onChange={(e) => setConfig(c => ({ ...c, win_threshold_percent: parseFloat(e.target.value) }))}
              className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value={1.0}>1%</option>
              <option value={2.0}>2% (Default)</option>
              <option value={3.0}>3%</option>
              <option value={5.0}>5%</option>
            </select>
          </div>

          {/* Run Button */}
          <div className="flex items-end">
            <Button
              onClick={runBacktest}
              disabled={loading}
              className="w-full bg-[#D946EF] hover:bg-[#D946EF]/80 text-white"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              Run Backtest
            </Button>
          </div>
        </div>
      </div>

      {/* Backtest Results */}
      {backtestResult && (
        <div className="glass-card rounded-xl p-4 border border-white/10">
          <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Backtest Results</h4>
          
          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard
              label="Win Rate"
              value={`${backtestResult.results.win_rate}%`}
              color={backtestResult.results.win_rate >= 55 ? 'green' : backtestResult.results.win_rate >= 45 ? 'amber' : 'red'}
            />
            <MetricCard
              label="Avg PnL"
              value={`${backtestResult.results.avg_pnl_percent >= 0 ? '+' : ''}${backtestResult.results.avg_pnl_percent}%`}
              color={backtestResult.results.avg_pnl_percent >= 0 ? 'green' : 'red'}
            />
            <MetricCard
              label="Signals Tested"
              value={backtestResult.results.signals_passed_filter}
              subtext={`${backtestResult.results.filter_pass_rate}% of total`}
              color="blue"
            />
            <MetricCard
              label="Max Drawdown"
              value={`${backtestResult.results.max_drawdown_percent}%`}
              color={backtestResult.results.max_drawdown_percent < 15 ? 'green' : 'red'}
            />
          </div>

          {/* Win/Loss Distribution */}
          <div className="mb-6">
            <p className="text-xs text-slate-400 mb-2">Win/Loss Distribution</p>
            <div className="h-4 rounded-full overflow-hidden bg-slate-800 flex">
              <div 
                className="bg-emerald-500 h-full transition-all"
                style={{ width: `${backtestResult.results.win_rate}%` }}
              />
              <div 
                className="bg-red-500 h-full transition-all"
                style={{ width: `${backtestResult.results.loss_rate}%` }}
              />
            </div>
            <div className="flex justify-between text-xs mt-1">
              <span className="text-emerald-400">{backtestResult.results.win_count} wins</span>
              <span className="text-red-400">{backtestResult.results.loss_count} losses</span>
            </div>
          </div>

          {/* Strategy Breakdown */}
          {Object.keys(backtestResult.by_strategy || {}).length > 0 && (
            <div className="mb-6">
              <p className="text-xs text-slate-400 mb-2">Strategy Breakdown</p>
              <div className="space-y-2">
                {Object.entries(backtestResult.by_strategy).map(([strat, data]) => (
                  <div key={strat} className="flex items-center justify-between p-2 rounded bg-white/5">
                    <span className="text-white capitalize">{strat}</span>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-slate-400">{data.total} signals</span>
                      <Badge className={data.win_rate >= 55 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}>
                        {data.win_rate}% win
                      </Badge>
                      <span className={data.avg_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                        {data.avg_pnl >= 0 ? '+' : ''}{data.avg_pnl}% avg
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {backtestResult.recommendations?.length > 0 && (
            <div>
              <p className="text-xs text-slate-400 mb-2">Recommendations</p>
              <div className="space-y-2">
                {backtestResult.recommendations.map((rec, i) => (
                  <div key={i} className="p-3 rounded bg-white/5 text-sm text-slate-300">
                    {rec}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Optimal Settings Results */}
      {optimalResult && (
        <div className="glass-card rounded-xl p-4 border border-[#D946EF]/30 bg-[#D946EF]/5">
          <h4 className="text-sm font-bold text-[#D946EF] uppercase mb-4 flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Optimal Settings Found
          </h4>
          
          {optimalResult.optimal_settings ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="p-3 rounded bg-white/5">
                  <p className="text-xs text-slate-400">Best Confidence</p>
                  <p className="text-xl font-bold text-white">
                    {(optimalResult.optimal_settings.config.min_confidence * 100).toFixed(0)}%
                  </p>
                </div>
                <div className="p-3 rounded bg-white/5">
                  <p className="text-xs text-slate-400">Win Rate</p>
                  <p className="text-xl font-bold text-emerald-400">
                    {optimalResult.optimal_settings.results.win_rate}%
                  </p>
                </div>
                <div className="p-3 rounded bg-white/5">
                  <p className="text-xs text-slate-400">Avg PnL</p>
                  <p className="text-xl font-bold text-white">
                    {optimalResult.optimal_settings.results.avg_pnl_percent >= 0 ? '+' : ''}
                    {optimalResult.optimal_settings.results.avg_pnl_percent}%
                  </p>
                </div>
                <div className="p-3 rounded bg-white/5">
                  <p className="text-xs text-slate-400">Quality Score</p>
                  <p className="text-xl font-bold text-[#D946EF]">
                    {optimalResult.optimal_settings.score}
                  </p>
                </div>
              </div>

              {/* Improvements */}
              {optimalResult.improvements?.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs text-slate-400">Suggested Improvements</p>
                  {optimalResult.improvements.map((imp, i) => (
                    <div key={i} className="p-3 rounded bg-[#D946EF]/10 text-sm text-white">
                      {imp}
                    </div>
                  ))}
                </div>
              )}

              {/* Top Results Table */}
              {optimalResult.all_results?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs text-slate-400 mb-2">Top Configurations</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-slate-400">
                          <th className="pb-2">Confidence</th>
                          <th className="pb-2">Strategy</th>
                          <th className="pb-2">Win Rate</th>
                          <th className="pb-2">Avg PnL</th>
                          <th className="pb-2">Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {optimalResult.all_results.slice(0, 5).map((r, i) => (
                          <tr key={i} className={i === 0 ? 'text-[#D946EF]' : 'text-slate-300'}>
                            <td className="py-1">{(r.min_confidence * 100).toFixed(0)}%</td>
                            <td className="py-1 capitalize">{r.strategy}</td>
                            <td className="py-1">{r.win_rate}%</td>
                            <td className="py-1">{r.avg_pnl >= 0 ? '+' : ''}{r.avg_pnl}%</td>
                            <td className="py-1 font-bold">{r.score}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-slate-400 text-center py-4">
              Could not find optimal settings. Try adjusting the period or time horizon.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, subtext, color }) {
  const colors = {
    green: 'text-emerald-400',
    red: 'text-red-400',
    amber: 'text-amber-400',
    blue: 'text-blue-400'
  };
  
  return (
    <div className="p-3 rounded-lg bg-white/5">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`text-xl font-bold ${colors[color] || 'text-white'}`}>{value}</p>
      {subtext && <p className="text-xs text-slate-500">{subtext}</p>}
    </div>
  );
}
