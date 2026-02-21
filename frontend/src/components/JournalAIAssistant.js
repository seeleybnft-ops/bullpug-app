/**
 * JournalAIAssistant - Enhanced AI assistant for Trading Journal
 * Features: Multi-language, Chat interface, Holdings tracking, Coin recommendations
 */

import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { 
  Bot, Sparkles, ChevronDown, ChevronUp, RefreshCw, Send, 
  Globe, TrendingUp, Wallet, AlertCircle, CheckCircle, 
  ArrowUpRight, ArrowDownRight, Loader2, MessageSquare
} from "lucide-react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Available languages for AI responses
const AI_LANGUAGES = [
  { code: "en", name: "English", flag: "🇺🇸" },
  { code: "es", name: "Español", flag: "🇪🇸" },
  { code: "zh", name: "中文", flag: "🇨🇳" },
  { code: "ja", name: "日本語", flag: "🇯🇵" },
  { code: "ko", name: "한국어", flag: "🇰🇷" },
  { code: "fr", name: "Français", flag: "🇫🇷" },
  { code: "de", name: "Deutsch", flag: "🇩🇪" },
  { code: "pt", name: "Português", flag: "🇧🇷" },
  { code: "ru", name: "Русский", flag: "🇷🇺" },
  { code: "ar", name: "العربية", flag: "🇸🇦" },
];

