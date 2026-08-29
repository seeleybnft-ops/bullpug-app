/**
 * DropModal — full-view drop card modal. Opens when a DropCard is tapped.
 *
 * Larger canvas, gentler gradient (image can afford to breathe here),
 * plus save + share actions. The save button downloads the RAW image —
 * spec §9.4 mentions "the card IS the artefact" but until we add a
 * canvas compositor the raw base64 image is the most useful thing to
 * hand a user. We can wire canvas compositing later if desired.
 */
import React, { useEffect } from "react";
import { X, Download, Share2 } from "lucide-react";

function fmtDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

function downloadImage(base64, filename) {
  if (!base64) return;
  const a = document.createElement("a");
  a.href = base64;
  a.download = filename || "bullpug-daily-drop.png";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function shareDrop(drop) {
  const text = `Day ${drop.day_number || "?"} in the Bullpug Archive. Today's drop: ${drop.scene_title || drop.theme || "an Archive record"}. bullpug.com/archive 🐾`;
  const shareUrl = window.location.origin + "/archive";
  if (navigator.share) {
    try {
      await navigator.share({ title: "Bullpug Archive", text, url: shareUrl });
      return;
    } catch {
      /* user cancelled — fall through to clipboard */
    }
  }
  try {
    await navigator.clipboard.writeText(`${text}\n${shareUrl}`);
    alert("Share text copied to clipboard.");
  } catch {
    /* silent */
  }
}

export default function DropModal({ drop, onClose }) {
  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [onClose]);

  if (!drop) return null;
  const title = drop.scene_title || drop.theme || "Archive record";
  const accent = drop.kind === "canonical" ? "#F5D300" : "#00FFA3";

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-8"
      style={{ background: "rgba(2,4,10,0.85)", backdropFilter: "blur(10px)" }}
      onClick={onClose}
      data-testid="drop-modal-backdrop"
    >
      <div
        className="relative w-full max-w-4xl max-h-[92vh] rounded-2xl overflow-hidden bg-[#05050A]"
        style={{
          boxShadow: `0 0 0 1px ${accent}22, 0 30px 80px rgba(0,0,0,0.7)`,
        }}
        onClick={(e) => e.stopPropagation()}
        data-testid="drop-modal"
      >
        {/* Image */}
        <div className="relative aspect-[16/9] bg-[#0a0f1e]">
          {drop.image_base64 && (
            <img
              src={drop.image_base64}
              alt={title}
              className="absolute inset-0 w-full h-full object-cover"
              draggable={false}
            />
          )}
          {/* Softer gradient — full view can show more of the image */}
          <div
            aria-hidden
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                "linear-gradient(180deg, rgba(5,5,10,0) 0%, rgba(5,5,10,0) 55%, rgba(5,5,10,0.4) 82%, rgba(5,5,10,0.75) 100%)",
            }}
          />
          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            data-testid="drop-modal-close"
            className="absolute top-3 right-3 w-9 h-9 rounded-full bg-black/60 border border-white/15 hover:border-white/40 flex items-center justify-center text-white/90 transition-colors"
          >
            <X size={16} />
          </button>
          {/* Day / date */}
          <div className="absolute top-4 left-5 flex flex-col gap-0.5">
            {drop.day_number && (
              <span className="text-[10px] tracking-[0.3em] text-white/85 font-bold" style={{ fontFamily: "monospace", textShadow: "0 1px 6px rgba(0,0,0,0.9)" }}>
                DAY {drop.day_number}
              </span>
            )}
            {drop.date_utc && (
              <span className="text-[10px] tracking-[0.2em] text-white/55" style={{ fontFamily: "monospace", textShadow: "0 1px 4px rgba(0,0,0,0.9)" }}>
                {fmtDate(drop.date_utc).toUpperCase()}
              </span>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="p-5 sm:p-7 space-y-4 max-h-[45vh] overflow-y-auto">
          <div>
            <h3 className="text-xl sm:text-2xl font-bold" style={{ color: accent, fontFamily: "Orbitron, sans-serif" }}>
              {title}
            </h3>
          </div>
          {drop.caption && (
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {drop.caption}
            </p>
          )}
          {drop.scene && (
            <p className="text-[11px] text-slate-500 italic">
              Archive scene log: {drop.scene}
            </p>
          )}
          <div className="flex flex-wrap gap-2 pt-2">
            <button
              type="button"
              data-testid="drop-modal-save"
              onClick={() => downloadImage(drop.image_base64, `bullpug-day-${drop.day_number || "drop"}.png`)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest bg-white/10 hover:bg-white/20 text-white border border-white/15 transition-colors"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              <Download size={13} /> Save to device
            </button>
            <button
              type="button"
              data-testid="drop-modal-share"
              onClick={() => shareDrop(drop)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest text-black transition-colors"
              style={{ background: accent, fontFamily: "Orbitron, sans-serif" }}
            >
              <Share2 size={13} /> Share
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
