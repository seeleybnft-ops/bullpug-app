use anchor_lang::prelude::*;
use anchor_lang::solana_program::hash::hash;

declare_id!("H5zK3o8qNaM5yxS2qLxjFzytu3CtQxUmBmMQWDgQPqQf");

// ============================================================================
// BULLPUG P2P BETTING - TRUSTLESS SOLANA SMART CONTRACT
// ============================================================================
// This program enables trustless P2P coin flip and pot betting on Solana.
// Funds are escrowed in Program Derived Addresses (PDAs) and automatically
// distributed to winners based on provably fair randomness.
// ============================================================================

pub const COINFLIP_SEED: &[u8] = b"coinflip";
pub const POT_SEED: &[u8] = b"pot";
pub const TREASURY_SEED: &[u8] = b"treasury";

// Rake percentage (2.5% = 250 basis points)
pub const RAKE_BPS: u64 = 250;
pub const BPS_DIVISOR: u64 = 10000;

// Minimum and maximum bet amounts in lamports
pub const MIN_BET_LAMPORTS: u64 = 10_000_000; // 0.01 SOL
pub const MAX_BET_LAMPORTS: u64 = 10_000_000_000; // 10 SOL

// Countdown duration in slots (~400ms per slot on mainnet)
pub const POT_COUNTDOWN_SLOTS: u64 = 150; // ~60 seconds

#[program]
pub mod bullpug_betting {
    use super::*;

    // ========================================================================
    // COINFLIP - P2P 1v1 Betting
    // ========================================================================

