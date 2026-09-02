/**
 * Archive — Tinkerpug's workspace.
 *
 * NOT a chat UI. A place. Deep indigo substrate-layer aesthetic, faint
 * cyan grid lines, instrument readouts along the edges, a round window
 * in the upper-left with the Newpug City skyline behind it. Tinkerpug's
 * avatar sits INSIDE the workspace beside his responses — not a
 * floating bubble.
 *
 * Layout:
 *   • Desktop (≥1024px): two-panel split — 60% workspace / 40% Ledger
 *   • Mobile: two tabs — "Speak with the Keeper" / "Your Ledger"
 *     (Ledger becomes default on return visits with unlocks)
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useSearchParams } from "react-router-dom";
import { Send, Loader2, Radio, MessageCircle, BookOpen, LogOut } from "lucide-react";
import ArchiveLedger from "@/components/ArchiveLedger";
import UnlockCelebration from "@/components/UnlockCelebration";
import { useAuth } from "@/contexts/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
// Small circular avatar next to Tinkerpug's responses in the Archive
// workspace. Points at the canonical Imgur-hosted reference so the
// avatar tracks the same source of truth used by the daily drop and
// image-gen pipelines (see backend/services/image_references.py).
// Feb 2026 Character Expansion v1.0 — swapped to IVCxhIp reference.
const TINKERPUG_AVATAR = "https://i.imgur.com/IVCxhIp.jpeg";

// Deterministic session id per browser tab so `chat_history` on the
// backend stays coherent across the visit but never leaks between tabs.
function useSessionId() {
  const [id] = useState(() => {
    const key = "bullpug_archive_session";
    let existing = null;
    try {
      existing = sessionStorage.getItem(key);
    } catch {
      /* private mode */
    }
    if (existing) return existing;
    const fresh = `archive-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
    try {
      sessionStorage.setItem(key, fresh);
    } catch {
      /* ignore */
    }
    return fresh;
  });
  return id;
}

function shortWallet(w) {
  if (!w) return "guest.station";
  const s = String(w);
  if (s.length <= 10) return s;
  return `${s.slice(0, 4)}…${s.slice(-4)}`;
}

// Privacy shortener for email — never render a full address in the UI
// (spec Compliance Note: "Email addresses are not included in The
// Record leaderboard display; use shortened format ben@..."). Mirrors
// the wallet shorthand in size + shape so the header layout is
// symmetric regardless of auth type.
function shortenEmail(email) {
  if (!email) return "keeper";
  const [local, domain] = String(email).split("@");
  if (!domain) return email;
  const head = local.length <= 4 ? local : `${local.slice(0, 3)}…`;
  return `${head}@${domain.replace(/^([^.]+).*/, "$1")}…`;
}

// The ambient "keeper's log — new presence detected" first-visit greeting.
const FIRST_VISIT_GREETING = [
  "keeper's log — new presence detected on the channel.",
  "",
  "I'm Tinkerpug. I keep the chain, the Genesis Vault, and The Ledger — the complete record of everything the PugChain has ever needed someone to remember.",
  "",
  "The Archive is open. Ask me anything.",
  "",
  "keeper's note: the deeper you dig, the more it gives back.",
].join("\n");

const RETURN_GREETING_FALLBACK =
  "keeper's log — familiar signal on the channel. Back at the station.";

// Minimal markdown → HTML. Just bold/italic/newlines — enough for
// Tinkerpug's voice. Everything else renders as plain text so nothing
// crashes on unexpected input.
function renderMarkdown(text) {
  if (!text) return null;
  const esc = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const html = esc
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, '<code class="px-1 rounded bg-white/10 text-cyan-300">$1</code>')
    .replace(/\n/g, "<br />");
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

// ── Ambient decorative pieces ─────────────────────────────────────────
// Deterministic pseudo-random hash-like strings for the scrolling data
// columns. The seed is a per-mount random offset so different tabs
// don't display identical text, but each column stays the same across
// re-renders. Kept short so nothing legible ever competes with the
// chat text — the columns read as texture, not content.
function makeHashStrip(seed) {
  const chars = "0123456789abcdef";
  const lines = [];
  // 24 lines per strip is more than enough vertical density; the CSS
  // animation duplicates the strip via a second copy for a seamless
  // loop, so effective density doubles.
  for (let i = 0; i < 24; i += 1) {
    // Vary the shape: some full-hash lines (14 chars), some block-
    // number lines (7-digit), some transaction snippet lines (label
    // + short hash) so it doesn't read as one homogeneous grid.
    const roll = (seed * 9301 + 49297 + i * 233) % 3;
    if (roll === 0) {
      let s = "0x";
      for (let j = 0; j < 12; j += 1) {
        s += chars[(seed + i * 17 + j * 7) % chars.length];
      }
      lines.push(s);
    } else if (roll === 1) {
      const num = ((seed + i * 419) * 7919) % 9_999_999;
      lines.push(`blk ${String(num).padStart(7, "0")}`);
    } else {
      let s = "tx·";
      for (let j = 0; j < 6; j += 1) {
        s += chars[(seed + i * 29 + j * 11) % chars.length];
      }
      lines.push(s);
    }
  }
  return lines;
}

function DataFlowLayer() {
  // Six evenly-spaced columns spanning the panel width. Duration and
  // vertical offset differ per column so the flow never looks like a
  // single sheet. Opacity is intentionally 8-10% (CSS variable) so
  // the layer stays sub-perceptual against the text foreground.
  const columns = useMemo(
    () =>
      Array.from({ length: 6 }, (_, i) => ({
        seed: 991 + i * 197,
        left: `${8 + i * 15}%`,
        duration: 42 + (i % 3) * 14, // 42s / 56s / 70s — long, ambient
        delay: -(i * 7), // stagger so pulses don't align
      })),
    []
  );

  // Two horizontal data pulses cross the panel. Long durations + a
  // negative delay on the second line so they fire at different
  // moments — the spec wants "irregular intervals", not a metronome.
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden>
      {/* Column flow */}
      {columns.map((c, idx) => {
        const strip = makeHashStrip(c.seed);
        return (
          <div
            key={idx}
            className="absolute top-0 flex flex-col"
            style={{
              left: c.left,
              transform: "translateX(-50%)",
              width: 92,
              color: "rgba(0,255,200,0.55)",
              opacity: 0.09,
              fontFamily: "monospace",
              fontSize: 10,
              lineHeight: "16px",
              letterSpacing: "0.06em",
              animation: `archive-flow ${c.duration}s linear ${c.delay}s infinite`,
              willChange: "transform",
            }}
          >
            {/* Duplicate the strip once so the loop wraps seamlessly */}
            {[...strip, ...strip].map((line, li) => (
              <span key={li} className="truncate">
                {line}
              </span>
            ))}
          </div>
        );
      })}

      {/* Horizontal data pulses — two independent lines with prime-ish
          durations so they never re-align. */}
      <div
        className="absolute left-0 right-0"
        style={{
          top: "38%",
          height: 1,
          background:
            "linear-gradient(90deg, transparent 0%, rgba(0,255,200,0.6) 50%, transparent 100%)",
          opacity: 0.35,
          animation: "archive-pulse-h 17s ease-in-out infinite",
          willChange: "transform, opacity",
        }}
      />
      <div
        className="absolute left-0 right-0"
        style={{
          top: "72%",
          height: 1,
          background:
            "linear-gradient(90deg, transparent 0%, rgba(0,194,255,0.55) 50%, transparent 100%)",
          opacity: 0.3,
          animation: "archive-pulse-h 23s ease-in-out -9s infinite",
          willChange: "transform, opacity",
        }}
      />

      {/* Node pulses — three positions cycled every ~30s so a soft
          circular ripple always looks like it fired from somewhere
          new. */}
      <div
        className="absolute rounded-full"
        style={{
          top: "22%",
          left: "70%",
          width: 220,
          height: 220,
          transform: "translate(-50%,-50%)",
          border: "1px solid rgba(0,255,200,0.35)",
          opacity: 0,
          animation: "archive-node-pulse 34s ease-out 0s infinite",
        }}
      />
      <div
        className="absolute rounded-full"
        style={{
          top: "80%",
          left: "40%",
          width: 220,
          height: 220,
          transform: "translate(-50%,-50%)",
          border: "1px solid rgba(0,194,255,0.32)",
          opacity: 0,
          animation: "archive-node-pulse 34s ease-out -11s infinite",
        }}
      />
      <div
        className="absolute rounded-full"
        style={{
          top: "54%",
          left: "18%",
          width: 220,
          height: 220,
          transform: "translate(-50%,-50%)",
          border: "1px solid rgba(180,124,255,0.3)",
          opacity: 0,
          animation: "archive-node-pulse 34s ease-out -22s infinite",
        }}
      />

      {/* Keyframes — scoped to the component. Duplication is fine;
          the browser dedupes matching @keyframes. */}
      <style>{`
        @keyframes archive-flow {
          0%   { transform: translate(-50%, -50%); }
          100% { transform: translate(-50%, 0%); }
        }
        @keyframes archive-pulse-h {
          0%,  100% { opacity: 0; transform: translateX(-40%); }
          40%       { opacity: 0.45; }
          50%       { opacity: 0.55; transform: translateX(0); }
          60%       { opacity: 0.45; }
          80%       { opacity: 0; transform: translateX(40%); }
        }
        @keyframes archive-node-pulse {
          0%   { opacity: 0; transform: translate(-50%, -50%) scale(0.4); }
          6%   { opacity: 0.55; }
          12%  { opacity: 0; transform: translate(-50%, -50%) scale(1.6); }
          100% { opacity: 0; transform: translate(-50%, -50%) scale(1.6); }
        }
      `}</style>
    </div>
  );
}

function WorkspaceBackground() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden>
      {/* Deep indigo base */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at top left, rgba(20,32,64,0.9) 0%, rgba(5,7,18,1) 55%, #05050A 100%)",
        }}
      />
      {/* PugChain data flow — hashes / block numbers / tx snippets +
          horizontal pulses + soft node pulses. Sits between the base
          and the grid so grid + instrument readouts still read clean. */}
      <DataFlowLayer />
      {/* Cyan grid — faint, generous spacing so it reads as ambient not busy */}
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,255,163,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,163,0.5) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)",
        }}
      />
      {/* Round window — upper-left, Newpug City skyline hint */}
      <div
        className="absolute top-8 left-6 rounded-full"
        style={{
          width: 130,
          height: 130,
          background:
            "radial-gradient(circle at 30% 45%, rgba(0,194,255,0.35) 0%, rgba(0,42,90,0.6) 45%, rgba(5,7,18,0.95) 90%)",
          border: "1px solid rgba(0,194,255,0.35)",
          boxShadow: "inset 0 0 24px rgba(0,194,255,0.2), 0 0 32px rgba(0,194,255,0.08)",
        }}
      />
      {/* Skyline silhouette inside the window */}
      <svg
        className="absolute top-[70px] left-[24px]"
        width="100" height="46" viewBox="0 0 100 46"
        style={{ opacity: 0.75, mixBlendMode: "screen" }}
      >
        <defs>
          <linearGradient id="skyline" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00C2FF" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#00C2FF" stopOpacity="0.3" />
          </linearGradient>
        </defs>
        <path
          fill="url(#skyline)"
          d="M0 46 L0 30 L8 30 L8 22 L14 22 L14 26 L20 26 L20 12 L26 12 L26 20 L34 20 L34 8 L42 8 L42 18 L50 18 L50 4 L58 4 L58 14 L64 14 L64 24 L72 24 L72 16 L80 16 L80 28 L88 28 L88 20 L96 20 L96 30 L100 30 L100 46 Z"
        />
      </svg>
      <p
        className="absolute top-[152px] left-8 text-[8px] uppercase tracking-[0.4em] text-cyan-300/60"
        style={{ fontFamily: "monospace" }}
      >
        newpug city · substrate lvl
      </p>

      {/* Instrument readout — right edge, running vertical */}
      <div
        className="absolute right-4 top-24 flex flex-col gap-3 text-[8px] uppercase tracking-[0.35em] text-cyan-300/40"
        style={{ fontFamily: "monospace", writingMode: "vertical-rl" }}
      >
        <span>pugchain sync · nominal</span>
        <span>archive integrity · 100%</span>
        <span>keeper station 001</span>
      </div>

      {/* Bottom-edge readout */}
      <div
        className="absolute bottom-3 left-6 right-6 flex justify-between text-[8px] uppercase tracking-[0.35em] text-cyan-300/25"
        style={{ fontFamily: "monospace" }}
      >
        <span>vault sealed</span>
        <span>signal · in the noise</span>
        <span>the ledger holds</span>
      </div>
    </div>
  );
}

function Avatar({ small = false }) {
  const size = small ? 32 : 44;
  return (
    <div
      className="relative flex-shrink-0 rounded-full overflow-hidden"
      style={{
        width: size,
        height: size,
        border: "1px solid rgba(0,255,163,0.35)",
        boxShadow: "0 0 12px rgba(0,255,163,0.18)",
      }}
    >
      <img src={TINKERPUG_AVATAR} alt="Tinkerpug" className="w-full h-full object-cover" />
    </div>
  );
}

// ── The workspace chat panel ──────────────────────────────────────────
// sessionStorage key for the message log — one entry per wallet (or
// `guest` for pre-connect visitors). sessionStorage means the log
// clears on tab close, which is what we want: a fresh tab starts fresh,
// but SPA navigation between /archive and any other page preserves the
// conversation.
function conversationStorageKey(wallet) {
  return `archive_conversation_${wallet || "guest"}`;
}

function loadPersistedMessages(wallet) {
  try {
    const raw = sessionStorage.getItem(conversationStorageKey(wallet));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length === 0) return null;
    return parsed;
  } catch {
    return null;
  }
}

function Workspace({ wallet, onAssistantReply, promptRequest }) {
  const { walletAddress: realWallet, authHeaders } = useAuth();
  // `?wallet=<addr>` is only appended when there's a REAL Solana wallet —
  // never for email users (their user_id UUID would leak in URLs).
  const walletUrlParam = realWallet ? `?wallet=${encodeURIComponent(realWallet)}` : "";
  const fetchOpts = useMemo(() => ({ headers: authHeaders }), [authHeaders]);
  const sessionId = useSessionId();
  // Lazy-init from sessionStorage so we don't flash the greeting on
  // remount. Falls back to the first-visit greeting if nothing is
  // stored yet for this wallet.
  const [messages, setMessages] = useState(() => {
    const persisted = loadPersistedMessages(wallet);
    if (persisted) return persisted;
    return [{ role: "assistant", content: FIRST_VISIT_GREETING, isGreeting: true }];
  });
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const isReturnGreetedRef = useRef(false);

  // When the wallet changes (connect/disconnect after mount), swap in
  // the persisted log for that identity if one exists — otherwise
  // leave the current thread in place so the visitor's guest chat
  // isn't lost on wallet connect. Also skip if the two logs are the
  // same instance (prevents needless re-render).
  useEffect(() => {
    const persisted = loadPersistedMessages(wallet);
    if (persisted) {
      setMessages(persisted);
      // A restored session should NOT re-greet — the "familiar signal"
      // effect below is short-circuited.
      isReturnGreetedRef.current = true;
    }
    // If no persisted log AND we're switching wallets, leave the
    // existing messages so a guest that connects mid-conversation
    // keeps their chat. The subsequent send will persist under the
    // wallet key.
  }, [wallet]);

  // Persist on every change. Skip the initial greeting-only state to
  // keep the storage clean.
  useEffect(() => {
    try {
      if (
        messages.length === 1 &&
        messages[0].isGreeting &&
        messages[0].content === FIRST_VISIT_GREETING
      ) {
        return;
      }
      sessionStorage.setItem(conversationStorageKey(wallet), JSON.stringify(messages));
    } catch {
      /* quota / private mode — silent */
    }
  }, [messages, wallet]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  // Any prompt-focus request from a locked-lore modal — set the input
  // and focus. We watch `.id` so repeat requests for the same prompt
  // still trigger.
  useEffect(() => {
    if (!promptRequest || !promptRequest.text) return;
    setInput(promptRequest.text);
    // Wait a tick for the mobile tab to swap in and the textarea to
    // mount, then focus + move caret to the end.
    const t = setTimeout(() => {
      const el = inputRef.current;
      if (!el) return;
      el.focus();
      try {
        el.setSelectionRange(promptRequest.text.length, promptRequest.text.length);
      } catch {
        /* some browsers reject on unfocused textareas */
      }
    }, 60);
    return () => clearTimeout(t);
  }, [promptRequest]);

  // On wallet-connect after first visit, swap the greeting for the return
  // form once we know the rank. Fire-and-forget — chat continues without.
  useEffect(() => {
    if (!wallet || isReturnGreetedRef.current) return;
    isReturnGreetedRef.current = true;
    fetch(`${API}/archive/rank${walletUrlParam}`, fetchOpts)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data || data.unlocked_count === 0) return;
        const title = data.rank_title || "Signal";
        setMessages((prev) => {
          if (prev.length !== 1 || !prev[0].isGreeting) return prev;
          return [
            {
              role: "assistant",
              content: `keeper's log — familiar signal on the channel. ${title} back again.`,
              isGreeting: true,
            },
          ];
        });
      })
      .catch(() => {});
  }, [wallet]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    setInput("");
    const nextMsgs = [...messages, { role: "user", content: text }];
    setMessages(nextMsgs);

    try {
      const chatHistory = nextMsgs
        .filter((m) => !m.isGreeting && !m.isError)
        .slice(-20)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API}/ai/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Bullpug-CSRF": "1",
          ...authHeaders,
        },
        body: JSON.stringify({
          session_id: sessionId,
          // For email users we send the JWT via Authorization header and
          // leave `wallet_address` null — the backend's chat pipeline
          // reads the header (via the same identity resolver) and pins
          // the session to the user_id.
          wallet_address: realWallet || null,
          message: text,
          chat_history: chatHistory,
        }),
      });
      const data = await res.json().catch(() => ({}));
      const assistantText =
        data.response ||
        "Signal's noisy on the substrate. Try again in a moment.";
      const nextMessage = {
        role: "assistant",
        content: assistantText,
        image: data.image_base64 || null,
        kind: data.kind || "text",
        // Supplemental image — attached when the user asked what
        // something looks like. Renders BELOW the text bubble, never
        // replaces it. See services/visual_intent.py on the backend.
        supplemental_image: data.supplemental_image || null,
      };
      setMessages((prev) => [...prev, nextMessage]);
      // Signal upstream so the Ledger panel can re-poll for unlocks
      onAssistantReply?.();
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "The channel dropped. Try that again in a moment.",
          isError: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  }, [input, sending, messages, sessionId, wallet, onAssistantReply]);

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="relative h-full flex flex-col" data-testid="archive-workspace">
      <WorkspaceBackground />

      {/* Message scroll region */}
      <div
        ref={scrollRef}
        className="relative flex-1 overflow-y-auto p-5 sm:p-8 pt-[176px] sm:pt-[192px] space-y-6"
        data-testid="archive-messages"
      >
        {messages.map((m, i) => {
          if (m.role === "user") {
            return (
              <div key={i} className="flex justify-end" data-testid="msg-user">
                <div
                  className="max-w-[80%] rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-white/95"
                  style={{
                    background: "rgba(0,255,163,0.12)",
                    border: "1px solid rgba(0,255,163,0.28)",
                  }}
                >
                  {renderMarkdown(m.content)}
                </div>
              </div>
            );
          }
          return (
            <div key={i} className="flex gap-3 items-start" data-testid="msg-assistant">
              <Avatar />
              <div className="flex-1 min-w-0">
                <p
                  className="text-[9px] uppercase tracking-[0.3em] mb-1.5 text-cyan-300/70"
                  style={{ fontFamily: "monospace" }}
                >
                  keeper station · {shortWallet(wallet)}
                </p>
                <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {renderMarkdown(m.content)}
                </div>
                {m.image && (
                  <img
                    src={m.image}
                    alt="Archive record"
                    className="mt-3 rounded-xl border border-cyan-300/25 max-w-md"
                  />
                )}
                {/* Supplemental image — inline card BELOW the text
                    response when Tinkerpug pulled a matching visual
                    from the Archive. Always additive, never a
                    replacement. */}
                {m.supplemental_image && m.supplemental_image.image_base64 && (
                  <div
                    className="mt-3 rounded-xl border overflow-hidden max-w-md"
                    style={{ borderColor: "rgba(180,124,255,0.35)", background: "rgba(180,124,255,0.05)" }}
                    data-testid="msg-supplemental-image"
                  >
                    <img
                      src={m.supplemental_image.image_base64}
                      alt={`Archive visual — ${m.supplemental_image.subject}`}
                      className="w-full"
                    />
                    <div
                      className="px-3 py-2 text-[10px] uppercase tracking-widest flex items-center gap-2"
                      style={{ color: "#B47CFF", fontFamily: "Orbitron, sans-serif", background: "rgba(0,0,0,0.35)" }}
                    >
                      <span>{m.supplemental_image.caption || "Direct from the Archive."}</span>
                      <span className="ml-auto opacity-60 normal-case tracking-normal text-slate-400">
                        {m.supplemental_image.subject}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {sending && (
          <div className="flex gap-3 items-start" data-testid="msg-typing">
            <Avatar small />
            <div className="flex items-center gap-2 text-[11px] tracking-widest text-cyan-300/60" style={{ fontFamily: "monospace" }}>
              <Loader2 size={12} className="animate-spin" />
              KEEPER TYPING
            </div>
          </div>
        )}
      </div>

      {/* Transmission caption + input */}
      <div className="relative flex-shrink-0 p-4 sm:p-5 border-t border-cyan-300/10" style={{ background: "rgba(5,7,18,0.7)", backdropFilter: "blur(8px)" }}>
        <p
          className="text-[9px] uppercase tracking-[0.35em] text-cyan-300/45 mb-2"
          style={{ fontFamily: "monospace" }}
        >
          <Radio size={10} className="inline mr-1.5" style={{ verticalAlign: "-1px" }} />
          transmitting to the keeper's station · {shortWallet(wallet)}
        </p>
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            rows={1}
            data-testid="archive-input"
            placeholder="Ask the Keeper anything about the Bullpughan universe…"
            className="flex-1 resize-none rounded-xl bg-black/50 border border-cyan-300/20 focus:border-cyan-300/50 focus:outline-none px-4 py-3 text-sm text-white placeholder:text-slate-600 max-h-32"
            style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
          />
          <button
            type="button"
            onClick={sendMessage}
            disabled={sending || !input.trim()}
            data-testid="archive-send-btn"
            className="w-11 h-11 rounded-xl flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: "#00FFA3",
              color: "#000",
              boxShadow: "0 0 16px rgba(0,255,163,0.35)",
            }}
          >
            {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page shell ────────────────────────────────────────────────────────
export default function Archive() {
  const { publicKey } = useWallet();
  const walletFromAdapter = useMemo(() => publicKey?.toBase58() || null, [publicKey]);
  const { sessionType, identity, email, authHeaders, hydrating, signOut } = useAuth();
  // Downstream code keeps using `wallet` as its opaque identity string
  // (real wallet for wallet users, user_id UUID for email users).
  const wallet = identity;

  // URL param builder — ONLY real Solana wallet addresses go into URLs.
  // Never put an email user's user_id in the query string (it'd leak
  // into browser history, referer headers, share links). Email users
  // authenticate via the Bearer JWT header instead.
  const walletUrlParam = walletFromAdapter
    ? `?wallet=${encodeURIComponent(walletFromAdapter)}`
    : "";
  const walletAmpParam = walletFromAdapter
    ? `&wallet=${encodeURIComponent(walletFromAdapter)}`
    : "";
  const fetchOpts = useMemo(() => ({ headers: authHeaders }), [authHeaders]);

  const [refreshTick, setRefreshTick] = useState(0);
  // Deep-link `?tab=drops|record|ledger` from other pages (e.g. the
  // homepage "Today's Drop — Curator Pick" CTA) needs to land on the
  // ledger side on mobile so the sub-tab is actually visible. On
  // desktop both panes are always visible, so this is a no-op there.
  const [initialSearch] = useSearchParams();
  const initialMobileTab = (() => {
    const t = (initialSearch.get("tab") || "").toLowerCase();
    return t === "drops" || t === "record" || t === "ledger" ? "ledger" : "keeper";
  })();
  const [mobileTab, setMobileTab] = useState(initialMobileTab); // keeper | ledger

  // Celebration queue — new unlocks detected by diffing the /unlocks
  // poll against a set of slugs we've already celebrated (or seen on
  // load). One celebration plays at a time; the queue drains in the
  // order the classifier recorded them.
  const [queue, setQueue] = useState([]);
  const [active, setActive] = useState(null);
  const [promptRequest, setPromptRequest] = useState(null);
  const seenSlugsRef = useRef(new Set());
  const seenRankRef = useRef(null); // last-observed rank; drives rank-up flag
  const initialisedRef = useRef(false);

  // Locked-card → chat handoff: switch to keeper tab on mobile and
  // pass the derived prompt down to Workspace with a fresh id so the
  // effect re-fires even when the same prompt is requested twice.
  const handleOpenArchive = useCallback((text) => {
    setMobileTab("keeper");
    setPromptRequest({ text, id: Date.now() });
  }, []);

  // Poll for new unlocks after each assistant reply. Runs immediately
  // (in case the classifier finished fast), then again at 4s and 9s to
  // catch typical latencies. Also runs once on mount to seed the
  // "already seen" baseline so an existing user doesn't get carpet-
  // celebrated on page load.
  const pollUnlocks = useCallback(async () => {
    if (!wallet) return;
    try {
      const [uRes, rRes] = await Promise.all([
        fetch(`${API}/archive/unlocks${walletUrlParam}`, fetchOpts),
        fetch(`${API}/archive/rank${walletUrlParam}`, fetchOpts),
      ]);
      if (!uRes.ok) return;
      const uData = await uRes.json();
      const rData = rRes.ok ? await rRes.json() : { rank: null };
      const currentRank = rData?.rank ?? null;
      const unlocks = uData.unlocks || [];

      // First run — seed baseline, don't celebrate anything historical.
      if (!initialisedRef.current) {
        initialisedRef.current = true;
        seenSlugsRef.current = new Set(unlocks.map((u) => u.entry_id));
        seenRankRef.current = currentRank;
        return;
      }

      // Anything new? Server returns newest-first — walk oldest-to-newest
      // when queueing so the celebrations play in chronological order.
      // Special-tier unlocks (companion-linked) already play their
      // celebration on the `/companion` page — mark them seen but
      // never enqueue.
      const allFresh = unlocks.filter((u) => !seenSlugsRef.current.has(u.entry_id));
      allFresh
        .filter((u) => u.entry_tier === "special")
        .forEach((u) => seenSlugsRef.current.add(u.entry_id));
      const fresh = allFresh
        .filter((u) => u.entry_tier !== "special")
        .reverse();
      if (fresh.length === 0) return;
      const previousRank = seenRankRef.current;
      const finalIndex = fresh.length - 1;
      const enriched = fresh.map((u, i) => {
        const isRankUp = i === finalIndex && currentRank && currentRank !== previousRank;
        return {
          entry_id: u.entry_id,
          entry_name: u.entry_id, // fallback — real name filled from entries below
          entry_tier: u.entry_tier,
          tinkerpug_excerpt: u.tinkerpug_excerpt,
          unlocked_at: u.unlocked_at,
          is_rank_up: !!isRankUp,
          new_rank: isRankUp ? currentRank : null,
          new_rank_title: isRankUp ? rData?.rank_title : null,
        };
      });
      // Enrich with real display names from /entries so the celebration
      // card shows "Ruffus and the Runes", not the slug.
      try {
        const eRes = await fetch(
          `${API}/archive/entries${walletUrlParam}`,
          fetchOpts,
        );
        if (eRes.ok) {
          const eData = await eRes.json();
          const byId = Object.fromEntries((eData.entries || []).map((e) => [e.slug, e]));
          enriched.forEach((u) => {
            const meta = byId[u.entry_id];
            if (meta) u.entry_name = meta.name;
          });
        }
      } catch {
        /* fall back to slug */
      }
      fresh.forEach((u) => seenSlugsRef.current.add(u.entry_id));
      seenRankRef.current = currentRank;
      setQueue((prev) => [...prev, ...enriched]);
    } catch {
      /* silent — celebrations are optional */
    }
  }, [wallet, walletUrlParam, fetchOpts]);

  // Poll trio after an assistant reply
  const bumpRefresh = useCallback(() => {
    setRefreshTick((n) => n + 1);
    pollUnlocks();
    const t1 = setTimeout(() => {
      setRefreshTick((n) => n + 1);
      pollUnlocks();
    }, 4000);
    const t2 = setTimeout(() => {
      setRefreshTick((n) => n + 1);
      pollUnlocks();
    }, 9000);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [pollUnlocks]);

  // Baseline poll on mount / wallet change
  useEffect(() => {
    initialisedRef.current = false;
    seenSlugsRef.current = new Set();
    seenRankRef.current = null;
    setQueue([]);
    setActive(null);
    if (wallet) pollUnlocks();
  }, [wallet, pollUnlocks]);

  // Fire today's daily-drop generation as soon as a wallet is connected
  // on the Archive page — independent of which sub-tab (ledger / drops
  // / record) the user is currently viewing. Before this, generation
  // was gated behind mounting `DailyDropVault`, which only happens when
  // the user manually opens the "Daily Drops" sub-tab, so first-connect
  // users never triggered the pipeline in production. Idempotent per
  // (wallet, UTC-day) on the backend — returns the cache hit for
  // returning users, ~5-10s for fresh first-connects. Fire-and-forget:
  // errors are silent, `DailyDropVault` will retry naturally when the
  // user opens the drops tab.
  useEffect(() => {
    if (!wallet) return;
    let cancelled = false;
    // Real wallet → `?wallet_address=<addr>`. Email user → no query
    // param + Authorization header (backend resolver reads the JWT).
    const url = walletFromAdapter
      ? `${API}/ai/daily-drop?wallet_address=${encodeURIComponent(walletFromAdapter)}`
      : `${API}/ai/daily-drop`;
    (async () => {
      try {
        const res = await fetch(url, fetchOpts);
        if (!cancelled && res.ok) {
          // Nudge the ledger's refresh key so the drops tab picks up
          // the newly-generated card without waiting for its own poll.
          setRefreshTick((n) => n + 1);
        }
      } catch {
        /* silent */
      }
    })();
    return () => { cancelled = true; };
  }, [wallet, walletFromAdapter, fetchOpts]);

  // Drain the queue one at a time
  useEffect(() => {
    if (active || queue.length === 0) return;
    const [next, ...rest] = queue;
    setActive(next);
    setQueue(rest);
  }, [active, queue]);

  // Dev-only test hook — expose a queue-push function on window when
  // the URL carries `?archive-test=1` so QA can validate the three
  // tier celebrations and rank-up overlay without driving a real
  // wallet + classifier cycle. Zero cost in normal usage.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const enabled =
      window.location.search.indexOf("archive-test=1") !== -1;
    if (!enabled) return;
    window.__archivePushUnlock = (u) => {
      setQueue((prev) => [...prev, u]);
    };
    return () => {
      try {
        delete window.__archivePushUnlock;
      } catch {
        /* ignore */
      }
    };
  }, []);

  return (
    <div className="min-h-[calc(100vh-4rem)] pt-16" data-testid="archive-page">
      {/* Sign-in is presented via the global <UnifiedWalletButton /> in
          the Navbar — a single dropdown that offers both email and
          wallet paths, always discoverable regardless of connection
          state. Archive shows a small guest-state prompt inline
          below so a first-time visitor knows to open the sign-in
          menu (rather than hitting a blank ledger). */}
      {sessionType === "guest" && !hydrating && (
        <div
          className="sticky top-16 z-30 border-b border-white/[0.06] bg-[#05050A]/90 backdrop-blur px-4 py-2 text-center"
          data-testid="archive-guest-hint"
        >
          <p
            className="text-[10px] uppercase tracking-widest text-slate-400"
            style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
          >
            keeper's log — sign in from the top-right to save your progress. the ledger stays open regardless.
          </p>
        </div>
      )}

      {/* Active-session strip — shown at the top when signed in.
          Displays either the wallet shorthand or the email shorthand
          and provides a sign-out affordance. Wallet sign-out is
          handled by the wallet adapter's own disconnect button, so
          this button only surfaces for email sessions. */}
      {sessionType === "email" && (
        <div
          className="sticky top-16 z-30 flex items-center justify-between gap-3 border-b border-white/[0.06] bg-[#05050A]/90 backdrop-blur px-4 py-1.5"
          data-testid="archive-email-session-strip"
        >
          <span
            className="text-[10px] uppercase tracking-widest text-slate-500"
            style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
          >
            signed in as{" "}
            <span className="text-slate-200" data-testid="archive-email-shorthand">
              {shortenEmail(email)}
            </span>
          </span>
          <div className="flex items-center gap-3">
            {/* Non-blocking hint: token-side features live on-chain.
                Opens the Navbar auth dropdown so the user can pick a
                wallet without leaving the Archive. */}
            <button
              type="button"
              onClick={() => document.querySelector('[data-testid="unified-wallet-btn"]')?.click()}
              data-testid="archive-link-wallet-hint"
              className="text-[10px] uppercase tracking-widest text-[#B47CFF] hover:text-white transition-colors"
              title="Link a wallet to unlock token features. Your Archive progress stays exactly where it is."
            >
              link wallet
            </button>
            <button
              type="button"
              onClick={signOut}
              data-testid="archive-sign-out"
              className="inline-flex items-center gap-1 text-[10px] uppercase tracking-widest text-slate-400 hover:text-white"
            >
              <LogOut size={11} /> sign out
            </button>
          </div>
        </div>
      )}

      {/* Mobile tab switcher */}
      <div className="lg:hidden sticky top-16 z-30 border-b border-white/[0.06] bg-[#05050A]/90 backdrop-blur px-4 py-2 flex gap-2">
        {[
          { id: "keeper", label: "Speak with the Keeper", icon: MessageCircle },
          { id: "ledger", label: "Your Ledger", icon: BookOpen },
        ].map(({ id, label, icon: Icon }) => {
          const active = mobileTab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setMobileTab(id)}
              data-testid={`archive-mobile-tab-${id}`}
              className={`flex-1 flex items-center justify-center gap-1.5 rounded-full py-2 text-[10px] font-bold uppercase tracking-widest transition-all ${
                active ? "text-black" : "text-slate-400"
              }`}
              style={{
                background: active ? "#00FFA3" : "rgba(255,255,255,0.05)",
                fontFamily: "Orbitron, sans-serif",
              }}
            >
              <Icon size={11} />
              <span className="truncate">{label}</span>
            </button>
          );
        })}
      </div>

      {/* Desktop split / mobile single-column */}
      <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] h-[calc(100vh-4rem)] max-h-[calc(100vh-4rem)]">
        <div className={`${mobileTab === "keeper" ? "block" : "hidden"} lg:block h-full min-h-0`}>
          <Workspace wallet={wallet} onAssistantReply={bumpRefresh} promptRequest={promptRequest} />
        </div>
        <div className={`${mobileTab === "ledger" ? "block" : "hidden"} lg:block h-full min-h-0`}>
          <ArchiveLedger wallet={wallet} refreshKey={refreshTick} onOpenArchive={handleOpenArchive} />
        </div>
      </div>

      {/* Unlock celebration overlay — plays one entry from the queue at
          a time. Fires the tier-appropriate FX + rank-up card, then
          drops the entry so the next one in the queue can play. */}
      {active && (
        <UnlockCelebration
          key={active.entry_id + "-" + (active.unlocked_at || "")}
          unlock={active}
          wallet={wallet}
          onDone={() => setActive(null)}
        />
      )}
    </div>
  );
}
