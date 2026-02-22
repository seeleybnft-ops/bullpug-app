/**
 * EVM Wallet Provider - Multi-chain EVM wallet support using Wagmi
 * 
 * This component provides EVM wallet connectivity (Ethereum, Base, Arbitrum)
 * alongside the existing Solana wallet integration.
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { WagmiProvider, createConfig, http, useAccount, useConnect, useDisconnect, useChainId, useSwitchChain } from 'wagmi';
import { mainnet, base, arbitrum } from 'wagmi/chains';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { injected, metaMask, coinbaseWallet, walletConnect } from 'wagmi/connectors';

// Create query client for React Query
const queryClient = new QueryClient();

// Configure wagmi with supported chains
const config = createConfig({
  chains: [mainnet, base, arbitrum],
  connectors: [
    injected(),
    metaMask(),
    coinbaseWallet({ appName: 'Bullpug' }),
  ],
  transports: {
    [mainnet.id]: http(),
    [base.id]: http(),
    [arbitrum.id]: http(),
  },
});

// EVM Wallet Context
const EVMWalletContext = createContext({
  address: null,
  isConnected: false,
  chainId: null,
  chainName: '',
  connect: () => {},
  disconnect: () => {},
  switchChain: () => {},
  supportedChains: [],
});

// Hook to use EVM wallet
export function useEVMWallet() {
  return useContext(EVMWalletContext);
}

// Inner component that uses wagmi hooks
function EVMWalletContextProvider({ children }) {
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { connectors, connect } = useConnect();
  const { disconnect } = useDisconnect();
  const { switchChain } = useSwitchChain();

  const getChainName = (id) => {
    switch (id) {
      case 1: return 'Ethereum';
      case 8453: return 'Base';
      case 42161: return 'Arbitrum';
      default: return 'Unknown';
    }
  };

  const supportedChains = [
    { id: 1, name: 'Ethereum', symbol: 'ETH' },
    { id: 8453, name: 'Base', symbol: 'ETH' },
    { id: 42161, name: 'Arbitrum', symbol: 'ETH' },
  ];

  const value = {
    address: address || null,
    isConnected,
    chainId,
    chainName: getChainName(chainId),
    connect: (connector) => connect({ connector }),
    disconnect,
    switchChain: (chainId) => switchChain({ chainId }),
    supportedChains,
    connectors,
  };

  return (
    <EVMWalletContext.Provider value={value}>
      {children}
    </EVMWalletContext.Provider>
  );
}

// Main provider component
export function EVMWalletProvider({ children }) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <EVMWalletContextProvider>
          {children}
        </EVMWalletContextProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}

export default EVMWalletProvider;
