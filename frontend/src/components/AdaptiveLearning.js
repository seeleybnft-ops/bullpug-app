/**
 * AdaptiveLearning Component
 * 
 * Displays adaptive learning insights and A/B testing controls:
 * - Real-time win rate from actual outcomes
 * - Recommended settings based on outcome data
 * - A/B test creation and monitoring
 * - Auto-tracking status
 */

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Brain, Sparkles, TestTube2, Clock, TrendingUp, TrendingDown,
  Loader2, RefreshCw, Play, Pause, Check, AlertCircle,
  BarChart3, Zap, Target, ArrowRight, Settings
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdaptiveLearning() {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('learning');
  
  // Adaptive learning state
  const [adaptiveSettings, setAdaptiveSettings] = useState(null);
  const [applyingSettings, setApplyingSettings] = useState(false);
  
  // Auto-tracking state
  const [trackingStatus, setTrackingStatus] = useState(null);
  const [runningTracking, setRunningTracking] = useState(false);
  
  // A/B testing state
  const [abTests, setAbTests] = useState([]);
  const [creatingTest, setCreatingTest] = useState(false);
  const [newTestConfig, setNewTestConfig] = useState({
    name: '',
    variant_a_confidence: 0.55,
    variant_b_confidence: 0.60,
    traffic_split_a: 50
  });

  // Fetch adaptive settings
  const fetchAdaptiveSettings = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/signal-analytics/adaptive/current-settings`);
      setAdaptiveSettings(data);
    } catch (e) {
      console.error('Failed to fetch adaptive settings:', e);
    }
  }, []);

  // Fetch tracking status
  const fetchTrackingStatus = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/signal-analytics/auto-tracking/status`);
      setTrackingStatus(data);
    } catch (e) {
      console.error('Failed to fetch tracking status:', e);
    }
  }, []);

  // Fetch A/B tests
  const fetchAbTests = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/signal-analytics/ab-test/list`);
      setAbTests(data.tests || []);
    } catch (e) {
      console.error('Failed to fetch A/B tests:', e);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await Promise.all([
        fetchAdaptiveSettings(),
        fetchTrackingStatus(),
        fetchAbTests()
      ]);
      setLoading(false);
    };
    load();
  }, [fetchAdaptiveSettings, fetchTrackingStatus, fetchAbTests]);

  // Run tracking
  const runTracking = async () => {
    try {
      setRunningTracking(true);
      const { data } = await axios.post(`${API}/signal-analytics/auto-tracking/run`);
      
      if (data.success) {
        const r = data.results;
        toast.success(`Tracked ${r.outcomes_1h + r.outcomes_4h + r.outcomes_24h} outcomes from ${r.signals_processed} signals`);
        await fetchTrackingStatus();
        await fetchAdaptiveSettings();
      } else {
        toast.error(data.message || 'Tracking failed');
      }
    } catch (e) {
      toast.error('Failed to run tracking');
    } finally {
      setRunningTracking(false);
    }
  };

  // Apply adaptive settings
  const applyAdaptiveSettings = async () => {
    try {
      setApplyingSettings(true);
      const { data } = await axios.post(`${API}/signal-analytics/adaptive/apply`);
      
      if (data.success) {
        toast.success(`Applied adaptive settings: ${data.applied_settings.min_confidence*100}% confidence`);
        await fetchAdaptiveSettings();
      } else {
        toast.error(data.message || 'Failed to apply settings');
      }
    } catch (e) {
      toast.error('Failed to apply settings');
    } finally {
      setApplyingSettings(false);
    }
  };

  // Create A/B test
  const createAbTest = async () => {
    if (!newTestConfig.name.trim()) {
      toast.error('Please enter a test name');
      return;
    }
    
    try {
      setCreatingTest(true);
      const params = new URLSearchParams({
        name: newTestConfig.name,
        variant_a_confidence: newTestConfig.variant_a_confidence,
        variant_b_confidence: newTestConfig.variant_b_confidence,
        traffic_split_a: newTestConfig.traffic_split_a
      });
      
      const { data } = await axios.post(`${API}/signal-analytics/ab-test/create?${params}`);
      
      if (data.success) {
        toast.success(`Created A/B test: ${newTestConfig.name}`);
        setNewTestConfig({ name: '', variant_a_confidence: 0.55, variant_b_confidence: 0.60, traffic_split_a: 50 });
        await fetchAbTests();
      }
    } catch (e) {
      toast.error('Failed to create A/B test');
    } finally {
      setCreatingTest(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#D946EF]" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="adaptive-learning">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Brain className="w-5 h-5 text-[#D946EF]" />
            Adaptive Learning
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            Continuously improve win rate using real outcome data
          </p>
        </div>
        
        <Button
          onClick={runTracking}
          disabled={runningTracking}
          size="sm"
          className="bg-[#00C2FF] hover:bg-[#00C2FF]/80 text-white"
        >
          {runningTracking ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4 mr-2" />
          )}
          Update Outcomes
        </Button>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-white/10 pb-2">
        {[
          { id: 'learning', label: 'Learning', icon: <Brain className="w-4 h-4" /> },
          { id: 'tracking', label: 'Tracking', icon: <Clock className="w-4 h-4" /> },
          { id: 'abtesting', label: 'A/B Testing', icon: <TestTube2 className="w-4 h-4" /> }
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

      {/* Learning Tab */}
      {activeTab === 'learning' && adaptiveSettings && (
        <div className="space-y-4">
          {!adaptiveSettings.sufficient_data ? (
            <div className="glass-card rounded-xl p-6 border border-amber-500/30 bg-amber-500/5 text-center">
              <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-white mb-2">Building Learning Data</h4>
              <p className="text-sm text-slate-400 mb-4">{adaptiveSettings.message}</p>
              <p className="text-xs text-slate-500">
                Current outcomes: {adaptiveSettings.outcomes_count || 0} / 20 required
              </p>
            </div>
          ) : (
            <>
              {/* Recommended Settings Card */}
              <div className="glass-card rounded-xl p-4 border border-[#D946EF]/30 bg-[#D946EF]/5">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-sm font-bold text-[#D946EF] uppercase flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    Learned Optimal Settings
                  </h4>
                  <Badge className="bg-emerald-500/20 text-emerald-400">
                    {adaptiveSettings.outcomes_analyzed} outcomes analyzed
                  </Badge>
                </div>
                
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="p-3 rounded bg-white/5">
                    <p className="text-xs text-slate-400">Min Confidence</p>
                    <p className="text-2xl font-bold text-white">
                      {(adaptiveSettings.recommended_settings.min_confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="p-3 rounded bg-white/5">
                    <p className="text-xs text-slate-400">Best Strategy</p>
                    <p className="text-2xl font-bold text-white capitalize">
                      {adaptiveSettings.recommended_settings.priority_strategy}
                    </p>
                  </div>
                  <div className="p-3 rounded bg-white/5">
                    <p className="text-xs text-slate-400">Trend Align</p>
                    <p className="text-2xl font-bold text-white">
                      {adaptiveSettings.recommended_settings.require_trend_alignment ? 'Yes' : 'No'}
                    </p>
                  </div>
                </div>

                {/* Improvement Stats */}
                {adaptiveSettings.improvement_over_default && (
                  <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/20 mb-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-300">
                        Default Win Rate: {adaptiveSettings.improvement_over_default.default_win_rate}%
                      </span>
                      <ArrowRight className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-emerald-400 font-bold">
                        Optimized: {adaptiveSettings.improvement_over_default.optimized_win_rate}%
                      </span>
                      <Badge className="bg-emerald-500/20 text-emerald-400">
                        +{adaptiveSettings.improvement_over_default.improvement_pct}%
                      </Badge>
                    </div>
                  </div>
                )}

                <Button
                  onClick={applyAdaptiveSettings}
                  disabled={applyingSettings}
                  className="w-full bg-gradient-to-r from-[#D946EF] to-[#00C2FF] text-white"
                >
                  {applyingSettings ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Check className="w-4 h-4 mr-2" />
                  )}
                  Apply Learned Settings
                </Button>
              </div>

              {/* Confidence Breakdown */}
              <div className="glass-card rounded-xl p-4 border border-white/10">
                <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Win Rate by Confidence (Real Outcomes)</h4>
                <div className="space-y-2">
                  {adaptiveSettings.confidence_breakdown?.map((item, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <span className="text-sm text-slate-400 w-24">{item.bucket}</span>
                      <div className="flex-1 h-6 bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all ${
                            item.win_rate >= 60 ? 'bg-emerald-500' : 
                            item.win_rate >= 50 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${item.win_rate}%` }}
                        />
                      </div>
                      <span className="text-sm text-white w-16 text-right">{item.win_rate}%</span>
                      <span className="text-xs text-slate-500 w-12">({item.total})</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Strategy Breakdown */}
              <div className="glass-card rounded-xl p-4 border border-white/10">
                <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Win Rate by Strategy (Real Outcomes)</h4>
                <div className="space-y-2">
                  {adaptiveSettings.strategy_breakdown?.map((item, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded bg-white/5">
                      <span className="text-white capitalize font-medium">{item.strategy}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-slate-400">{item.total} signals</span>
                        <Badge className={item.win_rate >= 55 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}>
                          {item.win_rate}% win
                        </Badge>
                        <span className={`text-sm ${item.avg_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {item.avg_pnl >= 0 ? '+' : ''}{item.avg_pnl}% avg
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Indicator Insights */}
              {adaptiveSettings.indicator_insights?.length > 0 && (
                <div className="glass-card rounded-xl p-4 border border-white/10">
                  <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Indicator Insights</h4>
                  <div className="space-y-2">
                    {adaptiveSettings.indicator_insights.map((insight, i) => (
                      <div key={i} className="p-3 rounded bg-white/5 text-sm text-slate-300">
                        {insight}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Tracking Tab */}
      {activeTab === 'tracking' && trackingStatus && (
        <div className="space-y-4">
          {/* Tracking Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard 
              label="Total Outcomes"
              value={trackingStatus.outcome_stats?.total_outcomes || 0}
              icon={<BarChart3 className="w-5 h-5" />}
            />
            <StatCard 
              label="With 1h Data"
              value={trackingStatus.outcome_stats?.with_1h_data || 0}
              icon={<Clock className="w-5 h-5" />}
            />
            <StatCard 
              label="With 4h Data"
              value={trackingStatus.outcome_stats?.with_4h_data || 0}
              icon={<Clock className="w-5 h-5" />}
            />
            <StatCard 
              label="With 24h Data"
              value={trackingStatus.outcome_stats?.with_24h_data || 0}
              icon={<Clock className="w-5 h-5" />}
            />
          </div>

          {/* Config Card */}
          <div className="glass-card rounded-xl p-4 border border-white/10">
            <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Tracking Configuration</h4>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-white">Auto Tracking</span>
                <Badge className={trackingStatus.config?.enabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}>
                  {trackingStatus.config?.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-white">Track Interval</span>
                <span className="text-sm text-slate-400">{trackingStatus.config?.track_interval_minutes || 60} minutes</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-white">Total Runs</span>
                <span className="text-sm text-slate-400">{trackingStatus.config?.total_runs || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-white">Last Run</span>
                <span className="text-sm text-slate-400">
                  {trackingStatus.config?.last_run 
                    ? new Date(trackingStatus.config.last_run).toLocaleString()
                    : 'Never'
                  }
                </span>
              </div>
            </div>
          </div>

          {/* Recent Runs */}
          {trackingStatus.recent_runs?.length > 0 && (
            <div className="glass-card rounded-xl p-4 border border-white/10">
              <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Recent Tracking Runs</h4>
              <div className="space-y-2">
                {trackingStatus.recent_runs.slice(0, 5).map((run, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded bg-white/5 text-sm">
                    <span className="text-slate-400">{new Date(run.run_at).toLocaleString()}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-white">{run.signals_processed} signals</span>
                      <Badge className="bg-emerald-500/20 text-emerald-400">
                        {run.outcomes_1h + run.outcomes_4h + run.outcomes_24h} tracked
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* A/B Testing Tab */}
      {activeTab === 'abtesting' && (
        <div className="space-y-4">
          {/* Create New Test */}
          <div className="glass-card rounded-xl p-4 border border-white/10">
            <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">Create A/B Test</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="col-span-2">
                <label className="text-xs text-slate-400 block mb-1">Test Name</label>
                <input
                  type="text"
                  value={newTestConfig.name}
                  onChange={(e) => setNewTestConfig(c => ({ ...c, name: e.target.value }))}
                  placeholder="e.g., Confidence Threshold Test"
                  className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Variant A Conf</label>
                <select
                  value={newTestConfig.variant_a_confidence}
                  onChange={(e) => setNewTestConfig(c => ({ ...c, variant_a_confidence: parseFloat(e.target.value) }))}
                  className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                >
                  {[0.45, 0.50, 0.55, 0.60, 0.65].map(v => (
                    <option key={v} value={v}>{v*100}%</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Variant B Conf</label>
                <select
                  value={newTestConfig.variant_b_confidence}
                  onChange={(e) => setNewTestConfig(c => ({ ...c, variant_b_confidence: parseFloat(e.target.value) }))}
                  className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                >
                  {[0.45, 0.50, 0.55, 0.60, 0.65].map(v => (
                    <option key={v} value={v}>{v*100}%</option>
                  ))}
                </select>
              </div>
            </div>
            <Button
              onClick={createAbTest}
              disabled={creatingTest || !newTestConfig.name.trim()}
              className="w-full bg-[#D946EF] hover:bg-[#D946EF]/80 text-white"
            >
              {creatingTest ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <TestTube2 className="w-4 h-4 mr-2" />}
              Create A/B Test
            </Button>
          </div>

          {/* Active Tests */}
          <div className="glass-card rounded-xl p-4 border border-white/10">
            <h4 className="text-sm font-bold text-slate-400 uppercase mb-4">A/B Tests</h4>
            {abTests.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-4">No A/B tests created yet</p>
            ) : (
              <div className="space-y-3">
                {abTests.map((test, i) => (
                  <ABTestCard key={i} test={test} onRefresh={fetchAbTests} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon }) {
  return (
    <div className="glass-card rounded-xl p-4 border border-white/10">
      <div className="flex items-center gap-2 text-slate-400 mb-2">
        {icon}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-400">{label}</p>
    </div>
  );
}

function ABTestCard({ test, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  
  const variants = test.variants || [];
  const variantA = variants[0] || {};
  const variantB = variants[1] || {};
  
  const totalA = variantA.wins + variantA.losses + variantA.neutrals;
  const totalB = variantB.wins + variantB.losses + variantB.neutrals;
  const winRateA = totalA > 0 ? (variantA.wins / totalA * 100).toFixed(1) : 0;
  const winRateB = totalB > 0 ? (variantB.wins / totalB * 100).toFixed(1) : 0;
  
  return (
    <div className="p-3 rounded-lg bg-white/5 border border-white/5">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-white font-medium">{test.name}</span>
          <Badge className={
            test.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' :
            test.status === 'paused' ? 'bg-amber-500/20 text-amber-400' :
            'bg-slate-500/20 text-slate-400'
          }>
            {test.status}
          </Badge>
        </div>
        <span className="text-xs text-slate-500">
          {new Date(test.start_date).toLocaleDateString()}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mt-3">
        <div className="p-2 rounded bg-blue-500/10 border border-blue-500/20">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-blue-400">Variant A ({variantA.min_confidence*100}%)</span>
            <span className="text-xs text-slate-400">{totalA} signals</span>
          </div>
          <p className="text-lg font-bold text-white">{winRateA}% win</p>
        </div>
        <div className="p-2 rounded bg-purple-500/10 border border-purple-500/20">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-purple-400">Variant B ({variantB.min_confidence*100}%)</span>
            <span className="text-xs text-slate-400">{totalB} signals</span>
          </div>
          <p className="text-lg font-bold text-white">{winRateB}% win</p>
        </div>
      </div>
      
      {test.current_winner && (
        <div className="mt-3 p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-center">
          <span className="text-sm text-emerald-400">
            Winner: Variant {test.current_winner} ({test.winner_confidence}% confidence)
          </span>
        </div>
      )}
    </div>
  );
}
