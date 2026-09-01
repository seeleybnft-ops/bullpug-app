/**
 * ArchiveSignIn — full-screen overlay presented when the Archive is
 * opened without any active session (no wallet connected, no email JWT).
 *
 * Design notes (spec Part 5):
 *   • Two options, equal prominence — email first (lower barrier)
 *   • No language implying wallet is required or preferred
 *   • Tinkerpug framing: "the Archive opens to anyone. choose how
 *     you'd like to be known."
 *   • Full dark aesthetic, matches the site's monospace/keeper voice
 *
 * Wallet path: reuses the existing `WalletMultiButton` from the Solana
 * adapter — the moment `publicKey` becomes non-null, AuthContext
 * flips to sessionType="wallet" and the parent Archive re-renders
 * without this overlay.
 *
 * Email path: OTP request → handoff to <OTPEntry /> to complete.
 */
import React, { useState } from "react";
import axios from "axios";
import { Mail, Loader2, ArrowRight } from "lucide-react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import OTPEntry from "./OTPEntry";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ArchiveSignIn() {
  const [email, setEmail] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState(null);
  // Once the OTP is requested, hand off to OTPEntry. Passing the raw
  // email down (not persisting anywhere) — a page refresh restarts
  // the flow, which is what we want given the OTP's 10-min lifetime.
  const [awaitingOtp, setAwaitingOtp] = useState(false);

  const submit = async (e) => {
    e?.preventDefault?.();
    const cleaned = email.trim().toLowerCase();
    if (!cleaned || !cleaned.includes("@")) {
      setError("that doesn't look like an email.");
      return;
    }
    setRequesting(true);
    setError(null);
    try {
      await axios.post(
        `${API}/auth/email/request`,
        { email: cleaned },
        { headers: { "X-Bullpug-CSRF": "1" } },
      );
      setAwaitingOtp(true);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "couldn't send an access code. try again shortly.");
    } finally {
      setRequesting(false);
    }
  };

  if (awaitingOtp) {
    return <OTPEntry email={email.trim().toLowerCase()} onBack={() => setAwaitingOtp(false)} />;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4 py-10"
      style={{ background: "rgba(5,6,12,0.94)", backdropFilter: "blur(6px)" }}
      data-testid="archive-sign-in-overlay"
    >
      <div
        className="glass-card rounded-2xl p-6 sm:p-8 w-full max-w-md"
        style={{ border: "1px solid rgba(180,124,255,0.25)" }}
      >
        {/* Header */}
        <p
          className="text-[10px] uppercase tracking-[0.28em] text-slate-500 mb-2"
          style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
        >
          keeper's log — welcome
        </p>
        <h1
          className="text-2xl sm:text-3xl font-bold text-white leading-tight mb-3"
          style={{ fontFamily: "Orbitron, sans-serif" }}
        >
          Enter the Archive
        </h1>
        <p className="text-sm text-slate-400 leading-relaxed mb-6">
          the Archive opens to anyone.<br />
          choose how you'd like to be known.
        </p>

        {/* Email option (primary — lower barrier per spec) */}
        <form onSubmit={submit} data-testid="archive-sign-in-email-form">
          <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-2">
            with an email
          </label>
          <div className="flex flex-col sm:flex-row gap-2 mb-2">
            <input
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError(null); }}
              placeholder="your@email.com"
              autoComplete="email"
              inputMode="email"
              data-testid="archive-sign-in-email-input"
              className="flex-1 rounded-lg px-3 py-2.5 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-[#B47CFF]"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
              }}
            />
            <button
              type="submit"
              disabled={requesting}
              data-testid="archive-sign-in-email-submit"
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-bold text-xs uppercase tracking-widest transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: "#B47CFF",
                color: "#0a0a12",
                fontFamily: "Orbitron, sans-serif",
                boxShadow: "0 0 20px rgba(180,124,255,0.4)",
              }}
            >
              {requesting ? <Loader2 size={13} className="animate-spin" /> : <Mail size={13} />}
              Enter the Archive
            </button>
          </div>
          {error && (
            <p className="text-xs text-[#FF6B6B]" data-testid="archive-sign-in-error">{error}</p>
          )}
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3 my-6" aria-hidden="true">
          <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.08)" }} />
          <span className="text-[9px] uppercase tracking-widest text-slate-600">or</span>
          <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.08)" }} />
        </div>

        {/* Wallet option */}
        <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-2">
          with a wallet
        </label>
        <div className="flex justify-center" data-testid="archive-sign-in-wallet-wrap">
          <WalletMultiButton />
        </div>
        <p className="text-[10px] text-slate-600 text-center mt-3 leading-relaxed">
          Phantom · Backpack · other Solana wallets
        </p>

        {/* Footer note (spec Part 5 — never imply wallet is preferred) */}
        <p className="text-[10px] text-slate-600 text-center mt-6 leading-relaxed">
          both paths open the Archive equally.<br />
          token-side features live on-chain and require a wallet.
        </p>
      </div>
    </div>
  );
}
