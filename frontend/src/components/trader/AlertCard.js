import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import axios from "axios";
import {
  TrendingUp, TrendingDown, Loader2, Zap,
  ExternalLink, Star, Trash2, DollarSign
} from "lucide-react";
import { API } from "./constants";

export function AlertCard({ alert, onDelete, walletAddress, onQuickBuy }) {
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [addingToWatchlist, setAddingToWatchlist] = useState(false);
  const [showQuickBuy, setShowQuickBuy] = useState(false);
  const [buyAmount, setBuyAmount] = useState(0.1);
  const [buying, setBuying] = useState(false);

  useEffect(() => {
    const checkWatchlist = async () => {
      if (!walletAddress) return;
      try {
        const response = await axios.get(`${API}/watchlist/${walletAddress}`);
        const coins = response.data.coins || [];
        setIsInWatchlist(coins.some(c => c.symbol?.toUpperCase() === alert.symbol?.toUpperCase()));
      } catch (err) { console.error("Check watchlist error:", err); }
    };
    checkWatchlist();
  }, [walletAddress, alert.symbol]);

  const addToWatchlist = async () => {
    if (!walletAddress || addingToWatchlist) return;
    setAddingToWatchlist(true);
    try {
      await axios.post(`${API}/watchlist/add`, { wallet_address: walletAddress, symbol: alert.symbol, contract_address: alert.token_mint || "" });
      setIsInWatchlist(true);
      toast.success(`${alert.symbol} added to watchlist!`);
    } catch (err) { toast.error("Failed to add to watchlist"); }
    setAddingToWatchlist(false);
  };

  const removeFromWatchlist = async () => {
    if (!walletAddress) return;
    try {
      await axios.delete(`${API}/watchlist/remove`, { data: { wallet_address: walletAddress, symbol: alert.symbol } });
      setIsInWatchlist(false);
      toast.success(`${alert.symbol} removed from watchlist`);
    } catch (err) { toast.error("Failed to remove from watchlist"); }
  };

  const handleQuickBuy = async () => {
    if (buyAmount <= 0 || buying) return;
    setBuying(true);
    let currentPrice = 0;
    try {
      if (alert.token_mint) {
        const response = await axios.get(`https://api.dexscreener.com/latest/dex/tokens/${alert.token_mint}`);
        const pairs = response.data?.pairs || [];
        if (pairs.length > 0) {
          const bestPair = pairs.reduce((a, b) => (parseFloat(a.liquidity?.usd || 0) > parseFloat(b.liquidity?.usd || 0) ? a : b));
          currentPrice = parseFloat(bestPair.priceUsd || 0);
        }
      }
    } catch (err) { console.error("Price fetch error:", err); }
    await onQuickBuy({ symbol: alert.symbol, contract_address: alert.token_mint, token_mint: alert.token_mint, price: currentPrice }, buyAmount);
    setBuying(false);
    setShowQuickBuy(false);
  };

  const dexScreenerUrl = alert.token_mint ? `https://dexscreener.com/solana/${alert.token_mint}` : `https://dexscreener.com/solana?q=${alert.symbol}`;

  return (
    <div className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10 hover:border-white/20 transition-colors" data-testid={`alert-${alert.alert_id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${alert.alert_type.includes("up") ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"}`}>
            {alert.alert_type.includes("up") ? <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFA3]" /> : <TrendingDown className="w-5 h-5 sm:w-6 sm:h-6 text-[#FF6B6B]" />}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-bold text-white text-sm sm:text-base">{alert.symbol}</p>
              <span className={`px-1.5 py-0.5 text-[10px] rounded ${alert.alert_type.includes("up") ? "bg-[#00FFA3]/20 text-[#00FFA3]" : "bg-[#FF6B6B]/20 text-[#FF6B6B]"}`}>
                {alert.alert_type === "breakout_up" && "BREAKOUT"}
                {alert.alert_type === "breakout_down" && "BREAKDOWN"}
                {alert.alert_type === "price_above" && "TARGET UP"}
                {alert.alert_type === "price_below" && "TARGET DOWN"}
              </span>
            </div>
            <p className="text-xs text-slate-500">{alert.alert_type.includes("price") && alert.target_price ? `Target: $${alert.target_price.toFixed(6)}` : "Momentum-based alert"}</p>
            {alert.scan_reason && <p className="text-[10px] text-[#F5D300] mt-0.5">{alert.scan_reason}</p>}
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <a href={dexScreenerUrl} target="_blank" rel="noopener noreferrer" className="p-2 rounded-lg bg-[#00C2FF]/10 text-[#00C2FF] hover:bg-[#00C2FF]/20 transition-colors" title="View on DexScreener" data-testid={`alert-dexscreener-${alert.alert_id}`}>
            <ExternalLink className="w-4 h-4" />
          </a>
          <button onClick={isInWatchlist ? removeFromWatchlist : addToWatchlist} disabled={addingToWatchlist} className={`p-2 rounded-lg transition-colors ${isInWatchlist ? "bg-[#F5D300]/20 text-[#F5D300]" : "bg-white/5 text-slate-400 hover:text-[#F5D300] hover:bg-[#F5D300]/10"}`} title={isInWatchlist ? "Remove from watchlist" : "Add to watchlist"} data-testid={`alert-watchlist-${alert.alert_id}`}>
            {addingToWatchlist ? <Loader2 className="w-4 h-4 animate-spin" /> : <Star className={`w-4 h-4 ${isInWatchlist ? "fill-[#F5D300]" : ""}`} />}
          </button>
          <button onClick={() => setShowQuickBuy(!showQuickBuy)} className="p-2 rounded-lg bg-[#00FFA3]/10 text-[#00FFA3] hover:bg-[#00FFA3]/20 transition-colors" title="Quick Buy" data-testid={`alert-quickbuy-${alert.alert_id}`}>
            <DollarSign className="w-4 h-4" />
          </button>
          <button onClick={() => onDelete(alert.alert_id)} className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-[#FF6B6B] hover:bg-[#FF6B6B]/10 transition-colors" title="Delete alert">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      {showQuickBuy && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-400">Quick Buy:</span>
            <div className="flex items-center gap-2 flex-1">
              <input type="number" value={buyAmount} onChange={(e) => setBuyAmount(Math.max(0.01, parseFloat(e.target.value) || 0))} step="0.01" min="0.01" max="10" className="w-20 bg-white/10 border border-white/20 rounded px-2 py-1.5 text-sm font-mono text-white focus:border-[#00FFA3] focus:outline-none" placeholder="SOL" />
              <span className="text-xs text-slate-500">SOL</span>
              <Button onClick={handleQuickBuy} disabled={buying || buyAmount <= 0 || !alert.token_mint} size="sm" className="bg-gradient-to-r from-[#00FFA3] to-[#00C2FF] text-black hover:opacity-90">
                {buying ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Zap className="w-4 h-4 mr-1" /> Buy {alert.symbol}</>}
              </Button>
            </div>
          </div>
          {!alert.token_mint && <p className="text-[10px] text-[#FF6B6B] mt-1">Token address not available for quick buy</p>}
        </div>
      )}
      <div className="mt-2 text-[10px] text-slate-600">Created: {new Date(alert.created_at).toLocaleString()}</div>
    </div>
  );
}
