/**
 * LoreCard — one card per Archive entry. Locked or unlocked state.
 *
 * Locked cards are deliberately expressive: the locked description
 * ("What the seer pays for what she sees") is the pull copy — it MUST
 * be fully visible, not tucked behind a generic lock icon. That single
 * line is what convinces a visitor to go dig for the entry.
 *
 * Unlocked cards show: name, 2-line excerpt from Tinkerpug's response,
 * unlock date, and (Phase E) the visual-canon image for the subject.
 *
 * Tier tint follows the same palette as RankBadge:
 *   Tier 1 → cyan   Tier 2 → violet   Tier 3 → gold
 */
import React, { useEffect, useState } from "react";
import { Lock, Sparkles, PawPrint } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIER = {
  1: { color: "#00FFA3", label: "TIER I", dots: 1 },
  2: { color: "#B47CFF", label: "TIER II", dots: 2 },
  3: { color: "#F5D300", label: "TIER III", dots: 3 },
  special: { color: "#F5D300", label: "SPECIAL", dots: 3 },
};

function TierDots({ tier }) {
  const c = TIER[tier];
  if (!c) return null;
  if (tier === "special") {
    return (
      <span className="inline-flex items-center" aria-label={c.label}>
        <PawPrint size={11} style={{ color: c.color }} strokeWidth={2.4} />
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1" aria-label={c.label}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="rounded-full"
          style={{
            width: 5,
            height: 5,
            background: i < c.dots ? c.color : "rgba(255,255,255,0.15)",
            boxShadow: i < c.dots ? `0 0 6px ${c.color}` : "none",
          }}
        />
      ))}
    </span>
  );
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return "";
  }
}