export default function JournalAIAssistant({ walletAddress }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState("holdings"); // holdings, recommendations, insights, chat
  const [language, setLanguage] = useState("en");
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  
  // Insights state
  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);
  
  // Holdings state
  const [holdings, setHoldings] = useState([]);
  const [holdingsLoading, setHoldingsLoading] = useState(false);
  const [holdingsSuggestions, setHoldingsSuggestions] = useState([]);
  
  // Recommendations state
  const [recommendations, setRecommendations] = useState([]);
  const [recsLoading, setRecsLoading] = useState(false);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Load initial data when wallet connects
  useEffect(() => {
    if (walletAddress) {
      fetchInsights();
      fetchHoldings();
      fetchRecommendations();
    }
  }, [walletAddress, language]);

  // Also fetch recommendations on component mount (no wallet needed)
  useEffect(() => {
    fetchRecommendations();
  }, []);

  // Auto-refresh holdings every 60 seconds when wallet connected
  useEffect(() => {
    if (!walletAddress) return;
    const interval = setInterval(fetchHoldings, 60000);
    return () => clearInterval(interval);
  }, [walletAddress]);

  // Auto-refresh recommendations every 5 minutes
  useEffect(() => {
    const interval = setInterval(fetchRecommendations, 300000);
    return () => clearInterval(interval);
  }, []);

  const fetchInsights = async () => {
    setInsightsLoading(true);
    try {
      const { data } = await axios.get(`${API}/ai-suggestions/journal-daily/${walletAddress}`, {
        params: { language }
      });
      setInsights(data.insight);
    } catch (e) {
      console.error("Failed to fetch insights:", e);
      setInsights("Connect your wallet and log trades to get personalized AI insights!");
    }
    setInsightsLoading(false);
  };

  const fetchHoldings = async () => {
    setHoldingsLoading(true);
    try {
      const { data } = await axios.get(`${API}/ai-suggestions/journal-holdings/${walletAddress}`, {
        params: { language }
      });
      setHoldings(data.holdings || []);
      setHoldingsSuggestions(data.suggestions || []);
    } catch (e) {
      console.error("Failed to fetch holdings:", e);
      setHoldings([]);
    }
    setHoldingsLoading(false);
  };

  const fetchRecommendations = async () => {
    setRecsLoading(true);
    try {
      const { data } = await axios.get(`${API}/ai-suggestions/coin-recommendations`, {
        params: { language }
      });
      setRecommendations(data.recommendations || []);
    } catch (e) {
      console.error("Failed to fetch recommendations:", e);
      setRecommendations([]);
    }
    setRecsLoading(false);
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;
    
    const userMessage = chatInput.trim();
    setChatInput("");
    setChatMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setChatLoading(true);

    try {
      const { data } = await axios.post(`${API}/ai-suggestions/journal-chat`, {
        wallet_address: walletAddress,
        message: userMessage,
        language,
        chat_history: chatMessages.slice(-10) // Send last 10 messages for context
      });
      setChatMessages(prev => [...prev, { role: "assistant", content: data.response }]);
    } catch (e) {
      console.error("Chat error:", e);
      setChatMessages(prev => [...prev, { 
        role: "assistant", 
        content: "Sorry, I encountered an error. Please try again." 
      }]);
    }
    setChatLoading(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  };

  if (!walletAddress) {
    return (
      <div className="glass-card rounded-2xl p-6 border border-[#D946EF]/30">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-white">AI Trading Assistant</h3>
            <p className="text-xs text-slate-400">Connect wallet to unlock AI features</p>
          </div>
        </div>
        <p className="text-slate-500 text-sm">
          Connect your Solana wallet to access personalized AI insights, chat with your trading assistant, 
          track your holdings, and get coin recommendations.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-[#D946EF]/30" data-testid="journal-ai-assistant">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-gradient-to-r from-[#D946EF]/10 to-[#00FFA3]/10">
        <div 
          className="flex items-center gap-3 cursor-pointer flex-1"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center animate-pulse">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#FFD700]" />
              AI Trading Assistant
            </h3>
            <p className="text-xs text-slate-400">Powered by GPT-4o</p>
          </div>
        </div>
        
        {/* Language Dropdown */}
        <div className="relative mr-2">
          <button
            onClick={() => setShowLangDropdown(!showLangDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:border-[#00FFA3]/50 transition-colors"
            data-testid="ai-language-selector"
          >
            <Globe className="w-4 h-4 text-slate-400" />
            <span className="text-sm">{AI_LANGUAGES.find(l => l.code === language)?.flag}</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>
          
          {showLangDropdown && (
            <div className="absolute right-0 top-full mt-1 z-50 w-40 bg-[#0D0D15] border border-white/10 rounded-lg shadow-xl overflow-hidden">
              {AI_LANGUAGES.map(lang => (
                <button
                  key={lang.code}
                  onClick={() => { setLanguage(lang.code); setShowLangDropdown(false); }}
                  className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-white/5 transition-colors ${
                    language === lang.code ? 'bg-[#00FFA3]/10 text-[#00FFA3]' : 'text-slate-300'
                  }`}
                >
                  <span>{lang.flag}</span>
                  <span>{lang.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <button onClick={() => setExpanded(!expanded)}>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>
      </div>

      {/* Content */}
      {expanded && (
        <div>
          {/* Tabs */}
          <div className="flex border-b border-white/10">
            {[
              { id: "holdings", icon: Wallet, label: "Holdings" },
              { id: "recommendations", icon: TrendingUp, label: "Top Picks" },
              { id: "insights", icon: Sparkles, label: "Insights" },
              { id: "chat", icon: MessageSquare, label: "Chat" },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-3 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
                  activeTab === tab.id 
                    ? 'text-[#00FFA3] border-b-2 border-[#00FFA3] bg-[#00FFA3]/5' 
                    : 'text-slate-500 hover:text-white'
                }`}
                data-testid={`ai-tab-${tab.id}`}
              >
                <tab.icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-4">
            {/* Insights Tab */}
            {activeTab === "insights" && (
              <div>
                <div className="flex justify-end mb-3">
                  <button 
                    onClick={fetchInsights}
                    disabled={insightsLoading}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${insightsLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                </div>
                {insightsLoading ? (
                  <div className="space-y-3">
                    <div className="h-4 bg-white/10 rounded animate-pulse w-3/4" />
                    <div className="h-4 bg-white/10 rounded animate-pulse w-full" />
                    <div className="h-4 bg-white/10 rounded animate-pulse w-5/6" />
                  </div>
                ) : (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="text-slate-300 text-sm mb-3 leading-relaxed">{children}</p>,
                        strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                        h1: ({ children }) => <h1 className="text-lg font-bold text-white mt-4 mb-2">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-base font-bold text-white mt-3 mb-2">{children}</h2>,
                        ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3">{children}</ul>,
                        li: ({ children }) => <li className="text-slate-300 text-sm">{children}</li>,
                      }}
                    >
                      {insights || "Loading insights..."}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            )}

            {/* Chat Tab */}
            {activeTab === "chat" && (
              <div>
                <div className="h-64 overflow-y-auto mb-3 space-y-3 pr-2">
                  {chatMessages.length === 0 && (
                    <div className="text-center text-slate-500 text-sm py-8">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>Ask me anything about your trades, portfolio strategy, or market analysis!</p>
                    </div>
                  )}
                  {chatMessages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${
                        msg.role === "user" 
                          ? "bg-[#00FFA3]/20 text-white" 
                          : "bg-white/5 text-slate-300"
                      }`}>
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
                  {chatLoading && (
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
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask about your trades..."
                    className="flex-1 px-4 py-2 rounded-xl bg-black/40 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-[#00FFA3]/50"
                    data-testid="ai-chat-input"
                  />
                  <button
                    onClick={sendChatMessage}
                    disabled={chatLoading || !chatInput.trim()}
                    className="px-4 py-2 rounded-xl bg-[#00FFA3] text-black font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#00FFA3]/80 transition-colors"
                    data-testid="ai-chat-send"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Holdings Tab */}
            {activeTab === "holdings" && (
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-xs font-medium text-slate-400 uppercase">Your Holdings</h4>
                  <button 
                    onClick={fetchHoldings}
                    disabled={holdingsLoading}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${holdingsLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                </div>

                {holdingsLoading ? (
                  <div className="space-y-2">
                    {[1,2,3].map(i => (
                      <div key={i} className="h-12 bg-white/5 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : holdings.length === 0 ? (
                  <p className="text-slate-500 text-sm text-center py-4">
                    No holdings tracked yet. Log trades to see your portfolio here.
                  </p>
                ) : (
                  <div className="space-y-2 mb-4">
                    {holdings.map((holding, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#00FFA3] to-[#00C2FF] flex items-center justify-center text-xs font-bold text-black">
                            {holding.symbol?.slice(0, 2)}
                          </div>
                          <div>
                            <p className="font-medium text-white text-sm">{holding.symbol}</p>
                            <p className="text-xs text-slate-500">{holding.amount} tokens</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-mono text-sm text-white">${holding.value?.toFixed(2)}</p>
                          <p className={`text-xs flex items-center gap-0.5 ${
                            holding.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'
                          }`}>
                            {holding.change_24h >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                            {Math.abs(holding.change_24h || 0).toFixed(2)}%
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* AI Suggestions for Holdings */}
                {holdingsSuggestions.length > 0 && (
                  <div className="border-t border-white/10 pt-3 mt-3">
                    <h4 className="text-xs font-medium text-[#D946EF] uppercase mb-2 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> AI Suggestions
                    </h4>
                    <div className="space-y-2">
                      {holdingsSuggestions.map((suggestion, i) => (
                        <div key={i} className="text-sm text-slate-300 flex items-start gap-2">
                          <CheckCircle className="w-4 h-4 text-[#00FFA3] mt-0.5 flex-shrink-0" />
                          <span>{suggestion}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Recommendations Tab */}
            {activeTab === "recommendations" && (
              <div>
                <div className="flex justify-between items-center mb-3">
                  <div>
                    <h4 className="text-xs font-medium text-slate-400 uppercase">Solana Memecoins</h4>
                    <p className="text-[10px] text-[#00FFA3]">From Pump.fun, Raydium, Orca, Meteora & more</p>
                  </div>
                  <button 
                    onClick={fetchRecommendations}
                    disabled={recsLoading}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${recsLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                </div>

                {recsLoading ? (
                  <div className="space-y-3">
                    {[1,2,3].map(i => (
                      <div key={i} className="h-24 bg-white/5 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : recommendations.length === 0 ? (
                  <p className="text-slate-500 text-sm text-center py-4">
                    No recommendations available at this time. Check back later!
                  </p>
                ) : (
                  <div className="space-y-3">
                    {recommendations.slice(0, 3).map((coin, i) => (
                      <div 
                        key={i} 
                        className={`p-4 rounded-xl border ${
                          i === 0 ? 'bg-gradient-to-r from-[#FFD700]/10 to-transparent border-[#FFD700]/30' :
                          i === 1 ? 'bg-gradient-to-r from-[#C0C0C0]/10 to-transparent border-[#C0C0C0]/30' :
                          'bg-gradient-to-r from-[#CD7F32]/10 to-transparent border-[#CD7F32]/30'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-lg font-bold">
                              {i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'}
                            </span>
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="font-bold text-white">{coin.symbol}</p>
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#D946EF]/20 text-[#D946EF] font-medium">
                                  {coin.platform}
                                </span>
                              </div>
                              <p className="text-xs text-slate-500">{coin.name}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="font-mono text-sm text-white">
                              ${coin.price < 0.001 ? coin.price?.toFixed(8) : coin.price?.toFixed(4)}
                            </p>
                            <p className={`text-xs ${coin.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                              {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(2)}%
                            </p>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div className="bg-black/20 rounded px-2 py-1">
                            <span className="text-slate-500">24h Vol</span>
                            <p className="text-white font-mono">
                              ${coin.volume_24h >= 1000000 
                                ? (coin.volume_24h / 1000000).toFixed(1) + 'M' 
                                : (coin.volume_24h / 1000).toFixed(0) + 'K'}
                            </p>
                          </div>
                          <div className="bg-black/20 rounded px-2 py-1">
                            <span className="text-slate-500">Liquidity</span>
                            <p className="text-white font-mono">
                              ${coin.liquidity_usd >= 1000000 
                                ? (coin.liquidity_usd / 1000000).toFixed(1) + 'M' 
                                : (coin.liquidity_usd / 1000).toFixed(0) + 'K'}
                            </p>
                          </div>
                          <div className="bg-black/20 rounded px-2 py-1">
                            <span className="text-slate-500">Status</span>
                            <p className={`font-medium ${coin.bonded ? 'text-[#00FFA3]' : 'text-yellow-400'}`}>
                              {coin.bonded ? '✓ Strong' : '⚡ New'}
                            </p>
                          </div>
                        </div>
                        <p className="text-xs text-slate-400 mt-2">{coin.reason}</p>
                      </div>
                    ))}
                  </div>
                )}

                <p className="text-[10px] text-slate-600 mt-4 text-center">
                  ⚠️ Memecoins are highly volatile. Not financial advice. Always DYOR.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
