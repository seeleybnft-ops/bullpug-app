/**
 * AccountMergeModal — Phase C account consolidation UI.
 *
 * Presented when POST /auth/wallet/link returns `merge_required: true`,
 * meaning the wallet the email user is trying to link already has its
 * own separate `users` row from earlier wallet-only usage. The user
 * picks which record becomes the primary; everything from the other
 * row (archive unlocks, ranks, daily drops, chat turns, ...) is
 * transferred to the primary via POST /auth/merge.
 *
 * Design intent: "Keep email" is presented as the recommended default
 * — the email account carries a rehydratable identity (magic-link
 * recovery), whereas losing the wallet's private key would strand the
 * merged history if we kept the wallet as primary.
 */
import React, { useState } from "react";
import axios from "axios";
import { AlertTriangle, Loader2, Mail, Wallet, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function shortenWallet(w) {
  if (!w) return "";
  return `${w.slice(0, 4)}...${w.slice(-4)}`;
}

export default function AccountMergeModal({ mergeInfo, onDismiss, onSuccess }) {
  const { authHeaders, refreshEmailUser } = useAuth();
  const [choice, setChoice] = useState("email"); // "email" | "wallet"
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!mergeInfo) return null;

  const { email, wallet, wallet_user_id } = mergeInfo;

  const runMerge = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await axios.post(
        `${API}/auth/merge`,
        { keep: choice, wallet_user_id },
        { headers: authHeaders },
      );
      refreshEmailUser();
      // Prefer the parent's success handler (which surfaces the
      // keeper's-log strip). Fall back to onDismiss if no onSuccess
      // was provided.
      if (onSuccess) onSuccess();
      else onDismiss?.();
    } catch (e) {
      const detail = e?.response?.data?.detail || "could not merge accounts. try again shortly.";
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      data-testid="account-merge-modal"
    >
      <div
        className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0a0a12] shadow-2xl overflow-hidden"
      >
        <div className="p-4 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#B47CFF]" />
            <h3 className="font-bold text-white text-sm">Two records found</h3>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            data-testid="account-merge-dismiss"
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/5"
            disabled={submitting}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <p className="text-xs text-slate-400 leading-relaxed">
            This wallet already has its own Archive history from before you
            signed in with email. Pick which record should become the
            primary — everything from the other will be moved onto it, and
            nothing gets lost.
          </p>

          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setChoice("email")}
              data-testid="account-merge-choice-email"
              className={`w-full text-left rounded-xl border p-3 transition-all ${
                choice === "email"
                  ? "border-[#B47CFF] bg-[#B47CFF]/10"
                  : "border-white/10 bg-black/30 hover:border-white/20"
              }`}
              disabled={submitting}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4 text-[#B47CFF]" />
                  <span className="text-xs font-bold uppercase tracking-wider text-white">
                    Keep email
                  </span>
                </div>
                <span
                  className="text-[9px] uppercase tracking-widest text-[#00FFA3]"
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  recommended
                </span>
              </div>
              <p
                className="text-[11px] text-slate-300 truncate"
                style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
              >
                {email}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">
                Wallet's history is transferred onto this account.
              </p>
            </button>

            <button
              type="button"
              onClick={() => setChoice("wallet")}
              data-testid="account-merge-choice-wallet"
              className={`w-full text-left rounded-xl border p-3 transition-all ${
                choice === "wallet"
                  ? "border-[#9945FF] bg-[#9945FF]/10"
                  : "border-white/10 bg-black/30 hover:border-white/20"
              }`}
              disabled={submitting}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <Wallet className="w-4 h-4 text-[#9945FF]" />
                <span className="text-xs font-bold uppercase tracking-wider text-white">
                  Keep wallet
                </span>
              </div>
              <p
                className="text-[11px] text-slate-300"
                style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
              >
                {shortenWallet(wallet)}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">
                Your email login gets moved onto this wallet account.
              </p>
            </button>
          </div>

          {error && (
            <p className="text-[11px] text-[#FF6B6B]" data-testid="account-merge-error">
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onDismiss}
              disabled={submitting}
              className="flex-1 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest border border-white/10 text-slate-300 hover:bg-white/5 disabled:opacity-50"
              data-testid="account-merge-cancel"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={runMerge}
              disabled={submitting}
              data-testid="account-merge-confirm"
              className="flex-1 inline-flex items-center justify-center gap-2 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest disabled:opacity-50"
              style={{
                background: choice === "email" ? "#B47CFF" : "#9945FF",
                color: "#0a0a12",
                fontFamily: "Orbitron, sans-serif",
              }}
            >
              {submitting ? <Loader2 size={11} className="animate-spin" /> : null}
              Merge accounts
            </button>
          </div>

          <p className="text-[10px] text-slate-600 leading-relaxed">
            Both accounts stay signed in as one identity after this. Neither
            record is deleted — the discarded one is flagged as merged so
            support can trace it if needed.
          </p>
        </div>
      </div>
    </div>
  );
}
