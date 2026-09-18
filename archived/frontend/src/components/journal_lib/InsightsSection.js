/**
 * InsightsSection - AI-generated trading insights from logged trades
 * Enhanced to show actual trade data and AI analysis
 */

import { useState, useEffect } from "react";
import { RefreshCw, TrendingUp, TrendingDown, Target, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function InsightsSection({ 
  insights, 
  loading, 
  onRefresh,
  walletAddress
}) {
  const [tradeStats, setTradeStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // Fetch trade statistics when wallet address is available
  useEffect(() => {
    if (walletAddress) {
      fetchTradeStats();
    }
  }, [walletAddress]);

  const fetchTradeStats = async () => {
    if (!walletAddress) return;
    setStatsLoading(true);
    try {
      const { data } = await axios.get(`${API}/journal/trades/${walletAddress}/stats`);
      setTradeStats(data);
    } catch (e) {
      console.error("Failed to fetch trade stats:", e);
      setTradeStats(null);
    }
    setStatsLoading(false);
  };

  return (
    <div data-testid="insights-section">
      <div className="flex justify-end mb-3">
        <button 
          onClick={() => {
            onRefresh();
            fetchTradeStats();
          }}
          disabled={loading}
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
          data-testid="refresh-insights-btn"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Trade Stats Summary */}
      {tradeStats && !statsLoading && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-white/5 rounded-lg p-3">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
              <Target className="w-3 h-3" />
              Win Rate
            </div>
            <p className={`text-lg font-bold ${tradeStats.win_rate >= 50 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
              {tradeStats.win_rate?.toFixed(1) || 0}%
            </p>
          </div>
          <div className="bg-white/5 rounded-lg p-3">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
              {tradeStats.total_pnl >= 0 ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              Total P&L
            </div>
            <p className={`text-lg font-bold ${tradeStats.total_pnl >= 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
              {tradeStats.total_pnl >= 0 ? '+' : ''}${tradeStats.total_pnl?.toFixed(2) || 0}
            </p>
          </div>
          <div className="bg-white/5 rounded-lg p-3">
            <div className="text-slate-400 text-xs mb-1">Total Trades</div>
            <p className="text-lg font-bold text-white">{tradeStats.total_trades || 0}</p>
          </div>
          <div className="bg-white/5 rounded-lg p-3">
            <div className="text-slate-400 text-xs mb-1">Best Trade</div>
            <p className="text-lg font-bold text-[#00FFA3]">
              {tradeStats.best_trade ? `+$${tradeStats.best_trade.toFixed(2)}` : '-'}
            </p>
          </div>
        </div>
      )}

      {/* AI Insights */}
      {loading || statsLoading ? (
        <div className="space-y-3">
          <div className="h-4 bg-white/10 rounded animate-pulse w-3/4" />
          <div className="h-4 bg-white/10 rounded animate-pulse w-full" />
          <div className="h-4 bg-white/10 rounded animate-pulse w-5/6" />
        </div>
      ) : (
        <div className="prose prose-invert prose-sm max-w-none">
          {!walletAddress ? (
            <div className="text-center py-4 bg-white/5 rounded-xl border border-white/10">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-slate-500" />
              <p className="text-slate-400 text-sm">Connect your wallet to see personalized insights</p>
            </div>
          ) : tradeStats?.total_trades === 0 ? (
            <div className="text-center py-4 bg-white/5 rounded-xl border border-white/10">
              <Target className="w-8 h-8 mx-auto mb-2 text-slate-500" />
              <p className="text-slate-400 text-sm">Log your first trade to get AI-powered insights</p>
              <p className="text-slate-500 text-xs mt-1">Go to the Trades tab to start tracking</p>
            </div>
          ) : (
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="text-slate-300 text-sm mb-3 leading-relaxed">{children}</p>,
                strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                h1: ({ children }) => <h1 className="text-lg font-bold text-white mt-4 mb-2">{children}</h1>,
                h2: ({ children }) => <h2 className="text-base font-bold text-white mt-3 mb-2">{children}</h2>,
                ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3">{children}</ul>,
                li: ({ children }) => <li className="text-slate-300 text-sm">{children}</li>,
              }}
            >
              {insights || "Loading insights..."}
            </ReactMarkdown>
          )}
        </div>
      )}
    </div>
  );
}
