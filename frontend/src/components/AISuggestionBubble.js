import { useState, useEffect } from "react";
import { Bot, Sparkles, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AISuggestionBubble({ 
  type = "exit-simulator", // "exit-simulator" or "journal"
  context = {},
  walletAddress = null,
  className = ""
}) {
  const [suggestion, setSuggestion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [livePrice, setLivePrice] = useState(null);

  useEffect(() => {
    if (type === "exit-simulator" && context.simulated_outcomes) {
      fetchExitSuggestion();
    } else if (type === "journal" && walletAddress) {
      fetchJournalInsight();
    }
  }, [type, context, walletAddress]);

  const fetchExitSuggestion = async () => {
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/ai-suggestions/exit-simulator`, {
        token_symbol: context.token_symbol || "SOL",
        entry_price: context.entry_price || 0,
        current_price: context.current_price || null,
        volatility: context.volatility || 0.5,
        simulated_outcomes: context.simulated_outcomes || {},
        wallet_address: walletAddress
      });
      setSuggestion(data.suggestion);
      setLivePrice(data.live_price);
    } catch (e) {
      console.error("Failed to get AI suggestion:", e);
      setSuggestion("Unable to generate suggestion at this time. Please try again later.");
    }
    setLoading(false);
  };

  const fetchJournalInsight = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/ai-suggestions/journal-daily/${walletAddress}`);
      setSuggestion(data.insight);
      setLivePrice(data.holdings_changes);
    } catch (e) {
      console.error("Failed to get journal insight:", e);
      setSuggestion("Unable to load daily insights. Connect your wallet and log some trades to get personalized suggestions!");
    }
    setLoading(false);
  };

  const refresh = () => {
    if (type === "exit-simulator") {
      fetchExitSuggestion();
    } else {
      fetchJournalInsight();
    }
  };

  if (!suggestion && !loading) return null;

  return (
    <div className={`glass-card rounded-2xl overflow-hidden border border-[#D946EF]/30 ${className}`}>
      {/* Header */}
      <div 
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between p-4 bg-gradient-to-r from-[#D946EF]/10 to-[#00FFA3]/10 cursor-pointer hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#FFD700]" />
              {type === "exit-simulator" ? "AI Trading Insight" : "Daily Trading Pulse"}
            </h3>
            <p className="text-xs text-slate-400">
              {type === "exit-simulator" ? "Based on your simulation results" : "Personalized for you"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={(e) => { e.stopPropagation(); refresh(); }}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4 pt-2">
          {loading ? (
            <div className="space-y-3">
              <div className="h-4 bg-white/10 rounded animate-pulse w-3/4" />
              <div className="h-4 bg-white/10 rounded animate-pulse w-full" />
              <div className="h-4 bg-white/10 rounded animate-pulse w-5/6" />
              <div className="h-4 bg-white/10 rounded animate-pulse w-2/3" />
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
                {suggestion}
              </ReactMarkdown>
            </div>
          )}

          {/* Live Price Info */}
          {livePrice && type === "exit-simulator" && (
            <div className="mt-4 pt-3 border-t border-white/10 flex items-center gap-4 text-xs">
              <span className="text-slate-500">Live Price:</span>
              <span className="text-white font-mono">${livePrice.price?.toFixed(6)}</span>
              <span className={`font-mono ${livePrice.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                {livePrice.change_24h >= 0 ? '+' : ''}{livePrice.change_24h?.toFixed(2)}% (24h)
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
