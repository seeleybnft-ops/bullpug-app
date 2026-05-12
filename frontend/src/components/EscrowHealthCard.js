import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Wallet, RefreshCw, TrendingUp, AlertTriangle, CheckCircle2, Coins } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_STYLE = {
  healthy:  { color: "#00FFA3", bg: "rgba(0,255,163,0.08)",  border: "rgba(0,255,163,0.30)",  label: "Healthy",  icon: CheckCircle2 },
  ok:       { color: "#F5D300", bg: "rgba(245,211,0,0.08)",  border: "rgba(245,211,0,0.30)",  label: "OK",       icon: TrendingUp },
  low:      { color: "#FB923C", bg: "rgba(251,146,60,0.08)", border: "rgba(251,146,60,0.30)", label: "Low",      icon: AlertTriangle },
  critical: { color: "#EF4444", bg: "rgba(239,68,68,0.10)",  border: "rgba(239,68,68,0.35)",  label: "Critical", icon: AlertTriangle },
  unknown:  { color: "#94A3B8", bg: "rgba(148,163,184,0.08)",border: "rgba(148,163,184,0.30)",label: "Unknown",  icon: AlertTriangle },
};

function fmtSol(v, digits = 4) {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

export default function EscrowHealthCard({ adminWallet }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = useCallback(async () => {
    if (!adminWallet) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.get(`${API}/admin/escrow-status`, {
        params: { admin_wallet: adminWallet },
      });
      setData(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not load escrow status");
    } finally {
      setLoading(false);
    }
  }, [adminWallet]);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 30000); // refresh every 30s
    return () => clearInterval(id);
  }, [fetchStatus]);

  const status = data?.headroom?.status || "unknown";
  const style = STATUS_STYLE[status] || STATUS_STYLE.unknown;
  const StatusIcon = style.icon;
  const target = data?.headroom?.target_sol ?? 0.5;
  const headroomPct = data?.free_capital_sol != null
    ? Math.min(100, Math.max(0, (data.free_capital_sol / target) * 100))
    : 0;

  return (
    <div
      data-testid="escrow-health-card"
      className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] p-5 mb-6 relative overflow-hidden"
    >
      {/* Top accent bar — colored by status */}
      <div className="absolute top-0 inset-x-0 h-1" style={{ background: `linear-gradient(90deg, ${style.color}, transparent)` }} />

      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0" style={{ background: style.bg, border: `1px solid ${style.border}` }}>
            <Wallet className="w-5 h-5" style={{ color: style.color }} />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-[0.25em] font-bold mb-0.5" style={{ color: style.color }}>
              Escrow · P2P Arena
            </p>
            <h3
              className="text-base md:text-lg font-bold text-white tracking-tight"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              Capital Health
            </h3>
            <p className="text-[11px] text-slate-500 font-mono mt-0.5 break-all">
              {data?.escrow_wallet || "—"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider"
            style={{ background: style.bg, color: style.color, border: `1px solid ${style.border}` }}
            data-testid="escrow-health-status"
          >
            <StatusIcon className="w-3 h-3" />
            {style.label}
          </span>
          <button
            type="button"
            onClick={fetchStatus}
            disabled={loading}
            data-testid="escrow-health-refresh"
            className="w-8 h-8 rounded-full bg-white/5 border border-white/10 hover:border-white/40 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
            aria-label="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="text-[11px] text-red-400 mb-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30">
          {error}
        </div>
      )}

      {/* Headroom progress */}
      <div className="mb-4">
        <div className="flex items-baseline justify-between mb-1.5">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Free Capital · Headroom</span>
          <span className="text-[10px] text-slate-500">target {fmtSol(target, 2)} SOL</span>
        </div>
        <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
          <div
            data-testid="escrow-headroom-bar"
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${headroomPct}%`, background: style.color }}
          />
        </div>
        <div className="flex items-baseline justify-between mt-2">
          <p className="text-2xl font-black leading-none tracking-tight" style={{ fontFamily: "Orbitron, sans-serif" }}>
            <span style={{ color: style.color }}>{fmtSol(data?.free_capital_sol, 4)}</span>
            <span className="text-sm text-slate-500 ml-1">SOL</span>
          </p>
          <p className="text-[10px] text-slate-500">
            on-chain {fmtSol(data?.balance_sol, 4)} SOL
          </p>
        </div>
      </div>

      {/* Stat grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        <Stat label="On-chain" value={fmtSol(data?.balance_sol)} testid="escrow-balance" />
        <Stat label="Pending out" value={fmtSol(data?.pending_obligations_sol)} testid="escrow-pending" />
        <Stat label="Jackpot owed" value={fmtSol(data?.jackpot_owed_sol)} testid="escrow-jackpot-owed" color="#F5D300" />
        <Stat label="Tx fee" value={fmtSol(data?.tx_fee_sol, 6)} testid="escrow-tx-fee" />
      </div>

      {/* 7-day rake breakdown */}
      <div className="rounded-xl border border-white/10 bg-black/30 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Coins className="w-3 h-3 text-[#00FFA3]" />
          <span className="text-[9px] uppercase tracking-wider font-bold text-slate-400">Last 7 Days · Rake Flow</span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <Stat label="Total rake" value={fmtSol(data?.rake_last_7d?.total_sol, 6)} testid="rake-7d-total" />
          <Stat label="Operator (75%)" value={fmtSol(data?.rake_last_7d?.operator_share_sol, 6)} testid="rake-7d-operator" color="#00FFA3" />
          <Stat label="Jackpot (25%)" value={fmtSol(data?.rake_last_7d?.jackpot_share_sol, 6)} testid="rake-7d-jackpot" color="#F5D300" />
        </div>
        <p className="text-[10px] text-slate-500 mt-2 italic">
          All on-chain transfer fees are absorbed by the 25% jackpot share — operator capital is untouched.
        </p>
      </div>

      {status === "low" || status === "critical" ? (
        <div
          className="mt-3 px-3 py-2 rounded-xl border text-[11px] flex items-start gap-2"
          style={{ background: style.bg, borderColor: style.border, color: style.color }}
        >
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>
            Free capital is below {status === "critical" ? "0.01" : "0.1"} SOL.
            Recommended top-up: <strong>{fmtSol(target - (data?.free_capital_sol || 0), 4)} SOL</strong>{" "}
            to reach the {fmtSol(target, 2)} SOL operating buffer.
          </span>
        </div>
      ) : null}
    </div>
  );
}

function Stat({ label, value, color = "#FFFFFF", testid }) {
  return (
    <div className="px-2.5 py-2 rounded-lg bg-white/[0.03] border border-white/5" data-testid={testid}>
      <p className="text-[9px] uppercase tracking-wider text-slate-500 font-bold mb-0.5">{label}</p>
      <p className="text-sm font-bold leading-none" style={{ fontFamily: "Orbitron, sans-serif", color }}>
        {value}
      </p>
    </div>
  );
}
