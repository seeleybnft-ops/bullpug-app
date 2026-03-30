import { useState, useEffect, useCallback } from "react";
import { BarChart3, TrendingUp, Brain, Activity, Target, Zap } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;

const MetricCard = ({ label, value, sub, icon, color = "#00FFA3" }) => (
  <div data-testid={`metric-${label.toLowerCase().replace(/\s/g, '-')}`} className="bg-[#1a1a2e]/80 border border-[#2a2a4a] rounded-lg p-4">
    <div className="flex items-center gap-2 mb-1">
      <span style={{ color }}>{icon}</span>
      <span className="text-xs text-gray-400 uppercase tracking-wider">{label}</span>
    </div>
    <div className="text-xl font-bold text-white">{value}</div>
    {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
  </div>
);

const StrategyRow = ({ name, stats }) => {
  const winRate = stats.win_rate || 0;
  const barColor = winRate >= 60 ? "#00FFA3" : winRate >= 40 ? "#F5D300" : "#FF6B6B";
  return (
    <div data-testid={`strategy-${name}`} className="flex items-center gap-3 py-2 border-b border-[#2a2a4a]/50 last:border-0">
      <div className="w-32 text-sm text-gray-300 truncate">{name}</div>
      <div className="flex-1">
        <div className="h-2 bg-[#0a0a1a] rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(winRate, 100)}%`, backgroundColor: barColor }} />
        </div>
      </div>
      <div className="text-xs font-mono w-12 text-right" style={{ color: barColor }}>{winRate}%</div>
      <div className="text-xs text-gray-400 w-16 text-right">{stats.trades} trades</div>
      <div className={`text-xs font-mono w-20 text-right ${stats.total_pnl_sol >= 0 ? 'text-green-400' : 'text-red-400'}`}>
        {stats.total_pnl_sol >= 0 ? '+' : ''}{stats.total_pnl_sol?.toFixed(4)} SOL
      </div>
    </div>
  );
};

const ConfidenceBucket = ({ range, data }) => {
  const barWidth = data.count > 0 ? Math.max(5, (data.count / 10) * 100) : 0;
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="text-xs text-gray-400 w-16 font-mono">{range}</span>
      <div className="flex-1 flex items-center gap-2">
        <div className="flex-1 h-3 bg-[#0a0a1a] rounded-full overflow-hidden">
          <div className="h-full rounded-full bg-purple-500/70" style={{ width: `${Math.min(barWidth, 100)}%` }} />
        </div>
        <span className="text-xs text-gray-300 w-8">{data.count}</span>
      </div>
      <span className={`text-xs font-mono w-12 text-right ${data.win_rate >= 50 ? 'text-green-400' : data.win_rate > 0 ? 'text-yellow-400' : 'text-gray-500'}`}>
        {data.win_rate}%
      </span>
    </div>
  );
};

