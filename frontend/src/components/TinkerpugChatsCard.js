/**
 * TinkerpugChatsCard — SIWS-gated review feed for Tinkerpug interactions.
 *
 * Polls `/api/ai/tinkerpug-chats` every 60s and renders the most recent
 * 100 turns within the last 7 days. Each row shows:
 *   • Relative "X ago" timestamp
 *   • Session id (truncated) + optional wallet
 *   • The user message (what they asked)
 *   • Tinkerpug's response (what he said back)
 *   • Tags: kind (text/image), has_live_data flag
 *
 * Long messages are clamped to ~2 lines with an expand toggle so the card
 * stays scannable but full transcripts are one click away.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import {
  MessageCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  User,
  Sparkles,
  Image as ImageIcon,
  Wifi,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const REFRESH_INTERVAL_MS = 60_000;

function relTime(iso) {
  if (!iso) return "—";
  try {
    const diff = Math.max(0, Date.now() - new Date(iso).getTime());
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

function shortWallet(w) {
  if (!w) return null;
  if (w.length <= 10) return w;
  return `${w.slice(0, 4)}…${w.slice(-4)}`;
}

function shortSession(s) {
  if (!s) return "anon";
  if (s === "anon") return "anon";
  return s.length <= 10 ? s : `${s.slice(0, 8)}…`;
}

export default function TinkerpugChatsCard() {
  const { authFetch, isAdmin } = useSiwsAdmin();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  const [expanded, setExpanded] = useState({});
  const [groupBy, setGroupBy] = useState("flat"); // "flat" | "session"
  const timerRef = useRef(null);

  useEffect(() => {
    if (!isAdmin || !authFetch) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    authFetch(`${API}/ai/tinkerpug-chats?limit=100&hours=168`)
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
    timerRef.current = setInterval(
      () => setTick((v) => v + 1),
      REFRESH_INTERVAL_MS
    );
    return () => clearInterval(timerRef.current);
  }, [isAdmin]);

  const items = data?.items || [];

  // Build session-grouped view when requested. Each session keeps its
  // turns in chronological order so the transcript reads top-to-bottom.
  const sessions = useMemo(() => {
    if (groupBy !== "session") return [];
    const map = new Map();
    [...items].reverse().forEach((row) => {
      const sid = row.session_id || "anon";
      if (!map.has(sid)) map.set(sid, { session_id: sid, turns: [], last_ts: row.ts, wallet: row.wallet });
      const bucket = map.get(sid);
      bucket.turns.push(row);
      // Last_ts should be the LATEST row (we're walking in reverse, so
      // the last assignment wins).
      bucket.last_ts = row.ts;
      if (row.wallet) bucket.wallet = row.wallet;
    });
    // Sort sessions by recency
    return Array.from(map.values()).sort(
      (a, b) => new Date(b.last_ts).getTime() - new Date(a.last_ts).getTime()
    );
  }, [items, groupBy]);

  if (!isAdmin) return null;

  return (
    <div className="glass-card rounded-2xl p-6" data-testid="tinkerpug-chats-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-[#D946EF]" />
          <h2
            className="text-sm font-black uppercase tracking-wider text-white"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Tinkerpug Chats
          </h2>
          <Badge className="bg-white/5 text-slate-400 border-white/10 text-[10px]">
            7d · top 100 turns
          </Badge>
          {data?.unique_sessions != null && (
            <Badge className="bg-white/5 text-slate-400 border-white/10 text-[10px]">
              {data.unique_sessions} sessions · {data.total_in_window} turns
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Grouping toggle */}
          <div className="flex rounded-lg border border-white/10 overflow-hidden">
            <button
              type="button"
              onClick={() => setGroupBy("flat")}
              className={`text-[10px] uppercase tracking-wider px-2 py-1 transition-colors ${
                groupBy === "flat"
                  ? "bg-white/10 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
              data-testid="tinkerpug-view-flat"
            >
              Flat
            </button>
            <button
              type="button"
              onClick={() => setGroupBy("session")}
              className={`text-[10px] uppercase tracking-wider px-2 py-1 border-l border-white/10 transition-colors ${
                groupBy === "session"
                  ? "bg-white/10 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
              data-testid="tinkerpug-view-sessions"
            >
              Sessions
            </button>
          </div>
          <button
            onClick={() => setTick((v) => v + 1)}
            disabled={loading}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors disabled:opacity-50"
            data-testid="tinkerpug-refresh"
            title="Refresh now"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 mb-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300">
          Failed to load: {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="p-6 text-center">
          <p className="text-xs text-slate-500">
            No Tinkerpug conversations in the last 7 days yet.
          </p>
        </div>
      )}

      {/* FLAT view — chronological feed */}
      {groupBy === "flat" && (
        <ul className="space-y-2 max-h-[520px] overflow-y-auto pr-1" data-testid="tinkerpug-flat-list">
          {items.map((row, idx) => {
            const key = `${row.session_id}-${row.ts}-${idx}`;
            const isExpanded = !!expanded[key];
            return (
              <li
                key={key}
                className="rounded-lg border border-white/5 bg-white/[0.02] p-3 hover:bg-white/[0.04] transition-colors"
              >
                {/* Meta row */}
                <div className="flex items-center justify-between gap-2 mb-2 text-[10px]">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-slate-500 font-mono truncate">
                      {shortSession(row.session_id)}
                    </span>
                    {row.wallet && (
                      <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] border-[#00FFA3]/30 text-[9px] font-mono">
                        {shortWallet(row.wallet)}
                      </Badge>
                    )}
                    {row.kind === "image" && (
                      <Badge className="bg-[#D946EF]/10 text-[#D946EF] border-[#D946EF]/30 text-[9px] flex items-center gap-0.5">
                        <ImageIcon className="w-2.5 h-2.5" /> image
                      </Badge>
                    )}
                    {row.has_live_data && (
                      <Badge className="bg-[#00C2FF]/10 text-[#00C2FF] border-[#00C2FF]/30 text-[9px] flex items-center gap-0.5">
                        <Wifi className="w-2.5 h-2.5" /> live
                      </Badge>
                    )}
                  </div>
                  <span className="text-slate-500 flex-shrink-0">
                    {relTime(row.ts)}
                  </span>
                </div>

                {/* User message */}
                <div className="flex gap-2 mb-1.5">
                  <User className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                  <p
                    className={`text-xs text-slate-200 whitespace-pre-wrap break-words ${
                      isExpanded ? "" : "line-clamp-2"
                    }`}
                  >
                    {row.user_message || "(empty message)"}
                  </p>
                </div>

                {/* Assistant message */}
                <div className="flex gap-2">
                  <Sparkles className="w-3.5 h-3.5 text-[#F5D300] flex-shrink-0 mt-0.5" />
                  <p
                    className={`text-xs text-slate-300 whitespace-pre-wrap break-words ${
                      isExpanded ? "" : "line-clamp-3"
                    }`}
                  >
                    {row.assistant_message || "(no response)"}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))
                  }
                  className="mt-2 flex items-center gap-1 text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
                  data-testid={`tinkerpug-expand-${idx}`}
                >
                  {isExpanded ? (
                    <>
                      <ChevronUp className="w-3 h-3" />
                      Collapse
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-3 h-3" />
                      Show full
                    </>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {/* SESSION view — grouped transcripts */}
      {groupBy === "session" && (
        <ul className="space-y-2 max-h-[520px] overflow-y-auto pr-1" data-testid="tinkerpug-session-list">
          {sessions.map((s) => {
            const open = !!expanded[`s-${s.session_id}`];
            return (
              <li
                key={s.session_id}
                className="rounded-lg border border-white/5 bg-white/[0.02]"
              >
                <button
                  type="button"
                  onClick={() =>
                    setExpanded((prev) => ({
                      ...prev,
                      [`s-${s.session_id}`]: !prev[`s-${s.session_id}`],
                    }))
                  }
                  className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-sm font-mono text-slate-300 truncate">
                      {shortSession(s.session_id)}
                    </span>
                    {s.wallet && (
                      <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] border-[#00FFA3]/30 text-[9px] font-mono">
                        {shortWallet(s.wallet)}
                      </Badge>
                    )}
                    <Badge className="bg-white/5 text-slate-400 border-white/10 text-[10px]">
                      {s.turns.length} turns
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-[10px] text-slate-500">
                      {relTime(s.last_ts)}
                    </span>
                    {open ? (
                      <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                    )}
                  </div>
                </button>
                {open && (
                  <ol className="px-3 pb-3 pt-1 border-t border-white/5 space-y-3">
                    {s.turns.map((row, i) => (
                      <li key={`${s.session_id}-${i}`} className="space-y-1">
                        <div className="flex gap-2">
                          <User className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                          <p className="text-xs text-slate-200 whitespace-pre-wrap break-words">
                            {row.user_message || "(empty)"}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Sparkles className="w-3.5 h-3.5 text-[#F5D300] flex-shrink-0 mt-0.5" />
                          <p className="text-xs text-slate-300 whitespace-pre-wrap break-words">
                            {row.assistant_message || "(no response)"}
                          </p>
                        </div>
                        <p className="text-[9px] text-slate-600 pl-5">
                          {relTime(row.ts)}
                          {row.kind === "image" && " · image"}
                          {row.has_live_data && " · live data"}
                        </p>
                      </li>
                    ))}
                  </ol>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
