import { useEffect, useRef, useState } from "react";
import { X, Volume2, VolumeX, SkipForward, Share2, Check } from "lucide-react";

const STORAGE_KEY = "bullpug_origins_trailer_seen_v1";

// Shareable text + URL — defined once so re-runs / re-opens use the same copy.
const SHARE_TEXT = "The Origins page is live — read the Bullpug canon: pug-faced skyscrapers, Snout Scanners, and a heartbeat in the noise. 🐾⚡";
function getShareUrl() {
  if (typeof window === "undefined") return "https://bullpug.io/lore";
  return `${window.location.origin}/lore`;
}

export default function OriginsTrailer() {
  const [open, setOpen] = useState(false);
  const [muted, setMuted] = useState(true);
  const [ended, setEnded] = useState(false);
  const [shared, setShared] = useState(false);
  const videoRef = useRef(null);

  // Listen for global "open trailer" events so other components (Lore page replay
  // button, future shareable links, etc.) can re-open this modal at any time.
  useEffect(() => {
    const onOpenEvent = () => {
      setEnded(false);
      setOpen(true);
    };
    window.addEventListener("bullpug:open-trailer", onOpenEvent);
    return () => window.removeEventListener("bullpug:open-trailer", onOpenEvent);
  }, []);

  useEffect(() => {
    let cancelled = false;
    // Only auto-open if the user has never seen it
    try {
      const seen = localStorage.getItem(STORAGE_KEY);
      if (!seen) {
        // Tiny delay so it doesn't fight the page entry animation
        const t = setTimeout(() => {
          if (!cancelled) setOpen(true);
        }, 600);
        return () => {
          cancelled = true;
          clearTimeout(t);
        };
      }
    } catch (e) {
      /* localStorage blocked — skip */
    }
  }, []);

  // Try to autoplay after the dialog opens
  useEffect(() => {
    if (!open) return;
    const v = videoRef.current;
    if (!v) return;
    v.muted = muted;
    const p = v.play();
    if (p && p.catch) p.catch(() => {});
  }, [open, muted]);

  const dismiss = () => {
    try {
      localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    } catch (e) {
      /* ignore */
    }
    setOpen(false);
  };

  const handleShare = async () => {
    const url = getShareUrl();
    const payload = { title: "Bullpug Origins", text: SHARE_TEXT, url };
    try {
      if (navigator.share && typeof navigator.share === "function") {
        await navigator.share(payload);
        setShared(true);
        setTimeout(() => setShared(false), 2200);
        return;
      }
    } catch (e) {
      /* user dismissed the native sheet — fall through to clipboard */
    }
    try {
      await navigator.clipboard.writeText(`${SHARE_TEXT}\n${url}`);
      setShared(true);
      setTimeout(() => setShared(false), 2200);
    } catch (e) {
      /* clipboard blocked — last resort: open X intent in a new tab */
      const intent = `https://twitter.com/intent/tweet?text=${encodeURIComponent(SHARE_TEXT)}&url=${encodeURIComponent(url)}`;
      window.open(intent, "_blank", "noopener,noreferrer");
    }
  };

  // ESC to close
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") dismiss();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85 backdrop-blur-md animate-[fadeIn_0.4s_ease-out] p-4"
      data-testid="origins-trailer-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Origins Trailer"
    >
      {/* Click outside to dismiss */}
      <button
        type="button"
        aria-label="Close trailer"
        className="absolute inset-0 cursor-default"
        onClick={dismiss}
      />

      <div className="relative w-full max-w-[420px] mx-auto">
        {/* Close button */}
        <button
          type="button"
          onClick={dismiss}
          data-testid="origins-trailer-close"
          className="absolute -top-3 -right-3 z-10 w-10 h-10 rounded-full bg-black border border-white/15 text-white flex items-center justify-center hover:scale-110 transition-transform shadow-lg shadow-black/60"
          aria-label="Close"
        >
          <X size={18} />
        </button>

        {/* Video card */}
        <div className="relative rounded-3xl overflow-hidden border border-[#00FFA3]/30 shadow-[0_0_60px_rgba(0,255,163,0.18)] bg-black aspect-[9/16]">
          <video
            ref={videoRef}
            className="absolute inset-0 w-full h-full object-cover block"
            playsInline
            autoPlay
            muted={muted}
            onEnded={() => setEnded(true)}
            data-testid="origins-trailer-video"
            preload="auto"
          >
            {/* WebM (VP9) listed first — Chromium variants without H.264 licensing
                will pick this up automatically. Safari / iOS fall through to MP4. */}
            <source src="/lore/origins-trailer.webm" type="video/webm" />
            <source src="/lore/origins-trailer.mp4" type="video/mp4" />
          </video>

          {/* Subtle top fade for control contrast */}
          <div className="absolute top-0 inset-x-0 h-20 bg-gradient-to-b from-black/60 to-transparent pointer-events-none" />
          {/* Subtle bottom fade */}
          <div className="absolute bottom-0 inset-x-0 h-32 bg-gradient-to-t from-black/80 to-transparent pointer-events-none" />

          {/* Top-left LIVE tag */}
          <div className="absolute top-3 left-3 inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-black/60 border border-[#00FFA3]/40 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00FFA3] animate-pulse" />
            <span className="text-[9px] uppercase tracking-[0.2em] text-[#00FFA3] font-bold">
              Bullpug Canon
            </span>
          </div>

          {/* Mute toggle */}
          <button
            type="button"
            onClick={() => setMuted((m) => !m)}
            data-testid="origins-trailer-mute"
            className="absolute top-3 right-3 w-9 h-9 rounded-full bg-black/60 border border-white/15 text-white flex items-center justify-center hover:bg-black/80 transition-colors backdrop-blur-sm"
            aria-label={muted ? "Unmute" : "Mute"}
          >
            {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
          </button>

          {/* Bottom overlay: title + CTAs */}
          <div className="absolute bottom-0 inset-x-0 p-5 text-center">
            <p
              className="text-[10px] uppercase tracking-[0.3em] text-[#F5D300] font-bold mb-1"
              style={{ fontFamily: "Space Grotesk, sans-serif" }}
            >
              The Origins
            </p>
            <h3
              className="text-2xl font-black tracking-tighter text-white mb-3"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00FFA3] via-[#D946EF] to-[#FFD700]">
                BULLPUG
              </span>
            </h3>

            <div className="flex items-center justify-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={dismiss}
                data-testid="origins-trailer-cta"
                className="group inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#00FFA3] text-black font-bold text-xs uppercase tracking-wider hover:scale-[1.04] transition-transform shadow-[0_0_24px_rgba(0,255,163,0.35)]"
              >
                {ended ? "Read the lore" : "Enter the canon"}
                <SkipForward size={14} />
              </button>
              <button
                type="button"
                onClick={handleShare}
                data-testid="origins-trailer-share"
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/10 hover:bg-white/15 border border-white/20 text-white font-bold text-xs uppercase tracking-wider transition-colors backdrop-blur-sm"
                aria-live="polite"
              >
                {shared ? (
                  <>
                    <Check size={13} />
                    Copied!
                  </>
                ) : (
                  <>
                    <Share2 size={13} />
                    Share
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Footer hint */}
        <p
          className="text-[10px] text-center text-slate-500 mt-3 tracking-wider uppercase"
          style={{ fontFamily: "Space Grotesk, sans-serif" }}
        >
          {muted ? "Tap the speaker for sound · ESC to skip" : "ESC to skip"}
        </p>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
      `}</style>
    </div>
  );
}
