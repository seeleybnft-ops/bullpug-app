/**
 * ShareableCard — the modal that pops up when a user hits "Share your
 * Archive" in the Ledger header.
 *
 * Fetches a server-rendered 1200×630 PNG from `POST /api/archive/share`
 * so link previews on X / Discord / Telegram resolve to the same card.
 * Locally offers Save-to-device and Web-Share fallback, and lets the
 * user edit the pre-populated share text before posting.
 */
import React, { useCallback, useEffect, useState } from "react";
import { X, Download, Share2, Loader2, RefreshCw } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const MAX_REGENERATIONS = 3; // caps LLM cost per share session

const RANK_TEXT = {
  seeker:
    "Just reached Seeker rank in the Bullpug Archive. The chain runs deeper than I thought. Ask Tinkerpug: bullpug.com/archive 🐾",
  archivist:
    "Archivist rank — {count} of {total} lore entries found. There's a full universe in here. bullpug.com/archive 🐾",
  keepers_circle:
    "Keeper's Circle. The full record. Tinkerpug filed my signal in The Ledger. bullpug.com/archive 🐾⚡",
};
const DEFAULT_TEXT =
  "{count} of {total} Archive entries discovered — building the record. bullpug.com/archive 🐾";

function suggestedShareText(rank, count, total) {
  const template = RANK_TEXT[rank] || DEFAULT_TEXT;
  return template
    .replace("{count}", String(count ?? 0))
    .replace("{total}", String(total ?? 0));
}