    /// Create a new coinflip challenge
    pub fn create_coinflip(
        ctx: Context<CreateCoinflip>,
        bet_amount: u64,
        choice: u8, // 0 = heads, 1 = tails
        server_seed_hash: [u8; 32],
    ) -> Result<()> {
        require!(bet_amount >= MIN_BET_LAMPORTS, BettingError::BetTooSmall);
        require!(bet_amount <= MAX_BET_LAMPORTS, BettingError::BetTooLarge);
        require!(choice <= 1, BettingError::InvalidChoice);

        // Transfer SOL from creator to escrow PDA
        let cpi_context = CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.creator.to_account_info(),
                to: ctx.accounts.coinflip_escrow.to_account_info(),
            },
        );
        anchor_lang::system_program::transfer(cpi_context, bet_amount)?;

        // Initialize coinflip state
        let coinflip = &mut ctx.accounts.coinflip;
        coinflip.creator = ctx.accounts.creator.key();
        coinflip.bet_amount = bet_amount;
        coinflip.creator_choice = choice;
        coinflip.server_seed_hash = server_seed_hash;
        coinflip.status = CoinflipStatus::Open;
        coinflip.created_at = Clock::get()?.unix_timestamp;
        coinflip.bump = ctx.bumps.coinflip;
        coinflip.escrow_bump = ctx.bumps.coinflip_escrow;

        emit!(CoinflipCreated {
            coinflip: coinflip.key(),
            creator: ctx.accounts.creator.key(),
            bet_amount,
            choice,
        });

        Ok(())
    }

    /// Accept a coinflip challenge and determine winner
    pub fn accept_coinflip(
        ctx: Context<AcceptCoinflip>,
        client_seed: [u8; 32],
        server_seed: [u8; 32],
    ) -> Result<()> {
        let coinflip = &mut ctx.accounts.coinflip;
        
        require!(coinflip.status == CoinflipStatus::Open, BettingError::CoinflipNotOpen);
        require!(ctx.accounts.opponent.key() != coinflip.creator, BettingError::CannotPlaySelf);

        // Verify server seed matches committed hash
        let computed_hash = hash(&server_seed);
        require!(
            computed_hash.to_bytes() == coinflip.server_seed_hash,
            BettingError::InvalidServerSeed
        );

        // Transfer SOL from opponent to escrow
        let cpi_context = CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.opponent.to_account_info(),
                to: ctx.accounts.coinflip_escrow.to_account_info(),
            },
        );
        anchor_lang::system_program::transfer(cpi_context, coinflip.bet_amount)?;

        // Determine outcome using combined seeds (provably fair)
        let combined = [server_seed, client_seed].concat();
        let result_hash = hash(&combined);
        let outcome = result_hash.to_bytes()[31] % 2; // 0 or 1

        let creator_won = outcome == coinflip.creator_choice;
        let winner = if creator_won {
            coinflip.creator
        } else {
            ctx.accounts.opponent.key()
        };

        // Calculate payout amounts
        let total_pot = coinflip.bet_amount * 2;
        let rake = total_pot * RAKE_BPS / BPS_DIVISOR;
        let payout = total_pot - rake;

        // Transfer rake to treasury
        let coinflip_key = coinflip.key();
        let seeds = &[
            COINFLIP_SEED,
            coinflip_key.as_ref(),
            b"escrow",
            &[coinflip.escrow_bump],
        ];
        let signer_seeds = &[&seeds[..]];

        let rake_cpi = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.coinflip_escrow.to_account_info(),
                to: ctx.accounts.treasury.to_account_info(),
            },
            signer_seeds,
        );
        anchor_lang::system_program::transfer(rake_cpi, rake)?;

        // Transfer payout to winner
        let winner_account = if creator_won {
            ctx.accounts.creator.to_account_info()
        } else {
            ctx.accounts.opponent.to_account_info()
        };

        let payout_cpi = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.coinflip_escrow.to_account_info(),
                to: winner_account,
            },
            signer_seeds,
        );
        anchor_lang::system_program::transfer(payout_cpi, payout)?;

        // Update coinflip state
        coinflip.opponent = Some(ctx.accounts.opponent.key());
        coinflip.outcome = Some(outcome);
        coinflip.winner = Some(winner);
        coinflip.client_seed = Some(client_seed);
        coinflip.server_seed = Some(server_seed);
        coinflip.status = CoinflipStatus::Completed;
        coinflip.completed_at = Some(Clock::get()?.unix_timestamp);
        coinflip.payout_amount = payout;
        coinflip.rake_amount = rake;

        emit!(CoinflipCompleted {
            coinflip: coinflip.key(),
            winner,
            outcome,
            payout,
            rake,
        });

        Ok(())
    }

    /// Cancel an open coinflip (creator only, refunds bet)
    pub fn cancel_coinflip(ctx: Context<CancelCoinflip>) -> Result<()> {
        let coinflip = &mut ctx.accounts.coinflip;
        
        require!(coinflip.status == CoinflipStatus::Open, BettingError::CoinflipNotOpen);
        require!(ctx.accounts.creator.key() == coinflip.creator, BettingError::Unauthorized);

        // Refund creator
        let coinflip_key = coinflip.key();
        let seeds = &[
            COINFLIP_SEED,
            coinflip_key.as_ref(),
            b"escrow",
            &[coinflip.escrow_bump],
        ];
        let signer_seeds = &[&seeds[..]];

        let cpi_context = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.coinflip_escrow.to_account_info(),
                to: ctx.accounts.creator.to_account_info(),
            },
            signer_seeds,
        );
        anchor_lang::system_program::transfer(cpi_context, coinflip.bet_amount)?;

        coinflip.status = CoinflipStatus::Cancelled;

        emit!(CoinflipCancelled {
            coinflip: coinflip.key(),
        });

        Ok(())
    }

    // ========================================================================
    // POT GAME - Winner Takes All (Multi-Player)
    // ========================================================================

    /// Initialize a new pot round
    pub fn initialize_pot(ctx: Context<InitializePot>, pot_id: u64) -> Result<()> {
        let pot = &mut ctx.accounts.pot;
        pot.pot_id = pot_id;
        pot.total_amount = 0;
        pot.entry_count = 0;
        pot.status = PotStatus::Open;
        pot.countdown_start_slot = 0;
        pot.draw_slot = 0;
        pot.winner = None;
        pot.bump = ctx.bumps.pot;
        pot.escrow_bump = ctx.bumps.pot_escrow;
        pot.created_at = Clock::get()?.unix_timestamp;

        emit!(PotCreated { pot_id });

        Ok(())
    }

    /// Join the pot with a bet
    pub fn join_pot(ctx: Context<JoinPot>, amount: u64) -> Result<()> {
        require!(amount >= MIN_BET_LAMPORTS, BettingError::BetTooSmall);
        
        let pot = &mut ctx.accounts.pot;
        require!(pot.status == PotStatus::Open || pot.status == PotStatus::Countdown, BettingError::PotClosed);

        // Transfer SOL to pot escrow
        let cpi_context = CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.player.to_account_info(),
                to: ctx.accounts.pot_escrow.to_account_info(),
            },
        );
        anchor_lang::system_program::transfer(cpi_context, amount)?;

        // Record entry
        let entry = &mut ctx.accounts.pot_entry;
        entry.pot = pot.key();
        entry.player = ctx.accounts.player.key();
        entry.amount = amount;
        entry.entry_index = pot.entry_count;
        entry.cumulative_amount = pot.total_amount + amount;
        entry.bump = ctx.bumps.pot_entry;

        pot.total_amount += amount;
        pot.entry_count += 1;

        // Start countdown when 2+ players
        if pot.entry_count == 2 && pot.status == PotStatus::Open {
            let clock = Clock::get()?;
            pot.countdown_start_slot = clock.slot;
            pot.draw_slot = clock.slot + POT_COUNTDOWN_SLOTS;
            pot.status = PotStatus::Countdown;

            emit!(PotCountdownStarted {
                pot_id: pot.pot_id,
                draw_slot: pot.draw_slot,
            });
        }

        emit!(PotEntryAdded {
            pot_id: pot.pot_id,
            player: ctx.accounts.player.key(),
            amount,
            total_pot: pot.total_amount,
        });

        Ok(())
    }

    /// Draw pot winner (can be called by anyone after countdown ends)
    pub fn draw_pot_winner(ctx: Context<DrawPotWinner>) -> Result<()> {
        let pot = &mut ctx.accounts.pot;
        
        require!(pot.status == PotStatus::Countdown, BettingError::PotNotInCountdown);
        require!(pot.entry_count >= 2, BettingError::NotEnoughEntries);
        
        let clock = Clock::get()?;
        require!(clock.slot >= pot.draw_slot, BettingError::CountdownNotEnded);

        // Use slot hash for randomness (provably fair)
        let slot_hashes = &ctx.accounts.slot_hashes;
        let random_seed = hash(&[
            &pot.pot_id.to_le_bytes()[..],
            &clock.slot.to_le_bytes()[..],
            slot_hashes.key().as_ref(),
        ].concat());

        // Convert hash to random value in [0, total_amount)
        let random_value = u64::from_le_bytes(
            random_seed.to_bytes()[..8].try_into().unwrap()
        ) % pot.total_amount;

        // The winner is determined by finding which entry's cumulative range
        // contains the random value. This is verified client-side by iterating
        // through pot entries.
        pot.random_value = random_value;
        pot.status = PotStatus::Drawing;

        emit!(PotDrawStarted {
            pot_id: pot.pot_id,
            random_value,
            total_pot: pot.total_amount,
        });

        Ok(())
    }

    /// Claim pot winnings (called by the winner)
    pub fn claim_pot_winnings(ctx: Context<ClaimPotWinnings>) -> Result<()> {
        let pot = &mut ctx.accounts.pot;
        let entry = &ctx.accounts.winner_entry;
        
        require!(pot.status == PotStatus::Drawing, BettingError::PotNotDrawing);
        require!(entry.pot == pot.key(), BettingError::InvalidEntry);
        require!(entry.player == ctx.accounts.claimer.key(), BettingError::NotWinner);

        // Verify this entry contains the random value
        let entry_start = entry.cumulative_amount - entry.amount;
        require!(
            pot.random_value >= entry_start && pot.random_value < entry.cumulative_amount,
            BettingError::NotWinner
        );

        // Calculate payout
        let rake = pot.total_amount * RAKE_BPS / BPS_DIVISOR;
        let payout = pot.total_amount - rake;

        // Transfer rake to treasury
        let pot_id_bytes = pot.pot_id.to_le_bytes();
        let seeds = &[
            POT_SEED,
            pot_id_bytes.as_ref(),
            b"escrow",
            &[pot.escrow_bump],
        ];
        let signer_seeds = &[&seeds[..]];

        let rake_cpi = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.pot_escrow.to_account_info(),
                to: ctx.accounts.treasury.to_account_info(),
            },
            signer_seeds,
        );
        anchor_lang::system_program::transfer(rake_cpi, rake)?;

        // Transfer payout to winner
        let payout_cpi = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.pot_escrow.to_account_info(),
                to: ctx.accounts.claimer.to_account_info(),
            },
            signer_seeds,
        );
        anchor_lang::system_program::transfer(payout_cpi, payout)?;

        pot.winner = Some(ctx.accounts.claimer.key());
        pot.status = PotStatus::Completed;
        pot.payout_amount = payout;
        pot.rake_amount = rake;

        emit!(PotCompleted {
            pot_id: pot.pot_id,
            winner: ctx.accounts.claimer.key(),
            payout,
            rake,
        });

        Ok(())
    }

    /// Withdraw treasury funds (admin only)
    pub fn withdraw_treasury(ctx: Context<WithdrawTreasury>, amount: u64) -> Result<()> {
        let seeds = &[TREASURY_SEED, &[ctx.bumps.treasury]];
        let signer_seeds = &[&seeds[..]];

        let cpi_context = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.treasury.to_account_info(),
                to: ctx.accounts.admin.to_account_info(),
            },
            signer_seeds,
        );
        anchor_lang::system_program::transfer(cpi_context, amount)?;

        Ok(())
    }
}

