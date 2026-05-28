/**
 * usePageviewTracker — fires one anonymous pageview to `/api/analytics/track`
 * on every SPA route change.
 *
 * Notes
 * ─────
 * • Pageviews are best-effort. We use `keepalive: true` so even if the
 *   browser starts navigating away the request still flushes, and we
 *   swallow every error — analytics must never break the app.
 * • The very first mount also records the initial route, otherwise
 *   visitors that land on `/` and bounce would be invisible in stats.
 * • We deliberately do NOT send any user identifier — the backend builds
 *   its own daily-rotating anonymous visitor hash from IP+UA.
 */

import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function usePageviewTracker() {
  const location = useLocation();
  // Guard against React StrictMode double-mounting the same path back to
  // back, which would otherwise double-count the initial visit.
  const lastSentRef = useRef(null);

  useEffect(() => {
    const path = location.pathname || "/";
    if (lastSentRef.current === path) return;
    lastSentRef.current = path;

    // Reset behaviour: don't block the user if backend is unreachable.
    try {
      fetch(`${API}/analytics/track`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path,
          referer: document.referrer || null,
          transition: "navigate",
        }),
        keepalive: true,
      }).catch(() => {});
    } catch {
      /* analytics never breaks the app */
    }
  }, [location.pathname]);
}
