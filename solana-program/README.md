# Bullpug P2P Betting - Solana Smart Contract

## Overview

This Anchor-based Solana smart contract enables **trustless peer-to-peer betting** for the Bullpug platform. It supports two game types:

1. **Coinflip** - 1v1 head-to-head betting with provably fair outcomes
2. **Pot** - Winner-takes-all multi-player betting

### Key Features

- **Fully Trustless**: All funds are held in Program Derived Addresses (PDAs), not controlled by any central authority
- **Provably Fair**: Randomness is derived from cryptographic seeds that can be verified
- **Automatic Payouts**: Winners receive their SOL automatically when the game concludes
- **Transparent Rake**: 2.5% house rake is clearly defined and sent to a treasury PDA
- **On-Chain Verification**: All game outcomes and transactions are verifiable on Solana Explorer

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      BULLPUG BETTING PROGRAM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│   │   COINFLIP   │     │     POT      │     │   TREASURY   │   │
│   │   ACCOUNTS   │     │   ACCOUNTS   │     │     PDA      │   │
│   └──────┬───────┘     └──────┬───────┘     └──────────────┘   │
│          │                    │                                  │
│   ┌──────▼───────┐     ┌──────▼───────┐                        │
│   │   COINFLIP   │     │     POT      │                        │
│   │    ESCROW    │     │    ESCROW    │                        │
│   │     PDA      │     │     PDA      │                        │
│   └──────────────┘     └──────────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Game Flows

### Coinflip Flow

```
1. CREATOR creates challenge:
   - Commits bet amount + choice (heads/tails)
   - Provides server_seed_hash (SHA-256 of secret seed)
   - SOL transferred to Coinflip Escrow PDA

2. OPPONENT accepts challenge:
   - Provides client_seed
   - Creator reveals server_seed (verified against hash)
   - SOL transferred to Coinflip Escrow PDA

3. Outcome determined:
   - outcome = SHA-256(server_seed || client_seed)[31] % 2
   - Winner receives (2 * bet - 2.5% rake)
   - Rake transferred to Treasury PDA

4. Verification:
   - Anyone can verify outcome using revealed seeds
```

### Pot Flow

```
1. INITIALIZE pot (new round)

2. PLAYERS join pot:
   - Each deposit SOL to Pot Escrow PDA
   - Probability = deposit / total_pot

3. COUNTDOWN starts when 2+ players join:
   - 60 second timer begins
   - More players can join during countdown

4. DRAW winner:
   - Called after countdown ends
   - Uses slot hash for randomness
   - random_value = hash(pot_id, slot, slot_hashes) % total_pot

5. CLAIM winnings:
   - Winner verifies their entry contains random_value
   - Winner receives (total_pot - 2.5% rake)
```

---

## Account Structures

### Coinflip Account (216 bytes)
```rust
pub struct Coinflip {
    pub creator: Pubkey,           // 32 bytes
    pub opponent: Option<Pubkey>,  // 33 bytes
    pub bet_amount: u64,           // 8 bytes
    pub creator_choice: u8,        // 1 byte (0=heads, 1=tails)
    pub outcome: Option<u8>,       // 2 bytes
    pub winner: Option<Pubkey>,    // 33 bytes
    pub server_seed_hash: [u8; 32],// 32 bytes
    pub server_seed: Option<[u8; 32]>, // 33 bytes
    pub client_seed: Option<[u8; 32]>, // 33 bytes
    pub status: CoinflipStatus,    // 1 byte
    pub created_at: i64,           // 8 bytes
    pub completed_at: Option<i64>, // 9 bytes
    pub payout_amount: u64,        // 8 bytes
    pub rake_amount: u64,          // 8 bytes
    pub bump: u8,                  // 1 byte
    pub escrow_bump: u8,           // 1 byte
}
```

### Pot Account (120 bytes)
```rust
pub struct Pot {
    pub pot_id: u64,               // 8 bytes
    pub total_amount: u64,         // 8 bytes
    pub entry_count: u64,          // 8 bytes
    pub status: PotStatus,         // 1 byte
    pub countdown_start_slot: u64, // 8 bytes
    pub draw_slot: u64,            // 8 bytes
    pub random_value: u64,         // 8 bytes
    pub winner: Option<Pubkey>,    // 33 bytes
    pub payout_amount: u64,        // 8 bytes
    pub rake_amount: u64,          // 8 bytes
    pub bump: u8,                  // 1 byte
    pub escrow_bump: u8,           // 1 byte
    pub created_at: i64,           // 8 bytes
}
```

---

## Instructions

| Instruction | Description | Accounts |
|------------|-------------|----------|
| `create_coinflip` | Create new challenge | creator, coinflip, escrow, system |
| `accept_coinflip` | Accept and resolve | opponent, creator, coinflip, escrow, treasury, system |
| `cancel_coinflip` | Cancel open challenge | creator, coinflip, escrow, system |
| `initialize_pot` | Start new pot round | initializer, pot, escrow, system |
| `join_pot` | Join pot with bet | player, pot, pot_entry, escrow, system |
| `draw_pot_winner` | Draw after countdown | pot, slot_hashes |
| `claim_pot_winnings` | Claim as winner | claimer, pot, winner_entry, escrow, treasury, system |
| `withdraw_treasury` | Admin withdraw | admin, treasury, system |

---

## Deployment

### Prerequisites
- Rust 1.70+
- Solana CLI 1.18+
- Anchor 0.30.1+

### Build
```bash
cd /app/solana-program
anchor build
```

### Deploy to Devnet
```bash
anchor deploy --provider.cluster devnet
```

### Deploy to Mainnet
```bash
anchor deploy --provider.cluster mainnet
```

---

## Security Considerations

1. **Randomness**: Coinflip uses commit-reveal scheme; Pot uses slot hashes
2. **Re-entrancy**: Anchor provides protection via account checks
3. **Overflow**: Rust's checked arithmetic prevents overflows
4. **Frontrunning**: Server seed is hashed before reveal to prevent MEV
5. **Refunds**: Cancelled coinflips return full bet to creator

---

## Integration with Frontend

The frontend should use `@solana/wallet-adapter-react` to:

1. Connect user wallets (Phantom, Solflare, etc.)
2. Sign transactions created by the client SDK
3. Listen for program events via WebSocket subscriptions

See `/app/solana-program/client/bullpug-betting-client.ts` for the TypeScript SDK.

---

## License

MIT License - Bullpug 2025
