import { useState, useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export function RiskCalculator({ settings, positionSize: externalPosition, entryPrice: externalEntry, onPositionChange, onEntryChange }) {
  const [positionSize, setPositionSize] = useState(externalPosition || 0.1);
  const [entryPrice, setEntryPrice] = useState(externalEntry || 1);
  const [stopLoss, setStopLoss] = useState(settings?.stop_loss_percent || 10);
  const [takeProfit, setTakeProfit] = useState(settings?.take_profit_percent || 25);

  useEffect(() => {
    if (externalPosition !== undefined && externalPosition !== positionSize) {
      setPositionSize(externalPosition);
    }
  }, [externalPosition]);

  useEffect(() => {
    if (externalEntry !== undefined && externalEntry !== entryPrice) {
      setEntryPrice(externalEntry);
    }
  }, [externalEntry]);

  const handlePositionChange = (value) => {
    setPositionSize(value);
    if (onPositionChange) onPositionChange(value);
  };

  const handleEntryChange = (value) => {
    setEntryPrice(value);
    if (onEntryChange) onEntryChange(value);
  };

  const maxLoss = positionSize * (stopLoss / 100);
  const potentialProfit = positionSize * (takeProfit / 100);
  const riskRewardRatio = takeProfit / stopLoss;

  return (
    <div className="bg-white/5 rounded-xl p-4 border border-[#D946EF]/20 mb-4" data-testid="risk-calculator">
      <h4 className="flex items-center gap-2 text-sm font-bold text-[#D946EF] mb-4">
        <AlertTriangle className="w-4 h-4" />
        Risk Calculator
      </h4>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Position (SOL)</label>
          <input
            type="number"
            value={positionSize}
            onChange={(e) => handlePositionChange(Math.max(0.01, parseFloat(e.target.value) || 0))}
            step="0.01"
            min="0.01"
            className="w-full bg-white/10 border border-white/20 rounded px-2 py-1.5 text-xs font-mono text-white focus:border-[#D946EF] focus:outline-none"
            data-testid="risk-calc-position"
          />
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Entry Price ($)</label>
          <input
            type="number"
            value={entryPrice}
            onChange={(e) => handleEntryChange(Math.max(0.000001, parseFloat(e.target.value) || 0))}
            step="0.01"
            min="0.000001"
            className="w-full bg-white/10 border border-white/20 rounded px-2 py-1.5 text-xs font-mono text-white focus:border-[#D946EF] focus:outline-none"
            data-testid="risk-calc-entry"
          />
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Stop Loss (%)</label>
          <input
            type="number"
            value={stopLoss}
            onChange={(e) => setStopLoss(Math.max(1, parseFloat(e.target.value) || 0))}
            step="1"
            min="1"
            max="100"
            className="w-full bg-white/10 border border-white/20 rounded px-2 py-1.5 text-xs font-mono text-white focus:border-[#FF6B6B] focus:outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Take Profit (%)</label>
          <input
            type="number"
            value={takeProfit}
            onChange={(e) => setTakeProfit(Math.max(1, parseFloat(e.target.value) || 0))}
            step="1"
            min="1"
            className="w-full bg-white/10 border border-white/20 rounded px-2 py-1.5 text-xs font-mono text-white focus:border-[#00FFA3] focus:outline-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="bg-[#FF6B6B]/10 rounded-lg p-2">
          <p className="text-[10px] text-slate-500">Max Loss</p>
          <p className="text-sm font-bold text-[#FF6B6B]">-{maxLoss.toFixed(4)} SOL</p>
        </div>
        <div className="bg-[#00FFA3]/10 rounded-lg p-2">
          <p className="text-[10px] text-slate-500">Potential Profit</p>
          <p className="text-sm font-bold text-[#00FFA3]">+{potentialProfit.toFixed(4)} SOL</p>
        </div>
        <div className={`${riskRewardRatio >= 2 ? 'bg-[#00FFA3]/10' : 'bg-[#F5D300]/10'} rounded-lg p-2`}>
          <p className="text-[10px] text-slate-500">Risk:Reward</p>
          <p className={`text-sm font-bold ${riskRewardRatio >= 2 ? 'text-[#00FFA3]' : 'text-[#F5D300]'}`}>
            1:{riskRewardRatio.toFixed(1)}
          </p>
        </div>
      </div>

      <p className="text-[10px] text-slate-500 text-center mt-2">
        {riskRewardRatio >= 2 ? 'Good risk:reward ratio (>=1:2)' : 'Consider higher take profit for better R:R'}
      </p>
    </div>
  );
}
