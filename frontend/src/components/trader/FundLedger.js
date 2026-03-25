import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Wallet, ArrowUpRight, ArrowDownRight, Lock, RefreshCw, History, ChevronDown, ChevronUp } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TYPE_STYLES = {
  deposit: { color: "#00FFA3", label: "Deposit", icon: <ArrowDownRight className="w-3 h-3" /> },
  withdrawal: { color: "#FF4444", label: "Withdrawal", icon: <ArrowUpRight className="w-3 h-3" /> },
  trade_open: { color: "#FFB800", label: "Trade Open", icon: <Lock className="w-3 h-3" /> },
  trade_close: { color: "#00C2FF", label: "Trade Close", icon: <ArrowDownRight className="w-3 h-3" /> },
  fee: { color: "#FF4444", label: "Fee", icon: <ArrowUpRight className="w-3 h-3" /> },
  adjustment: { color: "#D946EF", label: "Adjustment", icon: <RefreshCw className="w-3 h-3" /> },
};

function BalanceStat({ label, value, color, suffix = "SOL" }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="text-sm font-mono font-semibold" style={{ color }}>
        {value >= 0 ? "" : ""}{value.toFixed(6)} <span className="text-[10px] text-slate-500">{suffix}</span>
      </span>
    </div>
  );
}

export default function FundLedger({ walletAddress }) {
  const [balance, setBalance] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    if (!walletAddress) return;
    try {
      const [balRes, histRes] = await Promise.all([
        axios.get(`${API}/ledger/balance/${walletAddress}`),
        axios.get(`${API}/ledger/history/${walletAddress}?limit=20`),
      ]);
      setBalance(balRes.data);
      setHistory(histRes.data?.entries || []);
    } catch (e) {
      console.warn("Ledger fetch failed:", e);
    }
    setLoading(false);
  }, [walletAddress]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (!walletAddress) return null;

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm overflow-hidden" data-testid="fund-ledger">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#00FFA3]/10 flex items-center justify-center">
            <Wallet className="w-3.5 h-3.5 text-[#00FFA3]" />
          </div>
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300" style={{ fontFamily: "Orbitron, sans-serif" }}>
            Fund Ledger
          </span>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="w-6 h-6 rounded-full border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/30 transition-colors"
          data-testid="ledger-refresh-btn"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="px-5 py-4 space-y-1">
        {loading ? (
          <div className="h-20 flex items-center justify-center">
            <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
          </div>
        ) : balance ? (
          <>
            <div className="text-center py-3 mb-2">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Total Balance</p>
              <p className="text-2xl font-bold font-mono" style={{ color: balance.total_balance_sol >= 0 ? "#00FFA3" : "#FF4444" }} data-testid="ledger-total-balance">
                {balance.total_balance_sol.toFixed(6)} <span className="text-sm text-slate-500">SOL</span>
              </p>
            </div>
            <BalanceStat label="Available" value={balance.available_sol} color="#00FFA3" />
            <BalanceStat label="Locked in Trades" value={balance.locked_in_trades_sol} color="#FFB800" />
            <BalanceStat label="Total Deposited" value={balance.total_deposited_sol} color="#00C2FF" />
            <BalanceStat label="Total Withdrawn" value={balance.total_withdrawn_sol} color="#FF4444" />
            <BalanceStat label="Realised P&L" value={balance.realised_pnl_sol} color={balance.realised_pnl_sol >= 0 ? "#00FFA3" : "#FF4444"} />
          </>
        ) : (
          <p className="text-center text-xs text-slate-500 py-4">No ledger data yet</p>
        )}
      </div>

      {/* Transaction History Toggle */}
      <button
        onClick={() => setShowHistory(p => !p)}
        className="w-full flex items-center justify-between px-5 py-3 border-t border-white/[0.06] text-xs text-slate-400 hover:text-slate-200 transition-colors"
        data-testid="ledger-history-toggle"
      >
        <span className="flex items-center gap-1.5">
          <History className="w-3 h-3" />
          Transaction History ({history.length})
        </span>
        {showHistory ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>

      {showHistory && (
        <div className="px-5 pb-4 max-h-64 overflow-y-auto" data-testid="ledger-history-list">
          {history.length > 0 ? (
            <div className="space-y-2">
              {history.map(entry => {
                const style = TYPE_STYLES[entry.entry_type] || TYPE_STYLES.adjustment;
                return (
                  <div key={entry.entry_id} className="flex items-start gap-3 py-2 border-b border-white/[0.03] last:border-0">
                    <div className="w-5 h-5 rounded-full flex items-center justify-center mt-0.5" style={{ background: `${style.color}15`, color: style.color }}>
                      {style.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: style.color }}>{style.label}</span>
                        <span className="text-xs font-mono font-semibold" style={{ color: entry.amount_sol >= 0 ? "#00FFA3" : "#FF4444" }}>
                          {entry.amount_sol >= 0 ? "+" : ""}{entry.amount_sol.toFixed(6)}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 truncate mt-0.5">{entry.description}</p>
                      <p className="text-[9px] text-slate-600 mt-0.5">
                        {new Date(entry.created_at).toLocaleString()} · bal: {entry.balance_after.toFixed(6)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-center text-[10px] text-slate-500 py-3">No transactions yet</p>
          )}
        </div>
      )}
    </div>
  );
}
