/**
 * DetectedTrades Component - Auto-import trades from connected wallets
 * 
 * P1 UX Enhancements:
 * - Auto-scan on wallet connect
 * - Better empty states with guidance
 * - Progress indicator during scan
 * - Estimated value display
 * - Improved mobile responsiveness
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useAccount, useChainId } from 'wagmi';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  RefreshCw, Download, Check, X, ExternalLink, Wallet,
  ArrowRightLeft, AlertCircle, Loader2, ChevronDown, Scan, Info
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Chain configurations
const CHAINS = {
  ethereum: { name: 'Ethereum', color: '#627EEA', icon: '⟠' },
  base: { name: 'Base', color: '#0052FF', icon: '🔵' },
  arbitrum: { name: 'Arbitrum', color: '#28A0F0', icon: '🔷' },
  solana: { name: 'Solana', color: '#9945FF', icon: '◎' },
};

export default function DetectedTrades({ onImport }) {
  const { publicKey: solanaPublicKey, connected: solanaConnected } = useWallet();
  const { address: evmAddress, isConnected: evmConnected } = useAccount();
  const evmChainId = useChainId();

  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTrades, setSelectedTrades] = useState(new Set());
  const [selectedChain, setSelectedChain] = useState('all');
  const [importing, setImporting] = useState(false);
  const [showChainDropdown, setShowChainDropdown] = useState(false);
  const [scanProgress, setScanProgress] = useState('');
  const [hasScanned, setHasScanned] = useState(false);

  // Map chain ID to chain name
  const getEvmChainName = (chainId) => {
    switch (chainId) {
      case 1: return 'ethereum';
      case 8453: return 'base';
      case 42161: return 'arbitrum';
      default: return 'ethereum';
    }
  };

  // Fetch trades from connected wallets
  const fetchTrades = useCallback(async () => {
    setLoading(true);
    setTrades([]);
    setHasScanned(true);
    
    const allTrades = [];
    
    try {
      // Fetch from Solana if connected
      if (solanaConnected && solanaPublicKey) {
        setScanProgress('Scanning Solana transactions...');
        try {
          const { data } = await axios.get(
            `${API}/wallet-trades/solana/${solanaPublicKey.toBase58()}?limit=30`
          );
          if (data.trades) {
            allTrades.push(...data.trades);
          }
        } catch (e) {
          console.error('Solana fetch error:', e);
        }
      }
      
      // Fetch from EVM if connected
      if (evmConnected && evmAddress) {
        const evmChain = getEvmChainName(evmChainId);
        setScanProgress(`Scanning ${CHAINS[evmChain]?.name || 'EVM'} transactions...`);
        try {
          const { data } = await axios.get(
            `${API}/wallet-trades/evm/${evmAddress}?chain=${evmChain}&limit=30`
          );
          if (data.trades) {
            allTrades.push(...data.trades);
          }
        } catch (e) {
          console.error('EVM fetch error:', e);
          // Try other chains if the current one fails
          for (const chain of ['ethereum', 'base', 'arbitrum']) {
            if (chain !== evmChain) {
              setScanProgress(`Scanning ${CHAINS[chain]?.name} transactions...`);
              try {
                const { data } = await axios.get(
                  `${API}/wallet-trades/evm/${evmAddress}?chain=${chain}&limit=20`
                );
                if (data.trades) {
                  allTrades.push(...data.trades);
                }
              } catch (innerE) {
                // Silently continue
              }
            }
          }
        }
      }
      
      // Sort by timestamp descending
      allTrades.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      setTrades(allTrades);
      setScanProgress('');
      
      if (allTrades.length === 0 && (solanaConnected || evmConnected)) {
        toast.info('No recent DEX trades detected');
      } else if (allTrades.length > 0) {
        toast.success(`Found ${allTrades.length} trades`);
      }
    } catch (e) {
      console.error('Error fetching trades:', e);
      toast.error('Failed to fetch trades');
      setScanProgress('');
    }
    
    setLoading(false);
  }, [solanaConnected, solanaPublicKey, evmConnected, evmAddress, evmChainId]);

  // Auto-scan when wallet connects (only once)
  useEffect(() => {
    if ((solanaConnected || evmConnected) && !hasScanned) {
      fetchTrades();
    }
  }, [solanaConnected, evmConnected, hasScanned, fetchTrades]);

  // Toggle trade selection
  const toggleTradeSelection = (txHash) => {
    setSelectedTrades(prev => {
      const newSet = new Set(prev);
      if (newSet.has(txHash)) {
        newSet.delete(txHash);
      } else {
        newSet.add(txHash);
      }
      return newSet;
    });
  };

  // Select all visible trades
  const selectAll = () => {
    const filtered = filteredTrades;
    if (selectedTrades.size === filtered.length) {
      setSelectedTrades(new Set());
    } else {
      setSelectedTrades(new Set(filtered.map(t => t.tx_hash)));
    }
  };

  // Import selected trades
  const importSelected = async () => {
    if (selectedTrades.size === 0) {
      toast.error('Select at least one trade to import');
      return;
    }
    
    setImporting(true);
    
    try {
      const tradesToImport = trades.filter(t => selectedTrades.has(t.tx_hash));
      const walletAddress = solanaPublicKey?.toBase58() || evmAddress;
      
      const { data } = await axios.post(
        `${API}/wallet-trades/import-to-journal?wallet_address=${walletAddress}`,
        tradesToImport
      );
      
      toast.success(data.message);
      setSelectedTrades(new Set());
      
      // Refresh parent component
      if (onImport) {
        onImport();
      }
      
      // Remove imported trades from the list
      setTrades(prev => prev.filter(t => !selectedTrades.has(t.tx_hash)));
    } catch (e) {
      toast.error('Failed to import trades');
      console.error(e);
    }
    
    setImporting(false);
  };

  // Filter trades by chain
  const filteredTrades = selectedChain === 'all' 
    ? trades 
    : trades.filter(t => t.chain === selectedChain);

  // Check if any wallet is connected
  const hasWalletConnected = solanaConnected || evmConnected;

  // Calculate chain counts for filter badges
  const chainCounts = trades.reduce((acc, t) => {
    acc[t.chain] = (acc[t.chain] || 0) + 1;
    return acc;
  }, {});

  if (!hasWalletConnected) {
    return (
      <div className="glass-card rounded-xl p-8 text-center border border-white/5" data-testid="import-no-wallet">
        <Wallet className="w-12 h-12 mx-auto mb-4 text-slate-600" />
        <p className="text-slate-400 text-sm mb-2 font-medium">Connect a wallet to detect trades</p>
        <p className="text-slate-600 text-xs mb-4">
          Supports Solana, Ethereum, Base, and Arbitrum DEX swaps
        </p>
        <div className="flex justify-center gap-2 flex-wrap">
          {Object.entries(CHAINS).map(([key, chain]) => (
            <span key={key} className="text-[10px] px-2 py-1 rounded-full bg-white/5 text-slate-500">
              {chain.icon} {chain.name}
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/5" data-testid="detected-trades">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-sm font-bold uppercase text-[#00C2FF] flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4" />
            Auto-Import Trades
            <Badge className="bg-[#00C2FF]/10 text-[#00C2FF] text-[10px]">BETA</Badge>
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Automatically detect and import DEX swaps from your wallets
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Chain Filter */}
          <div className="relative">
            <button
              onClick={() => setShowChainDropdown(!showChainDropdown)}
              className="flex items-center gap-2 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-xs text-white hover:border-white/20 transition-colors"
              data-testid="chain-filter-btn"
            >
              {selectedChain === 'all' ? (
                <span>All Chains</span>
              ) : (
                <>
                  <span>{CHAINS[selectedChain]?.icon}</span>
                  <span>{CHAINS[selectedChain]?.name}</span>
                </>
              )}
              <ChevronDown className={`w-3 h-3 transition-transform ${showChainDropdown ? 'rotate-180' : ''}`} />
            </button>
            
            {showChainDropdown && (
              <div className="absolute z-10 right-0 mt-1 w-44 bg-[#0a0a12] border border-white/10 rounded-lg shadow-xl overflow-hidden">
                <button
                  onClick={() => { setSelectedChain('all'); setShowChainDropdown(false); }}
                  className={`w-full px-3 py-2 text-left text-xs hover:bg-white/5 flex items-center justify-between ${selectedChain === 'all' ? 'bg-white/5 text-[#00C2FF]' : 'text-white'}`}
                >
                  <span>All Chains</span>
                  <span className="text-slate-500">{trades.length}</span>
                </button>
                {Object.entries(CHAINS).map(([key, chain]) => (
                  <button
                    key={key}
                    onClick={() => { setSelectedChain(key); setShowChainDropdown(false); }}
                    className={`w-full px-3 py-2 text-left text-xs hover:bg-white/5 flex items-center justify-between ${selectedChain === key ? 'bg-white/5 text-[#00C2FF]' : 'text-white'}`}
                  >
                    <span className="flex items-center gap-2">
                      <span>{chain.icon}</span>
                      <span>{chain.name}</span>
                    </span>
                    <span className="text-slate-500">{chainCounts[key] || 0}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          
          <Button
            onClick={fetchTrades}
            disabled={loading}
            variant="outline"
            className="border-white/20 text-slate-400 hover:text-white rounded-lg px-4 py-2 text-xs"
            data-testid="fetch-trades-btn"
          >
            {loading ? (
              <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
            ) : (
              <Scan className="w-3 h-3 mr-1.5" />
            )}
            {loading ? 'Scanning...' : 'Scan Wallets'}
          </Button>
        </div>
      </div>

      {/* Connected Wallets Info */}
      <div className="flex flex-wrap gap-2 mb-4">
        {solanaConnected && solanaPublicKey && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#9945FF]/10 border border-[#9945FF]/30 rounded-lg">
            <span className="text-[#9945FF]">◎</span>
            <span className="text-xs text-[#9945FF]">
              {solanaPublicKey.toBase58().slice(0, 4)}...{solanaPublicKey.toBase58().slice(-4)}
            </span>
            <Check className="w-3 h-3 text-[#9945FF]" />
          </div>
        )}
        {evmConnected && evmAddress && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#627EEA]/10 border border-[#627EEA]/30 rounded-lg">
            <span className="text-[#627EEA]">⟠</span>
            <span className="text-xs text-[#627EEA]">
              {evmAddress.slice(0, 6)}...{evmAddress.slice(-4)}
            </span>
            <Check className="w-3 h-3 text-[#627EEA]" />
          </div>
        )}
      </div>

      {/* Trades List */}
      {loading ? (
        <div className="py-12 text-center">
          <Loader2 className="w-8 h-8 mx-auto mb-3 text-[#00C2FF] animate-spin" />
          <p className="text-slate-400 text-sm font-medium">{scanProgress || 'Scanning blockchain...'}</p>
          <p className="text-slate-600 text-xs mt-1">This may take a few seconds</p>
        </div>
      ) : filteredTrades.length === 0 ? (
        <div className="py-12 text-center">
          {!hasScanned ? (
            <>
              <Scan className="w-10 h-10 mx-auto mb-3 text-[#00C2FF]/50" />
              <p className="text-slate-400 text-sm font-medium mb-1">Ready to scan your wallets</p>
              <p className="text-slate-600 text-xs mb-4">
                Click "Scan Wallets" to detect recent DEX trades
              </p>
              <Button
                onClick={fetchTrades}
                className="bg-[#00C2FF]/20 text-[#00C2FF] hover:bg-[#00C2FF]/30 rounded-lg px-4 py-2 text-xs"
              >
                <Scan className="w-3 h-3 mr-1.5" />
                Start Scanning
              </Button>
            </>
          ) : trades.length === 0 ? (
            <>
              <AlertCircle className="w-10 h-10 mx-auto mb-3 text-slate-700" />
              <p className="text-slate-400 text-sm font-medium mb-1">No DEX trades found</p>
              <p className="text-slate-600 text-xs">
                Make some trades on DEXes like Jupiter, Uniswap, or Raydium to see them here
              </p>
            </>
          ) : (
            <>
              <AlertCircle className="w-10 h-10 mx-auto mb-3 text-slate-700" />
              <p className="text-slate-400 text-sm font-medium">No trades for {CHAINS[selectedChain]?.name}</p>
              <button 
                onClick={() => setSelectedChain('all')}
                className="text-[#00C2FF] text-xs mt-2 hover:underline"
              >
                Show all chains
              </button>
            </>
          )}
        </div>
      ) : (
        <>
          {/* Selection Controls */}
          <div className="flex items-center justify-between mb-3 pb-3 border-b border-white/5">
            <button
              onClick={selectAll}
              className="text-xs text-[#00C2FF] hover:text-white transition-colors"
              data-testid="select-all-btn"
            >
              {selectedTrades.size === filteredTrades.length ? 'Deselect All' : 'Select All'}
            </button>
            <span className="text-xs text-slate-500">
              {selectedTrades.size} of {filteredTrades.length} selected
            </span>
          </div>
          
          {/* Trades */}
          <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
            {filteredTrades.map((trade) => {
              const chain = CHAINS[trade.chain] || CHAINS.ethereum;
              const isSelected = selectedTrades.has(trade.tx_hash);
              
              return (
                <div
                  key={trade.tx_hash}
                  onClick={() => toggleTradeSelection(trade.tx_hash)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected 
                      ? 'bg-[#00C2FF]/5 border-[#00C2FF]/30' 
                      : 'bg-black/20 border-white/5 hover:border-white/10'
                  }`}
                  data-testid={`trade-item-${trade.tx_hash.slice(0, 8)}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                        isSelected ? 'bg-[#00C2FF] border-[#00C2FF]' : 'border-white/20'
                      }`}>
                        {isSelected && <Check className="w-3 h-3 text-black" />}
                      </div>
                      
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm" 
                        style={{ backgroundColor: `${chain.color}15`, color: chain.color }}>
                        {chain.icon}
                      </div>
                      
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-white">
                            {trade.token_out_symbol || trade.token_out_address?.slice(0, 6)} → {trade.token_in_symbol || trade.token_in_address?.slice(0, 6)}
                          </span>
                          <Badge className="text-[9px] bg-white/5 text-slate-400">
                            {trade.dex_protocol}
                          </Badge>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          {new Date(trade.timestamp).toLocaleDateString()} {new Date(trade.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <p className="text-xs text-red-400">-{trade.token_out_amount?.toFixed(4)}</p>
                        <p className="text-xs text-[#00FFA3]">+{trade.token_in_amount?.toFixed(4)}</p>
                      </div>
                      
                      <a
                        href={trade.explorer_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 rounded hover:bg-white/10 text-slate-500 hover:text-white transition-colors"
                        title="View on explorer"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* Import Button */}
          {selectedTrades.size > 0 && (
            <div className="mt-4 pt-4 border-t border-white/5">
              <Button
                onClick={importSelected}
                disabled={importing}
                className="w-full bg-gradient-to-r from-[#00C2FF] to-[#00FFA3] text-black font-bold rounded-xl py-4 text-sm uppercase"
                data-testid="import-trades-btn"
              >
                {importing ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Download className="w-4 h-4 mr-2" />
                )}
                Import {selectedTrades.size} Trade{selectedTrades.size > 1 ? 's' : ''} to Journal
              </Button>
            </div>
          )}

          {/* Help tip */}
          <div className="mt-4 p-3 rounded-lg bg-white/[0.02] border border-white/5">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
              <p className="text-[10px] text-slate-500 leading-relaxed">
                Imported trades will be added as draft entries in your journal. 
                You can edit entry/exit prices, add notes, and track your P&L.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
