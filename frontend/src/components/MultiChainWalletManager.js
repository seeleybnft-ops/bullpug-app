/**
 * MultiChainWalletManager Component
 * 
 * A comprehensive multi-chain wallet integration component that:
 * - Displays all connected wallets (Solana + EVM)
 * - Automatically fetches trade history across all chains
 * - Shows portfolio values and token holdings
 * - Enables one-click import to the Trading Journal
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useAccount, useChainId, useSwitchChain } from 'wagmi';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Wallet, RefreshCw, Download, Check, ExternalLink, Loader2,
  Coins, Link2, Unlink2, ChevronDown, ChevronUp, ArrowRightLeft,
  TrendingUp, TrendingDown, Copy, Eye, EyeOff, Zap, Network
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Chain configurations with branding
const CHAIN_CONFIG = {
  ethereum: {
    name: 'Ethereum',
    symbol: 'ETH',
    icon: '⟠',
    color: '#627EEA',
    chainId: 1,
    explorer: 'https://etherscan.io'
  },
  base: {
    name: 'Base',
    symbol: 'ETH',
    icon: '🔵',
    color: '#0052FF',
    chainId: 8453,
    explorer: 'https://basescan.org'
  },
  arbitrum: {
    name: 'Arbitrum',
    symbol: 'ETH',
    icon: '🔷',
    color: '#28A0F0',
    chainId: 42161,
    explorer: 'https://arbiscan.io'
  },
  solana: {
    name: 'Solana',
    symbol: 'SOL',
    icon: '◎',
    color: '#9945FF',
    explorer: 'https://solscan.io'
  }
};

export default function MultiChainWalletManager({ onTradesFound, onImportComplete, compact = false }) {
  const { publicKey: solanaPublicKey, connected: solanaConnected, disconnect: disconnectSolana } = useWallet();
  const { address: evmAddress, isConnected: evmConnected, connector } = useAccount();
  const evmChainId = useChainId();
  const { switchChain, chains } = useSwitchChain();

  const [expanded, setExpanded] = useState(!compact);
  const [loading, setLoading] = useState(false);
  const [scanningChain, setScanningChain] = useState(null);
  const [tradesByChain, setTradesByChain] = useState({});
  const [portfolioByChain, setPortfolioByChain] = useState({});
  const [selectedChains, setSelectedChains] = useState(new Set(['solana', 'ethereum', 'base', 'arbitrum']));
  const [showPortfolio, setShowPortfolio] = useState(true);
  const [copiedAddress, setCopiedAddress] = useState(null);
  const [autoScanEnabled, setAutoScanEnabled] = useState(true);

  // Get current EVM chain name
  const getCurrentEvmChain = () => {
    switch (evmChainId) {
      case 1: return 'ethereum';
      case 8453: return 'base';
      case 42161: return 'arbitrum';
      default: return 'ethereum';
    }
  };

  // Copy address to clipboard
  const copyAddress = async (address, chain) => {
    try {
      await navigator.clipboard.writeText(address);
      setCopiedAddress(chain);
      toast.success('Address copied!');
      setTimeout(() => setCopiedAddress(null), 2000);
    } catch (e) {
      toast.error('Failed to copy');
    }
  };

  // Toggle chain selection
  const toggleChain = (chain) => {
    setSelectedChains(prev => {
      const newSet = new Set(prev);
      if (newSet.has(chain)) {
        newSet.delete(chain);
      } else {
        newSet.add(chain);
      }
      return newSet;
    });
  };

  // Fetch trades for a single chain
  const fetchTradesForChain = async (chain, address) => {
    setScanningChain(chain);
    try {
      const endpoint = chain === 'solana'
        ? `${API}/wallet-trades/solana/${address}`
        : `${API}/wallet-trades/evm/${address}?chain=${chain}`;
      
      const { data } = await axios.get(endpoint);
      
      setTradesByChain(prev => ({
        ...prev,
        [chain]: data.trades || []
      }));
      
      return data.trades || [];
    } catch (e) {
      console.error(`Failed to fetch trades for ${chain}:`, e);
      setTradesByChain(prev => ({
        ...prev,
        [chain]: []
      }));
      return [];
    } finally {
      setScanningChain(null);
    }
  };

  // Fetch portfolio for a chain
  const fetchPortfolioForChain = async (chain, address) => {
    try {
      const endpoint = chain === 'solana'
        ? `${API}/portfolio/solana/${address}`
        : `${API}/portfolio/evm/${address}?chains=${chain}`;
      
      const { data } = await axios.get(endpoint);
      
      if (chain === 'solana' && data.solana) {
        setPortfolioByChain(prev => ({
          ...prev,
          solana: data.solana
        }));
      } else if (data.chains?.length > 0) {
        const chainData = data.chains.find(c => c.chain === chain);
        if (chainData) {
          setPortfolioByChain(prev => ({
            ...prev,
            [chain]: chainData
          }));
        }
      }
    } catch (e) {
      console.error(`Failed to fetch portfolio for ${chain}:`, e);
    }
  };

  // Scan all connected wallets
  const scanAllWallets = async () => {
    setLoading(true);
    const allTrades = [];
    
    try {
      // Scan Solana if connected
      if (solanaConnected && solanaPublicKey && selectedChains.has('solana')) {
        const solanaTrades = await fetchTradesForChain('solana', solanaPublicKey.toBase58());
        allTrades.push(...solanaTrades);
        await fetchPortfolioForChain('solana', solanaPublicKey.toBase58());
      }
      
      // Scan EVM chains if connected
      if (evmConnected && evmAddress) {
        for (const chain of ['ethereum', 'base', 'arbitrum']) {
          if (selectedChains.has(chain)) {
            const chainTrades = await fetchTradesForChain(chain, evmAddress);
            allTrades.push(...chainTrades);
            await fetchPortfolioForChain(chain, evmAddress);
          }
        }
      }
      
      if (allTrades.length > 0) {
        toast.success(`Found ${allTrades.length} trades across selected chains`);
        onTradesFound?.(allTrades);
      } else {
        toast.info('No trades found in selected chains');
      }
    } catch (e) {
      console.error('Scan error:', e);
      toast.error('Failed to scan wallets');
    }
    
    setLoading(false);
  };

  // Auto-scan on wallet connect
  useEffect(() => {
    if (autoScanEnabled && (solanaConnected || evmConnected)) {
      const timer = setTimeout(() => {
        scanAllWallets();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [solanaConnected, evmConnected, autoScanEnabled]);

  // Calculate total trades found
  const totalTrades = Object.values(tradesByChain).reduce((sum, trades) => sum + trades.length, 0);
  
  // Calculate total portfolio value
  const totalPortfolioValue = Object.values(portfolioByChain).reduce((sum, portfolio) => {
    return sum + (portfolio?.total_value_usd || 0);
  }, 0);

  // Format currency
  const formatUSD = (value) => {
    if (!value && value !== 0) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const hasWalletConnected = solanaConnected || evmConnected;

  if (!hasWalletConnected) {
    return (
      <div className="glass-card rounded-xl p-6 text-center border border-white/5" data-testid="wallet-manager-empty">
        <Wallet className="w-10 h-10 mx-auto mb-3 text-slate-600" />
        <p className="text-slate-400 text-sm mb-2">Connect a wallet to get started</p>
        <p className="text-slate-600 text-xs">
          Supports Solana, Ethereum, Base & Arbitrum
        </p>
        <div className="flex justify-center gap-2 mt-3 flex-wrap">
          {Object.entries(CHAIN_CONFIG).map(([key, config]) => (
            <span
              key={key}
              className="text-[10px] px-2 py-1 rounded-full"
              style={{ backgroundColor: `${config.color}15`, color: config.color }}
            >
              {config.icon} {config.name}
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl border border-white/5 overflow-hidden" data-testid="wallet-manager">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-[#9945FF] to-[#627EEA] flex items-center justify-center">
            <Network className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              Multi-Chain Wallets
              {loading && <Loader2 className="w-3 h-3 animate-spin text-[#00C2FF]" />}
            </h4>
            <p className="text-xs text-slate-500">
              {totalTrades > 0 ? `${totalTrades} trades found` : 'Ready to scan'}
              {totalPortfolioValue > 0 && ` • ${formatUSD(totalPortfolioValue)} value`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {totalTrades > 0 && (
            <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] text-[10px]">
              {totalTrades} trades
            </Badge>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-white/5 p-4 space-y-4">
          {/* Connected Wallets */}
          <div className="space-y-2">
            <p className="text-xs font-bold uppercase text-slate-400 mb-2">Connected Wallets</p>
            
            {/* Solana Wallet */}
            {solanaConnected && solanaPublicKey && (
              <div
                className="flex items-center justify-between p-3 rounded-lg"
                style={{ backgroundColor: `${CHAIN_CONFIG.solana.color}10`, borderLeft: `3px solid ${CHAIN_CONFIG.solana.color}` }}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{CHAIN_CONFIG.solana.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-white">Solana</p>
                    <p className="text-[10px] text-slate-400 font-mono">
                      {solanaPublicKey.toBase58().slice(0, 6)}...{solanaPublicKey.toBase58().slice(-4)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {portfolioByChain.solana && (
                    <span className="text-xs text-[#00FFA3] font-medium">
                      {formatUSD(portfolioByChain.solana.total_value_usd)}
                    </span>
                  )}
                  <button
                    onClick={() => copyAddress(solanaPublicKey.toBase58(), 'solana')}
                    className="p-1.5 rounded hover:bg-white/10 transition-colors"
                  >
                    {copiedAddress === 'solana' ? (
                      <Check className="w-3 h-3 text-[#00FFA3]" />
                    ) : (
                      <Copy className="w-3 h-3 text-slate-400" />
                    )}
                  </button>
                  <a
                    href={`${CHAIN_CONFIG.solana.explorer}/account/${solanaPublicKey.toBase58()}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded hover:bg-white/10 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3 text-slate-400" />
                  </a>
                </div>
              </div>
            )}
            
            {/* EVM Wallet */}
            {evmConnected && evmAddress && (
              <div
                className="flex items-center justify-between p-3 rounded-lg"
                style={{ backgroundColor: `${CHAIN_CONFIG[getCurrentEvmChain()].color}10`, borderLeft: `3px solid ${CHAIN_CONFIG[getCurrentEvmChain()].color}` }}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{CHAIN_CONFIG[getCurrentEvmChain()].icon}</span>
                  <div>
                    <p className="text-sm font-medium text-white">
                      {CHAIN_CONFIG[getCurrentEvmChain()].name}
                      <span className="text-slate-500 text-[10px] ml-2">(EVM)</span>
                    </p>
                    <p className="text-[10px] text-slate-400 font-mono">
                      {evmAddress.slice(0, 6)}...{evmAddress.slice(-4)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {portfolioByChain[getCurrentEvmChain()] && (
                    <span className="text-xs text-[#00FFA3] font-medium">
                      {formatUSD(portfolioByChain[getCurrentEvmChain()].total_value_usd)}
                    </span>
                  )}
                  <button
                    onClick={() => copyAddress(evmAddress, 'evm')}
                    className="p-1.5 rounded hover:bg-white/10 transition-colors"
                  >
                    {copiedAddress === 'evm' ? (
                      <Check className="w-3 h-3 text-[#00FFA3]" />
                    ) : (
                      <Copy className="w-3 h-3 text-slate-400" />
                    )}
                  </button>
                  <a
                    href={`${CHAIN_CONFIG[getCurrentEvmChain()].explorer}/address/${evmAddress}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded hover:bg-white/10 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3 text-slate-400" />
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Chain Selection */}
          <div>
            <p className="text-xs font-bold uppercase text-slate-400 mb-2">Chains to Scan</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(CHAIN_CONFIG).map(([key, config]) => {
                const isSelected = selectedChains.has(key);
                const tradesCount = tradesByChain[key]?.length || 0;
                const isDisabled = (key === 'solana' && !solanaConnected) || 
                                   (key !== 'solana' && !evmConnected);
                
                return (
                  <button
                    key={key}
                    onClick={() => !isDisabled && toggleChain(key)}
                    disabled={isDisabled}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isDisabled 
                        ? 'opacity-40 cursor-not-allowed bg-white/5 text-slate-500'
                        : isSelected
                          ? 'text-white'
                          : 'bg-white/5 text-slate-400 hover:bg-white/10'
                    }`}
                    style={isSelected && !isDisabled ? { backgroundColor: `${config.color}20`, color: config.color } : {}}
                  >
                    <span>{config.icon}</span>
                    <span>{config.name}</span>
                    {tradesCount > 0 && (
                      <Badge className="text-[9px] ml-1" style={{ backgroundColor: `${config.color}30`, color: config.color }}>
                        {tradesCount}
                      </Badge>
                    )}
                    {scanningChain === key && (
                      <Loader2 className="w-3 h-3 animate-spin ml-1" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button
              onClick={scanAllWallets}
              disabled={loading || selectedChains.size === 0}
              className="flex-1 bg-gradient-to-r from-[#9945FF] to-[#627EEA] text-white font-bold rounded-xl py-3 text-xs uppercase"
              data-testid="scan-wallets-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Scanning {scanningChain ? CHAIN_CONFIG[scanningChain]?.name : ''}...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 mr-2" />
                  Scan {selectedChains.size} Chain{selectedChains.size !== 1 ? 's' : ''}
                </>
              )}
            </Button>
            
            <button
              onClick={() => setShowPortfolio(!showPortfolio)}
              className={`p-3 rounded-xl transition-colors ${showPortfolio ? 'bg-[#00C2FF]/20 text-[#00C2FF]' : 'bg-white/5 text-slate-400'}`}
              title={showPortfolio ? 'Hide portfolio' : 'Show portfolio'}
            >
              {showPortfolio ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </button>
          </div>

          {/* Portfolio Summary */}
          {showPortfolio && Object.keys(portfolioByChain).length > 0 && (
            <div className="p-3 rounded-lg bg-gradient-to-r from-[#00FFA3]/5 to-[#00C2FF]/5 border border-white/5">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-bold uppercase text-[#00FFA3]">Portfolio Value</p>
                <p className="text-lg font-black text-white">{formatUSD(totalPortfolioValue)}</p>
              </div>
              <div className="flex gap-3 flex-wrap">
                {Object.entries(portfolioByChain).map(([chain, portfolio]) => (
                  <div
                    key={chain}
                    className="flex items-center gap-1.5 text-[10px] px-2 py-1 rounded"
                    style={{ backgroundColor: `${CHAIN_CONFIG[chain]?.color}15` }}
                  >
                    <span>{CHAIN_CONFIG[chain]?.icon}</span>
                    <span style={{ color: CHAIN_CONFIG[chain]?.color }}>{formatUSD(portfolio.total_value_usd)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Trades Summary by Chain */}
          {totalTrades > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase text-slate-400">Recent Trades by Chain</p>
              {Object.entries(tradesByChain).map(([chain, trades]) => {
                if (!trades?.length) return null;
                const config = CHAIN_CONFIG[chain];
                
                return (
                  <div
                    key={chain}
                    className="p-3 rounded-lg border border-white/5"
                    style={{ backgroundColor: `${config.color}05` }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span>{config.icon}</span>
                        <span className="text-sm font-medium text-white">{config.name}</span>
                        <Badge className="text-[9px]" style={{ backgroundColor: `${config.color}20`, color: config.color }}>
                          {trades.length} trades
                        </Badge>
                      </div>
                    </div>
                    <div className="space-y-1">
                      {trades.slice(0, 3).map((trade, i) => (
                        <div key={i} className="flex items-center justify-between text-[10px]">
                          <span className="text-slate-400">
                            {trade.token_out_symbol || trade.token_out_address?.slice(0, 6)} → {trade.token_in_symbol || trade.token_in_address?.slice(0, 6)}
                          </span>
                          <span className="text-slate-500">
                            {new Date(trade.timestamp).toLocaleDateString()}
                          </span>
                        </div>
                      ))}
                      {trades.length > 3 && (
                        <p className="text-[10px] text-slate-500">+ {trades.length - 3} more...</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Auto-scan Toggle */}
          <div className="flex items-center justify-between p-2 rounded-lg bg-white/5">
            <span className="text-xs text-slate-400">Auto-scan on wallet connect</span>
            <button
              onClick={() => setAutoScanEnabled(!autoScanEnabled)}
              className={`w-10 h-5 rounded-full transition-colors relative ${autoScanEnabled ? 'bg-[#00FFA3]' : 'bg-slate-600'}`}
            >
              <span
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${autoScanEnabled ? 'left-5' : 'left-0.5'}`}
              />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
