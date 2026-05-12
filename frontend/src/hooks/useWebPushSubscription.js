import { useCallback, useEffect, useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const STORAGE_KEY = "bullpug_web_push_state_v1"; // "idle" | "granted" | "denied"

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) arr[i] = raw.charCodeAt(i);
  return arr;
}

function isSupported() {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/**
 * Register the Bullpug service worker and (when called) subscribe the
 * browser to Web Push, posting the subscription up to the backend so the
 * server can wake the user with a notification even when the tab is closed.
 *
 * Returns:
 *   supported      — Web Push API available in this browser
 *   permission     — "default" | "granted" | "denied" | "unsupported"
 *   subscribed     — boolean (live state from the browser)
 *   subscribe()    — call from a user gesture to opt in (idempotent)
 *   unsubscribe()  — opt out
 */
export default function useWebPushSubscription({ walletAddress } = {}) {
  const [supported] = useState(() => isSupported());
  const [permission, setPermission] = useState(() => {
    if (!isSupported()) return "unsupported";
    return Notification.permission;
  });
  const [subscribed, setSubscribed] = useState(false);

  // Register SW once on mount; query current subscription state
  useEffect(() => {
    if (!supported) return;
    let cancelled = false;
    (async () => {
      try {
        const reg = await navigator.serviceWorker.register("/sw-push.js");
        const ready = await navigator.serviceWorker.ready;
        const existing = await (ready || reg).pushManager.getSubscription();
        if (!cancelled) setSubscribed(!!existing);
      } catch (e) {
        // SW registration failed — non-fatal; in-tab notifications still work
        // eslint-disable-next-line no-console
        console.warn("[push] SW register failed:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [supported]);

  const subscribe = useCallback(async () => {
    if (!supported) return false;
    try {
      // 1. Permission
      let perm = Notification.permission;
      if (perm === "default") {
        perm = await Notification.requestPermission();
        setPermission(perm);
        try { localStorage.setItem(STORAGE_KEY, perm); } catch (e) { /* ignore */ }
      }
      if (perm !== "granted") return false;

      // 2. VAPID public key
      const { data } = await axios.get(`${API}/push-notifications/vapid-public-key`);
      if (!data || !data.configured || !data.public_key) {
        // eslint-disable-next-line no-console
        console.warn("[push] backend missing VAPID config");
        return false;
      }

      // 3. Subscribe
      const reg = await navigator.serviceWorker.ready;
      let sub = await reg.pushManager.getSubscription();
      if (!sub) {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(data.public_key),
        });
      }

      // 4. Post to backend
      const json = sub.toJSON();
      await axios.post(`${API}/push-notifications/subscribe`, {
        wallet_address: walletAddress || null,
        subscription: { endpoint: json.endpoint, keys: json.keys },
        device_name: navigator.userAgent.slice(0, 60),
        platform: "web",
      });

      setSubscribed(true);
      return true;
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[push] subscribe failed:", e);
      return false;
    }
  }, [supported, walletAddress]);

  const unsubscribe = useCallback(async () => {
    if (!supported) return;
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        const endpoint = sub.endpoint;
        await sub.unsubscribe();
        if (walletAddress) {
          await axios.post(`${API}/push-notifications/unsubscribe`, null, {
            params: { wallet_address: walletAddress, endpoint },
          });
        }
      }
      setSubscribed(false);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[push] unsubscribe failed:", e);
    }
  }, [supported, walletAddress]);

  return { supported, permission, subscribed, subscribe, unsubscribe };
}
