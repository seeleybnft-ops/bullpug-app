/**
 * PerformanceScorecard - Weekly bot performance card shareable on X
 */

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { 
  Trophy, TrendingUp, Flame, Target, Activity, Share2, 
  RefreshCw, ChevronUp, ChevronDown, Loader2, Zap
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function PerformanceScorecard({ walletAddress }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const cardRef = useRef(null);

  useEffect(() => {
    if (!walletAddress) return;
    fetchScorecard();
  }, [walletAddress]);

  const fetchScorecard = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/ai-trader/performance-scorecard/${walletAddress}`);
      setData(res.data);
    } catch (e) {
      console.error("Scorecard fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  const shareOnX = () => {
    if (!data) return;
    const allTime = data.all_time;
    const week = data.this_week;
    const pnlEmoji = allTime.total_pnl_sol >= 0 ? "+" : "";
    const bestStr = data.best_trade_this_week
      ? `Best trade: $${data.best_trade_this_week.token_symbol} (+${data.best_trade_this_week.pnl_pct?.toFixed(1)}%)`
      : "";
    const streakStr = data.current_streak > 0 ? `${data.current_streak} win streak` : "";

    const text = [
      `My @BullpugBot Scorecard`,
      ``,
      `All-Time: ${allTime.total_trades} trades | ${allTime.win_rate}% win rate | ${pnlEmoji}${allTime.total_pnl_sol} SOL`,
      `This Week: ${week.trades} trades | ${week.win_rate}% WR | ${pnlEmoji}${week.pnl_sol} SOL`,
      bestStr,
      streakStr,
      ``,
      `#Bullpug #SolanaTrading #AI`
    ].filter(Boolean).join("\n");

    window.open(
      `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`,
      "_blank"
    );
  };

  if (loading) {
    return (
      <div className="glass-card rounded-xl p-4 border border-white/10 flex items-center justify-center h-20">
        <Loader2 className="w-5 h-5 animate-spin text-[#D946EF]" />
      </div>
    );
  }

  if (!data) return null;

  const { all_time, this_week, best_trade_this_week, current_streak, active_positions } = data;
  const pnlPositive = all_time.total_pnl_sol >= 0;

  return (
    <div 
      ref={cardRef}
      className="glass-card rounded-xl border border-[#D946EF]/20 overflow-hidden"
      data-testid="performance-scorecard"
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
        data-testid="scorecard-toggle"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#D946EF] to-[#FF6B6B] flex items-center justify-center">
            <Trophy className="w-4 h-4 text-white" />
          </div>
          <div className="text-left">
            <h4 className="text-sm font-bold text-white">Performance Scorecard</h4>
            <p className="text-[10px] text-slate-500">
              {all_time.total_trades} trades | {all_time.win_rate}% WR | {pnlPositive ? "+" : ""}{all_time.total_pnl_sol} SOL
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {current_streak >= 3 && (
            <span className="flex items-center gap-1 text-[10px] bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full">
              <Flame className="w-3 h-3" />
              {current_streak}
            </span>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* All-Time Stats */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-black/30 rounded-lg p-3 border border-white/5">
              <div className="flex items-center gap-1.5 mb-1">
                <Target className="w-3 h-3 text-[#D946EF]" />
                <span className="text-[10px] text-slate-500 uppercase">Win Rate</span>
              </div>
              <p className="text-lg font-bold text-white">{all_time.win_rate}%</p>
              <p className="text-[10px] text-slate-500">{all_time.wins}W / {all_time.losses}L</p>
            </div>
            <div className="bg-black/30 rounded-lg p-3 border border-white/5">
              <div className="flex items-center gap-1.5 mb-1">
                <TrendingUp className="w-3 h-3 text-[#00FFA3]" />
                <span className="text-[10px] text-slate-500 uppercase">Total P&L</span>
              </div>
              <p className={`text-lg font-bold ${pnlPositive ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>
                {pnlPositive ? "+" : ""}{all_time.total_pnl_sol} SOL
              </p>
              <p className="text-[10px] text-slate-500">{all_time.total_trades} trades</p>
            </div>
          </div>

          {/* This Week */}
          <div className="bg-[#D946EF]/5 rounded-lg p-3 border border-[#D946EF]/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[#D946EF]">This Week</span>
              <span className="text-[10px] text-slate-500">{this_week.trades} trades</span>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-bold text-white">{this_week.win_rate}% WR</span>
                <span className="text-xs text-slate-400 ml-2">
                  {this_week.pnl_sol >= 0 ? "+" : ""}{this_week.pnl_sol} SOL
                </span>
              </div>
              {best_trade_this_week && (
                <span className="text-[10px] bg-[#00FFA3]/20 text-[#00FFA3] px-2 py-0.5 rounded-full">
                  Best: ${best_trade_this_week.token_symbol} +{best_trade_this_week.pnl_pct?.toFixed(1)}%
                </span>
              )}
            </div>
          </div>

          {/* Streak + Active */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              {current_streak > 0 && (
                <span className="flex items-center gap-1 text-amber-400">
                  <Flame className="w-3.5 h-3.5" />
                  {current_streak} win streak
                </span>
              )}
              <span className="flex items-center gap-1 text-slate-400">
                <Activity className="w-3.5 h-3.5" />
                {active_positions} active
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <Button
              onClick={shareOnX}
              size="sm"
              className="flex-1 bg-black text-white border border-white/20 hover:bg-white/10"
              data-testid="share-scorecard-x"
            >
              <Share2 className="w-3.5 h-3.5 mr-1.5" />
              Share on X
            </Button>
            <Button
              onClick={fetchScorecard}
              size="sm"
              variant="outline"
              className="border-white/10"
              data-testid="refresh-scorecard"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
