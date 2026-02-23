/**
 * Dashboard Component - Trading statistics and analytics
 * Extracted from TradingJournal for better maintainability
 */

import { DollarSign, Target, BarChart3, TrendingUp, TrendingDown, Activity, Award, AlertTriangle, Hash, Brain } from "lucide-react";
import { BookOpen } from "lucide-react";
import { LineChart, Line as RechartsLine, BarChart, Bar as RechartsBar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

function SummaryCard({ icon, label, value, color }) {
  return (
    <div className="glass-card rounded-xl p-4 text-center" data-testid={`summary-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="w-8 h-8 mx-auto mb-2 rounded-full flex items-center justify-center" style={{ backgroundColor: `${color}15` }}>
        <span style={{ color }}>{icon}</span>
      </div>
      <p className="text-lg font-black" style={{ color, fontFamily: 'Orbitron' }}>{value}</p>
      <p className="text-[10px] text-slate-500 uppercase">{label}</p>
    </div>
  );
}

export default function Dashboard({ dashboard, trades, loading, formatCurrency, walletAddress }) {
  if (loading) {
    return (
      <div className="glass-card rounded-2xl p-16 text-center" data-testid="dashboard-loading">
        <Activity className="w-10 h-10 mx-auto mb-3 text-slate-600 animate-pulse" />
        <p className="text-slate-500">Loading dashboard...</p>
      </div>
    );
  }

  if (!dashboard || dashboard.total_trades === 0) {
    return (
      <div className="glass-card rounded-2xl p-16 text-center" data-testid="dashboard-empty">
        <BookOpen className="w-14 h-14 mx-auto mb-4 text-slate-700" />
        <p className="text-slate-500 text-sm mb-2">No trades logged yet</p>
        <p className="text-slate-600 text-xs">Start logging your trades to see analytics</p>
      </div>
    );
  }

  const pnlData = trades
    .filter(t => t.status === "closed")
    .sort((a, b) => new Date(a.date_entry) - new Date(b.date_entry))
    .reduce((acc, t, i) => {
      const cumPnl = (acc[i - 1]?.cumPnl || 0) + (t.pnl || 0);
      acc.push({ name: t.trade_id, pnl: t.pnl, cumPnl, asset: t.asset });
      return acc;
    }, []);

  const assetData = Object.entries(dashboard.pnl_by_asset || {}).map(([asset, pnl]) => ({
    name: asset, value: Math.abs(pnl), pnl, fill: pnl >= 0 ? "#00FFA3" : "#FF3B30"
  }));

  return (
    <div className="space-y-6" data-testid="dashboard">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <SummaryCard icon={<DollarSign />} label="Total P&L" value={formatCurrency(dashboard.total_pnl)} color={dashboard.total_pnl >= 0 ? "#00FFA3" : "#FF3B30"} />
        <SummaryCard icon={<Target />} label="Win Rate" value={`${dashboard.win_rate}%`} color="#00C2FF" />
        <SummaryCard icon={<BarChart3 />} label="Total Trades" value={dashboard.total_trades} color="#D946EF" />
        <SummaryCard icon={<TrendingUp />} label="Wins" value={dashboard.total_wins} color="#00FFA3" />
        <SummaryCard icon={<TrendingDown />} label="Losses" value={dashboard.total_losses} color="#FF3B30" />
        <SummaryCard icon={<Activity />} label="Avg P&L" value={formatCurrency(dashboard.avg_pnl)} color={dashboard.avg_pnl >= 0 ? "#00FFA3" : "#FF3B30"} />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase text-[#00FFA3] mb-3 flex items-center gap-2">
            <Award size={14} /> Best Trade
          </h4>
          {dashboard.biggest_win ? (
            <div>
              <p className="text-2xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron' }}>
                +${dashboard.biggest_win.pnl?.toLocaleString()}
              </p>
              <p className="text-xs text-slate-400">{dashboard.biggest_win.asset} - {dashboard.biggest_win.trade_id}</p>
            </div>
          ) : <p className="text-slate-500 text-sm">No winning trades yet</p>}
        </div>
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase text-red-400 mb-3 flex items-center gap-2">
            <AlertTriangle size={14} /> Worst Trade
          </h4>
          {dashboard.biggest_loss ? (
            <div>
              <p className="text-2xl font-black text-red-400" style={{ fontFamily: 'Orbitron' }}>
                -${Math.abs(dashboard.biggest_loss.pnl)?.toLocaleString()}
              </p>
              <p className="text-xs text-slate-400">{dashboard.biggest_loss.asset} - {dashboard.biggest_loss.trade_id}</p>
            </div>
          ) : <p className="text-slate-500 text-sm">No losing trades yet</p>}
        </div>
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase text-[#D946EF] mb-3 flex items-center gap-2">
            <Hash size={14} /> Most Traded
          </h4>
          {dashboard.most_traded_asset ? (
            <div>
              <p className="text-2xl font-black text-[#D946EF]" style={{ fontFamily: 'Orbitron' }}>
                {dashboard.most_traded_asset.asset}
              </p>
              <p className="text-xs text-slate-400">{dashboard.most_traded_asset.count} trades</p>
            </div>
          ) : <p className="text-slate-500 text-sm">No trades yet</p>}
        </div>
      </div>

      {/* Streaks & Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Win Streak</p>
          <p className="text-xl font-black text-[#00FFA3]">{dashboard.win_streak}</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Loss Streak</p>
          <p className="text-xl font-black text-red-400">{dashboard.loss_streak}</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Avg R:R</p>
          <p className="text-xl font-black text-[#00C2FF]">{dashboard.avg_rr}:1</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Sharpe Ratio</p>
          <p className="text-xl font-black text-[#F5D300]">{dashboard.sharpe_ratio}</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {pnlData.length > 0 && (
          <div className="glass-card rounded-2xl p-5">
            <h4 className="text-sm font-bold uppercase mb-4" style={{ fontFamily: 'Orbitron' }}>Cumulative P&L</h4>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={pnlData}>
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 9, fill: '#64748b' }} />
                <Tooltip contentStyle={{ backgroundColor: '#13131F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                <RechartsLine type="monotone" dataKey="cumPnl" stroke="#00FFA3" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
        {assetData.length > 0 && (
          <div className="glass-card rounded-2xl p-5">
            <h4 className="text-sm font-bold uppercase mb-4" style={{ fontFamily: 'Orbitron' }}>P&L by Asset</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={assetData}>
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 9, fill: '#64748b' }} />
                <Tooltip contentStyle={{ backgroundColor: '#13131F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                <RechartsBar dataKey="pnl" radius={[4, 4, 0, 0]}>
                  {assetData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </RechartsBar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Recent Emotions */}
      {dashboard.recent_emotions?.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase text-[#D946EF] mb-3 flex items-center gap-2">
            <Brain size={14} /> Recent Mindset
          </h4>
          <div className="flex flex-wrap gap-2">
            {dashboard.recent_emotions.map((e, i) => (
              <div key={i} className="text-[10px] px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
                <span className="text-slate-400">{e.asset}:</span>{" "}
                <span className="text-[#00FFA3]">{e.entry || "?"}</span>
                <span className="text-slate-600"> → </span>
                <span className="text-[#D946EF]">{e.exit || "?"}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