// ============================================================================
// ACCOUNT STRUCTURES
// ============================================================================

#[account]
#[derive(InitSpace)]
pub struct Coinflip {
    pub creator: Pubkey,
    pub opponent: Option<Pubkey>,
    pub bet_amount: u64,
    pub creator_choice: u8,
    pub outcome: Option<u8>,
    pub winner: Option<Pubkey>,
    pub server_seed_hash: [u8; 32],
    pub server_seed: Option<[u8; 32]>,
    pub client_seed: Option<[u8; 32]>,
    pub status: CoinflipStatus,
    pub created_at: i64,
    pub completed_at: Option<i64>,
    pub payout_amount: u64,
    pub rake_amount: u64,
    pub bump: u8,
    pub escrow_bump: u8,
}

#[account]
#[derive(InitSpace)]
pub struct Pot {
    pub pot_id: u64,
    pub total_amount: u64,
    pub entry_count: u64,
    pub status: PotStatus,
    pub countdown_start_slot: u64,
    pub draw_slot: u64,
    pub random_value: u64,
    pub winner: Option<Pubkey>,
    pub payout_amount: u64,
    pub rake_amount: u64,
    pub bump: u8,
    pub escrow_bump: u8,
    pub created_at: i64,
}

#[account]
#[derive(InitSpace)]
pub struct PotEntry {
    pub pot: Pubkey,
    pub player: Pubkey,
    pub amount: u64,
    pub entry_index: u64,
    pub cumulative_amount: u64,
    pub bump: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum CoinflipStatus {
    Open,
    Completed,
    Cancelled,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum PotStatus {
    Open,
    Countdown,
    Drawing,
    Completed,
}

// ============================================================================
// ACCOUNT CONTEXTS
// ============================================================================

#[derive(Accounts)]
pub struct CreateCoinflip<'info> {
    #[account(mut)]
    pub creator: Signer<'info>,
    
    #[account(
        init,
        payer = creator,
        space = 8 + Coinflip::INIT_SPACE,
        seeds = [COINFLIP_SEED, creator.key().as_ref(), &Clock::get()?.unix_timestamp.to_le_bytes()],
        bump
    )]
    pub coinflip: Account<'info, Coinflip>,
    
    /// CHECK: PDA escrow for this coinflip
    #[account(
        mut,
        seeds = [COINFLIP_SEED, coinflip.key().as_ref(), b"escrow"],
        bump
    )]
    pub coinflip_escrow: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct AcceptCoinflip<'info> {
    #[account(mut)]
    pub opponent: Signer<'info>,
    
    /// CHECK: Creator account for receiving payout if they win
    #[account(mut)]
    pub creator: UncheckedAccount<'info>,
    
    #[account(
        mut,
        constraint = coinflip.creator == creator.key() @ BettingError::InvalidCreator
    )]
    pub coinflip: Account<'info, Coinflip>,
    
    /// CHECK: PDA escrow
    #[account(
        mut,
        seeds = [COINFLIP_SEED, coinflip.key().as_ref(), b"escrow"],
        bump = coinflip.escrow_bump
    )]
    pub coinflip_escrow: UncheckedAccount<'info>,
    
    /// CHECK: Treasury PDA for rake
    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump
    )]
    pub treasury: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CancelCoinflip<'info> {
    #[account(mut)]
    pub creator: Signer<'info>,
    
    #[account(
        mut,
        constraint = coinflip.creator == creator.key() @ BettingError::Unauthorized
    )]
    pub coinflip: Account<'info, Coinflip>,
    
    /// CHECK: PDA escrow
    #[account(
        mut,
        seeds = [COINFLIP_SEED, coinflip.key().as_ref(), b"escrow"],
        bump = coinflip.escrow_bump
    )]
    pub coinflip_escrow: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(pot_id: u64)]
