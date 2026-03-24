import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";

export function SettingsModal({ settings, onSave, onClose }) {
  const [form, setForm] = useState({
    risk_level: settings?.risk_level || "safer",
    max_position_sol: settings?.max_position_sol || 0.5,
    stop_loss_percent: settings?.stop_loss_percent || 10,
    take_profit_percent: settings?.take_profit_percent || 20,
    max_daily_trades: settings?.max_daily_trades || 5
  });

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-white/10">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Trading Settings
        </h2>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Risk Level</label>
            <select value={form.risk_level} onChange={(e) => setForm({ ...form, risk_level: e.target.value })} className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white">
              <option value="safer">Safer Tokens Only</option>
              <option value="high_risk">High Risk Tokens Only</option>
              <option value="both">Both (User Decides)</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Max Position (SOL): {form.max_position_sol}</label>
            <input type="range" min="0.01" max="1" step="0.01" value={form.max_position_sol} onChange={(e) => setForm({ ...form, max_position_sol: parseFloat(e.target.value) })} className="w-full" />
            <div className="flex justify-between text-xs text-slate-500"><span>0.01 SOL</span><span>1 SOL</span></div>
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Stop Loss: {form.stop_loss_percent}%</label>
            <input type="range" min="5" max="50" step="1" value={form.stop_loss_percent} onChange={(e) => setForm({ ...form, stop_loss_percent: parseFloat(e.target.value) })} className="w-full" />
            <div className="flex justify-between text-xs text-slate-500"><span>5%</span><span>50%</span></div>
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Take Profit: {form.take_profit_percent}%</label>
            <input type="range" min="10" max="100" step="5" value={form.take_profit_percent} onChange={(e) => setForm({ ...form, take_profit_percent: parseFloat(e.target.value) })} className="w-full" />
            <div className="flex justify-between text-xs text-slate-500"><span>10%</span><span>100%</span></div>
          </div>
        </div>
        <div className="flex gap-3 mt-6">
          <Button onClick={onClose} variant="outline" className="flex-1 border-white/20">Cancel</Button>
          <Button onClick={() => onSave(form)} className="flex-1 bg-[#D946EF]">Save Settings</Button>
        </div>
      </div>
    </div>
  );
}
