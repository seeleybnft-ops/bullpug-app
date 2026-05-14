/**
 * TinkerpugCodex — unobtrusive companion pane for the AI chat that tracks
 * which Archive entries the user has unlocked through conversation.
 *
 * Detection: a static set of unlock keywords per entry. Whenever any
 * assistant message mentions a keyword for an entry, that entry flips from
 * locked → unlocked and gets persisted to localStorage. The pane itself is
 * toggled via a header button (BookOpen) and is fully collapsible so it
 * never crowds the regular chat experience.
 */

import { useEffect, useMemo, useState } from "react";
import { BookOpen, Lock, Sparkles, X } from "lucide-react";

// id ↔ display + match rules. Keep these light — we want false-positives to
// be rare. All keywords are checked case-insensitively against the joined
// text of every assistant message in the session.
export const CODEX_ENTRIES = [
  {
    id: "entry_zero_nebula",
    title: "Entry Zero · The Enlightenment Nebula",
    sub: "What Bullpug faced before he became what he is",
    keywords: ["enlightenment nebula", "three illusions", "elder moons"],
    tier: 2,
  },
  {
    id: "entry_one_first_crossing",
    title: "Entry One · The First Crossing",
    sub: "The signal that started everything",
    keywords: ["first crossing", "i didn't quit", "i did not quit", "first crosser"],
    tier: 2,
  },
  {
    id: "feat_bear_not_break",
    title: "Feat I · The Bear That Would Not Break",
    sub: "The longest siege the PugChain ever held",
    keywords: ["bear that would not break", "siege of the pugchain"],
    tier: 2,
  },
  {
    id: "feat_forgotten_wallet",
    title: "Feat II · The Guardian of the Forgotten Wallet",
    sub: "Every wallet matters — even the silent ones",
    keywords: ["forgotten wallet", "guardian of the forgotten"],
    tier: 2,
  },
  {
    id: "feat_pugchain_held",
    title: "Feat III · The Night the PugChain Held",
    sub: "Why the Guardians stand together",
    keywords: ["night the pugchain held", "pugchain held"],
    tier: 2,
  },
  {
    id: "feat_siren_scams",
    title: "Feat VI · The Siren Scams of the Forbidden Fork",
    sub: "Seventeen loops, one bark, the oldest coordinated scam in the Fork",
    keywords: [
      "siren scams",
      "the sirens",
      "seventeen loops",
      "seventeen independent",
      "forbidden fork",
      "this is also what community sounds like",
    ],
    tier: 2,
  },
  {
    id: "guardian_chargebull",
    title: "Guardian · Chargebull",
    sub: "The protector who answers first",
    keywords: ["chargebull"],
    tier: 1,
  },
  {
    id: "guardian_ruffus",
    title: "Guardian · Ruffus the Sage",
    sub: "Sees market cycles the rest can't",
    keywords: ["ruffus"],
    tier: 1,
  },
  {
    id: "guardian_luna",
    title: "Guardian · Luna the Visionary",
    sub: "Reads the chain's tomorrow",
    keywords: ["luna the visionary", "luna"],
    tier: 1,
  },
  {
    id: "guardian_grizzlor",
    title: "Guardian · Grizzlor",
    sub: "Reformed shadow — kept watch from the other side",
    keywords: ["grizzlor", "gideon"],
    tier: 1,
  },
  {
    id: "lore_horn_of_hodl",
    title: "Artifact · The Horn of HODL",
    sub: "The signal that calls Bullpughans to defend",
    keywords: ["horn of hodl"],
    tier: 2,
  },
  {
    id: "lore_convergence",
    title: "Prophecy · The Grand Convergence",
    sub: "Only spoken of in hints",
    keywords: ["grand convergence"],
    tier: 2,
  },
  {
    id: "lore_architect",
    title: "Deep · The Architect",
    sub: "The bad actor still operating in the dark",
    keywords: ["the architect"],
    tier: 3,
  },
];

const STORAGE_KEY = "bullpug_tinkerpug_codex_v1";

function loadUnlocked() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr : []);
  } catch (e) { return new Set(); }
}

function persist(set) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify([...set])); } catch (e) { /* ignore */ }
}

/** Scan the joined assistant-message text against every entry's keyword
 *  list. Returns the set of entry IDs that should be flagged unlocked. */
