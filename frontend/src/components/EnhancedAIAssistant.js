/**
 * EnhancedAIAssistant - Persistent AI chat assistant for Trading Journal
 * Features: MongoDB-backed persistent memory, no auto-scroll, available across all tabs
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useAccount } from "wagmi";
import { 
  Sparkles, X, Send, Loader2, 
  Minimize2, Maximize2, ChevronDown, Trash2, Image, XCircle, Share2, Check, Expand, Shrink
} from "lucide-react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import TinkerpugCodex, { CodexButton, detectUnlocked } from "./TinkerpugCodex";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Canonical Tinkerpug welcome greeting. Used both for the first-open
// auto-greeting AND when the user clears the chat — so deleting always
// resets back to a known, on-canon Archive intro.
const TINKERPUG_GREETING = "Hey there. I'm **Tinkerpug**, keeper of the Bullpug Archive. I can help you with:\n\n- **Bullpug Lore** — Newpug City, the Guardians, the Between, the feats. Just ask.\n- **Live coin prices** — \"What's the price of SOL?\" or \"Show me BTC price\"\n- **Trending coins** — \"What's trending on Solana?\"\n\nWhere do you want to dig first?";

const buildGreetingMessage = () => ({
  role: "assistant",
  content: TINKERPUG_GREETING,
  timestamp: Date.now(),
});

export default function EnhancedAIAssistant({ activeTab = "dashboard" }) {
  const { publicKey, connected: solanaConnected } = useWallet();
  const { address: evmAddress, isConnected: evmConnected } = useAccount();
  
  // Get wallet address from either connection
  const walletAddress = solanaConnected 
    ? publicKey?.toBase58() 
    : (evmConnected ? evmAddress : null);
  
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [hasNewMessage, setHasNewMessage] = useState(false);
  const [hasLiveData, setHasLiveData] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  // Track whether the auto-greeting has already been emitted this open-session.
  // Lets clearChat() suppress the welcome message so the chat actually empties
  // instead of immediately re-greeting the user.
  const [greetingShown, setGreetingShown] = useState(false);
  // ESC exits fullscreen (and only fullscreen, not the chat entirely)
  useEffect(() => {
    if (!isFullscreen) return;
    const onKey = (e) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isFullscreen]);

  // Allow any page to open Tinkerpug via a global custom event
  useEffect(() => {
    const handler = () => {
      setIsOpen(true);
      setIsMinimized(false);
    };
    window.addEventListener("tinkerpug:open", handler);
    return () => window.removeEventListener("tinkerpug:open", handler);
  }, []);

  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [dropShared, setDropShared] = useState(false);
  const [codexOpen, setCodexOpen] = useState(false);
  // Two-click confirm pattern for the trash button (replaces window.confirm
  // which can be blocked by some browsers / iframes / dismissed accidentally).
  const [clearPending, setClearPending] = useState(false);
  const clearPendingTimeoutRef = useRef(null);
  // Track Codex unlock count so the header badge stays in sync with the pane
  // (recomputed whenever assistant messages change). Cheap scan, runs in-effect.
  const [codexUnlockedCount, setCodexUnlockedCount] = useState(0);
  useEffect(() => {
    try {
      const unlocked = detectUnlocked(messages, new Set());
      setCodexUnlockedCount(unlocked.size);
    } catch (e) { /* noop */ }
  }, [messages]);

  // Share today's Bullpug Daily Drop — Web Share API → clipboard fallback → X intent
  const shareDailyDrop = async (msg) => {
    const text = `Today's Bullpug Daily Drop: ${msg.dropTheme}. ${msg.dropScene}. Catch tomorrow's drop on /lore. 🐾✨`;
    const url = `${window.location.origin}/lore`;
    try {
      if (navigator.share && typeof navigator.share === "function") {
        await navigator.share({ title: `Bullpug Daily Drop · ${msg.dropTheme}`, text, url });
        setDropShared(true);
        setTimeout(() => setDropShared(false), 2500);
        return;
      }
    } catch (e) { /* user cancelled — fall through */ }
    try {
      await navigator.clipboard.writeText(`${text}\n${url}`);
      setDropShared(true);
      setTimeout(() => setDropShared(false), 2500);
      toast.success("Copied — share the drop!");
    } catch (e) {
      const intent = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
      window.open(intent, "_blank", "noopener,noreferrer");
    }
  };
  
  const messagesContainerRef = useRef(null);
  const inputRef = useRef(null);
  const saveTimeoutRef = useRef(null);
  const fileInputRef = useRef(null);

  // Load chat history from MongoDB when wallet connects
  useEffect(() => {
    const loadHistory = async () => {
      if (!walletAddress) {
        // Anonymous user — no DB history to load, show greeting immediately
        if (!historyLoaded) setHistoryLoaded(true);
        return;
      }
      if (historyLoaded) return;
      try {
        const { data } = await axios.get(`${API}/ai/history/${walletAddress}`);
        if (data.success && data.messages && data.messages.length > 0) {
          // Migrate legacy "Bullpug AI" greeting → Tinkerpug. Drop the stale
          // first message; the welcome-message effect will re-emit the new
          // greeting on next mount if the history becomes empty.
          const cleaned = data.messages.filter((m, idx) => {
            if (idx !== 0) return true;
            if (m.role !== "assistant") return true;
            const c = (m.content || "");
            // Drop legacy greetings so the new "keeper of the Bullpug Archive" version takes over
            return !(
              c.includes("I'm **Bullpug AI**") ||
              c.includes("Bullpug AI with **real-time") ||
              c.includes("your Bullpug market intelligence companion") ||
              // Previous Tinkerpug greeting that included Market sentiment + Trade analysis bullets
              (c.includes("keeper of the Bullpug archive") && c.includes("Market sentiment")) ||
              // Older lowercase "archive" greeting that opened with "Hey there!"
              (c.includes("keeper of the Bullpug archive") && c.includes("Hey there!")) ||
              // Previous Tinkerpug greeting that referenced retired-canon "Mindverse"
              (c.includes("keeper of the Bullpug Archive") && c.includes("Mindverse"))
            );
          });
          setMessages(cleaned);
          if (data.session_id) {
            setSessionId(data.session_id);
          }
        }
        setHistoryLoaded(true);
      } catch (e) {
        console.error("Failed to load chat history:", e);
        setHistoryLoaded(true);
      }
    };

    loadHistory();
  }, [walletAddress, historyLoaded]);

  // Generate session ID on mount if not loaded from DB
  useEffect(() => {
    if (!sessionId) {
      const storedSession = sessionStorage.getItem('bullpug_ai_session');
      if (storedSession) {
        setSessionId(storedSession);
      } else {
        const newSession = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        setSessionId(newSession);
        sessionStorage.setItem('bullpug_ai_session', newSession);
      }
    }
  }, [sessionId]);

  // Save messages to MongoDB (debounced)
  const saveToMongoDB = useCallback(async (messagesToSave) => {
    if (!walletAddress || messagesToSave.length === 0) return;
    
    try {
      await axios.post(`${API}/ai/history/save`, {
        wallet_address: walletAddress,
        session_id: sessionId,
        messages: messagesToSave
      });
    } catch (e) {
      console.error("Failed to save chat history:", e);
    }
  }, [walletAddress, sessionId]);

  // Debounced save when messages change
  useEffect(() => {
    if (messages.length > 0 && walletAddress) {
      // Clear existing timeout
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      
      // Save after 2 seconds of no changes
      saveTimeoutRef.current = setTimeout(() => {
        saveToMongoDB(messages);
      }, 2000);
    }
    
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [messages, walletAddress, saveToMongoDB]);

  // Show welcome message when opened for first time
  useEffect(() => {
    if (isOpen && messages.length === 0 && !isLoading && historyLoaded && !greetingShown) {
      setMessages([buildGreetingMessage()]);
      setGreetingShown(true);
    }
  }, [isOpen, messages.length, isLoading, historyLoaded, greetingShown]);

  // When the panel is closed, reset the greeting flag so reopening shows the
  // intro again on a fresh session.
  useEffect(() => {
    if (!isOpen) setGreetingShown(false);
  }, [isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, isMinimized]);

  const sendMessage = useCallback(async () => {
    if ((!inputValue.trim() && !selectedImage) || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    
    // Add user message with optional image
    const newUserMessage = {
      role: "user",
      content: userMessage || (selectedImage ? "Please analyze this image" : ""),
      timestamp: Date.now(),
      image: imagePreview
    };
    
    setMessages(prev => [...prev, newUserMessage]);
    setIsLoading(true);

    try {
      let requestData = {
        wallet_address: walletAddress,
        message: userMessage || "Please analyze this image and identify any tokens, charts, or crypto-related content.",
        session_id: sessionId,
        active_tab: activeTab,
        daily_drop_last_seen: (() => {
          try { return localStorage.getItem("bullpug_daily_drop_last_seen") || null; } catch (e) { return null; }
        })(),
        chat_history: messages.slice(-40).map(m => {
          // Surface image attachments + generated images into the text content
          // so the LLM keeps full conversational context — including referent
          // resolution ("show me the OTHER side of it" → it = previously shown
          // image). Without this, only role+content survived and every image
          // turn became a blind hand-off.
          const parts = [m.content || ""];
          if (m.image) parts.push("[user attached an image]");
          if (m.generatedImage) parts.push("[assistant generated an image and showed it inline]");
          return {
            role: m.role,
            content: parts.filter(Boolean).join("\n").trim(),
          };
        })
      };

      // If there's an image, convert to base64 and send
      if (selectedImage) {
        const reader = new FileReader();
        const base64Promise = new Promise((resolve) => {
          reader.onloadend = () => resolve(reader.result);
          reader.readAsDataURL(selectedImage);
        });
        const base64Image = await base64Promise;
        requestData.image = base64Image;
        requestData.message = userMessage || "Please analyze this image. Identify any tokens, charts, prices, or crypto-related information. Reference live market data if you recognize any symbols.";
      }

      const { data } = await axios.post(`${API}/ai/chat`, requestData);

      // Prepend Daily Bullpug Drop card if backend included one
      const newMessages = [];
      if (data.daily_drop && data.daily_drop.image_base64) {
        newMessages.push({
          role: "drop",
          dropDate: data.daily_drop.date_utc,
          dropTheme: data.daily_drop.theme,
          dropScene: data.daily_drop.scene,
          dropImage: data.daily_drop.image_base64,
          dropCaption: data.daily_drop.caption,
          timestamp: Date.now(),
        });
        try {
          localStorage.setItem("bullpug_daily_drop_last_seen", data.daily_drop.date_utc);
        } catch (e) { /* ignore */ }
      }

      const assistantMessage = {
        role: "assistant",
        content: data.response,
        timestamp: Date.now(),
        hasLiveData: data.has_live_data,
        generatedImage: data.image_base64 || null,
        kind: data.kind || "text"
      };
      newMessages.push(assistantMessage);

      setMessages(prev => [...prev, ...newMessages]);
      setHasLiveData(data.has_live_data || false);
      
      // Clear image after sending
      setSelectedImage(null);
      setImagePreview(null);
      
      // Show notification if minimized
      if (isMinimized) {
        setHasNewMessage(true);
      }
    } catch (e) {
      console.error("Chat error:", e);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "I encountered an error processing your request. Please try again!",
        timestamp: Date.now()
      }]);
    }
    
    setIsLoading(false);
  }, [inputValue, isLoading, walletAddress, sessionId, activeTab, messages, isMinimized, selectedImage, imagePreview]);

  // Handle image selection
  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error("Image too large. Max 5MB allowed.");
        return;
      }
      if (!file.type.startsWith('image/')) {
        toast.error("Please select an image file.");
        return;
      }
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onloadend = () => setImagePreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      setIsAtBottom(true);
    }
  };

  // Smart auto-scroll — only follow new messages if the user was already near
  // the bottom when the message arrived. If they scrolled up to re-read older
  // messages, leave them in place and show the "Scroll to bottom" pill so
  // they choose when to jump down.
  //
  // wasAtBottomRef is captured BEFORE the messages array updates (via a
  // layout effect that runs synchronously after the previous render), so by
  // the time the post-render useEffect fires we already know whether to
  // follow or hold.
  const BOTTOM_SLACK_PX = 80; // "near bottom" tolerance
  const [isAtBottom, setIsAtBottom] = useState(true);
  const wasAtBottomRef = useRef(true);

  // Track scroll position so the pill shows/hides + we know whether to follow.
  const handleScroll = useCallback(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - BOTTOM_SLACK_PX;
    wasAtBottomRef.current = atBottom;
    setIsAtBottom(atBottom);
  }, []);

  // Wire/unwire the scroll listener whenever the container mounts (when chat
  // is opened the ref is created; when closed it's destroyed).
  useEffect(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [handleScroll, isOpen, isMinimized]);

  // Auto-scroll to the bottom on new messages — but only if the user was
  // already near the bottom. Otherwise we just leave them be and let the
  // pill button surface the new content.
  useEffect(() => {
    if (!wasAtBottomRef.current) return; // user is reading history — don't yank
    const id = requestAnimationFrame(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      }
    });
    return () => cancelAnimationFrame(id);
  }, [messages, isLoading]);

  const toggleOpen = () => {
    setIsOpen(!isOpen);
    setIsMinimized(false);
    setHasNewMessage(false);
  };

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
    if (isMinimized) {
      setHasNewMessage(false);
    }
  };

  const clearChat = async () => {
    // Two-click confirm: first click arms, second click within 4s executes.
    if (!clearPending) {
      setClearPending(true);
      if (clearPendingTimeoutRef.current) clearTimeout(clearPendingTimeoutRef.current);
      clearPendingTimeoutRef.current = setTimeout(() => setClearPending(false), 4000);
      toast("Click delete again to confirm", { duration: 3500 });
      return;
    }
    // Confirmed — disarm and clear synchronously first so the UI updates
    // immediately, then best-effort delete on the server.
    setClearPending(false);
    if (clearPendingTimeoutRef.current) {
      clearTimeout(clearPendingTimeoutRef.current);
      clearPendingTimeoutRef.current = null;
    }
    // Cancel any pending save so an in-flight debounced save can't re-persist
    // the old messages after we've cleared them.
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }

    // Clear local state IMMEDIATELY so the user sees the chat reset.
    // Re-emit the canonical Tinkerpug greeting straight away so deleting
    // always returns to a known, on-canon Archive intro instead of an
    // empty void.
    setMessages([buildGreetingMessage()]);
    sessionStorage.removeItem("bullpug_ai_messages");
    // greetingShown=true prevents the welcome useEffect from emitting a
    // duplicate greeting in this same open-session.
    setGreetingShown(true);

    // Rotate session id so any in-flight reply gets attributed to a new thread.
    const newSession = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSession);
    sessionStorage.setItem("bullpug_ai_session", newSession);

    // Server delete is best-effort and async — even if it fails, the local
    // state is already cleared so the UI is consistent.
    if (walletAddress) {
      try {
        const response = await axios.delete(`${API}/ai/history/${walletAddress}`);
        if (response.data?.success) {
          toast.success("Chat history cleared");
        } else {
          toast.success("Chat cleared (local)");
        }
      } catch (e) {
        console.error("Failed to clear history from server:", e);
        toast("Chat cleared locally — server sync failed");
      }
    } else {
      toast.success("Chat cleared");
    }
  };

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={toggleOpen}
          className="fixed bottom-24 right-6 z-50 w-14 h-14 rounded-full shadow-lg shadow-[#D946EF]/30 flex items-center justify-center hover:scale-110 transition-transform overflow-hidden border-2 border-[#D946EF]/50"
          data-testid="ai-assistant-trigger"
        >
          <img 
            src="https://customer-assets.emergentagent.com/job_6ea6c375-5ce0-4139-ba76-31b1e3c73fa6/artifacts/kfmcg9w5_image%20-%202026-05-12T133134.751.jpg" 
            alt="Tinkerpug" 
            className="w-full h-full object-cover"
          />
          {hasNewMessage && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-ping" />
          )}
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div 
          className={`fixed z-50 bg-[#0D0D15] border border-white/10 shadow-2xl shadow-black/50 overflow-hidden transition-all duration-300 ${
            isMinimized 
              ? 'bottom-24 right-6 w-72 h-14 rounded-2xl' 
              : isFullscreen
                ? 'inset-0 sm:inset-4 lg:inset-8 rounded-none sm:rounded-3xl'
                : 'bottom-24 right-6 w-[380px] h-[500px] sm:w-[420px] sm:h-[560px] rounded-2xl'
          }`}
          data-testid="ai-assistant-window"
        >
          {/* Header */}
          <div 
            className="flex items-center justify-between p-3 bg-gradient-to-r from-[#D946EF]/20 to-[#00FFA3]/20 border-b border-white/10 cursor-pointer"
            onClick={isMinimized ? toggleMinimize : undefined}
          >
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full overflow-hidden border border-[#D946EF]/50">
                <img 
                  src="https://customer-assets.emergentagent.com/job_6ea6c375-5ce0-4139-ba76-31b1e3c73fa6/artifacts/kfmcg9w5_image%20-%202026-05-12T133134.751.jpg" 
                  alt="Tinkerpug" 
                  className="w-full h-full object-cover"
                />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-1">
                  Tinkerpug
                  <Sparkles className="w-3 h-3 text-[#FFD700]" />
                  <span className="ml-1 px-1.5 py-0.5 bg-[#00FFA3]/20 text-[#00FFA3] text-[8px] rounded font-medium flex items-center gap-0.5">
                    <span className="w-1 h-1 bg-[#00FFA3] rounded-full animate-pulse" />
                    LIVE
                  </span>
                </h3>
                {!isMinimized && (
                  <p className="text-[10px] text-slate-400 flex items-center gap-1.5" data-testid="tinkerpug-status">
                    <span className="font-mono">jacked into PugChain</span>
                    <span className="text-slate-600">·</span>
                    <span
                      className={`inline-flex items-center gap-1 ${isLoading ? "text-[#F5D300]" : "text-[#00FFA3]"}`}
                    >
                      <span
                        className={`w-1 h-1 rounded-full ${isLoading ? "bg-[#F5D300] animate-pulse" : "bg-[#00FFA3]"}`}
                        style={{ boxShadow: isLoading ? "0 0 4px rgba(245,211,0,0.7)" : "0 0 4px rgba(0,255,163,0.6)" }}
                      />
                      <span className="font-mono">{isLoading ? "thinking…" : "online"}</span>
                    </span>
                  </p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-1">
              {!isMinimized && (
                <button
                  onClick={clearChat}
                  className={`p-1.5 rounded-lg transition-colors ${
                    clearPending
                      ? "bg-red-500/30 text-red-300 ring-1 ring-red-500/60 animate-pulse"
                      : "hover:bg-red-500/20 text-slate-400 hover:text-red-400"
                  }`}
                  title={clearPending ? "Click again to confirm" : "Clear chat history"}
                  data-testid="ai-chat-clear"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={toggleMinimize}
                className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                title={isMinimized ? "Expand chat" : "Minimize chat"}
                data-testid="ai-chat-minimize"
              >
                {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
              </button>
              {!isMinimized && (
                <CodexButton
                  unlockedCount={codexUnlockedCount}
                  open={codexOpen}
                  onClick={() => setCodexOpen((v) => !v)}
                />
              )}
              {!isMinimized && (
                <button
                  onClick={() => setIsFullscreen(prev => !prev)}
                  className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                  title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
                  data-testid="ai-chat-fullscreen"
                >
                  {isFullscreen ? <Shrink className="w-4 h-4" /> : <Expand className="w-4 h-4" />}
                </button>
              )}
              <button
                onClick={toggleOpen}
                className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages Area */}
          {!isMinimized && (
            <>
              <TinkerpugCodex
                messages={messages}
                open={codexOpen}
                onClose={() => setCodexOpen(false)}
                walletAddress={walletAddress}
              />
              <div 
                ref={messagesContainerRef}
                className="flex-1 p-4 overflow-y-auto h-[calc(100%-130px)] space-y-4"
              >
                {messages.map((msg, i) => {
                  // Special render: Daily Bullpug Drop card
                  if (msg.role === "drop") {
                    return (
                      <div key={i} className="flex justify-start" data-testid="daily-drop-card">
                        <div
                          className="max-w-[95%] rounded-2xl overflow-hidden border border-[#F5D300]/30 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] shadow-[0_0_30px_rgba(245,211,0,0.10)]"
                        >
                          <img
                            src={msg.dropImage}
                            alt={msg.dropTheme || "Bullpug Daily Drop"}
                            className="w-full h-auto block"
                            loading="lazy"
                          />
                          <div className="p-3">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <span className="w-1.5 h-1.5 bg-[#F5D300] rounded-full animate-pulse" />
                              <span className="text-[9px] uppercase tracking-[0.2em] text-[#F5D300] font-bold">
                                Today's Bullpug Drop
                              </span>
                            </div>
                            <p
                              className="text-sm font-bold text-white tracking-tight"
                              style={{ fontFamily: "Orbitron, sans-serif" }}
                            >
                              {msg.dropTheme}
                            </p>
                            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                              {msg.dropScene}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-2 italic">
                              Gone after midnight UTC — only one drop per day.
                            </p>
                            <button
                              type="button"
                              onClick={() => shareDailyDrop(msg)}
                              data-testid="daily-drop-share-btn"
                              className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#F5D300] hover:bg-[#F5D300]/90 text-black text-[10px] font-bold uppercase tracking-wider transition-colors"
                              aria-live="polite"
                            >
                              {dropShared ? <Check size={11} /> : <Share2 size={11} />}
                              {dropShared ? "Copied!" : "Share the drop"}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  }

                  return (
                  <div
                    key={i}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div 
                      className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm ${
                        msg.role === "user"
                          ? "bg-gradient-to-r from-[#00FFA3]/20 to-[#00C2FF]/20 text-white rounded-br-sm"
                          : "bg-white/5 text-slate-300 rounded-bl-sm"
                      }`}
                    >
                      {/* Show image if present in user message */}
                      {msg.image && msg.role === "user" && (
                        <img 
                          src={msg.image} 
                          alt="User uploaded" 
                          className="max-w-full h-auto max-h-40 rounded-lg mb-2 border border-white/10"
                        />
                      )}
                      {/* Show AI-generated image (Nano Banana) if present */}
                      {msg.generatedImage && msg.role === "assistant" && (
                        <div className="mb-2" data-testid="chat-generated-image">
                          <img
                            src={msg.generatedImage}
                            alt="Bullpug generated"
                            loading="lazy"
                            className="w-full h-auto rounded-lg border border-[#00FFA3]/30 shadow-lg shadow-[#00FFA3]/10"
                          />
                          <div className="flex items-center gap-1 mt-1.5 text-[9px] uppercase tracking-wider text-[#00FFA3] font-bold">
                            <span className="w-1 h-1 bg-[#00FFA3] rounded-full" />
                            Generated by Nano Banana
                          </div>
                        </div>
                      )}
                      {msg.hasLiveData && msg.role === "assistant" && (
                        <div className="flex items-center gap-1 mb-1 text-[10px] text-[#00FFA3]">
                          <span className="w-1.5 h-1.5 bg-[#00FFA3] rounded-full animate-pulse" />
                          LIVE DATA
                        </div>
                      )}
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <p className="mb-1 last:mb-0 leading-relaxed">{children}</p>,
                          strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                          ul: ({ children }) => <ul className="list-disc list-inside my-1 space-y-0.5">{children}</ul>,
                          li: ({ children }) => <li className="text-sm">{children}</li>,
                          code: ({ children }) => <code className="px-1 py-0.5 bg-black/30 rounded text-[#00FFA3] text-xs">{children}</code>,
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                  );
                })}
                
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white/5 px-4 py-3 rounded-2xl rounded-bl-sm">
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-[#D946EF]" />
                        <span className="text-sm text-slate-400">Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Scroll to bottom button — only shows when user has scrolled
                  up. Sticks subtly so they can jump back when ready. */}
              {!isAtBottom && (
                <div className="absolute bottom-[70px] left-1/2 -translate-x-1/2 pointer-events-auto" data-testid="scroll-to-bottom-wrap">
                  <button
                    onClick={scrollToBottom}
                    className="px-3 py-1.5 rounded-full bg-[#D946EF]/20 text-[#E9B5FF] text-xs flex items-center gap-1 hover:bg-[#D946EF]/30 ring-1 ring-[#D946EF]/40 transition-colors shadow-lg shadow-[#D946EF]/20"
                    data-testid="scroll-to-bottom-btn"
                  >
                    <ChevronDown className="w-3 h-3" />
                    Scroll to bottom
                  </button>
                </div>
              )}

              {/* Input Area */}
              <div className="absolute bottom-0 left-0 right-0 p-3 border-t border-white/10 bg-[#0D0D15]">
                {/* Image Preview */}
                {imagePreview && (
                  <div className="mb-2 relative inline-block">
                    <img 
                      src={imagePreview} 
                      alt="Upload preview" 
                      className="h-16 w-auto rounded-lg border border-white/20"
                    />
                    <button
                      onClick={clearImage}
                      className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white hover:bg-red-600"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  </div>
                )}
                <div className="flex gap-2">
                  {/* Hidden file input */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="hidden"
                    data-testid="ai-image-input"
                  />
                  {/* Image upload button */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isLoading}
                    className="px-3 py-2.5 rounded-xl bg-black/40 border border-white/10 text-slate-400 hover:text-white hover:border-[#D946EF]/50 transition-colors disabled:opacity-50"
                    title="Upload image for analysis"
                    data-testid="ai-image-btn"
                  >
                    <Image className="w-4 h-4" />
                  </button>
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={selectedImage ? "Add a message about the image..." : "Ask me anything · try /image …"}
                    disabled={isLoading}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-[#00FFA3]/50 disabled:opacity-50"
                    data-testid="ai-chat-input"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={isLoading || (!inputValue.trim() && !selectedImage)}
                    className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#D946EF] to-[#00FFA3] text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                    data-testid="ai-chat-send"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
