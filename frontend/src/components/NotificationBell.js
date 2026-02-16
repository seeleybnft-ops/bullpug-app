import { useState, useEffect, useCallback } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { Badge } from "@/components/ui/badge";
import axios from "axios";
import {
  Bell, X, MessageSquare, Trophy, Swords, Check
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const NOTIF_ICONS = {
  message: <MessageSquare size={14} className="text-[#00C2FF]" />,
  challenge: <Swords size={14} className="text-[#00FFA3]" />,
  pot: <Trophy size={14} className="text-[#D946EF]" />,
  general: <Bell size={14} className="text-amber-400" />
};

export default function NotificationBell() {
  const { publicKey, connected } = useWallet();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifications = useCallback(async () => {
    if (!publicKey) return;
    try {
      const { data } = await axios.get(`${API}/notifications/${publicKey.toBase58()}`);
      setNotifications(data.notifications);
      setUnreadCount(data.unread_count);
    } catch (e) {
      console.error(e);
    }
  }, [publicKey]);

  useEffect(() => {
    if (connected && publicKey) {
      fetchNotifications();
      
      // Connect WebSocket for real-time notifications
      const wsUrl = process.env.REACT_APP_BACKEND_URL.replace("https://", "wss://").replace("http://", "ws://");
      const socket = new WebSocket(`${wsUrl}/ws/notifications/${publicKey.toBase58()}`);
      
      socket.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "notification") {
          setNotifications(prev => [msg.data, ...prev]);
          setUnreadCount(prev => prev + 1);
          
          // Show browser notification if permitted
          if (Notification.permission === "granted") {
            new Notification(msg.data.title, {
              body: msg.data.body,
              icon: "/favicon.ico"
            });
          }
        } else if (msg.type === "initial_notifications") {
          setNotifications(prev => [...msg.data, ...prev.filter(n => !msg.data.find(m => m.id === n.id))]);
        }
      };

      // Request notification permission
      if (Notification.permission === "default") {
        Notification.requestPermission();
      }

      return () => socket.close();
    }
  }, [connected, publicKey, fetchNotifications]);

  const markAsRead = async (notifId) => {
    try {
      await axios.post(`${API}/notifications/read/${notifId}`);
      setNotifications(prev => prev.map(n => n.id === notifId ? { ...n, read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (e) {
      console.error(e);
    }
  };

  const markAllRead = async () => {
    if (!publicKey) return;
    try {
      await axios.post(`${API}/notifications/read-all/${publicKey.toBase58()}`);
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (e) {
      console.error(e);
    }
  };

  if (!connected) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-[#F5D300]/50 transition-all"
        data-testid="notification-bell"
      >
        <Bell size={14} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[9px] font-bold flex items-center justify-center text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-80 glass-card rounded-xl border border-white/10 shadow-xl z-50 overflow-hidden">
            <div className="p-3 border-b border-white/10 flex items-center justify-between">
              <span className="text-sm font-bold">Notifications</span>
              {unreadCount > 0 && (
                <button onClick={markAllRead} className="text-xs text-[#00FFA3] hover:underline">
                  Mark all read
                </button>
              )}
            </div>

            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-6 text-center">
                  <Bell className="w-8 h-8 mx-auto mb-2 text-slate-700" />
                  <p className="text-slate-600 text-sm">No notifications</p>
                </div>
              ) : (
                notifications.slice(0, 20).map(notif => (
                  <div
                    key={notif.id}
                    className={`p-3 border-b border-white/5 hover:bg-white/[0.02] cursor-pointer ${
                      !notif.read ? "bg-[#00FFA3]/5" : ""
                    }`}
                    onClick={() => !notif.read && markAsRead(notif.id)}
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center flex-shrink-0">
                        {NOTIF_ICONS[notif.type] || NOTIF_ICONS.general}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-bold text-white">{notif.title}</p>
                        <p className="text-xs text-slate-400 line-clamp-2">{notif.body}</p>
                        <p className="text-[10px] text-slate-600 mt-1">
                          {new Date(notif.created_at).toLocaleString()}
                        </p>
                      </div>
                      {!notif.read && (
                        <div className="w-2 h-2 rounded-full bg-[#00FFA3] flex-shrink-0 mt-2" />
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
