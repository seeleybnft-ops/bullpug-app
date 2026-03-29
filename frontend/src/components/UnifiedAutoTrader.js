/**
 * UnifiedAutoTrader Component
 * 
 * Combines Auto-Trade controls with Signal Analytics for data-driven decision making.
 * Users can see performance metrics while configuring their auto-trade settings.
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Cpu, Settings, Zap, Play, Pause, Loader2, RefreshCw,
  Activity, TrendingUp, TrendingDown, DollarSign, Target, Timer,
  ChevronDown, ChevronUp, Info, BarChart3, AlertCircle, Shield,
  Copy, History, X, Wallet, FlaskConical, ArrowRight
} from 'lucide-react';
import StrategyBacktester from './StrategyBacktester';
import AdaptiveLearning from './AdaptiveLearning';
import { TradingModeSelector, IntelligenceDashboard } from './trader';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Safe copy to clipboard helper
const safeCopyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand("copy");
    document.body.removeChild(textArea);
    return true;
  }
};

export default function UnifiedAutoTrader({
  status,
  logs = [],
  loading,
  onToggle,
  onUpdateSettings,
  onRunScan,
  onRefresh,
  custodialWallet,
  onRefreshCustodial,
  onWithdraw,
  walletAddress,
  walletConnected,
  traderSettings,
  onSaveSettings
}) {
  const [activeSection, setActiveSection] = useState('controls');
  const [showSettingsPanel, setShowSettingsPanel] = useState(false);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  
  // Analytics state
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [performanceSummary, setPerformanceSummary] = useState(null);
  const [optimalSettings, setOptimalSettings] = useState(null);
  const [periodDays, setPeriodDays] = useState(30);
  
  // Settings form state
  const [settingsForm, setSettingsForm] = useState({
    auto_trade_mode: status?.settings?.mode || 'conservative',
    auto_min_confidence: status?.settings?.min_confidence || 0.60,
    auto_max_position_sol: status?.settings?.max_position_sol || 0.1,
    auto_total_daily_limit_sol: status?.settings?.total_daily_limit_sol || 1.0,
    auto_max_daily_trades: status?.settings?.max_daily_trades || 3,
    auto_cooldown_minutes: status?.settings?.cooldown_minutes || 30,
    auto_stop_loss_percent: status?.settings?.stop_loss_percent || 15,
    auto_take_profit_percent: status?.settings?.take_profit_percent || 50,
    auto_require_multiple_signals: status?.settings?.require_multiple_signals || false,
    auto_pause_on_loss: status?.settings?.pause_on_loss || true,
    auto_trailing_stop_enabled: status?.settings?.trailing_stop_enabled || false,
    auto_trailing_stop_percent: status?.settings?.trailing_stop_percent || 5,
    auto_scale_in_enabled: status?.settings?.scale_in_enabled || false,
    auto_scale_in_threshold: status?.settings?.scale_in_threshold || 5,
    auto_scale_in_max_adds: status?.settings?.scale_in_max_adds || 2,
    auto_avoid_volatile_hours: status?.settings?.avoid_volatile_hours ?? true,
    auto_profit_target_alert: status?.settings?.profit_target_alert ?? true
  });

  // Update form when status changes
  useEffect(() => {
    if (status?.settings) {
      setSettingsForm(prev => ({
        ...prev,
        auto_trade_mode: status.settings.mode || prev.auto_trade_mode,
        auto_min_confidence: status.settings.min_confidence || prev.auto_min_confidence,
        auto_max_position_sol: status.settings.max_position_sol || prev.auto_max_position_sol,
        auto_total_daily_limit_sol: status.settings.total_daily_limit_sol || prev.auto_total_daily_limit_sol,
        auto_max_daily_trades: status.settings.max_daily_trades || prev.auto_max_daily_trades,
        auto_cooldown_minutes: status.settings.cooldown_minutes || prev.auto_cooldown_minutes,
        auto_stop_loss_percent: status.settings.stop_loss_percent || prev.auto_stop_loss_percent,
        auto_take_profit_percent: status.settings.take_profit_percent || prev.auto_take_profit_percent,
        auto_require_multiple_signals: status.settings.require_multiple_signals ?? prev.auto_require_multiple_signals,
        auto_pause_on_loss: status.settings.pause_on_loss ?? prev.auto_pause_on_loss,
        auto_trailing_stop_enabled: status.settings.trailing_stop_enabled ?? prev.auto_trailing_stop_enabled,
        auto_trailing_stop_percent: status.settings.trailing_stop_percent || prev.auto_trailing_stop_percent,
        auto_scale_in_enabled: status.settings.scale_in_enabled ?? prev.auto_scale_in_enabled,
        auto_scale_in_threshold: status.settings.scale_in_threshold || prev.auto_scale_in_threshold,
        auto_scale_in_max_adds: status.settings.scale_in_max_adds || prev.auto_scale_in_max_adds,
        auto_avoid_volatile_hours: status.settings.avoid_volatile_hours ?? prev.auto_avoid_volatile_hours,
        auto_profit_target_alert: status.settings.profit_target_alert ?? prev.auto_profit_target_alert
      }));
    }
  }, [status]);

  // Fetch analytics data
  const fetchAnalytics = useCallback(async () => {
    try {
      setAnalyticsLoading(true);
      const [perfRes, optRes] = await Promise.all([
        axios.get(`${API}/signal-analytics/performance-summary?period_days=${periodDays}`),
        axios.get(`${API}/signal-analytics/optimal-settings`)
      ]);
      
      setPerformanceSummary(perfRes.data);
      setOptimalSettings(optRes.data);
    } catch (e) {
      console.error('Failed to fetch analytics:', e);
    } finally {
      setAnalyticsLoading(false);
    }
  }, [periodDays]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Derived values
  const isEnabled = status?.auto_trade_enabled;
  const isPaused = status?.is_paused;
  const todayStats = status?.today_stats || {};
  const strategies = performanceSummary?.strategies || [];
  
  // Calculate average metrics
  const avgWinRate = strategies.length > 0
    ? strategies.reduce((acc, s) => acc + (s.win_rate_24h || s.approval_rate || 0), 0) / strategies.length
    : 0;
  const avgConfidence = strategies.length > 0
    ? strategies.reduce((acc, s) => acc + (s.avg_confidence || 0), 0) / strategies.length
    : 0;
  const recommendedConfidence = optimalSettings?.settings?.recommended_min_confidence || 0.55;

  // Handle save settings
  const handleSaveSettings = async () => {
    if (!walletAddress) return;
    
    await onUpdateSettings({
      auto_trade_mode: settingsForm.auto_trade_mode,
      auto_min_confidence: settingsForm.auto_min_confidence,
      auto_max_position_sol: settingsForm.auto_max_position_sol,
      auto_total_daily_limit_sol: settingsForm.auto_total_daily_limit_sol,
      auto_max_daily_trades: settingsForm.auto_max_daily_trades,
      auto_cooldown_minutes: settingsForm.auto_cooldown_minutes,
      auto_stop_loss_percent: settingsForm.auto_stop_loss_percent,
      auto_take_profit_percent: settingsForm.auto_take_profit_percent,
      auto_require_multiple_signals: settingsForm.auto_require_multiple_signals,
      auto_pause_on_loss: settingsForm.auto_pause_on_loss,
      auto_trailing_stop_enabled: settingsForm.auto_trailing_stop_enabled,
      auto_trailing_stop_percent: settingsForm.auto_trailing_stop_percent,
      auto_scale_in_enabled: settingsForm.auto_scale_in_enabled,
      auto_scale_in_threshold: settingsForm.auto_scale_in_threshold,
      auto_scale_in_max_adds: settingsForm.auto_scale_in_max_adds,
      auto_avoid_volatile_hours: settingsForm.auto_avoid_volatile_hours,
      auto_profit_target_alert: settingsForm.auto_profit_target_alert
    });
    
    setShowSettingsPanel(false);
  };

  // Apply recommended settings from analytics
  const applyRecommendedSettings = () => {
    if (!optimalSettings?.settings) return;
    
    const rec = optimalSettings.settings;
    setSettingsForm(prev => ({
      ...prev,
      auto_min_confidence: rec.recommended_min_confidence || prev.auto_min_confidence,
      auto_max_daily_trades: rec.auto_trade?.recommended_max_daily_trades || prev.auto_max_daily_trades,
      auto_cooldown_minutes: rec.auto_trade?.recommended_cooldown_minutes || prev.auto_cooldown_minutes,
      auto_require_multiple_signals: rec.require_multiple_strategies ?? prev.auto_require_multiple_signals
    }));
    
    toast.success('Applied recommended settings from analytics');
    setShowSettingsPanel(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#D946EF]" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="unified-auto-trader">
      {/* Header with Analytics Summary */}
      <div className="glass-card rounded-2xl p-5 border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center">
              <Cpu className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                Auto-Trade Engine
                {isEnabled && !isPaused && (
                  <Badge className="bg-emerald-500/20 text-emerald-400 text-xs animate-pulse">ACTIVE</Badge>
                )}
                {isPaused && (
                  <Badge className="bg-amber-500/20 text-amber-400 text-xs">PAUSED</Badge>
                )}
              </h2>
              <p className="text-sm text-slate-400">
                AI-powered trading with data-driven insights
              </p>
            </div>
          </div>
          
          {/* Master Toggle + Auto Optimization */}
          <div className="flex items-center gap-3">
            {/* Auto Optimization Toggle */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => onUpdateSettings({ auto_optimization_enabled: !status?.auto_optimization_enabled })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  status?.auto_optimization_enabled ? 'bg-[#D946EF]' : 'bg-slate-600'
                }`}
                title={status?.auto_optimization_enabled 
                  ? "Auto Optimization ON - Using data-driven settings" 
                  : "Auto Optimization OFF - Using manual settings"}
                data-testid="auto-optimization-toggle"
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    status?.auto_optimization_enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <span className="text-xs text-slate-400 hidden sm:inline">
                {status?.auto_optimization_enabled ? 'Auto Optimize' : 'Manual'}
              </span>
            </div>
            
            {/* Enable/Disable Button */}
            <Button
              onClick={() => onToggle(!isEnabled)}
              className={isEnabled 
                ? "bg-gradient-to-r from-emerald-500 to-emerald-600 text-white" 
                : "bg-slate-700 text-slate-300"
              }
              data-testid="auto-trade-toggle"
            >
              {isEnabled ? (
                <>
                  <Pause className="w-4 h-4 mr-2" />
                  Disable
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Enable
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Analytics Quick View */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard 
            label="Win Rate (24h)"
            value={avgWinRate > 0 ? `${avgWinRate.toFixed(1)}%` : 'N/A'}
            icon={<TrendingUp className="w-4 h-4" />}
            color={avgWinRate >= 50 ? 'green' : avgWinRate >= 40 ? 'amber' : 'red'}
            loading={analyticsLoading}
          />
          <MetricCard 
            label="Avg Confidence"
            value={avgConfidence > 0 ? `${(avgConfidence * 100).toFixed(0)}%` : 'N/A'}
            icon={<Target className="w-4 h-4" />}
            color="purple"
            loading={analyticsLoading}
          />
          <MetricCard 
            label="Recommended Min"
            value={`${(recommendedConfidence * 100).toFixed(0)}%`}
            icon={<Zap className="w-4 h-4" />}
            color="cyan"
            loading={analyticsLoading}
            hint="Based on backtest"
          />
          <MetricCard 
            label="Your Setting"
            value={`${(settingsForm.auto_min_confidence * 100).toFixed(0)}%`}
            icon={<Settings className="w-4 h-4" />}
            color={settingsForm.auto_min_confidence >= recommendedConfidence ? 'green' : 'amber'}
            loading={false}
          />
        </div>

        {/* Auto Optimization Status */}
        {status?.auto_optimization_enabled && optimalSettings?.sufficient_data && (
          <div className="mt-4 p-3 bg-[#D946EF]/10 border border-[#D946EF]/30 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-[#D946EF]/20 flex items-center justify-center">
                <Zap className="w-4 h-4 text-[#D946EF]" />
              </div>
              <div>
                <p className="text-sm text-[#D946EF] font-medium">Auto Optimization Active</p>
                <p className="text-xs text-slate-400">
                  Using data-driven settings: Min {(optimalSettings?.settings?.auto_trade?.recommended_min_confidence * 100 || 60).toFixed(0)}% confidence, 
                  {' '}{optimalSettings?.settings?.auto_trade?.recommended_max_daily_trades || 3} max daily trades,
                  {' '}{optimalSettings?.settings?.auto_trade?.recommended_cooldown_minutes || 45}min cooldown
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Recommendation Alert */}
        {optimalSettings?.sufficient_data && settingsForm.auto_min_confidence < recommendedConfidence && (
          <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-amber-400" />
              <div>
                <p className="text-sm text-amber-200 font-medium">Confidence Below Recommended</p>
                <p className="text-xs text-amber-400/80">
                  Analytics suggest {(recommendedConfidence * 100).toFixed(0)}% min confidence for better win rates
                </p>
              </div>
            </div>
            <Button
              onClick={applyRecommendedSettings}
              size="sm"
              className="bg-amber-500 text-black hover:bg-amber-400"
            >
              <Zap className="w-4 h-4 mr-1" />
              Apply
            </Button>
          </div>
        )}
      </div>

      {/* Section Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {[
          { id: 'controls', label: 'Controls & Wallet', icon: <Wallet className="w-4 h-4" /> },
          { id: 'settings', label: 'Trade Settings', icon: <Settings className="w-4 h-4" /> },
          { id: 'analytics', label: 'Performance', icon: <BarChart3 className="w-4 h-4" /> },
          { id: 'backtester', label: 'Backtester', icon: <FlaskConical className="w-4 h-4" /> },
          { id: 'adaptive', label: 'Adaptive AI', icon: <Cpu className="w-4 h-4" /> }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSection(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              activeSection === tab.id
                ? 'bg-[#D946EF]/20 text-[#D946EF] border border-[#D946EF]/30'
                : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Controls & Wallet Section */}
      {activeSection === 'controls' && (
        <div className="space-y-4">
          {/* Today's Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              icon={<Activity className="w-4 h-4" />}
              label="Trades Today"
              value={`${todayStats.trades_executed || 0}/${status?.settings?.max_daily_trades || 3}`}
            />
            <StatCard
              icon={<DollarSign className="w-4 h-4" />}
              label="SOL Used"
              value={`${todayStats.total_sol_used?.toFixed(3) || '0.000'}`}
            />
            <StatCard
              icon={<Target className="w-4 h-4" />}
              label="Mode"
              value={(traderSettings?.trading_mode || status?.settings?.mode || 'normal').charAt(0).toUpperCase() + (traderSettings?.trading_mode || status?.settings?.mode || 'normal').slice(1)}
              color={
                (traderSettings?.trading_mode || status?.settings?.mode) === 'aggressive' ? '#FF6B6B' : 
                (traderSettings?.trading_mode || status?.settings?.mode) === 'sniper' ? '#FF6B6B' :
                (traderSettings?.trading_mode || status?.settings?.mode) === 'normal' ? '#F5D300' : '#00FFA3'
              }
            />
            <StatCard
              icon={<Timer className="w-4 h-4" />}
              label="Cooldown"
              value={`${status?.settings?.cooldown_minutes || 30}m`}
            />
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={onRunScan}
              disabled={!isEnabled || isPaused}
              className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] hover:opacity-90 disabled:opacity-50"
              data-testid="run-auto-scan-btn"
            >
              <Zap className="w-4 h-4 mr-2" />
              Run Auto-Scan Now
            </Button>
            <Button
              onClick={onRefresh}
              variant="outline"
              className="border-white/20 text-slate-300"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>

          {/* Activity Log */}
          <ActivityLog logs={logs} />
          
          {/* Intelligence Systems */}
          <IntelligenceDashboard walletAddress={walletAddress} />
        </div>
      )}

      {/* Trade Settings Section */}
      {activeSection === 'settings' && (
        <TradeSettingsPanel
          settingsForm={settingsForm}
          setSettingsForm={setSettingsForm}
          showAdvancedSettings={showAdvancedSettings}
          setShowAdvancedSettings={setShowAdvancedSettings}
          handleSaveSettings={handleSaveSettings}
          recommendedConfidence={recommendedConfidence}
          optimalSettings={optimalSettings}
          tradingMode={traderSettings?.trading_mode || settingsForm.auto_trade_mode || "normal"}
          onTradingModeChange={async (mode) => {
            setSettingsForm(f => ({ ...f, auto_trade_mode: mode }));
            await onUpdateSettings({ auto_trade_mode: mode });
          }}
        />
      )}

      {/* Performance Analytics Section */}
      {activeSection === 'analytics' && (
        <PerformanceAnalytics
          performanceSummary={performanceSummary}
          periodDays={periodDays}
          setPeriodDays={setPeriodDays}
          onRefresh={fetchAnalytics}
          loading={analyticsLoading}
        />
      )}

      {/* Backtester Section */}
      {activeSection === 'backtester' && (
        <StrategyBacktester />
      )}

      {/* Adaptive Learning Section */}
      {activeSection === 'adaptive' && (
        <AdaptiveLearning />
      )}
    </div>
  );
}

// Sub-components

function MetricCard({ label, value, icon, color, loading, hint }) {
  const colorClasses = {
    green: 'bg-emerald-500/20 text-emerald-400',
    red: 'bg-red-500/20 text-red-400',
    amber: 'bg-amber-500/20 text-amber-400',
    purple: 'bg-[#D946EF]/20 text-[#D946EF]',
    cyan: 'bg-[#00C2FF]/20 text-[#00C2FF]'
  };
  
  return (
    <div className="glass-card rounded-xl p-3 border border-white/10">
      <div className="flex items-center gap-2 mb-1">
        <div className={`p-1.5 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        <span className="text-[10px] text-slate-500 uppercase">{label}</span>
      </div>
      {loading ? (
        <div className="h-6 bg-white/5 rounded animate-pulse" />
      ) : (
        <p className="text-lg font-bold text-white">{value}</p>
      )}
      {hint && <p className="text-[10px] text-slate-500 mt-0.5">{hint}</p>}
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/5">
      <div className="flex items-center gap-2 text-slate-400 mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-xl font-bold" style={{ color: color || 'white' }}>
        {value}
      </p>
    </div>
  );
}

