import { Settings } from "lucide-react";
import { toast } from "sonner";

function EditablePercent({ label, value, color, borderColor, bgColor, min, max, onConfirm, testIdPrefix }) {

  const handleClickValue = () => {
    const input = window.prompt(
      `Enter new ${label} (current: ${value}%)\nRange: ${min}% - ${max}%`,
      String(value)
    );
    if (input === null) return; // User cancelled
    const parsed = parseInt(input, 10);
    if (isNaN(parsed)) { toast.error("Please enter a valid number"); return; }
    const clamped = Math.min(max, Math.max(min, parsed));
    if (clamped === value) return; // No change
    if (window.confirm(`Change ${label} from ${value}% to ${clamped}%?\n\nThis applies to all open positions.`)) {
      onConfirm(clamped);
    }
  };

  const stepDown = () => { if (value > min) onConfirm(value - 1); };
  const stepUp = () => { if (value < max) onConfirm(value + 1); };

  return (
    <div>
      <label className="text-xs text-slate-400 mb-2 block">{label}</label>
      <div className="flex items-center justify-center gap-2">
        <button
          onClick={stepDown}
          className="w-10 h-10 rounded-lg bg-white/10 hover:bg-white/20 font-bold text-xl flex items-center justify-center transition-colors"
          style={{ color }}
          data-testid={`${testIdPrefix}-minus`}
        >
          −
        </button>

        <button
          onClick={handleClickValue}
          className="w-16 h-10 rounded-lg border flex items-center justify-center cursor-pointer hover:ring-2 hover:ring-white/20 transition-all"
          style={{ backgroundColor: bgColor, borderColor: borderColor }}
          title="Click to enter a custom value"
          data-testid={`${testIdPrefix}-display`}
        >
          <span className="text-lg font-bold" style={{ color }}>{value}%</span>
        </button>

        <button
          onClick={stepUp}
          className="w-10 h-10 rounded-lg bg-white/10 hover:bg-white/20 font-bold text-xl flex items-center justify-center transition-colors"
          style={{ color }}
          data-testid={`${testIdPrefix}-plus`}
        >
          +
        </button>
      </div>
    </div>
  );
}

export function QuickSettings({ autoTradeStatus, onUpdateSettings }) {
  const tpValue = autoTradeStatus?.settings?.take_profit_percent || 25;
  const slValue = autoTradeStatus?.settings?.stop_loss_percent || 15;

  return (
    <div className="bg-gradient-to-r from-[#D946EF]/5 to-[#00FFA3]/5 border border-white/10 rounded-xl p-4" data-testid="quick-settings-panel">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <Settings className="w-4 h-4 text-[#D946EF]" />
          Quick Settings
        </h4>
        <span className="text-xs text-slate-500">Click value to type custom % &middot; Changes apply to all positions</span>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <EditablePercent
          label="Take Profit"
          value={tpValue}
          color="#00FFA3"
          borderColor="rgba(0,255,163,0.3)"
          bgColor="rgba(0,255,163,0.1)"
          min={5}
          max={200}
          onConfirm={(v) => onUpdateSettings({ auto_take_profit_percent: v })}
          testIdPrefix="quick-tp"
        />
        <EditablePercent
          label="Stop Loss"
          value={slValue}
          color="#FF6B6B"
          borderColor="rgba(255,107,107,0.3)"
          bgColor="rgba(255,107,107,0.1)"
          min={3}
          max={50}
          onConfirm={(v) => onUpdateSettings({ auto_stop_loss_percent: v })}
          testIdPrefix="quick-sl"
        />
      </div>
    </div>
  );
}