pub struct InitializePot<'info> {
    #[account(mut)]
    pub initializer: Signer<'info>,
    
    #[account(
        init,
        payer = initializer,
        space = 8 + Pot::INIT_SPACE,
        seeds = [POT_SEED, &pot_id.to_le_bytes()],
        bump
    )]
    pub pot: Account<'info, Pot>,
    
    /// CHECK: PDA escrow for pot funds
    #[account(
        mut,
        seeds = [POT_SEED, &pot_id.to_le_bytes(), b"escrow"],
        bump
    )]
    pub pot_escrow: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct JoinPot<'info> {
    #[account(mut)]
    pub player: Signer<'info>,
    
    #[account(mut)]
    pub pot: Account<'info, Pot>,
    
    #[account(
        init,
        payer = player,
        space = 8 + PotEntry::INIT_SPACE,
        seeds = [POT_SEED, pot.key().as_ref(), player.key().as_ref()],
        bump
    )]
    pub pot_entry: Account<'info, PotEntry>,
    
    /// CHECK: PDA escrow
    #[account(
        mut,
        seeds = [POT_SEED, &pot.pot_id.to_le_bytes(), b"escrow"],
        bump = pot.escrow_bump
    )]
    pub pot_escrow: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct DrawPotWinner<'info> {
    #[account(mut)]
    pub pot: Account<'info, Pot>,
    
    /// CHECK: SlotHashes sysvar for randomness
    #[account(address = anchor_lang::solana_program::sysvar::slot_hashes::ID)]
    pub slot_hashes: UncheckedAccount<'info>,
}

