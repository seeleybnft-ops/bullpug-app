/**
 * TopPicksSection - Display AI-recommended coins (Safe + Volatile)
 * Extracted from JournalAIAssistant for better maintainability
 */

import { useState } from "react";
import { RefreshCw, CheckCircle, AlertCircle, Copy, ExternalLink, Star } from "lucide-react";
import { toast } from "sonner";

// Helper to copy text to clipboard
const copyToClipboard = async (text, label = "Address") => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`${label} copied!`);
  } catch (e) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand("copy");
    document.body.removeChild(textArea);
    toast.success(`${label} copied!`);
  }
};

// Truncate address for display
const truncateAddress = (address) => {
  if (!address) return "";
  if (address.length <= 12) return address;
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
};

// Single coin card component
function CoinCard({ coin, index, type, onAddToWatchlist, addingToWatchlist }) {
  const isSafe = type === "safe";
  const colors = isSafe 
    ? { bg: "#00FFA3", text: "#00FFA3", border: "#00FFA3" }
    : { bg: "#FF6B6B", text: "#FF6B6B", border: "#FF6B6B" };

  return (
    <div 
      className={`p-2.5 rounded-lg border transition-colors ${
        isSafe 
          ? 'bg-[#00FFA3]/5 border-[#00FFA3]/20 hover:bg-[#00FFA3]/10' 
          : 'bg-[#FF6B6B]/5 border-[#FF6B6B]/20 hover:bg-[#FF6B6B]/10'
      }`}
      data-testid={`coin-card-${coin.symbol}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div 
            className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
              isSafe 
                ? 'bg-gradient-to-br from-[#00FFA3] to-[#00C2FF] text-black'
                : 'bg-gradient-to-br from-[#FF6B6B] to-[#FF8C00] text-white'
            }`}
          >
            {isSafe ? index + 1 : "⚡"}
          </div>
          <div>
            <p className="font-medium text-white text-xs">{coin.symbol}</p>
            <p className="text-[9px] text-slate-500">{coin.platform}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-xs text-white">
            ${coin.price < 0.001 ? coin.price?.toFixed(6) : coin.price?.toFixed(4)}
          </p>
          <p className={`text-[10px] ${coin.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
            {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Contract Address & DEX Link */}
      <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between">
        {coin.contract_address ? (
          <button 
            onClick={() => copyToClipboard(coin.contract_address, "Contract")}
            className="flex items-center gap-1 text-[9px] text-slate-500 hover:text-white transition-colors group"
            title="Click to copy"
          >
            <Copy className={`w-2.5 h-2.5 group-hover:text-[${colors.text}]`} />
            <span className="font-mono">{truncateAddress(coin.contract_address)}</span>
          </button>
        ) : (
          <span className="text-[9px] text-slate-600">-</span>
        )}
        <div className="flex items-center gap-3">
          {/* Add to Watchlist Button */}
          <button
            onClick={() => onAddToWatchlist(coin)}
            disabled={addingToWatchlist === coin.symbol}
            className="text-[#FFD700] hover:text-[#FFF700] hover:scale-110 transition-all"
            title="Add to Watchlist"
            data-testid={`add-watchlist-${coin.symbol}`}
          >
            <Star className={`w-4 h-4 ${addingToWatchlist === coin.symbol ? 'animate-pulse' : ''}`} fill="currentColor" />
          </button>
          {coin.dex_url ? (
            <a 
              href={coin.dex_url}
              target="_blank"
              rel="noopener noreferrer"
              className={`flex items-center gap-1 text-[9px] text-[${colors.text}] hover:text-white transition-colors`}
            >
              <ExternalLink className="w-2.5 h-2.5" />
              Trade
            </a>
          ) : (
            <a 
              href={`https://dexscreener.com/solana?q=${coin.symbol}`}
              target="_blank"
              rel="noopener noreferrer"
              className={`flex items-center gap-1 text-[9px] text-[${colors.text}] hover:text-white transition-colors`}
            >
              <ExternalLink className="w-2.5 h-2.5" />
              Find
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// Loading skeleton
function LoadingSkeleton({ count = 6 }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-16 bg-white/5 rounded-lg animate-pulse" />
      ))}
    </div>
  );
}

export default function TopPicksSection({ 
  recommendations, 
  volatilePicks, 
  loading, 
  lastUpdate,
  onRefresh,
  onAddToWatchlist,
  addingToWatchlist,
  showAutoRefreshNotice = true
}) {
  return (
    <div data-testid="top-picks-section">
      <div className="flex justify-between items-center mb-3">
        <div>
          <h4 className="text-xs font-medium text-slate-400 uppercase">Top Picks</h4>
          <p className="text-[10px] text-slate-500">
            Safe & High-Risk Solana Memecoins
            {lastUpdate && (
              <span className="ml-2 text-slate-600">
                • Updated {lastUpdate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
              </span>
            )}
          </p>
        </div>
        <button 
          onClick={onRefresh}
          disabled={loading}
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
          data-testid="refresh-picks-btn"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Auto-refresh notice */}
      {showAutoRefreshNotice && (
        <div className="mb-3 px-2 py-1 bg-[#00FFA3]/5 rounded-lg text-[10px] text-slate-500 flex items-center gap-1">
          <span className="w-1.5 h-1.5 bg-[#00FFA3] rounded-full animate-pulse" />
          Auto-refreshes every hour with fresh picks
        </div>
      )}

      {loading ? (
        <LoadingSkeleton count={6} />
      ) : (
        <div className="space-y-4">
          {/* Safe Picks */}
          <div>
            <h5 className="text-xs font-bold text-[#00FFA3] mb-2 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> SAFER PICKS
            </h5>
            <div className="space-y-2">
              {recommendations.slice(0, 5).map((coin, i) => (
                <CoinCard 
                  key={`safe-${i}`}
                  coin={coin} 
                  index={i} 
                  type="safe"
                  onAddToWatchlist={onAddToWatchlist}
                  addingToWatchlist={addingToWatchlist}
                />
              ))}
            </div>
          </div>

          {/* Volatile Picks */}
          <div>
            <h5 className="text-xs font-bold text-[#FF6B6B] mb-2 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> HIGH RISK / HIGH REWARD
            </h5>
            <div className="space-y-2">
              {volatilePicks.slice(0, 5).map((coin, i) => (
                <CoinCard 
                  key={`volatile-${i}`}
                  coin={coin} 
                  index={i} 
                  type="volatile"
                  onAddToWatchlist={onAddToWatchlist}
                  addingToWatchlist={addingToWatchlist}
                />
              ))}
              {volatilePicks.length === 0 && (
                <p className="text-slate-500 text-[10px] text-center py-2">No volatile picks available</p>
              )}
            </div>
          </div>
        </div>
      )}

      <p className="text-[10px] text-slate-600 mt-4 text-center">
        ⚠️ Memecoins are highly volatile. "Safer" means relatively lower risk, not safe. Always DYOR.
      </p>
    </div>
  );
}
