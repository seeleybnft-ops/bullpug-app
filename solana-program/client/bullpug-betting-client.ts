/**
 * Bullpug P2P Betting - TypeScript Client SDK
 * 
 * This client interacts with the on-chain Bullpug betting smart contract
 * for trustless P2P coin flip and pot games.
 */

import {
  Connection,
  PublicKey,
  Transaction,
  SystemProgram,
  SYSVAR_SLOT_HASHES_PUBKEY,
  Keypair,
} from '@solana/web3.js';
import { sha256 } from 'js-sha256';

// Program ID - replace with actual deployed program ID
export const PROGRAM_ID = new PublicKey('BuLLPugBetxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');

// Seeds
const COINFLIP_SEED = Buffer.from('coinflip');
const POT_SEED = Buffer.from('pot');
const TREASURY_SEED = Buffer.from('treasury');

// Constants (matching on-chain)
export const RAKE_BPS = 250; // 2.5%
export const MIN_BET_LAMPORTS = 10_000_000; // 0.01 SOL
export const MAX_BET_LAMPORTS = 10_000_000_000; // 10 SOL

/**
 * Coinflip status enum
 */
export enum CoinflipStatus {
  Open = 0,
  Completed = 1,
  Cancelled = 2,
}

/**
 * Pot status enum
 */
export enum PotStatus {
  Open = 0,
  Countdown = 1,
  Drawing = 2,
  Completed = 3,
}

/**
 * Coinflip account data structure
 */
export interface CoinflipAccount {
  creator: PublicKey;
  opponent: PublicKey | null;
  betAmount: bigint;
  creatorChoice: number;
  outcome: number | null;
  winner: PublicKey | null;
  serverSeedHash: Uint8Array;
  serverSeed: Uint8Array | null;
  clientSeed: Uint8Array | null;
  status: CoinflipStatus;
  createdAt: bigint;
  completedAt: bigint | null;
  payoutAmount: bigint;
  rakeAmount: bigint;
}

/**
 * Pot account data structure
 */
export interface PotAccount {
  potId: bigint;
  totalAmount: bigint;
  entryCount: bigint;
  status: PotStatus;
  countdownStartSlot: bigint;
  drawSlot: bigint;
  randomValue: bigint;
  winner: PublicKey | null;
  payoutAmount: bigint;
  rakeAmount: bigint;
}

/**
 * Bullpug Betting Client
 */
export class BullpugBettingClient {
  connection: Connection;
  
  constructor(connection: Connection) {
    this.connection = connection;
  }

  /**
   * Derive PDA for coinflip account
   */
  static deriveCoinflipPDA(creator: PublicKey, timestamp: bigint): [PublicKey, number] {
    return PublicKey.findProgramAddressSync(
      [COINFLIP_SEED, creator.toBuffer(), Buffer.from(timestamp.toString())],
      PROGRAM_ID
    );
  }

  /**
   * Derive PDA for coinflip escrow
   */
  static deriveCoinflipEscrowPDA(coinflip: PublicKey): [PublicKey, number] {
    return PublicKey.findProgramAddressSync(
      [COINFLIP_SEED, coinflip.toBuffer(), Buffer.from('escrow')],
      PROGRAM_ID
    );
  }

  /**
   * Derive PDA for pot account
   */
  static derivePotPDA(potId: bigint): [PublicKey, number] {
    const potIdBuffer = Buffer.alloc(8);
    potIdBuffer.writeBigUInt64LE(potId);
    return PublicKey.findProgramAddressSync(
      [POT_SEED, potIdBuffer],
      PROGRAM_ID
    );
  }

  /**
   * Derive PDA for pot escrow
   */
  static derivePotEscrowPDA(potId: bigint): [PublicKey, number] {
    const potIdBuffer = Buffer.alloc(8);
    potIdBuffer.writeBigUInt64LE(potId);
    return PublicKey.findProgramAddressSync(
      [POT_SEED, potIdBuffer, Buffer.from('escrow')],
      PROGRAM_ID
    );
  }

  /**
   * Derive PDA for treasury
   */
  static deriveTreasuryPDA(): [PublicKey, number] {
    return PublicKey.findProgramAddressSync(
      [TREASURY_SEED],
      PROGRAM_ID
    );
  }

  /**
   * Generate a random server seed and its hash
   */
  static generateServerSeed(): { seed: Uint8Array; hash: Uint8Array } {
    const seed = Keypair.generate().secretKey.slice(0, 32);
    const hash = new Uint8Array(sha256.array(seed));
    return { seed, hash };
  }

  /**
   * Generate a random client seed
   */
  static generateClientSeed(): Uint8Array {
    return Keypair.generate().secretKey.slice(0, 32);
  }

  /**
   * Calculate coinflip outcome from seeds
   */
  static calculateOutcome(serverSeed: Uint8Array, clientSeed: Uint8Array): number {
    const combined = new Uint8Array([...serverSeed, ...clientSeed]);
    const hash = sha256.array(combined);
    return hash[31] % 2; // 0 = heads, 1 = tails
  }

  /**
   * Calculate payout after rake
   */
  static calculatePayout(totalPot: bigint): { payout: bigint; rake: bigint } {
    const rake = (totalPot * BigInt(RAKE_BPS)) / BigInt(10000);
    const payout = totalPot - rake;
    return { payout, rake };
  }

  /**
   * Convert SOL to lamports
   */
  static solToLamports(sol: number): bigint {
    return BigInt(Math.floor(sol * 1_000_000_000));
  }

  /**
   * Convert lamports to SOL
   */
  static lamportsToSol(lamports: bigint): number {
    return Number(lamports) / 1_000_000_000;
  }

  /**
   * Verify server seed matches committed hash
   */
  static verifyServerSeed(serverSeed: Uint8Array, hash: Uint8Array): boolean {
    const computedHash = new Uint8Array(sha256.array(serverSeed));
    return computedHash.every((byte, i) => byte === hash[i]);
  }
}

/**
 * Instructions builder for Bullpug Betting
 * 
 * Note: These are instruction builders. The actual transaction signing
 * and sending should be done using a wallet adapter in the frontend.
 */
export const BullpugBettingInstructions = {
  /**
   * Build instruction data for createCoinflip
   */
  createCoinflip(betAmount: bigint, choice: number, serverSeedHash: Uint8Array): Buffer {
    // Instruction discriminator (8 bytes) + bet_amount (8 bytes) + choice (1 byte) + hash (32 bytes)
    const buffer = Buffer.alloc(49);
    // Discriminator would be generated by Anchor - placeholder
    buffer.writeBigUInt64LE(betAmount, 8);
    buffer.writeUInt8(choice, 16);
    Buffer.from(serverSeedHash).copy(buffer, 17);
    return buffer;
  },

  /**
   * Build instruction data for acceptCoinflip
   */
  acceptCoinflip(clientSeed: Uint8Array, serverSeed: Uint8Array): Buffer {
    const buffer = Buffer.alloc(72);
    // Discriminator placeholder
    Buffer.from(clientSeed).copy(buffer, 8);
    Buffer.from(serverSeed).copy(buffer, 40);
    return buffer;
  },
};

export default BullpugBettingClient;
