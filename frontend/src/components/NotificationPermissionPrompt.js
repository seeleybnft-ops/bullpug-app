import { useEffect, useState } from "react";
import { Bell, X, Check } from "lucide-react";
import useWebPushSubscription from "../hooks/useWebPushSubscription";

const STORAGE_DISMISS = "bullpug_push_prompt_dismissed_v1";
const DELAY_MS = 12000; // give the user 12s on the page before nudging

/**
 * Tiny bottom-left card that asks the visitor once whether they want OS-level
 * push notifications for big arena wins. After dismissal it never re-appears.
 *
 * Renders nothing if:
 *   - the browser doesn't support push
 *   - the user has already granted or denied permission
 *   - the user has already dismissed the prompt in a previous session
 */
export default function NotificationPermissionPrompt() {
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [enabling, setEnabling] = useState(false);
  const { supported, permission, subscribed, subscribe } = useWebPushSubscription();

  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_DISMISS) === "1") {
        setDismissed(true);
      }
    } catch (e) { /* ignore */ }
  }, []);

  // Delay before showing so we don't interrupt landing animations
  useEffect(() => {
    if (!supported) return;
    if (dismissed) return;
    if (permission !== "default") return;
    if (subscribed) return;
    const t = setTimeout(() => setVisible(true), DELAY_MS);
    return () => clearTimeout(t);
  }, [supported, permission, subscribed, dismissed]);

  const handleEnable = async () => {
    setEnabling(true);
    const ok = await subscribe();
    setEnabling(false);
    if (ok) {
      setVisible(false);
      try { localStorage.setItem(STORAGE_DISMISS, "1"); } catch (e) { /* ignore */ }
    }
  };

  const handleDismiss = () => {
    setVisible(false);
    setDismissed(true);
    try { localStorage.setItem(STORAGE_DISMISS, "1"); } catch (e) { /* ignore */ }
  };

  if (!visible) return null;

  return (
    <div
      data-testid="push-permission-prompt"
      className="fixed bottom-4 left-4 z-[70] w-[320px] sm:w-[360px] rounded-2xl overflow-hidden border border-[#00FFA3]/30 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] shadow-[0_0_40px_rgba(0,255,163,0.18)] animate-[slideInLeft_0.4s_ease-out]"
    >
      <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-[#00FFA3] via-[#F5D300] to-[#D946EF]" />
      <button
        type="button"
        onClick={handleDismiss}
        data-testid="push-prompt-dismiss"
        className="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/50 border border-white/10 text-white/60 hover:text-white flex items-center justify-center transition-colors"
        aria-label="Dismiss"
      >
        <X size={12} />
      </button>
      <div className="p-4 pt-5">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30 flex items-center justify-center">
            <Bell className="w-4 h-4 text-[#00FFA3]" />
          </div>
          <span
            className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#00FFA3]"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Never miss a big win
          </span>
        </div>
        <p className="text-[12px] text-slate-300 leading-relaxed mb-3">
          Get a tiny ping when someone takes home <span className="text-[#F5D300] font-bold">&gt; 1 SOL</span> from
          the arena — works even when the tab is closed.
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleEnable}
            disabled={enabling}
            data-testid="push-prompt-enable"
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-full bg-[#00FFA3] hover:bg-[#00FFA3]/90 disabled:opacity-60 text-black text-[11px] font-bold uppercase tracking-wider transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
            {enabling ? "Enabling…" : "Enable pings"}
          </button>
          <button
            type="button"
            onClick={handleDismiss}
            className="px-3 py-2 rounded-full bg-transparent border border-white/15 hover:border-white/40 text-white/70 text-[11px] font-bold uppercase tracking-wider transition-colors"
          >
            Not now
          </button>
        </div>
      </div>
      <style>{`
        @keyframes slideInLeft {
          from { transform: translateX(-120%); opacity: 0; }
          to   { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
