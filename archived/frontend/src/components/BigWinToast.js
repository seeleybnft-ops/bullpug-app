import { useEffect, useRef, useState, useCallback } from "react";
import { Trophy, X, Coins, Sparkles } from "lucide-react";
import { FaXTwitter } from "react-icons/fa6";
import useBrowserNotifications from "../hooks/useBrowserNotifications";
import { playBigWinFanfare } from "../utils/sounds";

const LOGO =
  "/bullpug-canon.jpg";

const DISPLAY_DURATION_MS = 9000;
const MAX_VISIBLE = 3;

function buildShareText(win) {
  const game = win.game === "pot" ? "Winner Pot" : "Coin Flip";
  return (
    `${win.winner_name} just took ${win.payout_sol} SOL out of a Bullpug ${game}. ` +
    `Every rake feeds the Cosmic Runner Jackpot. 🐾⚡`
  );
}

function shareOnX(win) {
  const text = buildShareText(win);
  const url = `${window.location.origin}/betting`;
  const intent = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
  window.open(intent, "_blank", "noopener,noreferrer");
}

export default function BigWinToast() {
  const [wins, setWins] = useState([]); // visible queue
  const timersRef = useRef({});
  const seenIdsRef = useRef(new Set());
  const { notify } = useBrowserNotifications();

  const dismissWin = useCallback((id) => {
    setWins((prev) => prev.filter((w) => w._toastId !== id));
    if (timersRef.current[id]) {
      clearTimeout(timersRef.current[id]);
      delete timersRef.current[id];
    }
  }, []);

  const enqueueWin = useCallback((win) => {
    // Dedupe — backend doesn't send a stable id, so build one from contents
    const dedupeKey = `${win.game}-${win.occurred_at}-${win.winner_wallet || ""}-${win.payout_sol}`;
    if (seenIdsRef.current.has(dedupeKey)) return;
    seenIdsRef.current.add(dedupeKey);

    const _toastId = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const next = { ...win, _toastId };

    setWins((prev) => {
      const list = [...prev, next];
      // Trim oldest if we exceed MAX_VISIBLE
      while (list.length > MAX_VISIBLE) {
        const trimmed = list.shift();
        if (timersRef.current[trimmed._toastId]) {
          clearTimeout(timersRef.current[trimmed._toastId]);
          delete timersRef.current[trimmed._toastId];
        }
      }
      return list;
    });

    // 🎺 CELEBRATION — multi-note fanfare + haptic burst. Fired on every
    // qualifying big win so the page feels alive in real-time. Silently
    // no-ops if sound is disabled or the audio context is suspended.
    playBigWinFanfare();

    // Auto-dismiss
    timersRef.current[_toastId] = setTimeout(() => dismissWin(_toastId), DISPLAY_DURATION_MS);

    // Native browser notification when tab is hidden
    try {
      notify({
        title: `🏆 ${win.winner_name} won ${win.payout_sol} SOL`,
        body: `Bullpug ${win.game === "pot" ? "Winner Pot" : "Coin Flip"} just resolved.`,
        icon: LOGO,
        tag: `bigwin-${dedupeKey}`,
        onClick: () => window.open("/betting", "_self"),
      });
    } catch (e) { /* ignore */ }
  }, [dismissWin, notify]);

  // Poll the API every ~6 seconds. WebSockets can't traverse all ingress
  // configurations; polling is rare-event-friendly and 100% reliable.
  useEffect(() => {
    const apiUrl = process.env.REACT_APP_BACKEND_URL || "";
    const url = `${apiUrl}/api/big-wins/recent`;
    let stopped = false;
    let lastSeenIso = new Date().toISOString();  // only show wins AFTER mount

    const tick = async () => {
      if (stopped) return;
      try {
        const params = new URLSearchParams({ limit: "5", since: lastSeenIso });
        const res = await fetch(`${url}?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          const fresh = (data.big_wins || []).slice().reverse();  // oldest → newest
          for (const w of fresh) {
            if (w.occurred_at) lastSeenIso = w.occurred_at;
            enqueueWin(w);
          }
        }
      } catch (e) { /* swallow polling errors */ }
    };

    const id = setInterval(tick, 6000);
    return () => {
      stopped = true;
      clearInterval(id);
      Object.values(timersRef.current).forEach(clearTimeout);
      timersRef.current = {};
    };
  }, [enqueueWin]);

  if (wins.length === 0) return null;

  return (
    <div
      className="fixed top-20 right-4 z-[80] flex flex-col gap-3 pointer-events-none"
      data-testid="big-win-toast-stack"
    >
      {wins.map((win) => {
        const gameLabel = win.game === "pot" ? "WINNER POT" : "COIN FLIP";
        return (
          <div
            key={win._toastId}
            data-testid="big-win-toast"
            className="pointer-events-auto relative w-[340px] sm:w-[380px] rounded-2xl overflow-hidden border-2 border-[#F5D300]/60 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] shadow-[0_0_60px_rgba(245,211,0,0.45),0_0_30px_rgba(0,255,163,0.25)] animate-[bigWinEntry_0.8s_cubic-bezier(0.34,1.56,0.64,1)]"
          >
            {/* Animated halo behind the card */}
            <div className="absolute inset-0 pointer-events-none">
              <div className="absolute inset-[-4px] rounded-2xl bg-gradient-to-r from-[#F5D300]/0 via-[#F5D300]/40 to-[#F5D300]/0 animate-[shimmer_2.5s_linear_infinite] opacity-60" />
            </div>

            {/* Confetti sparkle burst — 8 particles flying out from logo */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              {Array.from({ length: 12 }).map((_, i) => (
                <span
                  key={i}
                  className="absolute left-12 top-12 w-1.5 h-1.5 rounded-full animate-[confettiBurst_1.4s_ease-out_forwards]"
                  style={{
                    background: ["#F5D300", "#00FFA3", "#D946EF", "#00D4FF"][i % 4],
                    boxShadow: "0 0 8px currentColor",
                    "--angle": `${i * 30}deg`,
                    "--dist": `${60 + (i % 3) * 25}px`,
                    animationDelay: `${i * 0.04}s`,
                  }}
                />
              ))}
            </div>

            {/* Top accent bar */}
            <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-[#F5D300] via-[#00FFA3] to-[#D946EF]" />

            <button
              type="button"
              onClick={() => dismissWin(win._toastId)}
              className="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/50 border border-white/10 text-white/60 hover:text-white flex items-center justify-center transition-colors"
              aria-label="Dismiss"
            >
              <X size={12} />
            </button>

            <div className="p-4 pt-5">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-[#F5D300]" />
                <span className="text-[9px] uppercase tracking-[0.25em] font-bold text-[#F5D300]">
                  Big Win · {gameLabel}
                </span>
                <span className="ml-auto inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30 mr-7">
                  <span className="w-1 h-1 rounded-full bg-[#00FFA3] animate-pulse" />
                  <span className="text-[8px] uppercase tracking-wider text-[#00FFA3] font-bold">Live</span>
                </span>
              </div>

              <div className="flex items-center gap-3">
                <div className="relative w-12 h-12 shrink-0">
                  <div className="absolute inset-0 bg-gradient-to-br from-[#F5D300] to-[#D946EF] rounded-full blur-md opacity-50 animate-pulse" />
                  <img
                    src={LOGO}
                    alt="Bullpug"
                    className="relative w-full h-full rounded-full ring-2 ring-[#F5D300]/40 object-cover"
                  />
                  <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#F5D300] border-2 border-[#0F1018] flex items-center justify-center">
                    <Trophy className="w-2.5 h-2.5 text-black" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-bold text-white tracking-tight truncate"
                    style={{ fontFamily: "Orbitron, sans-serif" }}
                  >
                    {win.winner_name || "Anonymous"}
                  </p>
                  <p className="text-[10px] text-slate-500 font-mono">
                    {win.winner_wallet_short || "—"}
                  </p>
                </div>
                <div className="text-right">
                  <p
                    className="text-2xl font-black leading-none tracking-tight"
                    style={{ fontFamily: "Orbitron, sans-serif" }}
                  >
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#F5D300] to-[#00FFA3]">
                      {Number(win.payout_sol).toFixed(2)}
                    </span>
                  </p>
                  <p className="text-[9px] uppercase tracking-wider text-slate-400 font-bold flex items-center gap-1 justify-end mt-0.5">
                    <Coins className="w-2.5 h-2.5" />
                    SOL
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 mt-3">
                <button
                  type="button"
                  onClick={() => shareOnX(win)}
                  data-testid="big-win-share-btn"
                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-full bg-black border border-white/15 hover:border-white/40 text-white text-[10px] font-bold uppercase tracking-wider transition-colors"
                >
                  <FaXTwitter className="w-3 h-3" />
                  Share on X
                </button>
                <a
                  href="/betting"
                  data-testid="big-win-cta"
                  className="inline-flex items-center justify-center px-3 py-1.5 rounded-full bg-[#00FFA3] hover:bg-[#00FFA3]/90 text-black text-[10px] font-bold uppercase tracking-wider transition-colors"
                >
                  Play arena →
                </a>
              </div>
            </div>
          </div>
        );
      })}
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(120%); opacity: 0; }
          to   { transform: translateX(0); opacity: 1; }
        }
        @keyframes bigWinEntry {
          0%   { transform: translateX(120%) scale(0.6); opacity: 0; }
          55%  { transform: translateX(-8px) scale(1.06); opacity: 1; }
          75%  { transform: translateX(4px) scale(0.98); }
          100% { transform: translateX(0) scale(1); opacity: 1; }
        }
        @keyframes shimmer {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes confettiBurst {
          0% {
            opacity: 1;
            transform: translate(0, 0) scale(0.5);
          }
          70% { opacity: 1; }
          100% {
            opacity: 0;
            transform:
              translate(
                calc(cos(var(--angle)) * var(--dist)),
                calc(sin(var(--angle)) * var(--dist) - 20px)
              )
              scale(1.2);
          }
        }
      `}</style>
    </div>
  );
}
