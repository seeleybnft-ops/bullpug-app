import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Wallet, ArrowUpRight, ArrowDownRight, Lock, RefreshCw, History, ChevronDown, ChevronUp, Copy, ArrowRight, X } from "lucide-react";
import { Button } from "../ui/button";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TYPE_STYLES = {
  deposit: { color: "#00FFA3", label: "Deposit", icon: <ArrowDownRight className="w-3 h-3" /> },
  withdrawal: { color: "#FF4444", label: "Withdrawal", icon: <ArrowUpRight className="w-3 h-3" /> },
  trade_open: { color: "#FFB800", label: "Trade Open", icon: <Lock className="w-3 h-3" /> },
  trade_close: { color: "#00C2FF", label: "Trade Close", icon: <ArrowDownRight className="w-3 h-3" /> },
  fee: { color: "#FF4444", label: "Fee", icon: <ArrowUpRight className="w-3 h-3" /> },
  adjustment: { color: "#D946EF", label: "Adjustment", icon: <RefreshCw className="w-3 h-3" /> },
};

function safeCopy(text) {
  const fallback = () => {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      toast.success("Address copied!");
    } catch {
      toast.error("Copy failed — please copy manually");
    }
  };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(
      () => toast.success("Address copied!"),
      () => fallback()
    );
  } else {
    fallback();
  }
}

function BalanceStat({ label, value, color }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="text-xs font-mono font-semibold" style={{ color }}>
        {value.toFixed(6)} <span className="text-[10px] text-slate-500">SOL</span>
      </span>
    </div>
  );
}

