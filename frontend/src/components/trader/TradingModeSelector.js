/**
 * Trading Mode Selector
 * Allows users to switch between trading modes:
 * - Conservative: Higher confidence thresholds, safer tokens only
 * - Normal: Balanced approach
 * - Aggressive: Lower thresholds, all tokens
 * - Sniper: Targets brand new token pairs (<30 min old)
 */
import { useState } from "react";
import { Shield, Target, Zap, Crosshair } from "lucide-react";

const MODES = [
  {
    id: "conservative",
    label: "Conservative",
    icon: Shield,
    color: "text-blue-400",
    bg: "bg-blue-500/20",
    border: "border-blue-500/50",
    desc: "High confidence, safer tokens"
  },
  {
    id: "normal",
    label: "Normal",
    icon: Target,
    color: "text-green-400",
    bg: "bg-green-500/20",
    border: "border-green-500/50",
    desc: "Balanced risk/reward"
  },
  {
    id: "aggressive",
    label: "Aggressive",
    icon: Zap,
    color: "text-orange-400",
    bg: "bg-orange-500/20",
    border: "border-orange-500/50",
    desc: "Lower thresholds, all tokens"
  },
  {
    id: "sniper",
    label: "Sniper",
    icon: Crosshair,
    color: "text-red-400",
    bg: "bg-red-500/20",
    border: "border-red-500/50",
    desc: "New pairs <30min, small positions"
  }
];

export default function TradingModeSelector({ currentMode, onModeChange }) {
  const [confirming, setConfirming] = useState(null);

  const handleSelect = (modeId) => {
    if (modeId === "sniper" && currentMode !== "sniper") {
      setConfirming(modeId);
    } else {
      onModeChange(modeId);
      setConfirming(null);
    }
  };

  return (
    <div data-testid="trading-mode-selector" className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4">
      <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
        <Target className="w-4 h-4 text-cyan-400" />
        Trading Mode
      </h4>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {MODES.map((mode) => {
          const Icon = mode.icon;
          const isActive = currentMode === mode.id;
          return (
            <button
              key={mode.id}
              data-testid={`mode-${mode.id}`}
              onClick={() => handleSelect(mode.id)}
              className={`p-3 rounded-lg border transition-all text-left ${
                isActive
                  ? `${mode.bg} ${mode.border} ring-1 ring-${mode.color.replace('text-', '')}`
                  : "bg-zinc-800/50 border-zinc-700 hover:border-zinc-600"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className={`w-4 h-4 ${isActive ? mode.color : "text-zinc-500"}`} />
                <span className={`text-xs font-medium ${isActive ? "text-white" : "text-zinc-400"}`}>
                  {mode.label}
                </span>
              </div>
              <p className="text-[10px] text-zinc-500">{mode.desc}</p>
            </button>
          );
        })}
      </div>

      {/* Sniper confirmation */}
      {confirming === "sniper" && (
        <div data-testid="sniper-confirm" className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-xs text-red-300 mb-2">
            Sniper mode targets brand new tokens (&lt;30 min old). This is HIGH RISK — positions are capped at 30% of normal size. Only enable if you understand the risks.
          </p>
          <div className="flex gap-2">
            <button
              data-testid="sniper-confirm-yes"
              onClick={() => { onModeChange("sniper"); setConfirming(null); }}
              className="px-3 py-1 bg-red-500/20 border border-red-500/50 rounded text-xs text-red-400 hover:bg-red-500/30"
            >
              Enable Sniper Mode
            </button>
            <button
              onClick={() => setConfirming(null)}
              className="px-3 py-1 bg-zinc-700 rounded text-xs text-zinc-400 hover:bg-zinc-600"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
