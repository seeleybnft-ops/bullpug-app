import { useEffect, useState, useRef, useCallback } from "react";

const STORAGE_KEY_PERM = "bullpug_browser_notify_permission";

/**
 * Lightweight wrapper around the browser Notification API.
 * Works while the tab is open — does not require a service worker.
 *
 * Returns:
 *   permission        — "default" | "granted" | "denied" | "unsupported"
 *   requestPermission — call from a user-gesture handler to prompt
 *   notify({title,body,icon,tag,onClick}) — fires only when tab is hidden
 */
export default function useBrowserNotifications() {
  const [permission, setPermission] = useState(() => {
    if (typeof Notification === "undefined") return "unsupported";
    return Notification.permission;
  });
  const lastNotificationRef = useRef({});

  const requestPermission = useCallback(async () => {
    if (typeof Notification === "undefined") return "unsupported";
    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      try {
        localStorage.setItem(STORAGE_KEY_PERM, result);
      } catch (e) { /* ignore */ }
      return result;
    } catch (e) {
      return "denied";
    }
  }, []);

  // If the user has already granted permission in a previous visit, sync state
  useEffect(() => {
    if (typeof Notification !== "undefined") {
      setPermission(Notification.permission);
    }
  }, []);

  const notify = useCallback(({ title, body, icon, tag, onClick }) => {
    if (typeof Notification === "undefined") return null;
    if (Notification.permission !== "granted") return null;
    // Only fire when the tab is hidden — avoid double-notifying users who can already see the toast
    if (typeof document !== "undefined" && document.visibilityState === "visible") return null;
    // Dedupe by tag (~3 second window)
    const now = Date.now();
    if (tag && lastNotificationRef.current[tag] && now - lastNotificationRef.current[tag] < 3000) {
      return null;
    }
    if (tag) lastNotificationRef.current[tag] = now;
    try {
      const n = new Notification(title, { body, icon, tag, silent: false });
      if (onClick) {
        n.onclick = () => {
          window.focus();
          onClick();
          n.close();
        };
      }
      // Auto-close after 6 seconds so they don't pile up
      setTimeout(() => { try { n.close(); } catch (e) {} }, 6000);
      return n;
    } catch (e) {
      return null;
    }
  }, []);

  return { permission, requestPermission, notify };
}
