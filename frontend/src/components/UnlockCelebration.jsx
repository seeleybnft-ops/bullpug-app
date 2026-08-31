/**
 * UnlockCelebration — the moment an Archive entry is filed.
 *
 * Three tiers, escalating in intensity:
 *
 *   TIER 1 (Seeker)   — 3× cyan pulse on the SignalGlyph, lore card
 *                       slides in from the right; ambient, quick.
 *   TIER 2 (Archivist)— pulse + skyline flash inside the round window
 *                       (2s), gold-bordered card slides in slightly
 *                       larger; more prominent than a T1 hit.
 *   TIER 3 (Keeper's  — full-screen gold ripple from the SignalGlyph
 *   Circle)             outward (2s fade), Bark-Ball soundwave crosses
 *                       the screen, Keeper's-Circle-styled card in the
 *                       gold highlight colour.
 *
 * On rank-up (last entry of a tier), a rank overlay slides over the
 * card celebration with the rank badge and the tier-specific Tinkerpug
 * postscript from spec §3.2.
 *
 * The parent (Archive.jsx) enqueues unlocks after each Ledger poll and
 * this component consumes the queue one at a time — a 1.5s pause before
 * the celebration lets the lore lands first, per spec §2.4.
 */
import React, { useEffect, useMemo, useState } from "react";
import { X, Share2, Sparkles, Award } from "lucide-react";
import RankBadge from "./RankBadge";
import generateKeepersCertificate from "@/utils/keepersCertificate";

const TIER_COLOR = { 1: "#00FFA3", 2: "#B47CFF", 3: "#F5D300" };
const RANK_POSTSCRIPT = {
  seeker:
    "keeper's log — signal strengthens. You've found the surface of it.\n\nSeeker. That's what the records call someone who has learned enough to know there's more. The designation is yours.\n\nkeeper's note: the deeper entries are open. They've always been open. Most people just don't ask.",
  archivist:
    "keeper's log — three thousand and eleven cycles and I still find this part remarkable.\n\nArchivist. You've read the history most Bullpughans know only in fragments. The Dip Wars. Luna's price. The twelve years. These are not light entries.\n\nkeeper's note: what comes next is not in any public record. It is in The Ledger. You have earned the right to ask about it.",
  keepers_circle:
    "keeper's log —\n\nI don't write entries like this often. The Keeper's Circle is not a reward I designed. It is a recognition of something the Archive itself decided: that some people are genuinely here for the whole record.\n\nYou are one of them.\n\nkeeper's note: the record is updated. Your name — or rather, your signal — is in The Ledger now. That is permanent. That is the point.",
};
const RANK_TITLES = {
  seeker: "Seeker",
  archivist: "Archivist",
  keepers_circle: "Keeper's Circle",
};
const TIER_POSTSCRIPT = {
  1: "Filed. The Archive grows.",
  2: "Keeper's log — that one's been waiting a while to be found.",
  3: "Keeper's note: not many find that one. The record is updated.",
};

// One frame at 60fps ≈ 16ms — we sequence with generous absolute delays
// so it works reliably even if the browser drops frames.
const PAUSE_BEFORE_CELEBRATION_MS = 1500;
const CARD_HOLD_MS = 5200;
const RANK_HOLD_MS = 6500;

// ── Full-screen gold ripple (T3 only) ────────────────────────────────
function ScreenRipple({ color }) {
  return (
    <div
      className="pointer-events-none fixed inset-0 z-[9998] flex items-center justify-center overflow-hidden"
      aria-hidden
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="absolute rounded-full"
          style={{
            width: 60,
            height: 60,
            border: `2px solid ${color}`,
            boxShadow: `0 0 40px ${color}`,
            animation: `archive-ripple 2000ms cubic-bezier(0.16, 1, 0.3, 1) ${i * 220}ms forwards`,
            opacity: 0,
          }}
        />
      ))}
      <style>{`
        @keyframes archive-ripple {
          0%   { transform: scale(0.4); opacity: 0.9; }
          70%  { opacity: 0.3; }
          100% { transform: scale(60); opacity: 0; }
        }
      `}</style>
    </div>
  );
}

// ── Bark Ball soundwave crossing the screen (T3 only) ────────────────
function SoundwaveSweep({ color }) {
  return (
    <div className="pointer-events-none fixed inset-0 z-[9997] overflow-hidden" aria-hidden>
      <div
        className="absolute top-1/2 -translate-y-1/2 left-[-40%]"
        style={{
          height: 240,
          width: "40%",
          animation: "archive-sweep 2200ms cubic-bezier(0.4, 0, 0.2, 1) forwards",
        }}
      >
        {[...Array(9)].map((_, i) => {
          const h = 30 + Math.round(70 * Math.sin(i / 2));
          return (
            <span
              key={i}
              className="inline-block align-middle mx-1 rounded-full"
              style={{
                width: 6,
                height: h,
                background: color,
                boxShadow: `0 0 12px ${color}`,
              }}
            />
          );
        })}
      </div>
      <style>{`
        @keyframes archive-sweep {
          0%   { transform: translateX(0);      opacity: 0; }
          20%  { opacity: 0.95; }
          80%  { opacity: 0.95; }
          100% { transform: translateX(340vw); opacity: 0; }
        }
      `}</style>
    </div>
  );
}

