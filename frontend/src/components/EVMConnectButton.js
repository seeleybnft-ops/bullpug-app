/**
 * EVM Wallet Connect Button - Connect to Ethereum, Base, Arbitrum wallets
 */

import { useState } from 'react';
import { useAccount, useConnect, useDisconnect, useChainId, useSwitchChain } from 'wagmi';
import { Button } from '@/components/ui/button';
import { Wallet, ChevronDown, LogOut, ExternalLink, Check, Loader2 } from 'lucide-react';

// Chain configurations
const CHAINS = [
  { id: 1, name: 'Ethereum', icon: '⟠', color: '#627EEA' },
  { id: 8453, name: 'Base', icon: '🔵', color: '#0052FF' },
  { id: 42161, name: 'Arbitrum', icon: '🔷', color: '#28A0F0' },
];

export default function EVMConnectButton() {
  const { address, isConnected } = useAccount();
  const { connectors, connect, isPending } = useConnect();
  const { disconnect } = useDisconnect();
  const chainId = useChainId();
  const { switchChain, isPending: isSwitching } = useSwitchChain();
  
  const [showMenu, setShowMenu] = useState(false);
  const [showChainMenu, setShowChainMenu] = useState(false);

  const currentChain = CHAINS.find(c => c.id === chainId) || CHAINS[0];

  const formatAddress = (addr) => {
    if (!addr) return '';
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  // Connected state
  if (isConnected && address) {
    return (
      <div className="relative">
        <button
          onClick={() => setShowMenu(!showMenu)}
          data-testid="evm-wallet-btn"
          className="flex items-center gap-2 px-3 py-2 bg-[#627EEA]/10 border border-[#627EEA]/30 rounded-full text-sm font-medium text-white hover:bg-[#627EEA]/20 transition-colors"
        >
          <span style={{ color: currentChain.color }}>{currentChain.icon}</span>
          <span>{formatAddress(address)}</span>
          <ChevronDown className={`w-3 h-3 text-slate-400 transition-transform ${showMenu ? 'rotate-180' : ''}`} />
        </button>
        
        {showMenu && (
          <div className="absolute right-0 mt-2 w-56 bg-[#0a0a12] border border-white/10 rounded-xl shadow-xl z-50 overflow-hidden">
            {/* Address */}
            <div className="p-3 border-b border-white/5">
              <p className="text-xs text-slate-500 mb-1">Connected Wallet</p>
              <div className="flex items-center justify-between">
                <span className="text-sm text-white font-mono">{formatAddress(address)}</span>
                <a
                  href={`https://etherscan.io/address/${address}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-white"
                >
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
            
            {/* Chain Switcher */}
            <div className="p-2 border-b border-white/5">
              <p className="text-[10px] text-slate-500 uppercase px-2 mb-1">Network</p>
              {CHAINS.map(chain => (
                <button
                  key={chain.id}
                  onClick={() => {
                    if (chain.id !== chainId) {
                      switchChain({ chainId: chain.id });
                    }
                    setShowMenu(false);
                  }}
                  disabled={isSwitching}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-colors ${
                    chain.id === chainId 
                      ? 'bg-white/5 text-white' 
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span>{chain.icon}</span>
                    <span>{chain.name}</span>
                  </div>
                  {chain.id === chainId && <Check className="w-3 h-3 text-[#00FFA3]" />}
                </button>
              ))}
            </div>
            
            {/* Disconnect */}
            <button
              onClick={() => { disconnect(); setShowMenu(false); }}
              className="w-full flex items-center gap-2 px-4 py-3 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="w-3 h-3" />
              Disconnect
            </button>
          </div>
        )}
      </div>
    );
  }

  // Disconnected state - show connect options
  return (
    <div className="relative">
      <Button
        onClick={() => setShowMenu(!showMenu)}
        disabled={isPending}
        data-testid="evm-connect-btn"
        className="bg-[#627EEA] hover:bg-[#627EEA]/80 text-white font-bold rounded-full px-4 py-2 text-xs"
      >
        {isPending ? (
          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
        ) : (
          <Wallet className="w-3 h-3 mr-1" />
        )}
        Connect EVM
      </Button>
      
      {showMenu && !isPending && (
        <div className="absolute right-0 mt-2 w-56 bg-[#0a0a12] border border-white/10 rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-3 border-b border-white/5">
            <p className="text-xs text-slate-500">Connect EVM Wallet</p>
          </div>
          <div className="p-2">
            {connectors.map((connector) => (
              <button
                key={connector.uid}
                onClick={() => {
                  connect({ connector });
                  setShowMenu(false);
                }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white hover:bg-white/5 transition-colors"
              >
                <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
                  {connector.name === 'MetaMask' && '🦊'}
                  {connector.name === 'Coinbase Wallet' && '🔵'}
                  {connector.name === 'WalletConnect' && '🔗'}
                  {connector.name === 'Rainbow' && '🌈'}
                  {!['MetaMask', 'Coinbase Wallet', 'WalletConnect', 'Rainbow'].includes(connector.name) && '💼'}
                </div>
                <span>{connector.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
