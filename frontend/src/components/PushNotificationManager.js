/**
 * PushNotificationManager Component
 * 
 * Manages browser push notification subscriptions for copy trading events:
 * - Subscribe/unsubscribe from push notifications
 * - Manage notification preferences
 * - Test notifications
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Bell, BellOff, BellRing, Smartphone, Monitor, Check, X,
  Loader2, Settings, Send, AlertCircle, ChevronDown, ChevronUp,
  Copy, UserPlus, TrendingUp, TrendingDown, AlertTriangle, DollarSign
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Check if push notifications are supported
const isPushSupported = () => {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
};

export default function PushNotificationManager({ compact = false }) {
  const { publicKey, connected } = useWallet();
  const walletAddress = publicKey?.toBase58();

  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(!compact);
  const [subscribed, setSubscribed] = useState(false);
  const [permission, setPermission] = useState('default');
  const [vapidKey, setVapidKey] = useState(null);
  const [vapidConfigured, setVapidConfigured] = useState(false);
  const [subscriptions, setSubscriptions] = useState([]);
  const [preferences, setPreferences] = useState({
    trade_copied: true,
    new_follower: true,
    fee_earned: true,
    profit_alerts: true,
    loss_alerts: true,
    stop_loss_triggered: true,
    min_profit_percent: 10.0,
    min_loss_percent: 5.0
  });

  // Check notification permission
  useEffect(() => {
    if (isPushSupported()) {
      setPermission(Notification.permission);
    }
  }, []);

  // Fetch VAPID public key
  const fetchVapidKey = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/push-notifications/vapid-public-key`);
      setVapidKey(data.public_key);
      setVapidConfigured(data.configured);
    } catch (e) {
      console.error('Failed to fetch VAPID key:', e);
    }
  }, []);

  // Fetch subscriptions
  const fetchSubscriptions = useCallback(async () => {
    if (!walletAddress) return;
    
    try {
      const { data } = await axios.get(`${API}/push-notifications/subscriptions/${walletAddress}`);
      setSubscriptions(data.subscriptions || []);
      setSubscribed(data.count > 0);
    } catch (e) {
      console.error('Failed to fetch subscriptions:', e);
    }
  }, [walletAddress]);

  // Fetch preferences
  const fetchPreferences = useCallback(async () => {
    if (!walletAddress) return;
    
    try {
      const { data } = await axios.get(`${API}/push-notifications/preferences/${walletAddress}`);
      setPreferences(data);
    } catch (e) {
      console.error('Failed to fetch preferences:', e);
    }
    setLoading(false);
  }, [walletAddress]);

  // Initial load
  useEffect(() => {
    fetchVapidKey();
    if (walletAddress) {
      fetchSubscriptions();
      fetchPreferences();
    } else {
      setLoading(false);
    }
  }, [walletAddress, fetchVapidKey, fetchSubscriptions, fetchPreferences]);

  // Request notification permission
  const requestPermission = async () => {
    if (!isPushSupported()) {
      toast.error('Push notifications are not supported in this browser');
      return false;
    }

    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      
      if (result === 'granted') {
        toast.success('Notification permission granted!');
        return true;
      } else if (result === 'denied') {
        toast.error('Notification permission denied. Please enable in browser settings.');
        return false;
      }
      return false;
    } catch (e) {
      toast.error('Failed to request permission');
      return false;
    }
  };

  // Subscribe to push notifications
  const subscribe = async () => {
    if (!walletAddress) {
      toast.error('Please connect your wallet first');
      return;
    }

    if (permission !== 'granted') {
      const granted = await requestPermission();
      if (!granted) return;
    }

    try {
      setLoading(true);

      // Register service worker if needed
      const registration = await navigator.serviceWorker.ready;

      // Get push subscription
      let subscription = await registration.pushManager.getSubscription();
      
      if (!subscription) {
        // Create new subscription
        // Note: In production, use the actual VAPID key
        const vapidKeyToUse = vapidKey || 'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U';
        
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidKeyToUse)
        });
      }

      // Send subscription to backend
      const subscriptionJson = subscription.toJSON();
      await axios.post(`${API}/push-notifications/subscribe`, {
        wallet_address: walletAddress,
        subscription: {
          endpoint: subscriptionJson.endpoint,
          keys: subscriptionJson.keys
        },
        device_name: getDeviceName(),
        platform: 'web'
      });

      setSubscribed(true);
      await fetchSubscriptions();
      toast.success('Push notifications enabled!');
    } catch (e) {
      console.error('Subscribe error:', e);
      toast.error('Failed to enable push notifications');
    } finally {
      setLoading(false);
    }
  };

  // Unsubscribe from push notifications
  const unsubscribe = async () => {
    if (!walletAddress) return;

    try {
      setLoading(true);

      // Unsubscribe from browser
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      
      if (subscription) {
        await subscription.unsubscribe();
      }

      // Unsubscribe from backend
      await axios.post(`${API}/push-notifications/unsubscribe`, null, {
        params: { wallet_address: walletAddress }
      });

      setSubscribed(false);
      setSubscriptions([]);
      toast.success('Push notifications disabled');
    } catch (e) {
      console.error('Unsubscribe error:', e);
      toast.error('Failed to disable push notifications');
    } finally {
      setLoading(false);
    }
  };

  // Update preference
  const updatePreference = async (key, value) => {
    if (!walletAddress) return;

    try {
      const { data } = await axios.put(
        `${API}/push-notifications/preferences/${walletAddress}`,
        null,
        { params: { [key]: value } }
      );
      setPreferences(data);
      toast.success('Preference updated');
    } catch (e) {
      toast.error('Failed to update preference');
    }
  };

  // Send test notification
  const sendTestNotification = async () => {
    if (!walletAddress) return;

    try {
      await axios.post(`${API}/push-notifications/send-test/${walletAddress}`);
      toast.success('Test notification sent! Check your browser.');
    } catch (e) {
      toast.error('Failed to send test notification');
    }
  };

  // Helper: Convert base64 to Uint8Array for VAPID key
  const urlBase64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  };

  // Helper: Get device name
  const getDeviceName = () => {
    const ua = navigator.userAgent;
    if (ua.includes('Chrome')) return 'Chrome Browser';
    if (ua.includes('Firefox')) return 'Firefox Browser';
    if (ua.includes('Safari')) return 'Safari Browser';
    if (ua.includes('Edge')) return 'Edge Browser';
    return 'Web Browser';
  };

  if (!connected) {
    return null;
  }

  if (!isPushSupported()) {
    return (
      <div className="glass-card rounded-xl p-4 border border-white/10" data-testid="push-notification-manager">
        <div className="flex items-center gap-3 text-slate-400">
          <AlertCircle className="w-5 h-5" />
          <p className="text-sm">Push notifications are not supported in this browser</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl overflow-hidden border border-white/10" data-testid="push-notification-manager">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="relative">
            {subscribed ? (
              <BellRing className="w-5 h-5 text-[#00FFA3]" />
            ) : (
              <Bell className="w-5 h-5 text-slate-400" />
            )}
          </div>
          <span className="text-sm font-medium text-white">Push Notifications</span>
          {subscribed && (
            <Badge className="text-[10px] bg-[#00FFA3]/20 text-[#00FFA3]">
              Active
            </Badge>
          )}
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>

      {expanded && (
        <div className="border-t border-white/5 p-4 space-y-4">
          {/* Status & Subscribe Button */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-white font-medium">Browser Notifications</p>
              <p className="text-xs text-slate-400">
                {subscribed 
                  ? `Receiving on ${subscriptions.length} device${subscriptions.length !== 1 ? 's' : ''}`
                  : 'Get instant alerts for copy trading events'
                }
              </p>
            </div>
            <Button
              size="sm"
              onClick={subscribed ? unsubscribe : subscribe}
              disabled={loading}
              className={subscribed 
                ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30'
                : 'bg-gradient-to-r from-[#D946EF] to-[#00C2FF] text-white'
              }
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : subscribed ? (
                <>
                  <BellOff className="w-4 h-4 mr-1" />
                  Disable
                </>
              ) : (
                <>
                  <Bell className="w-4 h-4 mr-1" />
                  Enable
                </>
              )}
            </Button>
          </div>

          {/* Permission Warning */}
          {permission === 'denied' && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-red-400 font-medium">Permission Blocked</p>
                <p className="text-xs text-red-400/70">
                  Please enable notifications in your browser settings to receive push alerts.
                </p>
              </div>
            </div>
          )}

          {/* Subscribed Devices */}
          {subscribed && subscriptions.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-bold text-slate-400 uppercase">Active Devices</p>
              {subscriptions.map((sub, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-300">
                  <Monitor className="w-3 h-3 text-[#00FFA3]" />
                  <span>{sub.device_name || 'Browser'}</span>
                  <span className="text-slate-600">•</span>
                  <span className="text-slate-500">{sub.platform}</span>
                </div>
              ))}
            </div>
          )}

          {/* Preferences */}
          {subscribed && (
            <>
              <div className="border-t border-white/5 pt-4">
                <p className="text-xs font-bold text-slate-400 uppercase mb-3">Notification Types</p>
                <div className="space-y-3">
                  {[
                    { key: 'trade_copied', label: 'Trade Copied', icon: <Copy className="w-4 h-4" />, desc: 'When a trade is copied from followed traders' },
                    { key: 'new_follower', label: 'New Follower', icon: <UserPlus className="w-4 h-4" />, desc: 'When someone starts copying your trades' },
                    { key: 'fee_earned', label: 'Fee Earned', icon: <DollarSign className="w-4 h-4" />, desc: 'When you earn a performance fee' },
                    { key: 'profit_alerts', label: 'Profit Alerts', icon: <TrendingUp className="w-4 h-4" />, desc: 'Significant profit on copied trades' },
                    { key: 'loss_alerts', label: 'Loss Alerts', icon: <TrendingDown className="w-4 h-4" />, desc: 'Significant loss on copied trades' },
                    { key: 'stop_loss_triggered', label: 'Stop Loss', icon: <AlertTriangle className="w-4 h-4" />, desc: 'When stop loss is triggered' }
                  ].map(({ key, label, icon, desc }) => (
                    <div key={key} className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-2 flex-1">
                        <span className="text-slate-400">{icon}</span>
                        <div>
                          <p className="text-sm text-white">{label}</p>
                          <p className="text-[10px] text-slate-500">{desc}</p>
                        </div>
                      </div>
                      <Switch
                        checked={preferences[key]}
                        onCheckedChange={(checked) => updatePreference(key, checked)}
                        className="data-[state=checked]:bg-[#D946EF]"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Thresholds */}
              <div className="border-t border-white/5 pt-4 space-y-3">
                <p className="text-xs font-bold text-slate-400 uppercase">Alert Thresholds</p>
                
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Min profit alert</span>
                    <span className="text-[#00FFA3]">{preferences.min_profit_percent}%</span>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max="100"
                    value={preferences.min_profit_percent}
                    onChange={(e) => updatePreference('min_profit_percent', parseFloat(e.target.value))}
                    className="w-full accent-[#00FFA3] h-1"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Min loss alert</span>
                    <span className="text-[#FF6B6B]">{preferences.min_loss_percent}%</span>
                  </div>
                  <input
                    type="range"
                    min="2"
                    max="50"
                    value={preferences.min_loss_percent}
                    onChange={(e) => updatePreference('min_loss_percent', parseFloat(e.target.value))}
                    className="w-full accent-[#FF6B6B] h-1"
                  />
                </div>
              </div>

              {/* Test Button */}
              <div className="border-t border-white/5 pt-4">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={sendTestNotification}
                  className="w-full border-white/10 text-slate-300 hover:text-white hover:bg-white/5"
                >
                  <Send className="w-4 h-4 mr-2" />
                  Send Test Notification
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
