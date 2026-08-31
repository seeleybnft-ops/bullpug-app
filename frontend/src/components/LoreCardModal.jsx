/**
 * LoreCardModal — full-view modal for Archive lore entries.
 *
 * Two states:
 *  • Unlocked: name (tier colour), full-size visual-canon image if
 *    available, Tinkerpug's full excerpt (untruncated), tier badge +
 *    rank requirement, filed date, close.
 *  • Locked: tier indicator, italic locked description, prompt to ask
 *    the Keeper, and an "Open the Archive" button that closes the modal
 *    and focuses the chat input with a thematic prompt derived from the
 *    locked description (never the real entry name — that would spoil
 *    the discovery loop).
 *
 * Esc closes. Click-outside-content closes. Focus is trapped to the
 * primary action on open.
 */
import React, { useEffect, useRef, useState } from "react";
import { X, Lock, Sparkles, MessageCircle, PawPrint } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIER = {
  1: { color: "#00FFA3", label: "TIER I", rank: "Seeker" },
  2: { color: "#B47CFF", label: "TIER II", rank: "Archivist" },
  3: { color: "#F5D300", label: "TIER III", rank: "Keeper's Circle" },
  special: { color: "#F5D300", label: "ARCHIVE SPECIAL", rank: "The Companion's Secret" },
};

function formatDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return "";
  }
}

/**
 * Given a locked description like "What the seer pays for what she sees.",
 * return a chat-input prompt like "Tell me about what the seer pays for what she sees."
 * Never uses the real entry name — the whole point of a locked card is
 * that the visitor has to phrase the request themselves.
 */
function derivePromptFromLockedDesc(desc) {
  if (!desc) return "Tell me something the chain doesn't say out loud.";
  const clean = String(desc).replace(/^["“]|["”]$/g, "").trim().replace(/\.$/, "");
  const lower = clean.charAt(0).toLowerCase() + clean.slice(1);
  return `Tell me about ${lower}.`;
}