export default function ShareableCard({ wallet, onClose }) {
  const [state, setState] = useState({ loading: true, image: null, rank: null, count: 0, error: null });
  const [text, setText] = useState("");
  // Session-local counter — resets when the modal is dismounted so
  // reopening the modal grants a fresh budget. Prevents runaway LLM
  // spend from an accidental hold-down-refresh.
  const [regensUsed, setRegensUsed] = useState(0);

  const fetchCard = useCallback(async () => {
    if (!wallet) {
      setState({ loading: false, image: null, rank: null, count: 0, error: "connect a wallet first" });
      return;
    }
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await fetch(`${API}/archive/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Bullpug-CSRF": "1" },
        body: JSON.stringify({ wallet }),
      });
      if (!res.ok) throw new Error(`share ${res.status}`);
      const data = await res.json();
      const image = `data:${data.mime || "image/png"};base64,${data.image_base64}`;
      setState({ loading: false, image, rank: data.rank, count: data.unlocked_count || 0, error: null });
      setText((t) => t || suggestedShareText(data.rank, data.unlocked_count, data.grand_total || data.total));
    } catch (e) {
      setState({ loading: false, image: null, rank: null, count: 0, error: "couldn't render your card — try again in a moment" });
    }
  }, [wallet]);

  // Initial load
  useEffect(() => {
    fetchCard();
  }, [fetchCard]);

  const canRegen = !state.loading && regensUsed < MAX_REGENERATIONS && !!wallet;
  const regenerate = async () => {
    if (!canRegen) return;
    setRegensUsed((n) => n + 1);
    await fetchCard();
  };

  useEffect(() => {
    const onEsc = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [onClose]);

  const [shareStatus, setShareStatus] = useState(null); // null | "copied" | "shared" | "error"

  const download = () => {
    if (!state.image) return;
    const a = document.createElement("a");
    a.href = state.image;
    a.download = `bullpug-archive-${state.rank || "seeker"}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  // Mobile UA sniff — same conservative check used elsewhere. Desktop
  // gets an image-clipboard copy; mobile keeps the Web Share sheet
  // which is fine there (native image previews render correctly).
  const isMobile = () => {
    if (typeof navigator === "undefined") return false;
    return /Android|iPhone|iPad|iPod|IEMobile|BlackBerry|Opera Mini/i.test(
      navigator.userAgent || ""
    );
  };

  // Copy the rendered PNG to the OS clipboard as a real image blob so
  // pasting into X / Discord / Slack lands the card, not a URL.
  const copyImageToClipboard = async () => {
    if (!state.image) return false;
    if (!navigator?.clipboard?.write || typeof ClipboardItem === "undefined") {
      return false;
    }
    try {
      const res = await fetch(state.image);
      const blob = await res.blob();
      await navigator.clipboard.write([
        new ClipboardItem({ [blob.type || "image/png"]: blob }),
      ]);
      return true;
    } catch {
      return false;
    }
  };

  const share = async () => {
    const url = window.location.origin + "/archive";
    setShareStatus(null);

    // ── Desktop path: copy the image to the clipboard, no OS dialog ──
    if (!isMobile()) {
      const ok = await copyImageToClipboard();
      if (ok) {
        setShareStatus("copied");
        // Also copy the share text so a follow-up paste in the caption
        // box lands the text half.
        try { await navigator.clipboard.writeText(text); } catch { /* silent */ }
        setTimeout(() => setShareStatus(null), 5000);
        return;
      }
      // Fallback if clipboard API unavailable: just copy the text.
      try {
        await navigator.clipboard.writeText(`${text}\n${url}`);
        setShareStatus("copied");
        setTimeout(() => setShareStatus(null), 5000);
      } catch {
        setShareStatus("error");
      }
      return;
    }

    // ── Mobile path: keep the Web Share sheet w/ file attachment ────
    try {
      if (state.image && navigator.canShare) {
        const res = await fetch(state.image);
        const blob = await res.blob();
        const file = new File([blob], "bullpug-archive.png", { type: "image/png" });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ title: "Bullpug Archive", text, url, files: [file] });
          setShareStatus("shared");
          return;
        }
      }
      if (navigator.share) {
        await navigator.share({ title: "Bullpug Archive", text, url });
        setShareStatus("shared");
        return;
      }
    } catch { /* user dismissed sheet — silent */ }
    try {
      await navigator.clipboard.writeText(`${text}\n${url}`);
      setShareStatus("copied");
    } catch {
      setShareStatus("error");
    }
  };

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center p-4 sm:p-8"
      style={{ background: "rgba(2,4,10,0.86)", backdropFilter: "blur(14px)" }}
      onClick={onClose}
      data-testid="share-card-backdrop"
    >
      <div
        className="relative w-full max-w-2xl rounded-2xl overflow-hidden"
        style={{
          background: "linear-gradient(180deg, rgba(10,15,30,0.98) 0%, rgba(5,7,18,0.98) 100%)",
          border: "1px solid rgba(0,255,163,0.25)",
          boxShadow: "0 30px 80px rgba(0,0,0,0.7)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 z-10 w-9 h-9 rounded-full bg-black/50 border border-white/15 hover:border-white/40 flex items-center justify-center text-white/90"
          data-testid="share-card-close"
        >
          <X size={16} />
        </button>

        <div className="p-5 sm:p-6 space-y-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.28em] text-cyan-300/70" style={{ fontFamily: "Orbitron, sans-serif" }}>
              Share your Archive
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              The image previews on X, Discord, and Telegram.
            </p>
          </div>

          <div
            className="aspect-[1200/630] rounded-xl overflow-hidden bg-[#05050A] flex items-center justify-center"
            data-testid="share-card-preview"
          >
            {state.loading && (
              <div className="flex items-center gap-2 text-[11px] tracking-widest text-cyan-300/60" style={{ fontFamily: "monospace" }}>
                <Loader2 size={12} className="animate-spin" /> RENDERING
              </div>
            )}
            {!state.loading && state.image && (
              <img src={state.image} alt="Your Archive rank card" className="w-full h-full object-cover" />
            )}
            {!state.loading && state.error && (
              <p className="text-xs text-slate-500 italic px-6 text-center">{state.error}</p>
            )}
          </div>

          <div>
            <label className="text-[10px] uppercase tracking-[0.28em] text-slate-500" style={{ fontFamily: "Orbitron, sans-serif" }}>
              Share text
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              data-testid="share-card-text"
              className="mt-1 w-full resize-none rounded-lg bg-black/50 border border-white/10 focus:border-cyan-300/40 focus:outline-none p-3 text-sm text-white"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <button
              type="button"
              onClick={regenerate}
              disabled={!canRegen}
              data-testid="share-card-regenerate"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest bg-white/5 hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed text-white border border-white/15"
              style={{ fontFamily: "Orbitron, sans-serif" }}
              title={
                regensUsed >= MAX_REGENERATIONS
                  ? "Regeneration limit reached for this session"
                  : "Generate a fresh Bullpug-universe scene"
              }
            >
              {state.loading ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <RefreshCw size={13} />
              )}
              Regenerate
              <span
                className="ml-1 text-[9px] px-1.5 py-0.5 rounded-full"
                style={{ background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.7)" }}
                data-testid="share-card-regen-counter"
              >
                {MAX_REGENERATIONS - regensUsed} left
              </span>
            </button>
            <button
              type="button"
              onClick={download}
              disabled={!state.image}
              data-testid="share-card-download"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest bg-white/10 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed text-white border border-white/15"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              <Download size={13} /> Save PNG
            </button>
            <button
              type="button"
              onClick={share}
              disabled={!state.image}
              data-testid="share-card-share"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest text-black disabled:opacity-40 disabled:cursor-not-allowed ml-auto"
              style={{ background: "#00FFA3", fontFamily: "Orbitron, sans-serif" }}
            >
              <Share2 size={13} /> Share
            </button>
          </div>
          {shareStatus === "copied" && (
            <p
              className="text-[11px] text-center pt-2"
              style={{ fontFamily: "monospace", color: "#00FFA3" }}
              data-testid="share-card-copied-message"
            >
              keeper's note: image copied to clipboard. paste it anywhere.
            </p>
          )}
          {shareStatus === "shared" && (
            <p
              className="text-[11px] text-center pt-2"
              style={{ fontFamily: "monospace", color: "#00FFA3" }}
              data-testid="share-card-shared-message"
            >
              keeper's note: signal on its way.
            </p>
          )}
          {shareStatus === "error" && (
            <p
              className="text-[11px] text-center pt-2 text-red-300/90"
              style={{ fontFamily: "monospace" }}
              data-testid="share-card-share-error"
            >
              keeper's note: clipboard blocked — use Save PNG instead.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
