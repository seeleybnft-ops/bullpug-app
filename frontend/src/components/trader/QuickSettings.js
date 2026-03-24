import { useState, useRef, useEffect } from "react";
import { Settings } from "lucide-react";
import { Button } from "@/components/ui/button";

function EditDialog({ label, value, min, max, color, onConfirm, onCancel }) {
  const [draft, setDraft] = useState(String(value));
  const inputRef = useRef(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, []);

  const handleSubmit = () => {
    const parsed = parseInt(draft, 10);
    if (isNaN(parsed)) { onCancel(); return; }
    const clamped = Math.min(max, Math.max(min, parsed));
    if (clamped === value) { onCancel(); return; }
    onConfirm(clamped);
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[100] p-4" onClick={onCancel} data-testid="edit-percent-dialog">
      <div className="bg-[#12121A] rounded-2xl p-6 max-w-sm w-full border border-white/10" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white mb-1">Edit {label}</h3>
        <p className="text-xs text-slate-500 mb-4">Current: {value}% &middot; Range: {min}% - {max}%</p>
        <input
          ref={inputRef}
          type="number"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit();
            if (e.key === "Escape") onCancel();
          }}
          min={min}
          max={max}
          step="1"
          className="w-full h-14 rounded-xl text-center text-3xl font-bold font-mono border-2 bg-black/40 focus:outline-none mb-2"
          style={{ color, borderColor: color }}
          data-testid="edit-percent-input"
        />
        <p className="text-[10px] text-slate-600 text-center mb-4">
          {label} will change from <span className="text-white font-bold">{value}%</span> to <span style={{ color }} className="font-bold">{draft}%</span> for all positions
        </p>
        <div className="flex gap-3">
          <Button onClick={onCancel} variant="outline" className="flex-1 border-white/20 text-slate-300">Cancel</Button>
          <Button onClick={handleSubmit} className="flex-1 font-bold" style={{ backgroundColor: color, color: "#000" }} data-testid="edit-percent-apply">
            Apply {draft}%
          </Button>
        </div>
      </div>
    </div>
  );
}

function EditablePercent({ label, value, color, borderColor, bgColor, min, max, onConfirm, testIdPrefix }) {
  const [showDialog, setShowDialog] = useState(false);

  const handleDialogConfirm = (newValue) => {
    setShowDialog(false);
    onConfirm(newValue);
  };

  const stepDown = () => { if (value > min) onConfirm(value - 1); };
  const stepUp = () => { if (value < max) onConfirm(value + 1); };

  return (
    <div>
      <label className="text-xs text-slate-400 mb-2 block">{label}</label>
      <div className="flex items-center justify-center gap-2">
        <button onClick={stepDown} className="w-10 h-10 rounded-lg bg-white/10 hover:bg-white/20 font-bold text-xl flex items-center justify-center transition-colors" style={{ color }} data-testid={`${testIdPrefix}-minus`}>−</button>
        <button onClick={() => setShowDialog(true)} className="w-16 h-10 rounded-lg border flex items-center justify-center cursor-pointer hover:ring-2 hover:ring-white/20 hover:scale-105 transition-all active:scale-95" style={{ backgroundColor: bgColor, borderColor }} title="Click to enter a custom value" data-testid={`${testIdPrefix}-display`}>
          <span className="text-lg font-bold" style={{ color }}>{value}%</span>
        </button>
        <button onClick={stepUp} className="w-10 h-10 rounded-lg bg-white/10 hover:bg-white/20 font-bold text-xl flex items-center justify-center transition-colors" style={{ color }} data-testid={`${testIdPrefix}-plus`}>+</button>
      </div>
      {showDialog && (
        <EditDialog label={label} value={value} min={min} max={max} color={color} onConfirm={handleDialogConfirm} onCancel={() => setShowDialog(false)} />
      )}
    </div>
  );
}

export function QuickSettings({ autoTradeStatus, onUpdateSettings }) {
  const tpValue = autoTradeStatus?.settings?.take_profit_percent || 25;
  const slValue = autoTradeStatus?.settings?.stop_loss_percent || 15;
  const trailingEnabled = autoTradeStatus?.settings?.auto_trailing_stop_enabled ?? true;
  const trailingPct = autoTradeStatus?.settings?.auto_trailing_stop_percent || 5;

  return (
    <div className="bg-gradient-to-r from-[#D946EF]/5 to-[#00FFA3]/5 border border-white/10 rounded-xl p-4" data-testid="quick-settings-panel">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <Settings className="w-4 h-4 text-[#D946EF]" />
          Quick Settings
        </h4>
        <span className="text-xs text-slate-500">Click value to type custom %</span>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <EditablePercent label="Take Profit" value={tpValue} color="#00FFA3" borderColor="rgba(0,255,163,0.3)" bgColor="rgba(0,255,163,0.1)" min={5} max={200} onConfirm={(v) => onUpdateSettings({ auto_take_profit_percent: v })} testIdPrefix="quick-tp" />
        <EditablePercent label="Stop Loss" value={slValue} color="#FF6B6B" borderColor="rgba(255,107,107,0.3)" bgColor="rgba(255,107,107,0.1)" min={3} max={50} onConfirm={(v) => onUpdateSettings({ auto_stop_loss_percent: v })} testIdPrefix="quick-sl" />
      </div>
      {/* Trailing Stop Controls */}
      <div className="mt-3 pt-3 border-t border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              data-testid="trailing-stop-toggle"
              onClick={() => onUpdateSettings({ auto_trailing_stop_enabled: !trailingEnabled })}
              className={`relative w-9 h-5 rounded-full transition-colors ${trailingEnabled ? 'bg-cyan-500' : 'bg-zinc-600'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${trailingEnabled ? 'translate-x-4' : ''}`} />
            </button>
            <span className="text-xs text-white">Trailing Stop</span>
            <span className="text-[10px] text-zinc-500">locks gains as price rises</span>
          </div>
          {trailingEnabled && (
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-zinc-500">Trail after +{trailingPct}%</span>
              <button
                onClick={() => onUpdateSettings({ auto_trailing_stop_percent: Math.max(2, trailingPct - 1) })}
                className="w-5 h-5 rounded bg-white/10 text-xs text-cyan-400 hover:bg-white/20 flex items-center justify-center"
              >-</button>
              <span className="text-xs font-mono text-cyan-400 w-6 text-center">{trailingPct}%</span>
              <button
                onClick={() => onUpdateSettings({ auto_trailing_stop_percent: Math.min(20, trailingPct + 1) })}
                className="w-5 h-5 rounded bg-white/10 text-xs text-cyan-400 hover:bg-white/20 flex items-center justify-center"
              >+</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
