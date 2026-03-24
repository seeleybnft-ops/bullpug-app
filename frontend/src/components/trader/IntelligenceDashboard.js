/**
 * Intelligence Dashboard Component
 * Shows real-time data from all 4 intelligence systems:
 * 1. Real OHLCV Price Data quality
 * 2. Smart Money whale tracking
 * 3. Social Sentiment analysis
 * 4. Jito MEV-protected execution status
 */
import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  Activity, Brain, Shield, TrendingUp, TrendingDown,
  Eye, BarChart3, Database, Zap, RefreshCw, ChevronDown, ChevronUp
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

function SentimentBar({ score, label }) {
  // score: -1 to 1
  const normalizedScore = ((score + 1) / 2) * 100; // 0-100
  const barColor = score > 0.1 ? "#22c55e" : score < -0.1 ? "#ef4444" : "#eab308";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${normalizedScore}%`, backgroundColor: barColor }}
        />
      </div>
      <span className="text-xs font-mono" style={{ color: barColor }}>
        {label}
      </span>
    </div>
  );
}

function FactorRow({ factor }) {
  const scoreColor = factor.score > 0.05 ? "text-green-400" : factor.score < -0.05 ? "text-red-400" : "text-yellow-400";

  return (
    <div className="flex items-center justify-between py-1 border-b border-zinc-800/50 last:border-0">
      <span className="text-xs text-zinc-400 capitalize">
        {factor.factor.replace(/_/g, " ")}
      </span>
      <div className="flex items-center gap-2">
        <span className="text-xs text-zinc-500">{factor.detail}</span>
        <span className={`text-xs font-mono ${scoreColor}`}>
          {factor.score > 0 ? "+" : ""}{(factor.score * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

export default function IntelligenceDashboard({ walletAddress }) {
  const [dashboard, setDashboard] = useState(null);
  const [tokenIntel, setTokenIntel] = useState({});
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [selectedToken, setSelectedToken] = useState(null);

  const TOKENS_TO_CHECK = [
    { symbol: "JUP", mint: "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN" },
    { symbol: "BONK", mint: "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263" },
    { symbol: "WIF", mint: "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm" },
    { symbol: "RAY", mint: "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R" },
    { symbol: "PYTH", mint: "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3" },
    { symbol: "RNDR", mint: "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof" },
  ];

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/ai-trader/intelligence-dashboard`);
      setDashboard(data);
    } catch (err) {
      console.error("Intelligence dashboard error:", err);
    }
    setLoading(false);
  }, []);

  const fetchTokenIntel = useCallback(async (mint, symbol) => {
    try {
      const { data } = await axios.get(`${API}/ai-trader/intelligence/${mint}`);
      setTokenIntel(prev => ({ ...prev, [symbol]: data }));
    } catch (err) {
      console.error(`Intelligence error for ${symbol}:`, err);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const handleTokenSelect = (token) => {
    setSelectedToken(token.symbol === selectedToken ? null : token.symbol);
    if (token.symbol !== selectedToken) {
      fetchTokenIntel(token.mint, token.symbol);
    }
  };

  const intel = selectedToken ? tokenIntel[selectedToken] : null;

  return (
    <div data-testid="intelligence-dashboard" className="bg-zinc-900/80 border border-zinc-800 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        data-testid="intelligence-toggle"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-zinc-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-cyan-500/20 rounded-lg flex items-center justify-center">
            <Brain className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-white">Intelligence Systems</h3>
            <p className="text-xs text-zinc-500">Real data, smart money, sentiment, MEV protection</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {dashboard && (
            <div className="flex gap-1">
              {[
                { label: "Price", ok: dashboard.price_collector?.tokens_with_real_data > 0 },
                { label: "SM", ok: dashboard.smart_money?.recent_signals > 0 },
                { label: "Sent", ok: dashboard.sentiment?.cached_entries > 0 },
                { label: "Jito", ok: true },
              ].map(sys => (
                <span
                  key={sys.label}
                  className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                    sys.ok ? "bg-green-500/20 text-green-400" : "bg-zinc-700 text-zinc-400"
                  }`}
                >
                  {sys.label}
                </span>
              ))}
            </div>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-zinc-800">
          {/* System Status Cards */}
          {dashboard && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 p-3">
              <div data-testid="price-collector-status" className="bg-zinc-800/50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Database className="w-3.5 h-3.5 text-blue-400" />
                  <span className="text-xs font-medium text-white">Real OHLCV</span>
                </div>
                <div className="text-lg font-bold text-blue-400">
                  {dashboard.price_collector?.tokens_with_real_data || 0}/{dashboard.price_collector?.tokens_tracked || 0}
                </div>
                <p className="text-[10px] text-zinc-500">tokens with real data</p>
              </div>

              <div data-testid="smart-money-status" className="bg-zinc-800/50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="w-3.5 h-3.5 text-purple-400" />
                  <span className="text-xs font-medium text-white">Smart Money</span>
                </div>
                <div className="text-lg font-bold text-purple-400">
                  {dashboard.smart_money?.wallets_tracked || 0}
                </div>
                <p className="text-[10px] text-zinc-500">
                  whales tracked / {dashboard.smart_money?.recent_signals || 0} signals
                </p>
              </div>

              <div data-testid="sentiment-status" className="bg-zinc-800/50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 className="w-3.5 h-3.5 text-yellow-400" />
                  <span className="text-xs font-medium text-white">Sentiment</span>
                </div>
                <div className="text-lg font-bold text-yellow-400">
                  {dashboard.sentiment?.cached_entries || 0}
                </div>
                <p className="text-[10px] text-zinc-500">tokens analyzed</p>
              </div>

              <div data-testid="jito-status" className="bg-zinc-800/50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-xs font-medium text-white">Jito MEV</span>
                </div>
                <div className="text-lg font-bold text-green-400">Active</div>
                <p className="text-[10px] text-zinc-500">MEV-protected execution</p>
              </div>
            </div>
          )}

          {/* Token Intelligence */}
          <div className="px-3 pb-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-zinc-400">Token Intelligence</span>
              <button
                data-testid="refresh-intelligence"
                onClick={fetchDashboard}
                className="p-1 hover:bg-zinc-700 rounded transition-colors"
                disabled={loading}
              >
                <RefreshCw className={`w-3 h-3 text-zinc-400 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>

            <div className="flex gap-1.5 flex-wrap mb-3">
              {TOKENS_TO_CHECK.map(token => (
                <button
                  key={token.symbol}
                  data-testid={`intel-token-${token.symbol.toLowerCase()}`}
                  onClick={() => handleTokenSelect(token)}
                  className={`px-2.5 py-1 text-xs rounded-full border transition-all ${
                    selectedToken === token.symbol
                      ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-400"
                      : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-600"
                  }`}
                >
                  {token.symbol}
                </button>
              ))}
            </div>

            {/* Selected Token Intelligence */}
            {intel && selectedToken && (
              <div data-testid="token-intel-detail" className="space-y-3 animate-in fade-in duration-200">
                {/* Sentiment */}
                <div className="bg-zinc-800/30 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-white flex items-center gap-1.5">
                      <Activity className="w-3 h-3 text-yellow-400" />
                      Sentiment Analysis
                    </span>
                    <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                      intel.sentiment?.score > 0.1 ? "bg-green-500/20 text-green-400" :
                      intel.sentiment?.score < -0.1 ? "bg-red-500/20 text-red-400" :
                      "bg-yellow-500/20 text-yellow-400"
                    }`}>
                      {intel.sentiment?.score > 0 ? "+" : ""}{((intel.sentiment?.score || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <SentimentBar
                    score={intel.sentiment?.score || 0}
                    label={intel.sentiment?.label || "neutral"}
                  />
                  {intel.sentiment?.factors && (
                    <div className="mt-2 space-y-0.5">
                      {intel.sentiment.factors.map((f, i) => (
                        <FactorRow key={i} factor={f} />
                      ))}
                    </div>
                  )}
                </div>

                {/* Smart Money */}
                <div className="bg-zinc-800/30 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-white flex items-center gap-1.5">
                      <Eye className="w-3 h-3 text-purple-400" />
                      Smart Money
                    </span>
                    <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                      intel.smart_money?.action === "buy" ? "bg-green-500/20 text-green-400" :
                      intel.smart_money?.action === "sell" ? "bg-red-500/20 text-red-400" :
                      "bg-zinc-700 text-zinc-400"
                    }`}>
                      {intel.smart_money?.action?.toUpperCase() || "NEUTRAL"}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="text-sm font-bold text-white">{intel.smart_money?.whale_count || 0}</div>
                      <div className="text-[10px] text-zinc-500">Whales</div>
                    </div>
                    <div>
                      <div className="text-sm font-bold text-green-400">{intel.smart_money?.buy_count || 0}</div>
                      <div className="text-[10px] text-zinc-500">Buys</div>
                    </div>
                    <div>
                      <div className="text-sm font-bold text-red-400">{intel.smart_money?.sell_count || 0}</div>
                      <div className="text-[10px] text-zinc-500">Sells</div>
                    </div>
                  </div>
                  {intel.smart_money?.total_sol > 0 && (
                    <p className="text-[10px] text-zinc-500 mt-1 text-center">
                      Total volume: {intel.smart_money.total_sol} SOL
                    </p>
                  )}
                </div>

                {/* Data Quality */}
                <div className="bg-zinc-800/30 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-white flex items-center gap-1.5">
                      <Database className="w-3 h-3 text-blue-400" />
                      Data Quality
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded ${
                      intel.data_quality?.has_real_data
                        ? "bg-green-500/20 text-green-400"
                        : "bg-orange-500/20 text-orange-400"
                    }`}>
                      {intel.data_quality?.has_real_data ? "REAL OHLCV" : "COLLECTING..."}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-zinc-500">
                      {intel.data_quality?.candles || 0} candles collected
                    </span>
                    {intel.data_quality?.latest_price && (
                      <span className="text-zinc-400 font-mono">
                        ${Number(intel.data_quality.latest_price).toFixed(4)}
                      </span>
                    )}
                  </div>
                  {!intel.data_quality?.has_real_data && (
                    <p className="text-[10px] text-orange-400/70 mt-1">
                      Need {20 - (intel.data_quality?.candles || 0)} more candles (~{Math.ceil((20 - (intel.data_quality?.candles || 0)) * 5 / 60)}h) for real data
                    </p>
                  )}
                </div>

                {/* Combined Confidence Adjustment */}
                <div className="flex items-center justify-between bg-zinc-800/30 rounded-lg px-3 py-2">
                  <span className="text-xs text-zinc-400">Combined Confidence Adjustment</span>
                  <span className={`text-sm font-bold font-mono ${
                    intel.combined_confidence_adj > 0 ? "text-green-400" :
                    intel.combined_confidence_adj < 0 ? "text-red-400" :
                    "text-zinc-400"
                  }`}>
                    {intel.combined_confidence_adj > 0 ? "+" : ""}
                    {((intel.combined_confidence_adj || 0) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
