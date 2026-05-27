/**
 * ErrorBoundary — top-level React error boundary that:
 *
 *  1. Catches render/lifecycle errors thrown anywhere in the React tree
 *     (via `componentDidCatch`) and reports them to `/api/client-errors`.
 *  2. Renders a graceful fallback UI with a "Reload" button instead of
 *     a blank white screen.
 *  3. Installs ONCE on mount two window-level listeners (`error` and
 *     `unhandledrejection`) so non-React crashes (e.g. inside a
 *     useEffect, a fetch handler, or third-party SDK code) are reported
 *     too. Both listeners use `keepalive` fetches so reports survive
 *     even if the page is unloading.
 *
 * The reporter is fire-and-forget — we never await its response or
 * surface failures, because by definition we're already in a broken
 * state and can't compound errors.
 *
 * Build id is read from `process.env.REACT_APP_BULLPUG_BUILD_ID` (set
 * by craco.config.js at build time — see PRD i168) so each captured
 * error is tied to the exact build it occurred on.
 */

import React from "react";

const REPORT_PATH = `${process.env.REACT_APP_BACKEND_URL}/api/client-errors`;
const BUILD_ID = process.env.REACT_APP_BULLPUG_BUILD_ID || "unknown";

// Suppress repeats so a render-loop doesn't fire hundreds of identical
// reports. The key is a short fingerprint of message + first stack frame.
const _seen = new Set();
const _MAX_REMEMBERED = 200;

function fingerprint(message, stack) {
  const head = (stack || "").split("\n").slice(0, 2).join("|");
  return `${message || ""}::${head}`.slice(0, 400);
}

function report(payload) {
  try {
    const fp = fingerprint(payload.message, payload.stack);
    if (_seen.has(fp)) return;
    if (_seen.size >= _MAX_REMEMBERED) _seen.clear();
    _seen.add(fp);

    let walletAddr = null;
    try { walletAddr = localStorage.getItem("walletAddress") || null; } catch (_) { /* ignore */ }

    const body = JSON.stringify({
      ...payload,
      url: typeof window !== "undefined" ? window.location.href.slice(0, 500) : null,
      user_agent: typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 400) : null,
      build_id: BUILD_ID,
      wallet: walletAddr ? walletAddr.slice(0, 64) : null,
    });

    // `keepalive: true` lets the request finish even if the page is
    // navigating away or unloading — important for fatal crashes.
    fetch(REPORT_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Bullpug-CSRF": "1" },
      body,
      keepalive: true,
      credentials: "same-origin",
    }).catch(() => { /* swallow — best effort */ });
  } catch (_) {
    // Reporting itself must NEVER throw.
  }
}

// ── Install global listeners exactly once (idempotent across HMR). ──
let _globalsInstalled = false;
function installGlobals() {
  if (_globalsInstalled || typeof window === "undefined") return;
  _globalsInstalled = true;

  window.addEventListener("error", (event) => {
    report({
      kind: "window-error",
      message: event.message || "unknown",
      stack: event.error && event.error.stack ? String(event.error.stack) : null,
      source: event.filename || null,
      line: event.lineno || null,
      column: event.colno || null,
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    const message = (reason && (reason.message || String(reason))) || "unhandled promise rejection";
    report({
      kind: "unhandled-rejection",
      message: String(message).slice(0, 2000),
      stack: reason && reason.stack ? String(reason.stack) : null,
    });
  });
}

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: null };
    installGlobals();
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: (error && error.message) || "Something went wrong.",
    };
  }

  componentDidCatch(error, errorInfo) {
    report({
      kind: "react-render",
      message: (error && error.message) || "react render error",
      stack: error && error.stack ? String(error.stack) : null,
      component_stack: errorInfo && errorInfo.componentStack
        ? String(errorInfo.componentStack)
        : null,
    });
  }

  handleReload = () => {
    try { window.location.reload(); } catch (_) { /* ignore */ }
  };

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div
        className="min-h-screen flex items-center justify-center px-6 bg-[#0a0a15]"
        data-testid="error-boundary-fallback"
      >
        <div className="max-w-md w-full glass-card rounded-2xl p-8 text-center border border-red-500/30">
          <div className="text-5xl mb-3">🐾</div>
          <h1
            className="text-2xl font-black text-red-400 mb-2"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Something tripped the pack
          </h1>
          <p className="text-sm text-slate-400 mb-4">
            We hit a snag rendering this page. The error has been logged so we can chase it down.
          </p>
          <p className="text-[10px] text-slate-600 font-mono break-all mb-5 line-clamp-3">
            {this.state.errorMessage}
          </p>
          <button
            onClick={this.handleReload}
            className="w-full py-3 rounded-xl bg-[#00FFA3] text-black font-bold text-sm uppercase tracking-wider hover:scale-[1.02] transition-transform"
            data-testid="error-boundary-reload"
          >
            Reload
          </button>
          <p className="text-[10px] text-slate-700 mt-4">build · {BUILD_ID}</p>
        </div>
      </div>
    );
  }
}
