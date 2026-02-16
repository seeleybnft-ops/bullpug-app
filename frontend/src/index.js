import { Buffer } from 'buffer';
window.Buffer = window.Buffer || Buffer;

import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import '@solana/wallet-adapter-react-ui/styles.css';
import App from "@/App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