export default function LoreCard({ entry, onClick, isKeeper = false }) {
  const tierMeta = TIER[entry.tier] || TIER[1];
  const unlocked = !!entry.unlocked;
  // Keeper's Circle milestone marker — only surfaces on the viewer's
  // OWN unlocked cards once they've hit top rank. Read from prop; the
  // Ledger owns the rank check so we don't refetch per-card.
  const showKeeperMarker = isKeeper && unlocked;

  // Lazily fetch the Visual Canon thumbnail on mount when the entry is
  // unlocked and the entries endpoint says an image exists. Failures
  // are silent — the card just renders without a thumb and the next
  // ledger refresh (or a page reload) retries. Never re-fetches once
  // we have a URL.
  const [thumb, setThumb] = useState(null);
  useEffect(() => {
    if (!unlocked || !entry.has_image || thumb) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API}/archive/entry-image/${encodeURIComponent(entry.slug)}`);
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled || !data.image_base64) return;
        setThumb(`data:${data.image_mime || "image/png"};base64,${data.image_base64}`);
      } catch {
        /* silent retry-on-remount */
      }
    })();
    return () => { cancelled = true; };
  }, [unlocked, entry.has_image, entry.slug, thumb]);

  const baseClasses =
    "relative flex flex-col rounded-xl overflow-hidden transition-all duration-300 group cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40";
  const stateClasses = unlocked
    ? (showKeeperMarker
        ? "bg-[#0a0f1e]/80 border hover:-translate-y-0.5"
        : "bg-[#0a0f1e]/80 border border-white/10 hover:border-white/25 hover:-translate-y-0.5")
    : "bg-[#0a0f1e]/40 border border-white/[0.06] hover:border-white/12";
  const keeperBorderStyle = showKeeperMarker
    ? {
        borderColor: "rgba(245,211,0,0.45)",
        boxShadow:
          "0 0 12px rgba(245,211,0,0.18), inset 0 0 0 1px rgba(245,211,0,0.15)",
      }
    : {};

  const handleKey = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <article
      onClick={onClick}
      onKeyDown={handleKey}
      role="button"
      tabIndex={0}
      aria-label={unlocked ? `Open ${entry.name}` : `Sealed record — ${entry.locked_desc}`}
      data-testid={`lore-card-${entry.slug}`}
      data-unlocked={unlocked ? "1" : "0"}
      className={`${baseClasses} ${stateClasses}`}
      style={{
        ...keeperBorderStyle,
        boxShadow: showKeeperMarker
          ? `inset 0 0 0 1px rgba(245,211,0,0.22), 0 0 18px rgba(245,211,0,0.15), 0 0 24px rgba(0,0,0,0.35)`
          : unlocked
            ? `inset 0 0 0 1px rgba(255,255,255,0.02), 0 0 24px rgba(0,0,0,0.35)`
            : "inset 0 0 0 1px rgba(255,255,255,0.02)",
      }}
    >
      {/* Keeper's Circle milestone pip — only for the viewer's own
          unlocked cards once they've reached the top rank. Gold
          SignalGlyph mirroring the rank badge. Subtle pulse animation
          scoped to this card. */}
      {showKeeperMarker && (
        <span
          aria-label="Keeper's Circle marker"
          data-testid={`lore-card-keeper-pip-${entry.slug}`}
          className="absolute top-2 right-2 z-[1] flex items-center justify-center rounded-full"
          style={{
            width: 14,
            height: 14,
            background:
              "radial-gradient(circle at 35% 30%, #F5D300 0%, #C9A200 65%, rgba(115,92,0,0.8) 100%)",
            border: "1px solid rgba(245,211,0,0.75)",
            boxShadow:
              "0 0 8px rgba(245,211,0,0.55), inset 0 0 0 1px rgba(0,0,0,0.25)",
            animation: "keeper-pip-pulse 2.8s ease-in-out infinite",
          }}
        >
          <span
            aria-hidden
            className="rounded-full"
            style={{ width: 4, height: 4, background: "#0a0a12" }}
          />
        </span>
      )}
      {/* Tier accent bar — thin left stripe */}
      <span
        aria-hidden
        className="absolute left-0 top-0 h-full"
        style={{
          width: 2,
          background: unlocked ? tierMeta.color : "rgba(255,255,255,0.08)",
          boxShadow: unlocked ? `0 0 12px ${tierMeta.color}55` : "none",
        }}
      />

      <div className="p-4 pl-5 flex flex-col gap-2.5 min-h-[132px]">
        {/* Header row: tier + status glyph */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TierDots tier={entry.tier} />
            <span
              className="text-[9px] font-bold uppercase tracking-[0.25em]"
              style={{ color: unlocked ? tierMeta.color : "rgba(255,255,255,0.35)", fontFamily: "Orbitron, sans-serif" }}
            >
              {tierMeta.label}
            </span>
          </div>
          {unlocked ? (
            <Sparkles size={12} style={{ color: tierMeta.color, opacity: 0.9 }} />
          ) : (
            <Lock size={11} className="text-slate-600" />
          )}
        </div>

        {/* Name — visible when unlocked, redacted with a heavy blur when
            locked. We still render the real string so the DOM node is
            the same shape (layout stays identical between states), but
            we apply `filter: blur(6px)`, dim the colour heavily, and
            block selection/aria-hide it so it cannot be copy-pasted or
            read by assistive tech. The shape of a title is implied;
            the words are not. */}
        {unlocked ? (
          <h4
            className="text-sm font-bold leading-tight"
            style={{
              color: "#fff",
              fontFamily: "Orbitron, sans-serif",
              letterSpacing: "0.02em",
            }}
          >
            {entry.name}
          </h4>
        ) : (
          <h4
            aria-hidden="true"
            className="text-sm font-bold leading-tight select-none"
            style={{
              color: "rgba(255,255,255,0.35)",
              fontFamily: "Orbitron, sans-serif",
              letterSpacing: "0.02em",
              filter: "blur(6px)",
              userSelect: "none",
              WebkitUserSelect: "none",
              pointerEvents: "none",
            }}
          >
            {entry.name}
          </h4>
        )}

        {/* Body — locked description OR unlocked excerpt */}
        {unlocked ? (
          <>
            {thumb && (
              <div
                className="relative w-full rounded-lg overflow-hidden mt-0.5"
                style={{
                  height: 96,
                  border: `1px solid ${tierMeta.color}33`,
                  boxShadow: `0 0 12px ${tierMeta.color}22`,
                }}
              >
                <img
                  src={thumb}
                  alt=""
                  className="absolute inset-0 w-full h-full object-cover"
                  loading="lazy"
                  draggable={false}
                />
                <div
                  aria-hidden
                  className="absolute inset-0 pointer-events-none"
                  style={{
                    background:
                      "linear-gradient(180deg, rgba(5,7,18,0) 40%, rgba(5,7,18,0.6) 100%)",
                  }}
                />
              </div>
            )}
            <p className="text-[11px] leading-relaxed text-slate-400 line-clamp-3">
              {(entry.tinkerpug_excerpt || entry.locked_desc || "").replace(/^["“]|["”]$/g, "")}
            </p>
            {entry.unlocked_at && (
              <p className="text-[9px] uppercase tracking-widest text-slate-600 mt-auto" style={{ fontFamily: "monospace" }}>
                Filed · {formatDate(entry.unlocked_at)}
              </p>
            )}
          </>
        ) : (
          <>
            {/* Locked description is blurred to match the title —
                shape-of-text is preserved so the card reads as sealed
                content, but the words themselves are unreadable and
                unsearchable. italic + slate colour survives underneath
                the blur so the visual language stays consistent with
                the unlocked state. */}
            <p
              aria-hidden="true"
              className="text-[11px] leading-relaxed italic text-slate-500 select-none"
              style={{
                filter: "blur(6px)",
                userSelect: "none",
                WebkitUserSelect: "none",
                pointerEvents: "none",
              }}
            >
              {entry.locked_desc}
            </p>
            <p
              className="text-[9px] uppercase tracking-widest text-slate-700 mt-auto"
              style={{ fontFamily: "monospace" }}
            >
              Sealed record · ask the Keeper
            </p>
          </>
        )}
      </div>
      {showKeeperMarker && (
        <style>{`
          @keyframes keeper-pip-pulse {
            0%, 100% { box-shadow: 0 0 8px rgba(245,211,0,0.55), inset 0 0 0 1px rgba(0,0,0,0.25); }
            50%      { box-shadow: 0 0 14px rgba(245,211,0,0.85), inset 0 0 0 1px rgba(0,0,0,0.25); }
          }
        `}</style>
      )}
    </article>
  );
}
