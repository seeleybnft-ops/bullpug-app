/**
 * Achievement Badges Component
 * 
 * Displays user's earned badges, progress toward new badges,
 * and allows sharing achievements on X (Twitter).
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import axios from 'axios';
import { toPng } from 'html-to-image';
import {
  Award, Trophy, Share2, Twitter, Download, Lock, Unlock,
  TrendingUp, Zap, Star, Crown, Target, Users, Eye, EyeOff,
  ChevronRight, Loader2, Check, Copy
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Rarity colors
const RARITY_COLORS = {
  common: { bg: '#00FFA3', text: '#000' },
  rare: { bg: '#00C2FF', text: '#000' },
  epic: { bg: '#D946EF', text: '#fff' },
  legendary: { bg: '#F5D300', text: '#000' },
};

const RARITY_GLOW = {
  common: '0 0 20px rgba(0, 255, 163, 0.3)',
  rare: '0 0 20px rgba(0, 194, 255, 0.3)',
  epic: '0 0 20px rgba(217, 70, 239, 0.4)',
  legendary: '0 0 30px rgba(245, 211, 0, 0.5)',
};

export default function AchievementBadges() {
  const { publicKey, connected } = useWallet();
  const [achievements, setAchievements] = useState(null);
  const [allBadges, setAllBadges] = useState([]);
  const [benchmarks, setBenchmarks] = useState(null);
  const [optIn, setOptIn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showShareCard, setShowShareCard] = useState(false);
  const [shareData, setShareData] = useState(null);
  const [scanningWallet, setScanningWallet] = useState(false);
  const shareCardRef = useRef(null);

  // Fetch user achievements and scan for new badges
  const fetchAchievements = useCallback(async () => {
    if (!connected || !publicKey) return;
    
    setLoading(true);
    try {
      const [achieveRes, badgesRes, optInRes] = await Promise.all([
        axios.get(`${API}/achievements/user/${publicKey.toBase58()}`),
        axios.get(`${API}/achievements/badges`),
        axios.get(`${API}/achievements/opt-in/${publicKey.toBase58()}`)
      ]);
      
      setAchievements(achieveRes.data);
      setAllBadges(badgesRes.data.badges);
      setOptIn(optInRes.data.opt_in);
      
      // Show toast for new badges
      if (achieveRes.data.new_badges?.length > 0) {
        achieveRes.data.new_badges.forEach(badge => {
          toast.success(`New Badge Earned: ${badge.name}!`, {
            description: badge.description,
            duration: 5000,
          });
        });
      }
    } catch (e) {
      console.error('Error fetching achievements:', e);
    }
    setLoading(false);
  }, [connected, publicKey]);

  // Scan wallet and calculate achievements from trades
  const scanWalletForAchievements = useCallback(async () => {
    if (!connected || !publicKey) return;
    
    setScanningWallet(true);
    try {
      // Trigger a full scan by fetching user achievements
      // The backend will recalculate from all journal trades
      const { data } = await axios.get(`${API}/achievements/user/${publicKey.toBase58()}`);
      
      setAchievements(data);
      
      // Show summary toast
      if (data.stats?.total_trades > 0) {
        toast.success(`Wallet Scanned: ${data.stats.total_trades} trades analyzed`, {
          description: `${data.total_badges} badges earned, ${data.stats.win_rate}% win rate`,
        });
      }
      
      // Show new badges if any
      if (data.new_badges?.length > 0) {
        data.new_badges.forEach(badge => {
          setTimeout(() => {
            toast.success(`Badge Unlocked: ${badge.name}!`, {
              description: badge.description,
              icon: badge.icon,
              duration: 6000,
            });
          }, 500);
        });
      }
    } catch (e) {
      console.error('Error scanning wallet:', e);
      toast.error('Failed to scan wallet for achievements');
    }
    setScanningWallet(false);
  }, [connected, publicKey]);

  // Fetch community benchmarks
  const fetchBenchmarks = useCallback(async () => {
    try {
      const params = connected && publicKey ? `?wallet_address=${publicKey.toBase58()}` : '';
      const { data } = await axios.get(`${API}/achievements/community/benchmarks${params}`);
      setBenchmarks(data);
    } catch (e) {
      console.error('Error fetching benchmarks:', e);
    }
  }, [connected, publicKey]);

  useEffect(() => {
    fetchAchievements();
    fetchBenchmarks();
  }, [fetchAchievements, fetchBenchmarks]);

  // Auto-scan wallet on initial connection
  useEffect(() => {
    if (connected && publicKey && !achievements) {
      // Small delay to ensure wallet is fully connected
      const timer = setTimeout(() => {
        scanWalletForAchievements();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [connected, publicKey, achievements, scanWalletForAchievements]);

  // Toggle community opt-in
  const toggleOptIn = async (value) => {
    if (!connected || !publicKey) return;
    
    try {
      await axios.post(`${API}/achievements/opt-in`, {
        wallet_address: publicKey.toBase58(),
        opt_in: value
      });
      setOptIn(value);
      toast.success(value ? 'Opted in to community benchmarks' : 'Opted out of community benchmarks');
      fetchBenchmarks();
    } catch (e) {
      toast.error('Failed to update opt-in status');
    }
  };

  // Prepare share data
  const prepareShare = async () => {
    if (!connected || !publicKey) return;
    
    try {
      const { data } = await axios.get(`${API}/achievements/share-data/${publicKey.toBase58()}`);
      setShareData(data);
      setShowShareCard(true);
    } catch (e) {
      toast.error('Failed to load share data');
    }
  };

  // Download share card as image
  const downloadShareCard = async () => {
    if (!shareCardRef.current) return;
    
    try {
      const dataUrl = await toPng(shareCardRef.current, { quality: 0.95 });
      const link = document.createElement('a');
      link.download = 'bullpug-stats.png';
      link.href = dataUrl;
      link.click();
      toast.success('Image downloaded!');
    } catch (e) {
      toast.error('Failed to generate image');
    }
  };

  // Share to X (Twitter)
  const shareToX = () => {
    if (!shareData) return;
    
    const text = encodeURIComponent(shareData.share_text);
    const url = `https://twitter.com/intent/tweet?text=${text}`;
    window.open(url, '_blank', 'width=550,height=420');
  };

  if (!connected) {
    return (
      <div className="glass-card rounded-2xl p-8 text-center border border-white/5">
        <Award className="w-12 h-12 mx-auto mb-4 text-slate-600" />
        <p className="text-slate-500 text-sm">Connect wallet to view achievements</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Trophy className="w-5 h-5 text-[#F5D300]" />
            Achievements
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            {achievements?.total_badges || 0} / {achievements?.available_badges || 0} badges earned
          </p>
        </div>
        
        <Button
          onClick={prepareShare}
          disabled={!achievements?.stats?.total_trades}
          className="bg-[#1DA1F2]/10 text-[#1DA1F2] border border-[#1DA1F2]/30 hover:bg-[#1DA1F2]/20 rounded-xl"
        >
          <Share2 className="w-4 h-4 mr-2" />
          Share Stats
        </Button>
      </div>

      {/* Stats Summary */}
      {achievements?.stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            icon={<TrendingUp className="w-4 h-4" />}
            label="Current Streak"
            value={`${achievements.stats.current_win_streak} days`}
            color="#00FFA3"
          />
          <StatCard
            icon={<Star className="w-4 h-4" />}
            label="Best Streak"
            value={`${achievements.stats.best_win_streak} days`}
            color="#F5D300"
          />
          <StatCard
            icon={<Target className="w-4 h-4" />}
            label="Win Rate"
            value={`${achievements.stats.win_rate}%`}
            color="#00C2FF"
          />
          <StatCard
            icon={<Zap className="w-4 h-4" />}
            label="Total PnL"
            value={`$${achievements.stats.total_pnl.toLocaleString()}`}
            color={achievements.stats.total_pnl >= 0 ? '#00FFA3' : '#FF6B6B'}
          />
        </div>
      )}

      {/* Badges Grid */}
      <div className="glass-card rounded-2xl p-5 border border-white/5">
        <h4 className="text-sm font-bold uppercase text-[#00C2FF] mb-4 flex items-center gap-2">
          <Award className="w-4 h-4" />
          Your Badges
        </h4>
        
        {loading ? (
          <div className="py-8 text-center">
            <Loader2 className="w-6 h-6 mx-auto animate-spin text-slate-500" />
          </div>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
            {allBadges.map((badge) => {
              const earned = achievements?.badges?.find(b => b.id === badge.id);
              const rarity = RARITY_COLORS[badge.rarity];
              
              return (
                <div
                  key={badge.id}
                  className={`relative p-3 rounded-xl text-center transition-all ${
                    earned 
                      ? 'bg-white/5 border border-white/10 hover:border-white/20' 
                      : 'bg-black/30 border border-white/5 opacity-40'
                  }`}
                  style={earned ? { boxShadow: RARITY_GLOW[badge.rarity] } : {}}
                  title={badge.description}
                >
                  <div className="text-2xl mb-1">{badge.icon}</div>
                  <p className="text-[10px] font-bold text-white truncate">{badge.name}</p>
                  <Badge 
                    className="mt-1 text-[8px] px-1.5"
                    style={{ 
                      backgroundColor: `${rarity.bg}20`,
                      color: rarity.bg,
                      border: `1px solid ${rarity.bg}40`
                    }}
                  >
                    {badge.rarity}
                  </Badge>
                  
                  {!earned && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/60 rounded-xl">
                      <Lock className="w-4 h-4 text-slate-500" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Community Benchmarks */}
      <div className="glass-card rounded-2xl p-5 border border-white/5">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-bold uppercase text-[#D946EF] flex items-center gap-2">
            <Users className="w-4 h-4" />
            Community Benchmarks
          </h4>
          
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Share my stats anonymously</span>
            <Switch
              checked={optIn}
              onCheckedChange={toggleOptIn}
              className="data-[state=checked]:bg-[#00FFA3]"
            />
          </div>
        </div>

        {benchmarks && benchmarks.total_users > 0 ? (
          <div className="space-y-4">
            {/* User's percentile */}
            {benchmarks.percentile_win_rate !== null && (
              <div className="bg-gradient-to-r from-[#00C2FF]/10 to-[#D946EF]/10 rounded-xl p-4 border border-white/5">
                <p className="text-sm text-white">
                  Your win rate puts you in the{' '}
                  <span className="font-bold text-[#00FFA3]">top {100 - benchmarks.percentile_win_rate}%</span>
                  {' '}of traders
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Your streak is better than {benchmarks.percentile_streak}% of the community
                </p>
              </div>
            )}

            {/* Community stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-black/30 rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-white">{benchmarks.total_users}</p>
                <p className="text-[10px] text-slate-500">Active Traders</p>
              </div>
              <div className="bg-black/30 rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-white">{benchmarks.average_win_rate.toFixed(1)}%</p>
                <p className="text-[10px] text-slate-500">Avg Win Rate</p>
              </div>
              <div className="bg-black/30 rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-white">{benchmarks.average_streak.toFixed(1)}</p>
                <p className="text-[10px] text-slate-500">Avg Win Streak</p>
              </div>
              <div className="bg-black/30 rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-white">{benchmarks.total_trades.toLocaleString()}</p>
                <p className="text-[10px] text-slate-500">Total Trades</p>
              </div>
            </div>

            {/* Top streaks */}
            {benchmarks.top_streaks?.length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-2">Top Win Streaks</p>
                <div className="space-y-1">
                  {benchmarks.top_streaks.slice(0, 5).map((entry, i) => (
                    <div key={i} className="flex items-center justify-between py-1.5 px-3 bg-black/20 rounded-lg">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold ${i === 0 ? 'text-[#F5D300]' : i === 1 ? 'text-slate-300' : i === 2 ? 'text-amber-600' : 'text-slate-500'}`}>
                          #{entry.rank}
                        </span>
                        <span className="text-xs text-white">{entry.streak}-day streak</span>
                      </div>
                      <span className="text-[10px] text-slate-500">{entry.win_rate}% WR</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-6 text-center">
            <Users className="w-8 h-8 mx-auto mb-2 text-slate-700" />
            <p className="text-sm text-slate-500">No community data yet</p>
            <p className="text-xs text-slate-600 mt-1">Be the first to opt-in!</p>
          </div>
        )}
      </div>

      {/* Share Card Modal */}
      {showShareCard && shareData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
          <div className="bg-[#0a0a12] rounded-2xl border border-white/10 p-6 max-w-lg w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white">Share Your Stats</h3>
              <button 
                onClick={() => setShowShareCard(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* Share Card Preview */}
            <div
              ref={shareCardRef}
              className="bg-gradient-to-br from-[#0a0a12] to-[#1a1a2e] rounded-xl p-6 border border-white/10"
              style={{ fontFamily: 'system-ui, sans-serif' }}
            >
              <div className="flex items-center gap-3 mb-4">
                <img src="/logo.png" alt="BullPug" className="w-10 h-10 rounded-full" />
                <div>
                  <p className="font-bold text-white">BULLPUG JOURNAL</p>
                  <p className="text-xs text-slate-400">Trading Stats</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-black/30 rounded-lg p-3 text-center">
                  <p className="text-2xl font-black text-[#00FFA3]">{shareData.stats.best_streak}</p>
                  <p className="text-[10px] text-slate-400">DAY WIN STREAK</p>
                </div>
                <div className="bg-black/30 rounded-lg p-3 text-center">
                  <p className="text-2xl font-black text-[#00C2FF]">{shareData.stats.win_rate}%</p>
                  <p className="text-[10px] text-slate-400">WIN RATE</p>
                </div>
              </div>

              <div className="bg-black/30 rounded-lg p-3 text-center mb-4">
                <p className={`text-3xl font-black ${shareData.stats.total_pnl >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                  {shareData.stats.total_pnl >= 0 ? '+' : ''}${shareData.stats.total_pnl.toLocaleString()}
                </p>
                <p className="text-[10px] text-slate-400">TOTAL P&L</p>
              </div>

              {shareData.best_badge && (
                <div className="flex items-center justify-center gap-2 bg-black/30 rounded-lg p-2">
                  <span className="text-xl">{shareData.best_badge.icon}</span>
                  <span className="text-sm font-bold text-white">{shareData.best_badge.name}</span>
                </div>
              )}

              <p className="text-center text-[10px] text-slate-500 mt-4">
                bullpug.com/journal
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-4">
              <Button
                onClick={downloadShareCard}
                variant="outline"
                className="flex-1 border-white/20 text-white"
              >
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
              <Button
                onClick={shareToX}
                className="flex-1 bg-[#1DA1F2] hover:bg-[#1DA1F2]/80 text-white"
              >
                <Twitter className="w-4 h-4 mr-2" />
                Share on X
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Stat Card Component
function StatCard({ icon, label, value, color }) {
  return (
    <div className="bg-black/30 rounded-xl p-3 border border-white/5">
      <div className="flex items-center gap-2 mb-1" style={{ color }}>
        {icon}
        <span className="text-[10px] text-slate-500 uppercase">{label}</span>
      </div>
      <p className="text-lg font-bold text-white">{value}</p>
    </div>
  );
}
