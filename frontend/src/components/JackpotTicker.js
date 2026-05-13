import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Trophy, Coins, Clock, Flame } from "lucide-react";
import axios from "axios";
import TipPotModal from "@/components/TipPotModal";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function formatCountdown(secs) {
  if (secs == null || secs < 0) return "—";
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  return `${m}m ${String(s).padStart(2, "0")}s`;
}

function CountUp({ value, decimals = 4 }) {
  const [displayValue, setDisplayValue] = useState(value);
  const prevValueRef = useRef(value);

  useEffect(() => {
    const start = prevValueRef.current;
    const end = value;
    if (start === end) return;
    const duration = 800;
    const startTs = performance.now();

    let raf;
    const step = (now) => {
      const elapsed = now - startTs;
      const t = Math.min(1, elapsed / duration);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - t, 3);
      const current = start + (end - start) * eased;
      setDisplayValue(current);
      if (t < 1) raf = requestAnimationFrame(step);
      else prevValueRef.current = end;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return <>{Number(displayValue).toFixed(decimals)}</>;
}

export default function JackpotTicker() {
  const [pool, setPool] = useState(null);
  const [error, setError] = useState(false);
  const [tick, setTick] = useState(0);
  const [tipOpen, setTipOpen] = useState(false);

  useEffect(() => {
    let mounted = true;

    const fetchPool = async () => {
      try {
        const { data } = await axios.get(`${API}/prize-pool/status`);
        if (mounted) {
          setPool(data);
          setError(false);
        }
      } catch (e) {
        if (mounted) setError(true);
      }
    };

    fetchPool();
    const refresh = setInterval(fetchPool, 15000);
    const ticker = setInterval(() => setTick((t) => t + 1), 1000);
    return () => {
      mounted = false;
      clearInterval(refresh);
      clearInterval(ticker);
    };
  }, []);

  // Live-decrement the visible countdown each second
  const liveSeconds = pool
    ? Math.max(0, (pool.seconds_remaining || 0) - tick)
    : null;

  const total = pool?.total_sol ?? 0;
  const top1 = pool?.prize_breakdown?.find((p) => p.rank === 1)?.amount_sol ?? 0;

  if (error) return null;

  return (
    <>
    <section className="py-12 md:py-16" data-testid="jackpot-ticker-section">
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div
          className="relative overflow-hidden rounded-3xl border border-[#F5D300]/30 p-8 md:p-12"
          style={{
            background:
              "radial-gradient(ellipse at top left, rgba(245,211,0,0.10) 0%, rgba(0,255,163,0.05) 35%, transparent 70%), linear-gradient(135deg, #07070d 0%, #0c0c14 100%)",
          }}
          data-testid="jackpot-ticker"
        >
          {/* Subtle animated grain */}
          <div
            className="absolute inset-0 opacity-[0.04] pointer-events-none mix-blend-overlay"
            style={{
              backgroundImage:
                "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.4'/%3E%3C/svg%3E\")",
            }}
          />

          <div className="relative grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-10 items-center">
            {/* Left: title + live total */}
            <div className="lg:col-span-7">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-9 h-9 rounded-full bg-[#F5D300]/15 border border-[#F5D300]/40 flex items-center justify-center">
                  <Trophy className="w-4 h-4 text-[#F5D300]" />
                </div>
                <span
                  className="text-[11px] font-bold tracking-[0.25em] uppercase text-[#F5D300]"
                  style={{ fontFamily: "Space Grotesk, sans-serif" }}
                >
                  Cosmic Runner Jackpot
                </span>
                <span className="ml-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00FFA3] animate-pulse" />
                  <span className="text-[9px] uppercase tracking-wider text-[#00FFA3] font-bold">Live</span>
                </span>
              </div>

              <h2
                className="text-5xl md:text-6xl lg:text-7xl font-black tracking-tighter leading-none"
                style={{ fontFamily: "Orbitron, sans-serif" }}
              >
                <span
                  className="bg-clip-text text-transparent"
                  style={{
                    backgroundImage:
                      "linear-gradient(135deg, #F5D300 0%, #FFB800 35%, #00FFA3 100%)",
                  }}
                  data-testid="jackpot-total"
                >
                  <CountUp value={total} decimals={4} />
                </span>
                <span className="text-2xl md:text-3xl ml-3 align-baseline text-slate-400 font-bold">
                  SOL
                </span>
              </h2>

              <p
                className="text-slate-400 text-sm mt-4 max-w-xl leading-relaxed"
                style={{ fontFamily: "Space Grotesk, sans-serif" }}
              >
                Every coin flip and pot round in the P2P Arena tops up this jackpot.
                The top 10 Cosmic Runner scorers split the prize pool every 3 days —
                the #1 runner takes <span className="text-[#F5D300] font-bold">25%</span>.
              </p>

              <div className="flex flex-wrap items-center gap-3 mt-6">
                <Link to="/game" data-testid="jackpot-cta-game">
                  <button className="group inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[#00FFA3] text-black font-bold text-xs uppercase tracking-wider hover:scale-[1.03] transition-transform shadow-[0_0_24px_rgba(0,255,163,0.35)]">
                    <Flame className="w-4 h-4" />
                    Run for the jackpot
                  </button>
                </Link>
                <Link to="/betting" data-testid="jackpot-cta-arena">
                  <button className="group inline-flex items-center gap-2 px-5 py-3 rounded-full bg-transparent border border-white/20 text-slate-200 font-bold text-xs uppercase tracking-wider hover:border-white/40 hover:bg-white/5 transition-colors">
                    <Trophy className="w-4 h-4" />
                    P2P Arena
                  </button>
                </Link>
                <button
                  type="button"
                  onClick={() => setTipOpen(true)}
                  data-testid="jackpot-cta-tip"
                  className="group inline-flex items-center gap-2 px-5 py-3 rounded-full bg-transparent border border-[#F5D300]/40 text-[#F5D300] font-bold text-xs uppercase tracking-wider hover:border-[#F5D300] hover:bg-[#F5D300]/10 transition-colors"
                >
                  <Coins className="w-4 h-4" />
                  Tip the pot
                </button>
              </div>
            </div>

            {/* Right: stat cards */}
            <div className="lg:col-span-5 grid grid-cols-2 gap-3">
              <div
                className="rounded-2xl border border-white/10 bg-black/40 backdrop-blur-md p-5"
                data-testid="jackpot-top1-card"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Trophy className="w-3.5 h-3.5 text-[#F5D300]" />
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">
                    #1 Prize
                  </span>
                </div>
                <p
                  className="text-3xl font-black text-[#F5D300] leading-none"
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  <CountUp value={top1} decimals={4} />
                </p>
                <p className="text-[10px] text-slate-500 mt-1.5">SOL · 25% share</p>
              </div>

              <div
                className="rounded-2xl border border-white/10 bg-black/40 backdrop-blur-md p-5"
                data-testid="jackpot-payout-card"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-3.5 h-3.5 text-[#00C2FF]" />
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">
                    Next Payout
                  </span>
                </div>
                <p
                  className="text-2xl font-black text-[#00C2FF] leading-none tabular-nums"
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                  data-testid="jackpot-countdown"
                >
                  {formatCountdown(liveSeconds)}
                </p>
                <p className="text-[10px] text-slate-500 mt-1.5">
                  Top 10 runners share
                </p>
              </div>

              <div
                className="rounded-2xl border border-white/10 bg-black/40 backdrop-blur-md p-5 col-span-2"
                data-testid="jackpot-source-card"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">
                      Funding Source
                    </span>
                    <p className="text-xs text-slate-300 mt-1.5 leading-snug">
                      <span className="text-[#F5D300] font-bold">25%</span> of every
                      P2P Arena rake auto-streams here in real time.
                    </p>
                  </div>
                  <div className="hidden sm:flex flex-col items-end text-right">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">
                      Cycle
                    </span>
                    <p className="text-xs text-slate-300 mt-1.5">
                      {pool?.payout_interval_days ?? 3}-day cycle
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
    <TipPotModal
      open={tipOpen}
      onClose={() => setTipOpen(false)}
      onTipped={({ newTotal }) => {
        if (newTotal != null) {
          setPool((p) => (p ? { ...p, total_sol: newTotal } : p));
        }
      }}
    />
    </>
  );
}
