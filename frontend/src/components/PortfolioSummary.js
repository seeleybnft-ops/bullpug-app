/**
 * Portfolio Summary Component
 * 
 * Shows portfolio value and token holdings across connected wallets.
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useAccount, useChainId } from 'wagmi';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Wallet, RefreshCw, DollarSign, Loader2, Coins, TrendingUp, TrendingDown
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CHAIN_COLORS = {
  ethereum: '#627EEA',
  base: '#0052FF',
  arbitrum: '#28A0F0',
  solana: '#9945FF',
};

const CHAIN_ICONS = {
  ethereum: '⟠',
  base: '🔵',
  arbitrum: '🔷',
  solana: '◎',
};

export default function PortfolioSummary() {
  const { publicKey: solanaPublicKey, connected: solanaConnected } = useWallet();
  const { address: evmAddress, isConnected: evmConnected } = useAccount();

  const [portfolio, setPortfolio] = useState(null);
  const [prices, setPrices] = useState({ ETH: { usd: 0 }, SOL: { usd: 0 } });
  const [loading, setLoading] = useState(false);

  const fetchPrices = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/portfolio/prices`);
      setPrices(data);
    } catch (e) {
      console.error('Price fetch error:', e);
    }
  }, []);

  const fetchPortfolio = useCallback(async () => {
    if (!solanaConnected && !evmConnected) return;

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (evmConnected && evmAddress) {
        params.append('evm_address', evmAddress);
      }
      if (solanaConnected && solanaPublicKey) {
        params.append('solana_address', solanaPublicKey.toBase58());
      }

      const { data } = await axios.get(`${API}/portfolio/combined?${params.toString()}`);
      setPortfolio(data);
      toast.success('Portfolio loaded');
    } catch (e) {
      console.error('Portfolio fetch error:', e);
      toast.error('Failed to load portfolio');
    }
    setLoading(false);
  }, [solanaConnected, evmConnected, solanaPublicKey, evmAddress]);

  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, 60000);
    return () => clearInterval(interval);
  }, [fetchPrices]);

  const formatUSD = (value) => {
    if (!value && value !== 0) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatBalance = (balance, decimals = 4) => {
    if (!balance) return '0';
    if (balance < 0.0001) return '<0.0001';
    return balance.toLocaleString(undefined, { maximumFractionDigits: decimals });
  };

  const hasWalletConnected = solanaConnected || evmConnected;

  // Collect all holdings from portfolio
  const getAllHoldings = () => {
    if (!portfolio) return [];
    
    const holdings = [];
    
    // Add EVM chain native tokens and tokens
    portfolio.chains?.forEach(chain => {
      // Native token
      if (chain.native_balance > 0) {
        holdings.push({
          chain: chain.chain,
          chainName: chain.chain_name,
          chainIcon: chain.chain_icon,
          symbol: chain.native_symbol,
          name: chain.chain_name,
          balance: chain.native_balance,
          valueUsd: chain.native_value_usd,
          isNative: true,
        });
      }
      // Other tokens
      chain.tokens?.forEach(token => {
        if (token.balance > 0.0001) {
          holdings.push({
            chain: token.chain,
            chainName: token.chain_name,
            chainIcon: token.chain_icon,
            symbol: token.symbol,
            name: token.name,
            balance: token.balance,
            valueUsd: token.value_usd,
            isNative: false,
            isStablecoin: token.is_stablecoin,
          });
        }
      });
    });
    
    // Add Solana
    if (portfolio.solana) {
      if (portfolio.solana.native_balance > 0) {
        holdings.push({
          chain: 'solana',
          chainName: 'Solana',
          chainIcon: '◎',
          symbol: 'SOL',
          name: 'Solana',
          balance: portfolio.solana.native_balance,
          valueUsd: portfolio.solana.native_value_usd,
          isNative: true,
        });
      }
      portfolio.solana.tokens?.forEach(token => {
        if (token.balance > 0.0001) {
          holdings.push({
            chain: 'solana',
            chainName: 'Solana',
            chainIcon: '◎',
            symbol: token.symbol,
            name: token.name || 'SPL Token',
            balance: token.balance,
            valueUsd: token.value_usd,
            isNative: false,
          });
        }
      });
    }
    
    // Sort by value (highest first)
    return holdings.sort((a, b) => (b.valueUsd || 0) - (a.valueUsd || 0));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-[#00FFA3]" />
            Portfolio Value
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Multi-chain holdings across connected wallets
          </p>
        </div>
        
        {hasWalletConnected && (
          <Button
            onClick={fetchPortfolio}
            disabled={loading}
            className="bg-[#00C2FF]/10 text-[#00C2FF] border border-[#00C2FF]/30 hover:bg-[#00C2FF]/20 rounded-xl"
            data-testid="refresh-portfolio-btn"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Refresh
          </Button>
        )}
      </div>

      {/* Price Ticker */}
      <div className="flex gap-3">
        <div className="flex items-center gap-2 px-4 py-2 bg-black/30 rounded-xl border border-white/5">
          <span className="text-[#627EEA] text-lg">⟠</span>
          <div>
            <p className="text-[10px] text-slate-500">ETH</p>
            <p className="text-sm text-white font-bold">{formatUSD(prices.ETH?.usd)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-black/30 rounded-xl border border-white/5">
          <span className="text-[#9945FF] text-lg">◎</span>
          <div>
            <p className="text-[10px] text-slate-500">SOL</p>
            <p className="text-sm text-white font-bold">{formatUSD(prices.SOL?.usd)}</p>
          </div>
        </div>
      </div>

      {!hasWalletConnected ? (
        <div className="glass-card rounded-2xl p-12 text-center border border-white/5">
          <Wallet className="w-12 h-12 mx-auto mb-4 text-slate-600" />
          <p className="text-slate-400 mb-2">Connect wallet to view portfolio</p>
          <p className="text-xs text-slate-600">Supports Ethereum, Base, Arbitrum, and Solana</p>
        </div>
      ) : !portfolio ? (
        <div className="glass-card rounded-2xl p-12 text-center border border-white/5">
          <Coins className="w-12 h-12 mx-auto mb-4 text-slate-600" />
          <p className="text-slate-400 mb-4">Click "Refresh" to load your holdings</p>
          <Button
            onClick={fetchPortfolio}
            disabled={loading}
            className="bg-gradient-to-r from-[#00C2FF] to-[#00FFA3] text-black font-bold rounded-xl px-6"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <DollarSign className="w-4 h-4 mr-2" />
            )}
            Load Portfolio
          </Button>
        </div>
      ) : (
        <>
          {/* Total Value Card */}
          <div className="glass-card rounded-2xl p-6 border border-white/5 bg-gradient-to-br from-[#00C2FF]/5 to-[#00FFA3]/5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 uppercase tracking-wider mb-1">Total Portfolio Value</p>
                <p className="text-4xl font-black text-white">
                  {formatUSD(portfolio.total_value_usd)}
                </p>
                <p className="text-sm text-slate-500 mt-1">
                  {portfolio.total_tokens} assets across {(portfolio.chains?.length || 0) + (portfolio.solana ? 1 : 0)} chains
                </p>
              </div>
              <div className="w-16 h-16 rounded-full bg-gradient-to-r from-[#00C2FF] to-[#00FFA3] flex items-center justify-center">
                <DollarSign className="w-8 h-8 text-black" />
              </div>
            </div>
          </div>

          {/* Chain Breakdown */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {portfolio.chains?.map((chain) => (
              <div 
                key={chain.chain} 
                className="glass-card rounded-xl p-4 border border-white/5"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span 
                    className="text-lg"
                    style={{ color: CHAIN_COLORS[chain.chain] }}
                  >
                    {chain.chain_icon}
                  </span>
                  <span className="text-xs text-slate-400">{chain.chain_name}</span>
                </div>
                <p className="text-lg font-bold text-white">{formatUSD(chain.total_value_usd)}</p>
                <p className="text-[10px] text-slate-500">{chain.token_count + 1} assets</p>
              </div>
            ))}
            {portfolio.solana && (
              <div className="glass-card rounded-xl p-4 border border-white/5">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg text-[#9945FF]">◎</span>
                  <span className="text-xs text-slate-400">Solana</span>
                </div>
                <p className="text-lg font-bold text-white">{formatUSD(portfolio.solana.total_value_usd)}</p>
                <p className="text-[10px] text-slate-500">{portfolio.solana.token_count + 1} assets</p>
              </div>
            )}
          </div>

          {/* Holdings List */}
          <div className="glass-card rounded-2xl p-5 border border-white/5">
            <h4 className="text-sm font-bold uppercase text-[#00C2FF] mb-4 flex items-center gap-2">
              <Coins className="w-4 h-4" />
              All Holdings ({getAllHoldings().length})
            </h4>
            
            {getAllHoldings().length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-slate-500 text-sm">No holdings found</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {getAllHoldings().map((holding, index) => {
                  const color = CHAIN_COLORS[holding.chain] || '#627EEA';
                  
                  return (
                    <div 
                      key={`${holding.chain}-${holding.symbol}-${index}`}
                      className="flex items-center justify-between p-3 bg-black/20 rounded-xl hover:bg-black/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div 
                          className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                          style={{ backgroundColor: `${color}15`, color }}
                        >
                          {holding.chainIcon}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-bold text-white">{holding.symbol}</p>
                            {holding.isNative && (
                              <span className="text-[8px] px-1.5 py-0.5 bg-white/10 rounded text-slate-400">NATIVE</span>
                            )}
                            {holding.isStablecoin && (
                              <span className="text-[8px] px-1.5 py-0.5 bg-[#00FFA3]/20 rounded text-[#00FFA3]">STABLE</span>
                            )}
                          </div>
                          <p className="text-[10px] text-slate-500">{holding.chainName}</p>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <p className="text-sm font-medium text-white">
                          {formatBalance(holding.balance)} {holding.symbol}
                        </p>
                        <p className="text-xs text-[#00FFA3]">
                          {holding.valueUsd ? formatUSD(holding.valueUsd) : '-'}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
