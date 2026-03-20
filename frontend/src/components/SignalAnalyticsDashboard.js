/**
 * SignalAnalyticsDashboard Component
 * 
 * Visualizes trading bot signal performance data:
 * - Token-level performance heatmap
 * - Win rate trends over time
 * - Confidence vs approval rate visualization
 * - Strategy backtester
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  BarChart3, TrendingUp, TrendingDown, Target, Activity, Zap,
  RefreshCw, ChevronDown, ChevronUp, Loader2, AlertCircle,
  ArrowUpRight, ArrowDownRight, Minus, Info, FlaskConical
} from 'lucide-react';
import StrategyBacktester from './StrategyBacktester';
import AdaptiveLearning from './AdaptiveLearning';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Color scales for heatmap
const getHeatmapColor = (value, min, max) => {
  if (value === null || value === undefined) return 'bg-slate-800';
  const normalized = (value - min) / (max - min || 1);
  
  if (normalized >= 0.8) return 'bg-emerald-500';
  if (normalized >= 0.6) return 'bg-emerald-600/80';
  if (normalized >= 0.4) return 'bg-amber-500/80';
  if (normalized >= 0.2) return 'bg-orange-500/80';
  return 'bg-red-500/80';
};

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.65) return 'text-emerald-400';
  if (confidence >= 0.55) return 'text-lime-400';
  if (confidence >= 0.50) return 'text-amber-400';
  if (confidence >= 0.45) return 'text-orange-400';
  return 'text-red-400';
};

export default function SignalAnalyticsDashboard() {
  const { connected } = useWallet();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [periodDays, setPeriodDays] = useState(30);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Data states
  const [performanceSummary, setPerformanceSummary] = useState(null);
  const [confidenceAnalysis, setConfidenceAnalysis] = useState(null);
  const [strategyComparison, setStrategyComparison] = useState(null);
  const [optimalSettings, setOptimalSettings] = useState(null);

  // Fetch all analytics data
  const fetchAnalytics = useCallback(async () => {
    try {
      setRefreshing(true);
      
      const [perfRes, confRes, stratRes, optRes] = await Promise.all([
        axios.get(`${API}/signal-analytics/performance-summary?period_days=${periodDays}`),
        axios.get(`${API}/signal-analytics/confidence-analysis?period_days=${periodDays}`),
        axios.get(`${API}/signal-analytics/strategy-comparison?period_days=${periodDays}`),
        axios.get(`${API}/signal-analytics/optimal-settings`)
      ]);
      
      setPerformanceSummary(perfRes.data);
      setConfidenceAnalysis(confRes.data);
      setStrategyComparison(stratRes.data);
      setOptimalSettings(optRes.data);
      
    } catch (e) {
      console.error('Failed to fetch analytics:', e);
      toast.error('Failed to load analytics data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [periodDays]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#D946EF]" />
      </div>
    );
  }

  const totalSignals = performanceSummary?.total_signals_analyzed || 0;
  const strategies = performanceSummary?.strategies || [];
  const topTokens = performanceSummary?.top_tokens || [];
  const recommendations = performanceSummary?.recommendations || [];
  const confidenceDist = confidenceAnalysis?.confidence_distribution || [];

  return (
    <div className="space-y-6" data-testid="signal-analytics-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-[#D946EF]" />
            Signal Analytics
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            {totalSignals} signals analyzed over {periodDays} days
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Period Selector */}
          <select
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
            className="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          
          <Button
            size="sm"
            variant="outline"
            onClick={fetchAnalytics}
            disabled={refreshing}
            className="border-white/10"
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-white/10 pb-2 overflow-x-auto">
        {[
          { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
          { id: 'heatmap', label: 'Token Heatmap', icon: <Target className="w-4 h-4" /> },
          { id: 'confidence', label: 'Confidence Analysis', icon: <Zap className="w-4 h-4" /> },
          { id: 'backtester', label: 'Backtester', icon: <FlaskConical className="w-4 h-4" /> },
          { id: 'adaptive', label: 'Adaptive', icon: <Zap className="w-4 h-4" /> },
          { id: 'recommendations', label: 'Recommendations', icon: <Info className="w-4 h-4" /> }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
              activeTab === tab.id 
                ? 'bg-[#D946EF]/20 text-[#D946EF] border-b-2 border-[#D946EF]' 
                : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Total Signals"
              value={totalSignals}
              icon={<Activity className="w-5 h-5" />}
              color="blue"
            />
            <MetricCard
              label="Avg Confidence"
              value={`${((strategies.reduce((acc, s) => acc + s.avg_confidence, 0) / (strategies.length || 1)) * 100).toFixed(1)}%`}
              icon={<Target className="w-5 h-5" />}
              color="purple"
            />
            <MetricCard
              label="Approval Rate"
              value={`${(strategies.reduce((acc, s) => acc + s.approval_rate, 0) / (strategies.length || 1)).toFixed(1)}%`}
              icon={<TrendingUp className="w-5 h-5" />}
              color="green"
            />
            <MetricCard
              label="Recommended Min"
              value={`${(optimalSettings?.settings?.recommended_min_confidence || 0.50) * 100}%`}
              icon={<Zap className="w-5 h-5" />}
              color="amber"
            />
          </div>

          {/* Strategy Performance Chart */}
          <div className="glass-card rounded-xl p-4 border border-white/10">
            <h3 className="text-sm font-bold text-slate-400 uppercase mb-4">Strategy Performance</h3>
            <div className="space-y-4">
              {strategies.map((strat, i) => (
                <StrategyBar key={i} strategy={strat} maxSignals={Math.max(...strategies.map(s => s.total_signals))} />
              ))}
              {strategies.length === 0 && (
                <p className="text-sm text-slate-500 text-center py-8">No strategy data available</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Token Heatmap Tab */}
      {activeTab === 'heatmap' && (
        <div className="glass-card rounded-xl p-4 border border-white/10">
          <h3 className="text-sm font-bold text-slate-400 uppercase mb-4">Token Performance Heatmap</h3>
          <p className="text-xs text-slate-500 mb-4">
            Shows signal distribution and confidence by token. Brighter colors = higher confidence.
          </p>
          
          {topTokens.length > 0 ? (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
              {topTokens.map((token, i) => (
                <TokenHeatmapCell key={i} token={token} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500">
              <Target className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No token data available</p>
            </div>
          )}
          
          {/* Legend */}
          <div className="flex items-center justify-center gap-4 mt-6 pt-4 border-t border-white/5">
            <span className="text-xs text-slate-500">Confidence:</span>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-red-500/80" />
              <span className="text-xs text-slate-400">&lt;45%</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-orange-500/80" />
              <span className="text-xs text-slate-400">45-50%</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-amber-500/80" />
              <span className="text-xs text-slate-400">50-55%</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-emerald-600/80" />
              <span className="text-xs text-slate-400">55-65%</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-emerald-500" />
              <span className="text-xs text-slate-400">&gt;65%</span>
            </div>
          </div>
        </div>
      )}

      {/* Confidence Analysis Tab */}
      {activeTab === 'confidence' && (
        <div className="space-y-6">
          {/* Confidence vs Approval Rate Chart */}
          <div className="glass-card rounded-xl p-4 border border-white/10">
            <h3 className="text-sm font-bold text-slate-400 uppercase mb-4">Confidence vs Approval Rate</h3>
            <p className="text-xs text-slate-500 mb-4">
              Shows how signal confidence correlates with user approval. Higher confidence should lead to higher approval.
            </p>
            
            <div className="space-y-3">
              {confidenceDist.map((bucket, i) => (
                <ConfidenceBar key={i} bucket={bucket} />
              ))}
            </div>
            
            {confidenceAnalysis?.recommended_min_confidence && (
              <div className="mt-4 pt-4 border-t border-white/5">
                <p className="text-sm text-slate-300">
                  <span className="text-[#D946EF] font-medium">Recommendation: </span>
                  {confidenceAnalysis.insight}
                </p>
              </div>
            )}
          </div>

          {/* Strategy Comparison */}
          <div className="glass-card rounded-xl p-4 border border-white/10">
            <h3 className="text-sm font-bold text-slate-400 uppercase mb-4">Strategy Quality Scores</h3>
            <div className="space-y-3">
              {strategyComparison?.strategies?.map((strat, i) => (
                <StrategyQualityCard key={i} strategy={strat} rank={i + 1} />
              ))}
            </div>
            {strategyComparison?.recommendation && (
              <div className="mt-4 pt-4 border-t border-white/5">
                <p className="text-sm text-slate-300">{strategyComparison.recommendation}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recommendations Tab */}
      {activeTab === 'recommendations' && (
        <div className="space-y-4">
          {/* Optimal Settings */}
          {optimalSettings?.sufficient_data && (
            <div className="glass-card rounded-xl p-4 border border-white/10">
              <h3 className="text-sm font-bold text-slate-400 uppercase mb-4">Recommended Settings</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <SettingCard
                  label="Min Confidence Threshold"
                  value={`${(optimalSettings.settings.recommended_min_confidence * 100).toFixed(0)}%`}
                  description={optimalSettings.settings.confidence_reasoning}
                />
                <SettingCard
                  label="Priority Strategy"
                  value={optimalSettings.settings.recommended_strategy_priority?.toUpperCase() || 'COMBINED'}
                  description="Strategy showing best overall quality"
                />
                <SettingCard
                  label="Multi-Strategy Mode"
                  value={optimalSettings.settings.require_multiple_strategies ? 'Recommended' : 'Optional'}
                  description="Require agreement from multiple strategies"
                />
                {optimalSettings.settings.auto_trade && (
                  <>
                    <SettingCard
                      label="Auto-Trade Min Confidence"
                      value={`${(optimalSettings.settings.auto_trade.recommended_min_confidence * 100).toFixed(0)}%`}
                      description="Higher threshold for automated trades"
                    />
                    <SettingCard
                      label="Max Daily Auto-Trades"
                      value={optimalSettings.settings.auto_trade.recommended_max_daily_trades}
                      description="Limit to prevent overtrading"
                    />
                    <SettingCard
                      label="Trade Cooldown"
                      value={`${optimalSettings.settings.auto_trade.recommended_cooldown_minutes} min`}
                      description="Wait period between auto-trades"
                    />
                  </>
                )}
              </div>
            </div>
          )}

          {/* Analysis Insights */}
          <div className="glass-card rounded-xl p-4 border border-white/10">
            <h3 className="text-sm font-bold text-slate-400 uppercase mb-4">Analysis Insights</h3>
            <div className="space-y-3">
              {recommendations.length > 0 ? (
                recommendations.map((rec, i) => (
                  <div key={i} className="p-3 rounded-lg bg-white/5 border border-white/5">
                    <p className="text-sm text-slate-300">{rec}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">
                  No specific recommendations at this time.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Backtester Tab */}
      {activeTab === 'backtester' && (
        <StrategyBacktester />
      )}

      {/* Adaptive Learning Tab */}
      {activeTab === 'adaptive' && (
        <AdaptiveLearning />
      )}
    </div>
  );
}

// Sub-components

function MetricCard({ label, value, icon, color }) {
  const colorClasses = {
    blue: 'bg-blue-500/20 text-blue-400',
    purple: 'bg-[#D946EF]/20 text-[#D946EF]',
    green: 'bg-emerald-500/20 text-emerald-400',
    amber: 'bg-amber-500/20 text-amber-400',
    red: 'bg-red-500/20 text-red-400'
  };
  
  return (
    <div className="glass-card rounded-xl p-4 border border-white/10">
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-400">{label}</p>
    </div>
  );
}

function StrategyBar({ strategy, maxSignals }) {
  const widthPercent = (strategy.total_signals / maxSignals) * 100;
  const approvalColor = strategy.approval_rate > 10 ? 'bg-emerald-500' : 
                        strategy.approval_rate > 5 ? 'bg-amber-500' : 'bg-red-500';
  
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-white font-medium capitalize">{strategy.strategy}</span>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-slate-400">{strategy.total_signals} signals</span>
          <span className={getConfidenceColor(strategy.avg_confidence)}>
            {(strategy.avg_confidence * 100).toFixed(0)}% conf
          </span>
          <Badge className={`${approvalColor} text-white text-[10px]`}>
            {strategy.approval_rate.toFixed(1)}% approved
          </Badge>
        </div>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-[#D946EF] to-[#00C2FF] rounded-full transition-all duration-500"
          style={{ width: `${widthPercent}%` }}
        />
      </div>
    </div>
  );
}

function TokenHeatmapCell({ token }) {
  const confidence = token.avg_confidence || 0;
  
  // Color based on confidence
  let bgColor;
  if (confidence >= 0.65) bgColor = 'bg-emerald-500';
  else if (confidence >= 0.55) bgColor = 'bg-emerald-600/80';
  else if (confidence >= 0.50) bgColor = 'bg-amber-500/80';
  else if (confidence >= 0.45) bgColor = 'bg-orange-500/80';
  else bgColor = 'bg-red-500/80';
  
  return (
    <div 
      className={`${bgColor} rounded-lg p-3 text-center transition-transform hover:scale-105 cursor-default`}
      title={`${token.token}: ${token.total_signals} signals, ${(confidence * 100).toFixed(1)}% avg confidence`}
    >
      <p className="text-white font-bold text-sm truncate">{token.token}</p>
      <p className="text-white/80 text-xs">{token.total_signals}</p>
      <p className="text-white/60 text-[10px]">{token.buy_sell_ratio}</p>
    </div>
  );
}

function ConfidenceBar({ bucket }) {
  const approvalRate = bucket.approval_rate || 0;
  const total = bucket.total_signals || 0;
  
  // Color based on approval rate
  let barColor;
  if (approvalRate >= 10) barColor = 'bg-emerald-500';
  else if (approvalRate >= 5) barColor = 'bg-amber-500';
  else if (approvalRate > 0) barColor = 'bg-orange-500';
  else barColor = 'bg-red-500/50';
  
  return (
    <div className="flex items-center gap-4">
      <span className="text-sm text-slate-400 w-28 flex-shrink-0">{bucket.confidence_range}</span>
      <div className="flex-1 h-6 bg-slate-800 rounded-full overflow-hidden relative">
        <div 
          className={`h-full ${barColor} rounded-full transition-all duration-500 flex items-center justify-end pr-2`}
          style={{ width: `${Math.max(approvalRate * 5, 2)}%` }}
        >
          {approvalRate > 0 && (
            <span className="text-xs text-white font-medium">{approvalRate.toFixed(1)}%</span>
          )}
        </div>
      </div>
      <span className="text-xs text-slate-500 w-16 text-right">{total} signals</span>
    </div>
  );
}

function StrategyQualityCard({ strategy, rank }) {
  const score = strategy.quality_score || 0;
  
  let scoreColor, scoreBg;
  if (score >= 50) { scoreColor = 'text-emerald-400'; scoreBg = 'bg-emerald-500/20'; }
  else if (score >= 30) { scoreColor = 'text-amber-400'; scoreBg = 'bg-amber-500/20'; }
  else { scoreColor = 'text-red-400'; scoreBg = 'bg-red-500/20'; }
  
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5">
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-500 font-mono">#{rank}</span>
        <div>
          <p className="text-white font-medium capitalize">{strategy.strategy}</p>
          <p className="text-xs text-slate-400">
            {strategy.total_signals} signals • {strategy.approval_rate.toFixed(1)}% approval • {strategy.buy_sell_ratio} buy/sell
          </p>
        </div>
      </div>
      <div className={`px-3 py-1 rounded-lg ${scoreBg}`}>
        <p className={`text-lg font-bold ${scoreColor}`}>{score.toFixed(0)}</p>
        <p className="text-[10px] text-slate-500">Quality</p>
      </div>
    </div>
  );
}

function SettingCard({ label, value, description }) {
  return (
    <div className="p-4 rounded-lg bg-white/5 border border-white/5">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-xl font-bold text-white">{value}</p>
      {description && (
        <p className="text-xs text-slate-500 mt-1">{description}</p>
      )}
    </div>
  );
}
