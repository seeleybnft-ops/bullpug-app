/**
 * Portfolio Dashboard - Unified multi-chain portfolio view
 * 
 * Displays combined holdings across Solana and EVM wallets with
 * real-time prices and 24h change indicators.
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useAccount, useChainId } from 'wagmi';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Wallet, RefreshCw, TrendingUp, TrendingDown, DollarSign,
  Coins, PieChart, ArrowUpRight, ArrowDownRight, Loader2,
  ExternalLink, Copy, Check
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Chain colors
const CHAIN_COLORS = {
  ethereum: '#627EEA',
  base: '#0052FF',
  arbitrum: '#28A0F0',
  solana: '#9945FF',
};

export default function PortfolioDashboard() {
  const { publicKey: solanaPublicKey, connected: solanaConnected } = useWallet();
  const { address: evmAddress, isConnected: evmConnected } = useAccount();

  const [portfolio, setPortfolio] = useState(null);
  const [prices, setPrices] = useState({ ETH: { usd: 0 }, SOL: { usd: 0 } });
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Fetch portfolio data
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
      setLastUpdated(new Date());
      toast.success('Portfolio updated');
    } catch (e) {
      console.error('Portfolio fetch error:', e);
      toast.error('Failed to fetch portfolio');
    }
    setLoading(false);
  }, [solanaConnected, evmConnected, solanaPublicKey, evmAddress]);

  // Fetch prices
  const fetchPrices = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/portfolio/prices`);
      setPrices(data);
    } catch (e) {
      console.error('Price fetch error:', e);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, 60000); // Update prices every minute
    return () => clearInterval(interval);
  }, [fetchPrices]);

  // Copy address to clipboard
  const copyAddress = (address, type) => {
    const done = () => { setCopied(type); setTimeout(() => setCopied(null), 2000); toast.success('Address copied'); };
    const fallback = () => { try { const ta = document.createElement("textarea"); ta.value = address; ta.style.position = "fixed"; ta.style.left = "-9999px"; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta); done(); } catch { toast.error("Copy failed"); } };
    if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(address).then(done, fallback); } else { fallback(); }
  };

  // Format currency
  const formatUSD = (value) => {
    if (!value && value !== 0) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  // Format token balance
  const formatBalance = (balance, decimals = 4) => {
    if (!balance && balance !== 0) return '0';
    if (balance < 0.0001) return '<0.0001';
    return balance.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: decimals,
    });
  };

  // Calculate percentage change color
  const getChangeColor = (change) => {
    if (!change) return 'text-slate-400';
    return change >= 0 ? 'text-[#00FFA3]' : 'text-red-400';
  };

  const hasWalletConnected = solanaConnected || evmConnected;

  if (!hasWalletConnected) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center border border-white/5">
        <Wallet className="w-16 h-16 mx-auto mb-6 text-slate-600" />
        <h3 className="text-xl font-bold text-white mb-2">Connect Your Wallet</h3>
        <p className="text-slate-500 text-sm mb-4">
          Connect a Solana or EVM wallet to view your portfolio
        </p>
        <p className="text-slate-600 text-xs">
          Supports Ethereum, Base, Arbitrum, and Solana
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight">
            <span className="text-white">MY </span>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00C2FF] to-[#00FFA3]">
              PORTFOLIO
            </span>
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Unified view across all connected wallets
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-slate-600">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
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
        </div>
      </div>

      {/* Connected Wallets */}
      <div className="flex flex-wrap gap-3">
        {solanaConnected && solanaPublicKey && (
          <div
            onClick={() => copyAddress(solanaPublicKey.toBase58(), 'solana')}
            className="flex items-center gap-2 px-4 py-2 bg-[#9945FF]/10 border border-[#9945FF]/30 rounded-xl cursor-pointer hover:bg-[#9945FF]/20 transition-colors"
          >
            <span className="text-[#9945FF] text-lg">◎</span>
            <span className="text-sm text-white font-mono">
              {solanaPublicKey.toBase58().slice(0, 6)}...{solanaPublicKey.toBase58().slice(-4)}
            </span>
            {copied === 'solana' ? (
              <Check className="w-3 h-3 text-[#00FFA3]" />
            ) : (
              <Copy className="w-3 h-3 text-slate-400" />
            )}
          </div>
        )}
        {evmConnected && evmAddress && (
          <div
            onClick={() => copyAddress(evmAddress, 'evm')}
            className="flex items-center gap-2 px-4 py-2 bg-[#627EEA]/10 border border-[#627EEA]/30 rounded-xl cursor-pointer hover:bg-[#627EEA]/20 transition-colors"
          >
            <span className="text-[#627EEA] text-lg">⟠</span>
            <span className="text-sm text-white font-mono">
              {evmAddress.slice(0, 6)}...{evmAddress.slice(-4)}
            </span>
            {copied === 'evm' ? (
              <Check className="w-3 h-3 text-[#00FFA3]" />
            ) : (
              <Copy className="w-3 h-3 text-slate-400" />
            )}
          </div>
        )}
      </div>

      {/* Price Ticker */}
      <div className="flex gap-4">
        <div className="glass-card rounded-xl p-4 border border-white/5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#627EEA]/20 flex items-center justify-center text-lg">
            ⟠
          </div>
          <div>
            <p className="text-xs text-slate-500">ETH Price</p>
            <p className="text-lg font-bold text-white">{formatUSD(prices.ETH?.usd)}</p>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4 border border-white/5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#9945FF]/20 flex items-center justify-center text-lg">
            ◎
          </div>
          <div>
            <p className="text-xs text-slate-500">SOL Price</p>
            <p className="text-lg font-bold text-white">{formatUSD(prices.SOL?.usd)}</p>
          </div>
        </div>
      </div>

      {/* Portfolio Content */}
      {!portfolio ? (
        <div className="glass-card rounded-2xl p-12 text-center border border-white/5">
          <PieChart className="w-12 h-12 mx-auto mb-4 text-slate-700" />
          <p className="text-slate-500 mb-4">Click "Refresh" to load your portfolio</p>
          <Button
            onClick={fetchPortfolio}
            disabled={loading}
            className="bg-gradient-to-r from-[#00C2FF] to-[#00FFA3] text-black font-bold rounded-xl px-6"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Coins className="w-4 h-4 mr-2" />
            )}
            Load Portfolio
          </Button>
        </div>
      ) : (
        <>
          {/* Total Value */}
          <div className="glass-card rounded-2xl p-6 border border-white/5 bg-gradient-to-br from-[#00C2FF]/5 to-[#00FFA3]/5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 uppercase tracking-wider mb-1">Total Portfolio Value</p>
                <p className="text-4xl font-black text-white">
                  {formatUSD(portfolio.total_value_usd)}
                </p>
                <p className="text-sm text-slate-500 mt-1">
                  {portfolio.total_tokens} tokens across {(portfolio.chains?.length || 0) + (portfolio.solana ? 1 : 0)} chains
                </p>
              </div>
              <div className="w-20 h-20 rounded-full bg-gradient-to-r from-[#00C2FF] to-[#00FFA3] flex items-center justify-center">
                <DollarSign className="w-10 h-10 text-black" />
              </div>
            </div>
          </div>

          {/* Chain Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* EVM Chains */}
            {portfolio.chains?.map((chain) => (
              <ChainCard key={chain.chain} chain={chain} formatUSD={formatUSD} formatBalance={formatBalance} />
            ))}

            {/* Solana */}
            {portfolio.solana && (
              <ChainCard chain={portfolio.solana} formatUSD={formatUSD} formatBalance={formatBalance} />
            )}
          </div>

          {/* Token List */}
          <div className="glass-card rounded-2xl p-6 border border-white/5">
            <h3 className="text-sm font-bold uppercase text-[#00C2FF] mb-4 flex items-center gap-2">
              <Coins className="w-4 h-4" />
              All Holdings
            </h3>

            <div className="space-y-2">
              {/* Native tokens first */}
              {portfolio.chains?.map((chain) => (
                <TokenRow
                  key={`${chain.chain}-native`}
                  token={{
                    chain: chain.chain,
                    chain_name: chain.chain_name,
                    chain_icon: chain.chain_icon,
                    symbol: chain.native_symbol,
                    name: chain.chain_name,
                    balance: chain.native_balance,
                    value_usd: chain.native_value_usd,
                    is_native: true,
                  }}
                  formatUSD={formatUSD}
                  formatBalance={formatBalance}
                />
              ))}
              {portfolio.solana && (
                <TokenRow
                  token={{
                    chain: 'solana',
                    chain_name: 'Solana',
                    chain_icon: '◎',
                    symbol: 'SOL',
                    name: 'Solana',
                    balance: portfolio.solana.native_balance,
                    value_usd: portfolio.solana.native_value_usd,
                    is_native: true,
                  }}
                  formatUSD={formatUSD}
                  formatBalance={formatBalance}
                />
              )}

              {/* Other tokens */}
              {portfolio.chains?.flatMap((chain) => chain.tokens).map((token, i) => (
                <TokenRow key={`token-${i}`} token={token} formatUSD={formatUSD} formatBalance={formatBalance} />
              ))}
              {portfolio.solana?.tokens?.map((token, i) => (
                <TokenRow key={`sol-token-${i}`} token={token} formatUSD={formatUSD} formatBalance={formatBalance} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Chain Card Component
function ChainCard({ chain, formatUSD, formatBalance }) {
  const color = CHAIN_COLORS[chain.chain] || '#627EEA';

  return (
    <div className="glass-card rounded-xl p-5 border border-white/5 hover:border-white/10 transition-colors">
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {chain.chain_icon}
        </div>
        <div>
          <p className="font-bold text-white">{chain.chain_name}</p>
          <p className="text-xs text-slate-500">{chain.token_count + 1} assets</p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">Native Balance</span>
          <span className="text-sm font-medium text-white">
            {formatBalance(chain.native_balance)} {chain.native_symbol}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">Value</span>
          <span className="text-sm font-bold text-[#00FFA3]">
            {formatUSD(chain.total_value_usd)}
          </span>
        </div>
      </div>
    </div>
  );
}

// Token Row Component
function TokenRow({ token, formatUSD, formatBalance }) {
  const color = CHAIN_COLORS[token.chain] || '#627EEA';

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-black/20 hover:bg-black/30 transition-colors">
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
          style={{ backgroundColor: `${color}15`, color }}
        >
          {token.chain_icon}
        </div>
        <div>
          <p className="text-sm font-medium text-white">{token.symbol}</p>
          <p className="text-[10px] text-slate-500">{token.chain_name}</p>
        </div>
      </div>

      <div className="text-right">
        <p className="text-sm text-white">{formatBalance(token.balance)}</p>
        <p className="text-xs text-[#00FFA3]">{formatUSD(token.value_usd)}</p>
      </div>
    </div>
  );
}
