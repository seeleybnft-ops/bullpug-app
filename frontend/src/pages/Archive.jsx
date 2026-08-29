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
import { Send, Loader2, Radio, MessageCircle, BookOpen } from "lucide-react";
import ArchiveLedger from "@/components/ArchiveLedger";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TINKERPUG_AVATAR = "/tinkerpug-canon.jpg";

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
function Workspace({ wallet, onAssistantReply }) {
  const sessionId = useSessionId();
  const [messages, setMessages] = useState(() => [
    { role: "assistant", content: FIRST_VISIT_GREETING, isGreeting: true },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);
  const isReturnGreetedRef = useRef(false);

  // Auto-scroll on new messages
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  // On wallet-connect after first visit, swap the greeting for the return
  // form once we know the rank. Fire-and-forget — chat continues without.
  useEffect(() => {
    if (!wallet || isReturnGreetedRef.current) return;
    isReturnGreetedRef.current = true;
    fetch(`${API}/archive/rank?wallet=${encodeURIComponent(wallet)}`)
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
        },
        body: JSON.stringify({
          session_id: sessionId,
          wallet_address: wallet || null,
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
  const wallet = useMemo(() => publicKey?.toBase58() || null, [publicKey]);
  const [refreshTick, setRefreshTick] = useState(0);
  const [mobileTab, setMobileTab] = useState("keeper"); // keeper | ledger

  // Poll for new unlocks briefly after each assistant reply — the
  // classifier runs async on the backend so the unlock lands 3–8s later.
  const bumpRefresh = useCallback(() => {
    // First bump immediately (in case the classifier finished fast),
    // then again at 4s and 9s to catch typical latencies.
    setRefreshTick((n) => n + 1);
    const t1 = setTimeout(() => setRefreshTick((n) => n + 1), 4000);
    const t2 = setTimeout(() => setRefreshTick((n) => n + 1), 9000);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  return (
    <div className="min-h-[calc(100vh-4rem)] pt-16" data-testid="archive-page">
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
          <Workspace wallet={wallet} onAssistantReply={bumpRefresh} />
        </div>
        <div className={`${mobileTab === "ledger" ? "block" : "hidden"} lg:block h-full min-h-0`}>
          <ArchiveLedger wallet={wallet} refreshKey={refreshTick} />
        </div>
      </div>
    </div>
  );
}
