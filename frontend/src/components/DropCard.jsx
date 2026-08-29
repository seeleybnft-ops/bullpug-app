/**
 * DropCard — a single daily-drop tile in the Vault.
 *
 * Design rule (from spec §9.2): the generated image IS the card. Full-bleed,
 * no border between image and card edge. A vertical gradient sits on top —
 * transparent at the top so the image reads as atmosphere, darkening to
 * ~75% opacity in the bottom third where text lives. The user is looking
 * INTO the scene, not AT an illustration inside a card.
 *
 * Gold accent triggers when Tinkerpug filed a field-note against this
 * drop (drop.kind === "canonical"); regular procedural drops use cyan.
 */
import React from "react";

const CYAN = "#00FFA3";
const GOLD = "#F5D300";

function shortDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { day: "numeric", month: "short" }).toUpperCase();
  } catch {
    return "";
  }
}

export default function DropCard({ drop, onClick }) {
  const title = drop.scene_title || drop.theme || "Archive record";
  const caption = drop.caption || "";
  const accent = drop.kind === "canonical" ? GOLD : CYAN;
  const image = drop.image_base64;
  const dayLabel = drop.day_number ? `DAY ${drop.day_number}` : "";
  const dateLabel = drop.date_utc ? shortDate(drop.date_utc) : "";

  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`drop-card-day-${drop.day_number || "x"}`}
      className="relative aspect-square rounded-xl overflow-hidden group text-left transition-transform duration-300 hover:-translate-y-0.5"
      style={{
        background: "#05050A",
        boxShadow: `0 4px 32px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(255,255,255,0.06)`,
      }}
    >
      {/* Image = the atmosphere. Full bleed, absolutely no crop margin. */}
      {image ? (
        <img
          src={image}
          alt={title}
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-[1.04]"
          draggable={false}
        />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a0f1e] to-[#05050A]" />
      )}

      {/* Gradient overlay — transparent at top, ~75% dark at the bottom third. */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "linear-gradient(180deg, rgba(5,5,10,0) 0%, rgba(5,5,10,0) 40%, rgba(5,5,10,0.55) 65%, rgba(5,5,10,0.85) 100%)",
        }}
      />

      {/* Top-left: day label + date, over the lighter part of the image */}
      <div className="absolute top-3 left-3 flex flex-col gap-0.5 z-10">
        {dayLabel && (
          <span
            className="text-[9px] font-bold tracking-[0.25em] text-white/85"
            style={{ fontFamily: "monospace", textShadow: "0 1px 6px rgba(0,0,0,0.9)" }}
          >
            {dayLabel}
          </span>
        )}
        {dateLabel && (
          <span
            className="text-[9px] tracking-[0.2em] text-white/55"
            style={{ fontFamily: "monospace", textShadow: "0 1px 4px rgba(0,0,0,0.9)" }}
          >
            {dateLabel}
          </span>
        )}
      </div>

      {/* Bottom-right SignalGlyph mark in the accent tier colour */}
      <span
        aria-hidden
        className="absolute bottom-3 right-3 rounded-full z-10"
        style={{
          width: 10,
          height: 10,
          background: "transparent",
          border: `1px solid ${accent}`,
          boxShadow: `0 0 8px ${accent}, inset 0 0 4px ${accent}`,
        }}
      />

      {/* Bottom text block — sits in the darkened third */}
      <div className="absolute bottom-0 left-0 right-0 p-4 z-10">
        <h4
          className="text-sm font-bold leading-tight mb-1"
          style={{
            color: accent,
            fontFamily: "Orbitron, sans-serif",
            textShadow: "0 1px 8px rgba(0,0,0,0.75)",
          }}
        >
          {title}
        </h4>
        <p
          className="text-[11px] leading-snug text-white/70 line-clamp-2"
          style={{ textShadow: "0 1px 4px rgba(0,0,0,0.85)" }}
        >
          {caption || "Direct from the Archive."}
        </p>
      </div>
    </button>
  );
}