export default function LoreCardModal({ entry, onClose, onOpenArchive }) {
  const primaryBtnRef = useRef(null);
  const tierMeta = TIER[entry?.tier] || TIER[1];
  const unlocked = !!entry?.unlocked;
  const [image, setImage] = useState(null);

  // Lazy-fetch the full-size visual canon image for unlocked entries.
  useEffect(() => {
    if (!unlocked || !entry?.has_image) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API}/archive/entry-image/${encodeURIComponent(entry.slug)}`);
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled || !data.image_base64) return;
        setImage(`data:${data.image_mime || "image/png"};base64,${data.image_base64}`);
      } catch {
        /* silent */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [unlocked, entry?.has_image, entry?.slug]);

  // Esc to close + focus primary button
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", onKey);
    primaryBtnRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!entry) return null;

  const handleOpenArchive = () => {
    const prompt = derivePromptFromLockedDesc(entry.locked_desc);
    onClose?.();
    onOpenArchive?.(prompt);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="lore-card-modal"
      onClick={onClose}
      className="fixed inset-0 z-[80] flex items-center justify-center p-4"
      style={{ background: "rgba(3,5,14,0.82)", backdropFilter: "blur(6px)" }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl"
        style={{
          background: "linear-gradient(180deg, rgba(10,15,30,0.98) 0%, rgba(5,7,18,0.98) 100%)",
          border: `1px solid ${tierMeta.color}44`,
          boxShadow: `0 0 48px ${tierMeta.color}22, inset 0 0 0 1px rgba(255,255,255,0.03)`,
        }}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          data-testid="lore-card-modal-close"
          className="absolute top-3 right-3 rounded-full p-1.5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors z-10"
        >
          <X size={16} />
        </button>

        {unlocked ? (
          <div className="p-6 sm:p-8" data-testid="lore-card-modal-unlocked">
            <div className="flex items-center gap-2 mb-3">
              {entry.tier === "special" ? (
                <PawPrint size={14} style={{ color: tierMeta.color }} strokeWidth={2.4} />
              ) : (
                Array.from({ length: entry.tier }).map((_, i) => (
                  <span
                    key={i}
                    className="rounded-full"
                    style={{ width: 7, height: 7, background: tierMeta.color, boxShadow: `0 0 8px ${tierMeta.color}` }}
                  />
                ))
              )}
              <span
                className="text-[10px] font-bold uppercase tracking-[0.32em] ml-1"
                style={{ color: tierMeta.color, fontFamily: "Orbitron, sans-serif" }}
              >
                {entry.tier === "special" ? `${tierMeta.label} · ${tierMeta.rank}` : tierMeta.label}
              </span>
              <Sparkles size={13} style={{ color: tierMeta.color, marginLeft: "auto" }} />
            </div>
            <h2
              className="text-2xl sm:text-3xl font-bold leading-tight mb-4"
              style={{ color: tierMeta.color, fontFamily: "Orbitron, sans-serif", letterSpacing: "0.01em" }}
              data-testid="lore-card-modal-title"
            >
              {entry.name}
            </h2>
            {image && (
              <div
                className="relative w-full rounded-xl overflow-hidden mb-5"
                style={{ border: `1px solid ${tierMeta.color}33`, boxShadow: `0 0 20px ${tierMeta.color}22` }}
              >
                <img
                  src={image}
                  alt={entry.name}
                  className="w-full h-auto max-h-[420px] object-cover"
                  draggable={false}
                />
              </div>
            )}
            {entry.tinkerpug_excerpt && (
              <blockquote
                className="text-sm leading-relaxed text-slate-200 whitespace-pre-wrap border-l-2 pl-4 py-1"
                style={{ borderColor: `${tierMeta.color}66` }}
                data-testid="lore-card-modal-excerpt"
              >
                {entry.tinkerpug_excerpt.replace(/^["“]|["”]$/g, "")}
              </blockquote>
            )}
            {entry.unlocked_at && (
              <p
                className="mt-5 text-[10px] uppercase tracking-[0.28em] text-slate-500"
                style={{ fontFamily: "monospace" }}
                data-testid="lore-card-modal-filed"
              >
                Filed · {formatDate(entry.unlocked_at)}
              </p>
            )}
          </div>
        ) : (
          <div className="p-6 sm:p-8" data-testid="lore-card-modal-locked">
            <div className="flex items-center gap-2 mb-3">
              {entry.tier === "special" ? (
                <PawPrint size={14} className="text-slate-500" strokeWidth={2.4} />
              ) : (
                Array.from({ length: entry.tier }).map((_, i) => (
                  <span
                    key={i}
                    className="rounded-full"
                    style={{ width: 7, height: 7, background: "rgba(255,255,255,0.25)" }}
                  />
                ))
              )}
              <span
                className="text-[10px] font-bold uppercase tracking-[0.32em] ml-1 text-slate-400"
                style={{ fontFamily: "Orbitron, sans-serif" }}
              >
                {tierMeta.label} · Sealed
              </span>
              <Lock size={13} className="text-slate-500 ml-auto" />
            </div>
            <p
              className="text-base italic leading-relaxed text-slate-300 mb-6"
              data-testid="lore-card-modal-locked-desc"
            >
              {entry.locked_desc}
            </p>
            <p className="text-sm text-slate-400 mb-6">
              Ask the Keeper to unlock this entry.
            </p>
            <button
              ref={primaryBtnRef}
              type="button"
              onClick={handleOpenArchive}
              data-testid="lore-card-modal-open-archive"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full font-bold uppercase tracking-widest text-[11px] transition-all"
              style={{
                background: tierMeta.color,
                color: "#000",
                fontFamily: "Orbitron, sans-serif",
                boxShadow: `0 0 20px ${tierMeta.color}55`,
              }}
            >
              <MessageCircle size={13} />
              Open the Archive
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
