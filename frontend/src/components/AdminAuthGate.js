/**
 * AdminAuthGate — wraps an admin page and prompts the user to Sign-In
 * With Solana before showing it. Once signed in, the JWT is reused for
 * 12 h via localStorage + the `useSiwsAdmin` hook.
 *
 * Usage:
 *   <AdminAuthGate>
 *     <AdminPanelInner />
 *   </AdminAuthGate>
 *
 * Children only render when `isAdmin` is true. If the connected wallet
 * isn't on the allow-list, the user sees an error message and can't
 * proceed.
 */

import { Shield, KeyRound, LogOut, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { useWallet } from "@solana/wallet-adapter-react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

export default function AdminAuthGate({ children, title = "Admin Console" }) {
  const { connected, publicKey } = useWallet();
  const { isAdmin, wallet, loading, error, loginAdmin, logoutAdmin, expiresAt } = useSiwsAdmin();

  if (isAdmin) {
    const expiresIn = expiresAt
      ? Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 60000))
      : null;
    return (
      <div className="relative" data-testid="admin-auth-gate-authorized">
        {/* Small persistent header so admins can sign out */}
        <div className="sticky top-16 z-30 bg-gradient-to-r from-emerald-500/10 via-transparent to-transparent border-y border-emerald-500/20 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-4 py-2 flex items-center justify-between text-xs">
            <span className="inline-flex items-center gap-2 text-emerald-400 font-bold uppercase tracking-wider">
              <CheckCircle className="w-3.5 h-3.5" />
              SIWS · Admin authorized
              {wallet && (
                <span className="text-slate-400 font-mono normal-case tracking-normal">
                  · {wallet.slice(0, 4)}...{wallet.slice(-4)}
                </span>
              )}
              {expiresIn != null && (
                <span className="text-slate-500 normal-case tracking-normal">
                  · {expiresIn}m left
                </span>
              )}
            </span>
            <button
              type="button"
              onClick={logoutAdmin}
              data-testid="admin-auth-logout"
              className="inline-flex items-center gap-1.5 text-slate-400 hover:text-white transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign out
            </button>
          </div>
        </div>
        {children}
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" data-testid="admin-auth-gate">
      <div className="w-full max-w-md rounded-2xl border border-[#D946EF]/30 bg-gradient-to-br from-[#120819] via-[#0a0612] to-[#1a0810] p-8 backdrop-blur-md">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center shadow-[0_0_24px_rgba(217,70,239,0.4)]">
            <Shield className="w-5 h-5 text-black" strokeWidth={2.5} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.25em] text-[#D946EF] font-bold" style={{ fontFamily: "Orbitron" }}>
              Sign-In With Solana
            </div>
            <h1 className="text-xl font-black text-white" style={{ fontFamily: "Orbitron" }}>{title}</h1>
          </div>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed mb-6">
          Admin pages are gated by an ed25519 signature from an allow-listed wallet. You'll be asked to sign a message — <span className="text-white font-semibold">no funds move</span>, no transaction is broadcast. The resulting session lasts 12 hours.
        </p>

        {!connected ? (
          <>
            <p className="text-[11px] text-slate-500 mb-2">Step 1 of 2 · connect your wallet</p>
            <WalletMultiButton className="!w-full !rounded-full !bg-gradient-to-r !from-[#D946EF] !to-[#00FFA3] !text-black !font-black !uppercase !tracking-wider" />
          </>
        ) : (
          <>
            <div className="rounded-lg bg-black/40 border border-white/10 px-3 py-2 mb-4 flex items-center justify-between text-xs">
              <span className="text-slate-400">Connected</span>
              <span className="text-white font-mono">{publicKey?.toBase58().slice(0, 4)}...{publicKey?.toBase58().slice(-4)}</span>
            </div>
            <button
              type="button"
              onClick={loginAdmin}
              disabled={loading}
              data-testid="admin-auth-sign-btn"
              className="w-full py-3 rounded-full bg-gradient-to-r from-[#D946EF] to-[#00FFA3] text-black font-black uppercase tracking-wider text-xs hover:scale-[1.02] transition-transform inline-flex items-center justify-center gap-2 disabled:opacity-50 disabled:hover:scale-100"
              style={{ fontFamily: "Orbitron" }}
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Awaiting signature...</>
              ) : (
                <><KeyRound className="w-4 h-4" /> Sign Admin Message</>
              )}
            </button>
            {error && (
              <div className="mt-4 flex items-start gap-2 text-[11px] text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg p-2.5" data-testid="admin-auth-error">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}
            <p className="text-[10px] text-slate-600 text-center mt-4 leading-relaxed">
              Domain: bullpug.app · Chain: mainnet-beta · Session: 12h
            </p>
          </>
        )}
      </div>
    </div>
  );
}
