# Bullpug Escrow Wallet — Backup Procedure

**Wallet address (public, safe to share)**:
`we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`

This file is the **operator's backup checklist**, not the backup itself.
A private key in plaintext on disk is itself a leak — never paste it here.

---

## 1. Where the live key lives RIGHT NOW

- `/app/backend/.env` → `ESCROW_PRIVATE_KEY=<base58 64-byte secret>`
- That's the **only** copy on the platform. If this container is rebuilt
  without preserving the env, **the wallet is lost**.

## 2. Off-platform backups you must create

Pick **two** independent storage methods. Do all of them:

- [ ] **Password manager** (1Password / Bitwarden / Proton Pass) — create
      a Secure Note titled "Bullpug Escrow Key" with:
      - Base58 secret key (copy from `.env`)
      - 12/24-word seed phrase from Phantom (or whichever wallet generated it)
      - Wallet pubkey for cross-check
- [ ] **Hardware air-gapped** — write the 12/24 words on the metal plate
      that comes with a Ledger / Cryptosteel backup, store in a safe.
- [ ] **Optional second cloud**: encrypted file in your personal Drive,
      gpg-encrypted with a passphrase only you know.

## 3. Restore procedure (if the container is wiped)

1. Spin up a fresh Bullpug deploy.
2. SSH or use the env editor: set
   `ESCROW_PRIVATE_KEY=<value from password manager>`.
3. `sudo supervisorctl restart backend`
4. `curl <preview-url>/api/escrow/balance` → should match the on-chain
   balance for `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`.

## 4. Compromise drill (if you suspect leakage)

1. From the password-manager backup, immediately sign a SystemProgram
   transfer of the **full balance** to a fresh wallet (or a cold multisig).
   - You can do this from any browser wallet that imports the seed phrase.
2. Generate a new keypair, fund it with ~0.05 SOL for rent + fees.
3. Update `ESCROW_PRIVATE_KEY` in the live env to the new keypair.
4. Update `DISTRIBUTION_WALLET` in `/app/backend/utils/config.py`
   (and `STORE_WALLET` reference in `frontend/src/components/SkinStore.js`
   + `TipPotModal.js`) to the new pubkey.
5. Restart backend; smoke test deposit + payout.
6. **Communicate** to users that the escrow has rotated.

## 5. Long-term: replace the single hot key with a multisig

Recommended before public mainnet launch:
- Set up a **Squads** 2-of-3 multisig with three signers
  (you + cofounder + emergency cold key).
- Move the bulk of the treasury to the multisig.
- The hot wallet keeps only `2 × max_open_challenge_sol` for fast payouts.
- A daily cron transfers anything above that into the multisig.

This is an operator/devops task — the app code already supports any
pubkey via the env var, no rewrite needed.
