import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight,
  ExternalLink, Clock, Shield, BarChart3, RefreshCw, Wallet
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function formatTime(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function TradeRow({ trade }) {
  const isBuy = trade.trade_type === "buy";
  const hasPnl = trade.pnl_sol !== undefined && trade.pnl_sol !== null;
  const pnlPositive = (trade.pnl_sol || 0) > 0;
  const solscanUrl = trade.tx_signature
    ? `https://solscan.io/tx/${trade.tx_signature}`
    : null;

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-colors"
      data-testid={`trade-row-${trade.execution_id}`}
    >
      {/* Type icon */}
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
        style={{
          background: isBuy ? "rgba(0,255,163,0.08)" : "rgba(255,68,68,0.08)",
        }}
      >
        {isBuy ? (
          <ArrowDownRight className="w-4 h-4 text-[#00FFA3]" />
        ) : (
          <ArrowUpRight className="w-4 h-4 text-[#FF4444]" />
        )}
      </div>

      {/* Token + action */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-white">{trade.token_symbol}</span>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider"
            style={{
              background: isBuy ? "rgba(0,255,163,0.1)" : "rgba(255,68,68,0.1)",
              color: isBuy ? "#00FFA3" : "#FF4444",
            }}
          >
            {isBuy ? "BUY" : "SELL"}
          </span>
          {trade.status === "open" && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#FFB800]/10 text-[#FFB800] font-semibold">
              OPEN
            </span>
          )}
          {trade.source === "auto" && (
            <Shield className="w-3 h-3 text-slate-500" title="Auto-trade" />
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-[10px] text-slate-500">
            {isBuy ? "Entry" : "Exit"}: ${(isBuy ? trade.entry_price : trade.exit_price || trade.entry_price)?.toFixed(6) || "—"}
          </span>
          <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
            <Clock className="w-2.5 h-2.5" />
            {formatTime(trade.executed_at || trade.created_at)}
          </span>
        </div>
      </div>

      {/* Amount */}
      <div className="text-right shrink-0">
        <p className="text-xs font-mono font-semibold text-white">
          {trade.amount_sol?.toFixed(4)} SOL
        </p>
        {hasPnl && (
          <p
            className="text-[10px] font-mono font-semibold"
            style={{ color: pnlPositive ? "#00FFA3" : "#FF4444" }}
          >
            {pnlPositive ? "+" : ""}{trade.pnl_sol?.toFixed(6)} ({trade.pnl_percent >= 0 ? "+" : ""}{trade.pnl_percent?.toFixed(1)}%)
          </p>
        )}
      </div>

      {/* TX link */}
      {solscanUrl && (
        <a
          href={solscanUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="w-7 h-7 rounded-lg border border-white/[0.08] flex items-center justify-center text-slate-500 hover:text-[#00C2FF] hover:border-[#00C2FF]/30 transition-colors shrink-0"
          title="View on Solscan"
          data-testid={`trade-tx-link-${trade.execution_id}`}
        >
          <ExternalLink className="w-3 h-3" />
        </a>
      )}
    </div>
  );
}

export default function TradeHistoryDashboard({ walletAddress }) {
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    if (!walletAddress) return;
    setLoading(true);
    try {
      const [histRes, balRes] = await Promise.all([
        axios.get(`${API}/ai-trader/history/${walletAddress}?limit=50`).catch(() => null),
        axios.get(`${API}/ledger/balance/${walletAddress}`).catch(() => null),
      ]);
      if (histRes) {
        setTrades(histRes.data?.trades || []);
        setStats(histRes.data?.stats || null);
      }
      if (balRes) setBalance(balRes.data);
    } catch (_) {}
    setLoading(false);
  }, [walletAddress]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (!walletAddress) return null;

  const available = balance?.available_sol ?? 0;
  const locked = balance?.locked_in_trades_sol ?? 0;
  const totalBalance = balance?.total_balance_sol ?? 0;
  const fees = balance?.total_fees_sol ?? 0;
  const deposited = balance?.total_deposited_sol ?? 0;
  const unrealisedPnl = balance?.unrealised_pnl_sol ?? 0;
  const buyTrades = trades.filter(t => t.trade_type === "buy");
  const totalInvested = buyTrades.reduce((sum, t) => sum + (t.amount_sol || 0), 0);

  return (
    <div
      className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm overflow-hidden"
      data-testid="trade-history-dashboard"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#00C2FF]/10 flex items-center justify-center">
            <BarChart3 className="w-3.5 h-3.5 text-[#00C2FF]" />
          </div>
          <span
            className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Trade History
          </span>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="w-6 h-6 rounded-full border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/30 transition-colors"
          data-testid="trade-history-refresh"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Trading Balance Banner */}
      <div className="px-5 py-4 border-b border-white/[0.06] bg-gradient-to-r from-[#00FFA3]/[0.03] to-transparent">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div data-testid="available-for-trading">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5 flex items-center gap-1">
              <Wallet className="w-2.5 h-2.5" /> Available for Trading
            </p>
            <p className="text-lg font-bold font-mono text-[#00FFA3]">
              {available.toFixed(6)}
              <span className="text-xs text-slate-500 ml-1">SOL</span>
            </p>
          </div>
          <div data-testid="locked-in-trades">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">Locked in Trades</p>
            <p className="text-lg font-bold font-mono text-[#FFB800]">
              {locked.toFixed(6)}
              <span className="text-xs text-slate-500 ml-1">SOL</span>
            </p>
          </div>
          <div data-testid="total-fees-paid">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">Total Fees</p>
            <p className="text-lg font-bold font-mono text-[#D946EF]">
              {fees.toFixed(6)}
              <span className="text-xs text-slate-500 ml-1">SOL</span>
            </p>
          </div>
          <div data-testid="unrealised-pnl">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">Unrealised P&L</p>
            <p
              className="text-lg font-bold font-mono"
              style={{ color: unrealisedPnl >= 0 ? "#00FFA3" : "#FF4444" }}
            >
              {unrealisedPnl >= 0 ? "+" : ""}{unrealisedPnl.toFixed(6)}
              <span className="text-xs text-slate-500 ml-1">SOL</span>
            </p>
          </div>
        </div>

        {/* Account Summary Bar */}
        <div className="mt-3 flex items-center gap-4 text-[10px]">
          <span className="text-slate-500">
            Deposited: <span className="text-[#00C2FF] font-mono">{deposited.toFixed(4)}</span>
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-500">
            Net Worth: <span className="text-white font-mono font-semibold">{totalBalance.toFixed(4)} SOL</span>
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-500">
            Total Invested: <span className="text-[#FFB800] font-mono">{totalInvested.toFixed(4)}</span>
          </span>
        </div>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-4 gap-px bg-white/[0.04]">
          {[
            { label: "Total Trades", value: trades.length, color: "#00C2FF" },
            { label: "Win Rate", value: stats.win_rate ? `${(stats.win_rate * 100).toFixed(0)}%` : "—", color: stats.win_rate > 0.5 ? "#00FFA3" : "#FFB800" },
            { label: "Wins / Losses", value: `${stats.wins} / ${stats.losses}`, color: "#00FFA3" },
            { label: "Total P&L", value: `${stats.total_pnl_sol >= 0 ? "+" : ""}${stats.total_pnl_sol?.toFixed(4) || "0"} SOL`, color: (stats.total_pnl_sol || 0) >= 0 ? "#00FFA3" : "#FF4444" },
          ].map((s, i) => (
            <div key={i} className="bg-[#0a0a0f] px-4 py-2.5 text-center">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider">{s.label}</p>
              <p className="text-sm font-bold font-mono mt-0.5" style={{ color: s.color }}>
                {s.value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Trade List */}
      <div className="max-h-[400px] overflow-y-auto" data-testid="trade-list">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
          </div>
        ) : trades.length > 0 ? (
          trades.map(trade => <TradeRow key={trade.execution_id} trade={trade} />)
        ) : (
          <div className="py-12 text-center">
            <BarChart3 className="w-8 h-8 text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-500">No trades executed yet</p>
            <p className="text-xs text-slate-600 mt-1">
              The bot will automatically execute trades when it finds opportunities
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
