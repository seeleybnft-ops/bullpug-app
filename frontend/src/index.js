import { Buffer } from 'buffer';
window.Buffer = window.Buffer || Buffer;

import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import '@solana/wallet-adapter-react-ui/styles.css';
import App from "@/App";

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
