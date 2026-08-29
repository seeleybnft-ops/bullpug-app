/**
 * DailyDropVault — the paginated grid of daily-drop cards.
 *
 * Layout: uniform grid (3 cols desktop / 2 tablet / 1 mobile).
 * Pagination: 12 per page, infinite scroll via a sentinel div at the
 * bottom that fires when it hits the viewport.
 *
 * Empty state (spec §9.3): a single placeholder card.
 * Wallet-less state: a prompt to connect, since the vault is per-wallet.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import DropCard from "./DropCard";
import DropModal from "./DropModal";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PAGE_SIZE = 12;

export default function DailyDropVault({ wallet }) {
  const [drops, setDrops] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initialised, setInitialised] = useState(false);
  const [selected, setSelected] = useState(null);
  const sentinelRef = useRef(null);

  // Fetch a page. Returns nothing — mutates state.
  const fetchPage = useCallback(
    async (nextPage, replace = false) => {
      if (!wallet) return;
      setLoading(true);
      try {
        const url = `${API}/archive/drops?wallet=${encodeURIComponent(wallet)}&page=${nextPage}&limit=${PAGE_SIZE}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`archive drops ${res.status}`);
        const data = await res.json();
        setTotal(data.total || 0);
        setHasMore(!!data.has_more);
        setDrops((prev) => (replace ? data.drops || [] : [...prev, ...(data.drops || [])]));
      } catch (e) {
        // Silent failure — vault falls back to whatever's already in state
      } finally {
        setLoading(false);
        setInitialised(true);
      }
    },
    [wallet]
  );

  // Reset on wallet change
  useEffect(() => {
    setDrops([]);
    setPage(1);
    setTotal(0);
    setHasMore(false);
    setInitialised(false);
    if (wallet) fetchPage(1, true);
  }, [wallet, fetchPage]);

  // Infinite-scroll sentinel
  useEffect(() => {
    if (!sentinelRef.current || !hasMore || loading) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          const next = page + 1;
          setPage(next);
          fetchPage(next);
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasMore, loading, page, fetchPage]);

  // ── Empty / wallet-less states ──────────────────────────────────────
  if (!wallet) {
    return (
      <div
        className="rounded-xl p-6 text-center"
        style={{ background: "rgba(10,15,30,0.55)", border: "1px dashed rgba(0,255,163,0.25)" }}
        data-testid="drop-vault-connect-prompt"
      >
        <p className="text-xs text-slate-400 leading-relaxed">
          Connect your wallet to open the vault. Each Bullpughan gets their own daily
          drop, filed here permanently.
        </p>
      </div>
    );
  }

  if (initialised && drops.length === 0) {
    return (
      <div
        className="rounded-xl p-6 text-center"
        style={{ background: "rgba(10,15,30,0.55)", border: "1px dashed rgba(0,255,163,0.25)" }}
        data-testid="drop-vault-empty"
      >
        <p className="text-sm text-white/80 font-bold mb-1" style={{ fontFamily: "Orbitron, sans-serif" }}>
          The vault is empty
        </p>
        <p className="text-xs text-slate-400 mb-2">Your first drop arrives tomorrow.</p>
        <p className="text-[11px] italic text-slate-500">keeper's note: worth the wait.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-[0.25em] text-slate-500" style={{ fontFamily: "Orbitron, sans-serif" }}>
          Daily Drops
        </p>
        <p className="text-[10px] text-slate-500" style={{ fontFamily: "monospace" }}>
          {total ? `${drops.length} of ${total}` : ""}
        </p>
      </div>

      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))" }}
        data-testid="drop-vault-grid"
      >
        {drops.map((d) => (
          <DropCard
            key={`${d.date_utc}-${d.day_number}`}
            drop={d}
            onClick={() => setSelected(d)}
          />
        ))}
      </div>

      {hasMore && (
        <div
          ref={sentinelRef}
          className="h-12 flex items-center justify-center text-[10px] tracking-[0.25em] text-slate-600"
          data-testid="drop-vault-load-more"
        >
          {loading ? "loading…" : ""}
        </div>
      )}

      {selected && <DropModal drop={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
