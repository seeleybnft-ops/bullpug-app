/**
 * TheRecord — public leaderboard of Archive wallets by unlock count.
 *
 * Fetches from GET /api/archive/record and renders wallets in
 * shortened form (`abcd…wxyz`) with their rank badge, unlock count,
 * and the date they reached their current rank. Top 10 by default,
 * "Load more" appends 10 at a time.
 *
 * Deliberately kept in Tinkerpug's voice ("The Record", "keeper's log —
 * these signals have gone the deepest.") so the leaderboard reads as a
 * ledger, not a scoreboard.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Loader2, PawPrint } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PAGE_SIZE = 10;

const RANK_COLOR = {
  Seeker: "#00FFA3",
  Archivist: "#B47CFF",
  "Keeper's Circle": "#F5D300",
};

function shortenWallet(w) {
  if (!w) return "";
  const s = String(w);
  if (s.length <= 10) return s;
  return `${s.slice(0, 4)}…${s.slice(-4)}`;
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

function RankBadgePill({ rankTitle }) {
  const color = RANK_COLOR[rankTitle] || "rgba(150,160,190,0.9)";
  if (!rankTitle) {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-widest text-slate-500"
        style={{
          fontFamily: "Orbitron, sans-serif",
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        Unranked
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-widest"
      style={{
        fontFamily: "Orbitron, sans-serif",
        background: `${color}18`,
        border: `1px solid ${color}55`,
        color,
      }}
    >
      <span
        className="inline-block rounded-full"
        style={{ width: 5, height: 5, background: color, boxShadow: `0 0 6px ${color}` }}
      />
      {rankTitle}
    </span>
  );
}

export default function TheRecord({ wallet }) {
  const [rows, setRows] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [initialised, setInitialised] = useState(false);

  const load = useCallback(
    async (nextPage, replace = false) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API}/archive/record?page=${nextPage}&limit=${PAGE_SIZE}`);
        if (!res.ok) throw new Error(`record ${res.status}`);
        const data = await res.json();
        setTotal(data.total || 0);
        setHasMore(!!data.has_more);
        setRows((prev) => (replace ? data.entries || [] : [...prev, ...(data.entries || [])]));
      } catch (e) {
        setError("Signal dropped. Try again.");
      } finally {
        setLoading(false);
        setInitialised(true);
      }
    },
    []
  );

  useEffect(() => {
    setRows([]);
    setPage(1);
    load(1, true);
  }, [load]);

  return (
    <div data-testid="the-record" className="space-y-4">
      {/* Tinkerpug header */}
      <div
        className="rounded-xl p-4"
        style={{
          background: "rgba(10,15,30,0.55)",
          border: "1px dashed rgba(0,255,200,0.22)",
        }}
      >
        <p
          className="text-[9px] uppercase tracking-[0.32em] text-cyan-300/80 mb-1"
          style={{ fontFamily: "Orbitron, sans-serif" }}
        >
          The Record
        </p>
        <p className="text-[12px] italic text-slate-300 leading-relaxed" data-testid="the-record-header">
          keeper's log — these signals have gone the deepest.
        </p>
      </div>

      {error && (
        <div
          className="rounded-lg p-3 text-xs text-red-200"
          style={{ background: "rgba(255,0,0,0.06)", border: "1px solid rgba(255,80,80,0.35)" }}
        >
          {error}
        </div>
      )}

      {/* Column header */}
      <div
        className="grid gap-2 px-3 py-2 rounded-lg text-[9px] uppercase tracking-widest text-slate-500"
        style={{
          gridTemplateColumns: "28px minmax(0,1fr) auto auto",
          fontFamily: "Orbitron, sans-serif",
          background: "rgba(5,7,18,0.55)",
        }}
      >
        <span>#</span>
        <span>Signal</span>
        <span className="text-right">Depth</span>
        <span className="text-right">Filed</span>
      </div>

      {!initialised ? (
        <p className="text-center text-[11px] tracking-widest text-slate-600 py-6">
          reading the ledger…
        </p>
      ) : rows.length === 0 ? (
        <div
          className="rounded-xl p-6 text-center"
          style={{ background: "rgba(10,15,30,0.55)", border: "1px dashed rgba(0,255,163,0.25)" }}
          data-testid="the-record-empty"
        >
          <p className="text-sm text-white/80 font-bold mb-1" style={{ fontFamily: "Orbitron, sans-serif" }}>
            No signals filed yet
          </p>
          <p className="text-xs text-slate-400">
            Be the first to unlock a lore entry — the Ledger tracks who goes deepest.
          </p>
        </div>
      ) : (
        <ul className="space-y-1.5" data-testid="the-record-list">
          {rows.map((row) => {
            const isSelf = wallet && row.wallet === wallet;
            const color = RANK_COLOR[row.rank_title] || "rgba(255,255,255,0.35)";
            return (
              <li
                key={`${row.wallet}-${row.position}`}
                className="grid gap-2 items-center px-3 py-2.5 rounded-lg transition-colors"
                style={{
                  gridTemplateColumns: "28px minmax(0,1fr) auto auto",
                  background: isSelf ? `${color}12` : "rgba(10,15,30,0.55)",
                  border: `1px solid ${isSelf ? `${color}55` : "rgba(255,255,255,0.05)"}`,
                }}
                data-testid={`the-record-row-${row.position}`}
              >
                <span
                  className="text-[11px] font-bold text-slate-400"
                  style={{ fontFamily: "monospace" }}
                >
                  {row.position}
                </span>
                <div className="min-w-0 flex flex-col gap-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="text-[13px] font-bold truncate"
                      style={{
                        fontFamily: "monospace",
                        color: isSelf ? color : "rgba(255,255,255,0.92)",
                      }}
                      title={row.wallet}
                    >
                      {shortenWallet(row.wallet)}
                    </span>
                    {isSelf && (
                      <span
                        className="text-[8px] uppercase tracking-widest px-1.5 py-0.5 rounded-full"
                        style={{
                          fontFamily: "Orbitron, sans-serif",
                          color,
                          background: `${color}22`,
                          border: `1px solid ${color}66`,
                        }}
                      >
                        you
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <RankBadgePill rankTitle={row.rank_title} />
                  </div>
                </div>
                <div
                  className="text-right text-[13px] font-bold whitespace-nowrap"
                  style={{ fontFamily: "monospace", color: isSelf ? color : "rgba(255,255,255,0.92)" }}
                  data-testid={`the-record-count-${row.position}`}
                >
                  {row.unlocked_count}
                </div>
                <div
                  className="text-right text-[10px] whitespace-nowrap text-slate-500"
                  style={{ fontFamily: "monospace" }}
                >
                  {fmtDate(row.rank_reached_at)}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {hasMore && !loading && rows.length > 0 && (
        <div className="text-center pt-2">
          <button
            type="button"
            data-testid="the-record-load-more"
            onClick={() => {
              const next = page + 1;
              setPage(next);
              load(next, false);
            }}
            className="inline-flex items-center gap-2 text-[10px] uppercase tracking-widest px-4 py-2 rounded-full border border-white/10 hover:border-white/25 text-slate-300 hover:text-white transition-colors"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Load more · {total - rows.length} left
          </button>
        </div>
      )}
      {loading && rows.length > 0 && (
        <p className="text-center text-[10px] tracking-widest text-slate-600 pt-1">
          <Loader2 className="inline animate-spin mr-1" size={11} /> reading deeper…
        </p>
      )}

      {/* Ambient paw footer — keeps the Tinkerpug voice */}
      <p
        className="text-center text-[10px] italic text-slate-600 pt-4 flex items-center justify-center gap-1.5"
        style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
      >
        <PawPrint size={10} className="text-slate-600" strokeWidth={2} />
        signals are filed in the order they went deepest
      </p>
    </div>
  );
}