function ActivityLog({ logs }) {
  return (
    <div>
      <h4 className="font-bold text-sm text-slate-400 mb-3 flex items-center gap-2">
        <History className="w-4 h-4" />
        Recent Activity
      </h4>
      
      {logs.length === 0 ? (
        <div className="text-center py-8 bg-white/5 rounded-xl border border-dashed border-white/10">
          <Activity className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">No auto-trade activity yet</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {logs.map((log, i) => (
            <div 
              key={log.log_id || i}
              className={`flex items-center justify-between p-3 rounded-xl border ${
                log.action === 'auto_buy' ? 'bg-[#00FFA3]/5 border-[#00FFA3]/20' :
                log.action === 'auto_sell' ? 'bg-[#FF6B6B]/5 border-[#FF6B6B]/20' :
                'bg-white/5 border-white/10'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  log.action === 'auto_buy' ? 'bg-[#00FFA3]/20' :
                  log.action === 'auto_sell' ? 'bg-[#FF6B6B]/20' :
                  log.action === 'auto_enabled' ? 'bg-[#D946EF]/20' :
                  'bg-slate-700'
                }`}>
                  {log.action === 'auto_buy' && <TrendingUp className="w-4 h-4 text-[#00FFA3]" />}
                  {log.action === 'auto_sell' && <TrendingDown className="w-4 h-4 text-[#FF6B6B]" />}
                  {log.action === 'auto_enabled' && <Play className="w-4 h-4 text-[#D946EF]" />}
                  {log.action === 'auto_disabled' && <Pause className="w-4 h-4 text-slate-400" />}
                  {log.action === 'auto_skip' && <X className="w-4 h-4 text-slate-400" />}
                </div>
                <div>
                  <p className="text-sm font-medium text-white">
                    {log.action === 'auto_buy' && `AUTO BUY ${log.token_symbol}`}
                    {log.action === 'auto_sell' && `AUTO SELL ${log.token_symbol}`}
                    {log.action === 'auto_enabled' && 'Auto-trading enabled'}
                    {log.action === 'auto_disabled' && 'Auto-trading disabled'}
                    {log.action === 'auto_skip' && `Skipped ${log.token_symbol}`}
                  </p>
                  <p className="text-[10px] text-slate-500 truncate max-w-[200px]">
                    {log.reason}
                  </p>
                </div>
              </div>
              <div className="text-right">
                {log.amount_sol && (
                  <p className="text-sm font-mono text-white">{log.amount_sol?.toFixed(3)} SOL</p>
                )}
                <p className="text-[10px] text-slate-500">
                  {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TradeSettingsPanel({ 
  settingsForm, 
  setSettingsForm, 
  showAdvancedSettings, 
  setShowAdvancedSettings,
  handleSaveSettings,
  recommendedConfidence,
  optimalSettings,
  tradingMode,
  onTradingModeChange
}) {
  return (
    <div className="glass-card rounded-2xl p-6 border border-white/10 space-y-5">
      <h4 className="font-bold text-lg flex items-center gap-2">
        <Settings className="w-5 h-5 text-[#D946EF]" />
        Auto-Trade Configuration
      </h4>

      {/* Trading Mode Tile Selector */}
      <TradingModeSelector
        currentMode={tradingMode}
        onModeChange={onTradingModeChange}
      />

      <div className="grid md:grid-cols-2 gap-5">
        {/* Min Confidence with Recommendation */}
        <div>
          <label className="text-sm text-slate-400 mb-2 block flex items-center justify-between">
            <span>Min Confidence: {(settingsForm.auto_min_confidence * 100).toFixed(0)}%</span>
            {recommendedConfidence > 0 && (
              <span className="text-[10px] text-[#00C2FF]">
                Rec: {(recommendedConfidence * 100).toFixed(0)}%
              </span>
            )}
          </label>
          <input
            type="range"
            min="0.5"
            max="0.9"
            step="0.05"
            value={settingsForm.auto_min_confidence}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_min_confidence: parseFloat(e.target.value) }))}
            className="w-full"
          />
          <div className="flex justify-between text-[10px] text-slate-500">
            <span>50%</span>
            <span>90%</span>
          </div>
        </div>

        {/* Max Position */}
        <div>
          <label className="text-sm text-slate-400 mb-2 block">
            Max Position: {settingsForm.auto_max_position_sol} SOL
          </label>
          <input
            type="range"
            min="0.01"
            max="1"
            step="0.01"
            value={settingsForm.auto_max_position_sol}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_max_position_sol: parseFloat(e.target.value) }))}
            className="w-full"
          />
        </div>

        {/* Daily Limit */}
        <div>
          <label className="text-sm text-slate-400 mb-2 block">
            Daily SOL Limit: {settingsForm.auto_total_daily_limit_sol} SOL
          </label>
          <input
            type="range"
            min="0.1"
            max="5"
            step="0.1"
            value={settingsForm.auto_total_daily_limit_sol}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_total_daily_limit_sol: parseFloat(e.target.value) }))}
            className="w-full"
          />
        </div>

        {/* Max Daily Trades */}
        <div>
          <label className="text-sm text-slate-400 mb-2 block">
            Max Daily Trades: {settingsForm.auto_max_daily_trades}
          </label>
          <input
            type="range"
            min="1"
            max="20"
            step="1"
            value={settingsForm.auto_max_daily_trades}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_max_daily_trades: parseInt(e.target.value) }))}
            className="w-full"
          />
        </div>

        {/* Cooldown */}
        <div>
          <label className="text-sm text-slate-400 mb-2 block">
            Cooldown: {settingsForm.auto_cooldown_minutes} minutes
          </label>
          <input
            type="range"
            min="5"
            max="120"
            step="5"
            value={settingsForm.auto_cooldown_minutes}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_cooldown_minutes: parseInt(e.target.value) }))}
            className="w-full"
          />
        </div>

        {/* Stop Loss */}
        <div>
          <label className="text-sm text-slate-400 mb-2 block">
            Stop Loss: {settingsForm.auto_stop_loss_percent}%
          </label>
          <input
            type="range"
            min="2"
            max="50"
            step="1"
            value={settingsForm.auto_stop_loss_percent}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_stop_loss_percent: parseInt(e.target.value) }))}
            className="w-full"
          />
          <p className="text-[10px] text-[#FF6B6B] mt-1">Auto-sell if price drops by this %</p>
        </div>

        {/* Take Profit */}
        <div>
          <label className="text-sm text-slate-400 mb-2 block">
            Take Profit: {settingsForm.auto_take_profit_percent}%
          </label>
          <input
            type="range"
            min="5"
            max="200"
            step="5"
            value={settingsForm.auto_take_profit_percent}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_take_profit_percent: parseInt(e.target.value) }))}
            className="w-full"
          />
          <p className="text-[10px] text-[#00FFA3] mt-1">Auto-sell if price rises by this %</p>
        </div>
      </div>

      {/* Toggle Options */}
      <div className="flex flex-wrap gap-4 pt-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={settingsForm.auto_require_multiple_signals}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_require_multiple_signals: e.target.checked }))}
            className="w-4 h-4 rounded border-white/30"
          />
          <span className="text-sm text-slate-300">Require 2+ strategies to agree</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={settingsForm.auto_pause_on_loss}
            onChange={(e) => setSettingsForm(f => ({ ...f, auto_pause_on_loss: e.target.checked }))}
            className="w-4 h-4 rounded border-white/30"
          />
          <span className="text-sm text-slate-300">Pause after a loss</span>
        </label>
      </div>

      {/* Advanced Settings */}
      <div className="mt-4 pt-4 border-t border-white/10">
        <button
          onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-3"
        >
          <Settings className="w-4 h-4" />
          Advanced Settings
          {showAdvancedSettings ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        
        {showAdvancedSettings && (
          <div className="space-y-4 p-3 bg-black/30 rounded-xl border border-white/5">
            {/* Trailing Stop */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-white">Trailing Stop-Loss</p>
                <p className="text-[10px] text-slate-500">Automatically raise stop as price increases</p>
              </div>
              <input
                type="checkbox"
                checked={settingsForm.auto_trailing_stop_enabled || false}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_trailing_stop_enabled: e.target.checked }))}
                className="w-4 h-4 rounded border-white/30"
              />
            </div>
            
            {settingsForm.auto_trailing_stop_enabled && (
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Trail Distance: {settingsForm.auto_trailing_stop_percent || 5}%
                </label>
                <input
                  type="range"
                  min="1"
                  max="20"
                  step="0.5"
                  value={settingsForm.auto_trailing_stop_percent || 5}
                  onChange={(e) => setSettingsForm(f => ({ ...f, auto_trailing_stop_percent: parseFloat(e.target.value) }))}
                  className="w-full"
                />
              </div>
            )}
            
            {/* DCA on Dip */}
            <div className="flex items-center justify-between pt-2 border-t border-white/5">
              <div>
                <p className="text-sm text-white">DCA on Dip</p>
                <p className="text-[10px] text-slate-500">Add to position when price drops</p>
              </div>
              <input
                type="checkbox"
                checked={settingsForm.auto_scale_in_enabled || false}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_scale_in_enabled: e.target.checked }))}
                className="w-4 h-4 rounded border-white/30"
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-3 pt-2">
        <Button
          onClick={handleSaveSettings}
          className="flex-1 bg-[#D946EF] hover:bg-[#D946EF]/80"
        >
          Save Settings
        </Button>
      </div>
    </div>
  );
}