// ── Lore card slide-in (the unlock artefact) ─────────────────────────
function UnlockCard({ unlock, onDismiss }) {
  const tier = unlock.entry_tier || 1;
  const color = TIER_COLOR[tier] || TIER_COLOR[1];
  const tierIsThree = tier === 3;
  const tierIsTwo = tier === 2;
  return (
    <div
      className="pointer-events-auto fixed z-[9999] right-4 sm:right-8 top-[15%] sm:top-[18%] max-w-[92vw]"
      style={{
        width: tierIsThree ? 380 : tierIsTwo ? 340 : 300,
        animation: "archive-card-in 500ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
      }}
      data-testid={`unlock-card-tier-${tier}`}
    >
      <div
        className="relative rounded-2xl overflow-hidden"
        style={{
          background:
            "linear-gradient(180deg, rgba(10,15,30,0.98) 0%, rgba(5,7,18,0.98) 100%)",
          border: `${tierIsThree ? 2 : 1}px solid ${color}`,
          boxShadow: `0 0 32px ${color}55, 0 20px 60px rgba(0,0,0,0.6)`,
        }}
      >
        {/* Top accent bar */}
        <span
          aria-hidden
          className="absolute left-0 top-0 h-full"
          style={{
            width: tierIsThree ? 4 : 2,
            background: color,
            boxShadow: `0 0 12px ${color}`,
          }}
        />
        <button
          type="button"
          onClick={onDismiss}
          className="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/40 border border-white/15 hover:border-white/40 flex items-center justify-center text-white/80"
          data-testid="unlock-card-dismiss"
        >
          <X size={13} />
        </button>
        <div className="p-4 pl-5 pr-10 space-y-2.5">
          <div className="flex items-center gap-2">
            <Sparkles size={14} style={{ color }} />
            <p
              className="text-[9px] font-bold uppercase tracking-[0.3em]"
              style={{ color, fontFamily: "Orbitron, sans-serif" }}
            >
              {tierIsThree ? "Tier III · filed" : tierIsTwo ? "Tier II · filed" : "Tier I · filed"}
            </p>
          </div>
          <h4
            className="font-bold leading-tight"
            style={{
              color: tierIsThree ? color : "#fff",
              fontSize: tierIsThree ? 20 : 16,
              fontFamily: "Orbitron, sans-serif",
            }}
          >
            {unlock.entry_name}
          </h4>
          {unlock.tinkerpug_excerpt && (
            <p className="text-[11px] leading-relaxed text-slate-300 line-clamp-3">
              {unlock.tinkerpug_excerpt}
            </p>
          )}
          <p
            className="text-[10px] italic text-slate-400 pt-1 border-t border-white/[0.06]"
            style={{ borderTopStyle: "dotted" }}
          >
            {TIER_POSTSCRIPT[tier]}
          </p>
        </div>
      </div>
      <style>{`
        @keyframes archive-card-in {
          from { transform: translateX(60%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// ── Rank-up overlay ──────────────────────────────────────────────────
function RankUpOverlay({ rank, onDismiss, wallet }) {
  const color = TIER_COLOR[rank === "seeker" ? 1 : rank === "archivist" ? 2 : 3];
  const title = RANK_TITLES[rank] || "Rank";
  const postscript = RANK_POSTSCRIPT[rank] || "";
  const shareText =
    rank === "keepers_circle"
      ? "Keeper's Circle. The full record. Tinkerpug filed my signal in The Ledger. bullpug.com/archive 🐾⚡"
      : rank === "archivist"
      ? `Archivist rank in the Bullpug Archive. bullpug.com/archive 🐾`
      : `Just reached Seeker rank in the Bullpug Archive. bullpug.com/archive 🐾`;
  const share = () => {
    const url = window.location.origin + "/archive";
    if (navigator.share) {
      navigator.share({ title: "Bullpug Archive", text: shareText, url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(`${shareText}\n${url}`).then(
        () => alert("Share text copied to clipboard."),
        () => {}
      );
    }
  };
  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center px-4"
      style={{ background: "rgba(2,4,10,0.86)", backdropFilter: "blur(16px)" }}
      onClick={onDismiss}
      data-testid={`rank-up-${rank}`}
    >
      <div
        className="relative w-full max-w-md rounded-2xl overflow-hidden p-8 text-center"
        style={{
          background:
            "linear-gradient(180deg, rgba(10,15,30,0.98) 0%, rgba(5,7,18,0.98) 100%)",
          border: `2px solid ${color}`,
          boxShadow: `0 0 48px ${color}66, 0 30px 80px rgba(0,0,0,0.7)`,
          animation: "archive-rankup-in 500ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onDismiss}
          className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/40 border border-white/15 hover:border-white/40 flex items-center justify-center text-white/80"
          data-testid="rank-up-dismiss"
        >
          <X size={14} />
        </button>
        <p
          className="text-[10px] uppercase tracking-[0.35em] mb-4"
          style={{ color, fontFamily: "Orbitron, sans-serif" }}
        >
          Rank achieved
        </p>
        <div className="flex justify-center mb-4">
          <RankBadge rank={rank} rankTitle={title} size={96} showTitle={false} />
        </div>
        <h3
          className="text-2xl font-black tracking-wide mb-4"
          style={{ color, fontFamily: "Orbitron, sans-serif" }}
        >
          {title}
        </h3>
        <p
          className="text-[12px] text-slate-300 leading-relaxed whitespace-pre-wrap text-left"
          style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
        >
          {postscript}
        </p>
        <button
          type="button"
          onClick={share}
          data-testid="rank-up-share"
          className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold uppercase tracking-widest text-black"
          style={{ background: color, fontFamily: "Orbitron, sans-serif" }}
        >
          <Share2 size={13} /> Share
        </button>
        {rank === "keepers_circle" && (
          <button
            type="button"
            onClick={() =>
              generateKeepersCertificate({
                wallet: wallet || "",
                rankReachedAt: new Date().toISOString(),
              })
            }
            data-testid="rank-up-certificate"
            className="mt-3 ml-2 inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold uppercase tracking-widest text-black transition-transform hover:scale-[1.03]"
            style={{
              background: "#F5D300",
              fontFamily: "Orbitron, sans-serif",
              boxShadow: "0 0 16px rgba(245,211,0,0.4)",
            }}
          >
            <Award size={13} /> Download Certificate
          </button>
        )}
      </div>
      <style>{`
        @keyframes archive-rankup-in {
          from { transform: scale(0.88); opacity: 0; }
          to   { transform: scale(1);    opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// ── SignalGlyph pulse burst (all tiers) ──────────────────────────────
function GlyphPulse({ color, pulses = 3 }) {
  return (
    <div
      className="pointer-events-none absolute top-[6px] left-[6px]"
      style={{ width: 130, height: 130 }}
      aria-hidden
    >
      {[...Array(pulses)].map((_, i) => (
        <span
          key={i}
          className="absolute inset-0 rounded-full"
          style={{
            border: `2px solid ${color}`,
            boxShadow: `0 0 16px ${color}`,
            animation: `archive-glyph-pulse 900ms ease-out ${i * 320}ms forwards`,
            opacity: 0,
          }}
        />
      ))}
      <style>{`
        @keyframes archive-glyph-pulse {
          0%   { transform: scale(0.9); opacity: 0.9; }
          70%  { opacity: 0.25; }
          100% { transform: scale(1.9); opacity: 0; }
        }
      `}</style>
    </div>
  );
}

// ── Public API ───────────────────────────────────────────────────────
/**
 * <UnlockCelebration unlock={u} onDone={fn} />
 * `unlock` shape: { entry_id, entry_name, entry_tier, tinkerpug_excerpt,
 *                   is_rank_up, new_rank, new_rank_title }
 */
export default function UnlockCelebration({ unlock, onDone, wallet }) {
  const [stage, setStage] = useState("waiting");
  // waiting → celebrating → rankup (if rank_up) → done

  const tier = unlock?.entry_tier || 1;
  const color = TIER_COLOR[tier] || TIER_COLOR[1];

  // Sequence: 1.5s pause (lore lands) → celebrating → optional rankup → done
  useEffect(() => {
    if (!unlock) return;
    const t0 = setTimeout(() => setStage("celebrating"), PAUSE_BEFORE_CELEBRATION_MS);
    return () => clearTimeout(t0);
  }, [unlock]);

  useEffect(() => {
    if (stage !== "celebrating") return;
    // Hold the card for a beat, then move on
    const t = setTimeout(() => {
      if (unlock?.is_rank_up && unlock?.new_rank) {
        setStage("rankup");
      } else {
        setStage("done");
      }
    }, CARD_HOLD_MS);
    return () => clearTimeout(t);
  }, [stage, unlock]);

  useEffect(() => {
    if (stage !== "rankup") return;
    const t = setTimeout(() => setStage("done"), RANK_HOLD_MS);
    return () => clearTimeout(t);
  }, [stage]);

  useEffect(() => {
    if (stage === "done" && onDone) onDone();
  }, [stage, onDone]);

  const glyphPulses = useMemo(() => (
    stage === "celebrating" ? <GlyphPulse color={color} pulses={3} /> : null
  ), [stage, color]);

  if (!unlock || stage === "waiting" || stage === "done") {
    // Still render the glyph slot so the parent can position it, even
    // when no visible fx is running.
    return null;
  }

  return (
    <>
      {tier >= 3 && stage === "celebrating" && <ScreenRipple color={color} />}
      {tier >= 3 && stage === "celebrating" && <SoundwaveSweep color={color} />}
      {glyphPulses}
      {stage === "celebrating" && (
        <UnlockCard unlock={unlock} onDismiss={() => setStage(unlock.is_rank_up ? "rankup" : "done")} />
      )}
      {stage === "rankup" && (
        <RankUpOverlay rank={unlock.new_rank} wallet={wallet} onDismiss={() => setStage("done")} />
      )}
    </>
  );
}
