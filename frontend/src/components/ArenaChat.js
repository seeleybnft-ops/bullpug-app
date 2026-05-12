import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import axios from "axios";
import { Send, MessageSquare, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const SESSION_KEY = "bullpug_arena_chat_session_v1";
const POLL_INTERVAL_MS = 5000;
const MAX_LEN = 240;

function getOrCreateSessionId() {
  try {
    let s = localStorage.getItem(SESSION_KEY);
    if (!s) {
      s = `s-${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
      localStorage.setItem(SESSION_KEY, s);
    }
    return s;
  } catch (e) {
    return `s-${Math.random().toString(36).slice(2, 10)}`;
  }
}

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch (e) {
    return "";
  }
}

export default function ArenaChat() {
  const { publicKey } = useWallet();
  const walletAddress = publicKey?.toBase58() || null;
  const sessionId = useMemo(() => getOrCreateSessionId(), []);

  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);
  const lastSeenRef = useRef(null);

  // Initial load
  const fetchInitial = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/arena-chat/messages?limit=50`);
      const msgs = data.messages || [];
      setMessages(msgs);
      if (msgs.length) lastSeenRef.current = msgs[msgs.length - 1].created_at;
    } catch (e) {
      setError("Couldn't load chat");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitial();
  }, [fetchInitial]);

  // Polling for new messages
  useEffect(() => {
    let stopped = false;
    const tick = async () => {
      if (stopped) return;
      try {
        const params = lastSeenRef.current ? `?since=${encodeURIComponent(lastSeenRef.current)}&limit=50` : "?limit=50";
        const { data } = await axios.get(`${API}/arena-chat/messages${params}`);
        const fresh = data.messages || [];
        if (fresh.length) {
          setMessages((prev) => {
            const seen = new Set(prev.map((m) => m.id));
            const merged = [...prev];
            for (const m of fresh) {
              if (!seen.has(m.id)) merged.push(m);
            }
            return merged.slice(-200);
          });
          lastSeenRef.current = fresh[fresh.length - 1].created_at;
        }
      } catch (e) { /* swallow */ }
    };
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => { stopped = true; clearInterval(id); };
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async (e) => {
    e?.preventDefault?.();
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setError(null);
    try {
      const { data } = await axios.post(`${API}/arena-chat/post`, {
        body,
        wallet_address: walletAddress,
        session_id: sessionId,
      });
      setDraft("");
      // Optimistically append the message; polling will reconcile
      if (data?.message) {
        setMessages((prev) => {
          if (prev.some((m) => m.id === data.message.id)) return prev;
          return [...prev, data.message].slice(-200);
        });
        lastSeenRef.current = data.message.created_at;
      }
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setError(detail || "Couldn't send — try again");
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      data-testid="arena-chat-panel"
      className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] overflow-hidden flex flex-col h-[420px] sm:h-[460px]"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 bg-gradient-to-r from-[#00FFA3]/8 to-[#D946EF]/8 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-[#00FFA3]" />
        <span
          className="text-[11px] uppercase tracking-[0.22em] font-bold text-white"
          style={{ fontFamily: "Orbitron, sans-serif" }}
        >
          Arena Chat
        </span>
        <span className="ml-auto inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30">
          <span className="w-1 h-1 rounded-full bg-[#00FFA3] animate-pulse" />
          <span className="text-[8px] uppercase tracking-wider text-[#00FFA3] font-bold">Live</span>
        </span>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        data-testid="arena-chat-feed"
        className="flex-1 overflow-y-auto px-4 py-3 space-y-2 text-[12.5px] leading-relaxed"
      >
        {loading && (
          <div className="text-slate-500 text-center text-[11px] py-6 flex items-center justify-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading chat…
          </div>
        )}
        {!loading && messages.length === 0 && (
          <div className="text-slate-500 text-center text-[11px] py-8">
            No messages yet — be the first to bark.
          </div>
        )}
        {messages.map((m) => {
          const isMine = m.session_id === sessionId || (walletAddress && m.wallet_address === walletAddress);
          if (m.is_system) {
            return (
              <div key={m.id} className="flex justify-center">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F5D300]/10 border border-[#F5D300]/30 text-[11px] text-[#F5D300] font-mono">
                  {m.body}
                </div>
              </div>
            );
          }
          return (
            <div key={m.id} className={`flex flex-col ${isMine ? "items-end" : "items-start"}`}>
              <div className="flex items-baseline gap-2 mb-0.5">
                <span
                  className={`text-[10px] uppercase tracking-wider font-bold ${isMine ? "text-[#00FFA3]" : "text-slate-400"}`}
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  {isMine ? "You" : m.author}
                </span>
                <span className="text-[9px] text-slate-600 font-mono">{formatTime(m.created_at)}</span>
              </div>
              <div
                className={`max-w-[85%] px-3 py-1.5 rounded-2xl whitespace-pre-wrap break-words ${
                  isMine
                    ? "bg-[#00FFA3]/12 border border-[#00FFA3]/30 text-white rounded-br-sm"
                    : "bg-white/5 border border-white/10 text-slate-200 rounded-bl-sm"
                }`}
              >
                {m.body}
              </div>
            </div>
          );
        })}
      </div>

      {/* Composer */}
      <form onSubmit={handleSend} className="px-3 py-3 border-t border-white/10 bg-black/40 flex items-center gap-2">
        <input
          type="text"
          maxLength={MAX_LEN}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={walletAddress ? "Say something to the arena…" : "Bark anonymously… connect wallet to use your handle"}
          data-testid="arena-chat-input"
          className="flex-1 px-3 py-2 bg-white/5 border border-white/10 focus:border-[#00FFA3]/60 focus:outline-none rounded-full text-[13px] text-white placeholder-slate-500"
        />
        <button
          type="submit"
          disabled={sending || !draft.trim()}
          data-testid="arena-chat-send"
          className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-[#00FFA3] hover:bg-[#00FFA3]/90 disabled:opacity-40 text-black transition-colors"
          aria-label="Send"
        >
          {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </form>
      {error && (
        <div className="px-4 py-1.5 text-[10px] text-red-400 border-t border-red-500/20 bg-red-500/5">
          {error}
        </div>
      )}
    </div>
  );
}
