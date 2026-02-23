/**
 * JournalAIAssistant - Enhanced AI assistant for Trading Journal
 * Features: Multi-language, Chat interface, Holdings tracking, Coin recommendations
 */

import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { 
  Bot, Sparkles, ChevronDown, ChevronUp, RefreshCw, Send, 
  Globe, TrendingUp, Wallet, AlertCircle, CheckCircle, 
  ArrowUpRight, ArrowDownRight, Loader2, MessageSquare,
  Copy, ExternalLink, Brain, Star
} from "lucide-react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { useWatchlist } from "./Watchlist";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Helper to copy text to clipboard
const copyToClipboard = async (text, label = "Address") => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`${label} copied!`);
  } catch (e) {
    // Fallback for older browsers
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand("copy");
    document.body.removeChild(textArea);
    toast.success(`${label} copied!`);
  }
};

// Truncate address for display
const truncateAddress = (address) => {
  if (!address) return "";
  if (address.length <= 12) return address;
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
};

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

export default function JournalAIAssistant({ walletAddress, solanaAddress, evmAddress }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState("chat"); // chat, recommendations, insights
  const [language, setLanguage] = useState("en");
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  
  // Watchlist hook
  const { addToWatchlist, walletAddress: watchlistWallet } = useWatchlist();
  const [addingToWatchlist, setAddingToWatchlist] = useState(null);
  
  // Determine effective wallet address (for backward compatibility)
  const effectiveWalletAddress = walletAddress || solanaAddress || evmAddress;
  
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

  // Add to watchlist handler
  const handleAddToWatchlist = async (coin) => {
    if (!watchlistWallet) {
      toast.error("Connect wallet to add to watchlist");
      return;
    }
    setAddingToWatchlist(coin.symbol);
    const success = await addToWatchlist({
      symbol: coin.symbol,
      name: coin.name,
      contract_address: coin.contract_address,
      dex_url: coin.dex_url,
      platform: coin.platform || "Solana",
      price: coin.price
    });
    setAddingToWatchlist(null);
  };

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Load initial data when wallet connects
  useEffect(() => {
    if (effectiveWalletAddress) {
      fetchInsights();
      fetchHoldings();
      fetchRecommendations();
    }
  }, [effectiveWalletAddress, solanaAddress, evmAddress, language]);

  // Also fetch recommendations on component mount (no wallet needed)
  useEffect(() => {
    fetchRecommendations();
  }, []);

  // Auto-refresh holdings every 60 seconds when wallet connected
  useEffect(() => {
    if (!effectiveWalletAddress) return;
    const interval = setInterval(fetchHoldings, 60000);
    return () => clearInterval(interval);
  }, [effectiveWalletAddress, solanaAddress, evmAddress]);

  // Auto-refresh recommendations every HOUR (3600000 ms)
  useEffect(() => {
    fetchRecommendations(); // Fetch immediately on mount
    const interval = setInterval(fetchRecommendations, 3600000); // 1 hour
    return () => clearInterval(interval);
  }, []);

  const fetchInsights = async () => {
    setInsightsLoading(true);
    try {
      const { data } = await axios.get(`${API}/ai-suggestions/journal-daily/${effectiveWalletAddress}`, {
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
      // Fetch actual wallet holdings from portfolio endpoint (uses Alchemy)
      const params = new URLSearchParams();
      
      // Use both Solana and EVM addresses if available
      if (solanaAddress) {
        params.append('solana_address', solanaAddress);
      }
      if (evmAddress) {
        params.append('evm_address', evmAddress);
      }
      
      // Fallback: detect address type from walletAddress prop
      if (!solanaAddress && !evmAddress && walletAddress) {
        const isSolanaAddress = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(walletAddress);
        if (isSolanaAddress) {
          params.append('solana_address', walletAddress);
        } else {
          params.append('evm_address', walletAddress);
        }
      }
      
      // If no addresses, show empty state
      if (!params.toString()) {
        setHoldings([]);
        setHoldingsSuggestions(["Connect a wallet to view your holdings."]);
        setHoldingsLoading(false);
        return;
      }
      
      const { data: portfolioData } = await axios.get(`${API}/portfolio/combined?${params.toString()}`);
      
      // Transform portfolio data to holdings format
      const transformedHoldings = [];
      
      // Process EVM chains
      if (portfolioData.chains) {
        portfolioData.chains.forEach(chain => {
          // Add native token
          if (chain.native_balance > 0) {
            transformedHoldings.push({
              symbol: chain.native_symbol,
              amount: chain.native_balance,
              value: chain.native_value_usd || 0,
              change_24h: 0,
              chain: chain.chain_name
            });
          }
          // Add other tokens
          chain.tokens?.forEach(token => {
            if (token.balance > 0.0001) {
              transformedHoldings.push({
                symbol: token.symbol,
                amount: token.balance,
                value: token.value_usd || 0,
                change_24h: 0,
                chain: chain.chain_name
              });
            }
          });
        });
      }
      
      // Process Solana
      if (portfolioData.solana) {
        if (portfolioData.solana.native_balance > 0) {
          transformedHoldings.push({
            symbol: 'SOL',
            amount: portfolioData.solana.native_balance,
            value: portfolioData.solana.native_value_usd || 0,
            change_24h: 0,
            chain: 'Solana'
          });
        }
        portfolioData.solana.tokens?.forEach(token => {
          if (token.balance > 0.0001) {
            transformedHoldings.push({
              symbol: token.symbol,
              amount: token.balance,
              value: token.value_usd || 0,
              change_24h: 0,
              chain: 'Solana'
            });
          }
        });
      }
      
      // Sort by value descending
      transformedHoldings.sort((a, b) => (b.value || 0) - (a.value || 0));
      
      setHoldings(transformedHoldings.slice(0, 10));
      
      // Generate suggestions based on holdings
      if (transformedHoldings.length > 0) {
        const totalValue = transformedHoldings.reduce((sum, h) => sum + (h.value || 0), 0);
        const topHolding = transformedHoldings[0];
        const chainCount = new Set(transformedHoldings.map(h => h.chain)).size;
        
        setHoldingsSuggestions([
          `Total portfolio value: $${totalValue.toFixed(2)} across ${chainCount} chain${chainCount > 1 ? 's' : ''}.`,
          `Largest position: ${topHolding.symbol} (${topHolding.chain}) at $${topHolding.value?.toFixed(2)}.`,
          chainCount === 1 ? "Consider diversifying across multiple chains." : "Good diversification across chains!"
        ]);
      } else {
        setHoldingsSuggestions([
          "No tokens detected in your wallet.",
          "Make sure your wallet is connected properly.",
          "Check the Portfolio Value tab for more details."
        ]);
      }
    } catch (e) {
      console.error("Failed to fetch holdings:", e);
      // Fallback to journal-based holdings
      try {
        if (effectiveWalletAddress) {
          const { data } = await axios.get(`${API}/ai-suggestions/journal-holdings/${effectiveWalletAddress}`, {
            params: { language }
          });
          setHoldings(data.holdings || []);
          setHoldingsSuggestions(data.suggestions || []);
        }
      } catch (fallbackError) {
        console.error("Fallback holdings also failed:", fallbackError);
        setHoldings([]);
        setHoldingsSuggestions(["Unable to load holdings. Please try again."]);
      }
    }
    setHoldingsLoading(false);
  };

  // Volatile picks state
  const [volatilePicks, setVolatilePicks] = useState([]);
  const [lastRecsUpdate, setLastRecsUpdate] = useState(null);

  const fetchRecommendations = async () => {
    setRecsLoading(true);
    try {
      const { data } = await axios.get(`${API}/ai-suggestions/coin-recommendations`, {
        params: { language }
      });
      setRecommendations(data.safe_picks || data.recommendations || []);
      setVolatilePicks(data.volatile_picks || []);
      setLastRecsUpdate(new Date());
    } catch (e) {
      console.error("Failed to fetch recommendations:", e);
      setRecommendations([]);
      setVolatilePicks([]);
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
      // Use the new real-time AI chat endpoint
      const { data } = await axios.post(`${API}/ai/chat`, {
        wallet_address: effectiveWalletAddress,
        message: userMessage,
        session_id: `journal_${effectiveWalletAddress || 'anon'}_${Date.now()}`,
        active_tab: activeTab,
        chat_history: chatMessages.slice(-10)
      });
      setChatMessages(prev => [...prev, { 
        role: "assistant", 
        content: data.response,
        hasLiveData: data.has_live_data 
      }]);
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

  if (!effectiveWalletAddress) {
    return (
      <div className="glass-card rounded-2xl overflow-hidden border border-[#D946EF]/30" data-testid="journal-ai-assistant">
        {/* Header - Always visible */}
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
                <span className="px-1.5 py-0.5 bg-[#00FFA3]/20 text-[#00FFA3] text-[8px] rounded font-medium flex items-center gap-0.5">
                  <span className="w-1 h-1 bg-[#00FFA3] rounded-full animate-pulse" />
                  LIVE
                </span>
              </h3>
              <p className="text-xs text-slate-400">Connect wallet to unlock all features</p>
            </div>
          </div>
          <button onClick={() => setExpanded(!expanded)}>
            {expanded ? (
              <ChevronUp className="w-5 h-5 text-slate-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400" />
            )}
          </button>
        </div>

        {/* Content when no wallet - still show Top Picks */}
        {expanded && (
          <div className="p-4">
            <div className="text-center mb-4 p-4 bg-white/5 rounded-xl border border-dashed border-white/20">
              <Wallet className="w-8 h-8 mx-auto mb-2 text-[#00FFA3] opacity-70" />
              <p className="text-white font-medium mb-1">Connect Your Wallet</p>
              <p className="text-slate-400 text-sm">
                Access personalized AI insights, track your holdings, and chat with your trading assistant.
              </p>
            </div>

            {/* Show Top Picks even without wallet */}
            <div className="border-t border-white/10 pt-4 space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="text-xs font-medium text-white uppercase">Top Picks</h4>
                  <p className="text-[10px] text-slate-500">Safe & High-Risk Solana Memecoins</p>
                </div>
                <button 
                  onClick={fetchRecommendations}
                  disabled={recsLoading}
                  className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${recsLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>
              
              {recsLoading ? (
                <div className="space-y-2">
                  {[1,2,3,4,5,6].map(i => (
                    <div key={i} className="h-16 bg-white/5 rounded-lg animate-pulse" />
                  ))}
                </div>
              ) : (
                <>
                  {/* Safe Picks */}
                  <div>
                    <h5 className="text-[10px] font-bold text-[#00FFA3] mb-2 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> SAFER PICKS
                    </h5>
                    <div className="space-y-2">
                      {recommendations.slice(0, 3).map((coin, i) => (
                        <div key={i} className="p-2.5 bg-[#00FFA3]/5 rounded-lg border border-[#00FFA3]/20 hover:bg-[#00FFA3]/10 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#00FFA3] to-[#00C2FF] flex items-center justify-center text-[10px] font-bold text-black">
                                {i + 1}
                              </div>
                              <div>
                                <p className="font-medium text-white text-xs">{coin.symbol}</p>
                                <p className="text-[9px] text-slate-500">{coin.platform}</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="font-mono text-xs text-white">${coin.price < 0.001 ? coin.price?.toFixed(6) : coin.price?.toFixed(4)}</p>
                              <p className={`text-[10px] ${coin.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                                {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(1)}%
                              </p>
                            </div>
                          </div>
                          {/* Contract Address & DEX Link */}
                          <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between">
                            {coin.contract_address ? (
                              <button 
                                onClick={() => copyToClipboard(coin.contract_address, "Contract")}
                                className="flex items-center gap-1 text-[9px] text-slate-500 hover:text-white transition-colors group"
                                title="Click to copy"
                              >
                                <Copy className="w-2.5 h-2.5 group-hover:text-[#00FFA3]" />
                                <span className="font-mono">{truncateAddress(coin.contract_address)}</span>
                              </button>
                            ) : (
                              <span className="text-[9px] text-slate-600">-</span>
                            )}
                            <div className="flex items-center gap-2">
                              {/* Add to Watchlist Button */}
                              <button
                                onClick={() => handleAddToWatchlist(coin)}
                                disabled={addingToWatchlist === coin.symbol}
                                className="flex items-center gap-1 text-[9px] text-[#FFD700] hover:text-white transition-colors"
                                title="Add to Watchlist"
                              >
                                <Star className={`w-2.5 h-2.5 ${addingToWatchlist === coin.symbol ? 'animate-pulse' : ''}`} />
                              </button>
                              {coin.dex_url ? (
                                <a 
                                  href={coin.dex_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[9px] text-[#00FFA3] hover:text-white transition-colors"
                                >
                                  <ExternalLink className="w-2.5 h-2.5" />
                                  Trade
                                </a>
                              ) : (
                                <a 
                                  href={`https://dexscreener.com/solana?q=${coin.symbol}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[9px] text-[#00FFA3] hover:text-white transition-colors"
                                >
                                  <ExternalLink className="w-2.5 h-2.5" />
                                  Find
                                </a>
                              )}
                            </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Volatile Picks */}
                  <div>
                    <h5 className="text-[10px] font-bold text-[#FF6B6B] mb-2 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> HIGH RISK / HIGH REWARD
                    </h5>
                    <div className="space-y-2">
                      {volatilePicks.slice(0, 3).map((coin, i) => (
                        <div key={i} className="p-2.5 bg-[#FF6B6B]/5 rounded-lg border border-[#FF6B6B]/20 hover:bg-[#FF6B6B]/10 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#FF6B6B] to-[#FF8C00] flex items-center justify-center text-[10px] font-bold text-white">
                                ⚡
                              </div>
                              <div>
                                <p className="font-medium text-white text-xs">{coin.symbol}</p>
                                <p className="text-[9px] text-slate-500">{coin.platform}</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="font-mono text-xs text-white">${coin.price < 0.001 ? coin.price?.toFixed(6) : coin.price?.toFixed(4)}</p>
                              <p className={`text-[10px] ${coin.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                                {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(1)}%
                              </p>
                            </div>
                          </div>
                          {/* Contract Address & DEX Link */}
                          <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between">
                            {coin.contract_address ? (
                              <button 
                                onClick={() => copyToClipboard(coin.contract_address, "Contract")}
                                className="flex items-center gap-1 text-[9px] text-slate-500 hover:text-white transition-colors group"
                                title="Click to copy"
                              >
                                <Copy className="w-2.5 h-2.5 group-hover:text-[#FF6B6B]" />
                                <span className="font-mono">{truncateAddress(coin.contract_address)}</span>
                              </button>
                            ) : (
                              <span className="text-[9px] text-slate-600">-</span>
                            )}
                            <div className="flex items-center gap-2">
                              {/* Add to Watchlist Button */}
                              <button
                                onClick={() => handleAddToWatchlist(coin)}
                                disabled={addingToWatchlist === coin.symbol}
                                className="flex items-center gap-1 text-[9px] text-[#FFD700] hover:text-white transition-colors"
                                title="Add to Watchlist"
                              >
                                <Star className={`w-2.5 h-2.5 ${addingToWatchlist === coin.symbol ? 'animate-pulse' : ''}`} />
                              </button>
                              {coin.dex_url ? (
                                <a 
                                  href={coin.dex_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[9px] text-[#FF6B6B] hover:text-white transition-colors"
                                >
                                  <ExternalLink className="w-2.5 h-2.5" />
                                  Trade
                                </a>
                              ) : (
                                <a 
                                  href={`https://dexscreener.com/solana?q=${coin.symbol}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[9px] text-[#FF6B6B] hover:text-white transition-colors"
                                >
                                  <ExternalLink className="w-2.5 h-2.5" />
                                  Find
                                </a>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                      {volatilePicks.length === 0 && (
                        <p className="text-slate-500 text-[10px] text-center py-2">No volatile picks available</p>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
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
              <span className="px-1.5 py-0.5 bg-[#00FFA3]/20 text-[#00FFA3] text-[8px] rounded font-medium flex items-center gap-0.5">
                <span className="w-1 h-1 bg-[#00FFA3] rounded-full animate-pulse" />
                LIVE
              </span>
            </h3>
            <p className="text-xs text-slate-400">Real-time market data</p>
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
              { id: "chat", icon: MessageSquare, label: "Chat" },
              { id: "recommendations", icon: TrendingUp, label: "Top Picks" },
              { id: "insights", icon: Sparkles, label: "Insights" },
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
                    <div className="text-center text-slate-500 text-sm py-6">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="font-medium text-white mb-1">Ask me anything with LIVE data!</p>
                      <p className="text-xs">Try: "What's the price of SOL?" or "What's trending on Solana?"</p>
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
                    placeholder="Ask about prices, trends, or your trades..."
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

            {/* Recommendations Tab */}
            {activeTab === "recommendations" && (
              <div>
                <div className="flex justify-between items-center mb-3">
                  <div>
                    <h4 className="text-xs font-medium text-slate-400 uppercase">Top Picks</h4>
                    <p className="text-[10px] text-slate-500">
                      Safe & High-Risk Solana Memecoins
                      {lastRecsUpdate && (
                        <span className="ml-2 text-slate-600">
                          • Updated {lastRecsUpdate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </span>
                      )}
                    </p>
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

                {/* Auto-refresh notice */}
                <div className="mb-3 px-2 py-1 bg-[#00FFA3]/5 rounded-lg text-[10px] text-slate-500 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-[#00FFA3] rounded-full animate-pulse" />
                  Auto-refreshes every hour with fresh picks
                </div>

                {recsLoading ? (
                  <div className="space-y-3">
                    {[1,2,3,4,5,6].map(i => (
                      <div key={i} className="h-16 bg-white/5 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Safe Picks */}
                    <div>
                      <h5 className="text-xs font-bold text-[#00FFA3] mb-2 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> SAFER PICKS
                      </h5>
                      <div className="space-y-2">
                        {recommendations.slice(0, 3).map((coin, i) => (
                          <div key={i} className="p-3 bg-[#00FFA3]/5 rounded-lg border border-[#00FFA3]/20 hover:bg-[#00FFA3]/10 transition-colors">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#00FFA3] to-[#00C2FF] flex items-center justify-center text-xs font-bold text-black">
                                  #{i + 1}
                                </div>
                                <div>
                                  <div className="flex items-center gap-1.5">
                                    <p className="font-medium text-white text-sm">{coin.symbol}</p>
                                    <span className="text-[8px] px-1 py-0.5 rounded bg-[#00FFA3]/20 text-[#00FFA3]">{coin.platform}</span>
                                  </div>
                                  <p className="text-[10px] text-slate-500 truncate max-w-[150px]">{coin.name}</p>
                                </div>
                              </div>
                              <div className="text-right">
                                <p className="font-mono text-sm text-white">${coin.price < 0.001 ? coin.price?.toFixed(6) : coin.price?.toFixed(4)}</p>
                                <p className={`text-xs flex items-center gap-0.5 justify-end ${coin.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                                  {coin.change_24h >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                                  {Math.abs(coin.change_24h || 0).toFixed(1)}%
                                </p>
                              </div>
                            </div>
                            
                            {/* Contract Address & Exchange Link */}
                            <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between">
                              {coin.contract_address ? (
                                <button 
                                  onClick={() => copyToClipboard(coin.contract_address, "Contract")}
                                  className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition-colors group"
                                  title="Click to copy contract address"
                                >
                                  <Copy className="w-3 h-3 group-hover:text-[#00FFA3]" />
                                  <span className="font-mono">{truncateAddress(coin.contract_address)}</span>
                                </button>
                              ) : (
                                <span className="text-[10px] text-slate-600">No contract</span>
                              )}
                              
                              {coin.dex_url ? (
                                <a 
                                  href={coin.dex_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[10px] text-[#00FFA3] hover:text-white transition-colors"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  Trade on DEX
                                </a>
                              ) : (
                                <a 
                                  href={`https://dexscreener.com/solana?q=${coin.symbol}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[10px] text-[#00FFA3] hover:text-white transition-colors"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  Find on DEX
                                </a>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Volatile Picks */}
                    <div>
                      <h5 className="text-xs font-bold text-[#FF6B6B] mb-2 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" /> HIGH RISK / HIGH REWARD
                      </h5>
                      <div className="space-y-2">
                        {volatilePicks.slice(0, 3).map((coin, i) => (
                          <div key={i} className="p-3 bg-[#FF6B6B]/5 rounded-lg border border-[#FF6B6B]/20 hover:bg-[#FF6B6B]/10 transition-colors">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#FF6B6B] to-[#FF8C00] flex items-center justify-center text-xs font-bold text-white">
                                  ⚡
                                </div>
                                <div>
                                  <div className="flex items-center gap-1.5">
                                    <p className="font-medium text-white text-sm">{coin.symbol}</p>
                                    <span className="text-[8px] px-1 py-0.5 rounded bg-[#FF6B6B]/20 text-[#FF6B6B]">{coin.platform}</span>
                                  </div>
                                  <p className="text-[10px] text-slate-500 truncate max-w-[150px]">{coin.name}</p>
                                </div>
                              </div>
                              <div className="text-right">
                                <p className="font-mono text-sm text-white">${coin.price < 0.001 ? coin.price?.toFixed(6) : coin.price?.toFixed(4)}</p>
                                <p className={`text-xs flex items-center gap-0.5 justify-end ${coin.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                                  {coin.change_24h >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                                  {Math.abs(coin.change_24h || 0).toFixed(1)}%
                                </p>
                              </div>
                            </div>
                            
                            {/* Contract Address & Exchange Link */}
                            <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between">
                              {coin.contract_address ? (
                                <button 
                                  onClick={() => copyToClipboard(coin.contract_address, "Contract")}
                                  className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition-colors group"
                                  title="Click to copy contract address"
                                >
                                  <Copy className="w-3 h-3 group-hover:text-[#FF6B6B]" />
                                  <span className="font-mono">{truncateAddress(coin.contract_address)}</span>
                                </button>
                              ) : (
                                <span className="text-[10px] text-slate-600">No contract</span>
                              )}
                              
                              {coin.dex_url ? (
                                <a 
                                  href={coin.dex_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[10px] text-[#FF6B6B] hover:text-white transition-colors"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  Trade on DEX
                                </a>
                              ) : (
                                <a 
                                  href={`https://dexscreener.com/solana?q=${coin.symbol}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-[10px] text-[#FF6B6B] hover:text-white transition-colors"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  Find on DEX
                                </a>
                              )}
                            </div>
                          </div>
                        ))}
                        {volatilePicks.length === 0 && (
                          <p className="text-slate-500 text-xs text-center py-2">No volatile picks found at this time</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <p className="text-[10px] text-slate-600 mt-4 text-center">
                  ⚠️ Memecoins are highly volatile. "Safer" means relatively lower risk, not safe. Always DYOR.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
