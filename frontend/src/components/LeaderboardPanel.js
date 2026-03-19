/**
 * LeaderboardPanel Component
 * 
 * Enhanced leaderboard display with:
 * - Wallet linking for prize eligibility
 * - Prize distribution preview
 * - User rank highlighting
 * - Recent winners display
 */

import { useState, useEffect } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useAccount } from "wagmi";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import {
  Trophy, Link2, Unlink, Crown, Medal, Star, 
  ChevronDown, ChevronUp, Wallet, Check, Copy,
  Sparkles, Clock, Gift
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Prize distribution percentages
const PRIZE_DISTRIBUTION = {
  1: { percent: 25, color: "#FFD700", label: "1st" },
  2: { percent: 15, color: "#C0C0C0", label: "2nd" },
  3: { percent: 12, color: "#CD7F32", label: "3rd" },
  4: { percent: 10, color: "#00FFA3", label: "4th" },
  5: { percent: 9, color: "#00FFA3", label: "5th" },
  6: { percent: 8, color: "#00C2FF", label: "6th" },
  7: { percent: 7, color: "#00C2FF", label: "7th" },
  8: { percent: 6, color: "#D946EF", label: "8th" },
  9: { percent: 5, color: "#D946EF", label: "9th" },
  10: { percent: 3, color: "#9945FF", label: "10th" },
};

export default function LeaderboardPanel({ 
  leaderboard = [], 
  playerName, 
  onRefresh,
  compact = false 
}) {
  const { publicKey: solanaPublicKey, connected: solanaConnected } = useWallet();
  const { address: evmAddress, isConnected: evmConnected } = useAccount();
  
  const [expanded, setExpanded] = useState(!compact);
  const [linking, setLinking] = useState(false);
  const [walletLinked, setWalletLinked] = useState(false);
  const [linkedWallet, setLinkedWallet] = useState(null);
  const [recentWinners, setRecentWinners] = useState([]);
  const [prizePool, setPrizePool] = useState(0);
  const [showWinners, setShowWinners] = useState(false);

  const walletAddress = solanaConnected 
    ? solanaPublicKey?.toBase58() 
    : (evmConnected ? evmAddress : null);

  // Fetch linked wallet status
  useEffect(() => {
    if (playerName) {
      checkWalletLink();
    }
    fetchRecentWinners();
    fetchPrizePool();
  }, [playerName]);

  const checkWalletLink = async () => {
    try {
      const { data } = await axios.get(`${API}/leaderboard/wallet-link/${encodeURIComponent(playerName)}`);
      setWalletLinked(!!data.wallet_address);
      setLinkedWallet(data.wallet_address);
    } catch (e) {
      setWalletLinked(false);
      setLinkedWallet(null);
    }
  };

  const fetchRecentWinners = async () => {
    try {
      const { data } = await axios.get(`${API}/prize-pool/recent-winners`);
      if (data.winners) {
        setRecentWinners(data.winners.slice(0, 5));
      }
    } catch (e) {
      console.error("Failed to fetch winners:", e);
    }
  };

  const fetchPrizePool = async () => {
    try {
      const { data } = await axios.get(`${API}/prize-pool/status`);
      setPrizePool(data.total_sol || 0);
    } catch (e) {
      console.error("Failed to fetch prize pool:", e);
    }
  };

  const linkWallet = async () => {
    if (!walletAddress) {
      toast.error("Connect a wallet first to link for prizes");
      return;
    }
    
    setLinking(true);
    try {
      await axios.post(`${API}/leaderboard/link-wallet`, {
        player_name: playerName,
        wallet_address: walletAddress
      });
      setWalletLinked(true);
      setLinkedWallet(walletAddress);
      toast.success("Wallet linked! You're now eligible for prizes.");
      onRefresh?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to link wallet");
    }
    setLinking(false);
  };

  const unlinkWallet = async () => {
    setLinking(true);
    try {
      await axios.post(`${API}/leaderboard/unlink-wallet`, {
        player_name: playerName
      });
      setWalletLinked(false);
      setLinkedWallet(null);
      toast.success("Wallet unlinked");
      onRefresh?.();
    } catch (e) {
      toast.error("Failed to unlink wallet");
    }
    setLinking(false);
  };

  // Find user's rank
  const userRank = leaderboard.findIndex(e => e.player_name === playerName) + 1;
  const userEntry = leaderboard.find(e => e.player_name === playerName);
  const isEligible = userRank > 0 && userRank <= 10;
  const userPrize = isEligible ? (prizePool * PRIZE_DISTRIBUTION[userRank]?.percent / 100) : 0;

  const getRankIcon = (rank) => {
    if (rank === 1) return <Crown className="w-4 h-4 text-[#FFD700]" />;
    if (rank === 2) return <Medal className="w-4 h-4 text-[#C0C0C0]" />;
    if (rank === 3) return <Medal className="w-4 h-4 text-[#CD7F32]" />;
    return <span className="text-xs font-bold text-slate-400">#{rank}</span>;
  };

  const copyAddress = async (address) => {
    try {
      await navigator.clipboard.writeText(address);
      toast.success("Address copied!");
    } catch (e) {
      toast.error("Failed to copy");
    }
  };

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-white/10" data-testid="leaderboard-panel">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#FFD700]/20 flex items-center justify-center">
            <Trophy className="w-5 h-5 text-[#FFD700]" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold text-white">LEADERBOARD</h3>
            <p className="text-xs text-slate-500">
              {prizePool > 0 ? `${prizePool.toFixed(4)} SOL prize pool` : "Play to rank!"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {userRank > 0 && (
            <Badge 
              className="text-[10px]"
              style={{ 
                backgroundColor: `${PRIZE_DISTRIBUTION[userRank]?.color || '#666'}20`,
                color: PRIZE_DISTRIBUTION[userRank]?.color || '#666',
                borderColor: `${PRIZE_DISTRIBUTION[userRank]?.color || '#666'}40`
              }}
            >
              #{userRank}
            </Badge>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/5">
          {/* Wallet Link Status */}
          <div className="p-3 bg-black/40 border-b border-white/5">
            {walletLinked ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-[#00FFA3]" />
                  <span className="text-xs text-[#00FFA3]">Wallet Linked</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500 font-mono">
                    {linkedWallet?.slice(0, 6)}...{linkedWallet?.slice(-4)}
                  </span>
                  <button
                    onClick={() => copyAddress(linkedWallet)}
                    className="p-1 rounded hover:bg-white/10"
                  >
                    <Copy className="w-3 h-3 text-slate-400" />
                  </button>
                  <button
                    onClick={unlinkWallet}
                    disabled={linking}
                    className="p-1 rounded hover:bg-red-500/20 text-red-400"
                    title="Unlink wallet"
                  >
                    <Unlink className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wallet className="w-4 h-4 text-amber-400" />
                  <span className="text-xs text-amber-400">Link wallet for prizes</span>
                </div>
                <Button
                  onClick={linkWallet}
                  disabled={linking || !walletAddress}
                  size="sm"
                  className="h-7 text-[10px] bg-[#FFD700] text-black hover:bg-[#FFD700]/80"
                >
                  {linking ? "..." : walletAddress ? <><Link2 className="w-3 h-3 mr-1" /> Link</> : "Connect Wallet"}
                </Button>
              </div>
            )}
          </div>

          {/* User Prize Eligibility */}
          {isEligible && prizePool > 0 && (
            <div className="p-3 bg-gradient-to-r from-[#FFD700]/10 to-transparent border-b border-white/5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Gift className="w-4 h-4 text-[#FFD700]" />
                  <span className="text-xs text-[#FFD700]">Your potential prize:</span>
                </div>
                <span className="text-sm font-bold text-[#FFD700]" style={{ fontFamily: 'Orbitron' }}>
                  {userPrize.toFixed(4)} SOL
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                {walletLinked ? "Prize will be sent automatically at payout" : "Link wallet to receive prizes"}
              </p>
            </div>
          )}

          {/* Leaderboard List */}
          <div className="p-3 space-y-1.5 max-h-[280px] overflow-y-auto">
            {leaderboard.slice(0, 10).map((entry, i) => {
              const rank = i + 1;
              const prizeInfo = PRIZE_DISTRIBUTION[rank];
              const isUser = entry.player_name === playerName;
              const prize = prizePool * prizeInfo.percent / 100;
              
              return (
                <div
                  key={i}
                  className={`flex items-center justify-between p-2.5 rounded-lg transition-colors ${
                    isUser 
                      ? 'bg-gradient-to-r from-[#FFD700]/20 to-[#00FFA3]/10 border border-[#FFD700]/30' 
                      : rank <= 3 
                        ? 'bg-gradient-to-r from-white/5 to-transparent' 
                        : 'bg-white/5 hover:bg-white/10'
                  }`}
                  data-testid={`leaderboard-entry-${rank}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 text-center">
                      {getRankIcon(rank)}
                    </div>
                    <div>
                      <p className={`text-sm font-medium ${isUser ? 'text-[#FFD700]' : 'text-white'}`}>
                        {entry.player_name}
                        {isUser && <span className="text-[10px] text-slate-400 ml-1">(You)</span>}
                      </p>
                      {entry.wallet_address && (
                        <p className="text-[9px] text-slate-500 font-mono">
                          {entry.wallet_address.slice(0, 4)}...{entry.wallet_address.slice(-4)}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold" style={{ color: prizeInfo.color }}>
                      {entry.score?.toLocaleString()}
                    </p>
                    {prizePool > 0 && (
                      <p className="text-[10px] text-slate-500">
                        {prize.toFixed(3)} SOL ({prizeInfo.percent}%)
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
            
            {leaderboard.length === 0 && (
              <div className="text-center py-6">
                <Star className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                <p className="text-sm text-slate-500">No scores yet</p>
                <p className="text-xs text-slate-600">Be the first to play!</p>
              </div>
            )}
          </div>

          {/* Recent Winners Toggle */}
          {recentWinners.length > 0 && (
            <>
              <button
                onClick={() => setShowWinners(!showWinners)}
                className="w-full p-2 flex items-center justify-center gap-2 text-xs text-slate-400 hover:text-white hover:bg-white/5 transition-colors border-t border-white/5"
              >
                <Sparkles className="w-3 h-3" />
                Recent Winners
                {showWinners ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
              
              {showWinners && (
                <div className="p-3 border-t border-white/5 bg-black/20 space-y-2">
                  {recentWinners.map((winner, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-[#FFD700]">#{winner.rank}</span>
                        <span className="text-slate-400">{winner.display_name}</span>
                      </div>
                      <span className="text-[#00FFA3] font-mono">
                        +{winner.prize_sol?.toFixed(4)} SOL
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
