import { useState } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  TrendingUp, TrendingDown, X, Loader2, Zap,
  ChevronDown, ChevronUp, ExternalLink
} from "lucide-react";
import { ShareButton } from "../SocialShare";
import { RISK_COLORS } from "./constants";

export function SignalCard({ signal, onReject, onQuickTrade }) {
  const [expanded, setExpanded] = useState(false);
  const [quickTrading, setQuickTrading] = useState(false);
  const [positionSol, setPositionSol] = useState(signal.suggested_position_sol);
  const riskColors = RISK_COLORS[signal.risk_category] || RISK_COLORS.safer;

  const handleQuickTrade = async () => {
    setQuickTrading(true);
    await onQuickTrade({ ...signal, suggested_position_sol: positionSol });
    setQuickTrading(false);
  };

  return (
    <div className={`bg-white/5 rounded-xl sm:rounded-2xl p-3 sm:p-5 border ${riskColors.border}`} data-testid={`signal-${signal.signal_id}`}>
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex items-center gap-3 sm:gap-4">
          <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl flex items-center justify-center flex-shrink-0 ${
            signal.signal_type === "buy" ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"
          }`}>
            {signal.signal_type === "buy" ? (
              <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFA3]" />
            ) : (
              <TrendingDown className="w-5 h-5 sm:w-6 sm:h-6 text-[#FF6B6B]" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-1 sm:gap-2 flex-wrap">
              <h3 className="text-base sm:text-lg font-bold">
                {signal.signal_type.toUpperCase()} {signal.token_symbol}
              </h3>
              <span className={`px-1.5 sm:px-2 py-0.5 rounded text-[10px] sm:text-xs ${riskColors.bg} ${riskColors.text}`}>
                {signal.risk_category === "safer" ? "SAFER" : "HIGH RISK"}
              </span>
              {signal.token_mint && (
                <a
                  href={`https://dexscreener.com/solana/${signal.token_mint}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded text-[10px] sm:text-xs bg-[#00C2FF]/10 text-[#00C2FF] hover:bg-[#00C2FF]/20 transition-colors"
                  title="View on DexScreener"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span className="hidden sm:inline">Chart</span>
                </a>
              )}
            </div>
            <p className="text-xs sm:text-sm text-slate-400">
              Confidence: <span className="text-white font-medium">{(signal.confidence * 100).toFixed(0)}%</span>
              {" \u2022 "}
              Strategy: <span className="text-white">{signal.strategy}</span>
            </p>
          </div>
        </div>

        <div className="flex gap-2 justify-end">
          <ShareButton type="signal" data={signal} className="hidden sm:flex" />
          <Button
            onClick={onReject}
            variant="outline"
            size="sm"
            className="border-[#FF6B6B]/30 text-[#FF6B6B] hover:bg-[#FF6B6B]/10 px-2 sm:px-3"
            data-testid={`reject-signal-${signal.signal_id}`}
          >
            <X className="w-4 h-4" />
          </Button>
          <Button
            onClick={handleQuickTrade}
            disabled={quickTrading || positionSol <= 0}
            size="sm"
            className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] text-white hover:opacity-90 text-xs sm:text-sm"
            data-testid={`quick-trade-${signal.signal_id}`}
          >
            {quickTrading ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Zap className="w-4 h-4 mr-1" />
            )}
            <span className="hidden xs:inline">Quick </span>Trade
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4 mt-3 sm:mt-4 text-xs sm:text-sm">
        <div>
          <p className="text-slate-500 text-[10px] sm:text-xs">Entry</p>
          <p className="font-mono">${signal.entry_price < 0.01 ? signal.entry_price.toFixed(8) : signal.entry_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500 text-[10px] sm:text-xs">Stop Loss</p>
          <p className="font-mono text-[#FF6B6B]">${signal.stop_loss_price < 0.01 ? signal.stop_loss_price.toFixed(8) : signal.stop_loss_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500 text-[10px] sm:text-xs">Take Profit</p>
          <p className="font-mono text-[#00FFA3]">${signal.take_profit_price < 0.01 ? signal.take_profit_price.toFixed(8) : signal.take_profit_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500 text-[10px] sm:text-xs mb-1">Position (SOL)</p>
          <div className="flex items-center gap-1">
            <input
              type="number"
              value={positionSol}
              onChange={(e) => setPositionSol(Math.max(0.01, parseFloat(e.target.value) || 0))}
              step="0.01"
              min="0.01"
              max="10"
              className="w-16 sm:w-20 bg-white/10 border border-white/20 rounded px-2 py-1 text-xs sm:text-sm font-mono text-white focus:border-[#00FFA3] focus:outline-none"
              data-testid={`position-input-${signal.signal_id}`}
            />
            <span className="text-slate-500 text-[10px] sm:text-xs">SOL</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-[10px] sm:text-xs text-slate-500 hover:text-white"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? "Hide" : "Show"} Analysis
        </button>
        <ShareButton type="signal" data={signal} className="sm:hidden" />
      </div>

      {expanded && (
        <div className="mt-3 p-2 sm:p-3 bg-black/20 rounded-lg sm:rounded-xl text-xs sm:text-sm">
          <p className="text-slate-400 mb-2">{signal.reasoning}</p>
          <div className="grid grid-cols-3 gap-2 text-[10px] sm:text-xs">
            <div>RSI: <span className="text-white">{signal.technical_indicators?.rsi?.toFixed(1)}</span></div>
            <div>Trend: <span className="text-white">{signal.technical_indicators?.short_trend}</span></div>
            <div>BB Pos: <span className="text-white">{(signal.technical_indicators?.bollinger?.position * 100)?.toFixed(0)}%</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
