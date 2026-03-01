/**
 * TradeForm Component - Modal form for logging/editing trades
 * Features: Live pricing dropdown for asset selection
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { X, Loader2, ChevronDown, TrendingUp, TrendingDown, Search } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TRADE_TYPES = ["Long", "Short", "Spot"];
const STRATEGIES = ["Scalping", "Day Trading", "Swing Trading", "Position Trading", "Breakout", "Mean Reversion", "News Trading", "Other"];
const EMOTIONS = ["Confident", "Calm", "Anxious", "Fearful", "Greedy", "FOMO", "Neutral", "Excited", "Frustrated"];
const GRADES = ["A+", "A", "B+", "B", "C+", "C", "D", "F"];
const MARKET_CONDITIONS = ["Bullish", "Bearish", "Ranging", "High Volatility", "Low Volatility", "Uncertain"];

export default function TradeForm({ trade, onClose, onSave, walletAddress }) {
  const [form, setForm] = useState({
    trade_id: trade?.trade_id || "",
    wallet_address: trade?.wallet_address || walletAddress || "",
    date_entry: trade?.date_entry || new Date().toISOString().split("T")[0],
    date_exit: trade?.date_exit || "",
    asset: trade?.asset || "",
    trade_type: trade?.trade_type || "Long",
    leverage: trade?.leverage || 1,
    entry_price: trade?.entry_price || "",
    position_size: trade?.position_size || "",
    exit_price: trade?.exit_price || "",
    exit_reason: trade?.exit_reason || "",
    stop_loss: trade?.stop_loss || "",
    take_profit: trade?.take_profit || "",
    fees: trade?.fees || 0,
    slippage: trade?.slippage || 0,
    chart_link: trade?.chart_link || "",
    entry_reason: trade?.entry_reason || "",
    strategy: trade?.strategy || "",
    market_conditions: trade?.market_conditions || "",
    expected_rr: trade?.expected_rr || "",
    emotion_entry: trade?.emotion_entry || "",
    emotion_exit: trade?.emotion_exit || "",
    confidence_level: trade?.confidence_level || 5,
    mindset_notes: trade?.mindset_notes || "",
    what_went_well: trade?.what_went_well || "",
    what_went_wrong: trade?.what_went_wrong || "",
    lessons: trade?.lessons || "",
    trade_grade: trade?.trade_grade || "",
    tags: trade?.tags?.join(", ") || "",
    external_influences: trade?.external_influences || "",
    health_notes: trade?.health_notes || "",
    status: trade?.status || "open",
  });
  const [saving, setSaving] = useState(false);
  const [activeSection, setActiveSection] = useState("basic");
  
  // Live pricing state
  const [tradeableAssets, setTradeableAssets] = useState([]);
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [showAssetDropdown, setShowAssetDropdown] = useState(false);
  const [assetSearch, setAssetSearch] = useState("");
  
  // Contract address lookup state
  const [contractAddress, setContractAddress] = useState("");
  const [contractLoading, setContractLoading] = useState(false);
  const [customTokens, setCustomTokens] = useState([]);

  // Major coins in fixed order (always shown at top)
  const MAJOR_COINS = [
    { symbol: "SOL", name: "Solana", coingecko_id: "solana" },
    { symbol: "ETH", name: "Ethereum", coingecko_id: "ethereum" },
    { symbol: "BTC", name: "Bitcoin", coingecko_id: "bitcoin" },
    { symbol: "BNB", name: "BNB", coingecko_id: "binancecoin" },
    { symbol: "DOGE", name: "Dogecoin", coingecko_id: "dogecoin" },
    { symbol: "XRP", name: "XRP", coingecko_id: "ripple" },
  ];

  // Fetch major coin prices
  const fetchMajorPrices = async () => {
    try {
      const { data } = await axios.get(`${API}/ai/prices`);
      if (data.prices) {
        return MAJOR_COINS.map(coin => {
          const priceData = data.prices[coin.symbol] || {};
          return {
            ...coin,
            price: priceData.price || 0,
            change_24h: priceData.change_24h || 0,
            chain: "major"
          };
        });
      }
    } catch (e) {
      console.error("Failed to fetch major prices:", e);
    }
    return MAJOR_COINS.map(c => ({ ...c, price: 0, change_24h: 0, chain: "major" }));
  };

  // Fetch trending/other assets
  const fetchTrendingAssets = async () => {
    try {
      const { data } = await axios.get(`${API}/ai/tradeable-assets`);
      if (data.assets && Array.isArray(data.assets)) {
        // Filter out major coins (we show them separately)
        return data.assets.filter(a => 
          !MAJOR_COINS.some(m => m.symbol === a.symbol)
        );
      }
    } catch (e) {
      console.error("Failed to fetch trending assets:", e);
    }
    return [];
  };

  // Load all assets when dropdown opens
  const loadAssets = async () => {
    if (tradeableAssets.length > 0) return;
    setAssetsLoading(true);
    try {
      const [majorCoins, trendingCoins] = await Promise.all([
        fetchMajorPrices(),
        fetchTrendingAssets()
      ]);
      
      // Combine: Major coins first, then trending
      setTradeableAssets([...majorCoins, ...trendingCoins]);
    } catch (e) {
      console.error("Failed to load assets:", e);
    } finally {
      setAssetsLoading(false);
    }
  };

  // Load assets when dropdown opens
  useEffect(() => {
    if (showAssetDropdown && tradeableAssets.length === 0) {
      loadAssets();
    }
  }, [showAssetDropdown]);

  // Lookup token by contract address
  const lookupContract = async () => {
    if (!contractAddress.trim()) return;
    
    setContractLoading(true);
    try {
      // Try DexScreener API for contract lookup
      const { data } = await axios.get(
        `https://api.dexscreener.com/latest/dex/tokens/${contractAddress.trim()}`
      );
      
      if (data.pairs && data.pairs.length > 0) {
        // Get the highest liquidity pair
        const bestPair = data.pairs.sort((a, b) => 
          (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0)
        )[0];
        
        const token = bestPair.baseToken;
        const newToken = {
          symbol: token.symbol,
          name: token.name,
          price: parseFloat(bestPair.priceUsd) || 0,
          change_24h: parseFloat(bestPair.priceChange?.h24) || 0,
          chain: bestPair.chainId,
          contract_address: contractAddress.trim(),
          isCustom: true
        };
        
        // Add to custom tokens if not already exists
        if (!customTokens.some(t => t.contract_address === contractAddress.trim())) {
          setCustomTokens(prev => [...prev, newToken]);
        }
        
        // Select it immediately
        selectAsset(newToken);
        setContractAddress("");
        toast.success(`Found ${token.symbol} - ${token.name}`);
      } else {
        toast.error("No token found for this contract address");
      }
    } catch (e) {
      console.error("Contract lookup failed:", e);
      toast.error("Failed to lookup contract. Check the address and try again.");
    } finally {
      setContractLoading(false);
    }
  };

  // Combine all assets: Major + Custom + Trending
  const allAssets = [
    ...tradeableAssets.filter(a => a.chain === "major"), // Major coins first
    ...customTokens, // Custom/contract-added tokens
    ...tradeableAssets.filter(a => a.chain !== "major"), // Other trending tokens
  ];

  // Filter assets based on search
  const filteredAssets = allAssets.filter(asset => 
    asset.symbol?.toLowerCase().includes(assetSearch.toLowerCase()) ||
    asset.name?.toLowerCase().includes(assetSearch.toLowerCase())
  );

  // Select asset and auto-fill price
  const selectAsset = (asset) => {
    setForm(prev => ({
      ...prev,
      asset: asset.symbol,
      entry_price: asset.price > 0 ? asset.price.toString() : prev.entry_price
    }));
    setShowAssetDropdown(false);
    setAssetSearch("");
  };

  const handleChange = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.asset || !form.entry_price || !form.position_size) {
      return toast.error("Fill required fields: Asset, Entry Price, Position Size");
    }
    setSaving(true);
    try {
      const payload = {
        ...form,
        entry_price: parseFloat(form.entry_price),
        position_size: parseFloat(form.position_size),
        exit_price: form.exit_price ? parseFloat(form.exit_price) : null,
        stop_loss: form.stop_loss ? parseFloat(form.stop_loss) : null,
        take_profit: form.take_profit ? parseFloat(form.take_profit) : null,
        fees: parseFloat(form.fees) || 0,
        slippage: parseFloat(form.slippage) || 0,
        leverage: parseFloat(form.leverage) || 1,
        expected_rr: form.expected_rr ? parseFloat(form.expected_rr) : null,
        confidence_level: parseInt(form.confidence_level) || null,
        tags: form.tags ? form.tags.split(",").map(t => t.trim()).filter(Boolean) : [],
      };

      if (trade) {
        await axios.put(`${API}/journal/trade/${trade.trade_id}`, payload);
        toast.success("Trade updated!");
      } else {
        await axios.post(`${API}/journal/trade`, payload);
        toast.success("Trade logged!");
      }
      onSave();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save");
    }
    setSaving(false);
  };

  const sections = [
    { id: "basic", label: "Basic Info" },
    { id: "prices", label: "Prices & Sizing" },
    { id: "strategy", label: "Strategy" },
    { id: "psychology", label: "Psychology" },
    { id: "review", label: "Review" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto" data-testid="trade-form-modal">
      <div className="w-full max-w-3xl glass-card rounded-2xl p-6 my-8 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-black uppercase" style={{ fontFamily: 'Orbitron' }}>
            {trade ? "Edit Trade" : "Log New Trade"}
          </h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white" data-testid="close-form-btn">
            <X size={20} />
          </button>
        </div>

        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {sections.map(s => (
            <button
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              className={`px-4 py-2 rounded-lg text-xs font-bold uppercase whitespace-nowrap transition-colors ${
                activeSection === s.id ? "bg-[#00C2FF]/10 text-[#00C2FF]" : "bg-white/5 text-slate-400 hover:text-white"
              }`}
              data-testid={`section-${s.id}`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {activeSection === "basic" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="relative">
                <label className="text-xs text-slate-500 uppercase mb-1 block">Asset *</label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowAssetDropdown(!showAssetDropdown)}
                    className="w-full flex items-center justify-between p-3 bg-black/50 border border-white/10 rounded-lg text-white hover:border-[#00C2FF]/50 transition-colors text-left"
                    data-testid="trade-asset-dropdown"
                  >
                    <span className={form.asset ? "text-white" : "text-slate-500"}>
                      {form.asset || "Select asset..."}
                    </span>
                    <div className="flex items-center gap-2">
                      {form.asset && form.entry_price && (
                        <span className="text-xs text-[#00FFA3]">${parseFloat(form.entry_price).toFixed(4)}</span>
                      )}
                      {assetsLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                      ) : (
                        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${showAssetDropdown ? 'rotate-180' : ''}`} />
                      )}
                    </div>
                  </button>
                  
                  {showAssetDropdown && (
                    <div className="absolute z-50 w-full mt-1 bg-[#0a0a12] border border-white/10 rounded-lg shadow-xl overflow-hidden">
                      {/* Search input */}
                      <div className="p-2 border-b border-white/10">
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                          <input
                            type="text"
                            value={assetSearch}
                            onChange={(e) => setAssetSearch(e.target.value)}
                            placeholder="Search assets..."
                            className="w-full pl-9 pr-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:border-[#00C2FF]/50"
                            data-testid="asset-search"
                          />
                        </div>
                      </div>
                      
                      {/* Contract Address Lookup */}
                      <div className="p-2 border-b border-white/10 bg-[#D946EF]/5">
                        <p className="text-[10px] text-[#D946EF] uppercase font-bold mb-1.5">Lookup by Contract Address</p>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={contractAddress}
                            onChange={(e) => setContractAddress(e.target.value)}
                            placeholder="Paste contract address..."
                            className="flex-1 px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#D946EF]/50 font-mono"
                            data-testid="contract-address-input"
                          />
                          <button
                            type="button"
                            onClick={lookupContract}
                            disabled={contractLoading || !contractAddress.trim()}
                            className="px-3 py-2 bg-[#D946EF]/20 text-[#D946EF] rounded-lg text-xs font-bold hover:bg-[#D946EF]/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                            data-testid="lookup-contract-btn"
                          >
                            {contractLoading ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Search className="w-3 h-3" />
                            )}
                            Find
                          </button>
                        </div>
                      </div>
                      
                      {/* Asset list */}
                      <div className="max-h-60 overflow-y-auto">
                        {/* Major Coins Section */}
                        {!assetSearch && (
                          <div className="px-2 py-1 bg-[#00FFA3]/5 border-b border-white/5">
                            <p className="text-[9px] text-[#00FFA3] uppercase font-bold">Major Coins</p>
                          </div>
                        )}
                        
                        {/* Show major coins first when no search */}
                        {filteredAssets.filter(a => a.chain === "major").map((asset, i) => (
                          <button
                            key={`major-${asset.symbol}-${i}`}
                            type="button"
                            onClick={() => selectAsset(asset)}
                            className="w-full px-3 py-2.5 text-left hover:bg-white/5 flex items-center justify-between border-b border-white/5"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-white font-bold">{asset.symbol}</span>
                              <span className="text-xs text-slate-500">{asset.name}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-slate-300">
                                ${asset.price < 1 ? asset.price.toFixed(6) : asset.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                              </span>
                              {asset.change_24h !== 0 && (
                                <span className={`text-xs flex items-center gap-0.5 ${asset.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                                  {asset.change_24h >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                  {Math.abs(asset.change_24h).toFixed(1)}%
                                </span>
                              )}
                            </div>
                          </button>
                        ))}
                        
                        {/* Custom tokens from contract lookup */}
                        {customTokens.length > 0 && !assetSearch && (
                          <div className="px-2 py-1 bg-[#D946EF]/5 border-b border-white/5">
                            <p className="text-[9px] text-[#D946EF] uppercase font-bold">Your Tokens</p>
                          </div>
                        )}
                        
                        {filteredAssets.filter(a => a.isCustom).map((asset, i) => (
                          <button
                            key={`custom-${asset.symbol}-${i}`}
                            type="button"
                            onClick={() => selectAsset(asset)}
                            className="w-full px-3 py-2 text-left hover:bg-white/5 flex items-center justify-between border-b border-white/5"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-white font-bold">{asset.symbol}</span>
                              <span className="text-xs text-slate-500">{asset.name}</span>
                              <span className="text-[9px] px-1.5 py-0.5 bg-[#D946EF]/20 text-[#D946EF] rounded">
                                {asset.chain}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-slate-300">
                                ${asset.price < 0.01 ? asset.price.toFixed(6) : asset.price.toFixed(4)}
                              </span>
                              <span className={`text-xs flex items-center gap-0.5 ${asset.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                                {asset.change_24h >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                {Math.abs(asset.change_24h).toFixed(1)}%
                              </span>
                            </div>
                          </button>
                        ))}
                        
                        {/* Trending section */}
                        {filteredAssets.filter(a => a.chain !== "major" && !a.isCustom).length > 0 && !assetSearch && (
                          <div className="px-2 py-1 bg-[#00C2FF]/5 border-b border-white/5">
                            <p className="text-[9px] text-[#00C2FF] uppercase font-bold">Trending</p>
                          </div>
                        )}
                        
                        {filteredAssets.filter(a => a.chain !== "major" && !a.isCustom).slice(0, 15).map((asset, i) => (
                          <button
                            key={`trending-${asset.symbol}-${i}`}
                            type="button"
                            onClick={() => selectAsset(asset)}
                            className="w-full px-3 py-2 text-left hover:bg-white/5 flex items-center justify-between border-b border-white/5 last:border-0"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-white font-bold">{asset.symbol}</span>
                              {asset.name && asset.name !== asset.symbol && (
                                <span className="text-xs text-slate-500 truncate max-w-[100px]">{asset.name}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-slate-300">
                                ${asset.price < 0.01 ? asset.price.toFixed(6) : asset.price.toFixed(4)}
                              </span>
                              <span className={`text-xs flex items-center gap-0.5 ${asset.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
                                {asset.change_24h >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                {Math.abs(asset.change_24h).toFixed(1)}%
                              </span>
                            </div>
                          </button>
                        ))}
                        
                        {/* Custom entry option when searching */}
                        {assetSearch && !filteredAssets.some(a => a.symbol?.toLowerCase() === assetSearch.toLowerCase()) && (
                          <button
                            type="button"
                            onClick={() => {
                              setForm(prev => ({ ...prev, asset: assetSearch.toUpperCase() }));
                              setShowAssetDropdown(false);
                              setAssetSearch("");
                            }}
                            className="w-full px-3 py-2 text-left hover:bg-white/5 border-t border-white/10"
                          >
                            <span className="text-[#00C2FF]">+ Add custom: </span>
                            <span className="text-white font-bold">{assetSearch.toUpperCase()}</span>
                          </button>
                        )}
                        
                        {/* Loading state */}
                        {assetsLoading && (
                          <div className="px-3 py-4 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Loading prices...
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Trade Type</label>
                <div className="flex gap-2">
                  {TRADE_TYPES.map(t => (
                    <button key={t} type="button" onClick={() => handleChange("trade_type", t)}
                      className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors ${
                        form.trade_type === t ? "bg-[#00C2FF]/20 text-[#00C2FF] border border-[#00C2FF]/50" : "bg-white/5 text-slate-400 border border-white/10"
                      }`}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Entry Date</label>
                <Input type="date" value={form.date_entry} onChange={e => handleChange("date_entry", e.target.value)}
                  className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Exit Date</label>
                <Input type="date" value={form.date_exit} onChange={e => handleChange("date_exit", e.target.value)}
                  className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Leverage</label>
                <Input type="number" step="0.1" value={form.leverage} onChange={e => handleChange("leverage", e.target.value)}
                  placeholder="1" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Status</label>
                <div className="flex gap-2">
                  {["open", "closed"].map(s => (
                    <button key={s} type="button" onClick={() => handleChange("status", s)}
                      className={`flex-1 py-2 rounded-lg text-xs font-bold uppercase transition-colors ${
                        form.status === s ? "bg-[#00FFA3]/20 text-[#00FFA3] border border-[#00FFA3]/50" : "bg-white/5 text-slate-400 border border-white/10"
                      }`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeSection === "prices" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Entry Price *</label>
                <Input type="number" step="any" value={form.entry_price} onChange={e => handleChange("entry_price", e.target.value)}
                  placeholder="50000" className="bg-black/50 border-white/10 text-white" data-testid="trade-entry-price" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Position Size *</label>
                <Input type="number" step="any" value={form.position_size} onChange={e => handleChange("position_size", e.target.value)}
                  placeholder="0.1" className="bg-black/50 border-white/10 text-white" data-testid="trade-position-size" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Exit Price</label>
                <Input type="number" step="any" value={form.exit_price} onChange={e => handleChange("exit_price", e.target.value)}
                  placeholder="52000" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Exit Reason</label>
                <Input value={form.exit_reason} onChange={e => handleChange("exit_reason", e.target.value)}
                  placeholder="Hit TP / Stopped out / Manual close" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Stop Loss</label>
                <Input type="number" step="any" value={form.stop_loss} onChange={e => handleChange("stop_loss", e.target.value)}
                  placeholder="48000" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Take Profit</label>
                <Input type="number" step="any" value={form.take_profit} onChange={e => handleChange("take_profit", e.target.value)}
                  placeholder="55000" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Fees (USD)</label>
                <Input type="number" step="any" value={form.fees} onChange={e => handleChange("fees", e.target.value)}
                  placeholder="2.50" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Slippage (USD)</label>
                <Input type="number" step="any" value={form.slippage} onChange={e => handleChange("slippage", e.target.value)}
                  placeholder="0.50" className="bg-black/50 border-white/10 text-white" />
              </div>
            </div>
          )}

          {activeSection === "strategy" && (
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Strategy</label>
                <div className="flex flex-wrap gap-2">
                  {STRATEGIES.map(s => (
                    <button key={s} type="button" onClick={() => handleChange("strategy", s)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                        form.strategy === s ? "bg-[#D946EF]/20 text-[#D946EF] border border-[#D946EF]/50" : "bg-white/5 text-slate-400 border border-white/10"
                      }`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Entry Reason</label>
                <textarea value={form.entry_reason} onChange={e => handleChange("entry_reason", e.target.value)}
                  placeholder="Breakout above resistance, bullish divergence on RSI..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[80px]" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Market Conditions</label>
                  <div className="flex flex-wrap gap-2">
                    {MARKET_CONDITIONS.map(m => (
                      <button key={m} type="button" onClick={() => handleChange("market_conditions", m)}
                        className={`px-2 py-1 rounded text-[10px] font-bold transition-colors ${
                          form.market_conditions === m ? "bg-[#00C2FF]/20 text-[#00C2FF]" : "bg-white/5 text-slate-400"
                        }`}>
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Expected R:R</label>
                  <Input type="number" step="0.1" value={form.expected_rr} onChange={e => handleChange("expected_rr", e.target.value)}
                    placeholder="3" className="bg-black/50 border-white/10 text-white" />
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Chart Link</label>
                <Input value={form.chart_link} onChange={e => handleChange("chart_link", e.target.value)}
                  placeholder="https://tradingview.com/..." className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">External Influences</label>
                <Input value={form.external_influences} onChange={e => handleChange("external_influences", e.target.value)}
                  placeholder="Fed announcement, on-chain whale activity..." className="bg-black/50 border-white/10 text-white" />
              </div>
            </div>
          )}

          {activeSection === "psychology" && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Emotion at Entry</label>
                  <div className="flex flex-wrap gap-2">
                    {EMOTIONS.map(e => (
                      <button key={e} type="button" onClick={() => handleChange("emotion_entry", e)}
                        className={`px-2 py-1 rounded text-[10px] font-bold transition-colors ${
                          form.emotion_entry === e ? "bg-[#00FFA3]/20 text-[#00FFA3]" : "bg-white/5 text-slate-400"
                        }`}>
                        {e}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Emotion at Exit</label>
                  <div className="flex flex-wrap gap-2">
                    {EMOTIONS.map(e => (
                      <button key={e} type="button" onClick={() => handleChange("emotion_exit", e)}
                        className={`px-2 py-1 rounded text-[10px] font-bold transition-colors ${
                          form.emotion_exit === e ? "bg-[#D946EF]/20 text-[#D946EF]" : "bg-white/5 text-slate-400"
                        }`}>
                        {e}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Confidence Level: {form.confidence_level}/10</label>
                <input type="range" min="1" max="10" value={form.confidence_level} onChange={e => handleChange("confidence_level", e.target.value)}
                  className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Mindset Notes</label>
                <textarea value={form.mindset_notes} onChange={e => handleChange("mindset_notes", e.target.value)}
                  placeholder="How were you feeling? Any distractions?"
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[80px]" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Health & Lifestyle</label>
                <Input value={form.health_notes} onChange={e => handleChange("health_notes", e.target.value)}
                  placeholder="Good sleep, well rested..." className="bg-black/50 border-white/10 text-white" />
              </div>
            </div>
          )}

          {activeSection === "review" && (
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">What Went Well</label>
                <textarea value={form.what_went_well} onChange={e => handleChange("what_went_well", e.target.value)}
                  placeholder="Good entry timing, followed the plan..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[60px]" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">What Went Wrong</label>
                <textarea value={form.what_went_wrong} onChange={e => handleChange("what_went_wrong", e.target.value)}
                  placeholder="Moved stop too early, oversized position..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[60px]" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Lessons & Adjustments</label>
                <textarea value={form.lessons} onChange={e => handleChange("lessons", e.target.value)}
                  placeholder="Next time I will..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[60px]" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Trade Grade</label>
                  <div className="flex flex-wrap gap-2">
                    {GRADES.map(g => (
                      <button key={g} type="button" onClick={() => handleChange("trade_grade", g)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                          form.trade_grade === g ? "bg-[#F5D300]/20 text-[#F5D300] border border-[#F5D300]/50" : "bg-white/5 text-slate-400 border border-white/10"
                        }`}>
                        {g}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Tags (comma separated)</label>
                  <Input value={form.tags} onChange={e => handleChange("tags", e.target.value)}
                    placeholder="breakout, btc, trending" className="bg-black/50 border-white/10 text-white" />
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-4 border-t border-white/10">
            <Button type="button" onClick={onClose} variant="outline"
              className="flex-1 border-white/20 text-slate-400 hover:text-white rounded-xl py-5">
              Cancel
            </Button>
            <Button type="submit" disabled={saving} data-testid="save-trade-btn"
              className="flex-1 bg-[#00FFA3] text-black font-bold rounded-xl py-5 hover:scale-[1.02] transition-transform">
              {saving ? "Saving..." : trade ? "Update Trade" : "Log Trade"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
