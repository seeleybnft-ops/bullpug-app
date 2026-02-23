/**
 * Watchlist Component - Track favorite coins from Top Picks
 * Shows price changes since adding and allows easy management
 */

import { useState, useEffect, useCallback } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useAccount } from "wagmi";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import axios from "axios";
import {
  Star, StarOff, TrendingUp, TrendingDown, Trash2, RefreshCw,
  ExternalLink, Copy, Eye, Loader2, Plus
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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

export default function Watchlist({ onClose }) {
  const { publicKey, connected: solanaConnected } = useWallet();
  const { address: evmAddress, isConnected: evmConnected } = useAccount();
  
  const walletAddress = solanaConnected 
    ? publicKey?.toBase58() 
    : (evmConnected ? evmAddress : null);

  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(false);
  const [removing, setRemoving] = useState(null);

  const fetchWatchlist = useCallback(async () => {
    if (!walletAddress) return;
    
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/watchlist/${walletAddress}`);
      setWatchlist(data.coins || []);
    } catch (e) {
      console.error("Failed to fetch watchlist:", e);
      toast.error("Failed to load watchlist");
    }
    setLoading(false);
  }, [walletAddress]);

  useEffect(() => {
    if (walletAddress) {
      fetchWatchlist();
    }
  }, [walletAddress, fetchWatchlist]);

  const removeFromWatchlist = async (symbol) => {
    if (!walletAddress) return;
    
    setRemoving(symbol);
    try {
      await axios.post(`${API}/watchlist/remove`, {
        wallet_address: walletAddress,
        symbol
      });
      setWatchlist(prev => prev.filter(c => c.symbol !== symbol));
      toast.success(`${symbol} removed from watchlist`);
    } catch (e) {
      console.error("Failed to remove from watchlist:", e);
      toast.error("Failed to remove");
    }
    setRemoving(null);
  };

  const clearWatchlist = async () => {
    if (!walletAddress) return;
    if (!confirm("Clear all coins from watchlist?")) return;
    
    setLoading(true);
    try {
      await axios.delete(`${API}/watchlist/${walletAddress}/clear`);
      setWatchlist([]);
      toast.success("Watchlist cleared");
    } catch (e) {
      console.error("Failed to clear watchlist:", e);
      toast.error("Failed to clear");
    }
    setLoading(false);
  };

  const formatPrice = (price) => {
    if (!price) return "$0.00";
    if (price < 0.0001) return `$${price.toFixed(8)}`;
    if (price < 1) return `$${price.toFixed(6)}`;
    return `$${price.toFixed(4)}`;
  };

  const formatPercent = (pct) => {
    if (!pct && pct !== 0) return "0.00%";
    const sign = pct >= 0 ? "+" : "";
    return `${sign}${pct.toFixed(2)}%`;
  };

  if (!walletAddress) {
    return (
      <div className="glass-card rounded-2xl p-6 border border-white/10">
        <div className="text-center py-8">
          <Star className="w-12 h-12 mx-auto mb-4 text-slate-600" />
          <h3 className="text-lg font-bold text-white mb-2">Watchlist</h3>
          <p className="text-sm text-slate-400">Connect wallet to track your favorite coins</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-gradient-to-r from-[#FFD700]/10 to-[#FF8C00]/10">
        <div className="flex items-center gap-2">
          <Star className="w-5 h-5 text-[#FFD700]" />
          <h3 className="font-bold text-white">Watchlist</h3>
          <span className="text-xs text-slate-400">({watchlist.length} coins)</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchWatchlist}
            disabled={loading}
            className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            title="Refresh prices"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {watchlist.length > 0 && (
            <button
              onClick={clearWatchlist}
              className="p-2 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
              title="Clear watchlist"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {loading && watchlist.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-[#FFD700]" />
          </div>
        ) : watchlist.length === 0 ? (
          <div className="text-center py-8">
            <Eye className="w-10 h-10 mx-auto mb-3 text-slate-600" />
            <p className="text-slate-400 text-sm mb-2">No coins in watchlist</p>
            <p className="text-slate-500 text-xs">
              Click the ⭐ on any coin in Top Picks to add it here
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {watchlist.map((coin, i) => (
              <div 
                key={i}
                className={`p-3 rounded-xl border transition-colors ${
                  coin.is_profitable 
                    ? 'bg-[#00FFA3]/5 border-[#00FFA3]/20 hover:bg-[#00FFA3]/10' 
                    : 'bg-red-500/5 border-red-500/20 hover:bg-red-500/10'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                      coin.is_profitable 
                        ? 'bg-gradient-to-br from-[#00FFA3] to-[#00C2FF] text-black'
                        : 'bg-gradient-to-br from-red-500 to-orange-500 text-white'
                    }`}>
                      {coin.symbol?.slice(0, 2)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-bold text-white">{coin.symbol}</p>
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/10 text-slate-400">
                          {coin.platform}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 truncate max-w-[150px]">{coin.name}</p>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <p className="font-mono text-sm text-white">{formatPrice(coin.current_price)}</p>
                    <div className={`flex items-center gap-1 justify-end text-xs ${
                      coin.is_profitable ? 'text-[#00FFA3]' : 'text-red-400'
                    }`}>
                      {coin.is_profitable ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {formatPercent(coin.price_change_pct)}
                    </div>
                  </div>
                </div>

                {/* Details Row */}
                <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between text-[10px]">
                  <div className="flex items-center gap-3">
                    {/* Contract Address */}
                    {coin.contract_address && (
                      <button 
                        onClick={() => copyToClipboard(coin.contract_address, "Contract")}
                        className="flex items-center gap-1 text-slate-500 hover:text-white transition-colors"
                      >
                        <Copy className="w-3 h-3" />
                        <span className="font-mono">{truncateAddress(coin.contract_address)}</span>
                      </button>
                    )}
                    
                    {/* Added Price */}
                    <span className="text-slate-600">
                      Added @ {formatPrice(coin.added_price)}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {/* DEX Link */}
                    {coin.dex_url ? (
                      <a 
                        href={coin.dex_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[#00FFA3] hover:text-white transition-colors"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Trade
                      </a>
                    ) : (
                      <a 
                        href={`https://dexscreener.com/solana?q=${coin.symbol}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[#00FFA3] hover:text-white transition-colors"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Find
                      </a>
                    )}
                    
                    {/* Remove Button */}
                    <button
                      onClick={() => removeFromWatchlist(coin.symbol)}
                      disabled={removing === coin.symbol}
                      className="flex items-center gap-1 text-red-400 hover:text-red-300 transition-colors"
                    >
                      {removing === coin.symbol ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <StarOff className="w-3 h-3" />
                      )}
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Export a hook for adding to watchlist from other components
export const useWatchlist = () => {
  const { publicKey, connected: solanaConnected } = useWallet();
  const { address: evmAddress, isConnected: evmConnected } = useAccount();
  
  const walletAddress = solanaConnected 
    ? publicKey?.toBase58() 
    : (evmConnected ? evmAddress : null);

  const addToWatchlist = async (coin) => {
    if (!walletAddress) {
      toast.error("Connect wallet to add to watchlist");
      return false;
    }
    
    try {
      const { data } = await axios.post(`${API}/watchlist/add`, {
        wallet_address: walletAddress,
        coin: {
          symbol: coin.symbol,
          name: coin.name,
          contract_address: coin.contract_address,
          dex_url: coin.dex_url,
          platform: coin.platform || "Solana",
          added_price: coin.price || 0
        }
      });
      
      if (data.success) {
        toast.success(`${coin.symbol} added to watchlist`);
        return true;
      } else {
        toast.info(data.message);
        return false;
      }
    } catch (e) {
      console.error("Failed to add to watchlist:", e);
      toast.error("Failed to add to watchlist");
      return false;
    }
  };

  const isInWatchlist = async (symbol) => {
    if (!walletAddress) return false;
    
    try {
      const { data } = await axios.get(`${API}/watchlist/${walletAddress}`);
      return data.coins?.some(c => c.symbol === symbol) || false;
    } catch {
      return false;
    }
  };

  return { addToWatchlist, isInWatchlist, walletAddress };
};
