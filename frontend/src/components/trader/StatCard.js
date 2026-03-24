import { TrendingUp, TrendingDown, History, DollarSign, Target } from "lucide-react";

export function StatCard({ icon, label, value, color, testId }) {
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/5 hover:border-white/10 transition-colors" data-testid={testId}>
      <div className="flex items-center gap-2 text-slate-400 mb-2">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-xl font-bold" style={{ color }}>{value}</p>
    </div>
  );
}
