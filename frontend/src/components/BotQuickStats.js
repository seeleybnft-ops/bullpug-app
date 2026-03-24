import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import axios from "axios";
import { TrendingUp, Target, BarChart3, Users, Bot, Activity } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BotQuickStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const { data } = await axios.get(`${API}/ai-trader/platform-stats`);
        setStats(data);
      } catch (e) {
        console.error("Failed to fetch platform stats:", e);
      }
      setLoading(false);
    };
    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  const statItems = [
    {
      label: "Total Trades",
      value: loading ? "\u2014" : (stats?.total_trades || 0).toLocaleString(),
      icon: <BarChart3 className="w-5 h-5" />,
      color: "#00C2FF",
      glow: "shadow-[0_0_20px_rgba(0,194,255,0.15)]"
    },
    {
      label: "Win Rate",
      value: loading ? "\u2014" : `${stats?.win_rate || 0}%`,
      icon: <TrendingUp className="w-5 h-5" />,
      color: "#00FFA3",
      glow: "shadow-[0_0_20px_rgba(0,255,163,0.15)]"
    },
    {
      label: "Total P/L",
      value: loading ? "\u2014" : `${(stats?.total_pnl_sol || 0) >= 0 ? "+" : ""}${(stats?.total_pnl_sol || 0).toFixed(4)} SOL`,
      icon: <Activity className="w-5 h-5" />,
      color: (stats?.total_pnl_sol || 0) >= 0 ? "#00FFA3" : "#FF6B6B",
      glow: (stats?.total_pnl_sol || 0) >= 0 ? "shadow-[0_0_20px_rgba(0,255,163,0.15)]" : "shadow-[0_0_20px_rgba(255,107,107,0.15)]"
    },
    {
      label: "Active Positions",
      value: loading ? "\u2014" : (stats?.active_positions || 0).toLocaleString(),
      icon: <Target className="w-5 h-5" />,
      color: "#D946EF",
      glow: "shadow-[0_0_20px_rgba(217,70,239,0.15)]"
    },
  ];

  return (
    <section className="py-12 md:py-16" data-testid="bot-quick-stats-section">
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div className="glass-card rounded-2xl p-6 md:p-8 border border-white/5 relative overflow-hidden">
          {/* Subtle background accent */}
          <div className="absolute -top-20 -right-20 w-60 h-60 bg-[#D946EF]/5 rounded-full blur-[80px] pointer-events-none" />
          <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-[#00FFA3]/5 rounded-full blur-[80px] pointer-events-none" />

          {/* Header row */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 relative z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center">
                <Bot className="w-5 h-5 text-black" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                  Trading Bot <span className="text-[#D946EF]">Live Stats</span>
                </h3>
                <p className="text-xs text-slate-500">Platform-wide performance, updated in real-time</p>
              </div>
            </div>
            <Link to="/ai-trader">
              <Button
                className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] text-black font-bold rounded-full px-6 py-4 text-xs uppercase hover:scale-[1.02] transition-transform"
                data-testid="bot-stats-cta"
              >
                <Bot className="w-4 h-4 mr-2" />
                Open Trading Bot
              </Button>
            </Link>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 relative z-10">
            {statItems.map((item, i) => (
              <div
                key={i}
                className={`rounded-xl bg-black/30 border border-white/5 p-4 md:p-5 ${item.glow} hover:border-white/10 transition-all duration-300`}
                data-testid={`bot-stat-${i}`}
              >
                <div className="flex items-center gap-2 mb-3">
                  <span style={{ color: item.color }}>{item.icon}</span>
                  <span className="text-[10px] uppercase tracking-widest text-slate-500" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                    {item.label}
                  </span>
                </div>
                <p
                  className="text-xl md:text-2xl font-black font-mono"
                  style={{ color: item.color }}
                >
                  {item.value}
                </p>
              </div>
            ))}
          </div>

          {/* Active traders footer */}
          {stats?.active_traders > 0 && (
            <div className="mt-4 pt-4 border-t border-white/5 flex items-center gap-2 text-xs text-slate-500 relative z-10">
              <Users className="w-3.5 h-3.5 text-[#D946EF]" />
              <span>{stats.active_traders} active trader{stats.active_traders !== 1 ? "s" : ""} on the platform</span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
