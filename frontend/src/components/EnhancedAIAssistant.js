/**
 * EnhancedAIAssistant - Persistent AI chat assistant for Trading Journal
 * Features: Session-based memory, no auto-scroll, available across all tabs
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { 
  Bot, Sparkles, X, Send, Loader2, MessageSquare, 
  Minimize2, Maximize2, ChevronDown
} from "lucide-react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function EnhancedAIAssistant({ activeTab = "dashboard" }) {
  const { publicKey, connected } = useWallet();
  const walletAddress = connected ? publicKey?.toBase58() : null;
  
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [hasNewMessage, setHasNewMessage] = useState(false);
  
  const messagesContainerRef = useRef(null);
  const inputRef = useRef(null);

  // Generate session ID on mount
  useEffect(() => {
    const storedSession = sessionStorage.getItem('bullpug_ai_session');
    if (storedSession) {
      setSessionId(storedSession);
      // Load stored messages
      const storedMessages = sessionStorage.getItem('bullpug_ai_messages');
      if (storedMessages) {
        try {
          setMessages(JSON.parse(storedMessages));
        } catch (e) {
          console.error("Failed to parse stored messages:", e);
        }
      }
    } else {
      const newSession = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setSessionId(newSession);
      sessionStorage.setItem('bullpug_ai_session', newSession);
    }
  }, []);

  // Persist messages to session storage
  useEffect(() => {
    if (messages.length > 0) {
      sessionStorage.setItem('bullpug_ai_messages', JSON.stringify(messages));
    }
  }, [messages]);

  // Show welcome message when opened for first time
  useEffect(() => {
    if (isOpen && messages.length === 0 && !isLoading) {
      setMessages([{
        role: "assistant",
        content: "Hey there! I'm **Bullpug AI**, your trading assistant. I can help you with:\n\n- **Analyzing your trades** and patterns\n- **Exit strategy suggestions**\n- **Market insights** and coin recommendations\n- **Portfolio optimization** tips\n\nWhat would you like to know?",
        timestamp: Date.now()
      }]);
    }
  }, [isOpen, messages.length, isLoading]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, isMinimized]);

  const sendMessage = useCallback(async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    
    // Add user message
    const newUserMessage = {
      role: "user",
      content: userMessage,
      timestamp: Date.now()
    };
    
    setMessages(prev => [...prev, newUserMessage]);
    setIsLoading(true);

    try {
      const { data } = await axios.post(`${API}/ai/chat`, {
        wallet_address: walletAddress,
        message: userMessage,
        session_id: sessionId,
        active_tab: activeTab,
        chat_history: messages.slice(-10).map(m => ({
          role: m.role,
          content: m.content
        }))
      });

      const assistantMessage = {
        role: "assistant",
        content: data.response,
        timestamp: Date.now()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      
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
  }, [inputValue, isLoading, walletAddress, sessionId, activeTab, messages, isMinimized]);

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

  const clearChat = () => {
    setMessages([]);
    sessionStorage.removeItem('bullpug_ai_messages');
    // Generate new session
    const newSession = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSession);
    sessionStorage.setItem('bullpug_ai_session', newSession);
  };

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={toggleOpen}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-r from-[#D946EF] to-[#00FFA3] shadow-lg shadow-[#D946EF]/30 flex items-center justify-center hover:scale-110 transition-transform animate-pulse"
          data-testid="ai-assistant-trigger"
        >
          <Bot className="w-7 h-7 text-white" />
          {hasNewMessage && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-ping" />
          )}
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div 
          className={`fixed z-50 bg-[#0D0D15] border border-white/10 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden transition-all duration-300 ${
            isMinimized 
              ? 'bottom-6 right-6 w-72 h-14' 
              : 'bottom-6 right-6 w-[380px] h-[500px] sm:w-[420px] sm:h-[560px]'
          }`}
          data-testid="ai-assistant-window"
        >
          {/* Header */}
          <div 
            className="flex items-center justify-between p-3 bg-gradient-to-r from-[#D946EF]/20 to-[#00FFA3]/20 border-b border-white/10 cursor-pointer"
            onClick={isMinimized ? toggleMinimize : undefined}
          >
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-1">
                  Bullpug AI
                  <Sparkles className="w-3 h-3 text-[#FFD700]" />
                </h3>
                {!isMinimized && (
                  <p className="text-[10px] text-slate-400">Your trading assistant</p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-1">
              {!isMinimized && (
                <button
                  onClick={clearChat}
                  className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors text-[10px]"
                  title="Clear chat"
                >
                  Clear
                </button>
              )}
              <button
                onClick={toggleMinimize}
                className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              >
                {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
              </button>
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
                {messages.map((msg, i) => (
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
                ))}
                
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
                <div className="flex gap-2">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask me anything..."
                    disabled={isLoading}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-[#00FFA3]/50 disabled:opacity-50"
                    data-testid="ai-chat-input"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={isLoading || !inputValue.trim()}
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
