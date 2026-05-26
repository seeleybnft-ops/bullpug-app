import { Buffer } from 'buffer';
window.Buffer = window.Buffer || Buffer;

import React from "react";
import ReactDOM from "react-dom/client";
import axios from "axios";
import "@/index.css";
import '@solana/wallet-adapter-react-ui/styles.css';
import App from "@/App";

/**
 * Build-id cache bust
 * --------------------
 * Bump `BULLPUG_BUILD_ID` whenever a deploy ships changes that must
 * not be served from a stale browser cache (HTML, JS bundles, stuck
 * localStorage state, etc.). On every boot we compare the constant
 * against `localStorage.bullpugLastBuildId`; on mismatch we:
 *
 *   1. Wipe the entire CacheStorage (covers any future precaching SWs
 *      and the offline cache fallback some browsers populate).
 *   2. Unregister every active service worker EXCEPT the push handler
 *      at `/sw-push.js` (defensive — keeps notifications working while
 *      flushing anything else that might have been registered later).
 *   3. Record the new build id.
 *   4. Force one hard reload — guarded by sessionStorage so the reload
 *      itself can never trigger another reload (no boot-loops even if
 *      the wipe somehow fails).
 *
 * The check runs BEFORE React mounts so users never see stale UI flash.
 * Whole block is try/catch wrapped — any storage failure (private mode,
 * sandboxed iframe) falls through to the normal render path so we never
 * brick the app on a permission error.
 */
const BULLPUG_BUILD_ID = "2026-02-26-pug-pit-eng-lock";

(function cacheBustBoot() {
  if (typeof window === "undefined") return;
  try {
    const last = window.localStorage.getItem("bullpugLastBuildId");
    if (last === BULLPUG_BUILD_ID) return;
    // Guard against reload loops — set a sessionStorage flag the first
    // time we trigger a reload, and never trigger a second reload in the
    // same tab session even if the localStorage write somehow failed.
    const reloadedFlag = window.sessionStorage.getItem("bullpugBuildBustReloaded");
    if (reloadedFlag === BULLPUG_BUILD_ID) {
      // Already reloaded once this session — just record + continue.
      window.localStorage.setItem("bullpugLastBuildId", BULLPUG_BUILD_ID);
      return;
    }
    // Fire-and-forget wipe. We don't wait for it — the reload below will
    // happen as soon as the synchronous part finishes.
    if ("caches" in window) {
      window.caches.keys().then((names) => names.forEach((n) => window.caches.delete(n))).catch(() => {});
    }
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((r) => {
          // Keep the push handler — it's the only SW we register and we
          // don't want to lose notification permission grants.
          if (!r.active || !r.active.scriptURL || !r.active.scriptURL.endsWith("/sw-push.js")) {
            r.unregister().catch(() => {});
          }
        });
      }).catch(() => {});
    }
    window.sessionStorage.setItem("bullpugBuildBustReloaded", BULLPUG_BUILD_ID);
    window.localStorage.setItem("bullpugLastBuildId", BULLPUG_BUILD_ID);
    // location.reload(true) is non-standard / deprecated in many engines —
    // setting a cache-busting query param + replace() is the portable
    // equivalent. The fresh URL bypasses HTTP-cache for the main document.
    const u = new URL(window.location.href);
    u.searchParams.set("_b", BULLPUG_BUILD_ID);
    window.location.replace(u.toString());
  } catch (_) {
    // Storage unavailable / cross-origin / sandboxed — skip the bust,
    // let the app render normally.
  }
})();

// ── CSRF: every state-changing request to the Bullpug API carries this
// header. The backend rejects POST/PUT/DELETE/PATCH on /api/* without it.
// Browsers cannot attach custom headers cross-origin without a successful
// CORS preflight, so this header is effectively unforgeable from a hostile
// site even if a user is logged in.
axios.defaults.headers.common["X-Bullpug-CSRF"] = "1";

// Cover the fetch() call-sites (BigWinToast, push subscribe, etc.) by
// wrapping the global fetch once. This keeps every existing fetch() call
// working without per-call changes.
if (typeof window !== "undefined" && typeof window.fetch === "function") {
  const _origFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const headers = new Headers(init.headers || (typeof input === "object" ? input.headers : undefined));
    headers.set("X-Bullpug-CSRF", "1");
    return _origFetch(input, { ...init, headers });
  };
}

// Register service worker for push notifications
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw-push.js')
      .then(registration => {
        console.log('Push SW registered:', registration.scope);
      })
      .catch(error => {
        console.log('Push SW registration failed:', error);
      });
  });
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
