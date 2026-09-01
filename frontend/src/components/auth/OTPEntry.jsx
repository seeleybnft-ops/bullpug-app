/**
 * OTPEntry — 6-digit access code entry, spec Part 5.
 *
 * Rules:
 *   • Digits only, 6 slots
 *   • Paste supported (paste "424242" → auto-fills all 6)
 *   • Verify button enabled only when all 6 digits filled
 *   • Resend cooldown: 60s (per spec; backend still rate-limits 3/hr)
 *   • On success → AuthContext.signInWithJwt(token) → parent overlay unmounts
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { ArrowLeft, Loader2, ShieldCheck } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const OTP_LEN = 6;
const RESEND_COOLDOWN = 60;

export default function OTPEntry({ email, onBack }) {
  const { signInWithJwt } = useAuth();
  const [digits, setDigits] = useState(Array(OTP_LEN).fill(""));
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(null);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(RESEND_COOLDOWN);
  const inputsRef = useRef([]);

  // Auto-focus the first input on mount.
  useEffect(() => { inputsRef.current[0]?.focus(); }, []);

  // Cooldown countdown — pure display, backend enforces the real limit.
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const code = useMemo(() => digits.join(""), [digits]);
  const complete = code.length === OTP_LEN && digits.every((d) => /^\d$/.test(d));

  const setDigit = (i, val) => {
    setError(null);
    const only = (val || "").replace(/\D/g, "").slice(0, 1);
    setDigits((prev) => {
      const next = [...prev];
      next[i] = only;
      return next;
    });
    if (only && i < OTP_LEN - 1) inputsRef.current[i + 1]?.focus();
  };

  const onKeyDown = (e, i) => {
    if (e.key === "Backspace" && !digits[i] && i > 0) {
      inputsRef.current[i - 1]?.focus();
    } else if (e.key === "ArrowLeft" && i > 0) {
      inputsRef.current[i - 1]?.focus();
    } else if (e.key === "ArrowRight" && i < OTP_LEN - 1) {
      inputsRef.current[i + 1]?.focus();
    } else if (e.key === "Enter" && complete) {
      verify();
    }
  };

  const onPaste = (e) => {
    const pasted = (e.clipboardData?.getData("text") || "").replace(/\D/g, "").slice(0, OTP_LEN);
    if (!pasted) return;
    e.preventDefault();
    const next = Array(OTP_LEN).fill("");
    for (let i = 0; i < pasted.length; i++) next[i] = pasted[i];
    setDigits(next);
    inputsRef.current[Math.min(pasted.length, OTP_LEN - 1)]?.focus();
  };

  const verify = useCallback(async () => {
    if (!complete || verifying) return;
    setVerifying(true);
    setError(null);
    try {
      const { data } = await axios.post(
        `${API}/auth/email/verify`,
        { email, otp: code },
        { headers: { "X-Bullpug-CSRF": "1" } },
      );
      signInWithJwt(data.token);
      // No unmount call needed — AuthContext flips sessionType and the
      // parent overlay unmounts on its next render.
    } catch (err) {
      const detail = err?.response?.data?.detail || "couldn't verify. try again.";
      setError(detail);
      // Clear the digits so the user can retype without ambiguity.
      setDigits(Array(OTP_LEN).fill(""));
      inputsRef.current[0]?.focus();
    } finally {
      setVerifying(false);
    }
  }, [complete, verifying, email, code, signInWithJwt]);

  const resend = async () => {
    if (cooldown > 0 || resending) return;
    setResending(true);
    setError(null);
    try {
      await axios.post(
        `${API}/auth/email/request`,
        { email },
        { headers: { "X-Bullpug-CSRF": "1" } },
      );
      setCooldown(RESEND_COOLDOWN);
    } catch (err) {
      const detail = err?.response?.data?.detail || "couldn't resend. try in a bit.";
      setError(detail);
    } finally {
      setResending(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4 py-10"
      style={{ background: "rgba(5,6,12,0.94)", backdropFilter: "blur(6px)" }}
      data-testid="archive-otp-overlay"
    >
      <div
        className="glass-card rounded-2xl p-6 sm:p-8 w-full max-w-md"
        style={{ border: "1px solid rgba(180,124,255,0.25)" }}
      >
        <button
          type="button"
          onClick={onBack}
          data-testid="archive-otp-back"
          className="inline-flex items-center gap-1 text-[10px] uppercase tracking-widest text-slate-400 hover:text-white mb-4"
        >
          <ArrowLeft size={11} /> use a different email
        </button>

        <p
          className="text-[10px] uppercase tracking-[0.28em] text-slate-500 mb-2"
          style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
        >
          keeper's log — check your inbox
        </p>
        <h1
          className="text-2xl sm:text-3xl font-bold text-white leading-tight mb-2"
          style={{ fontFamily: "Orbitron, sans-serif" }}
        >
          Enter your code
        </h1>
        <p className="text-sm text-slate-400 leading-relaxed mb-6">
          a 6-digit access code was sent to<br />
          <span className="text-slate-200 font-mono">{email}</span>
        </p>

        <div className="flex gap-2 justify-between mb-3" data-testid="archive-otp-input-row">
          {digits.map((d, i) => (
            <input
              key={i}
              ref={(el) => { inputsRef.current[i] = el; }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={d}
              onChange={(e) => setDigit(i, e.target.value)}
              onKeyDown={(e) => onKeyDown(e, i)}
              onPaste={i === 0 ? onPaste : undefined}
              disabled={verifying}
              data-testid={`archive-otp-digit-${i}`}
              className="flex-1 min-w-0 h-12 sm:h-14 text-center text-lg sm:text-xl font-bold rounded-lg text-white focus:outline-none focus:ring-1 focus:ring-[#B47CFF] disabled:opacity-50"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                letterSpacing: "0.05em",
              }}
            />
          ))}
        </div>

        {error && (
          <p className="text-xs text-[#FF6B6B] mb-3" data-testid="archive-otp-error">{error}</p>
        )}

        <button
          type="button"
          onClick={verify}
          disabled={!complete || verifying}
          data-testid="archive-otp-verify"
          className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-bold text-xs uppercase tracking-widest transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: "#B47CFF",
            color: "#0a0a12",
            fontFamily: "Orbitron, sans-serif",
            boxShadow: "0 0 20px rgba(180,124,255,0.4)",
          }}
        >
          {verifying ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
          Verify
        </button>

        <p className="text-[10px] text-slate-500 text-center mt-4">
          {cooldown > 0 ? (
            <>resend available in <span className="text-slate-300">{cooldown}s</span></>
          ) : (
            <button
              type="button"
              onClick={resend}
              disabled={resending}
              data-testid="archive-otp-resend"
              className="underline hover:text-white disabled:opacity-50"
            >
              {resending ? "sending…" : "resend code"}
            </button>
          )}
        </p>
      </div>
    </div>
  );
}
