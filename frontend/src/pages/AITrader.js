/**
 * AI Trading Bot Page - Bullpug AI Agent
 * Semi-automated trading with user approval
 */

import { useState, useEffect, useCallback } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import axios from "axios";
import {
  Bot, Settings, TrendingUp, TrendingDown, AlertTriangle, 
  Check, X, Loader2, RefreshCw, Zap, Shield, Skull,
  DollarSign, Target, Clock, ArrowRight, ChevronDown, ChevronUp,
  Wallet, History, Play, Pause, Info
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Risk level colors
const RISK_COLORS = {
  safer: { bg: "bg-[#00FFA3]/10", text: "text-[#00FFA3]", border: "border-[#00FFA3]/30" },
  high_risk: { bg: "bg-[#FF6B6B]/10", text: "text-[#FF6B6B]", border: "border-[#FF6B6B]/30" }
};

export default function AITrader() {
  const { publicKey, connected } = useWallet();
  const walletAddress = publicKey?.toString();

  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState(null);
  const [tokens, setTokens] = useState({ safer: [], high_risk: [] });
  const [signals, setSignals] = useState([]);
  const [positions, setPositions] = useState([]);
  const [history, setHistory] = useState({ trades: [], stats: {} });
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [activeTab, setActiveTab] = useState("signals");
  const [showSettings, setShowSettings] = useState(false);

  // Fetch all data
  const fetchData = useCallback(async () => {
    if (!walletAddress) return;
    setLoading(true);
    try {
      const [settingsRes, tokensRes, signalsRes, positionsRes, historyRes] = await Promise.all([
        axios.get(`${API}/ai-trader/settings/${walletAddress}`),
        axios.get(`${API}/ai-trader/tokens`),
        axios.get(`${API}/ai-trader/signals/${walletAddress}`),
        axios.get(`${API}/ai-trader/positions/${walletAddress}`),
        axios.get(`${API}/ai-trader/history/${walletAddress}`)
      ]);
      
      setSettings(settingsRes.data);
      setTokens({
        safer: tokensRes.data.safer_tokens || [],
        high_risk: tokensRes.data.high_risk_tokens || []
      });
      setSignals(signalsRes.data.signals || []);
      setPositions(positionsRes.data.positions || []);
      setHistory({
        trades: historyRes.data.trades || [],
        stats: historyRes.data.stats || {}
      });
      
      // Check if disclaimer was accepted before
      const accepted = localStorage.getItem(`ai_trader_disclaimer_${walletAddress}`);
      if (accepted === "true") {
        setDisclaimerAccepted(true);
        setShowDisclaimer(false);
      }
    } catch (e) {
      console.error("Error fetching data:", e);
    }
    setLoading(false);
  }, [walletAddress]);

  useEffect(() => {
    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Accept disclaimer
  const acceptDisclaimer = () => {
    setDisclaimerAccepted(true);
    setShowDisclaimer(false);
    localStorage.setItem(`ai_trader_disclaimer_${walletAddress}`, "true");
    toast.success("Disclaimer accepted - AI Trader enabled");
  };

  // Save settings
  const saveSettings = async (newSettings) => {
    try {
      await axios.post(`${API}/ai-trader/settings`, {
        wallet_address: walletAddress,
        ...newSettings
      });
      setSettings(prev => ({ ...prev, ...newSettings }));
      toast.success("Settings saved");
      setShowSettings(false);
    } catch (e) {
      toast.error("Failed to save settings");
    }
  };

  // Scan for signals
  const scanMarkets = async () => {
    setScanning(true);
    try {
      const { data } = await axios.get(`${API}/ai-trader/scan-all/${walletAddress}`);
      if (data.signals_generated > 0) {
        toast.success(`${data.signals_generated} trading signal(s) found!`);
        setSignals(prev => [...data.signals, ...prev]);
      } else {
        toast.info("No strong trading signals at this time");
      }
    } catch (e) {
      toast.error("Failed to scan markets");
    }
    setScanning(false);
  };

  // Approve signal
  const approveSignal = async (signalId) => {
    try {
      const { data } = await axios.post(`${API}/ai-trader/signals/approve`, {
        signal_id: signalId,
        wallet_address: walletAddress
      });
      toast.success(data.message);
      // Remove from pending signals
      setSignals(prev => prev.filter(s => s.signal_id !== signalId));
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to approve signal");
    }
  };

  // Reject signal
  const rejectSignal = async (signalId) => {
    try {
      await axios.post(`${API}/ai-trader/signals/reject/${signalId}?wallet_address=${walletAddress}`);
      setSignals(prev => prev.filter(s => s.signal_id !== signalId));
      toast.info("Signal rejected");
    } catch (e) {
      toast.error("Failed to reject signal");
    }
  };

  if (!connected) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <Bot className="w-20 h-20 mx-auto mb-6 text-[#D946EF]" />
          <h1 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Orbitron' }}>
            AI Trading Bot
          </h1>
          <p className="text-slate-400 mb-8">
            Connect your wallet to access the Bullpug AI Trading Agent
          </p>
          <Link to="/">
            <Button className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3]">
              Go Home to Connect Wallet
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-white py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center">
              <Bot className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ fontFamily: 'Orbitron' }}>
                AI Trading Bot
              </h1>
              <p className="text-sm text-slate-400">
                Bullpug AI Agent • Semi-Automated
              </p>
            </div>
          </div>
          
          <div className="flex gap-3">
            <Button
              onClick={() => setShowSettings(true)}
              variant="outline"
              className="border-white/20 text-slate-300"
            >
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
            <Button
              onClick={scanMarkets}
              disabled={scanning || !disclaimerAccepted}
              className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3]"
            >
              {scanning ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Zap className="w-4 h-4 mr-2" />
              )}
              {scanning ? "Scanning..." : "Scan Markets"}
            </Button>
          </div>
        </div>

        {/* Disclaimer Modal */}
        {showDisclaimer && !disclaimerAccepted && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-[#12121A] rounded-2xl p-6 max-w-lg border border-[#FF6B6B]/30">
              <div className="flex items-center gap-3 mb-4">
                <AlertTriangle className="w-8 h-8 text-[#FF6B6B]" />
                <h2 className="text-xl font-bold">Risk Disclaimer</h2>
              </div>
              
              <div className="space-y-3 text-sm text-slate-300 mb-6 max-h-64 overflow-y-auto">
                <p className="text-[#FF6B6B] font-medium">
                  ⚠️ Trading cryptocurrencies carries significant financial risk.
                </p>
                <ul className="space-y-2 list-disc list-inside">
                  <li>Only trade with funds you can afford to lose completely.</li>
                  <li>Past performance does not guarantee future results.</li>
                  <li>The AI makes no guarantees of profitability.</li>
                  <li>You maintain full control and must approve each trade.</li>
                  <li>Stop-loss orders may not execute at exact prices during high volatility.</li>
                  <li>This is not financial advice.</li>
                </ul>
                <p className="font-medium text-white pt-2">
                  By proceeding, you acknowledge and accept these risks.
                </p>
              </div>
              
              <div className="flex gap-3">
                <Link to="/journal" className="flex-1">
                  <Button variant="outline" className="w-full border-white/20">
                    Cancel
                  </Button>
                </Link>
                <Button
                  onClick={acceptDisclaimer}
                  className="flex-1 bg-[#FF6B6B] hover:bg-[#FF6B6B]/80"
                >
                  I Accept the Risks
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Settings Modal */}
        {showSettings && (
          <SettingsModal
            settings={settings}
            onSave={saveSettings}
            onClose={() => setShowSettings(false)}
          />
        )}

        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            icon={<TrendingUp className="w-5 h-5" />}
            label="Win Rate"
            value={`${history.stats.win_rate?.toFixed(1) || 0}%`}
            color={history.stats.win_rate >= 50 ? "#00FFA3" : "#FF6B6B"}
          />
          <StatCard
            icon={<DollarSign className="w-5 h-5" />}
            label="Total P&L"
            value={`${history.stats.total_pnl_sol >= 0 ? '+' : ''}${history.stats.total_pnl_sol?.toFixed(4) || 0} SOL`}
            color={history.stats.total_pnl_sol >= 0 ? "#00FFA3" : "#FF6B6B"}
          />
          <StatCard
            icon={<History className="w-5 h-5" />}
            label="Total Trades"
            value={history.stats.total_trades || 0}
            color="#D946EF"
          />
          <StatCard
            icon={<Target className="w-5 h-5" />}
            label="Open Positions"
            value={positions.length}
            color="#00C2FF"
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-white/10 pb-2">
          {[
            { id: "signals", label: "Signals", icon: <Zap className="w-4 h-4" />, count: signals.length },
            { id: "positions", label: "Positions", icon: <Target className="w-4 h-4" />, count: positions.length },
            { id: "history", label: "History", icon: <History className="w-4 h-4" /> },
            { id: "tokens", label: "Tokens", icon: <DollarSign className="w-4 h-4" /> }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-[#D946EF]/20 text-[#D946EF]"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span className="px-1.5 py-0.5 bg-[#D946EF] text-white text-xs rounded-full">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-[#D946EF]" />
          </div>
        ) : (
          <>
            {/* Signals Tab */}
            {activeTab === "signals" && (
              <div className="space-y-4">
                {signals.length === 0 ? (
                  <div className="text-center py-16 bg-white/5 rounded-2xl">
                    <Zap className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p className="text-slate-400">No pending signals</p>
                    <p className="text-sm text-slate-500 mt-1">
                      Click "Scan Markets" to analyze tokens for trading opportunities
                    </p>
                  </div>
                ) : (
                  signals.map(signal => (
                    <SignalCard
                      key={signal.signal_id}
                      signal={signal}
                      onApprove={() => approveSignal(signal.signal_id)}
                      onReject={() => rejectSignal(signal.signal_id)}
                    />
                  ))
                )}
              </div>
            )}

            {/* Positions Tab */}
            {activeTab === "positions" && (
              <div className="space-y-4">
                {positions.length === 0 ? (
                  <div className="text-center py-16 bg-white/5 rounded-2xl">
                    <Target className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p className="text-slate-400">No open positions</p>
                  </div>
                ) : (
                  positions.map(pos => (
                    <PositionCard key={pos.execution_id} position={pos} />
                  ))
                )}
              </div>
            )}

            {/* History Tab */}
            {activeTab === "history" && (
              <div className="space-y-4">
                {history.trades.length === 0 ? (
                  <div className="text-center py-16 bg-white/5 rounded-2xl">
                    <History className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p className="text-slate-400">No trade history</p>
                  </div>
                ) : (
                  history.trades.slice(0, 20).map(trade => (
                    <TradeHistoryCard key={trade.execution_id} trade={trade} />
                  ))
                )}
              </div>
            )}

            {/* Tokens Tab */}
            {activeTab === "tokens" && (
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h3 className="flex items-center gap-2 text-lg font-bold mb-4">
                    <Shield className="w-5 h-5 text-[#00FFA3]" />
                    Safer Tokens
                  </h3>
                  <div className="space-y-2">
                    {tokens.safer.map(token => (
                      <TokenCard key={token.symbol} token={token} />
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="flex items-center gap-2 text-lg font-bold mb-4">
                    <Skull className="w-5 h-5 text-[#FF6B6B]" />
                    High Risk Tokens
                  </h3>
                  <div className="space-y-2">
                    {tokens.high_risk.map(token => (
                      <TokenCard key={token.symbol} token={token} />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Sub-components
function StatCard({ icon, label, value, color }) {
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/5">
      <div className="flex items-center gap-2 text-slate-400 mb-2">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-xl font-bold" style={{ color }}>{value}</p>
    </div>
  );
}

function SignalCard({ signal, onApprove, onReject }) {
  const [expanded, setExpanded] = useState(false);
  const riskColors = RISK_COLORS[signal.risk_category];
  
  return (
    <div className={`bg-white/5 rounded-2xl p-5 border ${riskColors.border}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
            signal.signal_type === "buy" ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"
          }`}>
            {signal.signal_type === "buy" ? (
              <TrendingUp className="w-6 h-6 text-[#00FFA3]" />
            ) : (
              <TrendingDown className="w-6 h-6 text-[#FF6B6B]" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold">
                {signal.signal_type.toUpperCase()} {signal.token_symbol}
              </h3>
              <span className={`px-2 py-0.5 rounded text-xs ${riskColors.bg} ${riskColors.text}`}>
                {signal.risk_category === "safer" ? "SAFER" : "HIGH RISK"}
              </span>
            </div>
            <p className="text-sm text-slate-400">
              Confidence: <span className="text-white font-medium">{(signal.confidence * 100).toFixed(0)}%</span>
              {" • "}
              Strategy: <span className="text-white">{signal.strategy}</span>
            </p>
          </div>
        </div>
        
        <div className="flex gap-2">
          <Button
            onClick={onReject}
            variant="outline"
            size="sm"
            className="border-[#FF6B6B]/30 text-[#FF6B6B] hover:bg-[#FF6B6B]/10"
          >
            <X className="w-4 h-4" />
          </Button>
          <Button
            onClick={onApprove}
            size="sm"
            className="bg-[#00FFA3] text-black hover:bg-[#00FFA3]/80"
          >
            <Check className="w-4 h-4 mr-1" />
            Approve
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
        <div>
          <p className="text-slate-500">Entry</p>
          <p className="font-mono">${signal.entry_price < 0.01 ? signal.entry_price.toFixed(8) : signal.entry_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500">Stop Loss</p>
          <p className="font-mono text-[#FF6B6B]">${signal.stop_loss_price < 0.01 ? signal.stop_loss_price.toFixed(8) : signal.stop_loss_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500">Take Profit</p>
          <p className="font-mono text-[#00FFA3]">${signal.take_profit_price < 0.01 ? signal.take_profit_price.toFixed(8) : signal.take_profit_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500">Position</p>
          <p className="font-mono">{signal.suggested_position_sol} SOL</p>
        </div>
      </div>
      
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-slate-500 mt-3 hover:text-white"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? "Hide" : "Show"} Analysis
      </button>
      
      {expanded && (
        <div className="mt-3 p-3 bg-black/20 rounded-xl text-sm">
          <p className="text-slate-400 mb-2">{signal.reasoning}</p>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div>RSI: <span className="text-white">{signal.technical_indicators?.rsi?.toFixed(1)}</span></div>
            <div>Trend: <span className="text-white">{signal.technical_indicators?.short_trend}</span></div>
            <div>BB Pos: <span className="text-white">{(signal.technical_indicators?.bollinger?.position * 100)?.toFixed(0)}%</span></div>
          </div>
        </div>
      )}
    </div>
  );
}

function PositionCard({ position }) {
  const pnlColor = position.unrealized_pnl_pct >= 0 ? "#00FFA3" : "#FF6B6B";
  
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            position.trade_type === "buy" ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"
          }`}>
            {position.trade_type === "buy" ? (
              <TrendingUp className="w-5 h-5 text-[#00FFA3]" />
            ) : (
              <TrendingDown className="w-5 h-5 text-[#FF6B6B]" />
            )}
          </div>
          <div>
            <p className="font-bold">{position.token_symbol}</p>
            <p className="text-xs text-slate-500">{position.amount_sol} SOL</p>
          </div>
        </div>
        
        <div className="text-right">
          <p className="font-mono font-bold" style={{ color: pnlColor }}>
            {position.unrealized_pnl_pct >= 0 ? "+" : ""}{position.unrealized_pnl_pct?.toFixed(2)}%
          </p>
          <p className="text-xs text-slate-500">
            Entry: ${position.entry_price < 0.01 ? position.entry_price.toFixed(6) : position.entry_price.toFixed(4)}
          </p>
        </div>
      </div>
    </div>
  );
}

function TradeHistoryCard({ trade }) {
  const isProfitable = trade.pnl_sol > 0;
  
  return (
    <div className="bg-white/5 rounded-xl p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
          isProfitable ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"
        }`}>
          {isProfitable ? (
            <TrendingUp className="w-4 h-4 text-[#00FFA3]" />
          ) : (
            <TrendingDown className="w-4 h-4 text-[#FF6B6B]" />
          )}
        </div>
        <div>
          <p className="font-medium">{trade.token_symbol}</p>
          <p className="text-xs text-slate-500">
            {new Date(trade.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>
      
      <div className="text-right">
        <p className={`font-mono ${isProfitable ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>
          {isProfitable ? "+" : ""}{trade.pnl_sol?.toFixed(4)} SOL
        </p>
        <p className="text-xs text-slate-500">{trade.status}</p>
      </div>
    </div>
  );
}

function TokenCard({ token }) {
  const riskColors = RISK_COLORS[token.risk_category];
  
  return (
    <div className={`${riskColors.bg} rounded-xl p-3 flex items-center justify-between`}>
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg ${riskColors.bg} flex items-center justify-center`}>
          <span className={`text-sm font-bold ${riskColors.text}`}>
            {token.symbol.slice(0, 2)}
          </span>
        </div>
        <span className="font-medium">{token.symbol}</span>
      </div>
      <span className="font-mono text-sm">
        ${token.price_usd ? (token.price_usd < 0.01 ? token.price_usd.toFixed(6) : token.price_usd.toFixed(2)) : "N/A"}
      </span>
    </div>
  );
}

function SettingsModal({ settings, onSave, onClose }) {
  const [form, setForm] = useState({
    risk_level: settings?.risk_level || "safer",
    max_position_sol: settings?.max_position_sol || 0.5,
    stop_loss_percent: settings?.stop_loss_percent || 10,
    take_profit_percent: settings?.take_profit_percent || 20,
    max_daily_trades: settings?.max_daily_trades || 5
  });

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-white/10">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Trading Settings
        </h2>
        
        <div className="space-y-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Risk Level</label>
            <select
              value={form.risk_level}
              onChange={(e) => setForm({ ...form, risk_level: e.target.value })}
              className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white"
            >
              <option value="safer">Safer Tokens Only</option>
              <option value="high_risk">High Risk Tokens Only</option>
              <option value="both">Both (User Decides)</option>
            </select>
          </div>
          
          <div>
            <label className="text-sm text-slate-400 mb-1 block">
              Max Position (SOL): {form.max_position_sol}
            </label>
            <input
              type="range"
              min="0.05"
              max="1"
              step="0.05"
              value={form.max_position_sol}
              onChange={(e) => setForm({ ...form, max_position_sol: parseFloat(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-slate-500">
              <span>0.05 SOL</span>
              <span>1 SOL</span>
            </div>
          </div>
          
          <div>
            <label className="text-sm text-slate-400 mb-1 block">
              Stop Loss: {form.stop_loss_percent}%
            </label>
            <input
              type="range"
              min="5"
              max="50"
              step="1"
              value={form.stop_loss_percent}
              onChange={(e) => setForm({ ...form, stop_loss_percent: parseFloat(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-slate-500">
              <span>5%</span>
              <span>50%</span>
            </div>
          </div>
          
          <div>
            <label className="text-sm text-slate-400 mb-1 block">
              Take Profit: {form.take_profit_percent}%
            </label>
            <input
              type="range"
              min="10"
              max="100"
              step="5"
              value={form.take_profit_percent}
              onChange={(e) => setForm({ ...form, take_profit_percent: parseFloat(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-slate-500">
              <span>10%</span>
              <span>100%</span>
            </div>
          </div>
        </div>
        
        <div className="flex gap-3 mt-6">
          <Button onClick={onClose} variant="outline" className="flex-1 border-white/20">
            Cancel
          </Button>
          <Button onClick={() => onSave(form)} className="flex-1 bg-[#D946EF]">
            Save Settings
          </Button>
        </div>
      </div>
    </div>
  );
}
