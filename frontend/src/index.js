import { Buffer } from 'buffer';
window.Buffer = window.Buffer || Buffer;

import React from "react";
import ReactDOM from "react-dom/client";
import axios from "axios";
import "@/index.css";
import '@solana/wallet-adapter-react-ui/styles.css';
import App from "@/App";

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
