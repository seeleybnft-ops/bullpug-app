import { useEffect, useMemo, useRef, useState } from "react";
import { Coins, Trophy, Wallet, TrendingUp, Clock, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const REFRESH_INTERVAL_MS = 30000;

// Light helper — format SOL with up to 4 decimals, trimmed
function fmtSol(n) {
  if (n === null || n === undefined) return "—";
  const v = Number(n);
  if (!Number.isFinite(v)) return "—";
  if (v === 0) return "0";
  if (v >= 1) return v.toFixed(3).replace(/\.?0+$/, "");
  return v.toFixed(6).replace(/\.?0+$/, "");
}

function fmtCountdown(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds <= 0) return "due now";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

/**
 * Admin-only live rollup of rake & jackpot health.
 *
 * Hits SIWS-protected `/api/admin/rake-summary` every 30s and visualises:
 *  - Current jackpot pool + payout countdown
 *  - Lifetime operator share (75% cut)
 *  - Lifetime jackpot contributed (25% cut + 100% of tips)
 *  - Lifetime jackpot paid out across N payout cycles
 *  - 24h / 7d rolling rake totals (coinflip vs pot)
 *  - On-chain operator wallet balance
 *  - Last payout details + top winner
 */
export default function RakeJackpotCard() {
  const { authFetch, isAdmin } = useSiwsAdmin();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const timerRef = useRef(null);

  // Stable fetcher — uses the SIWS hook's authFetch which auto-attaches
  // the Bearer token and handles 401 retries / token refresh.
  useEffect(() => {
    if (!isAdmin || !authFetch) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    // `authFetch` is axios under the hood — it resolves with `{status, data}`
    // and rejects on non-2xx. Treating it as fetch (`.ok` / `.json()`) made
    // every healthy 200 render as `Failed to load: HTTP 200`.
    authFetch(`${API}/admin/rake-summary`)
      .then((r) => {
        if (!cancelled) setData(r.data);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [authFetch, isAdmin, refreshTick]);

  // 30s auto-refresh
  useEffect(() => {
    if (!isAdmin) return;
    timerRef.current = setInterval(() => setRefreshTick((v) => v + 1), REFRESH_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [isAdmin]);

  const lifetime = data?.lifetime || {};
  const cycle = data?.current_cycle || {};
  const rake24h = data?.rake_24h || {};
  const rake7d = data?.rake_7d || {};

  // 24h vs 7d delta as a sanity bar (24h share of 7d rake)
  const dailyShareOf7d = useMemo(() => {
    const t7 = Number(rake7d.total_sol || 0);
    const t24 = Number(rake24h.total_sol || 0);
    if (t7 <= 0) return 0;
    return Math.min(100, Math.round((t24 / t7) * 100));
  }, [rake24h.total_sol, rake7d.total_sol]);

  if (!isAdmin) return null;

  return (
    <div className="rounded-xl border border-[#F5D300]/30 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] p-5 mb-6 shadow-[0_0_30px_rgba(245,211,0,0.12)]" data-testid="rake-jackpot-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-[#F5D300]" />
          <h2 className="text-lg font-bold tracking-tight text-white">Rake &amp; Jackpot</h2>
          {loading && (
            <Badge className="bg-[#00C2FF]/10 text-[#00C2FF] border-[#00C2FF]/30 text-[10px]">
              Refreshing…
            </Badge>
          )}
        </div>
        <button
          onClick={() => setRefreshTick((v) => v + 1)}
          className="p-1.5 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-colors"
          title="Refresh now"
          data-testid="rake-card-refresh-btn"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && (
        <div className="mb-3 p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300" data-testid="rake-card-error">
          {error}
        </div>
      )}

      {/* TOP ROW — operator wallet + current jackpot countdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500">
            <Wallet className="w-3 h-3" /> Operator Wallet (on-chain)
          </div>
          <div className="mt-1.5 text-2xl font-bold text-white" data-testid="rake-card-on-chain-balance">
            {fmtSol(data?.on_chain_balance_sol)} <span className="text-sm text-slate-400 font-normal">SOL</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono break-all">
            {data?.operator_wallet || "—"}
          </div>
        </div>

        <div className="rounded-lg border border-[#F5D300]/30 bg-[#F5D300]/[0.04] p-3">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-[#F5D300]/70">
            <Clock className="w-3 h-3" /> Current Jackpot · Next payout in
          </div>
          <div className="mt-1.5 flex items-baseline justify-between">
            <div className="text-2xl font-bold text-[#F5D300]" data-testid="rake-card-pool">
              {fmtSol(cycle.pool_sol)} <span className="text-sm text-slate-400 font-normal">SOL</span>
            </div>
            <div className="text-base font-bold text-white" data-testid="rake-card-countdown">
              {fmtCountdown(cycle.time_until_payout_seconds)}
            </div>
          </div>
        </div>
      </div>

      {/* MIDDLE ROW — lifetime split */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <Stat
          icon={<Coins className="w-3 h-3" />}
          label="Lifetime Operator (75%)"
          value={fmtSol(lifetime.operator_share_sol)}
          accent="#00FFA3"
          testid="rake-card-operator-share"
        />
        <Stat
          icon={<Trophy className="w-3 h-3" />}
          label="Lifetime Jackpot Pool (25% + Tips)"
          value={fmtSol(lifetime.jackpot_contributed_sol)}
          accent="#F5D300"
          testid="rake-card-jackpot-contributed"
        />
        <Stat
          icon={<TrendingUp className="w-3 h-3" />}
          label="Lifetime Jackpot Paid Out"
          value={fmtSol(lifetime.jackpot_paid_sol)}
          accent="#D946EF"
          testid="rake-card-jackpot-paid"
          sub={`${lifetime.payout_cycles || 0} cycles`}
        />
        <Stat
          icon={<Coins className="w-3 h-3" />}
          label="Lifetime Skin Revenue"
          value={fmtSol(lifetime.skin_revenue_sol)}
          accent="#00C2FF"
          testid="rake-card-skin-revenue"
          sub={`${lifetime.skin_count || 0} sold`}
        />
      </div>

      {/* BOTTOM ROW — rolling 24h / 7d */}
      <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">Rolling Rake</div>
          <div className="text-[10px] text-slate-400">24h is <span className="text-white font-bold">{dailyShareOf7d}%</span> of 7d</div>
        </div>
        <div className="h-1.5 rounded-full bg-white/5 overflow-hidden mb-3">
          <div className="h-full bg-gradient-to-r from-[#00FFA3] to-[#F5D300] transition-all" style={{ width: `${dailyShareOf7d}%` }} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <RangeStat
            label="Last 24h"
            total={rake24h.total_sol}
            coinflip={rake24h.coinflip_sol}
            pot={rake24h.pot_sol}
            testidPrefix="rake-card-24h"
          />
          <RangeStat
            label="Last 7d"
            total={rake7d.total_sol}
            coinflip={rake7d.coinflip_sol}
            pot={rake7d.pot_sol}
            testidPrefix="rake-card-7d"
          />
        </div>
      </div>

      {/* LAST PAYOUT — only shown if a cycle has actually happened */}
      {cycle.last_payout && (
        <div className="mt-4 rounded-lg border border-[#D946EF]/30 bg-[#D946EF]/[0.04] p-3" data-testid="rake-card-last-payout">
          <div className="text-[10px] uppercase tracking-wider text-[#D946EF]/80 mb-1">Last Payout</div>
          <div className="flex items-center justify-between text-sm">
            <div>
              <div className="font-bold text-white">
                {fmtSol(cycle.last_payout.total_paid_sol)} SOL
                <span className="text-slate-400 font-normal text-xs ml-2">to {cycle.last_payout.winner_count} winner(s)</span>
              </div>
              {cycle.last_payout.top_winner && (
                <div className="text-xs text-slate-400 mt-0.5">
                  Top: <span className="text-white font-medium">{cycle.last_payout.top_winner.display_name || "anonymous"}</span>
                  {" · "}{fmtSol(cycle.last_payout.top_winner.prize_sol)} SOL
                </div>
              )}
            </div>
            <div className="text-[10px] text-slate-500">
              {cycle.last_payout.payout_at && new Date(cycle.last_payout.payout_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ icon, label, value, sub, accent, testid }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3" data-testid={testid}>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500">
        <span style={{ color: accent }}>{icon}</span>
        {label}
      </div>
      <div className="mt-1.5 text-xl font-bold text-white">
        {value}
        <span className="text-xs text-slate-400 font-normal"> SOL</span>
      </div>
      {sub && <div className="text-[10px] text-slate-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function RangeStat({ label, total, coinflip, pot, testidPrefix }) {
  return (
    <div className="text-sm" data-testid={`${testidPrefix}-block`}>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">{label}</div>
      <div className="text-lg font-bold text-white" data-testid={`${testidPrefix}-total`}>
        {fmtSol(total)} <span className="text-xs text-slate-400 font-normal">SOL</span>
      </div>
      <div className="text-[10px] text-slate-400 mt-0.5 flex gap-3">
        <span>flip <span className="text-white">{fmtSol(coinflip)}</span></span>
        <span>pot <span className="text-white">{fmtSol(pot)}</span></span>
      </div>
    </div>
  );
}
