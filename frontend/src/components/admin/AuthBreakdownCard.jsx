/**
 * AuthBreakdownCard — Phase C admin card.
 *
 * Shows totals by auth_type (email / wallet / linked), 24-hour signup
 * deltas, and OTP verification rate. Includes a small user lookup
 * search over email / wallet / user_id.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Users, RefreshCw, Search, AlertTriangle } from "lucide-react";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

export default function AuthBreakdownCard() {
  const { authFetch, isAdmin } = useSiwsAdmin();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);

  const load = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true); setError(null);
    try {
      const { data } = await authFetch("/admin/auth/breakdown");
      setData(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Failed to load");
    } finally { setLoading(false); }
  }, [authFetch, isAdmin]);

  useEffect(() => { load(); }, [load]);

  const search = async (e) => {
    e?.preventDefault?.();
    const q = query.trim();
    if (q.length < 3) return;
    setSearching(true);
    try {
      const { data } = await authFetch(`/admin/auth/lookup?q=${encodeURIComponent(q)}`);
      setResults(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Search failed");
    } finally { setSearching(false); }
  };

  const totals = data?.totals || { email: 0, wallet: 0, linked: 0 };
  const last24 = data?.last_24h || { email: 0, wallet: 0, linked: 0 };
  const rate = data?.email_verification_rate_24h ?? 0;

  return (
    <div className="glass-card rounded-xl p-5" data-testid="admin-auth-breakdown-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-[#00C2FF]" />
          <h3 className="text-sm font-bold uppercase tracking-widest text-[#00C2FF]"
              style={{ fontFamily: "Orbitron, sans-serif" }}>
            Auth Breakdown
          </h3>
        </div>
        <button type="button" onClick={load} disabled={loading}
                data-testid="admin-auth-refresh"
                className="text-[10px] uppercase tracking-widest text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                style={{ fontFamily: "Orbitron, sans-serif" }}>
          <RefreshCw size={11} className={`inline mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {/* Totals row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <Tile label="Email"  value={totals.email}  tint="#B47CFF" testid="auth-total-email" />
        <Tile label="Wallet" value={totals.wallet} tint="#00FFA3" testid="auth-total-wallet" />
        <Tile label="Linked" value={totals.linked} tint="#F5D300" testid="auth-total-linked" />
      </div>

      {/* 24h deltas */}
      <div className="rounded-lg border border-white/5 p-3 mb-3">
        <p className="text-[9px] uppercase tracking-widest text-slate-500 mb-2">New signups · last 24h</p>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div><span className="text-slate-500">Email</span>  <strong className="text-white ml-1">{last24.email}</strong></div>
          <div><span className="text-slate-500">Wallet</span> <strong className="text-white ml-1">{last24.wallet}</strong></div>
          <div><span className="text-slate-500">Linked</span> <strong className="text-white ml-1">{last24.linked}</strong></div>
        </div>
      </div>

      {/* OTP verification rate */}
      <div className="flex items-center justify-between text-xs mb-4 pb-3 border-b border-white/5">
        <span className="text-slate-400">OTP conversion (24h)</span>
        <span className="text-white font-bold">
          {data?.otp_verified_24h ?? 0} / {data?.otp_requested_24h ?? 0}
          <span className="text-slate-500 ml-2">({(rate * 100).toFixed(0)}%)</span>
        </span>
      </div>

      {/* Lookup */}
      <form onSubmit={search} className="flex gap-2 mb-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="email · wallet · user_id"
          data-testid="admin-auth-lookup-input"
          className="flex-1 min-w-0 rounded-lg px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-[#00C2FF]"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
        />
        <button type="submit" disabled={searching || query.trim().length < 3}
                data-testid="admin-auth-lookup-btn"
                className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest disabled:opacity-40"
                style={{ background: "#00C2FF", color: "#0a0a12", fontFamily: "Orbitron, sans-serif" }}>
          <Search size={11} /> Lookup
        </button>
      </form>

      {results && (
        <div className="rounded-lg border border-white/5 max-h-56 overflow-y-auto" data-testid="admin-auth-lookup-results">
          {results.matches.length === 0 ? (
            <p className="text-xs text-slate-500 p-3 text-center">no matches for that query.</p>
          ) : results.matches.map((r) => (
            <div key={r.user_id}
                 className="grid grid-cols-[1fr_auto] gap-2 px-3 py-2 text-[11px] border-b border-white/5 last:border-b-0">
              <div className="min-w-0">
                <div className="text-slate-200 truncate" style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
                  {r.email || r.wallet_address || r.user_id}
                </div>
                <div className="text-[10px] text-slate-500 truncate">{r.user_id}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-[9px] uppercase tracking-widest" style={{ color: r.auth_type === "linked" ? "#F5D300" : r.auth_type === "email" ? "#B47CFF" : "#00FFA3" }}>
                  {r.auth_type}
                </div>
                <div className="text-[10px] text-slate-500">{r.unlocked_count} unlocks</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg p-3 mt-3 text-xs text-[#FF6B6B] flex items-start gap-2"
             style={{ background: "rgba(255,107,107,0.08)", border: "1px solid rgba(255,107,107,0.3)" }}
             data-testid="admin-auth-error">
          <AlertTriangle size={13} className="shrink-0 mt-0.5" /> <span>{error}</span>
        </div>
      )}
    </div>
  );
}

function Tile({ label, value, tint, testid }) {
  return (
    <div className="rounded-lg p-3 text-center"
         style={{ background: `${tint}14`, border: `1px solid ${tint}33` }}
         data-testid={testid}>
      <p className="text-[9px] uppercase tracking-widest text-slate-400">{label}</p>
      <p className="text-2xl font-bold mt-0.5" style={{ color: tint, fontFamily: "Orbitron, sans-serif" }}>
        {value}
      </p>
    </div>
  );
}
