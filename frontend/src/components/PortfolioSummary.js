/**
 * Portfolio Summary Component
 * 
 * Compact portfolio view for embedding in the combined Journal page.
 * Shows token balances across connected wallets.
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useAccount, useChainId } from 'wagmi';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Wallet, RefreshCw, TrendingUp, DollarSign, Loader2, ExternalLink, ChevronRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CHAIN_COLORS = {
  ethereum: '#627EEA',
  base: '#0052FF',
  arbitrum: '#28A0F0',
  solana: '#9945FF',
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
    } catch (e) {
      console.error('Portfolio fetch error:', e);
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
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatBalance = (balance) => {
    if (!balance) return '0';
    if (balance < 0.001) return '<0.001';
    return balance.toLocaleString(undefined, { maximumFractionDigits: 4 });
  };

  const hasWalletConnected = solanaConnected || evmConnected;

  return (
    <div className="glass-card rounded-2xl p-5 border border-white/5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold uppercase text-[#00C2FF] flex items-center gap-2">
          <Wallet className="w-4 h-4" />
          Portfolio Overview
        </h3>
        
        {hasWalletConnected && (
          <Button
            onClick={fetchPortfolio}
            disabled={loading}
            variant="ghost"
            size="sm"
            className="text-slate-400 hover:text-white h-7 px-2"
          >
            {loading ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <RefreshCw className="w-3 h-3" />
            )}
          </Button>
        )}
      </div>

      {/* Price Ticker */}
      <div className="flex gap-3 mb-4">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-black/30 rounded-lg">
          <span className="text-[#627EEA]">⟠</span>
          <span className="text-xs text-white font-medium">{formatUSD(prices.ETH?.usd)}</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-black/30 rounded-lg">
          <span className="text-[#9945FF]">◎</span>
          <span className="text-xs text-white font-medium">{formatUSD(prices.SOL?.usd)}</span>
        </div>
      </div>

      {!hasWalletConnected ? (
        <div className="py-6 text-center">
          <Wallet className="w-8 h-8 mx-auto mb-2 text-slate-700" />
          <p className="text-xs text-slate-500">Connect wallet to view portfolio</p>
        </div>
      ) : !portfolio ? (
        <div className="py-6 text-center">
          <Button
            onClick={fetchPortfolio}
            disabled={loading}
            variant="outline"
            className="border-white/20 text-white text-xs"
          >
            {loading ? (
              <Loader2 className="w-3 h-3 mr-2 animate-spin" />
            ) : (
              <DollarSign className="w-3 h-3 mr-2" />
            )}
            Load Portfolio
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Total Value */}
          <div className="bg-gradient-to-r from-[#00C2FF]/10 to-[#00FFA3]/10 rounded-xl p-4 border border-white/5">
            <p className="text-[10px] text-slate-400 uppercase mb-1">Total Value</p>
            <p className="text-2xl font-black text-white">{formatUSD(portfolio.total_value_usd)}</p>
            <p className="text-xs text-slate-500">
              {portfolio.total_tokens} tokens across {(portfolio.chains?.length || 0) + (portfolio.solana ? 1 : 0)} chains
            </p>
          </div>

          {/* Chain Breakdown */}
          <div className="space-y-2">
            {portfolio.chains?.map((chain) => (
              <ChainRow key={chain.chain} chain={chain} formatUSD={formatUSD} formatBalance={formatBalance} />
            ))}
            {portfolio.solana && (
              <ChainRow chain={portfolio.solana} formatUSD={formatUSD} formatBalance={formatBalance} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ChainRow({ chain, formatUSD, formatBalance }) {
  const color = CHAIN_COLORS[chain.chain] || '#627EEA';
  
  return (
    <div className="flex items-center justify-between p-3 bg-black/20 rounded-lg">
      <div className="flex items-center gap-2">
        <div 
          className="w-7 h-7 rounded-lg flex items-center justify-center text-sm"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {chain.chain_icon}
        </div>
        <div>
          <p className="text-xs font-medium text-white">{chain.chain_name}</p>
          <p className="text-[10px] text-slate-500">
            {formatBalance(chain.native_balance)} {chain.native_symbol}
          </p>
        </div>
      </div>
      <p className="text-xs font-bold text-[#00FFA3]">{formatUSD(chain.total_value_usd)}</p>
    </div>
  );
}
