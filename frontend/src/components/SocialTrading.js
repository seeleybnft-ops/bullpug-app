/**
 * SocialTrading Component
 * 
 * Allows users to:
 * - View top trader leaderboard
 * - Follow/unfollow traders
 * - Configure copy trading settings
 * - Track copied trades performance
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Users, TrendingUp, TrendingDown, Crown, Medal, Star,
  UserPlus, UserMinus, Copy, Settings, ChevronDown, ChevronUp,
  Loader2, ExternalLink, BarChart2, Percent, DollarSign,
  Eye, EyeOff, Zap, Shield, Activity, Clock, Check
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Time period options
const PERIODS = [
  { value: '24h', label: '24H' },
  { value: '7d', label: '7D' },
  { value: '30d', label: '30D' },
  { value: 'all', label: 'All' }
];

export default function SocialTrading({ compact = false }) {
  const { publicKey, connected } = useWallet();
  const walletAddress = publicKey?.toBase58();

  const [activeTab, setActiveTab] = useState('leaderboard');
  const [period, setPeriod] = useState('7d');
  const [leaderboard, setLeaderboard] = useState([]);
  const [following, setFollowing] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [copiedTrades, setCopiedTrades] = useState([]);
  const [myProfile, setMyProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [followingWallet, setFollowingWallet] = useState(null);
  const [showFollowModal, setShowFollowModal] = useState(false);
  const [followSettings, setFollowSettings] = useState({
    copy_percentage: 50,
    max_position_sol: 0.1,
    auto_copy_enabled: true
  });

  // Fetch leaderboard
  const fetchLeaderboard = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/social-trading/leaderboard?period=${period}&limit=20`);
      setLeaderboard(data.leaderboard || []);
    } catch (e) {
      console.error('Failed to fetch leaderboard:', e);
    }
  }, [period]);

  // Fetch following list
  const fetchFollowing = useCallback(async () => {
    if (!walletAddress) return;
    try {
      const { data } = await axios.get(`${API}/social-trading/following/${walletAddress}`);
      setFollowing(data.following || []);
    } catch (e) {
      console.error('Failed to fetch following:', e);
    }
  }, [walletAddress]);

  // Fetch followers
  const fetchFollowers = useCallback(async () => {
    if (!walletAddress) return;
    try {
      const { data } = await axios.get(`${API}/social-trading/followers/${walletAddress}`);
      setFollowers(data.followers || []);
    } catch (e) {
      console.error('Failed to fetch followers:', e);
    }
  }, [walletAddress]);

  // Fetch my profile
  const fetchMyProfile = useCallback(async () => {
    if (!walletAddress) return;
    try {
      const { data } = await axios.get(`${API}/social-trading/profile/${walletAddress}`);
      setMyProfile(data);
    } catch (e) {
      console.error('Failed to fetch profile:', e);
    }
  }, [walletAddress]);

  // Fetch copied trades
  const fetchCopiedTrades = useCallback(async () => {
    if (!walletAddress) return;
    try {
      const { data } = await axios.get(`${API}/social-trading/copied-trades/${walletAddress}?limit=20`);
      setCopiedTrades(data.copied_trades || []);
    } catch (e) {
      console.error('Failed to fetch copied trades:', e);
    }
  }, [walletAddress]);

  // Initial fetch
  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      await Promise.all([
        fetchLeaderboard(),
        fetchFollowing(),
        fetchFollowers(),
        fetchMyProfile(),
        fetchCopiedTrades()
      ]);
      setLoading(false);
    };
    fetchAll();
  }, [fetchLeaderboard, fetchFollowing, fetchFollowers, fetchMyProfile, fetchCopiedTrades]);

  // Refetch leaderboard when period changes
  useEffect(() => {
    fetchLeaderboard();
  }, [period, fetchLeaderboard]);

  // Follow a trader
  const followTrader = async (traderWallet) => {
    if (!walletAddress) {
      toast.error('Connect your wallet first');
      return;
    }

    try {
      const { data } = await axios.post(`${API}/social-trading/follow`, {
        follower_wallet: walletAddress,
        trader_wallet: traderWallet,
        ...followSettings
      });

      toast.success(data.message);
      setShowFollowModal(false);
      fetchFollowing();
      fetchLeaderboard();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to follow trader');
    }
  };

  // Unfollow a trader
  const unfollowTrader = async (traderWallet) => {
    if (!walletAddress) return;

    try {
      await axios.post(`${API}/social-trading/unfollow?follower_wallet=${walletAddress}&trader_wallet=${traderWallet}`);
      toast.success('Unfollowed trader');
      fetchFollowing();
      fetchLeaderboard();
    } catch (e) {
      toast.error('Failed to unfollow trader');
    }
  };

  // Enable/disable copy trading on my profile
  const toggleCopyTrading = async (enabled) => {
    if (!walletAddress) return;

    try {
      await axios.post(`${API}/social-trading/profile/enable-copy-trading/${walletAddress}?enabled=${enabled}`);
      toast.success(enabled ? 'Copy trading enabled - others can now copy your trades!' : 'Copy trading disabled');
      fetchMyProfile();
    } catch (e) {
      toast.error('Failed to update copy trading status');
    }
  };

  // Check if already following
  const isFollowing = (traderWallet) => {
    return following.some(f => f.trader_wallet === traderWallet);
  };

  // Format numbers
  const formatPnL = (value) => {
    const prefix = value >= 0 ? '+' : '';
    return `${prefix}${value.toFixed(4)} SOL`;
  };

  const formatPercent = (value) => {
    const prefix = value >= 0 ? '+' : '';
    return `${prefix}${value.toFixed(1)}%`;
  };

  // Get rank badge
  const getRankBadge = (rank) => {
    if (rank === 1) return <Crown className="w-4 h-4 text-[#FFD700]" />;
    if (rank === 2) return <Medal className="w-4 h-4 text-[#C0C0C0]" />;
    if (rank === 3) return <Medal className="w-4 h-4 text-[#CD7F32]" />;
    return <span className="text-xs font-bold text-slate-500">#{rank}</span>;
  };

  if (loading) {
    return (
      <div className="glass-card rounded-2xl p-6 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#D946EF]" />
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-white/10" data-testid="social-trading">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#D946EF]/20 to-[#00C2FF]/20 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#D946EF]/20 flex items-center justify-center">
              <Users className="w-5 h-5 text-[#D946EF]" />
            </div>
            <div>
              <h3 className="font-bold text-white">Copy Trading</h3>
              <p className="text-xs text-slate-400">Follow top traders & copy their moves</p>
            </div>
          </div>
          {connected && myProfile && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Allow copying:</span>
              <button
                onClick={() => toggleCopyTrading(!myProfile.copy_trading_enabled)}
                className={`w-10 h-5 rounded-full transition-colors relative ${
                  myProfile.copy_trading_enabled ? 'bg-[#00FFA3]' : 'bg-slate-600'
                }`}
              >
                <span
                  className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                    myProfile.copy_trading_enabled ? 'left-5' : 'left-0.5'
                  }`}
                />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/10">
        {[
          { id: 'leaderboard', label: 'Top Traders', icon: <BarChart2 className="w-3 h-3" /> },
          { id: 'following', label: `Following (${following.length})`, icon: <Eye className="w-3 h-3" /> },
          { id: 'copied', label: 'Copied Trades', icon: <Copy className="w-3 h-3" /> }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-4 py-3 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
              activeTab === tab.id
                ? 'text-[#D946EF] border-b-2 border-[#D946EF] bg-white/5'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
        <div className="p-4">
          {/* Period Selector */}
          <div className="flex gap-2 mb-4">
            {PERIODS.map(p => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                  period === p.value
                    ? 'bg-[#D946EF] text-white'
                    : 'bg-white/5 text-slate-400 hover:bg-white/10'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Leaderboard List */}
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {leaderboard.length === 0 ? (
              <div className="text-center py-8">
                <Users className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-500 text-sm">No traders found</p>
                <p className="text-slate-600 text-xs">Start trading to appear on the leaderboard!</p>
              </div>
            ) : (
              leaderboard.map((trader, i) => (
                <div
                  key={trader.wallet_address}
                  className={`p-3 rounded-xl border transition-colors ${
                    i < 3
                      ? 'bg-gradient-to-r from-[#FFD700]/10 to-transparent border-[#FFD700]/20'
                      : 'bg-white/5 border-white/10 hover:bg-white/10'
                  }`}
                  data-testid={`trader-${trader.rank}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 text-center">
                        {getRankBadge(trader.rank)}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">
                          {trader.display_name}
                        </p>
                        <p className="text-[10px] text-slate-500 font-mono">
                          {trader.wallet_address.slice(0, 6)}...{trader.wallet_address.slice(-4)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-bold ${trader.total_pnl_sol >= 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                        {formatPnL(trader.total_pnl_sol)}
                      </p>
                      <p className="text-[10px] text-slate-500">
                        {trader.win_rate}% win rate • {trader.total_trades} trades
                      </p>
                    </div>
                  </div>
                  
                  {/* Action buttons */}
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
                    <div className="flex items-center gap-3 text-[10px] text-slate-500">
                      <span className="flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        {trader.followers_count} followers
                      </span>
                      <span>Best: {formatPercent(trader.best_trade_percent)}</span>
                    </div>
                    
                    {connected && trader.wallet_address !== walletAddress && (
                      <div>
                        {isFollowing(trader.wallet_address) ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => unfollowTrader(trader.wallet_address)}
                            className="h-7 text-[10px] border-[#FF6B6B]/30 text-[#FF6B6B] hover:bg-[#FF6B6B]/10"
                          >
                            <UserMinus className="w-3 h-3 mr-1" />
                            Unfollow
                          </Button>
                        ) : trader.copy_trading_enabled ? (
                          <Button
                            size="sm"
                            onClick={() => {
                              setFollowingWallet(trader.wallet_address);
                              setShowFollowModal(true);
                            }}
                            className="h-7 text-[10px] bg-[#D946EF] hover:bg-[#D946EF]/80"
                          >
                            <UserPlus className="w-3 h-3 mr-1" />
                            Follow
                          </Button>
                        ) : (
                          <Badge className="text-[9px] bg-slate-700 text-slate-400">
                            Not accepting copiers
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Following Tab */}
      {activeTab === 'following' && (
        <div className="p-4">
          {!connected ? (
            <div className="text-center py-8">
              <Shield className="w-10 h-10 text-slate-600 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">Connect wallet to see who you're following</p>
            </div>
          ) : following.length === 0 ? (
            <div className="text-center py-8">
              <Eye className="w-10 h-10 text-slate-600 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">Not following any traders yet</p>
              <p className="text-slate-600 text-xs mt-1">Check the leaderboard to find traders to follow!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {following.map((follow) => (
                <div
                  key={follow.trader_wallet}
                  className="p-3 rounded-xl bg-white/5 border border-white/10"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="text-sm font-medium text-white">
                        {follow.trader_display_name}
                      </p>
                      <p className="text-[10px] text-slate-500 font-mono">
                        {follow.trader_wallet.slice(0, 6)}...{follow.trader_wallet.slice(-4)}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => unfollowTrader(follow.trader_wallet)}
                      className="h-7 text-[10px] border-[#FF6B6B]/30 text-[#FF6B6B]"
                    >
                      <UserMinus className="w-3 h-3 mr-1" />
                      Unfollow
                    </Button>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 rounded-lg bg-black/30">
                      <p className="text-[10px] text-slate-500">Copy %</p>
                      <p className="text-sm font-bold text-white">{follow.copy_percentage}%</p>
                    </div>
                    <div className="p-2 rounded-lg bg-black/30">
                      <p className="text-[10px] text-slate-500">Max Position</p>
                      <p className="text-sm font-bold text-white">{follow.max_position_sol} SOL</p>
                    </div>
                    <div className="p-2 rounded-lg bg-black/30">
                      <p className="text-[10px] text-slate-500">Trades Copied</p>
                      <p className="text-sm font-bold text-[#00FFA3]">{follow.trades_copied}</p>
                    </div>
                  </div>
                  
                  {follow.trader_stats && (
                    <div className="mt-2 pt-2 border-t border-white/5 flex items-center gap-4 text-[10px] text-slate-400">
                      <span>{follow.trader_stats.win_rate}% win rate</span>
                      <span className={follow.trader_stats.total_pnl_sol >= 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}>
                        {formatPnL(follow.trader_stats.total_pnl_sol)} total PnL
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Copied Trades Tab */}
      {activeTab === 'copied' && (
        <div className="p-4">
          {!connected ? (
            <div className="text-center py-8">
              <Shield className="w-10 h-10 text-slate-600 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">Connect wallet to see copied trades</p>
            </div>
          ) : copiedTrades.length === 0 ? (
            <div className="text-center py-8">
              <Copy className="w-10 h-10 text-slate-600 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">No copied trades yet</p>
              <p className="text-slate-600 text-xs mt-1">Follow traders to start copying their trades!</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[350px] overflow-y-auto">
              {copiedTrades.map((trade) => (
                <div
                  key={trade.copy_trade_id}
                  className="p-3 rounded-xl bg-white/5 border border-white/10"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        trade.trade_type === 'buy' ? 'bg-[#00FFA3]/20' : 'bg-[#FF6B6B]/20'
                      }`}>
                        {trade.trade_type === 'buy' ? (
                          <TrendingUp className="w-4 h-4 text-[#00FFA3]" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-[#FF6B6B]" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">
                          {trade.trade_type.toUpperCase()} {trade.token_symbol}
                        </p>
                        <p className="text-[10px] text-slate-500">
                          Copied from {trade.trader_wallet.slice(0, 6)}...
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-white">
                        {trade.copied_amount_sol.toFixed(4)} SOL
                      </p>
                      <Badge className={`text-[9px] ${
                        trade.status === 'executed' ? 'bg-[#00FFA3]/20 text-[#00FFA3]' :
                        trade.status === 'pending' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {trade.status}
                      </Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Follow Modal */}
      {showFollowModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="glass-card rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-lg font-bold text-white mb-4">Follow Trader</h3>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 mb-2 block">
                  Copy Percentage: {followSettings.copy_percentage}%
                </label>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="10"
                  value={followSettings.copy_percentage}
                  onChange={(e) => setFollowSettings(s => ({ ...s, copy_percentage: parseInt(e.target.value) }))}
                  className="w-full"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Copy {followSettings.copy_percentage}% of trader's position size
                </p>
              </div>
              
              <div>
                <label className="text-sm text-slate-400 mb-2 block">
                  Max Position: {followSettings.max_position_sol} SOL
                </label>
                <input
                  type="range"
                  min="0.01"
                  max="1"
                  step="0.01"
                  value={followSettings.max_position_sol}
                  onChange={(e) => setFollowSettings(s => ({ ...s, max_position_sol: parseFloat(e.target.value) }))}
                  className="w-full"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Maximum SOL per copied trade
                </p>
              </div>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={followSettings.auto_copy_enabled}
                  onChange={(e) => setFollowSettings(s => ({ ...s, auto_copy_enabled: e.target.checked }))}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm text-slate-300">Auto-copy new trades</span>
              </label>
            </div>
            
            <div className="flex gap-3 mt-6">
              <Button
                variant="outline"
                onClick={() => setShowFollowModal(false)}
                className="flex-1 border-white/20"
              >
                Cancel
              </Button>
              <Button
                onClick={() => followTrader(followingWallet)}
                className="flex-1 bg-[#D946EF] hover:bg-[#D946EF]/80"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                Follow
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
