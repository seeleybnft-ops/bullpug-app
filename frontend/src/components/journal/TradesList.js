/**
 * TradesList Component - Display and manage logged trades
 * Extracted from TradingJournal for better maintainability
 */

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Edit2, Trash2, Calendar } from "lucide-react";

export default function TradesList({ trades, onEdit, onDelete, formatCurrency }) {
  const [filter, setFilter] = useState("all");
  const [deleting, setDeleting] = useState(null);
  const filtered = trades.filter(t => filter === "all" || t.status === filter);

  const handleDelete = async (tradeId) => {
    console.log("Delete requested for trade:", tradeId);
    setDeleting(tradeId);
    try {
      const result = await onDelete(tradeId);
      console.log("Delete result:", result);
    } catch (e) {
      console.error("Delete failed:", e);
    }
    setDeleting(null);
  };
  
  // Helper to format P/L - detects legacy USD values vs actual SOL values
  const formatPnL = (pnl, positionSize) => {
    if (pnl === null || pnl === undefined) return null;
    
    // If pnl is much larger than position size, it's likely a legacy USD value
    // Convert roughly: assume SOL ~$130, so divide by 130
    const isLegacyUSD = Math.abs(pnl) > 10 && positionSize && Math.abs(pnl) > positionSize * 50;
    
    if (isLegacyUSD) {
      const solValue = pnl / 130; // Approximate conversion
      return { value: solValue, isConverted: true };
    }
    return { value: pnl, isConverted: false };
  };

  return (
    <div className="space-y-4" data-testid="trades-list">
      <div className="flex items-center gap-2">
        {["all", "open", "closed"].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-xs font-bold uppercase transition-colors ${
              filter === f ? "bg-[#00C2FF]/10 text-[#00C2FF]" : "bg-white/5 text-slate-400 hover:text-white"
            }`}
            data-testid={`filter-${f}`}
          >
            {f}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="glass-card rounded-xl p-10 text-center" data-testid="no-trades">
          <p className="text-slate-500">No {filter !== "all" ? filter : ""} trades found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(trade => (
            <div key={trade.trade_id} className="glass-card rounded-xl p-4 hover:bg-white/[0.02] transition-colors" data-testid={`trade-${trade.trade_id}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm ${
                    trade.trade_type?.toLowerCase() === "long" ? "bg-[#00FFA3]/10 text-[#00FFA3]" :
                    trade.trade_type?.toLowerCase() === "short" ? "bg-red-500/10 text-red-400" :
                    "bg-[#00C2FF]/10 text-[#00C2FF]"
                  }`}>
                    {trade.asset?.slice(0, 4)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{trade.asset}</span>
                      <Badge className={`text-[9px] ${
                        trade.trade_type?.toLowerCase() === "long" ? "bg-[#00FFA3]/10 text-[#00FFA3]" :
                        trade.trade_type?.toLowerCase() === "short" ? "bg-red-500/10 text-red-400" :
                        "bg-[#00C2FF]/10 text-[#00C2FF]"
                      }`}>
                        {trade.trade_type} {trade.leverage && trade.leverage > 1 ? `${trade.leverage}x` : ""}
                      </Badge>
                      <Badge className={`text-[9px] ${trade.status === "open" ? "bg-amber-500/10 text-amber-400" : "bg-slate-500/10 text-slate-400"}`}>
                        {trade.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {trade.trade_id} | Entry: ${trade.entry_price} | Size: {trade.position_size}
                      {trade.exit_price && ` | Exit: $${trade.exit_price}`}
                    </p>
                    <p className="text-[10px] text-slate-600 mt-1">
                      <Calendar className="inline w-3 h-3 mr-1" />
                      {new Date(trade.date_entry).toLocaleDateString()}
                      {trade.strategy && <span className="ml-2">| {trade.strategy}</span>}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {trade.status === "closed" && (() => {
                    const pnlData = formatPnL(trade.pnl, trade.position_size);
                    if (!pnlData) return null;
                    return (
                      <>
                        <p className={`text-xl font-black ${pnlData.value >= 0 ? "text-[#00FFA3]" : "text-red-400"}`} style={{ fontFamily: 'Orbitron' }}>
                          {pnlData.value >= 0 ? "+" : ""}{pnlData.value.toFixed(4)} SOL
                          {pnlData.isConverted && <span className="text-[10px] text-slate-500 ml-1">~</span>}
                        </p>
                        {trade.pnl_percent !== undefined && (
                          <p className={`text-xs ${trade.pnl_percent >= 0 ? "text-[#00FFA3]" : "text-red-400"}`}>
                            {trade.pnl_percent >= 0 ? "+" : ""}{trade.pnl_percent?.toFixed(1)}%
                          </p>
                        )}
                      </>
                    );
                  })()}
                  <div className="flex items-center gap-2 mt-2">
                    <button onClick={() => onEdit(trade)} className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white" data-testid={`edit-${trade.trade_id}`}>
                      <Edit2 size={14} />
                    </button>
                    <button 
                      onClick={() => handleDelete(trade.trade_id)} 
                      disabled={deleting === trade.trade_id}
                      className="p-1.5 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-400 disabled:opacity-50" 
                      data-testid={`delete-${trade.trade_id}`}
                    >
                      {deleting === trade.trade_id ? (
                        <span className="w-3.5 h-3.5 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin inline-block" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                    </button>
                  </div>
                </div>
              </div>
              {(trade.entry_reason || trade.lessons) && (
                <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-1 md:grid-cols-2 gap-3">
                  {trade.entry_reason && (
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase mb-1">Entry Reason</p>
                      <p className="text-xs text-slate-300">{trade.entry_reason}</p>
                    </div>
                  )}
                  {trade.lessons && (
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase mb-1">Lessons</p>
                      <p className="text-xs text-slate-300">{trade.lessons}</p>
                    </div>
                  )}
                </div>
              )}
              {trade.tags?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {trade.tags.map((tag, i) => (
                    <span key={i} className="text-[9px] px-2 py-0.5 rounded-full bg-[#D946EF]/10 text-[#D946EF]">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
