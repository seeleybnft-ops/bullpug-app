/**
 * WhatsNewToast — one-shot "What's New in this build" announcement.
 *
 * Fires a sonner toast exactly once per user per build. The current
 * build is identified by `BUILD_ID` below; bump it whenever you want a
 * new announcement to fire for everyone. Suppression is stored as
 * `localStorage.bullpugLastSeenBuild` so returning users don't see the
 * same announcement twice.
 *
 * Safety:
 *   • Wrapped in try/catch so localStorage SecurityErrors (private
 *     browsing / sandboxed iframes) never crash the app — worst case,
 *     a user in private mode sees the toast every visit, which is fine.
 *   • Mounted next to `BigWinToast` in App.js so it runs once on every
 *     full app load after the PrivateAccessGate clears.
 *   • Delays display by 2.5s to let the page settle / wallet adapters
 *     finish bootstrapping before the toast appears.
 */

import { useEffect } from "react";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";

// Bump this string whenever you want all users to see a new announcement.
// Keep it short and readable; old IDs are kept commented for reference.
const BUILD_ID = "2026-02-27-canon-lock";

// Highlights array — drives the toast's bullet list. Keep punchy and
// player-facing (no internal jargon like "iteration 161").
const HIGHLIGHTS = [
  "Bullpug canon locked — the fawn guardian across the whole site",
  "Origins page rewritten — new artwork for every chapter",
  "Tinkerpug AI upgraded with the Visual Canon Ledger",
  "New Ecosystem tile — ask Tinkerpug anything, right from home",
];

export default function WhatsNewToast() {
  useEffect(() => {
    let storedBuild = null;
    try {
      storedBuild = localStorage.getItem("bullpugLastSeenBuild");
    } catch {
      // Storage unavailable — we'll show the toast on every load for
      // users in private mode. Acceptable degradation.
    }

    if (storedBuild === BUILD_ID) return; // user already saw this build

    const timer = setTimeout(() => {
      toast.custom(
        (id) => (
          <div
            className="glass-card rounded-2xl p-5 border border-[#00FFA3]/30 shadow-xl max-w-sm"
            style={{ background: "linear-gradient(140deg, rgba(0,255,163,0.08), rgba(217,70,239,0.08), rgba(0,0,0,0.7))" }}
            data-testid="whats-new-toast"
          >
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-[#00FFA3]" />
              <p className="text-sm font-black uppercase tracking-wider text-[#00FFA3]" style={{ fontFamily: "Orbitron, sans-serif" }}>
                What&apos;s new
              </p>
            </div>
            <ul className="space-y-1.5">
              {HIGHLIGHTS.map((h, i) => (
                <li key={i} className="text-xs text-slate-200 flex items-start gap-2">
                  <span className="text-[#D946EF] mt-[2px]">▸</span>
                  <span>{h}</span>
                </li>
              ))}
            </ul>
            <button
              onClick={() => toast.dismiss(id)}
              data-testid="whats-new-dismiss"
              className="mt-3 w-full py-2 rounded-lg bg-[#00FFA3] text-black text-xs font-bold uppercase tracking-wider hover:scale-[1.02] transition-transform"
            >
              Got it
            </button>
          </div>
        ),
        { duration: 12000, position: "bottom-right" }
      );

      try {
        localStorage.setItem("bullpugLastSeenBuild", BUILD_ID);
      } catch {
        // Storage unavailable — toast will re-show on next load.
      }
    }, 2500);

    return () => clearTimeout(timer);
  }, []);

  return null;
}
