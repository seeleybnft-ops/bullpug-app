/**
 * RankBadge — the SignalGlyph rendered as a rank marker.
 *
 * The SignalGlyph is Bullpug's chain-link circle with an ember centre.
 * Rank tint:
 *   • seeker         — cyan (Tier 1)
 *   • archivist      — violet (Tier 2)
 *   • keepers_circle — gold (Tier 3)
 *   • null           — dim slate, visitor hasn't earned Seeker yet
 *
 * Reused in the Archive Ledger header today and in profile pages later.
 */
import React from "react";

const RANK_COLOR = {
  seeker: { core: "#00FFA3", glow: "rgba(0,255,163,0.35)", ring: "rgba(0,255,163,0.55)" },
  archivist: { core: "#B47CFF", glow: "rgba(180,124,255,0.35)", ring: "rgba(180,124,255,0.6)" },
  keepers_circle: { core: "#F5D300", glow: "rgba(245,211,0,0.4)", ring: "rgba(245,211,0,0.65)" },
  none: { core: "#3A4560", glow: "rgba(58,69,96,0.25)", ring: "rgba(58,69,96,0.55)" },
};

export function RankBadge({ rank = null, rankTitle = null, size = 72, showTitle = true, subtitle = null }) {
  const key = rank || "none";
  const c = RANK_COLOR[key] || RANK_COLOR.none;
  const title = rankTitle || (rank ? rank : "Unranked");
  return (
    <div className="flex flex-col items-center gap-2" data-testid={`rank-badge-${key}`}>
      <div
        className="relative flex items-center justify-center"
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${c.glow} 0%, transparent 70%)`,
        }}
      >
        {/* Outer chain-link ring */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: `1.5px solid ${c.ring}`,
            boxShadow: `0 0 24px ${c.glow}, inset 0 0 12px ${c.glow}`,
          }}
        />
        {/* Inner chain-link ring (double stroke effect) */}
        <div
          className="absolute rounded-full"
          style={{
            inset: 6,
            border: `1px solid ${c.ring}`,
            opacity: 0.55,
          }}
        />
        {/* Ember centre */}
        <div
          className="rounded-full"
          style={{
            width: size * 0.28,
            height: size * 0.28,
            background: c.core,
            boxShadow: `0 0 12px ${c.core}, 0 0 24px ${c.glow}`,
          }}
        />
        {/* Four chain-link nubs at cardinals */}
        {[0, 90, 180, 270].map((deg) => (
          <span
            key={deg}
            className="absolute"
            style={{
              width: 4,
              height: 4,
              background: c.ring,
              borderRadius: "50%",
              transform: `rotate(${deg}deg) translateY(-${size / 2 - 2}px)`,
              transformOrigin: "center",
            }}
          />
        ))}
      </div>
      {showTitle && (
        <div className="text-center">
          <p
            className="text-[10px] font-bold uppercase tracking-[0.2em]"
            style={{ color: c.core, fontFamily: "Orbitron, sans-serif" }}
            data-testid="rank-badge-title"
          >
            {title}
          </p>
          {subtitle && <p className="text-[9px] text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
      )}
    </div>
  );
}

export default RankBadge;
