/**
 * Unified Wallet Connect Button
 * 
 * Single button that opens a modal to connect either Solana or EVM wallets.
 * Shows connected status for both wallet types.
 * Enhanced for Phantom in-app browser compatibility.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useWalletModal } from '@solana/wallet-adapter-react-ui';
import { useAccount, useConnect, useDisconnect, useChainId, useSwitchChain } from 'wagmi';
import { Button } from '@/components/ui/button';
import { 
  Wallet, ChevronDown, LogOut, ExternalLink, Check, Loader2, 
  Copy, X, Zap, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';

// Chain configurations
const EVM_CHAINS = [
  { id: 1, name: 'Ethereum', icon: '⟠', color: '#627EEA' },
  { id: 8453, name: 'Base', icon: '🔵', color: '#0052FF' },
  { id: 42161, name: 'Arbitrum', icon: '🔷', color: '#28A0F0' },
];

// Detect if running inside Phantom's in-app browser (mobile only)
const isPhantomBrowser = () => {
  if (typeof window === 'undefined') return false;
  const userAgent = navigator.userAgent || '';
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
  // Only detect as Phantom browser if mobile AND has Phantom in user agent
  return isMobile && userAgent.includes('Phantom');
};

// Check if Phantom extension is available (desktop or mobile)
const isPhantomAvailable = () => {
  if (typeof window === 'undefined') return false;
  return window.phantom?.solana || window.solana?.isPhantom;
};

export default function UnifiedWalletButton() {
  const [showModal, setShowModal] = useState(false);
  const [copied, setCopied] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const modalRef = useRef(null);

  // Solana wallet
  const { 
    publicKey: solanaPublicKey, 
    connected: solanaConnected, 
    disconnect: solanaDisconnect, 
    wallet: solanaWallet,
    select: selectWallet,
    wallets,
    connect: walletConnect
  } = useWallet();
  const { setVisible: setSolanaModalVisible } = useWalletModal();

  // EVM wallet
  const { address: evmAddress, isConnected: evmConnected } = useAccount();
  const { connectors, connect: evmConnect, isPending: evmConnecting } = useConnect();
  const { disconnect: evmDisconnect } = useDisconnect();
  const evmChainId = useChainId();
  const { switchChain } = useSwitchChain();

  const currentChain = EVM_CHAINS.find(c => c.id === evmChainId) || EVM_CHAINS[0];

  // Close modal on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        setShowModal(false);
      }
    };
    if (showModal) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showModal]);

  const formatAddress = (addr, length = 4) => {
    if (!addr) return '';
    return `${addr.slice(0, length + 2)}...${addr.slice(-length)}`;
  };

  const copyAddress = (address, type) => {
    navigator.clipboard.writeText(address);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };

  // Connect using wallet adapter (proper way)
  const connectPhantomViaAdapter = useCallback(async () => {
    setConnecting(true);
    
    try {
      // Find Phantom wallet in the available wallets
      const phantomWallet = wallets.find(w => 
        w.adapter.name.toLowerCase().includes('phantom')
      );
      
      if (phantomWallet) {
        // Select the Phantom wallet adapter
        selectWallet(phantomWallet.adapter.name);
        
        // Give time for selection to register
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Connect using the wallet adapter
        try {
          await walletConnect();
          toast.success('Connected to Phantom!');
          setShowModal(false);
        } catch (connectError) {
          // If connect fails, it might need user interaction via modal
          console.log('Connect attempt, opening modal...', connectError);
          setSolanaModalVisible(true);
          setShowModal(false);
        }
      } else {
        // Phantom not found in adapters, open modal
        setSolanaModalVisible(true);
        setShowModal(false);
      }
    } catch (error) {
      console.error('Phantom connection error:', error);
      
      if (error.code === 4001 || error.message?.includes('rejected')) {
        toast.error('Connection rejected by user');
      } else {
        // Fallback to modal
        setSolanaModalVisible(true);
        setShowModal(false);
      }
    } finally {
      setConnecting(false);
    }
  }, [wallets, selectWallet, walletConnect, setSolanaModalVisible]);

  // Handle Solana wallet connection
  const handleSolanaConnect = useCallback(async () => {
    // Always use wallet adapter for proper state management
    if (isPhantomAvailable()) {
      await connectPhantomViaAdapter();
    } else {
      // Use standard wallet modal
      setSolanaModalVisible(true);
      setShowModal(false);
    }
  }, [connectPhantomViaAdapter, setSolanaModalVisible]);

  const hasAnyWallet = solanaConnected || evmConnected;
  const connectedCount = (solanaConnected ? 1 : 0) + (evmConnected ? 1 : 0);

  // Check if we're in Phantom browser for UI hints
  const inPhantomBrowser = isPhantomBrowser();

  return (
    <div className="relative">
      {/* Main Button */}
      <Button
        onClick={() => setShowModal(!showModal)}
        data-testid="unified-wallet-btn"
        className={`font-bold rounded-full px-4 py-2 text-xs transition-all ${
          hasAnyWallet
            ? 'bg-gradient-to-r from-[#00C2FF] to-[#00FFA3] text-black hover:opacity-90'
            : 'bg-[#00FFA3] hover:bg-[#00FFA3]/80 text-black'
        }`}
      >
        <Wallet className="w-4 h-4 mr-2" />
        {hasAnyWallet ? (
          <>
            {connectedCount} Connected
            <ChevronDown className={`w-3 h-3 ml-1 transition-transform ${showModal ? 'rotate-180' : ''}`} />
          </>
        ) : (
          'Connect Wallet'
        )}
      </Button>

      {/* Modal */}
      {showModal && (
        <div 
          ref={modalRef}
          className="absolute right-0 mt-2 w-80 bg-[#0a0a12] border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden"
        >
          {/* Header */}
          <div className="p-4 border-b border-white/5 flex items-center justify-between">
            <h3 className="font-bold text-white text-sm">Wallet Connection</h3>
            <button 
              onClick={() => setShowModal(false)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Phantom browser notice */}
          {inPhantomBrowser && !solanaConnected && (
            <div className="mx-4 mt-3 p-2 bg-[#9945FF]/10 border border-[#9945FF]/30 rounded-lg">
              <p className="text-[10px] text-[#9945FF] flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Phantom browser detected - tap below to connect
              </p>
            </div>
          )}

          <div className="p-4 space-y-4">
            {/* Solana Section */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-slate-400 uppercase font-bold">
                <span className="text-[#9945FF]">◎</span> Solana
                {solanaConnected && <Check className="w-3 h-3 text-[#00FFA3]" />}
              </div>

              {solanaConnected && solanaPublicKey ? (
                <div className="bg-[#9945FF]/10 border border-[#9945FF]/30 rounded-xl p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {solanaWallet?.adapter?.icon && (
                        <img src={solanaWallet.adapter.icon} alt="" className="w-5 h-5 rounded" />
                      )}
                      <span className="text-sm font-mono text-white">
                        {formatAddress(solanaPublicKey.toBase58())}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyAddress(solanaPublicKey.toBase58(), 'solana')}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white"
                      >
                        {copied === 'solana' ? <Check className="w-3 h-3 text-[#00FFA3]" /> : <Copy className="w-3 h-3" />}
                      </button>
                      <button
                        onClick={() => { solanaDisconnect(); }}
                        className="p-1.5 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400"
                      >
                        <LogOut className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <button
                  onClick={handleSolanaConnect}
                  disabled={connecting}
                  className="w-full flex items-center justify-between p-3 bg-black/30 border border-white/10 rounded-xl hover:border-[#9945FF]/50 hover:bg-[#9945FF]/5 transition-all text-left disabled:opacity-50"
                  data-testid="connect-solana-btn"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#9945FF]/20 flex items-center justify-center">
                      {connecting ? (
                        <Loader2 className="w-4 h-4 text-[#9945FF] animate-spin" />
                      ) : (
                        <Zap className="w-4 h-4 text-[#9945FF]" />
                      )}
                    </div>
                    <div>
                      <span className="text-sm text-white block">
                        {inPhantomBrowser ? 'Connect Phantom' : 'Connect Solana'}
                      </span>
                      {inPhantomBrowser && (
                        <span className="text-[10px] text-slate-500">Tap to authorize</span>
                      )}
                    </div>
                  </div>
                  <ChevronDown className="w-4 h-4 text-slate-400 -rotate-90" />
                </button>
              )}
            </div>

            {/* EVM Section */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-slate-400 uppercase font-bold">
                <span className="text-[#627EEA]">⟠</span> EVM Chains
                {evmConnected && <Check className="w-3 h-3 text-[#00FFA3]" />}
              </div>

              {evmConnected && evmAddress ? (
                <div className="bg-[#627EEA]/10 border border-[#627EEA]/30 rounded-xl p-3 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span style={{ color: currentChain.color }}>{currentChain.icon}</span>
                      <span className="text-sm font-mono text-white">
                        {formatAddress(evmAddress)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyAddress(evmAddress, 'evm')}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white"
                      >
                        {copied === 'evm' ? <Check className="w-3 h-3 text-[#00FFA3]" /> : <Copy className="w-3 h-3" />}
                      </button>
                      <button
                        onClick={() => evmDisconnect()}
                        className="p-1.5 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400"
                      >
                        <LogOut className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {/* Chain Switcher */}
                  <div className="flex gap-1">
                    {EVM_CHAINS.map(chain => (
                      <button
                        key={chain.id}
                        onClick={() => switchChain?.({ chainId: chain.id })}
                        className={`flex-1 py-1.5 px-2 rounded-lg text-[10px] font-medium transition-all ${
                          chain.id === evmChainId
                            ? 'bg-white/10 text-white'
                            : 'text-slate-500 hover:text-white hover:bg-white/5'
                        }`}
                      >
                        {chain.icon} {chain.name}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {connectors.slice(0, 3).map((connector) => (
                    <button
                      key={connector.uid}
                      onClick={() => evmConnect({ connector })}
                      disabled={evmConnecting}
                      className="w-full flex items-center justify-between p-3 bg-black/30 border border-white/10 rounded-xl hover:border-[#627EEA]/50 hover:bg-[#627EEA]/5 transition-all text-left disabled:opacity-50"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-sm">
                          {connector.name === 'MetaMask' && '🦊'}
                          {connector.name === 'Coinbase Wallet' && '🔵'}
                          {connector.name === 'Injected' && '💼'}
                          {!['MetaMask', 'Coinbase Wallet', 'Injected'].includes(connector.name) && '🔗'}
                        </div>
                        <span className="text-sm text-white">{connector.name}</span>
                      </div>
                      {evmConnecting ? (
                        <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-400 -rotate-90" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="p-3 bg-black/30 border-t border-white/5">
            <p className="text-[10px] text-slate-600 text-center">
              Connect both wallets for unified portfolio tracking
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
