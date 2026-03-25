/**
 * Bullpug Trading Bot Page - Semi-automated trading with AI signals
 * Features: Auto-scan every 5 minutes, Quick Trade, Jupiter integration, Social Trading
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { VersionedTransaction } from "@solana/web3.js";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import axios from "axios";
import {
  Settings, TrendingUp, TrendingDown,
  Loader2, RefreshCw, Zap,
  DollarSign, Target,
  History, Info, AlertTriangle,
  Rocket, CheckCircle, AlertCircle, Timer, Trash2, Bell,
  Cpu, Users, Globe,
  RotateCcw, X, Wallet, Copy
} from "lucide-react";
import { ShareButton } from "../components/SocialShare";
import SocialTrading from "../components/SocialTrading";
import PushNotificationManager from "../components/PushNotificationManager";
import MultiChainCopyTrading from "../components/MultiChainCopyTrading";
import UnifiedAutoTrader from "../components/UnifiedAutoTrader";
import RunnerTokens from "../components/RunnerTokens";
import RunnerAlertManager from "../components/RunnerAlertManager";
import {
  RiskCalculator, SignalCard, PositionCard,
  TradeHistoryCard, SettingsModal, TopPickCard, AlertCard, QuickSettings,
  IntelligenceDashboard, TradingModeSelector, PerformanceScorecard,
  FundLedger,
  API, TRADING_BOT_IMAGE, AUTO_SCAN_INTERVAL, TOKENS
} from "../components/trader";

function DepositModal({ custodialWallet, walletAddress, onClose, onDepositDetected }) {
  const [detecting, setDetecting] = useState(false);
  const [detected, setDetected] = useState(null);

  // Auto-poll for deposits every 5 seconds
  useEffect(() => {
    const poll = setInterval(async () => {
      if (detected) return;
      try {
        const { data } = await axios.post(`${API}/custodial-wallet/detect-deposit/${walletAddress}`);
        if (data.detected) {
          setDetected(data);
          toast.success(`Deposit of ${data.deposit_sol} SOL detected!`);
          onDepositDetected();
        }
      } catch {}
    }, 5000);
    return () => clearInterval(poll);
  }, [walletAddress, detected, onDepositDetected]);

  const safeCopyAddr = () => {
    const addr = custodialWallet.wallet_address;
    const fallback = () => {
      try {
        const ta = document.createElement("textarea");
        ta.value = addr;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        toast.success("Address copied!");
      } catch { toast.error("Copy failed — please copy manually"); }
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(addr).then(() => toast.success("Address copied!"), fallback);
    } else { fallback(); }
  };

  const detectDeposit = async () => {
    setDetecting(true);
    try {
      const { data } = await axios.post(`${API}/custodial-wallet/detect-deposit/${walletAddress}`);
      if (data.detected) {
        setDetected(data);
        toast.success(`Deposit of ${data.deposit_sol} SOL detected!`);
        onDepositDetected();
      } else {
        toast.info("No new deposit found yet. Make sure the transaction is confirmed on-chain.");
      }
    } catch (e) {
      toast.error("Failed to check for deposit");
    }
    setDetecting(false);
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-[#00FFA3]/30" onClick={e => e.stopPropagation()} data-testid="deposit-modal">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Wallet className="w-5 h-5 text-[#00FFA3]" />
            Deposit SOL
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-4">
          <div className="p-4 bg-black/30 rounded-xl">
            <p className="text-xs text-slate-500 mb-2">Send SOL to this address:</p>
            <code className="block p-3 bg-black/50 rounded-lg text-sm font-mono text-[#00FFA3] break-all">
              {custodialWallet.wallet_address}
            </code>
          </div>

          <div className="flex gap-3">
            <Button onClick={safeCopyAddr} variant="outline" className="flex-1 border-[#00FFA3]/30 text-[#00FFA3]">
              <Copy className="w-4 h-4 mr-2" />
              Copy Address
            </Button>
          </div>

          <div className="border-t border-white/10 pt-4">
            <p className="text-xs text-slate-400 mb-3">
              After sending SOL from your wallet, click below to confirm and record the deposit:
            </p>
            <Button
              onClick={detectDeposit}
              disabled={detecting}
              className="w-full bg-[#00FFA3] text-black hover:bg-[#00FFA3]/80 font-bold"
              data-testid="detect-deposit-btn"
            >
              {detecting ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Checking...</>
              ) : (
                <><CheckCircle className="w-4 h-4 mr-2" /> I've Sent SOL — Confirm Deposit</>
              )}
            </Button>
          </div>

          {detected && (
            <div className="p-4 bg-[#00FFA3]/10 border border-[#00FFA3]/30 rounded-xl">
              <p className="text-sm font-bold text-[#00FFA3]">Deposit Recorded!</p>
              <p className="text-xs text-slate-300 mt-1">
                {detected.deposit_sol} SOL has been added to your Fund Ledger.
              </p>
              <Button onClick={onClose} className="w-full mt-3 bg-[#00FFA3] text-black hover:bg-[#00FFA3]/80">
                Done
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AITrader() {
  const { publicKey, connected, signTransaction } = useWallet();
  const { connection } = useConnection();
  const walletAddress = publicKey?.toString();
  const autoScanRef = useRef(null);
  const [nextScanIn, setNextScanIn] = useState(null);

  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [tokens, setTokens] = useState({ safer: [], high_risk: [] });
  const [signals, setSignals] = useState([]);
  const [positions, setPositions] = useState([]);
  const [history, setHistory] = useState({ trades: [], stats: {} });
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [showSettings, setShowSettings] = useState(false);
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [lastScan, setLastScan] = useState(null);
  const [autoScanEnabled, setAutoScanEnabled] = useState(true);
  
  // Top Picks state (moved from Bullpug AI)
  const [topPicks, setTopPicks] = useState({ safe: [], volatile: [], newPairs: [] });
  const [topPicksLoading, setTopPicksLoading] = useState(false);
  const [topPicksRefreshing, setTopPicksRefreshing] = useState(false);
  const [lastTopPicksUpdate, setLastTopPicksUpdate] = useState(null);
  const [runnerRefreshTrigger, setRunnerRefreshTrigger] = useState(0);
  const [runnersRefreshing, setRunnersRefreshing] = useState(false);
  
  // Price Alerts state
  const [priceAlerts, setPriceAlerts] = useState([]);
  const [triggeredAlerts, setTriggeredAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  
  // Telegram state
  const [telegramLinked, setTelegramLinked] = useState(false);
  const [telegramStatus, setTelegramStatus] = useState(null);
  const [telegramLinkCode, setTelegramLinkCode] = useState(null);
  const [showTelegramModal, setShowTelegramModal] = useState(false);
  const [telegramLoading, setTelegramLoading] = useState(false);
  
  // Auto-Trade state
  const [autoTradeStatus, setAutoTradeStatus] = useState(null);
  const [autoTradeLogs, setAutoTradeLogs] = useState([]);
  const [autoTradeLoading, setAutoTradeLoading] = useState(false);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  
  // Custodial Wallet state
  const [custodialWallet, setCustodialWallet] = useState(null);
  const [custodialLoading, setCustodialLoading] = useState(false);

  // Risk Calculator state (lifted for position integration)
  const [riskCalcPosition, setRiskCalcPosition] = useState(0.1);
  const [riskCalcEntryPrice, setRiskCalcEntryPrice] = useState(1);

  // Fetch Telegram status
  const fetchTelegramStatus = useCallback(async () => {
    if (!walletAddress) return;
    try {
      const response = await axios.get(`${API}/telegram/status/${walletAddress}`);
      setTelegramLinked(response.data.linked);
      setTelegramStatus(response.data);
    } catch (err) {
      console.error("Telegram status error:", err);
    }
  }, [walletAddress]);

  // Generate Telegram link code
  const generateTelegramCode = async () => {
    if (!walletAddress) return;
    setTelegramLoading(true);
    try {
      const response = await axios.post(`${API}/telegram/generate-link-code`, {
        wallet_address: walletAddress
      });
      if (response.data.success) {
        setTelegramLinkCode(response.data);
        setShowTelegramModal(true);
      } else {
        toast.error("Failed to generate code");
      }
    } catch (err) {
      toast.error("Failed to generate Telegram link code");
    }
    setTelegramLoading(false);
  };

  // Unlink Telegram
  const unlinkTelegram = async () => {
    if (!walletAddress) return;
    try {
      await axios.post(`${API}/telegram/unlink/${walletAddress}`);
      setTelegramLinked(false);
      setTelegramStatus(null);
      toast.success("Telegram unlinked");
    } catch (err) {
      toast.error("Failed to unlink Telegram");
    }
  };

  // Check for triggered alerts
  const checkAlerts = useCallback(async () => {
    if (!walletAddress) return;
    try {
      const response = await axios.get(`${API}/ai-trader/alerts/check/${walletAddress}`);
      if (response.data.triggered_alerts?.length > 0) {
        setTriggeredAlerts(response.data.triggered_alerts);
        // Show notification for each triggered alert
        response.data.triggered_alerts.forEach(alert => {
          toast.success(
            `🚨 ALERT: ${alert.symbol} - ${alert.trigger_reason}`,
            { duration: 10000 }
          );
          // Request browser notification permission and show notification
          if (Notification.permission === "granted") {
            new Notification(`Bullpug Alert: ${alert.symbol}`, {
              body: alert.trigger_reason,
              icon: "/logo.png"
            });
          }
        });
      }
    } catch (err) {
      console.error("Check alerts error:", err);
    }
  }, [walletAddress]);

  // Fetch price alerts
  const fetchAlerts = useCallback(async () => {
    if (!walletAddress) return;
    setAlertsLoading(true);
    try {
      const response = await axios.get(`${API}/ai-trader/alerts/${walletAddress}`);
      setPriceAlerts(response.data.alerts || []);
    } catch (err) {
      console.error("Fetch alerts error:", err);
    }
    setAlertsLoading(false);
  }, [walletAddress]);

  // Scan for breakout candidates
  const scanForBreakouts = async () => {
    if (!walletAddress) return;
    try {
      const response = await axios.post(`${API}/ai-trader/alerts/breakout-scan?wallet_address=${walletAddress}`);
      if (response.data.new_alerts?.length > 0) {
        toast.success(`Found ${response.data.count} potential breakout candidates!`);
        fetchAlerts();
      } else {
        toast.info("No new breakout candidates found");
      }
    } catch (err) {
      toast.error("Breakout scan failed");
    }
  };

  // Delete an alert
  const deleteAlert = async (alertId) => {
    try {
      await axios.delete(`${API}/ai-trader/alerts/${alertId}`);
      setPriceAlerts(prev => prev.filter(a => a.alert_id !== alertId));
      toast.success("Alert deleted");
    } catch (err) {
      toast.error("Failed to delete alert");
    }
  };

  // Request notification permission on mount
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  // Check alerts periodically
  useEffect(() => {
    if (!walletAddress || !disclaimerAccepted) return;
    
    // Initial check
    checkAlerts();
    fetchAlerts();
    fetchTelegramStatus();
    
    // Check every 30 seconds
    const interval = setInterval(checkAlerts, 30000);
    return () => clearInterval(interval);
  }, [walletAddress, disclaimerAccepted, checkAlerts, fetchAlerts, fetchTelegramStatus]);

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
      toast.error("Failed to load trading data — check your connection");
    }
    setLoading(false);
  }, [walletAddress]);

  // Reset statistics - full wipe of trading history
  const resetStatistics = async () => {
    if (!walletAddress) return;
    
    const confirmed = window.confirm(
      "This will completely reset ALL your trading statistics and history. This cannot be undone. Continue?"
    );
    
    if (!confirmed) return;
    
    const loadingToast = toast.loading("Resetting statistics...");
    
    try {
      const { data } = await axios.post(`${API}/ai-trader/reset-statistics/${walletAddress}?full_reset=true`);
      
      toast.dismiss(loadingToast);
      
      if (data.success) {
        toast.success("Statistics reset! Fresh start.");
        
        // Update local state with new stats
        setHistory(prev => ({
          ...prev,
          stats: data.new_stats,
          trades: []
        }));
        
        // Refresh all data
        fetchData();
      } else {
        toast.error("Failed to reset statistics");
      }
    } catch (e) {
      toast.dismiss(loadingToast);
      toast.error(`Error: ${e.response?.data?.detail || e.message}`);
    }
  };

  // Fetch Top Picks (Safe, Volatile, New Pairs)
  const fetchTopPicks = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setTopPicksRefreshing(true);
    } else {
      setTopPicksLoading(true);
    }
    try {
      const [recsRes, newPairsRes] = await Promise.all([
        axios.get(`${API}/ai-suggestions/coin-recommendations`),
        axios.get(`${API}/ai-trader/new-pairs`).catch(() => ({ data: { pairs: [] } }))
      ]);
      
      setTopPicks({
        safe: recsRes.data.safe_picks || [],
        volatile: recsRes.data.volatile_picks || [],
        newPairs: newPairsRes.data?.pairs || []
      });
      setLastTopPicksUpdate(new Date());
    } catch (e) {
      console.error("Error fetching top picks:", e);
    }
    setTopPicksLoading(false);
    setTopPicksRefreshing(false);
  }, []);

  // Fetch Auto-Trade Status
  const fetchAutoTradeStatus = useCallback(async () => {
    if (!walletAddress) return;
    setAutoTradeLoading(true);
    try {
      const [statusRes, logsRes] = await Promise.all([
        axios.get(`${API}/ai-trader/auto-trade/status/${walletAddress}`),
        axios.get(`${API}/ai-trader/auto-trade/logs/${walletAddress}?limit=20`)
      ]);
      setAutoTradeStatus(statusRes.data);
      setAutoTradeLogs(logsRes.data.logs || []);
    } catch (err) {
      console.error("Auto-trade status error:", err);
      toast.error("Failed to load auto-trade status");
    }
    setAutoTradeLoading(false);
  }, [walletAddress]);

  // Toggle Auto-Trade
  const toggleAutoTrade = async (enabled) => {
    if (!walletAddress) return;
    try {
      const response = await axios.post(`${API}/ai-trader/auto-trade/toggle/${walletAddress}?enabled=${enabled}`);
      if (response.data.success) {
        toast.success(response.data.message);
        fetchAutoTradeStatus();
      }
    } catch (err) {
      toast.error("Failed to toggle auto-trade");
    }
  };

  // Update Auto-Trade Settings
  const updateAutoTradeSettings = async (settingsUpdate) => {
    if (!walletAddress) return;
    try {
      const response = await axios.put(`${API}/ai-trader/auto-trade/settings/${walletAddress}`, settingsUpdate);
      if (response.data.success) {
        toast.success("Auto-trade settings updated");
        
        // Check if any exits were triggered by the settings change
        if (response.data.exits_count > 0) {
          const exits = response.data.exits_triggered;
          exits.forEach(exit => {
            if (exit.executed_on_chain) {
              toast.success(`${exit.action === 'take_profit' ? '💰' : '🛑'} ${exit.symbol} sold: ${exit.action.replace('_', ' ')} at ${exit.pnl_percent?.toFixed(1)}%`);
            } else {
              toast.warning(`${exit.symbol} triggered ${exit.action.replace('_', ' ')} but sell failed: ${exit.error || 'unknown error'}`);
            }
          });
          fetchData(); // Refresh positions
        }
        
        fetchAutoTradeStatus();
      }
    } catch (err) {
      toast.error("Failed to update auto-trade settings");
    }
  };

  // Manually Trigger Auto-Trade Scan
  const runAutoTradeScan = async () => {
    if (!walletAddress) return;
    const loadingToast = toast.loading("Running auto-trade scan...");
    try {
      const response = await axios.post(`${API}/ai-trader/auto-trade/scan-and-execute/${walletAddress}`);
      toast.dismiss(loadingToast);
      
      if (response.data.success) {
        const trades = response.data.trades || [];
        if (trades.length > 0) {
          toast.success(`Auto-trade executed ${trades.length} trade(s)!`);
          fetchData();
        } else {
          toast.info(response.data.message || "No trades executed");
        }
      } else {
        toast.info(response.data.message || "Auto-trade scan complete");
      }
      fetchAutoTradeStatus();
    } catch (err) {
      toast.dismiss(loadingToast);
      toast.error("Auto-trade scan failed");
    }
  };

  // Fetch Custodial Wallet Info
  const fetchCustodialWallet = useCallback(async () => {
    if (!walletAddress) return;
    setCustodialLoading(true);
    try {
      const response = await axios.get(`${API}/custodial-wallet/info/${walletAddress}`);
      setCustodialWallet(response.data);
    } catch (err) {
      console.error("Custodial wallet error:", err);
    }
    setCustodialLoading(false);
  }, [walletAddress]);

  // Withdraw from Custodial Wallet
  const withdrawFromCustodial = async (amount) => {
    if (!walletAddress || !amount) return;
    const loadingToast = toast.loading("Processing withdrawal...");
    try {
      const response = await axios.post(`${API}/custodial-wallet/withdraw`, {
        user_wallet: walletAddress,
        amount_sol: parseFloat(amount)
      });
      toast.dismiss(loadingToast);
      if (response.data.success) {
        toast.success(`Withdrew ${amount} SOL! TX: ${response.data.tx_signature?.slice(0, 8)}...`);
        fetchCustodialWallet();
      }
    } catch (err) {
      toast.dismiss(loadingToast);
      toast.error(err.response?.data?.detail || "Withdrawal failed");
    }
  };

  // Copy to clipboard helper
  const copyToClipboard = async (text, label = "Address") => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`${label} copied!`);
    } catch (e) {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      toast.success(`${label} copied!`);
    }
  };

  // Sync positions from on-chain data
  const syncPositionsFromChain = async () => {
    if (!walletAddress) return;
    const loadingToast = toast.loading("Syncing positions from blockchain...");
    try {
      const response = await axios.post(`${API}/custodial-wallet/sync-positions/${walletAddress}`);
      toast.dismiss(loadingToast);
      
      if (response.data.success) {
        const { positions_created, positions_synced, positions_closed } = response.data;
        if (positions_created > 0) {
          toast.success(`Found ${positions_created} new position(s) on-chain!`);
        }
        if (positions_closed > 0) {
          toast.info(`Closed ${positions_closed} position(s) no longer on-chain`);
        }
        if (positions_created === 0 && positions_closed === 0) {
          toast.success(`Positions synced (${positions_synced} updated)`);
        }
        fetchData(); // Refresh positions
      }
    } catch (err) {
      toast.dismiss(loadingToast);
      toast.error(err.response?.data?.detail || "Failed to sync positions");
    }
  };

  useEffect(() => {
    fetchData();
    fetchTopPicks();
    fetchAutoTradeStatus();
    fetchCustodialWallet();
    // Refresh top picks every 5 minutes, no auto-refresh for main data
    const topPicksInterval = setInterval(fetchTopPicks, 300000); // Refresh every 5 minutes
    return () => {
      clearInterval(topPicksInterval);
    };
  }, [fetchData, fetchTopPicks, fetchAutoTradeStatus, fetchCustodialWallet]);

  // Auto-scan every 5 minutes when enabled and disclaimer accepted
  useEffect(() => {
    if (!disclaimerAccepted || !walletAddress || !autoScanEnabled) {
      if (autoScanRef.current) {
        clearInterval(autoScanRef.current);
        autoScanRef.current = null;
      }
      setNextScanIn(null);
      return;
    }

    // Start countdown timer
    let countdown = AUTO_SCAN_INTERVAL / 1000;
    setNextScanIn(countdown);
    
    const countdownInterval = setInterval(() => {
      countdown -= 1;
      if (countdown <= 0) {
        countdown = AUTO_SCAN_INTERVAL / 1000;
      }
      setNextScanIn(countdown);
    }, 1000);

    // Auto-scan interval
    autoScanRef.current = setInterval(() => {
      if (!scanning) {
        scanMarkets();
      }
    }, AUTO_SCAN_INTERVAL);

    return () => {
      clearInterval(countdownInterval);
      if (autoScanRef.current) {
        clearInterval(autoScanRef.current);
      }
    };
  }, [disclaimerAccepted, walletAddress, autoScanEnabled, scanning]);

  // Accept disclaimer
  const acceptDisclaimer = () => {
    setDisclaimerAccepted(true);
    setShowDisclaimer(false);
    localStorage.setItem(`ai_trader_disclaimer_${walletAddress}`, "true");
    toast.success("Disclaimer accepted - Bullpug Trading Bot enabled");
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
      setLastScan(new Date());
      if (data.signals_generated > 0) {
        toast.success(
          <div className="flex items-center gap-2">
            <span>{data.signals_generated} trading signal(s) found!</span>
            <button 
              onClick={() => setActiveTab("discover")}
              className="text-xs bg-white/20 px-2 py-1 rounded hover:bg-white/30"
            >
              View
            </button>
          </div>,
          { duration: 5000 }
        );
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

  // Execute Jupiter Swap - Actually sign and submit the transaction
  const executeJupiterSwap = async (signal) => {
    if (!signTransaction || !connection) {
      toast.error("Wallet not ready for signing");
      return null;
    }

    try {
      const tokenMint = signal.token_mint || TOKENS[signal.token_symbol];
      const solMint = TOKENS.SOL;
      const amountLamports = Math.floor(signal.suggested_position_sol * 1e9);
      
      // Determine input/output based on buy/sell
      const inputMint = signal.signal_type === "buy" ? solMint : tokenMint;
      const outputMint = signal.signal_type === "buy" ? tokenMint : solMint;
      
      // Get swap transaction from backend
      const { data: swapData } = await axios.post(`${API}/ai-trader/swap-transaction`, null, {
        params: {
          user_public_key: walletAddress,
          input_mint: inputMint,
          output_mint: outputMint,
          amount_lamports: amountLamports,
          slippage_bps: 100
        }
      });

      if (!swapData.success || !swapData.swapTransaction) {
        throw new Error("Failed to get swap transaction");
      }

      // Deserialize the transaction
      const swapTransactionBuf = Buffer.from(swapData.swapTransaction, "base64");
      const transaction = VersionedTransaction.deserialize(swapTransactionBuf);

      // Sign the transaction
      const signedTransaction = await signTransaction(transaction);

      // Send the signed transaction
      const txSignature = await connection.sendRawTransaction(signedTransaction.serialize(), {
        skipPreflight: false,
        preflightCommitment: "confirmed",
        maxRetries: 3
      });

      // Wait for confirmation
      const confirmation = await connection.confirmTransaction(txSignature, "confirmed");
      
      if (confirmation.value.err) {
        throw new Error("Transaction failed on-chain");
      }

      return {
        signature: txSignature,
        inputAmount: amountLamports / 1e9,
        outputAmount: parseFloat(swapData.quote.outAmount) / 1e9
      };

    } catch (err) {
      console.error("Jupiter swap error:", err);
      throw err;
    }
  };

  // Quick Trade - Execute swap with wallet signing
  const quickTrade = async (signal) => {
    if (!signTransaction) {
      toast.error("Wallet does not support transaction signing");
      return;
    }

    try {
      // Show loading toast
      const loadingToast = toast.loading(
        <div>
          <p className="font-bold">Preparing Swap...</p>
          <p className="text-sm">{signal.signal_type.toUpperCase()} {signal.token_symbol}</p>
          <p className="text-xs text-slate-400">Please approve in your wallet</p>
        </div>
      );

      // First approve the signal
      await axios.post(`${API}/ai-trader/signals/approve`, {
        signal_id: signal.signal_id,
        wallet_address: walletAddress
      });

      // Execute the swap
      const result = await executeJupiterSwap(signal);
      
      toast.dismiss(loadingToast);

      if (result) {
        // Record the execution
        await axios.post(`${API}/ai-trader/execute-swap`, null, {
          params: {
            wallet_address: walletAddress,
            signal_id: signal.signal_id,
            tx_signature: result.signature,
            input_amount: result.inputAmount,
            output_amount: result.outputAmount
          }
        });

        // Remove from pending signals
        setSignals(prev => prev.filter(s => s.signal_id !== signal.signal_id));

        // Show success
        toast.success(
          <div>
            <p className="font-bold text-[#00FFA3]">Trade Executed!</p>
            <p className="text-sm">{signal.signal_type.toUpperCase()} {signal.token_symbol}</p>
            <p className="text-xs">
              <a 
                href={`https://solscan.io/tx/${result.signature}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#00C2FF] hover:underline"
              >
                View on Solscan →
              </a>
            </p>
          </div>,
          { duration: 8000 }
        );

        // Refresh data
        fetchData();
      }
    } catch (e) {
      toast.dismiss();
      const errorMsg = e.message || "Trade failed";
      if (errorMsg.includes("User rejected")) {
        toast.info("Transaction cancelled by user");
      } else {
        toast.error(
          <div>
            <p className="font-bold">Trade Failed</p>
            <p className="text-xs">{errorMsg}</p>
          </div>
        );
      }
    }
  };

  // Quick Sell - Sell position with editable amount
  const quickSell = async (position, sellAmount) => {
    if (!signTransaction) {
      toast.error("Wallet does not support transaction signing");
      return;
    }

    // Store the position ID to remove later
    const positionId = position.execution_id || position.position_id;

    try {
      const loadingToast = toast.loading(
        <div>
          <p className="font-bold">Preparing Sell...</p>
          <p className="text-sm">SELL {position.token_symbol}</p>
          <p className="text-xs text-slate-400">Please approve in your wallet</p>
        </div>
      );

      // Create a sell signal object
      const sellSignal = {
        signal_type: "sell",
        token_symbol: position.token_symbol,
        token_mint: position.token_mint || TOKENS[position.token_symbol],
        suggested_position_sol: sellAmount
      };

      // Execute the swap (token -> SOL)
      const result = await executeJupiterSwap(sellSignal);
      
      toast.dismiss(loadingToast);

      if (result) {
        // IMMEDIATELY remove the position from UI (optimistic update)
        setPositions(prev => prev.filter(p => 
          (p.execution_id || p.position_id) !== positionId
        ));

        // Record the sell in the background
        await axios.post(`${API}/ai-trader/close-position`, null, {
          params: {
            wallet_address: walletAddress,
            position_id: positionId,
            tx_signature: result.signature,
            sell_amount: sellAmount,
            received_sol: result.outputAmount
          }
        });

        toast.success(
          <div>
            <p className="font-bold text-[#00FFA3]">Position Sold!</p>
            <p className="text-sm">SOLD {position.token_symbol}</p>
            <p className="text-sm">Received: {result.outputAmount.toFixed(4)} SOL</p>
            <p className="text-xs">
              <a 
                href={`https://solscan.io/tx/${result.signature}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#00C2FF] hover:underline"
              >
                View on Solscan →
              </a>
            </p>
          </div>,
          { duration: 8000 }
        );

        // Refresh data to update stats (but UI already updated)
        fetchData();
      }
    } catch (e) {
      toast.dismiss();
      const errorMsg = e.message || "Sell failed";
      if (errorMsg.includes("User rejected")) {
        toast.info("Transaction cancelled by user");
      } else {
        toast.error(
          <div>
            <p className="font-bold">Sell Failed</p>
            <p className="text-xs">{errorMsg}</p>
          </div>
        );
      }
    }
  };

  // Delete/Remove position (doesn't sell, just removes from tracking)
  const deletePosition = async (position) => {
    const positionId = position.execution_id || position.position_id;
    
    if (!positionId) {
      console.error("No position ID found:", position);
      toast.error("Cannot delete: Position ID not found");
      return;
    }
    
    if (!walletAddress) {
      console.error("No wallet address");
      toast.error("Please connect your wallet first");
      return;
    }
    
    try {
      console.log(`Deleting position: ${positionId} for wallet: ${walletAddress}`);
      
      const response = await axios.delete(`${API}/ai-trader/delete-position`, {
        params: {
          wallet_address: walletAddress,
          position_id: positionId
        }
      });
      
      console.log("Delete response:", response.data);
      
      // Remove from UI immediately
      setPositions(prev => prev.filter(p => 
        (p.execution_id || p.position_id) !== positionId
      ));
      
      toast.success(`${position.token_symbol} position removed`);
    } catch (e) {
      console.error("Delete position error:", e);
      console.error("Error response:", e.response?.data);
      toast.error(e.response?.data?.detail || "Failed to remove position");
    }
  };

  // Manual close - marks position as closed without executing a sell
  const manualClosePosition = async (position) => {
    const positionId = position.execution_id || position.position_id;
    
    if (!positionId || !walletAddress) {
      toast.error("Missing position ID or wallet");
      return;
    }
    
    try {
      const response = await axios.post(`${API}/ai-trader/manual-close-position`, {
        wallet_address: walletAddress,
        position_id: positionId,
        exit_price: position.current_price || position.entry_price,
        exit_reason: "manual_close"
      });
      
      if (response.data.success) {
        // Remove from positions, will appear in history
        setPositions(prev => prev.filter(p => 
          (p.execution_id || p.position_id) !== positionId
        ));
        
        const pnl = response.data.pnl_percent || 0;
        toast.success(`${position.token_symbol} closed at ${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}%`);
        
        // Refresh history
        fetchHistory();
      } else {
        toast.error(response.data.message || "Failed to close position");
      }
    } catch (e) {
      console.error("Manual close error:", e);
      toast.error(e.response?.data?.detail || "Failed to close position");
    }
  };

  // Custodial Sell - Execute sell from custodial wallet (auto-execute, no wallet approval needed)
  const custodialSell = async (position, tokenAmount, percentage) => {
    const positionId = position.execution_id || position.position_id;
    
    try {
      const loadingToast = toast.loading(
        <div>
          <p className="font-bold">Executing Sell...</p>
          <p className="text-sm">SELL {percentage}% of {position.token_symbol}</p>
          <p className="text-xs text-slate-400">Processing via Auto-Trade Wallet</p>
        </div>
      );
      
      const response = await axios.post(`${API}/custodial-wallet/execute-sell`, {
        user_wallet: walletAddress,
        token_mint: position.token_mint,
        token_amount: tokenAmount,
        position_id: positionId
      });
      
      toast.dismiss(loadingToast);
      
      if (response.data.success) {
        // Update positions if we sold 100%
        if (percentage >= 100) {
          setPositions(prev => prev.filter(p => 
            (p.execution_id || p.position_id) !== positionId
          ));
        }
        
        const receivedSol = response.data.received_sol || 0;
        
        toast.success(
          <div>
            <p className="font-bold text-[#00FFA3]">Sell Executed!</p>
            <p className="text-sm">SOLD {percentage}% of {position.token_symbol}</p>
            {receivedSol > 0 && <p className="text-sm">Received: {receivedSol.toFixed(4)} SOL</p>}
            {response.data.tx_signature && (
              <p className="text-xs">
                <a 
                  href={`https://solscan.io/tx/${response.data.tx_signature}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#00C2FF] hover:underline"
                >
                  View on Solscan →
                </a>
              </p>
            )}
          </div>,
          { duration: 8000 }
        );
        
        // Refresh data
        fetchData();
        fetchCustodialWallet();
      } else {
        toast.error(response.data.error || "Sell failed");
      }
    } catch (e) {
      toast.dismiss();
      console.error("Custodial sell error:", e);
      toast.error(e.response?.data?.detail || "Sell execution failed");
    }
  };


  // Quick Buy from Tokens tab - Buy token directly
  const quickBuyToken = async (coin, buyAmountSol) => {
    if (!signTransaction) {
      toast.error("Wallet does not support transaction signing");
      return;
    }

    try {
      const loadingToast = toast.loading(
        <div>
          <p className="font-bold">Preparing Buy...</p>
          <p className="text-sm">BUY {coin.symbol}</p>
          <p className="text-xs text-slate-400">Please approve in your wallet</p>
        </div>
      );

      // Create a buy signal object
      const buySignal = {
        signal_type: "buy",
        token_symbol: coin.symbol,
        token_mint: coin.contract_address || TOKENS[coin.symbol],
        suggested_position_sol: buyAmountSol
      };

      // Execute the swap (SOL -> token)
      const result = await executeJupiterSwap(buySignal);
      
      toast.dismiss(loadingToast);

      if (result) {
        // Record the buy as a position
        await axios.post(`${API}/ai-trader/add-position`, null, {
          params: {
            wallet_address: walletAddress,
            token_symbol: coin.symbol,
            token_mint: coin.contract_address,
            tx_signature: result.signature,
            input_sol: buyAmountSol,
            output_amount: result.outputAmount,
            entry_price: coin.price
          }
        });

        toast.success(
          <div>
            <p className="font-bold text-[#00FFA3]">Token Purchased!</p>
            <p className="text-sm">BOUGHT {coin.symbol}</p>
            <p className="text-sm">Spent: {buyAmountSol} SOL</p>
            <p className="text-xs">
              <a 
                href={`https://solscan.io/tx/${result.signature}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#00C2FF] hover:underline"
              >
                View on Solscan →
              </a>
            </p>
          </div>,
          { duration: 8000 }
        );

        // Switch to positions tab and refresh
        setActiveTab("dashboard");
        fetchData();
      }
    } catch (e) {
      toast.dismiss();
      const errorMsg = e.message || "Buy failed";
      if (errorMsg.includes("User rejected")) {
        toast.info("Transaction cancelled by user");
      } else {
        toast.error(
          <div>
            <p className="font-bold">Buy Failed</p>
            <p className="text-xs">{errorMsg}</p>
          </div>
        );
      }
    }
  };

  if (!connected) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] text-white pt-24 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="w-28 h-28 mx-auto mb-6 rounded-2xl overflow-hidden shadow-lg shadow-[#D946EF]/30">
            <img src={TRADING_BOT_IMAGE} alt="Bullpug Trading Bot" className="w-full h-full object-cover" />
          </div>
          <h1 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Orbitron' }}>
            Bullpug Trading Bot
          </h1>
          <p className="text-slate-400 mb-8 max-w-md mx-auto">
            Connect your wallet to access the Bullpug Trading Bot. 
            Get AI-powered trading signals with technical analysis.
          </p>
          <Link to="/">
            <Button className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] px-8 py-6 text-lg font-bold rounded-xl">
              Go Home to Connect Wallet
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // Format countdown timer
  const formatCountdown = (seconds) => {
    if (!seconds) return "";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-white pt-20 pb-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl overflow-hidden shadow-lg shadow-[#D946EF]/20">
              <img src={TRADING_BOT_IMAGE} alt="Bullpug Trading Bot" className="w-full h-full object-cover" />
            </div>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2" style={{ fontFamily: 'Orbitron' }}>
                Bullpug Trading Bot
                <span className="px-2 py-0.5 text-[10px] bg-[#D946EF]/20 text-[#D946EF] rounded-full font-normal">BETA</span>
              </h1>
              <p className="text-sm text-slate-400 flex items-center gap-2">
                Semi-Automated Trading
                {lastScan && (
                  <span className="text-xs text-slate-500">
                    • Last scan: {lastScan.toLocaleTimeString()}
                  </span>
                )}
                {autoScanEnabled && nextScanIn && (
                  <span className="text-xs text-[#00FFA3] flex items-center gap-1">
                    <Timer className="w-3 h-3" />
                    Next: {formatCountdown(nextScanIn)}
                  </span>
                )}
              </p>
            </div>
          </div>
          
          <div className="flex gap-3">
            <Button
              onClick={scanMarkets}
              disabled={scanning || !disclaimerAccepted}
              className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] hover:opacity-90 disabled:opacity-50"
              data-testid="scan-markets-btn"
            >
              {scanning ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Zap className="w-4 h-4 mr-2" />
              )}
              {scanning ? "Scanning..." : "Scan Now"}
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

        {/* Fund Ledger — Always visible at top */}
        <div className="mb-6 sm:mb-8">
          <FundLedger
            walletAddress={walletAddress}
            custodialWallet={custodialWallet}
            onDeposit={() => setShowDepositModal(true)}
            onWithdraw={withdrawFromCustodial}
          />
        </div>
        
        {/* Share Performance & Reset Stats Buttons */}
        {history.stats.total_trades > 0 && (
          <div className="flex justify-end gap-2 mb-4">
            <Button
              onClick={resetStatistics}
              variant="outline"
              size="sm"
              className="border-white/20 text-slate-400 hover:text-white text-xs"
              data-testid="reset-stats-btn"
            >
              <RotateCcw className="w-3 h-3 mr-1" />
              Reset Stats
            </Button>
            <ShareButton 
              type="performance" 
              data={history.stats}
              className="px-3 py-1.5 text-xs"
            />
          </div>
        )}

        {/* Tabs - with scroll indicator */}
        <div className="relative mb-4 sm:mb-6">
          <div className="flex gap-1 sm:gap-2 border-b border-white/10 pb-2 overflow-x-auto tabs-container scrollbar-thin scrollbar-thumb-[#D946EF]/30 scrollbar-track-transparent">
            {[
              { id: "dashboard", label: "Dashboard", icon: <Target className="w-3 h-3 sm:w-4 sm:h-4" />, count: positions.length || undefined },
              { id: "autotrade", label: "Auto-Trade", icon: <Cpu className="w-3 h-3 sm:w-4 sm:h-4" />, badge: autoTradeStatus?.auto_trade_enabled ? "ON" : null },
              { id: "discover", label: "Signals", icon: <Zap className="w-3 h-3 sm:w-4 sm:h-4" />, badge: "HOT" },
              { id: "social", label: "Social & Alerts", icon: <Users className="w-3 h-3 sm:w-4 sm:h-4" /> },
            ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              data-testid={`tab-${tab.id}`}
              className={`flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-1.5 sm:py-2 rounded-lg sm:rounded-xl text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-[#D946EF]/20 text-[#D946EF]"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {tab.icon}
              <span className="hidden xs:inline sm:inline">{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span className="px-1 sm:px-1.5 py-0.5 bg-[#D946EF] text-white text-[10px] sm:text-xs rounded-full">
                  {tab.count}
                </span>
              )}
              {tab.badge && (
                <span className="px-1 sm:px-1.5 py-0.5 bg-[#00FFA3] text-black text-[10px] sm:text-xs rounded-full font-bold">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
          </div>
          {/* Scroll hint for mobile */}
          <div className="absolute right-0 top-0 bottom-2 w-8 bg-gradient-to-l from-[#0A0A0F] to-transparent pointer-events-none sm:hidden" />
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-[#D946EF]" />
          </div>
        ) : (
          <>
            {/* ===== DASHBOARD TAB ===== */}
            {activeTab === "dashboard" && (
              <div className="space-y-6" data-testid="dashboard-content">
                {/* Positions Section */}
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Target className="w-5 h-5 text-[#D946EF]" />
                        Open Positions
                      </h3>
                      <p className="text-xs text-slate-500">
                        {positions.length} active position{positions.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={syncPositionsFromChain}
                        size="sm"
                        variant="outline"
                        className="border-[#00FFA3]/30 hover:bg-[#00FFA3]/10 text-[#00FFA3]"
                        data-testid="sync-positions-btn"
                        title="Sync positions from blockchain"
                      >
                        <RefreshCw className="w-4 h-4 mr-1" />
                        Sync
                      </Button>
                      <Button
                        onClick={fetchData}
                        size="sm"
                        variant="outline"
                        className="border-white/10 hover:bg-white/5 text-slate-300"
                        data-testid="refresh-positions-btn"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  
                  {/* Quick Settings Panel */}
                  <QuickSettings
                    autoTradeStatus={autoTradeStatus}
                    onUpdateSettings={updateAutoTradeSettings}
                  />

                  {/* Performance Scorecard */}
                  <PerformanceScorecard walletAddress={walletAddress} />
                  
                  {/* Risk Calculator */}
                  <RiskCalculator 
                    settings={settings}
                    positionSize={riskCalcPosition}
                    entryPrice={riskCalcEntryPrice}
                    onPositionChange={setRiskCalcPosition}
                    onEntryChange={setRiskCalcEntryPrice}
                  />
                  
                  {positions.length === 0 ? (
                    <div className="text-center py-12 bg-white/5 rounded-2xl border border-white/5">
                      <Target className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                      <p className="text-slate-400">No open positions</p>
                      <p className="text-sm text-slate-500 mt-1">Head to the Discover tab to find tokens</p>
                    </div>
                  ) : (
                    <>
                      {positions.some(p => p.executed_on_chain === false) && (
                        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <AlertCircle className="w-5 h-5 text-amber-400" />
                            <div>
                              <p className="text-sm text-amber-200 font-medium">Ghost Positions Detected</p>
                              <p className="text-xs text-amber-400/80">
                                {positions.filter(p => p.executed_on_chain === false).length} position(s) failed to execute on-chain
                              </p>
                            </div>
                          </div>
                          <Button
                            onClick={async () => {
                              if (!window.confirm("Remove all ghost positions? This will clear positions that failed to execute on-chain.")) return;
                              const ghostPositions = positions.filter(p => p.executed_on_chain === false);
                              for (const pos of ghostPositions) {
                                await deletePosition(pos);
                              }
                            }}
                            size="sm"
                            className="bg-amber-500 text-black hover:bg-amber-400"
                            data-testid="clear-ghost-positions"
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            Clear All Ghost
                          </Button>
                        </div>
                      )}
                      {positions.map(pos => (
                        <PositionCard 
                          key={pos.execution_id || pos.position_id} 
                          position={pos} 
                          onQuickSell={quickSell}
                          onDelete={deletePosition}
                          onManualClose={manualClosePosition}
                          onCustodialSell={custodialSell}
                          custodialWallet={custodialWallet}
                          onUseInCalculator={(position) => {
                            setRiskCalcPosition(position.amount_sol || 0.1);
                            setRiskCalcEntryPrice(position.entry_price || 1);
                            toast.success(`${position.token_symbol} loaded into Risk Calculator`);
                          }}
                        />
                      ))}
                    </>
                  )}
                </div>

                {/* Trade History Section */}
                <div className="border-t border-white/10 pt-6">
                  <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
                    <History className="w-5 h-5 text-[#00C2FF]" />
                    Recent Trade History
                  </h3>
                  {history.trades.length === 0 ? (
                    <div className="text-center py-8 bg-white/5 rounded-2xl">
                      <History className="w-10 h-10 mx-auto mb-3 text-slate-600" />
                      <p className="text-slate-400 text-sm">No trade history yet</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {history.trades.slice(0, 10).map(trade => (
                        <TradeHistoryCard key={trade.execution_id} trade={trade} />
                      ))}
                      {history.trades.length > 10 && (
                        <p className="text-center text-xs text-slate-500 pt-2">
                          Showing 10 of {history.trades.length} trades
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ===== DISCOVER TAB ===== */}
            {activeTab === "discover" && (
              <div className="space-y-6" data-testid="discover-content">
                {/* Active Signals Section */}
                {signals.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Zap className="w-5 h-5 text-[#D946EF]" />
                        Active Signals
                        <span className="px-1.5 py-0.5 bg-[#D946EF] text-white text-[10px] rounded-full">{signals.length}</span>
                      </h3>
                    </div>
                    {signals.map(signal => (
                      <SignalCard
                        key={signal.signal_id}
                        signal={signal}
                        onReject={() => rejectSignal(signal.signal_id)}
                        onQuickTrade={quickTrade}
                      />
                    ))}
                  </div>
                )}

                {/* Scan Markets CTA (when no signals) */}
                {signals.length === 0 && (
                  <div className="flex items-center justify-between bg-white/5 rounded-xl p-4 border border-white/5">
                    <div>
                      <p className="text-sm font-medium text-white">No active signals</p>
                      <p className="text-xs text-slate-500">Scan markets for trading opportunities</p>
                    </div>
                    <Button
                      onClick={scanMarkets}
                      disabled={scanning || !disclaimerAccepted}
                      size="sm"
                      className="bg-[#D946EF] hover:bg-[#D946EF]/80"
                      data-testid="scan-markets-btn"
                    >
                      {scanning ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Zap className="w-4 h-4 mr-1" />}
                      {scanning ? "Scanning..." : "Scan Markets"}
                    </Button>
                  </div>
                )}

                {/* Top Picks Section */}
                <div className={`${signals.length > 0 ? 'border-t border-white/10 pt-6' : ''}`}>
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="text-lg font-bold text-white">Top Picks</h3>
                    <p className="text-xs text-slate-500">
                      AI-curated Solana tokens for trading
                      {lastTopPicksUpdate && (
                        <span className="ml-2">
                          • Updated {lastTopPicksUpdate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </span>
                      )}
                    </p>
                  </div>
                  <Button
                    onClick={() => {
                      fetchTopPicks(true);
                      setRunnersRefreshing(true);
                      setRunnerRefreshTrigger(prev => prev + 1);
                    }}
                    disabled={topPicksLoading || topPicksRefreshing}
                    variant="outline"
                    size="sm"
                    className="border-white/20 text-slate-300"
                    data-testid="refresh-top-picks-btn"
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${(topPicksLoading || topPicksRefreshing) ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                </div>

                {/* Auto-refresh notice */}
                <div className="px-3 py-2 bg-[#00FFA3]/5 rounded-lg text-xs text-slate-500 flex items-center gap-2 border border-[#00FFA3]/10">
                  <span className="w-2 h-2 bg-[#00FFA3] rounded-full animate-pulse" />
                  Auto-refreshes every 5 mins • Click any token to generate a signal
                </div>

                {topPicksLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div key={i} className="h-20 bg-white/5 rounded-xl animate-pulse" />
                    ))}
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Safe Picks */}
                    <div>
                      <h4 className="flex items-center gap-2 text-sm font-bold text-[#00FFA3] mb-3">
                        {topPicksRefreshing ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <CheckCircle className="w-4 h-4" />
                        )}
                        SAFER PICKS
                        {topPicksRefreshing && (
                          <span className="text-[10px] px-2 py-0.5 bg-[#00FFA3]/10 text-[#00FFA3]/70 rounded-full">
                            Refreshing...
                          </span>
                        )}
                      </h4>
                      <div className={`space-y-2 ${topPicksRefreshing ? 'opacity-60' : ''} transition-opacity duration-300`}>
                        {topPicks.safe.length > 0 ? (
                          topPicks.safe.slice(0, 5).map((coin, i) => (
                            <TopPickCard
                              key={`safe-${i}`}
                              coin={coin}
                              index={i}
                              type="safe"
                              onCopy={copyToClipboard}
                              onQuickBuy={quickBuyToken}
                              onAnalyze={async () => {
                                if (!disclaimerAccepted) {
                                  toast.error("Please accept the disclaimer first");
                                  return;
                                }
                                const loadingToast = toast.loading(`Analyzing ${coin.symbol}...`);
                                try {
                                  const params = new URLSearchParams({
                                    wallet_address: walletAddress,
                                    ...(coin.contract_address && { contract_address: coin.contract_address })
                                  });
                                  const { data } = await axios.post(
                                    `${API}/ai-trader/analyze/${coin.symbol}?${params}`
                                  );
                                  toast.dismiss(loadingToast);
                                  if (data.signal) {
                                    toast.success(
                                      <div className="flex items-center gap-2">
                                        <span>Signal generated for {coin.symbol}</span>
                                        <button 
                                          onClick={() => setActiveTab("discover")}
                                          className="text-xs bg-white/20 px-2 py-1 rounded hover:bg-white/30"
                                        >
                                          View
                                        </button>
                                      </div>,
                                      { duration: 5000 }
                                    );
                                    setSignals(prev => [data.signal, ...prev]);
                                  } else {
                                    toast.info(data.message || "No strong signal detected");
                                  }
                                } catch (e) {
                                  toast.dismiss(loadingToast);
                                  toast.error(e.response?.data?.message || "Failed to analyze token");
                                }
                              }}
                            />
                          ))
                        ) : (
                          <p className="text-slate-500 text-sm text-center py-4">No safe picks available</p>
                        )}
                      </div>
                    </div>

                    {/* Volatile Picks */}
                    <div>
                      <h4 className="flex items-center gap-2 text-sm font-bold text-[#FF6B6B] mb-3">
                        {topPicksRefreshing ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <AlertCircle className="w-4 h-4" />
                        )}
                        HIGH RISK / HIGH REWARD
                        {topPicksRefreshing && (
                          <span className="text-[10px] px-2 py-0.5 bg-[#FF6B6B]/10 text-[#FF6B6B]/70 rounded-full">
                            Refreshing...
                          </span>
                        )}
                      </h4>
                      <div className={`space-y-2 ${topPicksRefreshing ? 'opacity-60' : ''} transition-opacity duration-300`}>
                        {topPicks.volatile.length > 0 ? (
                          topPicks.volatile.slice(0, 5).map((coin, i) => (
                            <TopPickCard
                              key={`volatile-${i}`}
                              coin={coin}
                              index={i}
                              type="volatile"
                              onCopy={copyToClipboard}
                              onQuickBuy={quickBuyToken}
                              onAnalyze={async () => {
                                if (!disclaimerAccepted) {
                                  toast.error("Please accept the disclaimer first");
                                  return;
                                }
                                const loadingToast = toast.loading(`Analyzing ${coin.symbol}...`);
                                try {
                                  const params = new URLSearchParams({
                                    wallet_address: walletAddress,
                                    ...(coin.contract_address && { contract_address: coin.contract_address })
                                  });
                                  const { data } = await axios.post(
                                    `${API}/ai-trader/analyze/${coin.symbol}?${params}`
                                  );
                                  toast.dismiss(loadingToast);
                                  if (data.signal) {
                                    toast.success(
                                      <div className="flex items-center gap-2">
                                        <span>Signal generated for {coin.symbol}</span>
                                        <button 
                                          onClick={() => setActiveTab("discover")}
                                          className="text-xs bg-white/20 px-2 py-1 rounded hover:bg-white/30"
                                        >
                                          View
                                        </button>
                                      </div>,
                                      { duration: 5000 }
                                    );
                                    setSignals(prev => [data.signal, ...prev]);
                                  } else {
                                    toast.info(data.message || "No strong signal detected");
                                  }
                                } catch (e) {
                                  toast.dismiss(loadingToast);
                                  toast.error(e.response?.data?.message || "Failed to analyze token");
                                }
                              }}
                            />
                          ))
                        ) : (
                          <p className="text-slate-500 text-sm text-center py-4">No volatile picks available</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Runner Tokens Section - Between High Risk and New Pairs */}
                <div className="mt-6 pt-6 border-t border-white/10">
                  <h4 className="flex items-center gap-2 text-sm font-bold text-[#D946EF] mb-3">
                    {runnersRefreshing ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Rocket className="w-4 h-4" />
                    )}
                    RUNNER TOKENS
                    {runnersRefreshing ? (
                      <span className="text-[10px] px-2 py-0.5 bg-[#D946EF]/10 text-[#D946EF]/70 rounded-full">
                        Refreshing...
                      </span>
                    ) : (
                      <span className="text-[10px] px-2 py-0.5 bg-[#D946EF]/20 text-[#D946EF] rounded-full animate-pulse">HOT</span>
                    )}
                  </h4>
                  <p className="text-xs text-slate-500 mb-3">
                    Trending tokens with high momentum - auto-trade candidates
                  </p>
                  <div className={`${runnersRefreshing ? 'opacity-60' : ''} transition-opacity duration-300`}>
                    <RunnerTokens 
                      onTradeRunner={(runner) => {
                        toast.info(`Analyzing ${runner.symbol}...`);
                        runAutoTradeScan();
                      }}
                      onQuickBuy={async (runner, amount) => {
                        // Convert runner to coin format for quickBuyToken
                        const coin = {
                          symbol: runner.symbol,
                          contract_address: runner.token_address,
                          price: runner.price_usd
                        };
                        await quickBuyToken(coin, amount);
                      }}
                      onAnalyze={async (runner) => {
                        if (!disclaimerAccepted) {
                          toast.error("Please accept the disclaimer first");
                          return;
                        }
                        const loadingToast = toast.loading(`Analyzing ${runner.symbol}...`);
                        try {
                          const params = new URLSearchParams({
                            wallet_address: walletAddress,
                            ...(runner.token_address && { contract_address: runner.token_address })
                          });
                          const { data } = await axios.post(
                            `${API}/ai-trader/analyze/${runner.symbol}?${params}`
                          );
                          toast.dismiss(loadingToast);
                          if (data.signal) {
                            toast.success(`Signal generated for ${runner.symbol}`);
                            setSignals(prev => [data.signal, ...prev]);
                          }
                        } catch (e) {
                          toast.dismiss(loadingToast);
                          toast.error(`Analysis failed: ${e.response?.data?.detail || e.message}`);
                        }
                      }}
                      onCopy={copyToClipboard}
                      custodialBalance={custodialWallet?.balance_sol || 0}
                      compact={true}
                      refreshTrigger={runnerRefreshTrigger}
                      onRefreshComplete={() => setRunnersRefreshing(false)}
                    />
                  </div>
                </div>

                {/* New Pairs Section */}
                {topPicks.newPairs && topPicks.newPairs.length > 0 && (
                  <div className="mt-6 pt-6 border-t border-white/10">
                    <h4 className="flex items-center gap-2 text-sm font-bold text-[#F5D300] mb-3">
                      {topPicksRefreshing ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Rocket className="w-4 h-4" />
                      )}
                      NEW PAIRS (Potential Runners)
                      {topPicksRefreshing && (
                        <span className="text-[10px] px-2 py-0.5 bg-[#F5D300]/10 text-[#F5D300]/70 rounded-full">
                          Refreshing...
                        </span>
                      )}
                    </h4>
                    <p className="text-xs text-slate-500 mb-3">
                      Recently created pairs that meet minimum criteria - extremely high risk
                    </p>
                    <div className={`grid md:grid-cols-2 gap-2 ${topPicksRefreshing ? 'opacity-60' : ''} transition-opacity duration-300`}>
                      {topPicks.newPairs.slice(0, 5).map((pair, i) => (
                        <TopPickCard
                          key={`new-${i}`}
                          coin={pair}
                          index={i}
                          type="new"
                          onCopy={copyToClipboard}
                          onQuickBuy={quickBuyToken}
                          onAnalyze={async () => {
                            if (!disclaimerAccepted) {
                              toast.error("Please accept the disclaimer first");
                              return;
                            }
                            const loadingToast = toast.loading(`Analyzing ${pair.symbol}...`);
                            try {
                              const params = new URLSearchParams({
                                wallet_address: walletAddress,
                                ...(pair.contract_address && { contract_address: pair.contract_address })
                              });
                              const { data } = await axios.post(
                                `${API}/ai-trader/analyze/${pair.symbol}?${params}`
                              );
                              toast.dismiss(loadingToast);
                              if (data.signal) {
                                toast.success(
                                  <div className="flex items-center gap-2">
                                    <span>Signal generated for {pair.symbol}</span>
                                    <button 
                                      onClick={() => setActiveTab("discover")}
                                      className="text-xs bg-white/20 px-2 py-1 rounded hover:bg-white/30"
                                    >
                                      View
                                    </button>
                                  </div>,
                                  { duration: 5000 }
                                );
                                setSignals(prev => [data.signal, ...prev]);
                              } else {
                                toast.info(data.message || "No strong signal detected");
                              }
                            } catch (e) {
                              toast.dismiss(loadingToast);
                              toast.error(e.response?.data?.message || "Failed to analyze token");
                            }
                          }}
                        />
                      ))}
                    </div>
                  </div>
                )}

                <p className="text-[10px] text-slate-600 text-center mt-4">
                  Memecoins are highly volatile. "Safer" means relatively lower risk, not safe. Always DYOR.
                </p>

                {/* Breakout Scanner Section */}
                <div className="border-t border-white/10 pt-6 space-y-4">
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    <div>
                      <h3 className="text-lg font-bold flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-[#F5D300]" />
                        Breakout Scanner
                      </h3>
                      <p className="text-xs text-slate-500 mt-1">
                        Tokens breaking out with &gt;10% gain in 1 hour + high volume
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={scanForBreakouts} className="bg-gradient-to-r from-[#F5D300] to-[#FF8C00] text-black hover:opacity-90" size="sm" data-testid="scan-breakouts-btn">
                        <Zap className="w-4 h-4 mr-1" /> Scan Breakouts
                      </Button>
                      <Button onClick={fetchAlerts} variant="outline" size="sm" className="border-white/20" data-testid="refresh-alerts-btn">
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  
                  {triggeredAlerts.length > 0 && (
                    <div className="bg-[#00FFA3]/10 border border-[#00FFA3]/30 rounded-xl p-4">
                      <h4 className="font-bold text-[#00FFA3] flex items-center gap-2 mb-2">
                        <CheckCircle className="w-4 h-4" /> Recently Triggered ({triggeredAlerts.length})
                      </h4>
                      <div className="space-y-2">
                        {triggeredAlerts.map((alert, i) => (
                          <div key={i} className="flex items-center justify-between bg-black/20 rounded-lg p-2 text-sm">
                            <div>
                              <span className="font-bold text-white">{alert.symbol}</span>
                              <span className="text-slate-400 ml-2">{alert.trigger_reason}</span>
                            </div>
                            <span className="text-[10px] text-slate-500">{new Date(alert.triggered_at).toLocaleTimeString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {alertsLoading ? (
                    <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-[#F5D300]" /></div>
                  ) : priceAlerts.length > 0 ? (
                    <div className="space-y-2">
                      <h4 className="text-sm font-bold text-slate-400">Active Alerts ({priceAlerts.length})</h4>
                      {priceAlerts.map((alert) => (
                        <AlertCard key={alert.alert_id} alert={alert} onDelete={deleteAlert} walletAddress={walletAddress} onQuickBuy={quickBuyToken} />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 bg-white/5 rounded-xl border border-dashed border-white/10">
                      <AlertCircle className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                      <p className="text-slate-400 text-sm">No active alerts</p>
                      <p className="text-xs text-slate-500 mt-1">Click "Scan Breakouts" to find opportunities</p>
                    </div>
                  )}
                </div>
                </div>
              </div>
            )}
            
            {/* Auto-Trade Tab - Now includes Analytics */}
            {activeTab === "autotrade" && (
              <UnifiedAutoTrader 
                status={autoTradeStatus}
                logs={autoTradeLogs}
                loading={autoTradeLoading}
                onToggle={toggleAutoTrade}
                onUpdateSettings={updateAutoTradeSettings}
                onRunScan={runAutoTradeScan}
                onRefresh={fetchAutoTradeStatus}
                custodialWallet={custodialWallet}
                onRefreshCustodial={fetchCustodialWallet}
                onWithdraw={withdrawFromCustodial}
                walletAddress={walletAddress}
                walletConnected={connected}
                traderSettings={settings}
                onSaveSettings={saveSettings}
              />
            )}
            
            {/* ===== SOCIAL & ALERTS TAB ===== */}
            {activeTab === "social" && (
              <div className="space-y-6" data-testid="social-alerts-content">
                {/* Notifications & Telegram */}
                <div className="space-y-4">
                  <RunnerAlertManager />
                  <PushNotificationManager />
                  
                  {/* Telegram Connection Banner */}
                  <div className={`rounded-xl p-4 border ${telegramLinked ? 'bg-[#0088CC]/10 border-[#0088CC]/30' : 'bg-[#0088CC]/5 border-[#0088CC]/20'}`}>
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${telegramLinked ? 'bg-[#0088CC]/30' : 'bg-[#0088CC]/20'}`}>
                          <svg className="w-5 h-5 text-[#0088CC]" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                          </svg>
                        </div>
                        <div>
                          <h4 className="font-bold text-white flex items-center gap-2">
                            Telegram Alerts
                            {telegramLinked && <span className="text-[10px] px-2 py-0.5 bg-[#00FFA3]/20 text-[#00FFA3] rounded-full">Connected</span>}
                          </h4>
                          <p className="text-xs text-slate-400">
                            {telegramLinked 
                              ? `Alerts will be sent to ${telegramStatus?.telegram_username ? '@' + telegramStatus.telegram_username : 'your Telegram'}`
                              : 'Get alerts directly in Telegram, even when offline!'
                            }
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {telegramLinked ? (
                          <Button onClick={unlinkTelegram} variant="outline" size="sm" className="border-[#FF6B6B]/30 text-[#FF6B6B] hover:bg-[#FF6B6B]/10">
                            <X className="w-4 h-4 mr-1" /> Unlink
                          </Button>
                        ) : (
                          <Button onClick={generateTelegramCode} disabled={telegramLoading} size="sm" className="bg-[#0088CC] hover:bg-[#0088CC]/80 text-white" data-testid="link-telegram-btn">
                            {telegramLoading ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Bell className="w-4 h-4 mr-1" />}
                            Link Telegram
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Telegram Link Modal */}
                {showTelegramModal && telegramLinkCode && (
                  <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setShowTelegramModal(false)}>
                    <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-[#0088CC]/30" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-bold flex items-center gap-2">
                          <svg className="w-5 h-5 text-[#0088CC]" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                          </svg>
                          Link Telegram
                        </h3>
                        <button onClick={() => setShowTelegramModal(false)} className="text-slate-400 hover:text-white">
                          <X className="w-5 h-5" />
                        </button>
                      </div>
                      <div className="space-y-4">
                        <div className="bg-[#0088CC]/10 rounded-xl p-4 text-center">
                          <p className="text-sm text-slate-400 mb-2">Your link code:</p>
                          <p className="text-3xl font-mono font-bold text-[#0088CC] tracking-widest">{telegramLinkCode.code}</p>
                          <p className="text-xs text-slate-500 mt-2">Expires in 15 minutes</p>
                        </div>
                        <div className="space-y-2 text-sm">
                          <p className="font-bold">Instructions:</p>
                          <ol className="list-decimal list-inside space-y-1 text-slate-400">
                            <li>Open Telegram</li>
                            <li>Search for <span className="text-[#0088CC] font-medium">@{telegramLinkCode.bot_username}</span></li>
                            <li>Send the code: <span className="font-mono text-white">{telegramLinkCode.code}</span></li>
                          </ol>
                        </div>
                        <a href={telegramLinkCode.bot_link} target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 w-full py-3 bg-[#0088CC] hover:bg-[#0088CC]/80 text-white font-medium rounded-xl transition-colors">
                          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
                          Open Telegram
                        </a>
                        <Button onClick={() => { setShowTelegramModal(false); fetchTelegramStatus(); }} variant="outline" className="w-full border-white/20">
                          I've sent the code
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Copy Trading Section */}
                <div className="border-t border-white/10 pt-6">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5 text-[#00FFA3]" />
                    Solana Copy Trading
                  </h3>
                  <SocialTrading />
                </div>
                
                <div className="border-t border-white/10 pt-6">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Globe className="w-5 h-5 text-[#00C2FF]" />
                    Multi-Chain Copy Trading
                  </h3>
                  <MultiChainCopyTrading />
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Deposit Modal — with auto-detection flow */}
      {showDepositModal && custodialWallet && (
        <DepositModal
          custodialWallet={custodialWallet}
          walletAddress={walletAddress}
          onClose={() => setShowDepositModal(false)}
          onDepositDetected={() => { fetchCustodialWallet(); }}
        />
      )}
    </div>
  );
}
