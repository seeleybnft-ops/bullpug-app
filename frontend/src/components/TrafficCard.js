/**
 * TrafficCard — SIWS-gated traffic analytics for the admin panel.
 *
 * Polls `/api/analytics/summary` every 60s and shows:
 *   • Visits + uniques across 24h / 7d / 30d
 *   • Top pages and top referrers (last 7d)
 *   • A 14-day daily-visits sparkline
 *
 * Uses the same `useSiwsAdmin` hook + axios `authFetch` pattern as the
 * other admin cards so it slots in cleanly under "Client Crashes".
 */

import { useEffect, useRef, useState } from "react";
import { TrendingUp, RefreshCw, Users, Eye, Globe2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const REFRESH_INTERVAL_MS = 60_000;

function fmt(n) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

// Build an SVG path string from the daily-views series. Coordinates are
// normalised into a 100×30 viewBox so the rendered size is purely a CSS
// concern.
function buildSparklinePath(series) {
  if (!series || series.length === 0) return { line: "", area: "" };
  const max = Math.max(1, ...series.map((p) => p.views));
  const stepX = 100 / Math.max(1, series.length - 1);
  const pts = series.map((p, i) => {
    const x = i * stepX;
    const y = 30 - (p.views / max) * 28 - 1; // 1px padding top/bottom
    return [x, y];
  });
  const line = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L100,30 L0,30 Z`;
  return { line, area };
}

export default function TrafficCard() {
  const { authFetch, isAdmin } = useSiwsAdmin();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!isAdmin || !authFetch) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    // authFetch is axios — responses are `{status, data, ...}` and 4xx/5xx
    // reject. Same gotcha as RakeJackpotCard / ClientErrorsCard.
    authFetch(`${API}/analytics/summary`)
      .then((r) => {
        if (!cancelled) setData(r.data);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, isAdmin, tick]);

  useEffect(() => {
    if (!isAdmin) return;
    timerRef.current = setInterval(() => setTick((v) => v + 1), REFRESH_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [isAdmin]);

  if (!isAdmin) return null;

  const w = data?.windows || {};
  const sparkline = data?.sparkline || [];
  const { line, area } = buildSparklinePath(sparkline);
  const sparkTotal = sparkline.reduce((acc, p) => acc + (p.views || 0), 0);
  const directViews = data?.direct_7d ?? 0;
  // Prefer the new `top_sources` field (UTM-aware); fall back to the old
  // `top_referers` shape for backwards compatibility during deploys.
  const topSources = data?.top_sources || data?.top_referers || [];

  const windows = [
    { key: "h24", label: "24h", views: w.h24?.views, uniques: w.h24?.uniques, accent: "#00FFA3" },
    { key: "d7",  label: "7d",  views: w.d7?.views,  uniques: w.d7?.uniques,  accent: "#00C2FF" },
    { key: "d30", label: "30d", views: w.d30?.views, uniques: w.d30?.uniques, accent: "#D946EF" },
  ];

  return (
    <div className="glass-card rounded-2xl p-6" data-testid="traffic-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-[#00FFA3]" />
          <h2
            className="text-sm font-black uppercase tracking-wider text-white"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Traffic
          </h2>
          <Badge className="bg-white/5 text-slate-400 border-white/10 text-[10px]">
            anonymous · self-hosted
          </Badge>
        </div>
        <button
          onClick={() => setTick((v) => v + 1)}
          disabled={loading}
          className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors disabled:opacity-50"
          data-testid="traffic-refresh"
          title="Refresh now"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && (
        <div className="p-3 mb-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300">
          Failed to load: {error}
        </div>
      )}

      {/* Window totals */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {windows.map((win) => (
          <div
            key={win.key}
            className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2"
            data-testid={`traffic-window-${win.key}`}
          >
            <div
              className="text-[9px] font-bold uppercase tracking-[0.18em] mb-1"
              style={{ color: win.accent }}
            >
              {win.label}
            </div>
            <div className="flex items-baseline justify-between gap-2">
              <div className="flex items-center gap-1 text-slate-400 text-[10px]">
                <Eye className="w-3 h-3" />
                <span>views</span>
              </div>
              <div
                className="text-lg font-black text-white tabular-nums"
                style={{ fontFamily: "Orbitron, sans-serif" }}
              >
                {fmt(win.views)}
              </div>
            </div>
            <div className="flex items-baseline justify-between gap-2 mt-0.5">
              <div className="flex items-center gap-1 text-slate-500 text-[10px]">
                <Users className="w-3 h-3" />
                <span>uniques</span>
              </div>
              <div className="text-sm font-bold text-slate-300 tabular-nums">
                {fmt(win.uniques)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Sparkline */}
      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3 mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">
            Last 14 days
          </span>
          <span className="text-[10px] text-slate-400 tabular-nums">
            {fmt(sparkTotal)} views
          </span>
        </div>
        {sparkline.length > 0 ? (
          <svg
            viewBox="0 0 100 30"
            preserveAspectRatio="none"
            className="w-full h-12"
            data-testid="traffic-sparkline"
          >
            <defs>
              <linearGradient id="spark-fill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#00FFA3" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#00FFA3" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d={area} fill="url(#spark-fill)" />
            <path d={line} fill="none" stroke="#00FFA3" strokeWidth="1.2" strokeLinejoin="round" strokeLinecap="round" />
          </svg>
        ) : (
          <p className="text-[11px] text-slate-500">No traffic recorded yet.</p>
        )}
      </div>

      {/* Top pages + referers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-2">
            Top pages · 7d
          </p>
          <ul className="space-y-1.5" data-testid="traffic-top-pages">
            {(data?.top_pages || []).length === 0 ? (
              <li className="text-[11px] text-slate-500">No data yet.</li>
            ) : (
              (data?.top_pages || []).map((p) => (
                <li
                  key={p.key}
                  className="flex items-center justify-between gap-2 text-[11px]"
                >
                  <span className="text-slate-200 truncate" title={p.key}>
                    {p.key}
                  </span>
                  <span className="text-slate-400 tabular-nums">{fmt(p.count)}</span>
                </li>
              ))
            )}
          </ul>
        </div>
        <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-2 flex items-center gap-1">
            <Globe2 className="w-3 h-3" />
            Top sources · 7d
          </p>
          <ul className="space-y-1.5" data-testid="traffic-top-referers">
            {topSources.length === 0 ? (
              <li className="text-[11px] text-slate-500">
                Mostly direct traffic so far.
              </li>
            ) : (
              topSources.map((r) => (
                <li
                  key={r.key}
                  className="flex items-center justify-between gap-2 text-[11px]"
                >
                  <span className="text-slate-200 truncate" title={r.key}>
                    {r.key}
                  </span>
                  <span className="text-slate-400 tabular-nums">{fmt(r.count)}</span>
                </li>
              ))
            )}
            {directViews > 0 && (
              <li
                className="flex items-center justify-between gap-2 text-[11px] pt-1.5 mt-1.5 border-t border-white/5"
                title="Visits with no Referer and no UTM tag — typed URL, app/Twitter mobile, or stripped by privacy settings"
              >
                <span className="text-slate-500 italic">direct / unknown</span>
                <span className="text-slate-500 tabular-nums">{fmt(directViews)}</span>
              </li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
