import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import {
  Activity, Zap, Flame, Target, TrendingUp, AlertTriangle,
  RefreshCw, Crosshair, Bot, Fuel, Clock, ChevronDown, ChevronUp
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BotHealthDashboard({ adminWallet }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedScan, setExpandedScan] = useState(null);

  const fetch = useCallback(async () => {
    if (!adminWallet) return;
    setLoading(true);
    try {
      const { data: d } = await axios.get(`${API}/admin/bot-health?admin_wallet=${adminWallet}`);
      setData(d);
    } catch (e) {
      toast.error("Failed to load bot health data");
    }
    setLoading(false);
  }, [adminWallet]);

  useEffect(() => { fetch(); }, [fetch]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-16" data-testid="bot-health-loading">
        <RefreshCw className="w-6 h-6 text-slate-500 animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-16">
        <Bot className="w-10 h-10 mx-auto mb-3 text-slate-600" />
        <p className="text-slate-400 text-sm">No bot health data available</p>
        <Button onClick={fetch} variant="outline" size="sm" className="mt-4 border-white/20">
          <RefreshCw className="w-4 h-4 mr-2" /> Load Data
        </Button>
      </div>
    );
  }

  const f = data.funding;
  const a = data.activity;

  return (
    <div className="space-y-6" data-testid="bot-health-dashboard">
      {/* Funding Alert Banner */}
      <FundingBanner status={f.overall_status} available={f.total_available_sol} onChain={f.total_on_chain_sol} onRefresh={fetch} loading={loading} />

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MiniStat icon={<Fuel />} label="On-Chain" value={`${f.total_on_chain_sol.toFixed(4)}`} unit="SOL" color="#00C2FF" />
        <MiniStat icon={<Zap />} label="Available" value={`${f.total_available_sol.toFixed(4)}`} unit="SOL" color={f.overall_status === "ok" ? "#00FFA3" : f.overall_status === "low" ? "#FFB800" : "#EF4444"} />
        <MiniStat icon={<TrendingUp />} label="Today Buys" value={a.today_buys} color="#00FFA3" />
        <MiniStat icon={<Activity />} label="Today Exits" value={a.today_exits} color="#D946EF" />
        <MiniStat icon={<Target />} label="7d Buys" value={a.week_buys} color="#00C2FF" />
        <MiniStat icon={<Crosshair />} label="Open Positions" value={data.open_positions?.length || 0} color="#FFB800" />
      </div>

      {/* Bot Configurations */}
      {data.bot_configs?.length > 0 && (
        <div className="glass-card rounded-xl p-4">
          <h4 className="text-sm font-bold text-slate-300 mb-3 flex items-center gap-2">
            <Bot className="w-4 h-4 text-[#00C2FF]" /> Bot Configurations
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="bot-configs-table">
              <thead>
                <tr className="text-[10px] text-slate-500 uppercase border-b border-white/10">
                  <th className="text-left p-2">Wallet</th>
                  <th className="text-center p-2">Enabled</th>
                  <th className="text-center p-2">Mode</th>
                  <th className="text-center p-2">Min Conf</th>
                  <th className="text-center p-2">Max Pos</th>
                  <th className="text-center p-2">Daily Limit</th>
                  <th className="text-center p-2">Cooldown</th>
                  <th className="text-center p-2">SL / TP</th>
                </tr>
              </thead>
              <tbody>
                {data.bot_configs.map((c, i) => (
                  <tr key={i} className="border-b border-white/5">
                    <td className="p-2 text-xs font-mono text-slate-300">{c.wallet}</td>
                    <td className="p-2 text-center">
                      <Badge className={`text-[9px] ${c.enabled ? "bg-[#00FFA3]/10 text-[#00FFA3]" : "bg-red-500/10 text-red-400"}`}>
                        {c.enabled ? "ON" : "OFF"}
                      </Badge>
                    </td>
                    <td className="p-2 text-center">
                      <Badge className="text-[9px] bg-[#00C2FF]/10 text-[#00C2FF]">{c.mode}</Badge>
                    </td>
                    <td className="p-2 text-xs text-center text-slate-300">{(c.min_conf * 100).toFixed(0)}%</td>
                    <td className="p-2 text-xs text-center text-[#FFB800]">{c.max_pos} SOL</td>
                    <td className="p-2 text-xs text-center text-slate-300">{c.max_daily}</td>
                    <td className="p-2 text-xs text-center text-slate-400">{c.cooldown}m</td>
                    <td className="p-2 text-xs text-center">
                      <span className="text-red-400">{c.stop_loss}%</span>
                      <span className="text-slate-600 mx-1">/</span>
                      <span className="text-[#00FFA3]">{c.take_profit}%</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Open Positions */}
      {data.open_positions?.length > 0 && (
        <div className="glass-card rounded-xl p-4">
          <h4 className="text-sm font-bold text-slate-300 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#FFB800]" /> Open Positions ({data.open_positions.length})
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="open-positions-table">
              <thead>
                <tr className="text-[10px] text-slate-500 uppercase border-b border-white/10">
                  <th className="text-left p-2">Token</th>
                  <th className="text-right p-2">Amount</th>
                  <th className="text-right p-2">Entry $</th>
                  <th className="text-center p-2">Confidence</th>
                  <th className="text-center p-2">Strategy</th>
                  <th className="text-center p-2">Type</th>
                  <th className="text-left p-2">Opened</th>
                </tr>
              </thead>
              <tbody>
                {data.open_positions.map((p, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="p-2 text-sm font-bold text-white">{p.token_symbol}</td>
                    <td className="p-2 text-xs text-right font-mono text-[#00FFA3]">{p.amount_sol?.toFixed(4)} SOL</td>
                    <td className="p-2 text-xs text-right font-mono text-slate-300">${p.entry_price?.toFixed(6)}</td>
                    <td className="p-2 text-xs text-center">
                      <ConfidencePill value={p.confidence} />
                    </td>
                    <td className="p-2 text-xs text-center text-slate-400">{p.strategy || "—"}</td>
                    <td className="p-2 text-center">
                      {p.is_snipe ? <Badge className="text-[9px] bg-[#D946EF]/10 text-[#D946EF]">SNIPE</Badge> :
                       p.is_runner ? <Badge className="text-[9px] bg-[#FFB800]/10 text-[#FFB800]">RUNNER</Badge> :
                       <Badge className="text-[9px] bg-slate-500/10 text-slate-400">SIGNAL</Badge>}
                    </td>
                    <td className="p-2 text-[10px] text-slate-500">{timeAgo(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent Trade Log */}
      <div className="glass-card rounded-xl p-4">
        <h4 className="text-sm font-bold text-slate-300 mb-3 flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#00FFA3]" /> Recent Auto-Trade Activity
        </h4>
        {data.recent_scans?.length > 0 ? (
          <div className="space-y-1 max-h-[360px] overflow-y-auto" data-testid="recent-scans-list">
            {data.recent_scans.map((s, i) => (
              <div key={i} className="group">
                <div
                  className="flex items-center justify-between p-2 rounded hover:bg-white/[0.03] cursor-pointer"
                  onClick={() => setExpandedScan(expandedScan === i ? null : i)}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${s.success ? "bg-[#00FFA3]" : "bg-red-400"}`} />
                    <span className="text-xs font-mono text-slate-300">{s.token_symbol || "?"}</span>
                    <Badge className={`text-[9px] ${
                      s.action === "auto_buy" ? "bg-[#00FFA3]/10 text-[#00FFA3]" :
                      s.action === "auto_buy_runner" ? "bg-[#FFB800]/10 text-[#FFB800]" :
                      s.action === "sniper_buy" ? "bg-[#D946EF]/10 text-[#D946EF]" :
                      "bg-slate-500/10 text-slate-400"
                    }`}>{s.action?.replace("auto_", "").replace("_", " ")}</Badge>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-[#00C2FF] font-mono">{s.amount_sol?.toFixed(4)} SOL</span>
                    <span className="text-[10px] text-slate-500">{timeAgo(s.created_at)}</span>
                    {expandedScan === i ? <ChevronUp className="w-3 h-3 text-slate-600" /> : <ChevronDown className="w-3 h-3 text-slate-600" />}
                  </div>
                </div>
                {expandedScan === i && (
                  <div className="px-4 pb-3 text-[10px] text-slate-400 space-y-1 border-l-2 border-white/5 ml-3">
                    {s.confidence != null && <p>Confidence: <span className="text-white">{(s.confidence * 100).toFixed(0)}%</span></p>}
                    {s.reason && <p>Reason: <span className="text-slate-300">{s.reason}</span></p>}
                    {s.entry_price != null && <p>Entry: <span className="text-white">${s.entry_price?.toFixed(6)}</span></p>}
                    {s.tx_signature && <p>TX: <a href={`https://solscan.io/tx/${s.tx_signature}`} target="_blank" rel="noreferrer" className="text-[#00C2FF] underline">{s.tx_signature.slice(0, 16)}...</a></p>}
                    {s.execution_error && <p className="text-red-400">Error: {s.execution_error}</p>}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-xs text-slate-500 py-6">No trade activity recorded yet</p>
        )}
      </div>

      {/* Sniper History */}
      <div className="glass-card rounded-xl p-4">
        <h4 className="text-sm font-bold text-slate-300 mb-3 flex items-center gap-2">
          <Crosshair className="w-4 h-4 text-[#D946EF]" /> Sniper Scan History
        </h4>
        {data.sniper_history?.length > 0 ? (
          <div className="overflow-x-auto" data-testid="sniper-history-table">
            <table className="w-full">
              <thead>
                <tr className="text-[10px] text-slate-500 uppercase border-b border-white/10">
                  <th className="text-left p-2">Token</th>
                  <th className="text-left p-2">Mint</th>
                  <th className="text-center p-2">Confidence</th>
                  <th className="text-left p-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {data.sniper_history.map((s, i) => (
                  <tr key={i} className="border-b border-white/5">
                    <td className="p-2 text-xs font-bold text-[#D946EF]">{s.token_symbol}</td>
                    <td className="p-2 text-[10px] font-mono text-slate-500">{s.token_mint?.slice(0, 12)}...</td>
                    <td className="p-2 text-center"><ConfidencePill value={s.confidence} /></td>
                    <td className="p-2 text-[10px] text-slate-500">{timeAgo(s.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-center text-xs text-slate-500 py-6">No sniper targets recorded yet. Sniper mode scans every 5 minutes.</p>
        )}
      </div>

      {/* PugBurn Reclaim Logs */}
      <div className="glass-card rounded-xl p-4">
        <h4 className="text-sm font-bold text-slate-300 mb-3 flex items-center gap-2">
          <Flame className="w-4 h-4 text-orange-400" /> PugBurn Auto-Reclaim Log
        </h4>
        {data.burn_logs?.length > 0 ? (
          <div className="space-y-2" data-testid="burn-logs-list">
            {data.burn_logs.map((b, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-white/[0.02]">
                <div className="flex items-center gap-2">
                  <Flame className="w-3 h-3 text-orange-400" />
                  <span className="text-xs text-slate-300">{b.reason || "Account cleanup"}</span>
                </div>
                <span className="text-[10px] text-slate-500">{timeAgo(b.created_at)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-xs text-slate-500 py-6">
            No auto-burn events yet. PugBurn triggers when SOL is low before trades.
          </p>
        )}
      </div>

      {/* Last check */}
      {data.checked_at && (
        <p className="text-[10px] text-slate-600 text-right">
          Last checked: {new Date(data.checked_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}

function FundingBanner({ status, available, onChain, onRefresh, loading }) {
  const config = {
    ok: { bg: "bg-[#00FFA3]/5", border: "border-[#00FFA3]/20", icon: <Fuel className="w-7 h-7 text-[#00FFA3]" />, title: "Bot Funded", desc: "Sufficient SOL for trading" },
    low: { bg: "bg-[#FFB800]/5", border: "border-[#FFB800]/20", icon: <AlertTriangle className="w-7 h-7 text-[#FFB800]" />, title: "Low Funds", desc: "Bot may skip trades due to insufficient SOL" },
    critical: { bg: "bg-red-500/5", border: "border-red-500/30", icon: <AlertTriangle className="w-7 h-7 text-red-400" />, title: "Critically Low", desc: "Bot cannot trade — deposit SOL to custodial wallet" },
  };
  const c = config[status] || config.ok;

  return (
    <div className={`rounded-xl p-5 border ${c.bg} ${c.border}`} data-testid="funding-banner">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {c.icon}
          <div>
            <h3 className="text-lg font-bold" style={{ fontFamily: "Orbitron" }}>{c.title}</h3>
            <p className="text-xs text-slate-400">
              {c.desc} — Available: <span className="text-white font-mono">{available.toFixed(4)} SOL</span> | On-chain: <span className="text-white font-mono">{onChain.toFixed(4)} SOL</span>
            </p>
          </div>
        </div>
        <Button onClick={onRefresh} variant="outline" size="sm" className="border-white/20" disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>
    </div>
  );
}

function MiniStat({ icon, label, value, unit, color }) {
  return (
    <div className="glass-card rounded-xl p-3 text-center">
      <div className="w-6 h-6 mx-auto mb-1 rounded-full flex items-center justify-center" style={{ backgroundColor: `${color}12` }}>
        <span style={{ color }} className="[&>svg]:w-3 [&>svg]:h-3">{icon}</span>
      </div>
      <p className="text-lg font-black" style={{ color, fontFamily: "Orbitron" }}>
        {value}
      </p>
      {unit && <p className="text-[9px] text-slate-500">{unit}</p>}
      <p className="text-[9px] text-slate-600 uppercase">{label}</p>
    </div>
  );
}

function ConfidencePill({ value }) {
  if (value == null) return <span className="text-[10px] text-slate-600">—</span>;
  const pct = (value * 100).toFixed(0);
  const color = value >= 0.7 ? "text-[#00FFA3] bg-[#00FFA3]/10" : value >= 0.5 ? "text-[#FFB800] bg-[#FFB800]/10" : "text-red-400 bg-red-500/10";
  return <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${color}`}>{pct}%</span>;
}

function timeAgo(dateStr) {
  if (!dateStr) return "—";
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
