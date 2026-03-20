/**
 * MultiChainCopyTrading Component
 * 
 * Manages copy trading across multiple chains (Solana, Ethereum, Base, Arbitrum)
 * - Link wallets across chains
 * - Configure per-chain copy settings
 * - View multi-chain leaderboard
 * - Track copied trades across chains
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Link2, Unlink, Users, TrendingUp, TrendingDown, Copy, Settings,
  Loader2, RefreshCw, ChevronDown, ChevronUp, ExternalLink, Check,
  Wallet, Globe, Zap, AlertCircle, DollarSign
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Chain configurations with colors and icons
const CHAIN_CONFIG = {
  solana: {
    name: 'Solana',
    symbol: 'SOL',
    color: '#9945FF',
    bgClass: 'bg-[#9945FF]/20',
    textClass: 'text-[#9945FF]',
    explorer: 'https://solscan.io/account/'
  },
  ethereum: {
    name: 'Ethereum',
    symbol: 'ETH',
    color: '#627EEA',
    bgClass: 'bg-[#627EEA]/20',
    textClass: 'text-[#627EEA]',
    explorer: 'https://etherscan.io/address/'
  },
  base: {
    name: 'Base',
    symbol: 'ETH',
    color: '#0052FF',
    bgClass: 'bg-[#0052FF]/20',
    textClass: 'text-[#0052FF]',
    explorer: 'https://basescan.org/address/'
  },
  arbitrum: {
    name: 'Arbitrum',
    symbol: 'ETH',
    color: '#28A0F0',
    bgClass: 'bg-[#28A0F0]/20',
    textClass: 'text-[#28A0F0]',
    explorer: 'https://arbiscan.io/address/'
  }
};

export default function MultiChainCopyTrading() {
  const { publicKey, connected } = useWallet();
  const solanaAddress = publicKey?.toBase58();

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('wallets');
  
  // Wallet linking state
  const [linkedWallets, setLinkedWallets] = useState(null);
  const [evmAddress, setEvmAddress] = useState('');
  const [linkingWallet, setLinkingWallet] = useState(false);
  
  // Following state
  const [following, setFollowing] = useState([]);
  const [copiedTrades, setCopiedTrades] = useState([]);
  const [stats, setStats] = useState(null);
  
  // Leaderboard state
  const [leaderboard, setLeaderboard] = useState([]);
  const [leaderboardPeriod, setLeaderboardPeriod] = useState('7d');
  const [leaderboardChain, setLeaderboardChain] = useState('all');

  // Fetch linked wallets
  const fetchLinkedWallets = useCallback(async () => {
    if (!solanaAddress) return;
    
    try {
      const { data } = await axios.get(`${API}/multichain-copy/wallets/${solanaAddress}`);
      setLinkedWallets(data);
      if (data.wallets?.ethereum) {
        setEvmAddress(data.wallets.ethereum);
      }
    } catch (e) {
      console.error('Failed to fetch linked wallets:', e);
    }
  }, [solanaAddress]);

  // Fetch following and stats
  const fetchFollowingData = useCallback(async () => {
    if (!linkedWallets?.user_id) return;
    
    try {
      const [followingRes, statsRes, tradesRes] = await Promise.all([
        axios.get(`${API}/multichain-copy/following/${linkedWallets.user_id}`),
        axios.get(`${API}/multichain-copy/stats/${linkedWallets.user_id}`),
        axios.get(`${API}/multichain-copy/copied-trades/${linkedWallets.user_id}?limit=50`)
      ]);
      
      setFollowing(followingRes.data.following || []);
      setStats(statsRes.data);
      setCopiedTrades(tradesRes.data.copied_trades || []);
    } catch (e) {
      console.error('Failed to fetch following data:', e);
    }
  }, [linkedWallets?.user_id]);

  // Fetch leaderboard
  const fetchLeaderboard = useCallback(async () => {
    try {
      const chainParam = leaderboardChain === 'all' ? '' : `&chain=${leaderboardChain}`;
      const { data } = await axios.get(
        `${API}/multichain-copy/leaderboard?period=${leaderboardPeriod}${chainParam}&limit=20`
      );
      setLeaderboard(data.leaderboard || []);
    } catch (e) {
      console.error('Failed to fetch leaderboard:', e);
    }
  }, [leaderboardPeriod, leaderboardChain]);

  // Initial load
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await fetchLinkedWallets();
      await fetchLeaderboard();
      setLoading(false);
    };
    
    if (connected && solanaAddress) {
      load();
    } else {
      setLoading(false);
    }
  }, [connected, solanaAddress, fetchLinkedWallets, fetchLeaderboard]);

  // Load following data when wallets are linked
  useEffect(() => {
    if (linkedWallets?.user_id) {
      fetchFollowingData();
    }
  }, [linkedWallets?.user_id, fetchFollowingData]);

  // Link wallets handler
  const handleLinkWallets = async () => {
    if (!solanaAddress) {
      toast.error('Please connect your Solana wallet first');
      return;
    }
    
    if (!evmAddress || !evmAddress.startsWith('0x') || evmAddress.length !== 42) {
      toast.error('Please enter a valid EVM address (0x...)');
      return;
    }
    
    try {
      setLinkingWallet(true);
      const { data } = await axios.post(`${API}/multichain-copy/wallets/link`, null, {
        params: {
          solana_address: solanaAddress,
          ethereum_address: evmAddress,
          primary_chain: 'solana'
        }
      });
      
      setLinkedWallets({
        user_id: data.user_id,
        wallets: data.wallets,
        primary_chain: data.primary_chain,
        linked: true
      });
      
      toast.success('Wallets linked successfully!');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to link wallets');
    } finally {
      setLinkingWallet(false);
    }
  };

  // Follow trader with multi-chain settings
  const handleFollowTrader = async (traderUserId) => {
    if (!linkedWallets?.user_id) {
      toast.error('Please link your wallets first');
      return;
    }
    
    try {
      const { data } = await axios.post(`${API}/multichain-copy/follow`, {
        follower_user_id: linkedWallets.user_id,
        trader_user_id: traderUserId,
        chain_settings: [
          { chain: 'solana', enabled: true, copy_percentage: 50, max_position_native: 0.1, auto_copy: true },
          { chain: 'ethereum', enabled: linkedWallets.wallets?.ethereum ? true : false, copy_percentage: 50, max_position_native: 0.05, auto_copy: true },
          { chain: 'base', enabled: linkedWallets.wallets?.ethereum ? true : false, copy_percentage: 50, max_position_native: 0.05, auto_copy: true },
          { chain: 'arbitrum', enabled: linkedWallets.wallets?.ethereum ? true : false, copy_percentage: 50, max_position_native: 0.05, auto_copy: true }
        ]
      });
      
      toast.success(data.message);
      fetchFollowingData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to follow trader');
    }
  };

  // Update chain settings
  const handleUpdateChainSettings = async (traderUserId, chain, updates) => {
    try {
      await axios.put(`${API}/multichain-copy/chain-settings`, null, {
        params: {
          follower_user_id: linkedWallets.user_id,
          trader_user_id: traderUserId,
          chain,
          ...updates
        }
      });
      toast.success(`${chain} settings updated`);
      fetchFollowingData();
    } catch (e) {
      toast.error('Failed to update settings');
    }
  };

  if (!connected) {
    return (
      <div className="glass-card rounded-xl p-8 border border-white/10 text-center">
        <Wallet className="w-12 h-12 text-slate-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-white mb-2">Connect Wallet</h3>
        <p className="text-sm text-slate-400">Connect your Solana wallet to access multi-chain copy trading</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#D946EF]" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="multichain-copy-trading">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Globe className="w-6 h-6 text-[#00C2FF]" />
            Multi-Chain Copy Trading
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Copy trades across Solana, Ethereum, Base & Arbitrum
          </p>
        </div>
        
        {linkedWallets?.linked && (
          <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">
            <Check className="w-3 h-3 mr-1" />
            Wallets Linked
          </Badge>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-white/10 pb-2">
        {[
          { id: 'wallets', label: 'Wallets', icon: <Link2 className="w-4 h-4" /> },
          { id: 'following', label: 'Following', icon: <Users className="w-4 h-4" /> },
          { id: 'leaderboard', label: 'Leaderboard', icon: <TrendingUp className="w-4 h-4" /> },
          { id: 'trades', label: 'Copied Trades', icon: <Copy className="w-4 h-4" /> }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
              activeTab === tab.id 
                ? 'bg-[#00C2FF]/20 text-[#00C2FF] border-b-2 border-[#00C2FF]' 
                : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Wallets Tab */}
      {activeTab === 'wallets' && (
        <div className="space-y-4">
          {/* Wallet Linking Card */}
          <div className="glass-card rounded-xl p-6 border border-white/10">
            <h3 className="text-sm font-bold text-slate-400 uppercase mb-4">Link Your Wallets</h3>
            
            {/* Solana Wallet */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-[#9945FF]/10 border border-[#9945FF]/30 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#9945FF]/20 flex items-center justify-center">
                  <span className="text-[#9945FF] font-bold">S</span>
                </div>
                <div>
                  <p className="text-white font-medium">Solana</p>
                  <p className="text-xs text-slate-400 font-mono">
                    {solanaAddress?.slice(0, 6)}...{solanaAddress?.slice(-4)}
                  </p>
                </div>
              </div>
              <Badge className="bg-emerald-500/20 text-emerald-400">Connected</Badge>
            </div>

            {/* EVM Wallet Input */}
            <div className="space-y-3">
              <label className="text-sm text-slate-400">EVM Address (Ethereum/Base/Arbitrum)</label>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={evmAddress}
                  onChange={(e) => setEvmAddress(e.target.value)}
                  placeholder="0x..."
                  className="flex-1 bg-slate-800 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-[#00C2FF]"
                  disabled={linkedWallets?.linked}
                />
                <Button
                  onClick={handleLinkWallets}
                  disabled={linkingWallet || linkedWallets?.linked}
                  className="bg-gradient-to-r from-[#627EEA] to-[#00C2FF] text-white"
                >
                  {linkingWallet ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : linkedWallets?.linked ? (
                    <>
                      <Check className="w-4 h-4 mr-1" />
                      Linked
                    </>
                  ) : (
                    <>
                      <Link2 className="w-4 h-4 mr-1" />
                      Link
                    </>
                  )}
                </Button>
              </div>
              <p className="text-xs text-slate-500">
                Link your EVM wallet to enable copy trading on Ethereum, Base, and Arbitrum
              </p>
            </div>
          </div>

          {/* Chain Stats */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(CHAIN_CONFIG).map(([chainId, config]) => {
                const chainStats = stats.stats_by_chain?.[chainId];
                return (
                  <div key={chainId} className={`glass-card rounded-xl p-4 border border-white/10`}>
                    <div className={`w-8 h-8 rounded-full ${config.bgClass} flex items-center justify-center mb-2`}>
                      <span className={`${config.textClass} font-bold text-sm`}>{config.name[0]}</span>
                    </div>
                    <p className="text-white font-medium">{config.name}</p>
                    <p className="text-xs text-slate-400">
                      {chainStats?.total_trades || 0} trades • {chainStats?.total_pnl_native?.toFixed(4) || '0.0000'} {config.symbol}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Following Tab */}
      {activeTab === 'following' && (
        <div className="space-y-4">
          {following.length === 0 ? (
            <div className="glass-card rounded-xl p-8 border border-white/10 text-center">
              <Users className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No Traders Followed</h3>
              <p className="text-sm text-slate-400 mb-4">
                Browse the leaderboard to find top traders to follow
              </p>
              <Button onClick={() => setActiveTab('leaderboard')} className="bg-[#00C2FF]">
                View Leaderboard
              </Button>
            </div>
          ) : (
            following.map((follow, i) => (
              <FollowCard 
                key={i} 
                follow={follow} 
                onUpdateSettings={handleUpdateChainSettings}
              />
            ))
          )}
        </div>
      )}

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-3">
            <select
              value={leaderboardPeriod}
              onChange={(e) => setLeaderboardPeriod(e.target.value)}
              className="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            >
              <option value="24h">Last 24h</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="all">All time</option>
            </select>
            
            <select
              value={leaderboardChain}
              onChange={(e) => setLeaderboardChain(e.target.value)}
              className="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            >
              <option value="all">All Chains</option>
              <option value="solana">Solana</option>
              <option value="ethereum">Ethereum</option>
              <option value="base">Base</option>
              <option value="arbitrum">Arbitrum</option>
            </select>
            
            <Button size="sm" variant="outline" onClick={fetchLeaderboard} className="border-white/10">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>

          {/* Leaderboard List */}
          <div className="space-y-3">
            {leaderboard.map((trader, i) => (
              <LeaderboardCard
                key={i}
                trader={trader}
                canFollow={linkedWallets?.linked && linkedWallets?.user_id !== trader.user_id}
                onFollow={() => handleFollowTrader(trader.user_id)}
              />
            ))}
            {leaderboard.length === 0 && (
              <div className="text-center py-8 text-slate-500">
                No traders found for this period/chain
              </div>
            )}
          </div>
        </div>
      )}

      {/* Copied Trades Tab */}
      {activeTab === 'trades' && (
        <div className="space-y-4">
          {copiedTrades.length === 0 ? (
            <div className="glass-card rounded-xl p-8 border border-white/10 text-center">
              <Copy className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No Copied Trades</h3>
              <p className="text-sm text-slate-400">
                Trades will appear here when your followed traders execute trades
              </p>
            </div>
          ) : (
            <div className="glass-card rounded-xl border border-white/10 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="text-left text-xs text-slate-400 font-medium p-4">Chain</th>
                      <th className="text-left text-xs text-slate-400 font-medium p-4">Token</th>
                      <th className="text-left text-xs text-slate-400 font-medium p-4">Type</th>
                      <th className="text-right text-xs text-slate-400 font-medium p-4">Amount</th>
                      <th className="text-right text-xs text-slate-400 font-medium p-4">Status</th>
                      <th className="text-right text-xs text-slate-400 font-medium p-4">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {copiedTrades.map((trade, i) => {
                      const chainConfig = CHAIN_CONFIG[trade.chain] || CHAIN_CONFIG.solana;
                      return (
                        <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                          <td className="p-4">
                            <Badge className={`${chainConfig.bgClass} ${chainConfig.textClass} text-xs`}>
                              {chainConfig.name}
                            </Badge>
                          </td>
                          <td className="p-4 text-white font-medium">{trade.token_symbol}</td>
                          <td className="p-4">
                            <Badge className={trade.trade_type === 'buy' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}>
                              {trade.trade_type?.toUpperCase()}
                            </Badge>
                          </td>
                          <td className="p-4 text-right text-white">
                            {trade.copied_amount?.toFixed(4)} {chainConfig.symbol}
                          </td>
                          <td className="p-4 text-right">
                            <Badge className={
                              trade.status === 'executed' ? 'bg-emerald-500/20 text-emerald-400' :
                              trade.status === 'pending' ? 'bg-amber-500/20 text-amber-400' :
                              'bg-red-500/20 text-red-400'
                            }>
                              {trade.status}
                            </Badge>
                          </td>
                          <td className="p-4 text-right text-xs text-slate-400">
                            {new Date(trade.created_at).toLocaleString()}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Sub-components

function FollowCard({ follow, onUpdateSettings }) {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <div className="glass-card rounded-xl border border-white/10 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-white/5"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#D946EF] to-[#00C2FF] flex items-center justify-center">
            <span className="text-white font-bold">
              {follow.trader_display_name?.[0] || 'T'}
            </span>
          </div>
          <div className="text-left">
            <p className="text-white font-medium">{follow.trader_display_name || 'Trader'}</p>
            <p className="text-xs text-slate-400">
              {follow.trades_copied || 0} trades copied • {follow.trader_fee_percent || 10}% fee
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {follow.chain_settings?.filter(s => s.enabled).map((s, i) => {
              const config = CHAIN_CONFIG[s.chain];
              return (
                <div 
                  key={i}
                  className={`w-6 h-6 rounded-full ${config?.bgClass} flex items-center justify-center`}
                  title={config?.name}
                >
                  <span className={`${config?.textClass} text-[10px] font-bold`}>{s.chain[0].toUpperCase()}</span>
                </div>
              );
            })}
          </div>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>
      
      {expanded && (
        <div className="border-t border-white/5 p-4 space-y-4">
          <p className="text-xs text-slate-400 font-bold uppercase">Chain Settings</p>
          {follow.chain_settings?.map((settings, i) => {
            const config = CHAIN_CONFIG[settings.chain];
            return (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full ${config?.bgClass} flex items-center justify-center`}>
                    <span className={`${config?.textClass} font-bold text-sm`}>{config?.name[0]}</span>
                  </div>
                  <div>
                    <p className="text-white text-sm">{config?.name}</p>
                    <p className="text-xs text-slate-400">
                      {settings.copy_percentage}% copy • Max {settings.max_position_native} {config?.symbol}
                    </p>
                  </div>
                </div>
                <Switch
                  checked={settings.enabled}
                  onCheckedChange={(enabled) => onUpdateSettings(follow.trader_user_id, settings.chain, { enabled })}
                  className="data-[state=checked]:bg-[#00C2FF]"
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function LeaderboardCard({ trader, canFollow, onFollow }) {
  return (
    <div className="glass-card rounded-xl p-4 border border-white/10 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
          trader.rank <= 3 ? 'bg-gradient-to-br from-amber-400 to-orange-500' : 'bg-slate-700'
        }`}>
          <span className="text-white font-bold text-sm">#{trader.rank}</span>
        </div>
        
        <div>
          <div className="flex items-center gap-2">
            <p className="text-white font-medium">{trader.display_name}</p>
            {trader.copy_trading_enabled && (
              <Badge className="bg-emerald-500/20 text-emerald-400 text-[10px]">
                <Copy className="w-3 h-3 mr-1" />
                Copyable
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>{trader.total_trades} trades</span>
            <span>{trader.win_rate.toFixed(1)}% win</span>
            <span className="flex gap-1">
              {trader.chains_traded?.map((chain, i) => {
                const config = CHAIN_CONFIG[chain];
                return (
                  <span key={i} className={config?.textClass}>{chain[0].toUpperCase()}</span>
                );
              })}
            </span>
          </div>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className={`font-bold ${trader.total_pnl_usd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {trader.total_pnl_usd >= 0 ? '+' : ''}{trader.total_pnl_usd?.toFixed(2)} USD
          </p>
          <p className="text-xs text-slate-500">{trader.performance_fee_percent}% fee</p>
        </div>
        
        {trader.copy_trading_enabled && canFollow && (
          <Button size="sm" onClick={onFollow} className="bg-[#00C2FF] text-white">
            <Users className="w-4 h-4 mr-1" />
            Follow
          </Button>
        )}
      </div>
    </div>
  );
}
