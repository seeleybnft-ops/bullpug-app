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
import React from "react";
import { Lock, Sparkles } from "lucide-react";

const TIER = {
  1: { color: "#00FFA3", label: "TIER I", dots: 1 },
  2: { color: "#B47CFF", label: "TIER II", dots: 2 },
  3: { color: "#F5D300", label: "TIER III", dots: 3 },
};

function TierDots({ tier }) {
  const c = TIER[tier];
  if (!c) return null;
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

export default function LoreCard({ entry, onClick }) {
  const tierMeta = TIER[entry.tier] || TIER[1];
  const unlocked = !!entry.unlocked;

  const baseClasses =
    "relative flex flex-col rounded-xl overflow-hidden transition-all duration-300 group cursor-default";
  const stateClasses = unlocked
    ? "bg-[#0a0f1e]/80 border border-white/10 hover:border-white/25 hover:-translate-y-0.5"
    : "bg-[#0a0f1e]/40 border border-white/[0.06] hover:border-white/12";

  return (
    <article
      onClick={onClick}
      data-testid={`lore-card-${entry.slug}`}
      data-unlocked={unlocked ? "1" : "0"}
      className={`${baseClasses} ${stateClasses}`}
      style={{
        boxShadow: unlocked
          ? `inset 0 0 0 1px rgba(255,255,255,0.02), 0 0 24px rgba(0,0,0,0.35)`
          : "inset 0 0 0 1px rgba(255,255,255,0.02)",
      }}
    >
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
            {/* PULL COPY — locked description must be fully visible.
                Italicised, muted but readable — designed to make the
                visitor want to unlock this. */}
            <p className="text-[11px] leading-relaxed italic text-slate-500">
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
    </article>
  );
}