export function detectUnlocked(messages, prior = new Set()) {
  const merged = new Set(prior);
  const blob = messages
    .filter((m) => m && m.role === "assistant" && typeof m.content === "string")
    .map((m) => m.content.toLowerCase())
    .join("\n");
  if (!blob) return merged;
  for (const entry of CODEX_ENTRIES) {
    if (merged.has(entry.id)) continue;
    if (entry.keywords.some((k) => blob.includes(k))) merged.add(entry.id);
  }
  return merged;
}

export function CodexButton({ unlockedCount, open, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid="tinkerpug-codex-toggle"
      title={open ? "Close Codex" : `Codex · ${unlockedCount} unlocked`}
      className={`relative p-1.5 rounded-lg transition-colors ${
        open
          ? "bg-[#F5D300]/20 text-[#F5D300]"
          : "hover:bg-white/10 text-slate-400 hover:text-white"
      }`}
    >
      <BookOpen className="w-4 h-4" />
      {unlockedCount > 0 && !open && (
        <span className="absolute -top-1 -right-1 min-w-[14px] h-[14px] px-1 rounded-full bg-[#F5D300] text-black text-[9px] font-black flex items-center justify-center">
          {unlockedCount}
        </span>
      )}
    </button>
  );
}

export default function TinkerpugCodex({ messages, open, onClose }) {
  const [unlocked, setUnlocked] = useState(() => loadUnlocked());

  // Whenever new assistant messages land, rescan and persist new unlocks.
  useEffect(() => {
    setUnlocked((prev) => {
      const next = detectUnlocked(messages || [], prev);
      if (next.size !== prev.size) persist(next);
      return next;
    });
  }, [messages]);

  const grouped = useMemo(() => {
    return CODEX_ENTRIES.map((e) => ({ ...e, unlockedYet: unlocked.has(e.id) }));
  }, [unlocked]);

  if (!open) return null;

  const unlockedCount = grouped.filter((e) => e.unlockedYet).length;
  const totalCount = grouped.length;

  return (
    <div
      className="absolute inset-x-0 top-[60px] bottom-0 z-20 bg-[#0a0a13]/98 backdrop-blur-md border-t border-[#F5D300]/20 flex flex-col"
      data-testid="tinkerpug-codex-pane"
    >
      <div className="px-4 py-2.5 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-[#F5D300]" />
          <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#F5D300]" style={{ fontFamily: "Orbitron" }}>
            The Ledger · Codex
          </span>
          <span className="text-[10px] text-slate-500 tabular-nums">{unlockedCount}/{totalCount}</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          data-testid="tinkerpug-codex-close"
          className="p-1 rounded-md hover:bg-white/10 text-slate-400 hover:text-white"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5">
        {grouped.map((entry) => (
          <div
            key={entry.id}
            data-testid={`codex-entry-${entry.id}`}
            data-unlocked={entry.unlockedYet ? "1" : "0"}
            className={`rounded-lg border px-3 py-2 transition-colors ${
              entry.unlockedYet
                ? "bg-[#F5D300]/[0.06] border-[#F5D300]/25"
                : "bg-white/[0.02] border-white/[0.05]"
            }`}
          >
            <div className="flex items-start gap-2.5">
              <div className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5 ${
                entry.unlockedYet ? "bg-[#F5D300]/20 text-[#F5D300]" : "bg-white/5 text-slate-600"
              }`}>
                {entry.unlockedYet ? <BookOpen className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
              </div>
              <div className="min-w-0 flex-1">
                <p className={`text-[11px] font-bold leading-snug ${entry.unlockedYet ? "text-white" : "text-slate-500"}`}>
                  {entry.unlockedYet ? entry.title : "—  Sealed entry  —"}
                </p>
                <p className={`text-[10px] mt-0.5 ${entry.unlockedYet ? "text-slate-400" : "text-slate-600 italic"}`}>
                  {entry.unlockedYet ? entry.sub : "Pull the thread to reveal"}
                </p>
              </div>
              {entry.tier && entry.unlockedYet && (
                <span className={`text-[9px] uppercase tracking-wider font-bold flex-shrink-0 ${
                  entry.tier === 3 ? "text-[#D946EF]" : entry.tier === 2 ? "text-[#00FFA3]" : "text-slate-500"
                }`}>
                  T{entry.tier}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <p className="px-4 py-2 text-[10px] text-slate-500 text-center border-t border-white/5">
        Entries unlock automatically as Tinkerpug reveals them.
      </p>
    </div>
  );
}
