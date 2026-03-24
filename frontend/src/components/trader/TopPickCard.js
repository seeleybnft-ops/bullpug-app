import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Loader2, Zap, DollarSign, Copy, ExternalLink
} from "lucide-react";

export function TopPickCard({ coin, index, type, onCopy, onAnalyze, onQuickBuy }) {
  const [showBuyInput, setShowBuyInput] = useState(false);
  const [buyAmount, setBuyAmount] = useState(0.1);
  const [buying, setBuying] = useState(false);

  const colors = {
    safe: { bg: "bg-[#00FFA3]/5", border: "border-[#00FFA3]/20", text: "text-[#00FFA3]", hover: "hover:bg-[#00FFA3]/10" },
    volatile: { bg: "bg-[#FF6B6B]/5", border: "border-[#FF6B6B]/20", text: "text-[#FF6B6B]", hover: "hover:bg-[#FF6B6B]/10" },
    new: { bg: "bg-[#F5D300]/5", border: "border-[#F5D300]/20", text: "text-[#F5D300]", hover: "hover:bg-[#F5D300]/10" }
  };
  const c = colors[type] || colors.safe;
  const isHot = coin.volume_24h && coin.volume_24h > 100000;
  const isTrending = coin.change_24h && coin.change_24h > 50;

  const truncateAddress = (address) => {
    if (!address) return "";
    if (address.length <= 12) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  const handleQuickBuy = async () => {
    if (buyAmount <= 0) return;
    setBuying(true);
    await onQuickBuy(coin, buyAmount);
    setBuying(false);
    setShowBuyInput(false);
  };

  return (
    <div className={`p-3 rounded-xl border transition-colors ${c.bg} ${c.border} ${c.hover}`} data-testid={`top-pick-${coin.symbol}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold ${
            type === "safe" ? 'bg-gradient-to-br from-[#00FFA3] to-[#00C2FF] text-black'
            : type === "volatile" ? 'bg-gradient-to-br from-[#FF6B6B] to-[#FF8C00] text-white'
            : 'bg-gradient-to-br from-[#F5D300] to-[#FF8C00] text-black'
          }`}>
            {type === "new" ? "\uD83D\uDE80" : index + 1}
          </div>
          <div>
            <div className="flex items-center gap-1 flex-wrap">
              <p className="font-medium text-white text-sm">{coin.symbol}</p>
              {coin.is_bonded && <span className="px-1.5 py-0.5 text-[8px] bg-[#00FFA3]/20 text-[#00FFA3] rounded font-bold">BONDED</span>}
              {isHot && <span className="px-1.5 py-0.5 text-[8px] bg-[#FF6B6B]/30 text-[#FF6B6B] rounded font-bold animate-pulse">HOT</span>}
              {isTrending && <span className="px-1.5 py-0.5 text-[8px] bg-[#00FFA3]/30 text-[#00FFA3] rounded font-bold">TRENDING</span>}
            </div>
            <p className="text-[10px] text-slate-500">{coin.platform || "Solana"}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-sm text-white">${coin.price < 0.001 ? coin.price?.toFixed(6) : coin.price?.toFixed(4)}</p>
          <p className={`text-[10px] ${coin.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>{coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(1)}%</p>
        </div>
      </div>

      <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between flex-wrap gap-2">
        {coin.contract_address ? (
          <button onClick={() => onCopy(coin.contract_address, "Contract")} className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition-colors group" title="Click to copy contract address">
            <Copy className="w-3 h-3" /><span className="font-mono">{truncateAddress(coin.contract_address)}</span>
          </button>
        ) : <span className="text-[10px] text-slate-600">-</span>}
        <div className="flex items-center gap-2">
          <button onClick={onAnalyze} className={`flex items-center gap-1 text-[10px] ${c.text} hover:text-white transition-colors`} title="Generate trading signal">
            <Zap className="w-3 h-3" /> Analyze
          </button>
          <button onClick={() => setShowBuyInput(!showBuyInput)} className="flex items-center gap-1 text-[10px] bg-[#00FFA3]/20 text-[#00FFA3] px-2 py-1 rounded hover:bg-[#00FFA3]/30 transition-colors" title="Quick buy this token">
            <DollarSign className="w-3 h-3" /> Buy
          </button>
          {coin.dex_url && (
            <a href={coin.dex_url} target="_blank" rel="noopener noreferrer" className={`flex items-center gap-1 text-[10px] ${c.text} hover:text-white transition-colors`}>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>

      {showBuyInput && (
        <div className="mt-2 pt-2 border-t border-white/5 flex items-center gap-2">
          <input type="number" value={buyAmount} onChange={(e) => setBuyAmount(Math.max(0.01, parseFloat(e.target.value) || 0))} step="0.01" min="0.01" max="10" className="flex-1 bg-white/10 border border-white/20 rounded px-2 py-1 text-sm font-mono text-white focus:border-[#00FFA3] focus:outline-none" placeholder="SOL amount" />
          <Button onClick={handleQuickBuy} disabled={buying || buyAmount <= 0} size="sm" className="bg-gradient-to-r from-[#00FFA3] to-[#00C2FF] text-black hover:opacity-90">
            {buying ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3 mr-1" />}
            {buying ? "" : "Buy"}
          </Button>
        </div>
      )}

      {coin.reason && <p className="mt-2 text-[10px] text-slate-400 line-clamp-2">{coin.reason}</p>}
    </div>
  );
}
