/**
 * ArchiveLedger — the right panel of the Archive tab.
 *
 * Structure (top → bottom):
 *   1. Rank badge + title + progress bar   (always visible)
 *   2. Section switcher: Ledger / Daily Drops
 *   3. Section body
 *
 * On mobile the Archive page renders this same component in the second
 * tab, so it must stand on its own without the left workspace context.
 */
import React, { useEffect, useMemo, useState } from "react";
import LoreCard from "./LoreCard";
import LoreCardModal from "./LoreCardModal";
import RankBadge from "./RankBadge";
import DailyDropVault from "./DailyDropVault";
import ShareableCard from "./ShareableCard";
import { Share2, BookOpen, Sparkles } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function ProgressBar({ percent, color }) {
  return (
    <div
      className="relative w-full h-1.5 rounded-full overflow-hidden"
      style={{ background: "rgba(255,255,255,0.06)" }}
    >
      <div
        className="absolute inset-y-0 left-0 rounded-full transition-[width] duration-500"
        style={{
          width: `${Math.min(100, Math.max(0, percent))}%`,
          background: color,
          boxShadow: `0 0 8px ${color}88`,
        }}
      />
    </div>
  );
}

function TierGroup({ title, entries, color, onCardClick }) {
  if (!entries.length) return null;
  const unlocked = entries.filter((e) => e.unlocked).length;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-0.5">
        <p
          className="text-[10px] uppercase tracking-[0.28em] font-bold"
          style={{ color, fontFamily: "Orbitron, sans-serif" }}
        >
          {title}
        </p>
        <p className="text-[10px] text-slate-500" style={{ fontFamily: "monospace" }}>
          {unlocked}/{entries.length}
        </p>
      </div>
      <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))" }}>
        {entries.map((e) => (
          <LoreCard key={e.slug} entry={e} onClick={() => onCardClick?.(e)} />
        ))}
      </div>
    </div>
  );
}

const TIER_COLOR = { 1: "#00FFA3", 2: "#B47CFF", 3: "#F5D300" };

const RANK_COLOR = {
  seeker: "#00FFA3",
  archivist: "#B47CFF",
  keepers_circle: "#F5D300",
  none: "#3A4560",
};

