/**
 * PrivateAccessGate - Password gate for private testing period.
 * Remove this component from App.js when ready to go public.
 */

import { useState } from "react";
import { Lock, ArrowRight, Shield } from "lucide-react";

const ACCESS_KEY = "bullpug_private_access";
const VALID_HASH = "bullpug2026";

export default function PrivateAccessGate({ children }) {
  const [granted, setGranted] = useState(() => {
    try {
      return localStorage.getItem(ACCESS_KEY) === VALID_HASH;
    } catch {
      return false;
    }
  });
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);
  const [shaking, setShaking] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() === VALID_HASH) {
      localStorage.setItem(ACCESS_KEY, VALID_HASH);
      setGranted(true);
    } else {
      setError(true);
      setShaking(true);
      setTimeout(() => setShaking(false), 500);
      setTimeout(() => setError(false), 2000);
    }
  };

  if (granted) return children;

  return (
    <div className="min-h-screen bg-[#05050A] flex items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        {/* Lock Icon */}
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#D946EF]/20 to-[#00FFA3]/20 border border-white/10 flex items-center justify-center mx-auto mb-6">
          <Lock className="w-7 h-7 text-[#00FFA3]" />
        </div>

        <h1 className="text-2xl font-black mb-1 tracking-wide" style={{ fontFamily: 'Orbitron, sans-serif' }}>
          BULL<span className="text-[#00FFA3]">PUG</span>
        </h1>
        <p className="text-sm text-slate-500 mb-8">Private testing — enter access code</p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className={`relative ${shaking ? "animate-shake" : ""}`}>
            <input
              type="password"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Access code"
              autoFocus
              className={`w-full px-4 py-3 rounded-xl bg-white/5 border text-white placeholder-slate-600 text-center tracking-widest focus:outline-none focus:ring-2 transition-colors ${
                error
                  ? "border-red-500/50 focus:ring-red-500/30"
                  : "border-white/10 focus:ring-[#00FFA3]/30 focus:border-[#00FFA3]/30"
              }`}
              data-testid="access-code-input"
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 rounded-xl bg-gradient-to-r from-[#00FFA3] to-[#00C2FF] text-black font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
            data-testid="access-submit-btn"
          >
            Enter
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {error && (
          <p className="text-xs text-red-400 mt-3">Invalid access code</p>
        )}

        <div className="flex items-center justify-center gap-1.5 mt-8 text-[10px] text-slate-600">
          <Shield className="w-3 h-3" />
          Authorized testers only
        </div>
      </div>

      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-6px); }
          75% { transform: translateX(6px); }
        }
        .animate-shake { animation: shake 0.3s ease-in-out; }
      `}</style>
    </div>
  );
}