export default function FundLedger({ walletAddress, custodialWallet, onDeposit, onWithdraw }) {
  const [balance, setBalance] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [withdrawing, setWithdrawing] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    if (!walletAddress) return;
    try {
      // Auto-detect deposits on each refresh
      await axios.post(`${API}/custodial-wallet/detect-deposit/${walletAddress}`).catch(() => null);
      const [balRes, histRes] = await Promise.all([
        axios.get(`${API}/ledger/balance/${walletAddress}`).catch(() => null),
        axios.get(`${API}/ledger/history/${walletAddress}?limit=20`).catch(() => null),
      ]);
      if (balRes) setBalance(balRes.data);
      if (histRes) setHistory(histRes.data?.entries || []);
    } catch (_) {}
    setLoading(false);
  }, [walletAddress]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (!walletAddress) return null;

  // Per-user balance from ledger — locked reflects live pricing
  const available = balance?.available_sol ?? 0;
  const locked = balance?.locked_in_trades_sol ?? 0;
  const lockedEntryCost = balance?.locked_entry_cost_sol ?? 0;
  const totalBalance = balance?.total_balance_sol ?? (available + locked);
  const deposited = balance?.total_deposited_sol ?? 0;
  const withdrawn = balance?.total_withdrawn_sol ?? 0;
  const fees = balance?.total_fees_sol ?? 0;
  const pnl = balance?.realised_pnl_sol ?? 0;
  const unrealisedPnl = balance?.unrealised_pnl_sol ?? 0;

  const custodialAddr = custodialWallet?.wallet_address || balance?.custodial_address || "";
  const shortAddr = custodialAddr ? `${custodialAddr.slice(0, 6)}...${custodialAddr.slice(-4)}` : "";

  const handleWithdraw = async () => {
    const amount = parseFloat(withdrawAmount);
    if (!amount || amount <= 0) {
      toast.error("Enter a valid amount");
      return;
    }
    if (amount > available) {
      toast.error(`Max withdrawal: ${available.toFixed(6)} SOL`);
      return;
    }
    setWithdrawing(true);
    try {
      if (onWithdraw) {
        await onWithdraw(amount);
      }
      setShowWithdrawModal(false);
      setWithdrawAmount("");
      fetchData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Withdrawal failed");
    }
    setWithdrawing(false);
  };

  return (
    <>
      <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm overflow-hidden" data-testid="fund-ledger">
        {/* Header row */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[#00FFA3]/10 flex items-center justify-center">
              <Wallet className="w-3.5 h-3.5 text-[#00FFA3]" />
            </div>
            <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300" style={{ fontFamily: "Orbitron, sans-serif" }}>
              Fund Ledger
            </span>
          </div>
          <div className="flex items-center gap-2">
            {custodialAddr && (
              <button
                onClick={() => safeCopy(custodialAddr)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] hover:border-[#00FFA3]/30 transition-colors group"
                data-testid="ledger-wallet-address"
                title={custodialAddr}
              >
                <span className="text-[10px] font-mono text-slate-400 group-hover:text-slate-200">{shortAddr}</span>
                <Copy className="w-3 h-3 text-slate-500 group-hover:text-[#00FFA3]" />
              </button>
            )}
            <button
              onClick={fetchData}
              disabled={loading}
              className="w-6 h-6 rounded-full border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/30 transition-colors"
              data-testid="ledger-refresh-btn"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Main content */}
        <div className="px-5 py-4">
          {loading ? (
            <div className="h-16 flex items-center justify-center">
              <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-[1fr_1px_1fr_1px_auto] gap-4 md:gap-6 items-start">
              {/* Left: User's balance */}
              <div className="text-center md:text-left">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Your Balance</p>
                <p className="text-2xl font-bold font-mono" style={{ color: totalBalance >= 0 ? "#00FFA3" : "#FF4444" }} data-testid="ledger-total-balance">
                  {totalBalance.toFixed(6)} <span className="text-sm text-slate-500">SOL</span>
                </p>
                {locked > 0 && (
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {available.toFixed(6)} available · {locked.toFixed(6)} in trades
                    {unrealisedPnl !== 0 && (
                      <span className={unrealisedPnl >= 0 ? " text-[#00FFA3]" : " text-[#FF4444]"}>
                        {" "}({unrealisedPnl >= 0 ? "+" : ""}{unrealisedPnl.toFixed(6)} P&L)
                      </span>
                    )}
                  </p>
                )}
              </div>

              <div className="hidden md:block bg-white/[0.06] self-stretch" />

              {/* Center: Breakdown */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-0">
                <BalanceStat label="Deposited" value={deposited} color="#00C2FF" />
                <BalanceStat label="Withdrawn" value={withdrawn} color="#FF4444" />
                <BalanceStat label="In Trades (Live)" value={locked} color="#FFB800" />
                <BalanceStat label="Fees" value={fees} color="#D946EF" />
                <BalanceStat label="Realised P&L" value={pnl} color={pnl >= 0 ? "#00FFA3" : "#FF4444"} />
                <BalanceStat label="Unrealised P&L" value={unrealisedPnl} color={unrealisedPnl >= 0 ? "#00FFA3" : "#FF4444"} />
              </div>

              <div className="hidden md:block bg-white/[0.06] self-stretch" />

              {/* Right: Deposit/Withdraw */}
              <div className="flex md:flex-col gap-2 min-w-[140px]">
                <Button
                  onClick={onDeposit}
                  className="flex-1 bg-[#00FFA3] text-black hover:bg-[#00FFA3]/80 text-xs h-9"
                  data-testid="ledger-deposit-btn"
                >
                  <ArrowRight className="w-3.5 h-3.5 mr-1.5 rotate-90" />
                  Deposit
                </Button>
                <Button
                  onClick={() => { setWithdrawAmount(""); setShowWithdrawModal(true); }}
                  variant="outline"
                  className="flex-1 border-white/20 text-xs h-9"
                  disabled={available <= 0}
                  data-testid="ledger-withdraw-btn"
                >
                  <ArrowRight className="w-3.5 h-3.5 mr-1.5 -rotate-90" />
                  Withdraw
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Transaction History */}
        <button
          onClick={() => setShowHistory(p => !p)}
          className="w-full flex items-center justify-between px-5 py-2.5 border-t border-white/[0.06] text-xs text-slate-400 hover:text-slate-200 transition-colors"
          data-testid="ledger-history-toggle"
        >
          <span className="flex items-center gap-1.5">
            <History className="w-3 h-3" />
            Transaction History ({history.length})
          </span>
          {showHistory ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>

        {showHistory && (
          <div className="px-5 pb-4 max-h-48 overflow-y-auto" data-testid="ledger-history-list">
            {history.length > 0 ? (
              <div className="space-y-1.5">
                {history.map(entry => {
                  const style = TYPE_STYLES[entry.entry_type] || TYPE_STYLES.adjustment;
                  return (
                    <div key={entry.entry_id} className="flex items-start gap-2.5 py-1.5 border-b border-white/[0.03] last:border-0">
                      <div className="w-4 h-4 rounded-full flex items-center justify-center mt-0.5" style={{ background: `${style.color}15`, color: style.color }}>
                        {style.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: style.color }}>{style.label}</span>
                          <span className="text-[11px] font-mono font-semibold" style={{ color: entry.amount_sol >= 0 ? "#00FFA3" : "#FF4444" }}>
                            {entry.amount_sol >= 0 ? "+" : ""}{entry.amount_sol.toFixed(6)}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 truncate">{entry.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-center text-[10px] text-slate-500 py-3">No transactions yet. Deposit SOL to get started.</p>
            )}
          </div>
        )}
      </div>

      {/* Withdrawal Modal */}
      {showWithdrawModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setShowWithdrawModal(false)}>
          <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-[#FF4444]/30" onClick={e => e.stopPropagation()} data-testid="withdraw-modal">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <ArrowUpRight className="w-5 h-5 text-[#FF4444]" />
                Withdraw SOL
              </h3>
              <button onClick={() => setShowWithdrawModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Available balance */}
              <div className="p-4 bg-black/30 rounded-xl border border-white/[0.06]">
                <p className="text-xs text-slate-500 mb-1">Available to Withdraw</p>
                <p className="text-xl font-bold font-mono text-[#00FFA3]">
                  {available.toFixed(6)} <span className="text-sm text-slate-500">SOL</span>
                </p>
              </div>

              {/* Amount input */}
              <div>
                <label className="text-xs text-slate-400 block mb-2">Withdrawal Amount (SOL)</label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.000001"
                    min="0"
                    max={available}
                    value={withdrawAmount}
                    onChange={e => setWithdrawAmount(e.target.value)}
                    className="w-full p-3 pr-16 bg-black/40 border border-white/10 rounded-xl text-white font-mono text-sm focus:border-[#FF4444]/50 focus:outline-none"
                    placeholder="0.000000"
                    data-testid="withdraw-amount-input"
                  />
                  <button
                    onClick={() => setWithdrawAmount(available.toFixed(6))}
                    className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-[10px] font-bold text-[#FF4444] bg-[#FF4444]/10 rounded hover:bg-[#FF4444]/20 transition-colors"
                    data-testid="withdraw-max-btn"
                  >
                    MAX
                  </button>
                </div>
                {parseFloat(withdrawAmount) > available && (
                  <p className="text-[10px] text-red-400 mt-1">Exceeds available balance</p>
                )}
              </div>

              {/* Destination */}
              <div className="p-3 bg-black/20 rounded-xl">
                <p className="text-[10px] text-slate-500 mb-1">Funds will be sent to your connected wallet:</p>
                <p className="text-xs font-mono text-slate-300 break-all">{walletAddress}</p>
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-2">
                <Button
                  onClick={() => setShowWithdrawModal(false)}
                  variant="outline"
                  className="flex-1 border-white/20"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleWithdraw}
                  disabled={!withdrawAmount || parseFloat(withdrawAmount) <= 0 || parseFloat(withdrawAmount) > available || withdrawing}
                  className="flex-1 bg-[#FF4444] text-white hover:bg-[#FF4444]/80"
                  data-testid="withdraw-confirm-btn"
                >
                  {withdrawing ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <ArrowUpRight className="w-4 h-4 mr-2" />
                  )}
                  {withdrawing ? "Processing..." : "Confirm Withdrawal"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
