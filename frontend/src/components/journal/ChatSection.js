/**
 * ChatSection - AI Chat interface for Bullpug AI
 * Extracted from JournalAIAssistant for better maintainability
 */

import { useRef, useEffect } from "react";
import { Send, Loader2, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function ChatSection({
  messages,
  input,
  onInputChange,
  onSend,
  loading
}) {
  const chatEndRef = useRef(null);

  // Auto-scroll when messages change
  useEffect(() => {
    if (messages.length > 0) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div data-testid="chat-section">
      <div className="h-64 overflow-y-auto mb-3 space-y-3 pr-2">
        {messages.length === 0 && (
          <div className="text-center text-slate-500 text-sm py-6">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="font-medium text-white mb-1">Ask me anything with LIVE data!</p>
            <p className="text-xs">Try: "What's the price of SOL?" or "What's trending on Solana?"</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${
              msg.role === "user" 
                ? "bg-[#00FFA3]/20 text-white" 
                : "bg-white/5 text-slate-300"
            }`}>
              {msg.hasLiveData && msg.role === "assistant" && (
                <div className="flex items-center gap-1 mb-1 text-[10px] text-[#00FFA3]">
                  <span className="w-1.5 h-1.5 bg-[#00FFA3] rounded-full animate-pulse" />
                  LIVE DATA
                </div>
              )}
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                  strong: ({ children }) => <strong className="text-white">{children}</strong>,
                }}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/5 px-4 py-3 rounded-xl">
              <Loader2 className="w-4 h-4 animate-spin text-[#D946EF]" />
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>
      
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask about prices, trends, or your trades..."
          className="flex-1 px-4 py-2 rounded-xl bg-black/40 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-[#00FFA3]/50"
          data-testid="ai-chat-input"
        />
        <button
          onClick={onSend}
          disabled={loading || !input.trim()}
          className="px-4 py-2 rounded-xl bg-[#00FFA3] text-black font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#00FFA3]/80 transition-colors"
          data-testid="ai-chat-send"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