export const StrategyAnalytics = ({ walletAddress }) => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30);

  const fetchAnalytics = useCallback(async () => {
    if (!walletAddress) return;
    try {
      setLoading(true);
      const res = await axios.get(`${API}/ai-trader/analytics/performance/${walletAddress}?days=${period}`);
      setAnalytics(res.data);
    } catch (err) {
      console.error("Analytics fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, [walletAddress, period]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!analytics) return null;

  const strategies = analytics.strategy_performance || {};
  const buckets = analytics.confidence_buckets || {};
  const frequency = analytics.trade_frequency || {};
  const sm = analytics.smart_money_signals || {};
  const sent = analytics.sentiment_signals || {};

  const totalTrades = analytics.total_positions || 0;
  const totalLogs = analytics.total_logs || 0;
  const totalJournal = analytics.total_journal_entries || 0;

  // Calculate overall stats
  let totalWins = 0, totalLosses = 0, totalPnl = 0;
  Object.values(strategies).forEach(s => {
    totalWins += s.wins;
    totalLosses += s.losses;
    totalPnl += s.total_pnl_sol;
  });
  const overallWinRate = (totalWins + totalLosses) > 0 ? ((totalWins / (totalWins + totalLosses)) * 100).toFixed(1) : "—";

  const sortedDays = Object.keys(frequency).sort();
  const maxDayTrades = Math.max(...Object.values(frequency), 1);

  return (
    <div data-testid="strategy-analytics" className="space-y-6">
      {/* Period selector */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-400" />
          Strategy Performance
        </h3>
        <div className="flex gap-1">
          {[7, 14, 30, 90].map(d => (
            <button
              key={d}
              data-testid={`period-${d}d`}
              onClick={() => setPeriod(d)}
              className={`px-3 py-1 text-xs rounded-md transition-all ${
                period === d ? 'bg-purple-600 text-white' : 'bg-[#1a1a2e] text-gray-400 hover:text-white'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Overview metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Total Trades" value={totalTrades} sub={`${totalLogs} signals processed`} icon={<Activity className="w-4 h-4" />} />
        <MetricCard label="Win Rate" value={`${overallWinRate}%`} sub={`${totalWins}W / ${totalLosses}L`} icon={<Target className="w-4 h-4" />} color={parseFloat(overallWinRate) >= 50 ? "#00FFA3" : "#FF6B6B"} />
        <MetricCard label="Net PnL" value={`${totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(4)} SOL`} icon={<TrendingUp className="w-4 h-4" />} color={totalPnl >= 0 ? "#00FFA3" : "#FF6B6B"} />
        <MetricCard label="Journal Entries" value={totalJournal} sub={`${sm.data_points || 0} SM signals`} icon={<Brain className="w-4 h-4" />} color="#A78BFA" />
      </div>

      {/* Strategy breakdown */}
      <div className="bg-[#12121e] border border-[#2a2a4a] rounded-xl p-4">
        <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-yellow-400" /> Strategy Breakdown
        </h4>
        {Object.keys(strategies).length > 0 ? (
          Object.entries(strategies)
            .sort((a, b) => b[1].trades - a[1].trades)
            .map(([name, stats]) => <StrategyRow key={name} name={name} stats={stats} />)
        ) : (
          <p className="text-sm text-gray-500 text-center py-4">No strategy data yet — trades need to close for PnL analysis</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Confidence vs Outcome */}
        <div className="bg-[#12121e] border border-[#2a2a4a] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Confidence vs Win Rate</h4>
          {Object.entries(buckets).map(([range, data]) => (
            <ConfidenceBucket key={range} range={range} data={data} />
          ))}
          <p className="text-[10px] text-gray-600 mt-2">Higher confidence should correlate with higher win rates</p>
        </div>

        {/* Smart Money & Sentiment */}
        <div className="bg-[#12121e] border border-[#2a2a4a] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Signal Intelligence</h4>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b border-[#2a2a4a]/50">
              <span className="text-xs text-gray-400">Smart Money Signals</span>
              <span className="text-sm font-mono text-white">{sm.data_points || 0} data points</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-[#2a2a4a]/50">
              <span className="text-xs text-gray-400">Avg SM Adjustment</span>
              <span className={`text-sm font-mono ${(sm.avg_adjustment || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {(sm.avg_adjustment || 0) >= 0 ? '+' : ''}{sm.avg_adjustment || 0}%
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-[#2a2a4a]/50">
              <span className="text-xs text-gray-400">Sentiment Signals</span>
              <span className="text-sm font-mono text-white">{sent.data_points || 0} data points</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-xs text-gray-400">Avg Sentiment Adjustment</span>
              <span className={`text-sm font-mono ${(sent.avg_adjustment || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {(sent.avg_adjustment || 0) >= 0 ? '+' : ''}{sent.avg_adjustment || 0}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Trade frequency timeline */}
      {sortedDays.length > 0 && (
        <div className="bg-[#12121e] border border-[#2a2a4a] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Trade Frequency (Daily)</h4>
          <div className="flex items-end gap-1 h-20">
            {sortedDays.map(day => (
              <div key={day} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-purple-500/60 rounded-t-sm min-h-[2px]"
                  style={{ height: `${(frequency[day] / maxDayTrades) * 100}%` }}
                  title={`${day}: ${frequency[day]} trades`}
                />
                <span className="text-[8px] text-gray-600 -rotate-45 origin-top-left whitespace-nowrap">
                  {day.slice(5)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
