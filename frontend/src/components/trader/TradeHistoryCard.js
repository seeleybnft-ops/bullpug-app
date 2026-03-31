import { TrendingUp, TrendingDown, ArrowRight, ExternalLink } from "lucide-react";

export function TradeHistoryCard({ trade }) {
  const isProfitable = (trade.pnl_sol || trade.pnl_percent || 0) > 0;
  const isSell = trade.trade_type === "sell" || trade.action?.includes("sell") || trade.action?.includes("close") || trade.action?.includes("take_profit") || trade.action?.includes("stop_loss");
  const pnlSol = trade.pnl_sol || trade.realized_pnl_sol || 0;
  const pnlPct = trade.pnl_pct || trade.pnl_percent || trade.realized_pnl_pct || 0;
  const inputSol = trade.input_sol || trade.amount_sol || 0;
  const entryPrice = trade.entry_price || 0;
  const exitPrice = trade.exit_price || trade.current_price || 0;

  const getTimeHeld = () => {
    // Use backend-calculated time if available
    if (trade.time_held_minutes != null && trade.time_held_minutes > 0) {
      const mins = trade.time_held_minutes;
      const days = Math.floor(mins / (60 * 24));
      const hours = Math.floor((mins % (60 * 24)) / 60);
      const minutes = Math.floor(mins % 60);
      if (days > 0) return `${days}d ${hours}h`;
      if (hours > 0) return `${hours}h ${minutes}m`;
      return `${minutes}m`;
    }
    // Fallback: calculate from timestamps
    if (!trade.created_at) return null;
    const closeTime = trade.closed_at || trade.executed_at;
    if (!closeTime && !isSell) return null;
    const openTime = trade.position_opened_at || trade.created_at;
    const start = new Date(openTime);
    const end = closeTime ? new Date(closeTime) : new Date();
    const diffMs = end - start;
    if (diffMs <= 0) return null;
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const timeHeld = getTimeHeld();
  const tradeSource = trade.source || (trade.action?.includes("auto") ? "Auto-Trade" : "Manual");
  const borderColor = isSell ? (isProfitable ? "border-[#00FFA3]/30" : "border-[#FF6B6B]/30") : "border-white/10";
  const bgTint = isSell ? (isProfitable ? "bg-[#00FFA3]/5" : "bg-[#FF6B6B]/5") : "bg-white/5";

  return (
    <div className={`${bgTint} rounded-xl p-4 border ${borderColor}`} data-testid={`trade-history-${trade.execution_id || trade.log_id}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isSell ? (isProfitable ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20") : "bg-[#00C2FF]/20"}`}>
            {isSell ? (isProfitable ? <TrendingUp className="w-5 h-5 text-[#00FFA3]" /> : <TrendingDown className="w-5 h-5 text-[#FF6B6B]" />) : <ArrowRight className="w-5 h-5 text-[#00C2FF]" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-bold">{trade.token_symbol}</p>
              <span className={`px-2 py-0.5 text-[10px] rounded-full font-semibold ${isSell ? (isProfitable ? "bg-[#00FFA3]/20 text-[#00FFA3]" : "bg-[#FF6B6B]/20 text-[#FF6B6B]") : "bg-[#00C2FF]/20 text-[#00C2FF]"}`}>
                {isSell ? (trade.action?.includes("take_profit") ? "TAKE PROFIT" : trade.action?.includes("stop_loss") ? "STOP LOSS" : "SOLD") : "BUY"}
              </span>
              <span className="px-2 py-0.5 text-[10px] rounded-full bg-white/10 text-slate-400">{tradeSource}</span>
            </div>
            <p className="text-xs text-slate-500">{new Date(trade.executed_at || trade.created_at).toLocaleString()}</p>
          </div>
        </div>
        {isSell && (
          <div className="text-right">
            <p className={`font-mono font-bold text-lg ${isProfitable ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>{isProfitable ? "+" : ""}{pnlPct.toFixed(2)}%</p>
            <p className={`text-sm font-mono ${isProfitable ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>{isProfitable ? "+" : ""}{pnlSol.toFixed(4)} SOL</p>
          </div>
        )}
      </div>
      <div className="grid grid-cols-4 gap-3 text-xs pt-3 border-t border-white/5">
        <div>
          <p className="text-slate-500">{isSell ? "Sold" : "Invested"}</p>
          <p className="font-mono text-white">{inputSol.toFixed(4)} SOL</p>
        </div>
        {entryPrice > 0 && <div><p className="text-slate-500">Entry Price</p><p className="font-mono text-white">${entryPrice < 0.01 ? entryPrice.toFixed(8) : entryPrice.toFixed(6)}</p></div>}
        {isSell && exitPrice > 0 && <div><p className="text-slate-500">Exit Price</p><p className={`font-mono ${isProfitable ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>${exitPrice < 0.01 ? exitPrice.toFixed(8) : exitPrice.toFixed(6)}</p></div>}
        {timeHeld && <div><p className="text-slate-500">Time Held</p><p className="font-mono text-[#D946EF]">{timeHeld}</p></div>}
      </div>
      {(trade.tx_signature || trade.sell_tx_signature) && (
        <a href={`https://solscan.io/tx/${trade.sell_tx_signature || trade.tx_signature}`} target="_blank" rel="noopener noreferrer" className="mt-3 pt-3 border-t border-white/5 flex items-center gap-1 text-xs text-[#00C2FF] hover:underline">
          <ExternalLink className="w-3 h-3" /> View on Solscan
        </a>
      )}
    </div>
  );
}
