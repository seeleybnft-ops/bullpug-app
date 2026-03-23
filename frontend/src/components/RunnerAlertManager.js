/**
 * RunnerAlertManager Component
 * 
 * Manages real-time runner token alerts via Telegram and Push notifications.
 * Users can:
 * - Enable/disable runner alerts
 * - Configure alert thresholds (score, price change, volume)
 * - Choose notification channels (Telegram, Push)
 * - Test alerts
 * - View alert history
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Bell, BellRing, Rocket, Zap, Activity, TrendingUp, BarChart3,
  Loader2, Settings, Send, AlertCircle, ChevronDown, ChevronUp,
  History, Check, X, Volume2, Clock
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Alert category descriptions
const ALERT_CATEGORIES = {
  high_momentum: {
    label: "High Momentum",
    description: "Strong 1h price movement (>20%)",
    icon: TrendingUp,
    color: "#00FFA3"
  },
  new_runner: {
    label: "New Runner",
    description: "Fresh token (<24h) with momentum",
    icon: Rocket,
    color: "#D946EF"
  },
  breakout: {
    label: "Breakout",
    description: "Multiple bullish factors aligned",
    icon: Zap,
    color: "#FFD700"
  },
  volume_surge: {
    label: "Volume Surge",
    description: "Unusual volume activity",
    icon: BarChart3,
    color: "#00C2FF"
  }
};

export default function RunnerAlertManager({ compact = false }) {
  const { publicKey, connected } = useWallet();
  const walletAddress = publicKey?.toBase58();

  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(!compact);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [preferences, setPreferences] = useState({
    enabled: false,
    telegram_enabled: true,
    push_enabled: true,
    min_runner_score: 50,
    min_price_change_1h: 10,
    min_volume_24h: 100000,
    alert_categories: ["high_momentum", "new_runner", "breakout"]
  });
  const [alertHistory, setAlertHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [telegramLinked, setTelegramLinked] = useState(false);

  // Fetch preferences
  const fetchPreferences = useCallback(async () => {
    if (!walletAddress) return;
    
    try {
      const { data } = await axios.get(`${API}/runner-alerts/preferences/${walletAddress}`);
      setPreferences(data);
    } catch (e) {
      console.error('Failed to fetch runner alert preferences:', e);
    }
    setLoading(false);
  }, [walletAddress]);

  // Check Telegram status
  const checkTelegramStatus = useCallback(async () => {
    if (!walletAddress) return;
    
    try {
      const { data } = await axios.get(`${API}/telegram/status/${walletAddress}`);
      setTelegramLinked(data.linked);
    } catch (e) {
      console.error('Failed to check Telegram status:', e);
    }
  }, [walletAddress]);

  // Fetch alert history
  const fetchAlertHistory = useCallback(async () => {
    if (!walletAddress) return;
    
    try {
      const { data } = await axios.get(`${API}/runner-alerts/history/${walletAddress}?limit=10`);
      setAlertHistory(data.alerts || []);
    } catch (e) {
      console.error('Failed to fetch alert history:', e);
    }
  }, [walletAddress]);

  // Initial load
  useEffect(() => {
    if (walletAddress) {
      fetchPreferences();
      checkTelegramStatus();
      fetchAlertHistory();
    }
  }, [walletAddress, fetchPreferences, checkTelegramStatus, fetchAlertHistory]);

  // Save preferences
  const savePreferences = async (updates) => {
    if (!walletAddress) return;
    setSaving(true);
    
    try {
      const { data } = await axios.put(
        `${API}/runner-alerts/preferences/${walletAddress}`,
        updates
      );
      setPreferences(data);
      toast.success("Runner alert settings saved");
    } catch (e) {
      toast.error("Failed to save settings");
    }
    setSaving(false);
  };

  // Toggle alerts
  const toggleAlerts = async (enabled) => {
    await savePreferences({ enabled });
  };

  // Toggle category
  const toggleCategory = async (category) => {
    const current = preferences.alert_categories || [];
    const updated = current.includes(category)
      ? current.filter(c => c !== category)
      : [...current, category];
    await savePreferences({ alert_categories: updated });
  };

  // Send test alert
  const sendTestAlert = async () => {
    if (!walletAddress) return;
    setTesting(true);
    
    try {
      const { data } = await axios.post(`${API}/runner-alerts/test/${walletAddress}`);
      if (data.success) {
        toast.success("Test alert sent! Check Telegram/Push notifications.");
      } else {
        toast.warning(data.message || "Alert may not have been delivered. Check your notification setup.");
      }
      fetchAlertHistory();
    } catch (e) {
      toast.error("Failed to send test alert");
    }
    setTesting(false);
  };

  if (!connected) {
    return null;
  }

  if (loading) {
    return (
      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-[#D946EF]" />
        </div>
      </div>
    );
  }

  // Compact view
  if (compact && !expanded) {
    return (
      <div 
        className="bg-gradient-to-r from-[#D946EF]/10 to-[#00FFA3]/10 rounded-xl p-4 border border-[#D946EF]/30 cursor-pointer hover:border-[#D946EF]/50 transition-colors"
        onClick={() => setExpanded(true)}
        data-testid="runner-alerts-compact"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${preferences.enabled ? 'bg-[#D946EF]/30' : 'bg-white/10'}`}>
              <Rocket className={`w-5 h-5 ${preferences.enabled ? 'text-[#D946EF]' : 'text-slate-400'}`} />
            </div>
            <div>
              <h4 className="font-bold text-white flex items-center gap-2">
                Runner Alerts
                {preferences.enabled && (
                  <Badge className="bg-[#00FFA3]/20 text-[#00FFA3] text-[10px]">ACTIVE</Badge>
                )}
              </h4>
              <p className="text-xs text-slate-400">
                {preferences.enabled 
                  ? `Telegram: ${preferences.telegram_enabled ? 'On' : 'Off'} • Push: ${preferences.push_enabled ? 'On' : 'Off'}`
                  : "Get alerts when new runners are detected"
                }
              </p>
            </div>
          </div>
          <ChevronDown className="w-5 h-5 text-slate-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-[#D946EF]/10 to-[#00FFA3]/10 rounded-xl border border-[#D946EF]/30" data-testid="runner-alerts-manager">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${preferences.enabled ? 'bg-[#D946EF]/30' : 'bg-white/10'}`}>
              <Rocket className={`w-5 h-5 ${preferences.enabled ? 'text-[#D946EF]' : 'text-slate-400'}`} />
            </div>
            <div>
              <h4 className="font-bold text-white flex items-center gap-2">
                Runner Token Alerts
                {preferences.enabled && (
                  <Badge className="bg-[#00FFA3]/20 text-[#00FFA3] text-[10px]">ACTIVE</Badge>
                )}
              </h4>
              <p className="text-xs text-slate-400">
                Real-time alerts for high-potential runner tokens
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={preferences.enabled}
              onCheckedChange={toggleAlerts}
              disabled={saving}
              data-testid="toggle-runner-alerts"
            />
            {compact && (
              <button 
                onClick={() => setExpanded(false)}
                className="p-1 hover:bg-white/10 rounded"
              >
                <ChevronUp className="w-5 h-5 text-slate-400" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Settings */}
      {preferences.enabled && (
        <div className="p-4 space-y-4">
          {/* Notification Channels */}
          <div>
            <h5 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Bell className="w-4 h-4 text-[#D946EF]" />
              Notification Channels
            </h5>
            <div className="space-y-2">
              {/* Telegram */}
              <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                <div className="flex items-center gap-3">
                  <svg className="w-5 h-5 text-[#0088CC]" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                  </svg>
                  <div>
                    <p className="text-sm text-white">Telegram</p>
                    <p className="text-[10px] text-slate-500">
                      {telegramLinked ? "Connected" : "Not linked - Link in Alerts tab"}
                    </p>
                  </div>
                </div>
                <Switch
                  checked={preferences.telegram_enabled && telegramLinked}
                  onCheckedChange={(checked) => savePreferences({ telegram_enabled: checked })}
                  disabled={saving || !telegramLinked}
                />
              </div>

              {/* Push */}
              <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                <div className="flex items-center gap-3">
                  <BellRing className="w-5 h-5 text-[#D946EF]" />
                  <div>
                    <p className="text-sm text-white">Push Notifications</p>
                    <p className="text-[10px] text-slate-500">Browser notifications</p>
                  </div>
                </div>
                <Switch
                  checked={preferences.push_enabled}
                  onCheckedChange={(checked) => savePreferences({ push_enabled: checked })}
                  disabled={saving}
                />
              </div>
            </div>
          </div>

          {/* Alert Thresholds */}
          <div>
            <h5 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Settings className="w-4 h-4 text-[#D946EF]" />
              Alert Thresholds
            </h5>
            <div className="space-y-4 p-3 bg-white/5 rounded-lg">
              {/* Runner Score */}
              <div>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-slate-400">Min Runner Score</span>
                  <span className="text-[#00FFA3] font-bold">{preferences.min_runner_score}/100</span>
                </div>
                <Slider
                  value={[preferences.min_runner_score]}
                  onValueChange={([value]) => setPreferences(p => ({ ...p, min_runner_score: value }))}
                  onValueCommit={([value]) => savePreferences({ min_runner_score: value })}
                  min={30}
                  max={90}
                  step={5}
                  className="cursor-pointer"
                />
                <p className="text-[10px] text-slate-500 mt-1">Higher = fewer but higher quality alerts</p>
              </div>

              {/* Price Change */}
              <div>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-slate-400">Min 1H Price Change</span>
                  <span className="text-[#00FFA3] font-bold">{preferences.min_price_change_1h}%</span>
                </div>
                <Slider
                  value={[preferences.min_price_change_1h]}
                  onValueChange={([value]) => setPreferences(p => ({ ...p, min_price_change_1h: value }))}
                  onValueCommit={([value]) => savePreferences({ min_price_change_1h: value })}
                  min={5}
                  max={50}
                  step={5}
                  className="cursor-pointer"
                />
              </div>

              {/* Volume */}
              <div>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-slate-400">Min 24H Volume</span>
                  <span className="text-[#00FFA3] font-bold">${(preferences.min_volume_24h / 1000).toFixed(0)}K</span>
                </div>
                <Slider
                  value={[preferences.min_volume_24h / 10000]}
                  onValueChange={([value]) => setPreferences(p => ({ ...p, min_volume_24h: value * 10000 }))}
                  onValueCommit={([value]) => savePreferences({ min_volume_24h: value * 10000 })}
                  min={1}
                  max={100}
                  step={1}
                  className="cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Alert Categories */}
          <div>
            <h5 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#D946EF]" />
              Alert Categories
            </h5>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(ALERT_CATEGORIES).map(([key, cat]) => {
                const isEnabled = preferences.alert_categories?.includes(key);
                const Icon = cat.icon;
                return (
                  <button
                    key={key}
                    onClick={() => toggleCategory(key)}
                    disabled={saving}
                    className={`p-3 rounded-lg border transition-all ${
                      isEnabled 
                        ? 'bg-white/10 border-white/20' 
                        : 'bg-white/5 border-transparent hover:border-white/10'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className="w-4 h-4" style={{ color: isEnabled ? cat.color : '#64748b' }} />
                      <span className={`text-xs font-medium ${isEnabled ? 'text-white' : 'text-slate-400'}`}>
                        {cat.label}
                      </span>
                      {isEnabled && <Check className="w-3 h-3 text-[#00FFA3] ml-auto" />}
                    </div>
                    <p className="text-[10px] text-slate-500 text-left">{cat.description}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Button
              onClick={sendTestAlert}
              disabled={testing || (!preferences.telegram_enabled && !preferences.push_enabled)}
              size="sm"
              variant="outline"
              className="flex-1 border-[#D946EF]/30 text-[#D946EF] hover:bg-[#D946EF]/10"
            >
              {testing ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Send className="w-4 h-4 mr-2" />
              )}
              Send Test Alert
            </Button>
            <Button
              onClick={() => setShowHistory(!showHistory)}
              size="sm"
              variant="outline"
              className="border-white/20 text-slate-300"
            >
              <History className="w-4 h-4 mr-1" />
              History
            </Button>
          </div>

          {/* Alert History */}
          {showHistory && (
            <div className="mt-4 p-3 bg-black/30 rounded-lg">
              <h6 className="text-xs font-semibold text-slate-300 mb-2">Recent Alerts</h6>
              {alertHistory.length > 0 ? (
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {alertHistory.map((alert, i) => (
                    <div key={i} className="flex items-center justify-between text-xs p-2 bg-white/5 rounded">
                      <div className="flex items-center gap-2">
                        <Rocket className="w-3 h-3 text-[#D946EF]" />
                        <span className="text-white font-medium">{alert.symbol}</span>
                        <Badge className="text-[8px] bg-white/10">{alert.alert_type}</Badge>
                      </div>
                      <div className="flex items-center gap-2 text-slate-500">
                        <span>{alert.channel}</span>
                        <Clock className="w-3 h-3" />
                        <span>{new Date(alert.sent_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 text-center py-2">No alerts sent yet</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Disabled State */}
      {!preferences.enabled && (
        <div className="p-4 text-center">
          <p className="text-sm text-slate-400 mb-3">
            Enable runner alerts to get notified when high-potential tokens are detected
          </p>
          <div className="flex flex-wrap justify-center gap-2 mb-3">
            {Object.entries(ALERT_CATEGORIES).map(([key, cat]) => {
              const Icon = cat.icon;
              return (
                <Badge key={key} className="bg-white/5 text-slate-400 text-[10px]">
                  <Icon className="w-3 h-3 mr-1" style={{ color: cat.color }} />
                  {cat.label}
                </Badge>
              );
            })}
          </div>
          <Button
            onClick={() => toggleAlerts(true)}
            size="sm"
            className="bg-[#D946EF] hover:bg-[#D946EF]/80"
          >
            <Bell className="w-4 h-4 mr-2" />
            Enable Runner Alerts
          </Button>
        </div>
      )}
    </div>
  );
}
