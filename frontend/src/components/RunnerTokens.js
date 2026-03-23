/**
 * RunnerTokens Component
 * 
 * Displays trending "runner" tokens discovered by the AI trading bot.
 * Runners are new/trending tokens with high momentum potential.
 * 
 * Features:
 * - Real-time runner discovery from DexScreener
 * - Score-based ranking system
 * - Quick trade actions
 * - Performance metrics (price change, volume, liquidity)
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Rocket, TrendingUp, TrendingDown, Loader2, RefreshCw,
  ExternalLink, DollarSign, Clock, Users, Zap, 
  AlertTriangle, ChevronDown, ChevronUp, Copy, Activity
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Score tier configurations
const SCORE_TIERS = {
  legendary: { min: 90, color: '#FFD700', bg: 'bg-[#FFD700]/20', label: 'Legendary' },
  excellent: { min: 80, color: '#00FFA3', bg: 'bg-[#00FFA3]/20', label: 'Excellent' },
  good: { min: 70, color: '#00C2FF', bg: 'bg-[#00C2FF]/20', label: 'Good' },
  moderate: { min: 60, color: '#D946EF', bg: 'bg-[#D946EF]/20', label: 'Moderate' },
  risky: { min: 0, color: '#FF6B6B', bg: 'bg-[#FF6B6B]/20', label: 'Risky' }
};

const getScoreTier = (score) => {
  if (score >= 90) return SCORE_TIERS.legendary;
  if (score >= 80) return SCORE_TIERS.excellent;
  if (score >= 70) return SCORE_TIERS.good;
  if (score >= 60) return SCORE_TIERS.moderate;
  return SCORE_TIERS.risky;
};

const formatNumber = (num) => {
  if (num >= 1000000) return `$${(num / 1000000).toFixed(2)}M`;
  if (num >= 1000) return `$${(num / 1000).toFixed(1)}K`;
  return `$${num.toFixed(2)}`;
};

const formatPrice = (price) => {
  if (price < 0.00001) return price.toExponential(2);
  if (price < 0.01) return price.toFixed(6);
  if (price < 1) return price.toFixed(4);
  return price.toFixed(2);
};

// Safe copy to clipboard
const safeCopyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand("copy");
    document.body.removeChild(textArea);
    return true;
  }
};

export default function RunnerTokens({ 
  onTradeRunner, 
  custodialBalance = 0, 
  compact = false,
  onQuickBuy,
  onAnalyze,
  onCopy,
  refreshTrigger = 0, // When this value changes, component will refresh its data
  onRefreshComplete = null // Callback when refresh completes
}) {
  const { publicKey, connected } = useWallet();
  const walletAddress = publicKey?.toBase58();

  const [loading, setLoading] = useState(true);
  const [runners, setRunners] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [expandedRunner, setExpandedRunner] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  
  // Compact mode state - must be at top level to follow Rules of Hooks
  const [buyInputOpen, setBuyInputOpen] = useState(null);
  const [buyAmount, setBuyAmount] = useState(0.1);
  const [buying, setBuying] = useState(false);

  // Fetch runner tokens
  const fetchRunners = useCallback(async (showRefreshing = false, isExternalTrigger = false) => {
    if (showRefreshing) setRefreshing(true);
    else setLoading(true);
    
    try {
      const { data } = await axios.get(`${API}/ai-trader/runners`);
      if (data.success) {
        setRunners(data.runners || []);
        setLastUpdate(new Date());
      }
    } catch (e) {
      console.error('Failed to fetch runners:', e);
      toast.error('Failed to fetch runner tokens');
    } finally {
      setLoading(false);
      setRefreshing(false);
      // Notify parent when external trigger refresh completes
      if (isExternalTrigger && onRefreshComplete) {
        onRefreshComplete();
      }
    }
  }, [onRefreshComplete]);

  // Initial fetch and refresh every 2 minutes
  useEffect(() => {
    fetchRunners();
    const interval = setInterval(() => fetchRunners(true), 2 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchRunners]);

  // Respond to external refresh trigger from parent
  useEffect(() => {
    if (refreshTrigger > 0) {
      fetchRunners(true, true); // Pass true for isExternalTrigger
    }
  }, [refreshTrigger, fetchRunners]);

  const copyAddress = async (address) => {
    await safeCopyToClipboard(address);
    toast.success('Token address copied!');
  };

  if (loading && runners.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-10 h-10 text-[#D946EF] animate-spin mb-4" />
        <p className="text-slate-400">Scanning for runner tokens...</p>
      </div>
    );
  }

  // Compact mode - show action buttons like TopPickCard
  if (compact) {
    const truncateAddress = (address) => {
      if (!address) return "";
      if (address.length <= 12) return address;
      return `${address.slice(0, 6)}...${address.slice(-4)}`;
    };

    const handleQuickBuy = async (runner) => {
      if (buyAmount <= 0) return;
      setBuying(true);
      try {
        await onQuickBuy(runner, buyAmount);
      } finally {
        setBuying(false);
        setBuyInputOpen(null);
      }
    };

    return (
      <div className="space-y-2" data-testid="runner-tokens-compact">
        {runners.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">No runners found</p>
        ) : (
          <div className="space-y-2">
            {runners.slice(0, 6).map((runner, idx) => {
              const tier = getScoreTier(runner.runner_score);
              const isHot = runner.volume_24h && runner.volume_24h > 100000;
              const isBuyOpen = buyInputOpen === runner.token_address;
              
              return (
                <div
                  key={runner.token_address || idx}
                  className="bg-[#12121A] border border-[#D946EF]/20 rounded-xl p-3 hover:border-[#D946EF]/40 transition-colors"
                  data-testid={`runner-compact-${idx}`}
                >
                  {/* Main Row: Token info & Price */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {runner.image_url ? (
                        <img src={runner.image_url} alt={runner.symbol} className="w-9 h-9 rounded-lg object-cover" />
                      ) : (
                        <div className={`w-9 h-9 rounded-lg ${tier.bg} flex items-center justify-center`}>
                          <span className="text-sm font-bold" style={{ color: tier.color }}>
                            {runner.symbol?.charAt(0) || '?'}
                          </span>
                        </div>
                      )}
                      <div>
                        <div className="flex items-center gap-1 flex-wrap">
                          <p className="font-semibold text-sm text-white">{runner.symbol}</p>
                          {runner.is_bonded && (
                            <span className="px-1.5 py-0.5 text-[8px] bg-[#00FFA3]/20 text-[#00FFA3] rounded font-bold">
                              BONDED
                            </span>
                          )}
                          {isHot && (
                            <span className="px-1.5 py-0.5 text-[8px] bg-[#FF6B6B]/30 text-[#FF6B6B] rounded font-bold animate-pulse">
                              🔥 HOT
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-slate-500 capitalize">{runner.dex || 'Solana'}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm text-white">
                        ${formatPrice(runner.price_usd || 0)}
                      </p>
                      <p className={`text-[10px] ${runner.price_change_24h >= 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                        {runner.price_change_24h >= 0 ? '+' : ''}{runner.price_change_24h?.toFixed(1)}%
                      </p>
                    </div>
                  </div>

                  {/* Contract Address & Actions Row */}
                  <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between flex-wrap gap-2">
                    <button 
                      onClick={() => onCopy ? onCopy(runner.token_address, "Contract") : copyAddress(runner.token_address)}
                      className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition-colors"
                      title="Click to copy contract address"
                    >
                      <Copy className="w-3 h-3" />
                      <span className="font-mono">{truncateAddress(runner.token_address)}</span>
                    </button>
                    
                    <div className="flex items-center gap-2">
                      {/* Analyze Button */}
                      <button
                        onClick={() => onAnalyze ? onAnalyze(runner) : toast.info(`Analyzing ${runner.symbol}...`)}
                        className="flex items-center gap-1 text-[10px] text-[#D946EF] hover:text-white transition-colors"
                        title="Generate trading signal"
                      >
                        <Zap className="w-3 h-3" />
                        Analyze
                      </button>
                      
                      {/* Buy Button */}
                      {onQuickBuy && (
                        <button
                          onClick={() => {
                            if (custodialBalance <= 0) {
                              toast.error('Deposit SOL to enable trading');
                              return;
                            }
                            setBuyInputOpen(isBuyOpen ? null : runner.token_address);
                          }}
                          className="flex items-center gap-1 text-[10px] bg-[#00FFA3]/20 text-[#00FFA3] px-2 py-1 rounded hover:bg-[#00FFA3]/30 transition-colors"
                          title="Quick buy this token"
                          data-testid={`buy-runner-${idx}`}
                        >
                          <DollarSign className="w-3 h-3" />
                          Buy
                        </button>
                      )}
                      
                      {/* DEX Link */}
                      <a 
                        href={`https://dexscreener.com/solana/${runner.pair_address || runner.token_address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[10px] text-[#D946EF] hover:text-white transition-colors"
                        title="View on DexScreener"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>

                  {/* Quick Buy Input */}
                  {isBuyOpen && onQuickBuy && (
                    <div className="mt-2 pt-2 border-t border-white/5 flex items-center gap-2">
                      <input
                        type="number"
                        value={buyAmount}
                        onChange={(e) => setBuyAmount(Math.max(0.01, parseFloat(e.target.value) || 0))}
                        step="0.01"
                        min="0.01"
                        max="10"
                        className="flex-1 bg-white/10 border border-white/20 rounded px-2 py-1 text-sm font-mono text-white focus:border-[#00FFA3] focus:outline-none"
                        placeholder="SOL amount"
                      />
                      <button
                        onClick={() => handleQuickBuy(runner)}
                        disabled={buying || buyAmount <= 0}
                        className="bg-gradient-to-r from-[#00FFA3] to-[#00C2FF] text-black text-xs font-bold px-3 py-1 rounded hover:opacity-90 disabled:opacity-50"
                      >
                        {buying ? 'Buying...' : `Buy ${buyAmount} SOL`}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="runner-tokens-section">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#FFD700]/20 to-[#FF6B6B]/20 flex items-center justify-center">
            <Rocket className="w-5 h-5 text-[#FFD700]" />
          </div>
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              Runner Tokens
              <Badge variant="outline" className="text-[10px] border-[#FFD700]/30 text-[#FFD700]">
                LIVE
              </Badge>
            </h3>
            <p className="text-xs text-slate-400">
              New trending tokens with high momentum potential
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {lastUpdate && (
            <span className="text-xs text-slate-500">
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <Button
            onClick={() => fetchRunners(true)}
            disabled={refreshing}
            size="sm"
            variant="outline"
            className="border-white/20"
            data-testid="refresh-runners-btn"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Warning Banner */}
      <div className="bg-[#FF6B6B]/10 border border-[#FF6B6B]/30 rounded-xl p-3 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-[#FF6B6B] shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="text-[#FF6B6B] font-medium">High Risk Assets</p>
          <p className="text-slate-400 text-xs mt-1">
            Runner tokens are extremely volatile. Only trade with funds you can afford to lose. 
            DYOR and verify contracts before trading.
          </p>
        </div>
      </div>

      {/* Custodial Balance Info */}
      {connected && (
        <div className="bg-[#12121A] border border-white/10 rounded-xl p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-[#00FFA3]" />
            <span className="text-sm text-slate-300">Auto-Trade Balance:</span>
            <span className={`font-mono font-semibold ${custodialBalance > 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
              {custodialBalance.toFixed(4)} SOL
            </span>
          </div>
          {custodialBalance === 0 && (
            <span className="text-xs text-[#FF6B6B]">Deposit SOL to enable auto-trading</span>
          )}
        </div>
      )}

      {/* Runner List */}
      {runners.length === 0 ? (
        <div className="bg-[#12121A] border border-white/10 rounded-xl p-8 text-center">
          <Rocket className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No runner tokens found at the moment</p>
          <p className="text-xs text-slate-500 mt-1">Check back in a few minutes</p>
        </div>
      ) : (
        <div className="space-y-3">
          {runners.map((runner, idx) => {
            const tier = getScoreTier(runner.runner_score);
            const isExpanded = expandedRunner === idx;
            
            return (
              <div
                key={runner.token_address || idx}
                className="bg-[#12121A] border border-white/10 rounded-xl overflow-hidden hover:border-white/20 transition-colors"
                data-testid={`runner-card-${idx}`}
              >
                {/* Main Row */}
                <div 
                  className="p-4 cursor-pointer"
                  onClick={() => setExpandedRunner(isExpanded ? null : idx)}
                >
                  <div className="flex items-center justify-between">
                    {/* Left: Token Info */}
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className={`w-12 h-12 rounded-xl ${tier.bg} flex items-center justify-center`}>
                          <span className="text-lg font-bold" style={{ color: tier.color }}>
                            {runner.symbol?.charAt(0) || '?'}
                          </span>
                        </div>
                        <div 
                          className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold"
                          style={{ backgroundColor: tier.color, color: '#000' }}
                        >
                          {runner.runner_score}
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">{runner.symbol}</span>
                          <Badge 
                            variant="outline" 
                            className="text-[9px] px-1.5"
                            style={{ borderColor: `${tier.color}30`, color: tier.color }}
                          >
                            {tier.label}
                          </Badge>
                          {runner.hours_since_creation < 24 && (
                            <Badge className="text-[9px] px-1.5 bg-[#FFD700]/20 text-[#FFD700] border-none">
                              NEW
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-slate-400">${formatPrice(runner.price_usd)}</span>
                          <span className="text-xs text-slate-500">•</span>
                          <span className="text-xs text-slate-400 capitalize">{runner.dex}</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Right: Price Change & Actions */}
                    <div className="flex items-center gap-4">
                      {/* Price Changes */}
                      <div className="hidden sm:flex items-center gap-3">
                        <div className="text-right">
                          <p className="text-xs text-slate-500">1H</p>
                          <p className={`text-sm font-medium ${runner.price_change_1h >= 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                            {runner.price_change_1h >= 0 ? '+' : ''}{runner.price_change_1h?.toFixed(1)}%
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-slate-500">24H</p>
                          <p className={`text-sm font-medium ${runner.price_change_24h >= 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                            {runner.price_change_24h >= 0 ? '+' : ''}{runner.price_change_24h?.toFixed(0)}%
                          </p>
                        </div>
                      </div>
                      
                      {/* Expand Button */}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-slate-400 hover:text-white"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </Button>
                    </div>
                  </div>
                  
                  {/* Mobile Price Changes */}
                  <div className="flex sm:hidden items-center gap-4 mt-3 pt-3 border-t border-white/5">
                    <div className="flex-1 flex items-center justify-between">
                      <span className="text-xs text-slate-500">1H Change:</span>
                      <span className={`text-sm font-medium ${runner.price_change_1h >= 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                        {runner.price_change_1h >= 0 ? '+' : ''}{runner.price_change_1h?.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex-1 flex items-center justify-between">
                      <span className="text-xs text-slate-500">24H:</span>
                      <span className={`text-sm font-medium ${runner.price_change_24h >= 0 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}`}>
                        {runner.price_change_24h >= 0 ? '+' : ''}{runner.price_change_24h?.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
                
                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-0 border-t border-white/5">
                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                      <div className="bg-white/5 rounded-lg p-2">
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                          <DollarSign className="w-3 h-3" /> Liquidity
                        </p>
                        <p className="text-sm font-medium text-white">{formatNumber(runner.liquidity_usd)}</p>
                      </div>
                      <div className="bg-white/5 rounded-lg p-2">
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                          <Activity className="w-3 h-3" /> 24H Volume
                        </p>
                        <p className="text-sm font-medium text-white">{formatNumber(runner.volume_24h)}</p>
                      </div>
                      <div className="bg-white/5 rounded-lg p-2">
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                          <Users className="w-3 h-3" /> Buy/Sell (1H)
                        </p>
                        <p className="text-sm font-medium text-white">
                          <span className="text-[#00FFA3]">{runner.buys_1h}</span>
                          {' / '}
                          <span className="text-[#FF6B6B]">{runner.sells_1h}</span>
                        </p>
                      </div>
                      <div className="bg-white/5 rounded-lg p-2">
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                          <Clock className="w-3 h-3" /> Age
                        </p>
                        <p className="text-sm font-medium text-white">
                          {runner.hours_since_creation < 24 
                            ? `${runner.hours_since_creation?.toFixed(1)}h`
                            : `${(runner.hours_since_creation / 24).toFixed(1)}d`
                          }
                        </p>
                      </div>
                    </div>
                    
                    {/* Buy Ratio Bar */}
                    <div className="mb-4">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-slate-400">Buy Pressure</span>
                        <span className={runner.buy_ratio > 0.5 ? 'text-[#00FFA3]' : 'text-[#FF6B6B]'}>
                          {(runner.buy_ratio * 100).toFixed(0)}% Buys
                        </span>
                      </div>
                      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-[#00FFA3] to-[#00FFA3]/60"
                          style={{ width: `${runner.buy_ratio * 100}%` }}
                        />
                      </div>
                    </div>
                    
                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-white/20 text-slate-300"
                        onClick={(e) => {
                          e.stopPropagation();
                          copyAddress(runner.token_address);
                        }}
                        data-testid={`copy-token-${idx}`}
                      >
                        <Copy className="w-3 h-3 mr-1" />
                        Copy CA
                      </Button>
                      
                      <a
                        href={`https://dexscreener.com/solana/${runner.pair_address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-white/20 text-slate-300"
                        >
                          <ExternalLink className="w-3 h-3 mr-1" />
                          DexScreener
                        </Button>
                      </a>
                      
                      <a
                        href={`https://solscan.io/token/${runner.token_address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-white/20 text-slate-300"
                        >
                          <ExternalLink className="w-3 h-3 mr-1" />
                          Solscan
                        </Button>
                      </a>
                      
                      {onTradeRunner && connected && (
                        <Button
                          size="sm"
                          className="ml-auto bg-gradient-to-r from-[#D946EF] to-[#FFD700] hover:opacity-90"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (custodialBalance === 0) {
                              toast.error('Deposit SOL to your custodial wallet first');
                              return;
                            }
                            onTradeRunner(runner);
                          }}
                          disabled={custodialBalance === 0}
                          data-testid={`trade-runner-${idx}`}
                        >
                          <Zap className="w-3 h-3 mr-1" />
                          Quick Trade
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
      
      {/* Info Footer */}
      <div className="text-center text-xs text-slate-500 py-2">
        <p>Runner scores are based on momentum, volume, liquidity, and buy pressure.</p>
        <p className="mt-1">Data sourced from DexScreener. Auto-refreshes every 2 minutes.</p>
      </div>
    </div>
  );
}
