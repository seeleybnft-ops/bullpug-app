/**
 * AI Assistant Chat Component
 * 
 * Interactive AI chat bubble with:
 * - Conversation memory (persists through chat session)
 * - Context-aware suggestions based on current tab
 * - No auto-scroll behavior
 */

import { useState, useRef, useCallback } from "react";
import { Bot, Sparkles, Send, X, Minimize2, Maximize2, Loader2, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import axios from "axios";
import ReactMarkdown from "react-markdown";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AIAssistantChat({ 
  context = "dashboard",
  contextData = {},
  walletAddress = null,
  className = ""
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Context-specific prompts
  const getContextGreeting = () => {
    switch (context) {
      case "dashboard":
        return "I can help analyze your trading performance, spot patterns in your wins/losses, and suggest improvements. What would you like to know?";
      case "portfolio":
        return "I can help you understand your portfolio allocation, identify concentration risks, and suggest rebalancing strategies. Ask me anything!";
      case "import":
        return "I can help you review imported trades, identify missing entries, and explain transaction patterns. How can I assist?";
      case "trades":
        return "I can analyze your trade history, identify your best setups, and help improve your journaling. What's on your mind?";
      case "simulator":
        return "I can explain simulation results, suggest exit strategies based on your risk tolerance, and help interpret probability distributions. What would you like to explore?";
      case "achievements":
        return "I can help you understand badge requirements, track your progress, and suggest strategies to unlock new achievements. Ask away!";
      default:
        return "I'm your AI trading assistant. I can help with portfolio analysis, trade journaling, and strategy suggestions. How can I help?";
    }
  };

  // Open chat and show greeting if first time
  const openChat = () => {
    setIsOpen(true);
    setIsMinimized(false);
    if (messages.length === 0) {
      setMessages([{
        role: "assistant",
        content: getContextGreeting(),
        timestamp: new Date().toISOString()
      }]);
    }
  };

  // Send message to AI
  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString()
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Build conversation history for context
      const conversationHistory = messages.map(m => ({
        role: m.role,
        content: m.content
      }));
      conversationHistory.push({ role: "user", content: userMessage.content });

      const { data } = await axios.post(`${API}/ai-suggestions/chat`, {
        messages: conversationHistory,
        context: context,
        context_data: contextData,
        wallet_address: walletAddress
      });

      const assistantMessage = {
        role: "assistant",
        content: data.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (e) {
      console.error("AI chat error:", e);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "I'm having trouble connecting right now. Please try again in a moment.",
        timestamp: new Date().toISOString(),
        isError: true
      }]);
    }

    setLoading(false);
  }, [input, loading, messages, context, contextData, walletAddress]);

  // Handle enter key
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Clear conversation
  const clearChat = () => {
    setMessages([{
      role: "assistant",
      content: getContextGreeting(),
      timestamp: new Date().toISOString()
    }]);
  };

  // Closed state - floating button
  if (!isOpen) {
    return (
      <button
        onClick={openChat}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-[#D946EF] to-[#00FFA3] shadow-lg shadow-[#D946EF]/30 flex items-center justify-center hover:scale-110 transition-transform ${className}`}
        data-testid="ai-chat-button"
      >
        <Bot className="w-7 h-7 text-white" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#00FFA3] rounded-full flex items-center justify-center">
          <Sparkles className="w-2.5 h-2.5 text-black" />
        </span>
      </button>
    );
  }

  // Minimized state
  if (isMinimized) {
    return (
      <div 
        className="fixed bottom-6 right-6 z-50 bg-[#0a0a12] border border-[#D946EF]/30 rounded-full px-4 py-2 flex items-center gap-3 cursor-pointer hover:border-[#D946EF]/50 transition-colors shadow-lg"
        onClick={() => setIsMinimized(false)}
      >
        <Bot className="w-5 h-5 text-[#D946EF]" />
        <span className="text-sm text-white font-medium">AI Assistant</span>
        <Maximize2 className="w-4 h-4 text-slate-400" />
      </div>
    );
  }

  // Full chat panel
  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 max-w-[calc(100vw-3rem)] bg-[#0a0a12] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[500px]">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-gradient-to-r from-[#D946EF]/10 to-[#00FFA3]/10 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-[#FFD700]" />
              AI Assistant
            </h3>
            <p className="text-[10px] text-slate-500 capitalize">{context} context</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button 
            onClick={clearChat}
            className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            title="Clear chat"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
          <button 
            onClick={() => setIsMinimized(true)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
          <button 
            onClick={() => setIsOpen(false)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages - NO auto scroll */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[200px]">
        {messages.map((message, index) => (
          <div 
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
              message.role === "user" 
                ? "bg-[#00FFA3]/20 text-white" 
                : message.isError 
                  ? "bg-red-500/10 border border-red-500/30 text-red-300"
                  : "bg-white/5 text-slate-300"
            }`}>
              {message.role === "assistant" ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="text-sm mb-2 last:mb-0 leading-relaxed">{children}</p>,
                      strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                      ul: ({ children }) => <ul className="list-disc list-inside space-y-0.5 mb-2 text-sm">{children}</ul>,
                      li: ({ children }) => <li className="text-sm">{children}</li>,
                      code: ({ children }) => <code className="bg-black/30 px-1 rounded text-[#00FFA3] text-xs">{children}</code>,
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm">{message.content}</p>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/5 rounded-2xl px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-[#D946EF] animate-spin" />
              <span className="text-sm text-slate-400">Thinking...</span>
            </div>
          </div>
        )}

        {/* Invisible element for reference, but NOT auto-scrolling to it */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-white/5 bg-black/30">
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything..."
            className="flex-1 bg-black/50 border-white/10 text-white placeholder:text-slate-500 text-sm rounded-xl"
            disabled={loading}
          />
          <Button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] text-white rounded-xl px-4"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-[9px] text-slate-600 mt-2 text-center">
          AI suggestions are for informational purposes only
        </p>
      </div>
    </div>
  );
}
