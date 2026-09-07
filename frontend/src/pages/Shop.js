/**
 * Shop — Phase 1 holding state.
 *
 * The Kennel isn't open yet. This page shows a keeper's-log holding
 * message + email capture until the campaign launches. The access
 * gate (wallet connected + Companion's Secret tile unlocked) stays
 * exactly as-is upstream of this component — if a user can render
 * this page, they've earned the door.
 */
import { useState } from "react";
import { RankBadge } from "../components/RankBadge";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Shop() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState(null); // null | "success" | "invalid" | "error"

  const onSubmit = async (e) => {
    e?.preventDefault?.();
    const trimmed = email.trim();
    if (!EMAIL_RE.test(trimmed)) {
      setStatus("invalid");
      return;
    }
    setSubmitting(true);
    setStatus(null);
    try {
      const res = await fetch(`${API}/newsletter/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Bullpug-CSRF": "1" },
        body: JSON.stringify({ email: trimmed, source: "shop-waitlist" }),
      });
      if (!res.ok) throw new Error("subscribe failed");
      setStatus("success");
    } catch {
      setStatus("error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-lg mx-auto px-6 md:px-12">
        <div
          className="flex flex-col items-center gap-4 py-16"
          data-testid="shop-phase-1"
          role="status"
          aria-live="polite"
        >
          {/* Pulsing gold SignalGlyph — same treatment as Origins */}
          <div
            className="opacity-90"
            style={{ animation: "shop-glyph-pulse 3.4s ease-in-out infinite" }}
          >
            <RankBadge rank="keepers_circle" size={84} showTitle={false} />
          </div>

          {/* Keeper's-log holding message */}
          <p
            className="text-[12px] leading-relaxed text-slate-300 text-center whitespace-pre-line mt-2"
            style={{ fontFamily: "monospace" }}
            data-testid="shop-holding-message"
          >
            {`keeper's log — the Kennel is coming.
the pack decides when it opens.
you've found the door. that's enough for now.`}
          </p>

          {status === "success" ? (
            <p
              className="text-[11px] leading-relaxed text-center whitespace-pre-line px-3 py-3 rounded-lg mt-3 max-w-xs"
              style={{
                fontFamily: "monospace",
                color: "#F5D300",
                background: "rgba(245,211,0,0.06)",
                border: "1px solid rgba(245,211,0,0.28)",
              }}
              data-testid="shop-notify-success"
            >
              keeper's note: signal logged.{"\n"}you'll know when the Kennel opens.
            </p>
          ) : (
            <form
              onSubmit={onSubmit}
              className="w-full max-w-xs flex flex-col gap-2 mt-4"
              data-testid="shop-notify-form"
            >
              <input
                type="text"
                inputMode="email"
                autoComplete="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); if (status === "invalid") setStatus(null); }}
                placeholder="your@email.com"
                data-testid="shop-notify-input"
                className="w-full px-3 py-2 rounded-lg bg-black/50 border border-white/15 focus:border-[#F5D300]/60 focus:outline-none text-xs text-white placeholder:text-slate-600"
                style={{ fontFamily: "monospace" }}
                disabled={submitting}
              />
              <button
                type="submit"
                disabled={submitting}
                data-testid="shop-notify-submit"
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: "#F5D300",
                  color: "#0a0a12",
                  fontFamily: "Orbitron, sans-serif",
                  boxShadow: "0 0 14px rgba(245,211,0,0.25)",
                }}
              >
                {submitting ? "sending…" : "notify me when the Kennel opens"}
              </button>
              {status === "invalid" && (
                <p
                  className="text-[10px] text-red-300/90 text-center"
                  style={{ fontFamily: "monospace" }}
                  data-testid="shop-notify-invalid"
                >
                  keeper's note: that address isn't a valid signal.
                </p>
              )}
              {status === "error" && (
                <p
                  className="text-[10px] text-red-300/90 text-center"
                  style={{ fontFamily: "monospace" }}
                  data-testid="shop-notify-error"
                >
                  keeper's note: the channel dropped. try again.
                </p>
              )}
            </form>
          )}

          <style>{`
            @keyframes shop-glyph-pulse {
              0%, 100% { transform: scale(1);     filter: drop-shadow(0 0 10px rgba(245,211,0,0.35)); }
              50%      { transform: scale(1.055); filter: drop-shadow(0 0 22px rgba(245,211,0,0.6)); }
            }
          `}</style>
        </div>
      </div>
    </div>
  );
}
