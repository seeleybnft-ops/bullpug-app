/**
 * Bullpug Trading Bot Page - Semi-automated trading with AI signals
 * Features: Auto-scan every 5 minutes, Quick Trade, Jupiter integration, Social Trading
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { VersionedTransaction } from "@solana/web3.js";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import axios from "axios";
import {
  Bot, Settings, TrendingUp, TrendingDown, AlertTriangle, 
  Check, X, Loader2, RefreshCw, Zap, Shield, Skull,
  DollarSign, Target, Clock, ArrowRight, ChevronDown, ChevronUp,
  Wallet, History, Play, Pause, Info, Copy, ExternalLink, Star,
  Rocket, CheckCircle, AlertCircle, Timer, Trash2, Share2, BarChart3, Bell,
  Cpu, ToggleLeft, ToggleRight, Activity, TrendingUp as TrendUp, Users, Globe
} from "lucide-react";
import { ShareButton, ShareTradeResult, ShareSignal, SharePortfolioPerformance } from "../components/SocialShare";
import SocialTrading from "../components/SocialTrading";
import PushNotificationManager from "../components/PushNotificationManager";
import SignalAnalyticsDashboard from "../components/SignalAnalyticsDashboard";
import MultiChainCopyTrading from "../components/MultiChainCopyTrading";
import UnifiedAutoTrader from "../components/UnifiedAutoTrader";
import RunnerTokens from "../components/RunnerTokens";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TRADING_BOT_IMAGE = "https://customer-assets.emergentagent.com/job_eece36b0-bd7c-41e3-9663-864558bfa54c/artifacts/79azcfdc_image%20-%202026-03-04T094746.318.jpg";
const AUTO_SCAN_INTERVAL = 5 * 60 * 1000; // 5 minutes in milliseconds

// Token mint addresses
const TOKENS = {
  SOL: "So11111111111111111111111111111111111111112",
  USDC: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  BONK: "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
  WIF: "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
  JUP: "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
};

// Risk level colors
const RISK_COLORS = {
  safer: { bg: "bg-[#00FFA3]/10", text: "text-[#00FFA3]", border: "border-[#00FFA3]/30" },
  high_risk: { bg: "bg-[#FF6B6B]/10", text: "text-[#FF6B6B]", border: "border-[#FF6B6B]/30" }
};

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
  const [activeTab, setActiveTab] = useState("autotrade");
  const [showSettings, setShowSettings] = useState(false);
  const [lastScan, setLastScan] = useState(null);
  const [autoScanEnabled, setAutoScanEnabled] = useState(true);
  
  // Top Picks state (moved from Bullpug AI)
  const [topPicks, setTopPicks] = useState({ safe: [], volatile: [], newPairs: [] });
  const [topPicksLoading, setTopPicksLoading] = useState(false);
  const [lastTopPicksUpdate, setLastTopPicksUpdate] = useState(null);
  
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
    }
    setLoading(false);
  }, [walletAddress]);

  // Fetch Top Picks (Safe, Volatile, New Pairs)
  const fetchTopPicks = useCallback(async () => {
    setTopPicksLoading(true);
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
        toast.success(`${data.signals_generated} trading signal(s) found!`);
        setSignals(prev => [...data.signals, ...prev]);
        setActiveTab("signals"); // Switch to signals tab
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
        setActiveTab("positions");
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
            {/* Auto-scan toggle */}
            <Button
              onClick={() => setAutoScanEnabled(!autoScanEnabled)}
              variant="outline"
              className={`border-white/20 ${autoScanEnabled ? 'text-[#00FFA3] border-[#00FFA3]/30' : 'text-slate-500'}`}
              data-testid="auto-scan-toggle"
              title={autoScanEnabled ? "Auto-scan enabled (5 min)" : "Auto-scan disabled"}
            >
              {autoScanEnabled ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </Button>
            <Button
              onClick={() => setShowSettings(true)}
              variant="outline"
              className="border-white/20 text-slate-300 hover:text-white hover:bg-white/5"
              data-testid="settings-btn"
            >
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
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

        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-4 mb-6 sm:mb-8">
          <StatCard
            icon={<TrendingUp className="w-4 h-4 sm:w-5 sm:h-5" />}
            label="Win Rate"
            value={loading ? "..." : `${history.stats.win_rate?.toFixed(1) || 0}%`}
            color={history.stats.win_rate >= 50 ? "#00FFA3" : "#FF6B6B"}
            testId="stat-win-rate"
          />
          <StatCard
            icon={<DollarSign className="w-4 h-4 sm:w-5 sm:h-5" />}
            label="Total P&L"
            value={loading ? "..." : `${history.stats.total_pnl_sol >= 0 ? '+' : ''}${history.stats.total_pnl_sol?.toFixed(4) || 0} SOL`}
            color={history.stats.total_pnl_sol >= 0 ? "#00FFA3" : "#FF6B6B"}
            testId="stat-pnl"
          />
          <StatCard
            icon={<History className="w-4 h-4 sm:w-5 sm:h-5" />}
            label="Total Trades"
            value={loading ? "..." : history.stats.total_trades || 0}
            color="#D946EF"
            testId="stat-trades"
          />
          <StatCard
            icon={<Target className="w-4 h-4 sm:w-5 sm:h-5" />}
            label="Open Positions"
            value={loading ? "..." : positions.length}
            color="#00C2FF"
            testId="stat-positions"
          />
        </div>
        
        {/* Share Performance Button */}
        {history.stats.total_trades > 0 && (
          <div className="flex justify-end mb-4">
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
              { id: "autotrade", label: "Auto-Trade", icon: <Cpu className="w-3 h-3 sm:w-4 sm:h-4" />, badge: autoTradeStatus?.auto_trade_enabled ? "ON" : null },
              { id: "tokens", label: "Top Picks", icon: <Rocket className="w-3 h-3 sm:w-4 sm:h-4" />, badge: "HOT" },
              { id: "signals", label: "Signals", icon: <Zap className="w-3 h-3 sm:w-4 sm:h-4" />, count: signals.length },
              { id: "alerts", label: "Breakouts", icon: <AlertCircle className="w-3 h-3 sm:w-4 sm:h-4" />, count: priceAlerts.length },
              { id: "social", label: "Copy Trading", icon: <Users className="w-3 h-3 sm:w-4 sm:h-4" /> },
              { id: "positions", label: "Positions", icon: <Target className="w-3 h-3 sm:w-4 sm:h-4" />, count: positions.length },
              { id: "history", label: "Trade History", icon: <History className="w-3 h-3 sm:w-4 sm:h-4" /> }
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
            {/* Signals Tab */}
            {activeTab === "signals" && (
              <div className="space-y-4" data-testid="signals-content">
                {signals.length === 0 ? (
                  <div className="text-center py-16 bg-white/5 rounded-2xl border border-white/5" data-testid="no-signals">
                    <Zap className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <h3 className="text-lg font-semibold mb-2">No pending signals</h3>
                    <p className="text-sm text-slate-500 mb-6 max-w-md mx-auto">
                      Click "Scan Markets" to analyze tokens for trading opportunities based on technical indicators like RSI, MACD, and Bollinger Bands.
                    </p>
                    <Button
                      onClick={scanMarkets}
                      disabled={scanning || !disclaimerAccepted}
                      className="bg-[#D946EF] hover:bg-[#D946EF]/80"
                    >
                      {scanning ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Zap className="w-4 h-4 mr-2" />
                      )}
                      {scanning ? "Scanning..." : "Scan Markets Now"}
                    </Button>
                  </div>
                ) : (
                  signals.map(signal => (
                    <SignalCard
                      key={signal.signal_id}
                      signal={signal}
                      onReject={() => rejectSignal(signal.signal_id)}
                      onQuickTrade={quickTrade}
                    />
                  ))
                )}
              </div>
            )}

            {/* Positions Tab */}
            {activeTab === "positions" && (
              <div className="space-y-4" data-testid="positions-content">
                {/* Header with Refresh & Sync */}
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
                <div className="bg-gradient-to-r from-[#D946EF]/5 to-[#00FFA3]/5 border border-white/10 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Settings className="w-4 h-4 text-[#D946EF]" />
                      Quick Settings
                    </h4>
                    <span className="text-xs text-slate-500">Changes apply to all positions</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">Take Profit %</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="5"
                          max="100"
                          value={autoTradeStatus?.settings?.take_profit_percent || 25}
                          onChange={(e) => {
                            const value = parseInt(e.target.value);
                            updateAutoTradeSettings({ auto_take_profit_percent: value });
                          }}
                          className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-[#00FFA3]"
                          data-testid="quick-tp-slider"
                        />
                        <span className="text-sm font-bold text-[#00FFA3] w-12 text-right">
                          {autoTradeStatus?.settings?.take_profit_percent || 25}%
                        </span>
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">Stop Loss %</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="5"
                          max="50"
                          value={autoTradeStatus?.settings?.stop_loss_percent || 15}
                          onChange={(e) => {
                            const value = parseInt(e.target.value);
                            updateAutoTradeSettings({ auto_stop_loss_percent: value });
                          }}
                          className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-[#FF6B6B]"
                          data-testid="quick-sl-slider"
                        />
                        <span className="text-sm font-bold text-[#FF6B6B] w-12 text-right">
                          {autoTradeStatus?.settings?.stop_loss_percent || 15}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Risk Calculator */}
                <RiskCalculator settings={settings} />
                
                {positions.length === 0 ? (
                  <div className="text-center py-16 bg-white/5 rounded-2xl border border-white/5">
                    <Target className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p className="text-slate-400">No open positions</p>
                    <p className="text-sm text-slate-500 mt-1">Buy tokens from the Tokens tab to create positions</p>
                  </div>
                ) : (
                  <>
                    {/* Ghost Position Warning & Cleanup */}
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
                      />
                    ))}
                  </>
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

            {/* Tokens Tab - Now shows Top Picks */}
            {activeTab === "tokens" && (
              <div className="space-y-6" data-testid="tokens-content">
                {/* Header with refresh */}
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
                    onClick={fetchTopPicks}
                    disabled={topPicksLoading}
                    variant="outline"
                    size="sm"
                    className="border-white/20 text-slate-300"
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${topPicksLoading ? 'animate-spin' : ''}`} />
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
                        <CheckCircle className="w-4 h-4" />
                        SAFER PICKS
                      </h4>
                      <div className="space-y-2">
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
                                    toast.success(`Signal generated for ${coin.symbol}`);
                                    setSignals(prev => [data.signal, ...prev]);
                                    setActiveTab("signals");
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
                        <AlertCircle className="w-4 h-4" />
                        HIGH RISK / HIGH REWARD
                      </h4>
                      <div className="space-y-2">
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
                                    toast.success(`Signal generated for ${coin.symbol}`);
                                    setSignals(prev => [data.signal, ...prev]);
                                    setActiveTab("signals");
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
                    <Rocket className="w-4 h-4" />
                    RUNNER TOKENS
                    <span className="text-[10px] px-2 py-0.5 bg-[#D946EF]/20 text-[#D946EF] rounded-full animate-pulse">HOT</span>
                  </h4>
                  <p className="text-xs text-slate-500 mb-3">
                    Trending tokens with high momentum - auto-trade candidates
                  </p>
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
                  />
                </div>

                {/* New Pairs Section */}
                {topPicks.newPairs && topPicks.newPairs.length > 0 && (
                  <div className="mt-6 pt-6 border-t border-white/10">
                    <h4 className="flex items-center gap-2 text-sm font-bold text-[#F5D300] mb-3">
                      <Rocket className="w-4 h-4" />
                      NEW PAIRS (Potential Runners)
                    </h4>
                    <p className="text-xs text-slate-500 mb-3">
                      Recently created pairs that meet minimum criteria - extremely high risk
                    </p>
                    <div className="grid md:grid-cols-2 gap-2">
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
                                toast.success(`Signal generated for ${pair.symbol}`);
                                setSignals(prev => [data.signal, ...prev]);
                                setActiveTab("signals");
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
                  ⚠️ Memecoins are highly volatile. "Safer" means relatively lower risk, not safe. Always DYOR.
                </p>
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
              />
            )}
            
            {/* Combined Copy Trading Tab - Social + Multi-Chain */}
            {activeTab === "social" && (
              <div className="space-y-6">
                {/* Solana Copy Trading */}
                <div>
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5 text-[#00FFA3]" />
                    Solana Copy Trading
                  </h3>
                  <SocialTrading />
                </div>
                
                {/* Divider */}
                <div className="border-t border-white/10 pt-6">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Globe className="w-5 h-5 text-[#00C2FF]" />
                    Multi-Chain Copy Trading
                  </h3>
                  <MultiChainCopyTrading />
                </div>
              </div>
            )}
            
            {/* Alerts Tab */}
            {activeTab === "alerts" && (
              <div className="space-y-4" data-testid="alerts-tab">
                {/* Push Notifications for Copy Trading */}
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
                        <Button
                          onClick={unlinkTelegram}
                          variant="outline"
                          size="sm"
                          className="border-[#FF6B6B]/30 text-[#FF6B6B] hover:bg-[#FF6B6B]/10"
                        >
                          <X className="w-4 h-4 mr-1" />
                          Unlink
                        </Button>
                      ) : (
                        <Button
                          onClick={generateTelegramCode}
                          disabled={telegramLoading}
                          size="sm"
                          className="bg-[#0088CC] hover:bg-[#0088CC]/80 text-white"
                          data-testid="link-telegram-btn"
                        >
                          {telegramLoading ? (
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          ) : (
                            <Bell className="w-4 h-4 mr-1" />
                          )}
                          Link Telegram
                        </Button>
                      )}
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
                        
                        <a
                          href={telegramLinkCode.bot_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-center gap-2 w-full py-3 bg-[#0088CC] hover:bg-[#0088CC]/80 text-white font-medium rounded-xl transition-colors"
                        >
                          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                          </svg>
                          Open Telegram
                        </a>
                        
                        <Button
                          onClick={() => { setShowTelegramModal(false); fetchTelegramStatus(); }}
                          variant="outline"
                          className="w-full border-white/20"
                        >
                          I've sent the code
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Alerts Header */}
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <h3 className="text-lg font-bold flex items-center gap-2">
                      <AlertCircle className="w-5 h-5 text-[#F5D300]" />
                      Price Alerts & Breakout Scanner
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Get notified when tokens break out or hit your price targets
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={scanForBreakouts}
                      className="bg-gradient-to-r from-[#F5D300] to-[#FF8C00] text-black hover:opacity-90"
                      size="sm"
                      data-testid="scan-breakouts-btn"
                    >
                      <Zap className="w-4 h-4 mr-1" />
                      Scan Breakouts
                    </Button>
                    <Button
                      onClick={fetchAlerts}
                      variant="outline"
                      size="sm"
                      className="border-white/20"
                      data-testid="refresh-alerts-btn"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                
                {/* Triggered Alerts Banner */}
                {triggeredAlerts.length > 0 && (
                  <div className="bg-[#00FFA3]/10 border border-[#00FFA3]/30 rounded-xl p-4">
                    <h4 className="font-bold text-[#00FFA3] flex items-center gap-2 mb-2">
                      <CheckCircle className="w-4 h-4" />
                      Recently Triggered ({triggeredAlerts.length})
                    </h4>
                    <div className="space-y-2">
                      {triggeredAlerts.map((alert, i) => (
                        <div key={i} className="flex items-center justify-between bg-black/20 rounded-lg p-2 text-sm">
                          <div>
                            <span className="font-bold text-white">{alert.symbol}</span>
                            <span className="text-slate-400 ml-2">{alert.trigger_reason}</span>
                          </div>
                          <span className="text-[10px] text-slate-500">
                            {new Date(alert.triggered_at).toLocaleTimeString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Info Banner */}
                <div className="bg-[#F5D300]/10 border border-[#F5D300]/20 rounded-xl p-3">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 text-[#F5D300] flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-slate-300">
                      <p><strong>Breakout Alerts</strong> trigger when a token gains &gt;10% in 1 hour with high volume.</p>
                      <p className="mt-1 text-slate-500">
                        {telegramLinked 
                          ? '✅ Telegram connected - you\'ll receive alerts there too!'
                          : 'Link Telegram above to receive alerts even when offline.'
                        }
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Active Alerts List */}
                {alertsLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-[#F5D300]" />
                  </div>
                ) : priceAlerts.length > 0 ? (
                  <div className="space-y-2">
                    <h4 className="text-sm font-bold text-slate-400">Active Alerts ({priceAlerts.length})</h4>
                    {priceAlerts.map((alert) => (
                      <AlertCard 
                        key={alert.alert_id}
                        alert={alert}
                        onDelete={deleteAlert}
                        walletAddress={walletAddress}
                        onQuickBuy={quickBuyToken}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 bg-white/5 rounded-xl border border-dashed border-white/10">
                    <AlertCircle className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                    <p className="text-slate-400">No active alerts</p>
                    <p className="text-xs text-slate-500 mt-1">Click "Scan Breakouts" to find potential opportunities</p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Sub-components
function StatCard({ icon, label, value, color, testId }) {
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/5 hover:border-white/10 transition-colors" data-testid={testId}>
      <div className="flex items-center gap-2 text-slate-400 mb-2">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-xl font-bold" style={{ color }}>{value}</p>
    </div>
  );
}

// Risk Calculator Component
function RiskCalculator({ settings }) {
  const [positionSize, setPositionSize] = useState(0.1);
  const [entryPrice, setEntryPrice] = useState(1);
  const [stopLoss, setStopLoss] = useState(10);
  const [takeProfit, setTakeProfit] = useState(25);
  
  const maxLoss = positionSize * (stopLoss / 100);
  const potentialProfit = positionSize * (takeProfit / 100);
  const riskRewardRatio = takeProfit / stopLoss;
  
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-[#D946EF]/20 mb-4" data-testid="risk-calculator">
      <h4 className="flex items-center gap-2 text-sm font-bold text-[#D946EF] mb-4">
        <AlertTriangle className="w-4 h-4" />
        Risk Calculator
      </h4>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Position (SOL)</label>
          <input
            type="number"
            value={positionSize}
            onChange={(e) => setPositionSize(Math.max(0.01, parseFloat(e.target.value) || 0))}
            step="0.01"
            min="0.01"
            className="w-full bg-white/10 border border-white/20 rounded px-2 py-1.5 text-xs font-mono text-white focus:border-[#D946EF] focus:outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Entry Price ($)</label>
          <input
            type="number"
            value={entryPrice}
            onChange={(e) => setEntryPrice(Math.max(0.000001, parseFloat(e.target.value) || 0))}
            step="0.01"
            min="0.000001"
            className="w-full bg-white/10 border border-white/20 rounded px-2 py-1.5 text-xs font-mono text-white focus:border-[#D946EF] focus:outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Stop Loss (%)</label>
          <input
            type="number"
            value={stopLoss}
            onChange={(e) => setStopLoss(Math.max(1, parseFloat(e.target.value) || 0))}
            step="1"
            min="1"
            max="100"
            className="w-full bg-white/10 border border-white/20 rounded px-2 py-1.5 text-xs font-mono text-white focus:border-[#FF6B6B] focus:outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] text-slate-500 block mb-1">Take Profit (%)</label>
          <input
            type="number"
            value={takeProfit}
            onChange={(e) => setTakeProfit(Math.max(1, parseFloat(e.target.value) || 0))}
            step="1"
            min="1"
            className="w-full bg-white/10 border border-white/20 rounded px-2 py-1.5 text-xs font-mono text-white focus:border-[#00FFA3] focus:outline-none"
          />
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="bg-[#FF6B6B]/10 rounded-lg p-2">
          <p className="text-[10px] text-slate-500">Max Loss</p>
          <p className="text-sm font-bold text-[#FF6B6B]">-{maxLoss.toFixed(4)} SOL</p>
        </div>
        <div className="bg-[#00FFA3]/10 rounded-lg p-2">
          <p className="text-[10px] text-slate-500">Potential Profit</p>
          <p className="text-sm font-bold text-[#00FFA3]">+{potentialProfit.toFixed(4)} SOL</p>
        </div>
        <div className={`${riskRewardRatio >= 2 ? 'bg-[#00FFA3]/10' : 'bg-[#F5D300]/10'} rounded-lg p-2`}>
          <p className="text-[10px] text-slate-500">Risk:Reward</p>
          <p className={`text-sm font-bold ${riskRewardRatio >= 2 ? 'text-[#00FFA3]' : 'text-[#F5D300]'}`}>
            1:{riskRewardRatio.toFixed(1)}
          </p>
        </div>
      </div>
      
      <p className="text-[10px] text-slate-500 text-center mt-2">
        {riskRewardRatio >= 2 ? '✓ Good risk:reward ratio (≥1:2)' : '⚠ Consider higher take profit for better R:R'}
      </p>
    </div>
  );
}

// Auto-Trade Tab Component
function AutoTradeTab({ status, logs, loading, onToggle, onUpdateSettings, onRunScan, onRefresh, custodialWallet, onRefreshCustodial, onWithdraw, walletAddress, walletConnected }) {
  const [showSettingsPanel, setShowSettingsPanel] = useState(false);
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [depositAmount, setDepositAmount] = useState("");
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [settingsForm, setSettingsForm] = useState({
    auto_trade_mode: status?.settings?.mode || "conservative",
    auto_min_confidence: status?.settings?.min_confidence || 0.65,
    auto_max_daily_trades: status?.settings?.max_daily_trades || 3,
    auto_max_position_sol: status?.settings?.max_position_sol || 0.2,
    auto_cooldown_minutes: status?.settings?.cooldown_minutes || 30,
    auto_require_multiple_signals: status?.settings?.require_multiple_signals !== false,
    auto_pause_on_loss: status?.settings?.pause_on_loss !== false,
    auto_total_daily_limit_sol: status?.settings?.total_daily_limit_sol || 1.0,
    auto_stop_loss_percent: status?.settings?.stop_loss_percent || 10,
    auto_take_profit_percent: status?.settings?.take_profit_percent || 20
  });

  // Safe clipboard copy with fallback
  const safeCopyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Address copied!");
    } catch (e) {
      // Fallback for browsers/contexts where clipboard API is blocked
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.left = "-9999px";
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand("copy");
        toast.success("Address copied!");
      } catch (err) {
        toast.error("Failed to copy. Please copy manually.");
      }
      document.body.removeChild(textArea);
    }
  };

  // Update form when status changes
  useEffect(() => {
    if (status?.settings) {
      setSettingsForm({
        auto_trade_mode: status.settings.mode || "conservative",
        auto_min_confidence: status.settings.min_confidence || 0.65,
        auto_max_daily_trades: status.settings.max_daily_trades || 3,
        auto_max_position_sol: status.settings.max_position_sol || 0.2,
        auto_cooldown_minutes: status.settings.cooldown_minutes || 30,
        auto_require_multiple_signals: status.settings.require_multiple_signals !== false,
        auto_pause_on_loss: status.settings.pause_on_loss !== false,
        auto_total_daily_limit_sol: status.settings.total_daily_limit_sol || 1.0,
        auto_stop_loss_percent: status.settings.stop_loss_percent || 10,
        auto_take_profit_percent: status.settings.take_profit_percent || 20
      });
    }
  }, [status]);

  const handleSaveSettings = () => {
    onUpdateSettings(settingsForm);
    setShowSettingsPanel(false);
  };

  if (loading && !status) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-[#D946EF]" />
      </div>
    );
  }

  const isEnabled = status?.auto_trade_enabled;
  const isPaused = status?.auto_paused;
  const todayStats = status?.today_stats || { trades_executed: 0, total_sol_used: 0 };

  return (
    <div className="space-y-6" data-testid="autotrade-tab">
      {/* Main Toggle Card */}
      <div className={`rounded-2xl p-6 border transition-all ${
        isEnabled && !isPaused 
          ? 'bg-gradient-to-br from-[#00FFA3]/10 to-[#00C2FF]/10 border-[#00FFA3]/30' 
          : 'bg-white/5 border-white/10'
      }`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${
              isEnabled && !isPaused ? 'bg-[#00FFA3]/20' : 'bg-white/10'
            }`}>
              <Cpu className={`w-7 h-7 ${isEnabled && !isPaused ? 'text-[#00FFA3]' : 'text-slate-500'}`} />
            </div>
            <div>
              <h3 className="text-xl font-bold flex items-center gap-2">
                Auto-Trade Bot
                {isEnabled && (
                  <span className={`px-2 py-0.5 text-[10px] rounded-full font-bold ${
                    isPaused ? 'bg-[#F5D300]/20 text-[#F5D300]' : 'bg-[#00FFA3]/20 text-[#00FFA3]'
                  }`}>
                    {isPaused ? 'PAUSED' : 'ACTIVE'}
                  </span>
                )}
              </h3>
              <p className="text-sm text-slate-400">
                {isEnabled 
                  ? isPaused 
                    ? status.pause_reason || 'Auto-trading is paused'
                    : 'Automatically executing trades based on AI signals'
                  : 'Enable to let AI execute trades automatically'
                }
              </p>
            </div>
          </div>
          
          <button
            onClick={() => onToggle(!isEnabled)}
            className={`relative w-16 h-8 rounded-full transition-all ${
              isEnabled ? 'bg-[#00FFA3]' : 'bg-slate-700'
            }`}
            data-testid="auto-trade-toggle"
          >
            <div className={`absolute top-1 w-6 h-6 rounded-full bg-white shadow-lg transition-all ${
              isEnabled ? 'left-9' : 'left-1'
            }`} />
          </button>
        </div>

        {/* Warning Banner */}
        <div className="flex items-start gap-2 px-4 py-3 bg-[#FF6B6B]/10 border border-[#FF6B6B]/20 rounded-xl text-sm">
          <AlertTriangle className="w-5 h-5 text-[#FF6B6B] flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-[#FF6B6B] font-medium">High Risk Feature</p>
            <p className="text-slate-400 text-xs mt-1">
              Auto-trading executes real trades with your funds. Use with caution and only risk what you can afford to lose.
            </p>
          </div>
        </div>
      </div>

      {/* Custodial Wallet Card - For Automated Execution */}
      <div className="rounded-2xl p-5 bg-gradient-to-br from-[#D946EF]/5 to-[#00C2FF]/5 border border-[#D946EF]/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-[#D946EF]/20 flex items-center justify-center">
              <Wallet className="w-6 h-6 text-[#D946EF]" />
            </div>
            <div>
              <h4 className="font-bold text-white flex items-center gap-2">
                Trading Wallet
                <span className="text-[8px] px-1.5 py-0.5 bg-[#D946EF]/20 text-[#D946EF] rounded-full">HYBRID</span>
              </h4>
              <p className="text-xs text-slate-400">Deposit SOL for automated execution</p>
            </div>
          </div>
          <button onClick={onRefreshCustodial} className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
            <RefreshCw className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {custodialWallet ? (
          <>
            {/* Balance Display */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-black/30 rounded-xl p-3">
                <p className="text-[10px] text-slate-500 uppercase mb-1">Available Balance</p>
                <p className="text-2xl font-bold text-[#00FFA3]">{custodialWallet.balance_sol?.toFixed(4)} SOL</p>
              </div>
              <div className="bg-black/30 rounded-xl p-3">
                <p className="text-[10px] text-slate-500 uppercase mb-1">Max Deposit</p>
                <p className="text-2xl font-bold text-slate-300">{custodialWallet.max_deposit_sol} SOL</p>
                <p className="text-[10px] text-slate-500">Can add: {custodialWallet.available_deposit_sol?.toFixed(4)} SOL</p>
              </div>
            </div>

            {/* Deposit Address */}
            <div className="bg-black/20 rounded-xl p-3 mb-4">
              <p className="text-[10px] text-slate-500 uppercase mb-1">Deposit Address</p>
              <div className="flex items-center gap-2">
                <code className="text-xs text-white font-mono flex-1 truncate">{custodialWallet.wallet_address}</code>
                <button 
                  onClick={() => safeCopyToClipboard(custodialWallet.wallet_address)}
                  className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                >
                  <Copy className="w-3.5 h-3.5 text-slate-300" />
                </button>
              </div>
              <p className="text-[10px] text-[#F5D300] mt-2">
                Send SOL directly to this address or use Deposit button below
              </p>
            </div>

            {/* Deposit/Withdraw Actions */}
            <div className="flex gap-3">
              <Button
                onClick={() => setShowDepositModal(true)}
                disabled={custodialWallet.available_deposit_sol <= 0}
                className="flex-1 bg-[#00FFA3] text-black hover:bg-[#00FFA3]/80 disabled:opacity-50"
                data-testid="deposit-btn"
              >
                <ArrowRight className="w-4 h-4 mr-2 rotate-90" />
                Deposit
              </Button>
              <Button
                onClick={() => {
                  const amount = prompt(`Withdraw SOL (max: ${custodialWallet.balance_sol?.toFixed(4)})`);
                  if (amount && parseFloat(amount) > 0) {
                    onWithdraw(amount);
                  }
                }}
                disabled={custodialWallet.balance_sol <= 0.00001}
                variant="outline"
                className="flex-1 border-white/20 text-slate-300 disabled:opacity-50"
                data-testid="withdraw-btn"
              >
                <ArrowRight className="w-4 h-4 mr-2 -rotate-90" />
                Withdraw
              </Button>
            </div>

            {/* Deposit Modal */}
            {showDepositModal && (
              <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
                <div className="bg-[#12121A] rounded-2xl p-6 max-w-md w-full border border-white/10">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Wallet className="w-5 h-5 text-[#D946EF]" />
                    Deposit to Trading Wallet
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm text-slate-400 mb-1 block">Amount (SOL)</label>
                      <div className="flex gap-2">
                        <Input
                          type="number"
                          step="0.01"
                          max={custodialWallet.available_deposit_sol}
                          value={depositAmount}
                          onChange={(e) => setDepositAmount(e.target.value)}
                          placeholder={`Max: ${custodialWallet.available_deposit_sol?.toFixed(4)}`}
                          className="flex-1 bg-black/40 border-white/10"
                        />
                        <Button
                          onClick={() => setDepositAmount(custodialWallet.available_deposit_sol?.toFixed(4))}
                          variant="outline"
                          className="border-white/20"
                        >
                          Max
                        </Button>
                      </div>
                    </div>

                    <div className="bg-[#F5D300]/10 rounded-xl p-3 border border-[#F5D300]/20">
                      <p className="text-xs text-[#F5D300] flex items-center gap-2">
                        <Info className="w-4 h-4" />
                        Send {depositAmount || '0'} SOL to:
                      </p>
                      <code className="text-[10px] text-white font-mono mt-1 block break-all">
                        {custodialWallet.wallet_address}
                      </code>
                    </div>

                    <p className="text-[10px] text-slate-500">
                      After sending, click "Confirm Deposit" once the transaction is complete on-chain.
                    </p>

                    <div className="flex gap-3">
                      <Button
                        onClick={() => {
                          setShowDepositModal(false);
                          setDepositAmount("");
                        }}
                        variant="outline"
                        className="flex-1 border-white/20"
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={async () => {
                          // Copy address and close
                          await safeCopyToClipboard(custodialWallet.wallet_address);
                          toast.success("Send SOL and refresh balance.");
                          setShowDepositModal(false);
                          setDepositAmount("");
                        }}
                        className="flex-1 bg-[#00FFA3] text-black hover:bg-[#00FFA3]/80"
                      >
                        <Copy className="w-4 h-4 mr-2" />
                        Copy Address
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-4">
            <p className="text-slate-500 text-sm">Loading trading wallet...</p>
          </div>
        )}

        {/* Info about custodial wallet */}
        <div className="mt-4 pt-4 border-t border-white/5">
          <p className="text-[10px] text-slate-500">
            <span className="text-[#D946EF]">Hybrid Mode:</span> Funds in this wallet can be used for automated trades. 
            Your main wallet remains untouched. Max limit: {custodialWallet?.max_deposit_sol || 0.5} SOL for safety.
          </p>
        </div>
      </div>

      {/* Today's Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white/5 rounded-xl p-4 border border-white/5">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <Activity className="w-4 h-4" />
            <span className="text-xs">Trades Today</span>
          </div>
          <p className="text-xl font-bold text-white">
            {todayStats.trades_executed}/{status?.settings?.max_daily_trades || 3}
          </p>
        </div>
        <div className="bg-white/5 rounded-xl p-4 border border-white/5">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <DollarSign className="w-4 h-4" />
            <span className="text-xs">SOL Used</span>
          </div>
          <p className="text-xl font-bold text-white">
            {todayStats.total_sol_used?.toFixed(3) || '0.000'}
          </p>
        </div>
        <div className="bg-white/5 rounded-xl p-4 border border-white/5">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <Target className="w-4 h-4" />
            <span className="text-xs">Mode</span>
          </div>
          <p className="text-xl font-bold capitalize" style={{ color: 
            status?.settings?.mode === 'aggressive' ? '#FF6B6B' : 
            status?.settings?.mode === 'moderate' ? '#F5D300' : '#00FFA3'
          }}>
            {status?.settings?.mode || 'Conservative'}
          </p>
        </div>
        <div className="bg-white/5 rounded-xl p-4 border border-white/5">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <Timer className="w-4 h-4" />
            <span className="text-xs">Cooldown</span>
          </div>
          <p className="text-xl font-bold text-white">
            {status?.settings?.cooldown_minutes || 30}m
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        <Button
          onClick={onRunScan}
          disabled={!isEnabled || isPaused}
          className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] hover:opacity-90 disabled:opacity-50"
          data-testid="run-auto-scan-btn"
        >
          <Zap className="w-4 h-4 mr-2" />
          Run Auto-Scan Now
        </Button>
        <Button
          onClick={() => setShowSettingsPanel(!showSettingsPanel)}
          variant="outline"
          className="border-white/20 text-slate-300"
        >
          <Settings className="w-4 h-4 mr-2" />
          Configure Settings
        </Button>
        <Button
          onClick={onRefresh}
          variant="outline"
          className="border-white/20 text-slate-300"
        >
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Settings Panel */}
      {showSettingsPanel && (
        <div className="bg-[#12121A] rounded-2xl p-6 border border-white/10 space-y-5">
          <h4 className="font-bold text-lg flex items-center gap-2">
            <Settings className="w-5 h-5 text-[#D946EF]" />
            Auto-Trade Configuration
          </h4>

          <div className="grid md:grid-cols-2 gap-5">
            {/* Mode Selection */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">Trading Mode</label>
              <select
                value={settingsForm.auto_trade_mode}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_trade_mode: e.target.value }))}
                className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white"
              >
                <option value="conservative">Conservative (Safest)</option>
                <option value="moderate">Moderate (Balanced)</option>
                <option value="aggressive">Aggressive (Risky)</option>
              </select>
              <p className="text-[10px] text-slate-500 mt-1">
                {settingsForm.auto_trade_mode === 'conservative' && 'Higher confidence required, one trade per scan'}
                {settingsForm.auto_trade_mode === 'moderate' && 'Balanced approach with standard settings'}
                {settingsForm.auto_trade_mode === 'aggressive' && 'Lower confidence threshold, more frequent trades'}
              </p>
            </div>

            {/* Min Confidence */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">
                Min Confidence: {(settingsForm.auto_min_confidence * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0.5"
                max="0.9"
                step="0.05"
                value={settingsForm.auto_min_confidence}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_min_confidence: parseFloat(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>50%</span>
                <span>90%</span>
              </div>
            </div>

            {/* Max Position */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">
                Max Position: {settingsForm.auto_max_position_sol} SOL
              </label>
              <input
                type="range"
                min="0.01"
                max="1"
                step="0.01"
                value={settingsForm.auto_max_position_sol}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_max_position_sol: parseFloat(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>0.01 SOL</span>
                <span>1 SOL</span>
              </div>
            </div>

            {/* Daily Limit */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">
                Daily SOL Limit: {settingsForm.auto_total_daily_limit_sol} SOL
              </label>
              <input
                type="range"
                min="0.1"
                max="5"
                step="0.1"
                value={settingsForm.auto_total_daily_limit_sol}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_total_daily_limit_sol: parseFloat(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>0.1 SOL</span>
                <span>5 SOL</span>
              </div>
            </div>

            {/* Max Daily Trades */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">
                Max Daily Trades: {settingsForm.auto_max_daily_trades}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={settingsForm.auto_max_daily_trades}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_max_daily_trades: parseInt(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>1</span>
                <span>10</span>
              </div>
            </div>

            {/* Cooldown */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">
                Cooldown: {settingsForm.auto_cooldown_minutes} minutes
              </label>
              <input
                type="range"
                min="5"
                max="120"
                step="5"
                value={settingsForm.auto_cooldown_minutes}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_cooldown_minutes: parseInt(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>5 min</span>
                <span>120 min</span>
              </div>
            </div>

            {/* Stop Loss */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">
                Stop Loss: {settingsForm.auto_stop_loss_percent}%
              </label>
              <input
                type="range"
                min="2"
                max="50"
                step="1"
                value={settingsForm.auto_stop_loss_percent}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_stop_loss_percent: parseInt(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>2%</span>
                <span>50%</span>
              </div>
              <p className="text-[10px] text-[#FF6B6B] mt-1">Auto-sell if price drops by this %</p>
            </div>

            {/* Take Profit */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">
                Take Profit: {settingsForm.auto_take_profit_percent}%
              </label>
              <input
                type="range"
                min="5"
                max="200"
                step="5"
                value={settingsForm.auto_take_profit_percent}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_take_profit_percent: parseInt(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>5%</span>
                <span>200%</span>
              </div>
              <p className="text-[10px] text-[#00FFA3] mt-1">Auto-sell if price rises by this %</p>
            </div>
          </div>

          {/* Toggle Options */}
          <div className="flex flex-wrap gap-4 pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settingsForm.auto_require_multiple_signals}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_require_multiple_signals: e.target.checked }))}
                className="w-4 h-4 rounded border-white/30"
              />
              <span className="text-sm text-slate-300">Require 2+ strategies to agree</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settingsForm.auto_pause_on_loss}
                onChange={(e) => setSettingsForm(f => ({ ...f, auto_pause_on_loss: e.target.checked }))}
                className="w-4 h-4 rounded border-white/30"
              />
              <span className="text-sm text-slate-300">Pause after a loss</span>
            </label>
          </div>

          {/* Advanced Settings Section */}
          <div className="mt-4 pt-4 border-t border-white/10">
            <button
              onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
              className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-3"
            >
              <Settings className="w-4 h-4" />
              Advanced Settings
              {showAdvancedSettings ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            
            {showAdvancedSettings && (
              <div className="space-y-4 p-3 bg-black/30 rounded-xl border border-white/5">
                {/* Trailing Stop */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">Trailing Stop-Loss</p>
                    <p className="text-[10px] text-slate-500">Automatically raise stop as price increases</p>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settingsForm.auto_trailing_stop_enabled || false}
                      onChange={(e) => setSettingsForm(f => ({ ...f, auto_trailing_stop_enabled: e.target.checked }))}
                      className="w-4 h-4 rounded border-white/30"
                    />
                  </label>
                </div>
                
                {settingsForm.auto_trailing_stop_enabled && (
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">
                      Trail Distance: {settingsForm.auto_trailing_stop_percent || 5}%
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="20"
                      step="0.5"
                      value={settingsForm.auto_trailing_stop_percent || 5}
                      onChange={(e) => setSettingsForm(f => ({ ...f, auto_trailing_stop_percent: parseFloat(e.target.value) }))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>1%</span>
                      <span>20%</span>
                    </div>
                  </div>
                )}
                
                {/* Scale-In (DCA on Dip) */}
                <div className="flex items-center justify-between pt-2 border-t border-white/5">
                  <div>
                    <p className="text-sm text-white">DCA on Dip</p>
                    <p className="text-[10px] text-slate-500">Add to position when price drops</p>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settingsForm.auto_scale_in_enabled || false}
                      onChange={(e) => setSettingsForm(f => ({ ...f, auto_scale_in_enabled: e.target.checked }))}
                      className="w-4 h-4 rounded border-white/30"
                    />
                  </label>
                </div>
                
                {settingsForm.auto_scale_in_enabled && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">
                        Dip Threshold: {settingsForm.auto_scale_in_threshold || 5}%
                      </label>
                      <input
                        type="range"
                        min="2"
                        max="15"
                        step="1"
                        value={settingsForm.auto_scale_in_threshold || 5}
                        onChange={(e) => setSettingsForm(f => ({ ...f, auto_scale_in_threshold: parseFloat(e.target.value) }))}
                        className="w-full"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">
                        Max Adds: {settingsForm.auto_scale_in_max_adds || 2}
                      </label>
                      <input
                        type="range"
                        min="1"
                        max="5"
                        step="1"
                        value={settingsForm.auto_scale_in_max_adds || 2}
                        onChange={(e) => setSettingsForm(f => ({ ...f, auto_scale_in_max_adds: parseInt(e.target.value) }))}
                        className="w-full"
                      />
                    </div>
                  </div>
                )}
                
                {/* Additional Toggles */}
                <div className="pt-2 border-t border-white/5 space-y-2">
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-slate-300">Avoid volatile hours</span>
                    <input
                      type="checkbox"
                      checked={settingsForm.auto_avoid_volatile_hours ?? true}
                      onChange={(e) => setSettingsForm(f => ({ ...f, auto_avoid_volatile_hours: e.target.checked }))}
                      className="w-4 h-4 rounded border-white/30"
                    />
                  </label>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-slate-300">Profit target alerts</span>
                    <input
                      type="checkbox"
                      checked={settingsForm.auto_profit_target_alert ?? true}
                      onChange={(e) => setSettingsForm(f => ({ ...f, auto_profit_target_alert: e.target.checked }))}
                      className="w-4 h-4 rounded border-white/30"
                    />
                  </label>
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-3 pt-2">
            <Button
              onClick={() => setShowSettingsPanel(false)}
              variant="outline"
              className="flex-1 border-white/20"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveSettings}
              className="flex-1 bg-[#D946EF] hover:bg-[#D946EF]/80"
            >
              Save Settings
            </Button>
          </div>
        </div>
      )}

      {/* Activity Log */}
      <div>
        <h4 className="font-bold text-sm text-slate-400 mb-3 flex items-center gap-2">
          <History className="w-4 h-4" />
          Recent Activity
        </h4>
        
        {logs.length === 0 ? (
          <div className="text-center py-8 bg-white/5 rounded-xl border border-dashed border-white/10">
            <Activity className="w-10 h-10 text-slate-600 mx-auto mb-2" />
            <p className="text-slate-500 text-sm">No auto-trade activity yet</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {logs.map((log, i) => (
              <div 
                key={log.log_id || i}
                className={`flex items-center justify-between p-3 rounded-xl border ${
                  log.action === 'auto_buy' ? 'bg-[#00FFA3]/5 border-[#00FFA3]/20' :
                  log.action === 'auto_sell' ? 'bg-[#FF6B6B]/5 border-[#FF6B6B]/20' :
                  'bg-white/5 border-white/10'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    log.action === 'auto_buy' ? 'bg-[#00FFA3]/20' :
                    log.action === 'auto_sell' ? 'bg-[#FF6B6B]/20' :
                    log.action === 'auto_enabled' ? 'bg-[#D946EF]/20' :
                    'bg-slate-700'
                  }`}>
                    {log.action === 'auto_buy' && <TrendingUp className="w-4 h-4 text-[#00FFA3]" />}
                    {log.action === 'auto_sell' && <TrendingDown className="w-4 h-4 text-[#FF6B6B]" />}
                    {log.action === 'auto_enabled' && <Play className="w-4 h-4 text-[#D946EF]" />}
                    {log.action === 'auto_disabled' && <Pause className="w-4 h-4 text-slate-400" />}
                    {log.action === 'auto_skip' && <X className="w-4 h-4 text-slate-400" />}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">
                      {log.action === 'auto_buy' && `AUTO BUY ${log.token_symbol}`}
                      {log.action === 'auto_sell' && `AUTO SELL ${log.token_symbol}`}
                      {log.action === 'auto_enabled' && 'Auto-trading enabled'}
                      {log.action === 'auto_disabled' && 'Auto-trading disabled'}
                      {log.action === 'auto_skip' && `Skipped ${log.token_symbol}`}
                    </p>
                    <p className="text-[10px] text-slate-500 truncate max-w-[200px]">
                      {log.reason}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {log.amount_sol && (
                    <p className="text-sm font-mono text-white">{log.amount_sol?.toFixed(3)} SOL</p>
                  )}
                  <p className="text-[10px] text-slate-500">
                    {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* How It Works */}
      <div className="bg-[#D946EF]/5 rounded-xl p-4 border border-[#D946EF]/20">
        <h4 className="font-bold text-sm text-[#D946EF] mb-2 flex items-center gap-2">
          <Info className="w-4 h-4" />
          How Auto-Trading Works
        </h4>
        <ul className="text-xs text-slate-400 space-y-1">
          <li>• AI continuously scans markets for opportunities based on technical analysis</li>
          <li>• When signals meet your confidence threshold, trades are executed automatically</li>
          <li>• Positions are managed with your configured stop-loss and take-profit levels</li>
          <li>• Daily limits and cooldowns prevent over-trading</li>
          <li>• You can pause or disable auto-trading at any time</li>
        </ul>
      </div>
    </div>
  );
}

function SignalCard({ signal, onReject, onQuickTrade }) {
  const [expanded, setExpanded] = useState(false);
  const [quickTrading, setQuickTrading] = useState(false);
  const [positionSol, setPositionSol] = useState(signal.suggested_position_sol);
  const riskColors = RISK_COLORS[signal.risk_category] || RISK_COLORS.safer;
  
  const handleQuickTrade = async () => {
    setQuickTrading(true);
    // Pass the custom position to the trade function
    await onQuickTrade({ ...signal, suggested_position_sol: positionSol });
    setQuickTrading(false);
  };
  
  return (
    <div className={`bg-white/5 rounded-xl sm:rounded-2xl p-3 sm:p-5 border ${riskColors.border}`} data-testid={`signal-${signal.signal_id}`}>
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex items-center gap-3 sm:gap-4">
          <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl flex items-center justify-center flex-shrink-0 ${
            signal.signal_type === "buy" ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"
          }`}>
            {signal.signal_type === "buy" ? (
              <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFA3]" />
            ) : (
              <TrendingDown className="w-5 h-5 sm:w-6 sm:h-6 text-[#FF6B6B]" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-1 sm:gap-2 flex-wrap">
              <h3 className="text-base sm:text-lg font-bold">
                {signal.signal_type.toUpperCase()} {signal.token_symbol}
              </h3>
              <span className={`px-1.5 sm:px-2 py-0.5 rounded text-[10px] sm:text-xs ${riskColors.bg} ${riskColors.text}`}>
                {signal.risk_category === "safer" ? "SAFER" : "HIGH RISK"}
              </span>
              {signal.token_mint && (
                <a
                  href={`https://dexscreener.com/solana/${signal.token_mint}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded text-[10px] sm:text-xs bg-[#00C2FF]/10 text-[#00C2FF] hover:bg-[#00C2FF]/20 transition-colors"
                  title="View on DexScreener"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span className="hidden sm:inline">Chart</span>
                </a>
              )}
            </div>
            <p className="text-xs sm:text-sm text-slate-400">
              Confidence: <span className="text-white font-medium">{(signal.confidence * 100).toFixed(0)}%</span>
              {" • "}
              Strategy: <span className="text-white">{signal.strategy}</span>
            </p>
          </div>
        </div>
        
        <div className="flex gap-2 justify-end">
          <ShareButton type="signal" data={signal} className="hidden sm:flex" />
          <Button
            onClick={onReject}
            variant="outline"
            size="sm"
            className="border-[#FF6B6B]/30 text-[#FF6B6B] hover:bg-[#FF6B6B]/10 px-2 sm:px-3"
            data-testid={`reject-signal-${signal.signal_id}`}
          >
            <X className="w-4 h-4" />
          </Button>
          <Button
            onClick={handleQuickTrade}
            disabled={quickTrading || positionSol <= 0}
            size="sm"
            className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] text-white hover:opacity-90 text-xs sm:text-sm"
            data-testid={`quick-trade-${signal.signal_id}`}
          >
            {quickTrading ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Zap className="w-4 h-4 mr-1" />
            )}
            <span className="hidden xs:inline">Quick </span>Trade
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4 mt-3 sm:mt-4 text-xs sm:text-sm">
        <div>
          <p className="text-slate-500 text-[10px] sm:text-xs">Entry</p>
          <p className="font-mono">${signal.entry_price < 0.01 ? signal.entry_price.toFixed(8) : signal.entry_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500 text-[10px] sm:text-xs">Stop Loss</p>
          <p className="font-mono text-[#FF6B6B]">${signal.stop_loss_price < 0.01 ? signal.stop_loss_price.toFixed(8) : signal.stop_loss_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500 text-[10px] sm:text-xs">Take Profit</p>
          <p className="font-mono text-[#00FFA3]">${signal.take_profit_price < 0.01 ? signal.take_profit_price.toFixed(8) : signal.take_profit_price.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-slate-500 text-[10px] sm:text-xs mb-1">Position (SOL)</p>
          <div className="flex items-center gap-1">
            <input
              type="number"
              value={positionSol}
              onChange={(e) => setPositionSol(Math.max(0.01, parseFloat(e.target.value) || 0))}
              step="0.01"
              min="0.01"
              max="10"
              className="w-16 sm:w-20 bg-white/10 border border-white/20 rounded px-2 py-1 text-xs sm:text-sm font-mono text-white focus:border-[#00FFA3] focus:outline-none"
              data-testid={`position-input-${signal.signal_id}`}
            />
            <span className="text-slate-500 text-[10px] sm:text-xs">SOL</span>
          </div>
        </div>
      </div>
      
      <div className="flex items-center justify-between mt-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-[10px] sm:text-xs text-slate-500 hover:text-white"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? "Hide" : "Show"} Analysis
        </button>
        <ShareButton type="signal" data={signal} className="sm:hidden" />
      </div>
      
      {expanded && (
        <div className="mt-3 p-2 sm:p-3 bg-black/20 rounded-lg sm:rounded-xl text-xs sm:text-sm">
          <p className="text-slate-400 mb-2">{signal.reasoning}</p>
          <div className="grid grid-cols-3 gap-2 text-[10px] sm:text-xs">
            <div>RSI: <span className="text-white">{signal.technical_indicators?.rsi?.toFixed(1)}</span></div>
            <div>Trend: <span className="text-white">{signal.technical_indicators?.short_trend}</span></div>
            <div>BB Pos: <span className="text-white">{(signal.technical_indicators?.bollinger?.position * 100)?.toFixed(0)}%</span></div>
          </div>
        </div>
      )}
    </div>
  );
}

function PositionCard({ position, onQuickSell, onDelete, onManualClose, onCustodialSell, custodialWallet }) {
  const [showSellInput, setShowSellInput] = useState(false);
  const [sellPercentage, setSellPercentage] = useState(100); // Default to sell 100%
  const [tokenBalance, setTokenBalance] = useState(null);
  const [loadingBalance, setLoadingBalance] = useState(false);
  const [selling, setSelling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [closing, setClosing] = useState(false);
  const [holdTime, setHoldTime] = useState("");
  const pnlColor = position.unrealized_pnl_pct >= 0 ? "#00FFA3" : "#FF6B6B";
  const pnlSol = position.unrealized_pnl_sol || 0;
  const pnlUsd = position.unrealized_pnl_usd || 0;
  const currentValueSol = position.current_value_sol || position.amount_sol || position.input_sol || 0;
  const currentValueUsd = position.current_value_usd || 0;
  
  // Determine if this is a custodial position (auto-trade, synced from chain) or user wallet position
  const isCustodialPosition = position.auto_trade || position.custodial || position.source === 'custodial' || position.synced_from_chain;
  
  // Fetch token balance when sell input is shown
  useEffect(() => {
    const fetchTokenBalance = async () => {
      if (!showSellInput || !position.token_mint) return;
      
      setLoadingBalance(true);
      try {
        const API = process.env.REACT_APP_BACKEND_URL + '/api';
        const walletToCheck = isCustodialPosition ? custodialWallet?.wallet_address : position.wallet_address;
        
        if (walletToCheck) {
          const response = await fetch(
            `${API}/custodial-wallet/token-balance/${walletToCheck}/${position.token_mint}`
          );
          if (response.ok) {
            const data = await response.json();
            setTokenBalance(data);
          }
        }
      } catch (e) {
        console.error("Error fetching token balance:", e);
      }
      setLoadingBalance(false);
    };
    
    fetchTokenBalance();
  }, [showSellInput, position.token_mint, isCustodialPosition, custodialWallet, position.wallet_address]);
  
  // Calculate and update hold time
  useEffect(() => {
    const calculateHoldTime = () => {
      const createdAt = new Date(position.created_at);
      const now = new Date();
      const diffMs = now - createdAt;
      
      const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
      
      if (days > 0) {
        setHoldTime(`${days}d ${hours}h ${minutes}m`);
      } else if (hours > 0) {
        setHoldTime(`${hours}h ${minutes}m ${seconds}s`);
      } else if (minutes > 0) {
        setHoldTime(`${minutes}m ${seconds}s`);
      } else {
        setHoldTime(`${seconds}s`);
      }
    };
    
    calculateHoldTime();
    const interval = setInterval(calculateHoldTime, 1000);
    return () => clearInterval(interval);
  }, [position.created_at]);
  
  const handleQuickSell = async () => {
    if (!tokenBalance || tokenBalance.amount <= 0) {
      toast.error("No tokens to sell");
      return;
    }
    
    const sellTokenAmount = (tokenBalance.raw_amount * sellPercentage) / 100;
    
    setSelling(true);
    try {
      if (isCustodialPosition) {
        // Custodial wallet - execute automatically via backend
        await onCustodialSell(position, sellTokenAmount, sellPercentage);
      } else {
        // User wallet - prompt for approval
        await onQuickSell(position, sellTokenAmount);
      }
    } catch (e) {
      console.error("Sell error:", e);
    }
    setSelling(false);
    setShowSellInput(false);
  };
  
  const handleDelete = async () => {
    // Skip confirmation for ghost positions (executed_on_chain === false)
    const isGhostPosition = position.executed_on_chain === false;
    
    if (!isGhostPosition && !window.confirm(`Remove ${position.token_symbol} position? This won't sell the token, just removes it from tracking.`)) {
      return;
    }
    
    try {
      setDeleting(true);
      await onDelete(position);
    } catch (e) {
      console.error("Delete error:", e);
    } finally {
      setDeleting(false);
    }
  };
  
  const handleManualClose = async () => {
    const confirmMsg = `Mark ${position.token_symbol} as closed?\n\nThis will:\n- Record the current price as exit price\n- Calculate and log your P/L\n- Move the position to history\n\nUse this if you sold the tokens outside the bot.`;
    
    if (!window.confirm(confirmMsg)) return;
    
    try {
      setClosing(true);
      await onManualClose(position);
    } catch (e) {
      console.error("Manual close error:", e);
    } finally {
      setClosing(false);
    }
  };
  
  const isGhostPosition = position.executed_on_chain === false;
  const isPendingExit = position.status?.startsWith('pending_');
  
  return (
    <div className={`bg-white/5 rounded-xl p-4 border ${isGhostPosition ? 'border-amber-500/30 bg-amber-500/5' : isPendingExit ? 'border-purple-500/30 bg-purple-500/5' : 'border-white/10'}`} data-testid={`position-${position.token_symbol}`}>
      {/* Ghost Position Warning */}
      {isGhostPosition && (
        <div className="flex items-center gap-2 mb-3 pb-3 border-b border-amber-500/20">
          <AlertCircle className="w-4 h-4 text-amber-400" />
          <span className="text-xs text-amber-400">Ghost Position - Not executed on-chain</span>
        </div>
      )}
      
      {/* Pending Exit Warning */}
      {isPendingExit && !isGhostPosition && (
        <div className="flex items-center justify-between gap-2 mb-3 pb-3 border-b border-purple-500/20">
          <div className="flex items-center gap-2">
            <Timer className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-purple-400">
              {position.status === 'pending_take_profit' ? 'Take-Profit Triggered' : 'Stop-Loss Triggered'} - Sell pending
            </span>
          </div>
          <Button
            onClick={handleManualClose}
            disabled={closing}
            size="sm"
            className="bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 text-xs"
            data-testid={`manual-close-${position.token_symbol}`}
          >
            {closing ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <CheckCircle className="w-3 h-3 mr-1" />}
            Mark as Sold
          </Button>
        </div>
      )}
      
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
            <p className="text-xs text-slate-500">{(position.amount_sol || position.input_sol)?.toFixed(4)} SOL invested</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {/* P/L Display */}
          <div className="text-right">
            {position.current_price ? (
              <>
                <p className="font-mono font-bold text-lg" style={{ color: pnlColor }}>
                  {position.unrealized_pnl_pct >= 0 ? "+" : ""}{(position.unrealized_pnl_pct || 0).toFixed(2)}%
                </p>
                <div className="flex items-center gap-2 text-xs">
                  <span style={{ color: pnlColor }} className="font-mono">
                    {pnlSol >= 0 ? "+" : ""}{pnlSol.toFixed(4)} SOL
                  </span>
                  <span className="text-slate-500">|</span>
                  <span style={{ color: pnlColor }} className="font-mono">
                    {pnlUsd >= 0 ? "+" : ""}${Math.abs(pnlUsd).toFixed(2)}
                  </span>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500">Price unavailable</p>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setShowSellInput(!showSellInput)}
              size="sm"
              className="bg-[#FF6B6B]/20 text-[#FF6B6B] hover:bg-[#FF6B6B]/30"
              data-testid={`sell-btn-${position.token_symbol}`}
            >
              <TrendingDown className="w-4 h-4 mr-1" />
              Sell
            </Button>
            {/* Manual Close - for tokens sold outside the bot */}
            {!isPendingExit && (
              <Button
                onClick={handleManualClose}
                disabled={closing}
                size="sm"
                variant="outline"
                className="border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
                title="Mark as closed (for tokens sold outside the bot)"
                data-testid={`close-btn-${position.token_symbol}`}
              >
                {closing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              </Button>
            )}
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-[#FF6B6B] transition-colors"
              title="Remove position (won't sell)"
              data-testid={`delete-btn-${position.token_symbol}`}
            >
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
      
      {/* Position Details Row */}
      <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-3 gap-4 text-xs">
        <div>
          <p className="text-slate-500">Entry Price</p>
          <p className="font-mono text-white">
            {position.entry_price 
              ? `$${position.entry_price < 0.01 ? position.entry_price?.toFixed(8) : position.entry_price?.toFixed(6)}`
              : "N/A"
            }
          </p>
        </div>
        <div>
          <p className="text-slate-500">Current Price</p>
          <p className="font-mono text-white">
            {position.current_price 
              ? `$${position.current_price < 0.01 ? position.current_price?.toFixed(8) : position.current_price?.toFixed(6)}`
              : <span className="text-slate-500">Loading...</span>
            }
          </p>
        </div>
        <div>
          <p className="text-slate-500">Current Value</p>
          <p className="font-mono text-[#00C2FF]">
            {currentValueSol.toFixed(4)} SOL <span className="text-slate-500">(${currentValueUsd.toFixed(2)})</span>
          </p>
        </div>
      </div>
      
      {/* Hold Time Display */}
      <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          <Timer className="w-4 h-4 text-[#D946EF]" />
          <span className="text-slate-400">Holding for:</span>
          <span className="font-mono text-[#D946EF] font-medium">{holdTime}</span>
        </div>
        {position.token_mint && (
          <a
            href={`https://dexscreener.com/solana/${position.token_mint}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-[#00C2FF] hover:underline"
          >
            <ExternalLink className="w-3 h-3" />
            DexScreener
          </a>
        )}
      </div>
      
      {/* Quick Sell Input */}
      {showSellInput && (
        <div className="mt-3 pt-3 border-t border-white/10 space-y-3">
          {/* Token Balance Display */}
          <div className="flex items-center justify-between bg-white/5 rounded-lg p-3">
            <div>
              <p className="text-xs text-slate-500">Your {position.token_symbol} Holdings</p>
              {loadingBalance ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                  <span className="text-sm text-slate-400">Loading...</span>
                </div>
              ) : tokenBalance ? (
                <p className="font-mono text-lg text-white">
                  {tokenBalance.amount?.toLocaleString(undefined, { maximumFractionDigits: 4 })} <span className="text-sm text-slate-400">{position.token_symbol}</span>
                </p>
              ) : (
                <p className="text-sm text-[#FF6B6B]">No tokens found</p>
              )}
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Location</p>
              <p className={`text-sm font-medium ${isCustodialPosition ? 'text-[#D946EF]' : 'text-[#00C2FF]'}`}>
                {isCustodialPosition ? 'Auto-Trade Wallet' : 'Your Wallet'}
              </p>
            </div>
          </div>
          
          {/* Sell Amount Controls */}
          <div>
            <label className="text-xs text-slate-500 mb-2 block">
              Sell Amount ({sellPercentage}% = {tokenBalance ? ((tokenBalance.amount * sellPercentage) / 100).toFixed(4) : '0'} {position.token_symbol})
            </label>
            
            {/* Percentage Buttons */}
            <div className="flex gap-2 mb-3">
              {[25, 50, 75, 100].map(pct => (
                <button
                  key={pct}
                  onClick={() => setSellPercentage(pct)}
                  className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-colors ${
                    sellPercentage === pct 
                      ? 'bg-[#FF6B6B] text-white' 
                      : 'bg-white/10 text-slate-400 hover:bg-white/20'
                  }`}
                >
                  {pct}%
                </button>
              ))}
            </div>
            
            {/* Custom Slider */}
            <input
              type="range"
              value={sellPercentage}
              onChange={(e) => setSellPercentage(parseInt(e.target.value))}
              min="1"
              max="100"
              className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer accent-[#FF6B6B]"
            />
          </div>
          
          {/* Sell Button */}
          <Button
            onClick={handleQuickSell}
            disabled={selling || !tokenBalance || tokenBalance.amount <= 0}
            className="w-full bg-gradient-to-r from-[#FF6B6B] to-[#FF8C00] text-white hover:opacity-90"
          >
            {selling ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Zap className="w-4 h-4 mr-2" />
            )}
            {selling 
              ? "Processing..." 
              : isCustodialPosition 
                ? `Sell ${sellPercentage}% (Auto-Execute)` 
                : `Sell ${sellPercentage}% (Wallet Approval)`
            }
          </Button>
          
          {!isCustodialPosition && (
            <p className="text-[10px] text-slate-500 text-center">
              You will be prompted to approve this transaction in your wallet
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function TradeHistoryCard({ trade }) {
  const isProfitable = (trade.pnl_sol || trade.pnl_percent || 0) > 0;
  const isSell = trade.trade_type === "sell" || trade.action?.includes("sell") || trade.action?.includes("close") || trade.action?.includes("take_profit") || trade.action?.includes("stop_loss");
  const pnlSol = trade.pnl_sol || trade.realized_pnl_sol || 0;
  const pnlPct = trade.pnl_pct || trade.pnl_percent || trade.realized_pnl_pct || 0;
  const inputSol = trade.input_sol || trade.amount_sol || 0;
  const receivedSol = trade.received_sol || trade.output_amount || 0;
  const entryPrice = trade.entry_price || 0;
  const exitPrice = trade.exit_price || trade.current_price || 0;
  
  // Calculate time held
  const getTimeHeld = () => {
    if (!trade.created_at) return null;
    const closeTime = trade.closed_at || trade.executed_at;
    if (!closeTime && !isSell) return null;
    
    const start = new Date(trade.created_at);
    const end = closeTime ? new Date(closeTime) : new Date();
    const diffMs = end - start;
    
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };
  
  const timeHeld = getTimeHeld();
  const tradeSource = trade.source || (trade.action?.includes("auto") ? "Auto-Trade" : "Manual");
  
  // Determine border color based on profit/loss
  const borderColor = isSell 
    ? (isProfitable ? "border-[#00FFA3]/30" : "border-[#FF6B6B]/30")
    : "border-white/10";
  const bgTint = isSell
    ? (isProfitable ? "bg-[#00FFA3]/5" : "bg-[#FF6B6B]/5")
    : "bg-white/5";
  
  return (
    <div className={`${bgTint} rounded-xl p-4 border ${borderColor}`} data-testid={`trade-history-${trade.execution_id || trade.log_id}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            isSell 
              ? (isProfitable ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20")
              : "bg-[#00C2FF]/20"
          }`}>
            {isSell ? (
              isProfitable ? <TrendingUp className="w-5 h-5 text-[#00FFA3]" /> : <TrendingDown className="w-5 h-5 text-[#FF6B6B]" />
            ) : (
              <ArrowRight className="w-5 h-5 text-[#00C2FF]" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-bold">{trade.token_symbol}</p>
              <span className={`px-2 py-0.5 text-[10px] rounded-full font-semibold ${
                isSell 
                  ? (isProfitable ? "bg-[#00FFA3]/20 text-[#00FFA3]" : "bg-[#FF6B6B]/20 text-[#FF6B6B]") 
                  : "bg-[#00C2FF]/20 text-[#00C2FF]"
              }`}>
                {isSell ? (trade.action?.includes("take_profit") ? "TAKE PROFIT" : trade.action?.includes("stop_loss") ? "STOP LOSS" : "SOLD") : "BUY"}
              </span>
              <span className="px-2 py-0.5 text-[10px] rounded-full bg-white/10 text-slate-400">
                {tradeSource}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              {new Date(trade.executed_at || trade.created_at).toLocaleString()}
            </p>
          </div>
        </div>
        
        {isSell && (
          <div className="text-right">
            <p className={`font-mono font-bold text-lg ${isProfitable ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>
              {isProfitable ? "+" : ""}{pnlPct.toFixed(2)}%
            </p>
            <p className={`text-sm font-mono ${isProfitable ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>
              {isProfitable ? "+" : ""}{pnlSol.toFixed(4)} SOL
            </p>
          </div>
        )}
      </div>
      
      {/* Trade details */}
      <div className="grid grid-cols-4 gap-3 text-xs pt-3 border-t border-white/5">
        <div>
          <p className="text-slate-500">{isSell ? "Sold" : "Invested"}</p>
          <p className="font-mono text-white">{inputSol.toFixed(4)} SOL</p>
        </div>
        {entryPrice > 0 && (
          <div>
            <p className="text-slate-500">Entry Price</p>
            <p className="font-mono text-white">${entryPrice < 0.01 ? entryPrice.toFixed(8) : entryPrice.toFixed(6)}</p>
          </div>
        )}
        {isSell && exitPrice > 0 && (
          <div>
            <p className="text-slate-500">Exit Price</p>
            <p className={`font-mono ${isProfitable ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>
              ${exitPrice < 0.01 ? exitPrice.toFixed(8) : exitPrice.toFixed(6)}
            </p>
          </div>
        )}
        {timeHeld && (
          <div>
            <p className="text-slate-500">Time Held</p>
            <p className="font-mono text-[#D946EF]">{timeHeld}</p>
          </div>
        )}
      </div>
      
      {/* Transaction link */}
      {(trade.tx_signature || trade.sell_tx_signature) && (
        <a 
          href={`https://solscan.io/tx/${trade.sell_tx_signature || trade.tx_signature}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 pt-3 border-t border-white/5 flex items-center gap-1 text-xs text-[#00C2FF] hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          View on Solscan
        </a>
      )}
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
              min="0.01"
              max="1"
              step="0.01"
              value={form.max_position_sol}
              onChange={(e) => setForm({ ...form, max_position_sol: parseFloat(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-slate-500">
              <span>0.01 SOL</span>
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

// TopPickCard - Display coin from Top Picks with copy CA and trade link
function TopPickCard({ coin, index, type, onCopy, onAnalyze, onQuickBuy }) {
  const [showBuyInput, setShowBuyInput] = useState(false);
  const [buyAmount, setBuyAmount] = useState(0.1);
  const [buying, setBuying] = useState(false);
  
  const colors = {
    safe: { bg: "bg-[#00FFA3]/5", border: "border-[#00FFA3]/20", text: "text-[#00FFA3]", hover: "hover:bg-[#00FFA3]/10" },
    volatile: { bg: "bg-[#FF6B6B]/5", border: "border-[#FF6B6B]/20", text: "text-[#FF6B6B]", hover: "hover:bg-[#FF6B6B]/10" },
    new: { bg: "bg-[#F5D300]/5", border: "border-[#F5D300]/20", text: "text-[#F5D300]", hover: "hover:bg-[#F5D300]/10" }
  };
  
  const c = colors[type] || colors.safe;
  
  // Determine HOT and TRENDING status
  const isHot = coin.volume_24h && coin.volume_24h > 100000; // >$100K volume = HOT
  const isTrending = coin.change_24h && coin.change_24h > 50; // >50% gain = TRENDING
  
  const truncateAddress = (address) => {
    if (!address) return "";
    if (address.length <= 12) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  const handleQuickBuy = async () => {
    if (buyAmount <= 0) return;
    setBuying(true);
    await onQuickBuy(coin, buyAmount);
    setBuying(false);
    setShowBuyInput(false);
  };

  return (
    <div 
      className={`p-3 rounded-xl border transition-colors ${c.bg} ${c.border} ${c.hover}`}
      data-testid={`top-pick-${coin.symbol}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold ${
            type === "safe" 
              ? 'bg-gradient-to-br from-[#00FFA3] to-[#00C2FF] text-black'
              : type === "volatile"
                ? 'bg-gradient-to-br from-[#FF6B6B] to-[#FF8C00] text-white'
                : 'bg-gradient-to-br from-[#F5D300] to-[#FF8C00] text-black'
          }`}>
            {type === "new" ? "🚀" : index + 1}
          </div>
          <div>
            <div className="flex items-center gap-1 flex-wrap">
              <p className="font-medium text-white text-sm">{coin.symbol}</p>
              {coin.is_bonded && (
                <span className="px-1.5 py-0.5 text-[8px] bg-[#00FFA3]/20 text-[#00FFA3] rounded font-bold">
                  BONDED
                </span>
              )}
              {isHot && (
                <span className="px-1.5 py-0.5 text-[8px] bg-[#FF6B6B]/30 text-[#FF6B6B] rounded font-bold animate-pulse">
                  🔥 HOT
                </span>
              )}
              {isTrending && (
                <span className="px-1.5 py-0.5 text-[8px] bg-[#00FFA3]/30 text-[#00FFA3] rounded font-bold">
                  📈 TRENDING
                </span>
              )}
            </div>
            <p className="text-[10px] text-slate-500">{coin.platform || "Solana"}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-sm text-white">
            ${coin.price < 0.001 ? coin.price?.toFixed(6) : coin.price?.toFixed(4)}
          </p>
          <p className={`text-[10px] ${coin.change_24h >= 0 ? 'text-[#00FFA3]' : 'text-red-400'}`}>
            {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Contract Address & Actions */}
      <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between flex-wrap gap-2">
        {coin.contract_address ? (
          <button 
            onClick={() => onCopy(coin.contract_address, "Contract")}
            className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition-colors group"
            title="Click to copy contract address"
          >
            <Copy className="w-3 h-3" />
            <span className="font-mono">{truncateAddress(coin.contract_address)}</span>
          </button>
        ) : (
          <span className="text-[10px] text-slate-600">-</span>
        )}
        <div className="flex items-center gap-2">
          <button
            onClick={onAnalyze}
            className={`flex items-center gap-1 text-[10px] ${c.text} hover:text-white transition-colors`}
            title="Generate trading signal"
          >
            <Zap className="w-3 h-3" />
            Analyze
          </button>
          <button
            onClick={() => setShowBuyInput(!showBuyInput)}
            className="flex items-center gap-1 text-[10px] bg-[#00FFA3]/20 text-[#00FFA3] px-2 py-1 rounded hover:bg-[#00FFA3]/30 transition-colors"
            title="Quick buy this token"
          >
            <DollarSign className="w-3 h-3" />
            Buy
          </button>
          {coin.dex_url ? (
            <a 
              href={coin.dex_url}
              target="_blank"
              rel="noopener noreferrer"
              className={`flex items-center gap-1 text-[10px] ${c.text} hover:text-white transition-colors`}
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          ) : null}
        </div>
      </div>

      {/* Quick Buy Input */}
      {showBuyInput && (
        <div className="mt-2 pt-2 border-t border-white/5 flex items-center gap-2">
          <input
            type="number"
            value={buyAmount}
            onChange={(e) => setBuyAmount(Math.max(0.01, parseFloat(e.target.value) || 0))}
            step="0.01"
            min="0.01"
            max="10"
            className="flex-1 bg-white/10 border border-white/20 rounded px-2 py-1 text-sm font-mono text-white focus:border-[#00FFA3] focus:outline-none"
            placeholder="SOL amount"
          />
          <Button
            onClick={handleQuickBuy}
            disabled={buying || buyAmount <= 0}
            size="sm"
            className="bg-gradient-to-r from-[#00FFA3] to-[#00C2FF] text-black hover:opacity-90"
          >
            {buying ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3 mr-1" />}
            {buying ? "" : "Buy"}
          </Button>
        </div>
      )}

      {coin.reason && (
        <p className="mt-2 text-[10px] text-slate-400 line-clamp-2">{coin.reason}</p>
      )}
    </div>
  );
}


// AlertCard Component with DexScreener link, Watchlist star, and Quick Buy
function AlertCard({ alert, onDelete, walletAddress, onQuickBuy }) {
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [addingToWatchlist, setAddingToWatchlist] = useState(false);
  const [showQuickBuy, setShowQuickBuy] = useState(false);
  const [buyAmount, setBuyAmount] = useState(0.1);
  const [buying, setBuying] = useState(false);
  
  // Check if already in watchlist on mount
  useEffect(() => {
    const checkWatchlist = async () => {
      if (!walletAddress) return;
      try {
        const response = await axios.get(`${API}/watchlist/${walletAddress}`);
        const coins = response.data.coins || [];
        setIsInWatchlist(coins.some(c => c.symbol?.toUpperCase() === alert.symbol?.toUpperCase()));
      } catch (err) {
        console.error("Check watchlist error:", err);
      }
    };
    checkWatchlist();
  }, [walletAddress, alert.symbol]);
  
  // Add to watchlist
  const addToWatchlist = async () => {
    if (!walletAddress || addingToWatchlist) return;
    setAddingToWatchlist(true);
    try {
      await axios.post(`${API}/watchlist/add`, {
        wallet_address: walletAddress,
        symbol: alert.symbol,
        contract_address: alert.token_mint || ""
      });
      setIsInWatchlist(true);
      toast.success(`${alert.symbol} added to watchlist!`);
    } catch (err) {
      toast.error("Failed to add to watchlist");
    }
    setAddingToWatchlist(false);
  };
  
  // Remove from watchlist
  const removeFromWatchlist = async () => {
    if (!walletAddress) return;
    try {
      await axios.delete(`${API}/watchlist/remove`, {
        data: { wallet_address: walletAddress, symbol: alert.symbol }
      });
      setIsInWatchlist(false);
      toast.success(`${alert.symbol} removed from watchlist`);
    } catch (err) {
      toast.error("Failed to remove from watchlist");
    }
  };
  
  // Handle quick buy
  const handleQuickBuy = async () => {
    if (buyAmount <= 0 || buying) return;
    setBuying(true);
    
    // Fetch current price for the token
    let currentPrice = 0;
    try {
      if (alert.token_mint) {
        const response = await axios.get(
          `https://api.dexscreener.com/latest/dex/tokens/${alert.token_mint}`
        );
        const pairs = response.data?.pairs || [];
        if (pairs.length > 0) {
          const bestPair = pairs.reduce((a, b) => 
            (parseFloat(a.liquidity?.usd || 0) > parseFloat(b.liquidity?.usd || 0) ? a : b)
          );
          currentPrice = parseFloat(bestPair.priceUsd || 0);
        }
      }
    } catch (err) {
      console.error("Price fetch error:", err);
    }
    
    // Create a coin object for the buy function
    const coinData = {
      symbol: alert.symbol,
      contract_address: alert.token_mint,
      token_mint: alert.token_mint,
      price: currentPrice
    };
    
    await onQuickBuy(coinData, buyAmount);
    setBuying(false);
    setShowQuickBuy(false);
  };
  
  // DexScreener URL
  const dexScreenerUrl = alert.token_mint 
    ? `https://dexscreener.com/solana/${alert.token_mint}`
    : `https://dexscreener.com/solana?q=${alert.symbol}`;
  
  return (
    <div 
      className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10 hover:border-white/20 transition-colors"
      data-testid={`alert-${alert.alert_id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${
            alert.alert_type.includes("up") ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"
          }`}>
            {alert.alert_type.includes("up") ? (
              <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-[#00FFA3]" />
            ) : (
              <TrendingDown className="w-5 h-5 sm:w-6 sm:h-6 text-[#FF6B6B]" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-bold text-white text-sm sm:text-base">{alert.symbol}</p>
              <span className={`px-1.5 py-0.5 text-[10px] rounded ${
                alert.alert_type.includes("up") 
                  ? "bg-[#00FFA3]/20 text-[#00FFA3]" 
                  : "bg-[#FF6B6B]/20 text-[#FF6B6B]"
              }`}>
                {alert.alert_type === "breakout_up" && "BREAKOUT"}
                {alert.alert_type === "breakout_down" && "BREAKDOWN"}
                {alert.alert_type === "price_above" && "TARGET UP"}
                {alert.alert_type === "price_below" && "TARGET DOWN"}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              {alert.alert_type.includes("price") && alert.target_price 
                ? `Target: $${alert.target_price.toFixed(6)}`
                : "Momentum-based alert"
              }
            </p>
            {alert.scan_reason && (
              <p className="text-[10px] text-[#F5D300] mt-0.5">{alert.scan_reason}</p>
            )}
          </div>
        </div>
        
        {/* Action Buttons */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {/* DexScreener Link */}
          <a
            href={dexScreenerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg bg-[#00C2FF]/10 text-[#00C2FF] hover:bg-[#00C2FF]/20 transition-colors"
            title="View on DexScreener"
            data-testid={`alert-dexscreener-${alert.alert_id}`}
          >
            <ExternalLink className="w-4 h-4" />
          </a>
          
          {/* Watchlist Star */}
          <button
            onClick={isInWatchlist ? removeFromWatchlist : addToWatchlist}
            disabled={addingToWatchlist}
            className={`p-2 rounded-lg transition-colors ${
              isInWatchlist 
                ? "bg-[#F5D300]/20 text-[#F5D300]" 
                : "bg-white/5 text-slate-400 hover:text-[#F5D300] hover:bg-[#F5D300]/10"
            }`}
            title={isInWatchlist ? "Remove from watchlist" : "Add to watchlist"}
            data-testid={`alert-watchlist-${alert.alert_id}`}
          >
            {addingToWatchlist ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Star className={`w-4 h-4 ${isInWatchlist ? "fill-[#F5D300]" : ""}`} />
            )}
          </button>
          
          {/* Quick Buy Button */}
          <button
            onClick={() => setShowQuickBuy(!showQuickBuy)}
            className="p-2 rounded-lg bg-[#00FFA3]/10 text-[#00FFA3] hover:bg-[#00FFA3]/20 transition-colors"
            title="Quick Buy"
            data-testid={`alert-quickbuy-${alert.alert_id}`}
          >
            <DollarSign className="w-4 h-4" />
          </button>
          
          {/* Delete Button */}
          <button
            onClick={() => onDelete(alert.alert_id)}
            className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-[#FF6B6B] hover:bg-[#FF6B6B]/10 transition-colors"
            title="Delete alert"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Quick Buy Panel */}
      {showQuickBuy && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-400">Quick Buy:</span>
            <div className="flex items-center gap-2 flex-1">
              <input
                type="number"
                value={buyAmount}
                onChange={(e) => setBuyAmount(Math.max(0.01, parseFloat(e.target.value) || 0))}
                step="0.01"
                min="0.01"
                max="10"
                className="w-20 bg-white/10 border border-white/20 rounded px-2 py-1.5 text-sm font-mono text-white focus:border-[#00FFA3] focus:outline-none"
                placeholder="SOL"
              />
              <span className="text-xs text-slate-500">SOL</span>
              <Button
                onClick={handleQuickBuy}
                disabled={buying || buyAmount <= 0 || !alert.token_mint}
                size="sm"
                className="bg-gradient-to-r from-[#00FFA3] to-[#00C2FF] text-black hover:opacity-90"
              >
                {buying ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Zap className="w-4 h-4 mr-1" />
                    Buy {alert.symbol}
                  </>
                )}
              </Button>
            </div>
          </div>
          {!alert.token_mint && (
            <p className="text-[10px] text-[#FF6B6B] mt-1">Token address not available for quick buy</p>
          )}
        </div>
      )}
      
      {/* Created Date */}
      <div className="mt-2 text-[10px] text-slate-600">
        Created: {new Date(alert.created_at).toLocaleString()}
      </div>
    </div>
  );
}
