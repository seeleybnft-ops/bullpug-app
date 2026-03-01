/**
 * JournalAIAssistant - Enhanced AI assistant for Trading Journal
 * Refactored to use extracted sub-components for better maintainability
 * Features: Multi-language, Chat interface, Coin recommendations
 */

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { 
  Bot, Sparkles, ChevronDown, ChevronUp, 
  Globe, TrendingUp, Wallet, Loader2, MessageSquare
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWatchlist } from "./Watchlist";

// Import extracted components
import { TopPicksSection, ChatSection, InsightsSection } from "./journal";

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

export default function JournalAIAssistant({ walletAddress, solanaAddress, evmAddress }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState("chat");
  const [language, setLanguage] = useState("en");
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  
  // Watchlist hook
  const { addToWatchlist, walletAddress: watchlistWallet } = useWatchlist();
  const [addingToWatchlist, setAddingToWatchlist] = useState(null);
  
  // Determine effective wallet address
  const effectiveWalletAddress = walletAddress || solanaAddress || evmAddress;
  
  // Insights state
  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  
  // Recommendations state
  const [recommendations, setRecommendations] = useState([]);
  const [volatilePicks, setVolatilePicks] = useState([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [lastRecsUpdate, setLastRecsUpdate] = useState(null);

  // Add to watchlist handler
  const handleAddToWatchlist = async (coin) => {
    if (!watchlistWallet) {
      toast.error("Connect wallet to add to watchlist");
      return;
    }
    setAddingToWatchlist(coin.symbol);
    await addToWatchlist({
      symbol: coin.symbol,
      name: coin.name,
      contract_address: coin.contract_address,
      dex_url: coin.dex_url,
      platform: coin.platform || "Solana",
      price: coin.price
    });
    setAddingToWatchlist(null);
  };

  // Load initial data when wallet connects
  useEffect(() => {
    if (effectiveWalletAddress) {
      fetchInsights();
      fetchRecommendations();
    }
  }, [effectiveWalletAddress, solanaAddress, evmAddress, language]);

  // Fetch recommendations on mount
  useEffect(() => {
    fetchRecommendations();
  }, []);

  // Auto-refresh recommendations every hour
  useEffect(() => {
    const interval = setInterval(fetchRecommendations, 3600000);
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
    if ((!chatInput.trim() && !selectedImage) || chatLoading) return;
    
    const userMessage = chatInput.trim();
    setChatInput("");
    
    // Add user message with optional image
    const newUserMsg = { 
      role: "user", 
      content: userMessage || (selectedImage ? "Please analyze this image" : ""),
      image: imagePreview
    };
    setChatMessages(prev => [...prev, newUserMsg]);
    setChatLoading(true);

    try {
      let requestData = {
        wallet_address: effectiveWalletAddress,
        message: userMessage || "Please analyze this image. Identify any tokens, charts, prices, or crypto-related information.",
        session_id: `journal_${effectiveWalletAddress || 'anon'}_${Date.now()}`,
        active_tab: activeTab,
        chat_history: chatMessages.slice(-10)
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
      }
      
      const { data } = await axios.post(`${API}/ai/chat`, requestData);
      setChatMessages(prev => [...prev, { 
        role: "assistant", 
        content: data.response,
        hasLiveData: data.has_live_data 
      }]);
      
      // Clear image after sending
      setSelectedImage(null);
      setImagePreview(null);
    } catch (e) {
      console.error("Chat error:", e);
      setChatMessages(prev => [...prev, { 
        role: "assistant", 
        content: "Sorry, I encountered an error. Please try again." 
      }]);
    }
    setChatLoading(false);
  };

  // Handle image selection
  const handleImageSelect = (file) => {
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
  };

  const handleImageClear = () => {
    setSelectedImage(null);
    setImagePreview(null);
  };

  // Header component (shared between both states)
  const Header = () => (
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
            Bullpug AI
            <span className="px-1.5 py-0.5 bg-[#00FFA3]/20 text-[#00FFA3] text-[8px] rounded font-medium flex items-center gap-0.5">
              <span className="w-1 h-1 bg-[#00FFA3] rounded-full animate-pulse" />
              LIVE
            </span>
          </h3>
          <p className="text-xs text-slate-400">
            {effectiveWalletAddress ? "Real-time market data" : "Connect wallet to unlock all features"}
          </p>
        </div>
      </div>
      
      {/* Language Dropdown (only when wallet connected) */}
      {effectiveWalletAddress && (
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
      )}

      <button onClick={() => setExpanded(!expanded)}>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400" />
        )}
      </button>
    </div>
  );

  // Render without wallet (limited features)
  if (!effectiveWalletAddress) {
    return (
      <div className="glass-card rounded-2xl overflow-hidden border border-[#D946EF]/30" data-testid="journal-ai-assistant">
        <Header />
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
            <div className="border-t border-white/10 pt-4">
              <TopPicksSection
                recommendations={recommendations}
                volatilePicks={volatilePicks}
                loading={recsLoading}
                lastUpdate={lastRecsUpdate}
                onRefresh={fetchRecommendations}
                onAddToWatchlist={handleAddToWatchlist}
                addingToWatchlist={addingToWatchlist}
                showAutoRefreshNotice={false}
              />
            </div>
          </div>
        )}
      </div>
    );
  }

  // Full featured render (with wallet)
  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-[#D946EF]/30" data-testid="journal-ai-assistant">
      <Header />

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
            {/* Chat Tab */}
            {activeTab === "chat" && (
              <ChatSection
                messages={chatMessages}
                input={chatInput}
                onInputChange={setChatInput}
                onSend={sendChatMessage}
                loading={chatLoading}
              />
            )}

            {/* Recommendations Tab */}
            {activeTab === "recommendations" && (
              <TopPicksSection
                recommendations={recommendations}
                volatilePicks={volatilePicks}
                loading={recsLoading}
                lastUpdate={lastRecsUpdate}
                onRefresh={fetchRecommendations}
                onAddToWatchlist={handleAddToWatchlist}
                addingToWatchlist={addingToWatchlist}
                showAutoRefreshNotice={true}
              />
            )}

            {/* Insights Tab */}
            {activeTab === "insights" && (
              <InsightsSection
                insights={insights}
                loading={insightsLoading}
                onRefresh={fetchInsights}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
