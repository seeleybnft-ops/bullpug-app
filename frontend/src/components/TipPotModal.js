/**
 * TipPotModal — community can directly add SOL to the Cosmic Runner Jackpot
 * pot without playing P2P. 100% of the tipped amount goes to the pool.
 *
 * Flow:
 *   1. User picks (or types) an amount in SOL.
 *   2. Wallet signs a SystemProgram.transfer to DISTRIBUTION_WALLET.
 *   3. We POST the tx signature to /api/prize-pool/tip — backend credits the
 *      active pool and writes a pot_tips row.
 */

import { useState } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import {
  Transaction,
  SystemProgram,
  PublicKey,
  LAMPORTS_PER_SOL,
} from "@solana/web3.js";
import axios from "axios";
import { toast } from "sonner";
import { X, Coins, Flame, Sparkles, AlertCircle, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const DISTRIBUTION_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT";

const QUICK_AMOUNTS = [0.01, 0.05, 0.1, 0.5, 1.0];

export default function TipPotModal({ open, onClose, onTipped }) {
  const { publicKey, connected, sendTransaction } = useWallet();
  const { connection } = useConnection();
  const [amount, setAmount] = useState(0.05);
  const [customMode, setCustomMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const setQuick = (v) => {
    setAmount(v);
    setCustomMode(false);
  };

  const setCustom = (raw) => {
    setCustomMode(true);
    const v = parseFloat(raw);
    if (Number.isFinite(v)) setAmount(v);
    else setAmount(0);
  };

  const handleTip = async () => {
    if (!connected || !publicKey) {
      toast.error("Connect your wallet to tip the pot");
      return;
    }
    if (!Number.isFinite(amount) || amount < 0.001) {
      toast.error("Minimum tip is 0.001 SOL");
      return;
    }
    if (amount > 100) {
      toast.error("Maximum tip is 100 SOL — split it if needed");
      return;
    }
    setSubmitting(true);
    const loadingToast = toast.loading(`Tipping ${amount.toFixed(4)} SOL to the pot...`);
    try {
      const lamports = Math.round(amount * LAMPORTS_PER_SOL);
      const tx = new Transaction().add(
        SystemProgram.transfer({
          fromPubkey: publicKey,
          toPubkey: new PublicKey(DISTRIBUTION_WALLET),
          lamports,
        })
      );
      const { blockhash } = await connection.getLatestBlockhash();
      tx.recentBlockhash = blockhash;
      tx.feePayer = publicKey;

      const signature = await sendTransaction(tx, connection);
      await connection.confirmTransaction(signature, "confirmed");

      let displayName = "";
      try { displayName = localStorage.getItem("bullpugPlayerName") || ""; } catch (e) { /* ignore */ }

      const { data } = await axios.post(`${API}/prize-pool/tip`, {
        wallet_address: publicKey.toBase58(),
        amount_sol: amount,
        tx_signature: signature,
        display_name: displayName,
      });

      toast.dismiss(loadingToast);
      toast.success(
        <div>
          <p className="font-bold text-[#F5D300]">Thanks for feeding the pot! 🐾</p>
          <p className="text-xs text-slate-300 mt-1">
            +{amount.toFixed(4)} SOL → new pot {Number(data?.new_pool_total_sol || 0).toFixed(4)} SOL
          </p>
        </div>
      );
      onTipped?.({ amount, signature, newTotal: data?.new_pool_total_sol });
      onClose?.();
    } catch (e) {
      toast.dismiss(loadingToast);
      const msg = e?.response?.data?.detail || e?.message || "Tip failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center px-4"
      data-testid="tip-pot-modal"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={submitting ? undefined : onClose}
        data-testid="tip-pot-modal-backdrop"
      />
      {/* Card */}
      <div className="relative w-full max-w-md rounded-2xl border border-[#F5D300]/40 bg-gradient-to-br from-[#1a1308] via-[#0a0612] to-[#1a0810] p-6 shadow-[0_0_50px_rgba(245,211,0,0.25)]">
        <button
          type="button"
          onClick={onClose}
          disabled={submitting}
          aria-label="Close"
          data-testid="tip-pot-close-btn"
          className="absolute top-3 right-3 w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-colors disabled:opacity-40"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#F5D300] to-[#FF6B6B] flex items-center justify-center shadow-[0_0_24px_rgba(245,211,0,0.5)]">
            <Coins className="w-5 h-5 text-black" strokeWidth={2.5} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.25em] text-[#F5D300] font-bold" style={{ fontFamily: "Orbitron" }}>
              Cosmic Runner Jackpot
            </div>
            <h2 className="text-xl font-black text-white" style={{ fontFamily: "Orbitron" }}>
              Feed the Pot
            </h2>
          </div>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed mb-5">
          Top up the runners' jackpot directly. <span className="text-white font-semibold">100%</span> of your tip goes to the pool — no rake, no fees beyond the standard Solana network fee.
        </p>

        {/* Amount picker */}
        <div className="mb-4">
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold mb-2">Amount (SOL)</div>
          <div className="grid grid-cols-5 gap-1.5 mb-2">
            {QUICK_AMOUNTS.map((v) => {
              const active = !customMode && Math.abs(amount - v) < 1e-9;
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => setQuick(v)}
                  data-testid={`tip-pot-quick-${v}`}
                  disabled={submitting}
                  className={`py-2 rounded-lg text-xs font-bold border transition-colors ${
                    active
                      ? "bg-[#F5D300] text-black border-[#F5D300]"
                      : "bg-white/5 text-slate-300 border-white/10 hover:border-[#F5D300]/40"
                  }`}
                >
                  {v}
                </button>
              );
            })}
          </div>
          <div className="relative">
            <input
              type="number"
              step="0.001"
              min="0.001"
              max="100"
              placeholder="Custom amount"
              value={customMode ? (amount || "") : ""}
              onChange={(e) => setCustom(e.target.value)}
              data-testid="tip-pot-custom-input"
              disabled={submitting}
              className="w-full px-3 py-2.5 bg-black/40 border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-[#F5D300]/50"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500 font-bold">SOL</span>
          </div>
        </div>

        {/* Live total preview */}
        <div className="rounded-xl bg-black/40 border border-white/10 p-3 mb-5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">You send</span>
            <span className="text-[#F5D300] font-black tabular-nums" style={{ fontFamily: "Orbitron" }}>
              {Number.isFinite(amount) ? amount.toFixed(4) : "0.0000"} SOL
            </span>
          </div>
          <div className="flex items-center justify-between text-xs mt-2">
            <span className="text-slate-400 flex items-center gap-1"><Sparkles className="w-3 h-3 text-[#00FFA3]" /> Goes to runners</span>
            <span className="text-[#00FFA3] font-bold tabular-nums">
              100% · {Number.isFinite(amount) ? amount.toFixed(4) : "0.0000"} SOL
            </span>
          </div>
        </div>

        {!connected && (
          <div className="flex items-start gap-2 text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5 mb-4">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            <span>Connect your Solana wallet first to sign the tip.</span>
          </div>
        )}

        <button
          type="button"
          onClick={handleTip}
          disabled={submitting || !connected || !Number.isFinite(amount) || amount <= 0}
          data-testid="tip-pot-confirm-btn"
          className="w-full py-3 rounded-full bg-gradient-to-r from-[#F5D300] to-[#FF6B6B] text-black font-black uppercase tracking-wider text-xs hover:scale-[1.02] transition-transform disabled:opacity-40 disabled:hover:scale-100 inline-flex items-center justify-center gap-2"
          style={{ fontFamily: "Orbitron" }}
        >
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" /> Signing transfer...
            </>
          ) : (
            <>
              <Flame className="w-4 h-4" /> Tip {Number.isFinite(amount) ? amount.toFixed(4) : "0"} SOL
            </>
          )}
        </button>

        <p className="text-[10px] text-slate-500 text-center mt-3">
          Funds land in the escrow that pays the next top-10 split. No refunds.
        </p>
      </div>
    </div>
  );
}
