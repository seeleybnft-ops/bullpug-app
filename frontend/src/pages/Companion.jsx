/**
 * Companion — physical-companion token claim page.
 *
 * Flow:
 *   /companion?key=<token>
 *   1. On mount, validate the token via `GET /api/companion/validate`.
 *   2. Show the appropriate state:
 *        • unknown       — friendly "not a valid token"
 *        • already_claimed — friendly "someone else already found it"
 *        • valid         — prompt wallet-connect
 *   3. When the wallet connects, POST `/api/companion/claim` with the
 *      token + wallet. On success:
 *        • play the celebration (plushie bounce + bark soundwave)
 *        • stream Tinkerpug's message in
 *        • display the entry text
 *        • give the visitor a "Enter the Archive" CTA
 *
 * The unlock itself is fired server-side inside the claim endpoint —
 * this page just triggers the celebration UI and pushes the visitor
 * into /archive when they're done reading.
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useWallet } from "@solana/wallet-adapter-react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import { AlertCircle, Loader2, ArrowRight, PawPrint } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ── Streamed-text hook ─────────────────────────────────────────────────
function useStreamedText(text, enabled, speedMs = 22) {
  const [rendered, setRendered] = useState("");
  useEffect(() => {
    if (!enabled || !text) {
      setRendered("");
      return undefined;
    }
    let i = 0;
    setRendered("");
    const id = setInterval(() => {
      i += 1;
      setRendered(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speedMs);
    return () => clearInterval(id);
  }, [text, enabled, speedMs]);
  return rendered;
}

// ── Celebration overlay pieces ────────────────────────────────────────
function PlushieBounce() {
  return (
    <div
      className="absolute left-1/2 -translate-x-1/2 pointer-events-none"
      style={{
        top: 16,
        width: 96,
        height: 96,
        animation: "companion-bounce 1.6s ease-out",
      }}
      aria-hidden
    >
      <div
        className="w-full h-full rounded-full flex items-center justify-center"
        style={{
          background:
            "radial-gradient(circle at 35% 30%, #F5D300 0%, #C9A200 55%, #715c00 100%)",
          border: "3px solid #F5D300",
          boxShadow:
            "0 0 32px rgba(245,211,0,0.55), inset 0 -8px 16px rgba(0,0,0,0.35)",
        }}
      >
        <PawPrint size={36} strokeWidth={2.4} style={{ color: "#0a0a12" }} />
      </div>
    </div>
  );
}

function BarkSoundwave() {
  // Three staggered rings sweeping outward. All CSS keyframes are
  // scoped to this page in the <style> block below.
  return (
    <div className="absolute inset-0 pointer-events-none" aria-hidden>
      {[0, 0.4, 0.8].map((delay, i) => (
        <span
          key={i}
          className="absolute left-1/2 top-1/2 rounded-full"
          style={{
            transform: "translate(-50%,-50%)",
            width: 20,
            height: 20,
            border: "2px solid rgba(245,211,0,0.6)",
            opacity: 0,
            animation: `companion-wave 2s ease-out ${delay}s 1`,
          }}
        />
      ))}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────
export default function Companion() {
  const [params] = useSearchParams();
  const token = (params.get("key") || "").trim();
  const { publicKey, connected } = useWallet();
  const navigate = useNavigate();

  const [state, setState] = useState("loading"); // loading | invalid | claimed | ready | claiming | success | error
  const [reason, setReason] = useState(null);
  const [claim, setClaim] = useState(null); // { celebration_text, entry_text }
  const [error, setError] = useState(null);

  const celebration = useStreamedText(claim?.celebration_text || "", state === "success");

  // 1. Validate on mount / token change
  useEffect(() => {
    if (!token) {
      setState("invalid");
      setReason("no_key");
      return;
    }
    let cancelled = false;
    (async () => {
      setState("loading");
      try {
        const res = await fetch(
          `${API}/companion/validate?key=${encodeURIComponent(token)}`
        );
        const data = await res.json();
        if (cancelled) return;
        if (data.valid) {
          setState("ready");
        } else if (data.claimed) {
          setState("claimed");
          setReason(data.reason);
        } else {
          setState("invalid");
          setReason(data.reason || "unknown");
        }
      } catch (e) {
        if (cancelled) return;
        setState("error");
        setError("Signal dropped. Try again.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  // 2. Auto-claim when the wallet connects
  useEffect(() => {
    if (state !== "ready" || !connected || !publicKey) return;
    const wallet = publicKey.toBase58();
    setState("claiming");
    (async () => {
      try {
        const res = await fetch(`${API}/companion/claim`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Bullpug-CSRF": "1",
          },
          body: JSON.stringify({ token, wallet_address: wallet }),
        });
        const data = await res.json();
        if (!res.ok) {
          if (res.status === 409) {
            setState("claimed");
            setReason("already_claimed");
            return;
          }
          throw new Error(data.detail || "claim failed");
        }
        setClaim(data);
        setState("success");
      } catch (e) {
        setState("error");
        setError(e.message || "Claim failed. Try again shortly.");
      }
    })();
  }, [state, connected, publicKey, token]);

  return (
    <div
      className="min-h-[calc(100vh-4rem)] pt-16 flex items-center justify-center px-4"
      data-testid="companion-page"
      style={{
        background:
          "radial-gradient(ellipse at 20% 20%, rgba(24,20,60,0.9) 0%, #05050A 55%, #05050A 100%)",
      }}
    >
      <div
        className="relative w-full max-w-lg rounded-2xl p-8 sm:p-10"
        style={{
          background:
            "linear-gradient(180deg, rgba(15,20,42,0.95) 0%, rgba(5,7,18,0.98) 100%)",
          border: "1px solid rgba(245,211,0,0.28)",
          boxShadow:
            "0 0 40px rgba(245,211,0,0.15), inset 0 0 0 1px rgba(255,255,255,0.03)",
        }}
      >
        {/* ── Loading ── */}
        {state === "loading" && (
          <div className="text-center" data-testid="companion-loading">
            <Loader2 className="mx-auto mb-4 animate-spin text-yellow-300" size={28} />
            <p
              className="text-[10px] uppercase tracking-[0.35em] text-yellow-300/70"
              style={{ fontFamily: "monospace" }}
            >
              keeper's station · verifying signal
            </p>
          </div>
        )}

        {/* ── Invalid token ── */}
        {state === "invalid" && (
          <div className="text-center" data-testid="companion-invalid">
            <div
              className="mx-auto mb-4 flex items-center justify-center rounded-full"
              style={{
                width: 60,
                height: 60,
                background:
                  "radial-gradient(circle at 35% 30%, rgba(245,211,0,0.45) 0%, rgba(115,92,0,0.5) 60%, rgba(15,15,25,0.9) 100%)",
                border: "1px solid rgba(245,211,0,0.35)",
              }}
            >
              <PawPrint size={26} style={{ color: "rgba(245,211,0,0.85)" }} strokeWidth={2.2} />
            </div>
            <p
              className="text-[10px] uppercase tracking-[0.32em] text-yellow-300/70 mb-3"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              keeper's station
            </p>
            <p
              className="text-sm text-slate-200 leading-relaxed mb-5 whitespace-pre-wrap text-left px-2"
              data-testid="companion-invalid-message"
            >
              keeper's log — this key hasn't been activated yet, or it's already been
              claimed. if you're waiting on a companion, it's on its way. the Archive
              will be here when it arrives.
            </p>
            <button
              type="button"
              onClick={() => navigate("/archive")}
              data-testid="companion-invalid-archive-btn"
              className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-[11px] font-bold uppercase tracking-widest"
              style={{
                background: "#F5D300",
                color: "#0a0a12",
                fontFamily: "Orbitron, sans-serif",
                boxShadow: "0 0 20px rgba(245,211,0,0.35)",
              }}
            >
              Enter the Archive <ArrowRight size={13} />
            </button>
          </div>
        )}

        {/* ── Already claimed ── */}
        {state === "claimed" && (
          <div className="text-center" data-testid="companion-claimed">
            <PawPrint className="mx-auto mb-3 text-yellow-300/70" size={32} />
            <h1
              className="text-xl font-bold mb-2"
              style={{ fontFamily: "Orbitron, sans-serif", color: "#F5D300" }}
            >
              This companion has already crossed
            </h1>
            <p className="text-sm text-slate-300 mb-4 leading-relaxed">
              Someone got here first. Every companion carries a single signal —
              once it's answered, that particular one is done.
            </p>
            <p className="text-xs italic text-slate-500 mb-6">
              keeper's note: take care of the companion. The record stands whether
              or not it can still be claimed.
            </p>
            <button
              type="button"
              onClick={() => navigate("/archive")}
              data-testid="companion-claimed-archive-btn"
              className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-[11px] font-bold uppercase tracking-widest"
              style={{
                background: "#F5D300",
                color: "#0a0a12",
                fontFamily: "Orbitron, sans-serif",
                boxShadow: "0 0 20px rgba(245,211,0,0.4)",
              }}
            >
              Enter the Archive <ArrowRight size={13} />
            </button>
          </div>
        )}

        {/* ── Ready for wallet-connect ── */}
        {state === "ready" && (
          <div className="text-center" data-testid="companion-ready">
            <div
              className="mx-auto mb-5 flex items-center justify-center rounded-full"
              style={{
                width: 72,
                height: 72,
                background:
                  "radial-gradient(circle at 35% 30%, #F5D300 0%, #C9A200 60%, #715c00 100%)",
                boxShadow: "0 0 24px rgba(245,211,0,0.35)",
              }}
            >
              <PawPrint size={30} style={{ color: "#0a0a12" }} strokeWidth={2.4} />
            </div>
            <h1
              className="text-2xl font-bold mb-2"
              style={{ fontFamily: "Orbitron, sans-serif", color: "#F5D300" }}
            >
              You found a companion
            </h1>
            <p className="text-sm text-slate-300 mb-6 leading-relaxed">
              Connect your wallet to claim the record. The Archive has an entry for
              what you just did — it only appears once the physical object is
              linked to a chain identity.
            </p>
            <div className="flex justify-center" data-testid="companion-connect-slot">
              <WalletMultiButton
                style={{
                  background: "#F5D300",
                  color: "#0a0a12",
                  height: 44,
                  padding: "0 22px",
                  borderRadius: 999,
                  fontFamily: "Orbitron, sans-serif",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  boxShadow: "0 0 20px rgba(245,211,0,0.4)",
                }}
              />
            </div>
          </div>
        )}

        {/* ── Claiming ── */}
        {state === "claiming" && (
          <div className="text-center" data-testid="companion-claiming">
            <Loader2 className="mx-auto mb-4 animate-spin text-yellow-300" size={28} />
            <p
              className="text-[10px] uppercase tracking-[0.35em] text-yellow-300/70"
              style={{ fontFamily: "monospace" }}
            >
              keeper's station · filing the signal
            </p>
          </div>
        )}

        {/* ── Success — the celebration ── */}
        {state === "success" && claim && (
          <div className="relative" data-testid="companion-success">
            <div
              className="relative"
              style={{ height: 130 }}
            >
              <BarkSoundwave />
              <PlushieBounce />
            </div>
            <div className="mt-4 mb-6 text-center">
              <p
                className="text-[10px] uppercase tracking-[0.32em] text-yellow-300/80 mb-2"
                style={{ fontFamily: "Orbitron, sans-serif" }}
              >
                Archive Special · The Companion's Secret
              </p>
              <h2
                className="text-2xl font-bold mb-1"
                style={{ fontFamily: "Orbitron, sans-serif", color: "#F5D300" }}
              >
                Filed
              </h2>
            </div>
            <div
              className="rounded-xl p-5 mb-5 whitespace-pre-wrap text-sm leading-relaxed text-slate-200 min-h-[168px]"
              style={{
                background: "rgba(5,7,18,0.6)",
                border: "1px solid rgba(245,211,0,0.28)",
              }}
              data-testid="companion-tinkerpug-message"
            >
              {celebration}
              {celebration.length < (claim.celebration_text || "").length && (
                <span className="inline-block w-2 h-3 bg-yellow-300/70 animate-pulse ml-0.5" />
              )}
            </div>
            <button
              type="button"
              onClick={() => navigate("/archive")}
              data-testid="companion-success-archive-btn"
              className="w-full inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-[11px] font-bold uppercase tracking-widest"
              style={{
                background: "#F5D300",
                color: "#0a0a12",
                fontFamily: "Orbitron, sans-serif",
                boxShadow: "0 0 20px rgba(245,211,0,0.4)",
              }}
            >
              Enter the Archive <ArrowRight size={13} />
            </button>
          </div>
        )}

        {/* ── Error ── */}
        {state === "error" && (
          <div className="text-center" data-testid="companion-error">
            <AlertCircle className="mx-auto mb-3 text-red-400/70" size={32} />
            <h1
              className="text-xl font-bold mb-2"
              style={{ fontFamily: "Orbitron, sans-serif", color: "#fff" }}
            >
              The channel dropped
            </h1>
            <p className="text-sm text-slate-400 mb-4">{error}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              data-testid="companion-error-retry-btn"
              className="text-xs uppercase tracking-widest text-yellow-300/80 hover:text-yellow-200 transition-colors"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              Try again
            </button>
          </div>
        )}
      </div>

      <style>{`
        @keyframes companion-bounce {
          0%   { transform: translate(-50%, -240%) scale(0.4); opacity: 0; }
          40%  { transform: translate(-50%, 12%)   scale(1.15); opacity: 1; }
          65%  { transform: translate(-50%, -8%)   scale(0.94); }
          85%  { transform: translate(-50%, 3%)    scale(1.03); }
          100% { transform: translate(-50%, 0%)    scale(1); }
        }
        @keyframes companion-wave {
          0%   { opacity: 0; width: 20px;  height: 20px;  border-width: 3px; }
          20%  { opacity: 0.7; }
          100% { opacity: 0; width: 260px; height: 260px; border-width: 1px; }
        }
      `}</style>
    </div>
  );
}