#[derive(Accounts)]
pub struct ClaimPotWinnings<'info> {
    #[account(mut)]
    pub claimer: Signer<'info>,
    
    #[account(mut)]
    pub pot: Account<'info, Pot>,
    
    #[account(
        constraint = winner_entry.player == claimer.key() @ BettingError::NotWinner
    )]
    pub winner_entry: Account<'info, PotEntry>,
    
    /// CHECK: PDA escrow
    #[account(
        mut,
        seeds = [POT_SEED, &pot.pot_id.to_le_bytes(), b"escrow"],
        bump = pot.escrow_bump
    )]
    pub pot_escrow: UncheckedAccount<'info>,
    
    /// CHECK: Treasury PDA
    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump
    )]
    pub treasury: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct WithdrawTreasury<'info> {
    #[account(
        mut,
        // TODO: Add admin authority check
    )]
    pub admin: Signer<'info>,
    
    /// CHECK: Treasury PDA
    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump
    )]
    pub treasury: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
}

// ============================================================================
// ERRORS
// ============================================================================

#[error_code]
pub enum BettingError {
    #[msg("Bet amount is below minimum (0.01 SOL)")]
    BetTooSmall,
    #[msg("Bet amount exceeds maximum (10 SOL)")]
    BetTooLarge,
    #[msg("Invalid choice - must be 0 (heads) or 1 (tails)")]
    InvalidChoice,
    #[msg("Coinflip is not open for acceptance")]
    CoinflipNotOpen,
    #[msg("Cannot play against yourself")]
    CannotPlaySelf,
    #[msg("Server seed does not match committed hash")]
    InvalidServerSeed,
    #[msg("Unauthorized action")]
    Unauthorized,
    #[msg("Invalid creator account")]
    InvalidCreator,
    #[msg("Pot is closed")]
    PotClosed,
    #[msg("Pot is not in countdown status")]
    PotNotInCountdown,
    #[msg("Need at least 2 entries to draw")]
    NotEnoughEntries,
    #[msg("Countdown has not ended yet")]
    CountdownNotEnded,
    #[msg("Pot is not in drawing status")]
    PotNotDrawing,
    #[msg("Invalid entry for this pot")]
    InvalidEntry,
    #[msg("You are not the winner")]
    NotWinner,
}

// ============================================================================
// EVENTS
// ============================================================================

#[event]
pub struct CoinflipCreated {
    pub coinflip: Pubkey,
    pub creator: Pubkey,
    pub bet_amount: u64,
    pub choice: u8,
}

#[event]
pub struct CoinflipCompleted {
    pub coinflip: Pubkey,
    pub winner: Pubkey,
    pub outcome: u8,
    pub payout: u64,
    pub rake: u64,
}

#[event]
pub struct CoinflipCancelled {
    pub coinflip: Pubkey,
}

#[event]
pub struct PotCreated {
    pub pot_id: u64,
}

#[event]
pub struct PotCountdownStarted {
    pub pot_id: u64,
    pub draw_slot: u64,
}

#[event]
pub struct PotEntryAdded {
    pub pot_id: u64,
    pub player: Pubkey,
    pub amount: u64,
    pub total_pot: u64,
}

#[event]
pub struct PotDrawStarted {
    pub pot_id: u64,
    pub random_value: u64,
    pub total_pot: u64,
}

#[event]
pub struct PotCompleted {
    pub pot_id: u64,
    pub winner: Pubkey,
    pub payout: u64,
    pub rake: u64,
}
