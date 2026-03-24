import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  TrendingUp, TrendingDown, Loader2, Zap,
  ExternalLink, Timer, Trash2, CheckCircle, AlertCircle, Calculator
} from "lucide-react";

export function PositionCard({ position, onQuickSell, onDelete, onManualClose, onCustodialSell, custodialWallet, onUseInCalculator }) {
  const [showSellInput, setShowSellInput] = useState(false);
  const [sellPercentage, setSellPercentage] = useState(100);
  const [tokenBalance, setTokenBalance] = useState(null);
  const [loadingBalance, setLoadingBalance] = useState(false);
  const [selling, setSelling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [closing, setClosing] = useState(false);
  const [holdTime, setHoldTime] = useState("");
  const pnlColor = position.unrealized_pnl_pct >= 0 ? "#00FFA3" : "#FF6B6B";
  const pnlSol = position.unrealized_pnl_sol || 0;
  const pnlUsd = position.unrealized_pnl_usd || 0;
  const currentValueSol = position.current_value_sol || position.amount_sol || position.input_sol || 0;
  const currentValueUsd = position.current_value_usd || 0;

  const isCustodialPosition = position.auto_trade || position.custodial || position.source === 'custodial' || position.synced_from_chain;

  useEffect(() => {
    const fetchTokenBalance = async () => {
      if (!showSellInput || !position.token_mint) return;
      setLoadingBalance(true);
      try {
        const API = process.env.REACT_APP_BACKEND_URL + '/api';
        const walletToCheck = isCustodialPosition ? custodialWallet?.wallet_address : position.wallet_address;
        if (walletToCheck) {
          const response = await fetch(`${API}/custodial-wallet/token-balance/${walletToCheck}/${position.token_mint}`);
          if (response.ok) {
            const data = await response.json();
            setTokenBalance(data);
          }
        }
      } catch (e) {
        console.error("Error fetching token balance:", e);
      }
      setLoadingBalance(false);
    };
    fetchTokenBalance();
  }, [showSellInput, position.token_mint, isCustodialPosition, custodialWallet, position.wallet_address]);

  useEffect(() => {
    const calculateHoldTime = () => {
      const createdAt = new Date(position.created_at);
      const now = new Date();
      const diffMs = now - createdAt;
      const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
      if (days > 0) setHoldTime(`${days}d ${hours}h ${minutes}m`);
      else if (hours > 0) setHoldTime(`${hours}h ${minutes}m ${seconds}s`);
      else if (minutes > 0) setHoldTime(`${minutes}m ${seconds}s`);
      else setHoldTime(`${seconds}s`);
    };
    calculateHoldTime();
    const interval = setInterval(calculateHoldTime, 1000);
    return () => clearInterval(interval);
  }, [position.created_at]);

  const handleQuickSell = async () => {
    if (!tokenBalance || tokenBalance.amount <= 0) { toast.error("No tokens to sell"); return; }
    const sellTokenAmount = (tokenBalance.raw_amount * sellPercentage) / 100;
    setSelling(true);
    try {
      if (isCustodialPosition) await onCustodialSell(position, sellTokenAmount, sellPercentage);
      else await onQuickSell(position, sellTokenAmount);
    } catch (e) { console.error("Sell error:", e); }
    setSelling(false);
    setShowSellInput(false);
  };

  const handleDelete = async () => {
    const isGhostPosition = position.executed_on_chain === false;
    if (!isGhostPosition && !window.confirm(`Remove ${position.token_symbol} position? This won't sell the token, just removes it from tracking.`)) return;
    try { setDeleting(true); await onDelete(position); } catch (e) { console.error("Delete error:", e); } finally { setDeleting(false); }
  };

  const handleManualClose = async () => {
    if (!window.confirm(`Mark ${position.token_symbol} as closed?\n\nThis will record the current price as exit price and move the position to history.\n\nUse this if you sold the tokens outside the bot.`)) return;
    try { setClosing(true); await onManualClose(position); } catch (e) { console.error("Manual close error:", e); } finally { setClosing(false); }
  };

  const isGhostPosition = position.executed_on_chain === false;
  const isPendingExit = position.status?.startsWith('pending_');

  return (
    <div className={`bg-white/5 rounded-xl p-4 border ${isGhostPosition ? 'border-amber-500/30 bg-amber-500/5' : isPendingExit ? 'border-purple-500/30 bg-purple-500/5' : 'border-white/10'}`} data-testid={`position-${position.token_symbol}`}>
      {isGhostPosition && (
        <div className="flex items-center gap-2 mb-3 pb-3 border-b border-amber-500/20">
          <AlertCircle className="w-4 h-4 text-amber-400" />
          <span className="text-xs text-amber-400">Ghost Position - Not executed on-chain</span>
        </div>
      )}
      {isPendingExit && !isGhostPosition && (
        <div className="flex items-center justify-between gap-2 mb-3 pb-3 border-b border-purple-500/20">
          <div className="flex items-center gap-2">
            <Timer className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-purple-400">
              {position.status === 'pending_take_profit' ? 'Take-Profit Triggered' : 'Stop-Loss Triggered'} - Sell pending
            </span>
          </div>
          <Button onClick={handleManualClose} disabled={closing} size="sm" className="bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 text-xs" data-testid={`manual-close-${position.token_symbol}`}>
            {closing ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <CheckCircle className="w-3 h-3 mr-1" />}
            Mark as Sold
          </Button>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${position.trade_type === "buy" ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"}`}>
            {position.trade_type === "buy" ? <TrendingUp className="w-5 h-5 text-[#00FFA3]" /> : <TrendingDown className="w-5 h-5 text-[#FF6B6B]" />}
          </div>
          <div>
            <p className="font-bold">{position.token_symbol}</p>
            <p className="text-xs text-slate-500">{(position.amount_sol || position.input_sol)?.toFixed(4)} SOL invested</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            {position.current_price ? (
              <>
                <p className="font-mono font-bold text-lg" style={{ color: pnlColor }}>{position.unrealized_pnl_pct >= 0 ? "+" : ""}{(position.unrealized_pnl_pct || 0).toFixed(2)}%</p>
                <div className="flex items-center gap-2 text-xs">
                  <span style={{ color: pnlColor }} className="font-mono">{pnlSol >= 0 ? "+" : ""}{pnlSol.toFixed(4)} SOL</span>
                  <span className="text-slate-500">|</span>
                  <span style={{ color: pnlColor }} className="font-mono">{pnlUsd >= 0 ? "+" : ""}${Math.abs(pnlUsd).toFixed(2)}</span>
                </div>
              </>
            ) : <p className="text-sm text-slate-500">Price unavailable</p>}
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => setShowSellInput(!showSellInput)} size="sm" className="bg-[#FF6B6B]/20 text-[#FF6B6B] hover:bg-[#FF6B6B]/30" data-testid={`sell-btn-${position.token_symbol}`}>
              <TrendingDown className="w-4 h-4 mr-1" /> Sell
            </Button>
            {!isPendingExit && (
              <Button onClick={handleManualClose} disabled={closing} size="sm" variant="outline" className="border-purple-500/30 text-purple-400 hover:bg-purple-500/10" title="Mark as closed" data-testid={`close-btn-${position.token_symbol}`}>
                {closing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              </Button>
            )}
            {onUseInCalculator && (
              <Button onClick={() => onUseInCalculator(position)} size="sm" variant="outline" className="border-[#D946EF]/30 text-[#D946EF] hover:bg-[#D946EF]/10" title="Use in Risk Calculator" data-testid={`calc-btn-${position.token_symbol}`}>
                <Calculator className="w-4 h-4" />
              </Button>
            )}
            <button onClick={handleDelete} disabled={deleting} className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-[#FF6B6B] transition-colors" title="Remove position" data-testid={`delete-btn-${position.token_symbol}`}>
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-3 gap-4 text-xs">
        <div>
          <p className="text-slate-500">Entry Price</p>
          <p className="font-mono text-white">{position.entry_price ? `$${position.entry_price < 0.01 ? position.entry_price?.toFixed(8) : position.entry_price?.toFixed(6)}` : "N/A"}</p>
        </div>
        <div>
          <p className="text-slate-500">Current Price</p>
          <p className="font-mono text-white">{position.current_price ? `$${position.current_price < 0.01 ? position.current_price?.toFixed(8) : position.current_price?.toFixed(6)}` : <span className="text-slate-500">Loading...</span>}</p>
        </div>
        <div>
          <p className="text-slate-500">Current Value</p>
          <p className="font-mono text-[#00C2FF]">{currentValueSol.toFixed(4)} SOL <span className="text-slate-500">(${currentValueUsd.toFixed(2)})</span></p>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          <Timer className="w-4 h-4 text-[#D946EF]" />
          <span className="text-slate-400">Holding for:</span>
          <span className="font-mono text-[#D946EF] font-medium">{holdTime}</span>
        </div>
        {position.token_mint && (
          <a href={`https://dexscreener.com/solana/${position.token_mint}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-[#00C2FF] hover:underline">
            <ExternalLink className="w-3 h-3" /> DexScreener
          </a>
        )}
      </div>

      {showSellInput && (
        <div className="mt-3 pt-3 border-t border-white/10 space-y-3">
          <div className="flex items-center justify-between bg-white/5 rounded-lg p-3">
            <div>
              <p className="text-xs text-slate-500">Your {position.token_symbol} Holdings</p>
              {loadingBalance ? (
                <div className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin text-slate-400" /><span className="text-sm text-slate-400">Loading...</span></div>
              ) : tokenBalance ? (
                <p className="font-mono text-lg text-white">{tokenBalance.amount?.toLocaleString(undefined, { maximumFractionDigits: 4 })} <span className="text-sm text-slate-400">{position.token_symbol}</span></p>
              ) : <p className="text-sm text-[#FF6B6B]">No tokens found</p>}
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Location</p>
              <p className={`text-sm font-medium ${isCustodialPosition ? 'text-[#D946EF]' : 'text-[#00C2FF]'}`}>{isCustodialPosition ? 'Auto-Trade Wallet' : 'Your Wallet'}</p>
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Sell Amount ({sellPercentage}% = {tokenBalance ? ((tokenBalance.amount * sellPercentage) / 100).toFixed(4) : '0'} {position.token_symbol})</label>
            <div className="flex gap-2 mb-3">
              {[25, 50, 75, 100].map(pct => (
                <button key={pct} onClick={() => setSellPercentage(pct)} className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-colors ${sellPercentage === pct ? 'bg-[#FF6B6B] text-white' : 'bg-white/10 text-slate-400 hover:bg-white/20'}`}>{pct}%</button>
              ))}
            </div>
            <input type="range" value={sellPercentage} onChange={(e) => setSellPercentage(parseInt(e.target.value))} min="1" max="100" className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer accent-[#FF6B6B]" />
          </div>
          <Button onClick={handleQuickSell} disabled={selling || !tokenBalance || tokenBalance.amount <= 0} className="w-full bg-gradient-to-r from-[#FF6B6B] to-[#FF8C00] text-white hover:opacity-90">
            {selling ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
            {selling ? "Processing..." : isCustodialPosition ? `Sell ${sellPercentage}% (Auto-Execute)` : `Sell ${sellPercentage}% (Wallet Approval)`}
          </Button>
          {!isCustodialPosition && <p className="text-[10px] text-slate-500 text-center">You will be prompted to approve this transaction in your wallet</p>}
        </div>
      )}
    </div>
  );
}
