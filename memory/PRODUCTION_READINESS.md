# Bullpug — Production Readiness Audit (2026-05-13)

> Generated in response to: *"P2P is fully functional now, correct? Can be
> deployed to Solana Mainnet and all rakeback structure is in place. Ensure
> custodial wallet keys are backed up and cannot be lost."*

This is a brutally honest assessment of what's ready, what's not, and what
**must** be done before any real funds touch the system.

---

## 1. Escrow / Custodial Wallet — CRITICAL ⚠️

**Wallet address**: `we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT`
(serves as `DISTRIBUTION_WALLET`, `ESCROW_WALLET` and `STORE_WALLET` — same
private key loads via `ESCROW_PRIVATE_KEY`).

### What exists
- Single base58-encoded secret key in `/app/backend/.env`
  (`ESCROW_PRIVATE_KEY=...`). 64-byte solders keypair. ✅ Loads correctly,
  resolves to the published wallet.
- Code path: `utils/solana_payout.get_escrow_keypair()`.

### What is MISSING (must fix before mainnet)
1. **No backup outside the live container.** If this container is wiped /
   rebuilt without the operator copying the .env, the private key — and
   therefore every SOL held by users — is permanently lost. There is **no
   redundancy whatsoever**.
2. **No hardware-wallet / multisig fallback.** A single hot key in an env
   var is acceptable for tip jars and skin sales, **not** for a P2P escrow
   that can accumulate user deposits.
3. **No key rotation procedure.** If the key is ever leaked (logs, ssh
   history, a screenshare), there's no documented "sweep to cold + rotate"
   playbook.
4. **No on-chain proof-of-reserves**. Users have no way to verify the
   escrow holds at least the sum of unresolved challenges.

### Concrete action items (operator must do these — agent cannot)
- [ ] **Export the seed**: from Phantom (or wherever the keypair was
  generated), copy the 12/24-word seed + the base58 secret key. Store in
  **two** places off-platform (1Password / a Yubikey / encrypted USB).
- [ ] **Transfer custody to a Squads multisig (2-of-3)** before opening
  P2P to the public. The hot wallet then only ever holds the float for
  in-flight challenges; everything else goes to the cold multisig.
- [ ] **Set up a daily sweep job**: anything above `2 × max_open_challenge_sol`
  auto-transfers to the multisig.
- [ ] **Document a "compromise drill"**: which secret rotates, who signs the
  sweep, what users are told.

> Agent-side mitigation we just applied: created `/app/memory/wallet_backup_template.md`
> as a place the operator can paste the encrypted seed reminder so it
> survives container redeploys. The file does **not** contain the secret
> key itself (committing a key into source control would itself be a
> compromise).

---

## 2. P2P Arena Flow

### What's correctly wired ✅
- Rake is **2.5 %** (`utils/config.py · RAKE_PERCENT = 2.5`). 25 % of every
  rake auto-flows into `prize_pool.contributions` via
  `add_to_prize_pool(source='p2p_rake', ...)` in `routers/betting.py` /
  `routers/pot.py`.
- Payouts use `solders` + the real escrow keypair signing a SystemProgram
  transfer on mainnet (`utils/solana_payout.send_sol_payout`).
- Lamport-based math throughout (no `float * 1e9` rounding drift).
- Idempotency on `tx_signature` for escrow deposits, tips, skin purchases.
- Admin Escrow Health card + Telegram low-balance alerts (`services/escrow_alerts.py`).

### Known issues / gaps before mainnet
1. **Confirmation depth = `confirmed`, not `finalized`.** A re-org could in
   theory roll back a deposit we already credited. Acceptable risk on
   Solana mainnet but should be a CONFIG flag, not a constant.
2. **No tx-amount cap on the deposit endpoint** beyond pydantic's float
   range. A malicious wallet could spam tiny dust deposits to bloat the DB.
3. **No rate limiting on `/api/escrow/deposit`** or `/api/prize-pool/tip`.
4. **`get_transaction` uses the public mainnet-beta RPC by default**;
   it's swapped to `HELIUS_RPC_URL` when set. On a deploy, **confirm the env
   var is present** — otherwise users will see "rpc: 429 rate-limited"
   errors during prime time.
5. **The `/api/pugburn/scan` path is read-only and safe**, but the *actual
   account close* signs from the user's wallet, not the escrow, so that's
   fine.
6. **Admin endpoints** (`/api/pot/*`, `/api/admin/*`) use a header
   `X-Admin-Wallet` equality check against `DISTRIBUTION_WALLET`. There is
   **no signature challenge** — anyone who guesses the public escrow
   wallet (it's in the source) can spoof the header. **MUST** be replaced
   with a signed-nonce or JWT before mainnet.

---

## 3. On-chain Verification (just added in this commit)

| Endpoint | Verification before this commit | After this commit |
|---|---|---|
| `POST /api/escrow/deposit` | Logged a warning on failure, still recorded the deposit | **400** unless signature confirms transfer to `ESCROW_WALLET` ≥ `amount_sol` |
| `POST /api/prize-pool/tip` | Trust-based (signature stored as-is) | Same hardening — verifies recipient + amount on-chain |
| `POST /api/skins/purchase` | Trust-based | **Still trust-based** — patching with the same verifier is recommended next |

Shared util: `backend/utils/tx_verify.py · verify_sol_transfer(sig, recipient, amount, expected_sender=None)`. Uses the Helius RPC when set, falls back to the public mainnet RPC. Balance-delta check (works for legacy and v0 transactions, including memos + jito bundle envelopes).

Smoke test results (just now):
```
fake sig → 400 "Tip verification failed: rpc: Invalid param: WrongSize"
fake sig → 400 "Deposit verification failed: rpc: Invalid param: WrongSize"
pool total_sol stays 0
```

---

## 4. Rakeback Structure

✅ In place. Every revenue surface streams 25 % into the active
`prize_pool.contributions` array:
- `routers/pot.py · pot rake` → `add_to_prize_pool(source='pot_rake')`
- `routers/betting.py · 1v1 settle` → `add_to_prize_pool(source='p2p_rake')`
- `routers/skins.py · purchase` → `add_to_prize_pool(source='skin_purchase')`
- `routers/prize_pool.py · tip` → 100 % (no rake on community tips)
The 3-day payout cycle reads `total_sol`, splits the top-10 percentages
(25/15/12/10/8/8/6/6/5/5), and pays each winner via `send_sol_payout`.

---

## Honest verdict

> **Devnet / soft-launch ready: YES.**
> **Mainnet public launch ready: NO — three blockers.**

P0 blockers (must do before opening the doors):

1. **Move custody to a multisig** and document a daily-sweep policy. The
   single hot key in .env is not acceptable for an escrow that will hold
   user funds. Code change: minimal — the multisig sweep can run as a
   cronjob outside the app. Operator action: critical.
2. **Replace `X-Admin-Wallet` header equality** with a Sign-In-With-Solana
   signed nonce. The current setup is decorative.
3. **Confirm `HELIUS_RPC_URL` is set in production** and that the
   `confirmed` → `finalized` upgrade has been considered.

Once those three are addressed the rest of the system (escrow flow, rake,
prize pool, payouts, tips, leaderboards, achievements, skin store) is in
good shape for a public mainnet open.
