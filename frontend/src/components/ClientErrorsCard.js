/**
 * ClientErrorsCard — SIWS-gated launch-day ops dashboard for client crashes.
 *
 * Polls `/api/client-errors/grouped` every 60s and renders the top 25
 * crash groups in the last 24 hours, sorted by count. Each group shows:
 *   • Crash count (bolded — fires bubble to the top)
 *   • Error kind chip (react-render / window-error / unhandled-rejection)
 *   • Message + last-seen relative time
 *   • Distinct build_ids that hit it + first URL where it landed
 *   • Expand to see the sample stack
 *
 * Uses the same `useSiwsAdmin` hook + `authFetch` pattern as
 * RakeJackpotCard so the auth/refresh story is already battle-tested.
 */

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const REFRESH_INTERVAL_MS = 60_000;

// Relative-time helper: "12s ago", "4m ago", "3h ago", "2d ago".
function relTime(iso) {
  if (!iso) return "—";
  try {
    const then = new Date(iso).getTime();
    const diff = Math.max(0, Date.now() - then);
    const s = Math.floor(diff / 1000);
    if (s < 60) return `${s}s ago`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
  } catch {
    return "—";
  }
}

// Color the kind chip by severity. react-render is the loudest because
// it means the user actually saw the fallback UI.
function kindBadgeClass(kind) {
  if (kind === "react-render") return "bg-red-500/15 text-red-300 border-red-500/40";
  if (kind === "unhandled-rejection") return "bg-amber-500/15 text-amber-300 border-amber-500/40";
  return "bg-slate-500/15 text-slate-300 border-slate-500/40";
}

export default function ClientErrorsCard() {
  const { authFetch, isAdmin } = useSiwsAdmin();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  const [expanded, setExpanded] = useState({});
  const timerRef = useRef(null);

  useEffect(() => {
    if (!isAdmin || !authFetch) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    authFetch(`${API}/client-errors/grouped?limit=25&hours=24`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((j) => {
        if (!cancelled) setData(j);
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

  const items = data?.items || [];

  return (
    <div className="glass-card rounded-2xl p-6" data-testid="client-errors-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <h2
            className="text-sm font-black uppercase tracking-wider text-white"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Client Crashes
          </h2>
          <Badge className="bg-white/5 text-slate-400 border-white/10 text-[10px]">
            last 24h · top 25
          </Badge>
        </div>
        <button
          onClick={() => setTick((v) => v + 1)}
          disabled={loading}
          className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors disabled:opacity-50"
          data-testid="client-errors-refresh"
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

      {!loading && !error && items.length === 0 && (
        <div className="p-6 text-center">
          <p className="text-xs text-slate-500">No client errors in the last 24h. Pack is healthy. 🦴</p>
        </div>
      )}

      {/* Group list — sorted server-side by count desc */}
      <div className="space-y-2">
        {items.map((g) => (
          <div
            key={g.fingerprint}
            className="rounded-lg border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
            data-testid={`error-group-${g.fingerprint.slice(0, 30)}`}
          >
            <button
              type="button"
              onClick={() =>
                setExpanded((prev) => ({ ...prev, [g.fingerprint]: !prev[g.fingerprint] }))
              }
              className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left"
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span
                  className="text-base font-black text-red-400 tabular-nums w-8 text-right"
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  {g.count}
                </span>
                <Badge className={`text-[9px] border ${kindBadgeClass(g.kind)}`}>{g.kind}</Badge>
                <p className="text-xs text-slate-200 truncate flex-1">{g.message || "(no message)"}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-[10px] text-slate-500">{relTime(g.last_seen)}</span>
                {expanded[g.fingerprint] ? (
                  <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                )}
              </div>
            </button>

            {expanded[g.fingerprint] && (
              <div className="px-3 pb-3 pt-1 border-t border-white/5 space-y-2">
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div>
                    <p className="text-slate-500 uppercase tracking-wider mb-0.5">First seen</p>
                    <p className="text-slate-300">{relTime(g.first_seen)}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 uppercase tracking-wider mb-0.5">Builds</p>
                    <p className="text-slate-300 font-mono truncate" title={g.build_ids.join(", ")}>
                      {g.build_ids.length ? g.build_ids.join(", ") : "—"}
                    </p>
                  </div>
                </div>
                {g.urls?.length > 0 && (
                  <div className="text-[10px]">
                    <p className="text-slate-500 uppercase tracking-wider mb-0.5">URLs</p>
                    <ul className="text-slate-400 space-y-0.5">
                      {g.urls.map((u, i) => (
                        <li key={i} className="truncate" title={u}>
                          {u}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {g.sample_stack && (
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Sample stack</p>
                    <pre className="text-[10px] text-slate-400 bg-black/40 rounded p-2 max-h-32 overflow-auto whitespace-pre-wrap break-all">
                      {g.sample_stack}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
