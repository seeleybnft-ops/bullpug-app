/**
 * Solana Program Configuration
 * 
 * This file contains configuration for the Bullpug P2P Betting smart contract.
 * Update these values after deploying the contract to devnet/mainnet.
 */

// Program ID from /app/solana-program/target/deploy/bullpug_betting-keypair.json
export const PROGRAM_ID = 'H8GBfrx5drPZkAQXw1ueGtBrKD5QBwbh2DE4EcP2DCFm';

// Network configuration
export const SOLANA_CONFIG = {
  NETWORK: process.env.REACT_APP_SOLANA_NETWORK || 'devnet',
  
  RPC_URLS: {
    'devnet': process.env.REACT_APP_SOLANA_DEVNET_RPC || 'https://api.devnet.solana.com',
    'mainnet-beta': process.env.REACT_APP_SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com',
  },
  
  WS_URLS: {
    'devnet': process.env.REACT_APP_SOLANA_DEVNET_WS || 'wss://api.devnet.solana.com',
    'mainnet-beta': process.env.REACT_APP_SOLANA_MAINNET_WS || 'wss://api.mainnet-beta.solana.com',
  },
  
  COMMITMENT: 'confirmed',
};

// Game configuration
export const BETTING_CONFIG = {
  // Rake percentage (2.5%)
  RAKE_PERCENTAGE: 0.025,
  
  // Minimum bet amounts (in SOL)
  MIN_BET: {
    COINFLIP: 0.01,
    POT: 0.01,
  },
  
  // Maximum bet amounts (in SOL)
  MAX_BET: {
    COINFLIP: 10,
    POT: 5,
  },
  
  // Pot countdown duration (in seconds)
  POT_COUNTDOWN_SECONDS: 60,
};

export const TREASURY_WALLET = process.env.REACT_APP_TREASURY_WALLET || 'we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT';

// Helper to get current RPC URL
export const getRpcUrl = () => {
  return SOLANA_CONFIG.RPC_URLS[SOLANA_CONFIG.NETWORK];
};

// Helper to get current WebSocket URL
export const getWsUrl = () => {
  return SOLANA_CONFIG.WS_URLS[SOLANA_CONFIG.NETWORK];
};

// Check if using devnet
export const isDevnet = () => {
  return SOLANA_CONFIG.NETWORK === 'devnet';
};

// Check if using mainnet
export const isMainnet = () => {
  return SOLANA_CONFIG.NETWORK === 'mainnet-beta';
};

export default {
  PROGRAM_ID,
  SOLANA_CONFIG,
  BETTING_CONFIG,
  TREASURY_WALLET,
  getRpcUrl,
  getWsUrl,
  isDevnet,
  isMainnet,
};