export default function ArchiveLedger({ wallet, refreshKey = 0, onOpenArchive }) {
  const [entries, setEntries] = useState([]);
  const [rankData, setRankData] = useState(null);
  const [section, setSection] = useState("ledger"); // "ledger" | "drops"
  const [loading, setLoading] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [modalEntry, setModalEntry] = useState(null);

  // Fetch entries + rank on mount / wallet change / external refresh
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const qs = wallet ? `?wallet=${encodeURIComponent(wallet)}` : "";
        const [entriesRes, rankRes] = await Promise.all([
          fetch(`${API}/archive/entries${qs}`),
          wallet ? fetch(`${API}/archive/rank${qs}`) : Promise.resolve(null),
        ]);
        if (cancelled) return;
        if (entriesRes.ok) {
          const data = await entriesRes.json();
          setEntries(data.entries || []);
        }
        if (rankRes && rankRes.ok) {
          setRankData(await rankRes.json());
        } else if (!wallet) {
          setRankData(null);
        }
      } catch {
        /* keep whatever's already in state */
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [wallet, refreshKey]);

  // Sort within each tier: unlocked first, then locked (spec §2.5)
  const grouped = useMemo(() => {
    const byTier = { 1: [], 2: [], 3: [] };
    entries.forEach((e) => (byTier[e.tier] || (byTier[e.tier] = [])).push(e));
    Object.values(byTier).forEach((arr) => {
      arr.sort((a, b) => Number(!!b.unlocked) - Number(!!a.unlocked));
    });
    return byTier;
  }, [entries]);

  const unlockedCount = rankData?.unlocked_count ?? entries.filter((e) => e.unlocked).length;
  const total = rankData?.total ?? entries.length ?? 61;
  const rank = rankData?.rank ?? null;
  const rankTitle = rankData?.rank_title ?? null;
  const rankColor = RANK_COLOR[rank || "none"];
  const progressPct = total ? (unlockedCount / total) * 100 : 0;

  const shareArchive = () => setShareOpen(true);

  return (
    <aside
      className="relative h-full flex flex-col"
      data-testid="archive-ledger"
      style={{
        background:
          "linear-gradient(180deg, rgba(10,15,30,0.85) 0%, rgba(5,7,18,0.9) 100%)",
        borderLeft: "1px solid rgba(0,255,163,0.08)",
      }}
    >
      {/* Rank header — always visible */}
      <header className="p-5 border-b border-white/[0.06] flex-shrink-0">
        <div className="flex items-start gap-4">
          <RankBadge rank={rank} rankTitle={rankTitle} size={64} showTitle={false} />
          <div className="flex-1 min-w-0">
            <p
              className="text-[9px] uppercase tracking-[0.28em] text-slate-500"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              Archive Rank
            </p>
            <p
              className="text-base font-bold truncate"
              style={{ color: rankColor, fontFamily: "Orbitron, sans-serif" }}
              data-testid="ledger-rank-title"
            >
              {rankTitle || "Unranked"}
            </p>
            <p className="text-[10px] text-slate-500 mt-1" style={{ fontFamily: "monospace" }}>
              {unlockedCount} of {total} discovered
            </p>
          </div>
          <button
            type="button"
            onClick={shareArchive}
            data-testid="ledger-share-btn"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest border border-white/15 hover:border-white/35 text-white/80 hover:text-white transition-colors"
            style={{ fontFamily: "Orbitron, sans-serif" }}
            title="Share your Archive"
          >
            <Share2 size={11} />
            <span className="hidden lg:inline">Share</span>
          </button>
        </div>
        <div className="mt-4">
          <ProgressBar percent={progressPct} color={rankColor} />
        </div>
        {/* Section switcher */}
        <nav className="mt-4 flex gap-1 p-1 rounded-full bg-white/[0.03] border border-white/[0.06] w-fit">
          {[
            { id: "ledger", label: "Ledger", icon: BookOpen },
            { id: "drops", label: "Daily Drops", icon: Sparkles },
          ].map(({ id, label, icon: Icon }) => {
            const active = section === id;
            return (
              <button
                key={id}
                type="button"
                onClick={() => setSection(id)}
                data-testid={`ledger-section-${id}`}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all ${
                  active ? "text-black" : "text-slate-400 hover:text-white"
                }`}
                style={{
                  fontFamily: "Orbitron, sans-serif",
                  background: active ? rankColor : "transparent",
                }}
              >
                <Icon size={11} /> {label}
              </button>
            );
          })}
        </nav>
      </header>

      {/* Section body — scrolls independently */}
      <div className="flex-1 overflow-y-auto p-5" data-testid="archive-ledger-body">
        {section === "ledger" ? (
          <div className="space-y-6">
            {!wallet && (
              <div
                className="rounded-xl p-4 text-center"
                style={{ background: "rgba(10,15,30,0.55)", border: "1px dashed rgba(0,255,163,0.25)" }}
              >
                <p className="text-[11px] leading-relaxed text-slate-400">
                  Connect your wallet to open your Ledger. Discoveries you make with
                  Tinkerpug get filed permanently.
                </p>
              </div>
            )}
            <TierGroup title="Tier I · Seeker" entries={grouped[1] || []} color={TIER_COLOR[1]} onCardClick={setModalEntry} />
            <TierGroup title="Tier II · Archivist" entries={grouped[2] || []} color={TIER_COLOR[2]} onCardClick={setModalEntry} />
            <TierGroup title="Tier III · Keeper's Circle" entries={grouped[3] || []} color={TIER_COLOR[3]} onCardClick={setModalEntry} />
            {loading && entries.length === 0 && (
              <p className="text-center text-[11px] tracking-widest text-slate-600">loading the ledger…</p>
            )}
          </div>
        ) : (
          <DailyDropVault wallet={wallet} />
        )}
      </div>

      {shareOpen && <ShareableCard wallet={wallet} onClose={() => setShareOpen(false)} />}
      {modalEntry && (
        <LoreCardModal
          entry={modalEntry}
          onClose={() => setModalEntry(null)}
          onOpenArchive={(prompt) => {
            setModalEntry(null);
            onOpenArchive?.(prompt);
          }}
        />
      )}
    </aside>
  );
}
