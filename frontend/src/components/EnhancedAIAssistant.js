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

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  // ESC exits fullscreen (and only fullscreen, not the chat entirely)
  useEffect(() => {
    if (!isFullscreen) return;
    const onKey = (e) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isFullscreen]);

  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [dropShared, setDropShared] = useState(false);

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
      if (walletAddress && !historyLoaded) {
        try {
          const { data } = await axios.get(`${API}/ai/history/${walletAddress}`);
          if (data.success && data.messages && data.messages.length > 0) {
            setMessages(data.messages);
            if (data.session_id) {
              setSessionId(data.session_id);
            }
          }
          setHistoryLoaded(true);
        } catch (e) {
          console.error("Failed to load chat history:", e);
          setHistoryLoaded(true);
        }
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
    if (isOpen && messages.length === 0 && !isLoading && historyLoaded) {
      setMessages([{
        role: "assistant",
        content: "Hey there! I'm **Bullpug AI** with **real-time market data**! I can help you with:\n\n- **Live coin prices** - Ask \"What's the price of SOL?\" or \"Show me BTC price\"\n- **Trending coins** - Ask \"What's trending on Solana?\"\n- **Market sentiment** - Fear & Greed Index and global market data\n- **Bullpug Lore** - Learn about Newpug City, the Guardians, and our cosmic origins\n- **Trade analysis** and exit strategies\n\nI'll remember our conversation so feel free to continue anytime!",
        timestamp: Date.now()
      }]);
    }
  }, [isOpen, messages.length, isLoading, historyLoaded]);

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
        chat_history: messages.slice(-10).map(m => ({
          role: m.role,
          content: m.content
        }))
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
    }
  };

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
    if (!window.confirm("Clear all chat history? This cannot be undone.")) return;
    
    // Cancel any pending save operations
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }
    
    // Clear from MongoDB if wallet connected
    if (walletAddress) {
      try {
        const response = await axios.delete(`${API}/ai/history/${walletAddress}`);
        if (response.data?.success) {
          toast.success("Chat history cleared");
        }
      } catch (e) {
        console.error("Failed to clear history from server:", e);
        toast.error("Failed to clear chat history");
      }
    } else {
      toast.success("Chat cleared");
    }
    
    // Clear local state
    setMessages([]);
    sessionStorage.removeItem('bullpug_ai_messages');
    
    // Generate new session
    const newSession = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSession);
    sessionStorage.setItem('bullpug_ai_session', newSession);
    
    // Reset historyLoaded so it doesn't try to re-fetch cleared history
    setHistoryLoaded(true);  // Keep true since we just cleared it intentionally
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
            src="/assets/bullpug_professor.png" 
            alt="Bullpug AI" 
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
                  src="/assets/bullpug_professor.png" 
                  alt="Bullpug AI" 
                  className="w-full h-full object-cover"
                />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-1">
                  Bullpug AI
                  <Sparkles className="w-3 h-3 text-[#FFD700]" />
                  <span className="ml-1 px-1.5 py-0.5 bg-[#00FFA3]/20 text-[#00FFA3] text-[8px] rounded font-medium flex items-center gap-0.5">
                    <span className="w-1 h-1 bg-[#00FFA3] rounded-full animate-pulse" />
                    LIVE
                  </span>
                </h3>
                {!isMinimized && (
                  <p className="text-[10px] text-slate-400">Real-time market data</p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-1">
              {!isMinimized && (
                <button
                  onClick={clearChat}
                  className="p-1.5 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                  title="Clear chat history"
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

              {/* Scroll to bottom button */}
              <div className="absolute bottom-[70px] left-1/2 -translate-x-1/2">
                <button
                  onClick={scrollToBottom}
                  className="px-3 py-1 rounded-full bg-white/10 text-slate-400 text-xs flex items-center gap-1 hover:bg-white/20 transition-colors"
                >
                  <ChevronDown className="w-3 h-3" />
                  Scroll to bottom
                </button>
              </div>

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