function PerformanceAnalytics({ performanceSummary, periodDays, setPeriodDays, onRefresh, loading }) {
  const strategies = performanceSummary?.strategies || [];
  const topTokens = performanceSummary?.top_tokens || [];
  const recommendations = performanceSummary?.recommendations || [];
  const totalSignals = performanceSummary?.total_signals_analyzed || performanceSummary?.total_outcomes_analyzed || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[#D946EF]" />
            Signal Performance
          </h3>
          <p className="text-sm text-slate-400">{totalSignals} signals analyzed</p>
        </div>
        <div className="flex items-center gap-3">
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
            onClick={onRefresh}
            disabled={loading}
            className="border-white/10"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-8 h-8 animate-spin text-[#D946EF]" />
        </div>
      ) : (
        <>
          {/* Strategy Performance */}
          <div className="glass-card rounded-xl p-4 border border-white/10">
            <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Strategy Performance</h4>
            <div className="space-y-4">
              {strategies.map((strat, i) => (
                <StrategyRow key={i} strategy={strat} maxSignals={Math.max(...strategies.map(s => s.total_signals || 0))} />
              ))}
              {strategies.length === 0 && (
                <p className="text-sm text-slate-500 text-center py-8">No strategy data available yet</p>
              )}
            </div>
          </div>

          {/* Top Tokens */}
          {topTokens.length > 0 && (
            <div className="glass-card rounded-xl p-4 border border-white/10">
              <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Top Performing Tokens</h4>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
                {topTokens.slice(0, 12).map((token, i) => (
                  <TokenCell key={i} token={token} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StrategyRow({ strategy, maxSignals }) {
  const widthPercent = maxSignals > 0 ? ((strategy.total_signals || 0) / maxSignals) * 100 : 0;
  const approvalRate = strategy.approval_rate || strategy.win_rate_24h || 0;
  const avgConfidence = strategy.avg_confidence || 0;
  
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-white font-medium capitalize">{strategy.strategy || 'Unknown'}</span>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-slate-400">{strategy.total_signals || 0} signals</span>
          <span className={avgConfidence >= 0.55 ? 'text-emerald-400' : 'text-amber-400'}>
            {(avgConfidence * 100).toFixed(0)}% conf
          </span>
          <Badge className={`${approvalRate > 10 ? 'bg-emerald-500' : approvalRate > 5 ? 'bg-amber-500' : 'bg-red-500'} text-white text-[10px]`}>
            {approvalRate.toFixed(1)}%
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

function TokenCell({ token }) {
  const confidence = token.avg_confidence || 0;
  
  let bgColor;
  if (confidence >= 0.65) bgColor = 'bg-emerald-500';
  else if (confidence >= 0.55) bgColor = 'bg-emerald-600/80';
  else if (confidence >= 0.50) bgColor = 'bg-amber-500/80';
  else bgColor = 'bg-red-500/80';
  
  return (
    <div className={`${bgColor} rounded-lg p-2 text-center`}>
      <p className="text-white font-bold text-xs truncate">{token.token}</p>
      <p className="text-white/60 text-[10px]">{token.total_signals}</p>
    </div>
  );
}
