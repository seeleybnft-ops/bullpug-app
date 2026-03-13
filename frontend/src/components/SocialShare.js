/**
 * Social Sharing Component for Bullpug
 * Features:
 * - Share Trade Results with P/L screenshots
 * - Share AI Signals with referral links
 * - Share Portfolio Performance (weekly/monthly summaries)
 * - Leaderboard Sharing
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  Share2, Twitter, Copy, TrendingUp, TrendingDown, Trophy,
  Wallet, Target, Zap, Calendar, BarChart3, X
} from "lucide-react";

// Generate share URL for X (Twitter)
const generateTwitterUrl = (text, url = "") => {
  const encodedText = encodeURIComponent(text);
  const encodedUrl = url ? encodeURIComponent(url) : "";
  return `https://twitter.com/intent/tweet?text=${encodedText}${encodedUrl ? `&url=${encodedUrl}` : ""}`;
};

// Share Trade Result
export function ShareTradeResult({ trade, onClose }) {
  const isProfitable = (trade.pnl_pct || 0) > 0;
  const pnlEmoji = isProfitable ? "🚀" : "📉";
  const pnlSign = isProfitable ? "+" : "";
  
  const shareText = `${pnlEmoji} Just ${isProfitable ? "closed a winning" : "exited a"} trade on @BullpugToken!\n\n` +
    `📊 ${trade.token_symbol}\n` +
    `💰 P/L: ${pnlSign}${(trade.pnl_pct || 0).toFixed(2)}%\n` +
    `⏱️ Hold time: ${trade.hold_time || "N/A"}\n\n` +
    `Trade smarter with Bullpug AI Trading Bot! 🐶\n\n` +
    `#Bullpug #SolanaTrading #Memecoin`;
  
  const handleShare = () => {
    window.open(generateTwitterUrl(shareText), "_blank", "width=600,height=400");
    toast.success("Opening X to share your trade!");
    onClose?.();
  };
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(shareText);
    toast.success("Trade result copied to clipboard!");
  };
  
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-white/10" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Share2 className="w-5 h-5 text-[#D946EF]" />
            Share Trade Result
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Preview Card */}
        <div className={`p-4 rounded-xl border mb-4 ${isProfitable ? 'bg-[#00FFA3]/10 border-[#00FFA3]/30' : 'bg-[#FF6B6B]/10 border-[#FF6B6B]/30'}`}>
          <div className="flex items-center gap-3 mb-3">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${isProfitable ? 'bg-[#00FFA3]/20' : 'bg-[#FF6B6B]/20'}`}>
              {isProfitable ? <TrendingUp className="w-6 h-6 text-[#00FFA3]" /> : <TrendingDown className="w-6 h-6 text-[#FF6B6B]" />}
            </div>
            <div>
              <p className="font-bold text-lg">{trade.token_symbol}</p>
              <p className={`text-2xl font-bold ${isProfitable ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                {pnlSign}{(trade.pnl_pct || 0).toFixed(2)}%
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-400">Traded on Bullpug AI Trading Bot</p>
        </div>
        
        <div className="flex gap-3">
          <Button onClick={handleShare} className="flex-1 bg-black hover:bg-black/80 text-white">
            <Twitter className="w-4 h-4 mr-2" />
            Share on X
          </Button>
          <Button onClick={handleCopy} variant="outline" className="border-white/20">
            <Copy className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// Share AI Signal
export function ShareSignal({ signal, onClose }) {
  const signalEmoji = signal.signal_type === "buy" ? "🟢" : "🔴";
  const confidenceBar = "█".repeat(Math.round(signal.confidence * 10)) + "░".repeat(10 - Math.round(signal.confidence * 10));
  
  const shareText = `${signalEmoji} AI Trading Signal Alert!\n\n` +
    `📊 ${signal.signal_type?.toUpperCase()} ${signal.token_symbol}\n` +
    `📈 Entry: $${signal.entry_price?.toFixed(6)}\n` +
    `🎯 Target: $${signal.take_profit_price?.toFixed(6)}\n` +
    `🛡️ Stop: $${signal.stop_loss_price?.toFixed(6)}\n` +
    `📊 Confidence: [${confidenceBar}] ${(signal.confidence * 100).toFixed(0)}%\n\n` +
    `Get your own AI signals with @BullpugToken! 🐶\n\n` +
    `#Bullpug #TradingSignal #Solana`;
  
  const handleShare = () => {
    window.open(generateTwitterUrl(shareText), "_blank", "width=600,height=400");
    toast.success("Opening X to share this signal!");
    onClose?.();
  };
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(shareText);
    toast.success("Signal copied to clipboard!");
  };
  
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-white/10" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Zap className="w-5 h-5 text-[#F5D300]" />
            Share AI Signal
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Preview Card */}
        <div className={`p-4 rounded-xl border mb-4 ${signal.signal_type === 'buy' ? 'bg-[#00FFA3]/10 border-[#00FFA3]/30' : 'bg-[#FF6B6B]/10 border-[#FF6B6B]/30'}`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{signalEmoji}</span>
              <div>
                <p className="font-bold text-lg">{signal.signal_type?.toUpperCase()} {signal.token_symbol}</p>
                <p className="text-xs text-slate-400">Strategy: {signal.strategy}</p>
              </div>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-bold ${signal.signal_type === 'buy' ? 'bg-[#00FFA3]/20 text-[#00FFA3]' : 'bg-[#FF6B6B]/20 text-[#FF6B6B]'}`}>
              {(signal.confidence * 100).toFixed(0)}%
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="bg-white/5 rounded p-2">
              <p className="text-slate-500">Entry</p>
              <p className="font-mono">${signal.entry_price?.toFixed(6)}</p>
            </div>
            <div className="bg-white/5 rounded p-2">
              <p className="text-slate-500">Target</p>
              <p className="font-mono text-[#00FFA3]">${signal.take_profit_price?.toFixed(6)}</p>
            </div>
            <div className="bg-white/5 rounded p-2">
              <p className="text-slate-500">Stop</p>
              <p className="font-mono text-[#FF6B6B]">${signal.stop_loss_price?.toFixed(6)}</p>
            </div>
          </div>
        </div>
        
        <div className="flex gap-3">
          <Button onClick={handleShare} className="flex-1 bg-black hover:bg-black/80 text-white">
            <Twitter className="w-4 h-4 mr-2" />
            Share on X
          </Button>
          <Button onClick={handleCopy} variant="outline" className="border-white/20">
            <Copy className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// Share Portfolio Performance
export function SharePortfolioPerformance({ stats, period = "weekly", onClose }) {
  const { total_pnl_sol, win_rate, total_trades, best_trade } = stats;
  const isProfitable = total_pnl_sol > 0;
  const periodLabel = period === "weekly" ? "This Week" : "This Month";
  
  const shareText = `📊 My Bullpug Trading Performance - ${periodLabel}\n\n` +
    `💰 Total P/L: ${isProfitable ? "+" : ""}${total_pnl_sol?.toFixed(4)} SOL\n` +
    `📈 Win Rate: ${win_rate?.toFixed(1)}%\n` +
    `🎯 Total Trades: ${total_trades}\n` +
    `${best_trade ? `🏆 Best Trade: ${best_trade.symbol} (+${best_trade.pnl_pct?.toFixed(1)}%)\n` : ""}` +
    `\nTrade smarter with @BullpugToken AI Bot! 🐶\n\n` +
    `#Bullpug #TradingPerformance #Solana`;
  
  const handleShare = () => {
    window.open(generateTwitterUrl(shareText), "_blank", "width=600,height=400");
    toast.success("Opening X to share your performance!");
    onClose?.();
  };
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(shareText);
    toast.success("Performance summary copied!");
  };
  
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-white/10" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[#00C2FF]" />
            Share Performance
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Preview Card */}
        <div className="bg-gradient-to-br from-[#D946EF]/10 to-[#00FFA3]/10 p-4 rounded-xl border border-[#D946EF]/30 mb-4">
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-5 h-5 text-[#D946EF]" />
            <span className="font-bold">{periodLabel} Summary</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-xs text-slate-400">Total P/L</p>
              <p className={`text-xl font-bold ${isProfitable ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                {isProfitable ? "+" : ""}{total_pnl_sol?.toFixed(4)} SOL
              </p>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-xs text-slate-400">Win Rate</p>
              <p className="text-xl font-bold text-[#00C2FF]">{win_rate?.toFixed(1)}%</p>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-xs text-slate-400">Total Trades</p>
              <p className="text-xl font-bold text-white">{total_trades}</p>
            </div>
            {best_trade && (
              <div className="bg-white/5 rounded-lg p-3">
                <p className="text-xs text-slate-400">Best Trade</p>
                <p className="text-sm font-bold text-[#F5D300]">{best_trade.symbol} +{best_trade.pnl_pct?.toFixed(1)}%</p>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex gap-3">
          <Button onClick={handleShare} className="flex-1 bg-black hover:bg-black/80 text-white">
            <Twitter className="w-4 h-4 mr-2" />
            Share on X
          </Button>
          <Button onClick={handleCopy} variant="outline" className="border-white/20">
            <Copy className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// Share Leaderboard Ranking
export function ShareLeaderboardRank({ rank, stats, onClose }) {
  const rankEmoji = rank <= 3 ? ["🥇", "🥈", "🥉"][rank - 1] : "🏆";
  
  const shareText = `${rankEmoji} I'm ranked #${rank} on the @BullpugToken Leaderboard!\n\n` +
    `📊 Stats:\n` +
    `💰 Total P/L: ${stats.total_pnl_sol > 0 ? "+" : ""}${stats.total_pnl_sol?.toFixed(4)} SOL\n` +
    `📈 Win Rate: ${stats.win_rate?.toFixed(1)}%\n` +
    `🎯 Trades: ${stats.total_trades}\n\n` +
    `Can you beat my score? Join Bullpug! 🐶\n\n` +
    `#Bullpug #Leaderboard #SolanaTrading`;
  
  const handleShare = () => {
    window.open(generateTwitterUrl(shareText), "_blank", "width=600,height=400");
    toast.success("Opening X to share your ranking!");
    onClose?.();
  };
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(shareText);
    toast.success("Ranking copied to clipboard!");
  };
  
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-white/10" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Trophy className="w-5 h-5 text-[#F5D300]" />
            Share Ranking
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Preview Card */}
        <div className="bg-gradient-to-br from-[#F5D300]/10 to-[#FF8C00]/10 p-4 rounded-xl border border-[#F5D300]/30 mb-4 text-center">
          <div className="text-5xl mb-2">{rankEmoji}</div>
          <p className="text-3xl font-bold text-[#F5D300]">#{rank}</p>
          <p className="text-slate-400">Leaderboard Ranking</p>
          
          <div className="grid grid-cols-3 gap-2 mt-4 text-xs">
            <div className="bg-white/5 rounded p-2">
              <p className="text-slate-500">P/L</p>
              <p className={`font-bold ${stats.total_pnl_sol > 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                {stats.total_pnl_sol > 0 ? "+" : ""}{stats.total_pnl_sol?.toFixed(2)}
              </p>
            </div>
            <div className="bg-white/5 rounded p-2">
              <p className="text-slate-500">Win Rate</p>
              <p className="font-bold text-[#00C2FF]">{stats.win_rate?.toFixed(0)}%</p>
            </div>
            <div className="bg-white/5 rounded p-2">
              <p className="text-slate-500">Trades</p>
              <p className="font-bold text-white">{stats.total_trades}</p>
            </div>
          </div>
        </div>
        
        <div className="flex gap-3">
          <Button onClick={handleShare} className="flex-1 bg-black hover:bg-black/80 text-white">
            <Twitter className="w-4 h-4 mr-2" />
            Share on X
          </Button>
          <Button onClick={handleCopy} variant="outline" className="border-white/20">
            <Copy className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// Share Button Component (reusable)
export function ShareButton({ type, data, className = "" }) {
  const [showModal, setShowModal] = useState(false);
  
  const icons = {
    trade: TrendingUp,
    signal: Zap,
    performance: BarChart3,
    leaderboard: Trophy
  };
  
  const Icon = icons[type] || Share2;
  
  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className={`flex items-center gap-1 text-[10px] bg-black/50 hover:bg-black/80 text-white px-2 py-1 rounded transition-colors ${className}`}
        title="Share on X"
      >
        <Icon className="w-3 h-3" />
        <span className="hidden sm:inline">Share</span>
      </button>
      
      {showModal && type === "trade" && <ShareTradeResult trade={data} onClose={() => setShowModal(false)} />}
      {showModal && type === "signal" && <ShareSignal signal={data} onClose={() => setShowModal(false)} />}
      {showModal && type === "performance" && <SharePortfolioPerformance stats={data} onClose={() => setShowModal(false)} />}
      {showModal && type === "leaderboard" && <ShareLeaderboardRank rank={data.rank} stats={data.stats} onClose={() => setShowModal(false)} />}
    </>
  );
}

export default {
  ShareTradeResult,
  ShareSignal,
  SharePortfolioPerformance,
  ShareLeaderboardRank,
  ShareButton
};
