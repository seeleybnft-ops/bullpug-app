import { useState, useEffect } from "react";
import { Trophy, Clock, Coins, ChevronDown, ChevronUp } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Prize distribution percentages
const PRIZE_DISTRIBUTION = [
  { rank: 1, percentage: 25, emoji: "🥇" },
  { rank: 2, percentage: 15, emoji: "🥈" },
  { rank: 3, percentage: 12, emoji: "🥉" },
  { rank: 4, percentage: 10, emoji: "4️⃣" },
  { rank: 5, percentage: 9, emoji: "5️⃣" },
  { rank: 6, percentage: 8, emoji: "6️⃣" },
  { rank: 7, percentage: 7, emoji: "7️⃣" },
  { rank: 8, percentage: 6, emoji: "8️⃣" },
  { rank: 9, percentage: 5, emoji: "9️⃣" },
  { rank: 10, percentage: 3, emoji: "🔟" },
];

export default function JackpotDisplay({ compact = false }) {
  const [prizePool, setPrizePool] = useState(null);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPrizePool();
    const interval = setInterval(fetchPrizePool, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (timeRemaining > 0) {
      const timer = setInterval(() => {
        setTimeRemaining((prev) => Math.max(0, prev - 1));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [timeRemaining]);

  const fetchPrizePool = async () => {
    try {
      const { data } = await axios.get(`${API}/prize-pool/status`);
      setPrizePool(data);
      setTimeRemaining(data.seconds_remaining);
      setLoading(false);
    } catch (e) {
      console.error("Failed to fetch prize pool:", e);
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (days > 0) {
      return `${days}d ${hours.toString().padStart(2, "0")}h ${minutes.toString().padStart(2, "0")}m ${secs.toString().padStart(2, "0")}s`;
    }
    if (hours > 0) {
      return `${hours.toString().padStart(2, "0")}h ${minutes.toString().padStart(2, "0")}m ${secs.toString().padStart(2, "0")}s`;
    }
    return `${minutes.toString().padStart(2, "0")}m ${secs.toString().padStart(2, "0")}s`;
  };

  if (loading) {
    return (
      <div className="glass-card rounded-xl p-4 animate-pulse">
        <div className="h-6 bg-white/10 rounded w-1/2 mb-2"></div>
        <div className="h-8 bg-white/10 rounded w-3/4"></div>
      </div>
    );
  }

  if (!prizePool) return null;

  const totalSol = prizePool.total_sol || 0;

  if (compact) {
    return (
      <div className="glass-card rounded-xl p-4 border border-[#FFD700]/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-[#FFD700]" />
            <span className="text-sm text-slate-400">Jackpot</span>
          </div>
          <div className="text-right">
            <p className="text-lg font-black text-[#FFD700]" style={{ fontFamily: "Orbitron" }}>
              {totalSol.toFixed(4)} SOL
            </p>
            <p className="text-xs text-slate-500 flex items-center gap-1 justify-end">
              <Clock className="w-3 h-3" />
              {formatTime(timeRemaining)}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-[#FFD700]/20">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#FFD700]/20 to-[#FF6B35]/20 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-[#FFD700]/20 flex items-center justify-center">
              <Trophy className="w-6 h-6 text-[#FFD700]" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">LEADERBOARD JACKPOT</h3>
              <p className="text-xs text-slate-400">Top 10 winners every 3 days</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-3xl font-black text-[#FFD700]" style={{ fontFamily: "Orbitron", textShadow: "0 0 20px rgba(255,215,0,0.5)" }}>
              {totalSol.toFixed(4)}
            </p>
            <p className="text-xs text-slate-400">SOL</p>
          </div>
        </div>
      </div>

      {/* Countdown Timer */}
      <div className="bg-black/40 p-4 border-t border-white/5">
        <div className="flex items-center justify-center gap-2 text-center">
          <Clock className="w-5 h-5 text-[#00FFA3]" />
          <span className="text-sm text-slate-400">Next Payout In:</span>
          <span
            className="text-xl font-mono font-bold text-[#00FFA3]"
            style={{ fontFamily: "Orbitron" }}
          >
            {formatTime(timeRemaining)}
          </span>
        </div>
      </div>

      {/* Prize Breakdown Toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 transition-colors border-t border-white/5"
      >
        <Coins className="w-4 h-4" />
        Prize Breakdown
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* Prize Breakdown */}
      {expanded && (
        <div className="p-4 border-t border-white/5 bg-black/20">
          <div className="grid grid-cols-2 gap-2">
            {PRIZE_DISTRIBUTION.map((prize) => (
              <div
                key={prize.rank}
                className={`flex items-center justify-between p-2 rounded-lg ${
                  prize.rank <= 3 ? "bg-[#FFD700]/10" : "bg-white/5"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{prize.emoji}</span>
                  <span className="text-sm text-slate-400">#{prize.rank}</span>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-500">{prize.percentage}%</span>
                  <p className={`text-sm font-bold ${prize.rank <= 3 ? "text-[#FFD700]" : "text-white"}`}>
                    {(totalSol * prize.percentage / 100).toFixed(4)} SOL
                  </p>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 text-center mt-3">
            Funded by skin purchases
          </p>
        </div>
      )}
    </div>
  );
}
