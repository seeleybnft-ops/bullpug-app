/**
 * CopyTradeNotifications Component
 * 
 * Displays notifications for copy trading activity:
 * - Trade copied notifications
 * - New follower notifications
 * - Profit/loss alerts
 * - Stop loss triggers
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Bell, BellOff, Check, X, Trash2, Copy, TrendingUp, TrendingDown,
  UserPlus, AlertTriangle, Loader2, ChevronDown, ChevronUp,
  Settings, DollarSign, Shield, Zap, Clock
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Notification type icons and colors
const NOTIFICATION_STYLES = {
  trade_copied: {
    icon: <Copy className="w-4 h-4" />,
    color: '#D946EF',
    bg: 'rgba(217, 70, 239, 0.15)'
  },
  new_follower: {
    icon: <UserPlus className="w-4 h-4" />,
    color: '#00FFA3',
    bg: 'rgba(0, 255, 163, 0.15)'
  },
  profit_alert: {
    icon: <TrendingUp className="w-4 h-4" />,
    color: '#00FFA3',
    bg: 'rgba(0, 255, 163, 0.15)'
  },
  loss_alert: {
    icon: <TrendingDown className="w-4 h-4" />,
    color: '#FF6B6B',
    bg: 'rgba(255, 107, 107, 0.15)'
  },
  stop_loss_triggered: {
    icon: <AlertTriangle className="w-4 h-4" />,
    color: '#FFA500',
    bg: 'rgba(255, 165, 0, 0.15)'
  },
  default: {
    icon: <Bell className="w-4 h-4" />,
    color: '#00C2FF',
    bg: 'rgba(0, 194, 255, 0.15)'
  }
};

export default function CopyTradeNotifications({ compact = false }) {
  const { publicKey, connected } = useWallet();
  const walletAddress = publicKey?.toBase58();

  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(!compact);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    trade_copied: true,
    new_follower: true,
    profit_alerts: true,
    loss_alerts: true,
    stop_loss_triggered: true,
    min_profit_alert_percent: 10,
    min_loss_alert_percent: 5
  });

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    if (!walletAddress) return;
    
    try {
      const { data } = await axios.get(`${API}/social-trading/notifications/${walletAddress}?limit=20`);
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (e) {
      console.error('Failed to fetch notifications:', e);
    }
    setLoading(false);
  }, [walletAddress]);

  // Fetch notification settings
  const fetchSettings = useCallback(async () => {
    if (!walletAddress) return;
    
    try {
      const { data } = await axios.get(`${API}/social-trading/notifications/settings/${walletAddress}`);
      setSettings(data);
    } catch (e) {
      console.error('Failed to fetch settings:', e);
    }
  }, [walletAddress]);

  // Initial fetch
  useEffect(() => {
    fetchNotifications();
    fetchSettings();
  }, [fetchNotifications, fetchSettings]);

  // Poll for new notifications every 30 seconds
  useEffect(() => {
    if (!connected) return;
    
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [connected, fetchNotifications]);

  // Mark notification as read
  const markAsRead = async (notificationId) => {
    if (!walletAddress) return;
    
    try {
      await axios.post(`${API}/social-trading/notifications/mark-read/${walletAddress}`, null, {
        params: { notification_ids: [notificationId] }
      });
      
      setNotifications(prev => prev.map(n => 
        n.notification_id === notificationId ? { ...n, read: true } : n
      ));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (e) {
      console.error('Failed to mark as read:', e);
    }
  };

  // Mark all as read
  const markAllAsRead = async () => {
    if (!walletAddress) return;
    
    try {
      await axios.post(`${API}/social-trading/notifications/mark-read/${walletAddress}`);
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
      toast.success('All notifications marked as read');
    } catch (e) {
      toast.error('Failed to mark all as read');
    }
  };

  // Delete notification
  const deleteNotification = async (notificationId) => {
    if (!walletAddress) return;
    
    try {
      await axios.delete(`${API}/social-trading/notifications/${walletAddress}/${notificationId}`);
      setNotifications(prev => prev.filter(n => n.notification_id !== notificationId));
      toast.success('Notification deleted');
    } catch (e) {
      toast.error('Failed to delete notification');
    }
  };

  // Update settings
  const updateSettings = async (key, value) => {
    if (!walletAddress) return;
    
    try {
      const { data } = await axios.put(
        `${API}/social-trading/notifications/settings/${walletAddress}`,
        null,
        { params: { [key]: value } }
      );
      setSettings(data);
      toast.success('Settings updated');
    } catch (e) {
      toast.error('Failed to update settings');
    }
  };

  // Format relative time
  const formatTime = (isoString) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  // Get notification style
  const getStyle = (type) => NOTIFICATION_STYLES[type] || NOTIFICATION_STYLES.default;

  if (!connected) {
    return null; // Don't show if wallet not connected
  }

  return (
    <div className="glass-card rounded-xl overflow-hidden border border-white/10" data-testid="copy-trade-notifications">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="relative">
            <Bell className="w-5 h-5 text-[#D946EF]" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#FF6B6B] rounded-full text-[10px] font-bold flex items-center justify-center text-white">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </div>
          <span className="text-sm font-medium text-white">Copy Trade Alerts</span>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Badge className="text-[10px] bg-[#D946EF]/20 text-[#D946EF]">
              {unreadCount} new
            </Badge>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/5">
          {/* Actions */}
          <div className="p-2 flex items-center justify-between bg-black/20">
            <div className="flex gap-2">
              {unreadCount > 0 && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={markAllAsRead}
                  className="h-7 text-[10px] text-slate-400 hover:text-white"
                >
                  <Check className="w-3 h-3 mr-1" />
                  Mark all read
                </Button>
              )}
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowSettings(!showSettings)}
              className={`h-7 text-[10px] ${showSettings ? 'text-[#D946EF]' : 'text-slate-400 hover:text-white'}`}
            >
              <Settings className="w-3 h-3 mr-1" />
              Settings
            </Button>
          </div>

          {/* Settings Panel */}
          {showSettings && (
            <div className="p-3 border-b border-white/5 bg-black/30 space-y-2">
              <p className="text-xs font-bold text-slate-400 uppercase mb-2">Notification Preferences</p>
              
              {[
                { key: 'trade_copied', label: 'Trade Copied', icon: <Copy className="w-3 h-3" /> },
                { key: 'new_follower', label: 'New Follower', icon: <UserPlus className="w-3 h-3" /> },
                { key: 'profit_alerts', label: 'Profit Alerts', icon: <TrendingUp className="w-3 h-3" /> },
                { key: 'loss_alerts', label: 'Loss Alerts', icon: <TrendingDown className="w-3 h-3" /> },
                { key: 'stop_loss_triggered', label: 'Stop Loss', icon: <AlertTriangle className="w-3 h-3" /> }
              ].map(({ key, label, icon }) => (
                <label key={key} className="flex items-center justify-between cursor-pointer">
                  <span className="text-xs text-slate-300 flex items-center gap-2">
                    {icon} {label}
                  </span>
                  <button
                    onClick={() => updateSettings(key, !settings[key])}
                    className={`w-8 h-4 rounded-full transition-colors relative ${
                      settings[key] ? 'bg-[#D946EF]' : 'bg-slate-600'
                    }`}
                  >
                    <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${
                      settings[key] ? 'left-4' : 'left-0.5'
                    }`} />
                  </button>
                </label>
              ))}
              
              <div className="pt-2 border-t border-white/5">
                <label className="text-xs text-slate-400">
                  Min profit alert: {settings.min_profit_alert_percent}%
                </label>
                <input
                  type="range"
                  min="5"
                  max="50"
                  value={settings.min_profit_alert_percent}
                  onChange={(e) => updateSettings('min_profit_alert_percent', parseInt(e.target.value))}
                  className="w-full mt-1"
                />
              </div>
            </div>
          )}

          {/* Notifications List */}
          <div className="max-h-[300px] overflow-y-auto">
            {loading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-[#D946EF]" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-8">
                <BellOff className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No notifications yet</p>
                <p className="text-xs text-slate-600">Follow traders to get copy trade alerts!</p>
              </div>
            ) : (
              notifications.map((notification) => {
                const style = getStyle(notification.notification_type);
                
                return (
                  <div
                    key={notification.notification_id}
                    className={`p-3 border-b border-white/5 hover:bg-white/5 transition-colors ${
                      !notification.read ? 'bg-white/5' : ''
                    }`}
                    onClick={() => !notification.read && markAsRead(notification.notification_id)}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: style.bg, color: style.color }}
                      >
                        {style.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-medium text-white truncate">
                            {notification.title}
                            {!notification.read && (
                              <span className="ml-2 w-2 h-2 bg-[#D946EF] rounded-full inline-block" />
                            )}
                          </p>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteNotification(notification.notification_id);
                            }}
                            className="p-1 rounded hover:bg-white/10 text-slate-500 hover:text-red-400"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5">{notification.message}</p>
                        <p className="text-[10px] text-slate-600 mt-1 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTime(notification.created_at)}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
