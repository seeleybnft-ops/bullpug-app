import { useState, useEffect } from "react";
import { Trophy, ExternalLink, PartyPopper, Clock } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RecentWinners() {
  const [winnersData, setWinnersData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentWinners();
    // Refresh every 5 minutes
    const interval = setInterval(fetchRecentWinners, 300000);
    return () => clearInterval(interval);
  }, []);

  const fetchRecentWinners = async () => {
    try {
      const { data } = await axios.get(`${API}/prize-pool/recent-winners`);
      setWinnersData(data);
      setLoading(false);
    } catch (e) {
      console.error("Failed to fetch recent winners:", e);
      setLoading(false);
    }
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const truncateWallet = (wallet) => {
    if (!wallet) return "???";
    return `${wallet.slice(0, 4)}...${wallet.slice(-4)}`;
  };

  const getRankStyle = (rank) => {
    switch (rank) {
      case 1:
        return "bg-gradient-to-r from-[#FFD700] to-[#FFA500] text-black";
      case 2:
        return "bg-gradient-to-r from-[#C0C0C0] to-[#A8A8A8] text-black";
      case 3:
        return "bg-gradient-to-r from-[#CD7F32] to-[#B8860B] text-black";
      default:
        return "bg-white/10 text-white";
    }
  };

  const getRankEmoji = (rank) => {
    switch (rank) {
      case 1: return "🥇";
      case 2: return "🥈";
      case 3: return "🥉";
      default: return `#${rank}`;
    }
  };

  if (loading) {
    return (
      <section className="py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-white/10 rounded w-64 mx-auto mb-8"></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 bg-white/5 rounded-xl"></div>
              ))}
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (!winnersData?.has_winners) {
    return (
      <section className="py-16 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Trophy className="w-8 h-8 text-[#FFD700]" />
            <h2 className="text-2xl md:text-3xl font-bold text-white">RECENT JACKPOT WINNERS</h2>
          </div>
          <p className="text-slate-400 mb-8">No winners yet! Be the first to claim the jackpot.</p>
          <div className="glass-card rounded-2xl p-8 max-w-md mx-auto border border-[#FFD700]/20">
            <PartyPopper className="w-12 h-12 text-[#FFD700] mx-auto mb-4" />
            <p className="text-white font-semibold">First Jackpot Coming Soon!</p>
            <p className="text-sm text-slate-400 mt-2">
              Play Cosmic Runner and climb the leaderboard to win SOL prizes every 3 days!
            </p>
          </div>
        </div>
      </section>
    );
  }

  const { winners, payout_at, total_pool_sol } = winnersData;

  return (
    <section className="py-16 px-4 bg-gradient-to-b from-transparent via-[#FFD700]/5 to-transparent">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center gap-3 mb-2">
            <PartyPopper className="w-8 h-8 text-[#FFD700]" />
            <h2 className="text-2xl md:text-3xl font-bold text-white">RECENT JACKPOT WINNERS</h2>
            <PartyPopper className="w-8 h-8 text-[#FFD700] transform scale-x-[-1]" />
          </div>
          <div className="flex items-center justify-center gap-2 text-slate-400 text-sm">
            <Clock className="w-4 h-4" />
            <span>Paid out on {formatDate(payout_at)}</span>
            <span className="text-[#FFD700] font-bold ml-2">
              {total_pool_sol?.toFixed(4)} SOL Total
            </span>
          </div>
        </div>

        {/* Top 3 Winners - Featured */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {winners.slice(0, 3).map((winner, index) => (
            <div
              key={winner.rank}
              className={`glass-card rounded-2xl p-6 border ${
                winner.rank === 1
                  ? "border-[#FFD700]/50 bg-[#FFD700]/5 md:scale-105 md:-mt-4"
                  : winner.rank === 2
                  ? "border-[#C0C0C0]/50 bg-[#C0C0C0]/5"
                  : "border-[#CD7F32]/50 bg-[#CD7F32]/5"
              }`}
            >
              <div className="text-center">
                <div className="text-4xl mb-2">{getRankEmoji(winner.rank)}</div>
                <h3 className="text-lg font-bold text-white mb-1">
                  {winner.display_name || truncateWallet(winner.wallet_address)}
                </h3>
                <p className="text-xs text-slate-400 mb-3">
                  Score: {winner.high_score?.toLocaleString()}
                </p>
                <div
                  className={`inline-block px-4 py-2 rounded-full ${getRankStyle(winner.rank)} font-bold`}
                >
                  {winner.prize_sol?.toFixed(4)} SOL
                </div>
                <p className="text-xs text-slate-500 mt-2">{winner.percentage}% of pool</p>
                {winner.tx_signature && (
                  <a
                    href={`https://solscan.io/tx/${winner.tx_signature}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#00FFA3] hover:underline flex items-center justify-center gap-1 mt-2"
                  >
                    View TX <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Remaining Winners (4-10) */}
        {winners.length > 3 && (
          <div className="glass-card rounded-xl overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-white/5">
              {winners.slice(3, 10).map((winner) => (
                <div
                  key={winner.rank}
                  className="bg-black/40 p-4 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getRankStyle(
                        winner.rank
                      )}`}
                    >
                      {winner.rank}
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {winner.display_name || truncateWallet(winner.wallet_address)}
                      </p>
                      <p className="text-xs text-slate-500">
                        Score: {winner.high_score?.toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-[#00FFA3]">
                      {winner.prize_sol?.toFixed(4)} SOL
                    </p>
                    <p className="text-xs text-slate-500">{winner.percentage}%</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
