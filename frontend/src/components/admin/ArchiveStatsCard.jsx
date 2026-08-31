/**
 * ArchiveStatsCard — admin panel card surfacing Archive engagement.
 *
 * Pulls `/api/archive/admin/stats` (admin-gated) and renders:
 *   • daily active wallets (last 24h)
 *   • rank distribution (Unranked / Seeker / Archivist / Keeper's Circle)
 *   • per-entry unlock counts, sorted most→least discovered
 *
 * Refresh: manual button + auto-refresh every 60s while mounted.
 */
import React, { useCallback, useEffect, useState } from "react";
import { RefreshCw, TrendingUp, TrendingDown, Activity, Users } from "lucide-react";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

const RANK_LABEL = {
  none: "Unranked",
  seeker: "Seeker",
  archivist: "Archivist",
  keepers_circle: "Keeper's Circle",
};
const RANK_COLOR = {
  none: "#94A3B8",
  seeker: "#00FFA3",
  archivist: "#B47CFF",
  keepers_circle: "#F5D300",
};
const TIER_COLOR = { 1: "#00FFA3", 2: "#B47CFF", 3: "#F5D300", special: "#F5D300" };

export default function ArchiveStatsCard() {
  const { authFetch } = useSiwsAdmin();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [entriesView, setEntriesView] = useState("top"); // top | bottom

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await authFetch("/archive/admin/stats");
      setStats(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Failed to load Archive stats");
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    load();
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [load]);

  const totalWallets = stats?.total_wallets ?? 0;
  const rankDist = stats?.rank_distribution || {};
  const dailyActive = stats?.daily_active_wallets ?? 0;
  const entries = stats?.entries || [];
  const sortedEntries = [...entries].sort((a, b) =>
    entriesView === "top"
      ? b.unlock_count - a.unlock_count
      : a.unlock_count - b.unlock_count
  );
  const shown = sortedEntries.slice(0, 10);

  return (
    <div className="glass-card rounded-xl p-5" data-testid="admin-archive-stats-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#00FFA3]" />
          <h3
            className="text-sm font-bold uppercase tracking-widest text-[#00FFA3]"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Archive Engagement
          </h3>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          data-testid="admin-archive-stats-refresh"
          className="text-[10px] uppercase tracking-widest text-slate-400 hover:text-white transition-colors disabled:opacity-50"
          style={{ fontFamily: "Orbitron, sans-serif" }}
        >
          <RefreshCw size={11} className={`inline mr-1 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg p-3 mb-3 text-xs text-red-200 border border-red-500/30 bg-red-500/5">
          {error}
        </div>
      )}

      {!stats ? (
        <p className="text-xs text-slate-500 text-center py-4">Loading engagement…</p>
      ) : (
        <>
          {/* Top-line metrics */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            <MetricCell
              icon={<Users size={14} />}
              label="Total Wallets"
              value={totalWallets}
              color="#00C2FF"
              testid="admin-stat-total-wallets"
            />
            <MetricCell
              icon={<Activity size={14} />}
              label="Active · 24h"
              value={dailyActive}
              color="#00FFA3"
              testid="admin-stat-daily-active"
            />
            <MetricCell
              label="Entries"
              value={`${stats.total_entries}${stats.grand_total_entries && stats.grand_total_entries !== stats.total_entries ? ` + ${stats.grand_total_entries - stats.total_entries}` : ""}`}
              color="#F5D300"
              testid="admin-stat-entries-total"
            />
          </div>

          {/* Rank distribution — horizontal stacked bar */}
          <div className="mb-5">
            <p
              className="text-[10px] uppercase tracking-[0.28em] text-slate-500 mb-2"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              Rank Distribution
            </p>
            <div
              className="flex w-full h-3 rounded-full overflow-hidden bg-white/[0.03]"
              data-testid="admin-rank-dist-bar"
            >
              {["none", "seeker", "archivist", "keepers_circle"].map((k) => {
                const count = rankDist[k] || 0;
                const pct = totalWallets ? (count / totalWallets) * 100 : 0;
                if (!pct) return null;
                return (
                  <div
                    key={k}
                    style={{ width: `${pct}%`, background: RANK_COLOR[k], boxShadow: `0 0 6px ${RANK_COLOR[k]}66` }}
                    title={`${RANK_LABEL[k]}: ${count}`}
                  />
                );
              })}
            </div>
            <div className="flex flex-wrap gap-3 mt-2">
              {["none", "seeker", "archivist", "keepers_circle"].map((k) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1.5 text-[10px]"
                  style={{ fontFamily: "monospace" }}
                  data-testid={`admin-rank-count-${k}`}
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ background: RANK_COLOR[k] }}
                  />
                  <span className="text-slate-400">{RANK_LABEL[k]}</span>
                  <span className="text-white font-bold">{rankDist[k] || 0}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Per-entry unlock counts */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p
                className="text-[10px] uppercase tracking-[0.28em] text-slate-500"
                style={{ fontFamily: "Orbitron, sans-serif" }}
              >
                Entries · {entriesView === "top" ? "Most" : "Least"} Discovered
              </p>
              <div className="flex items-center gap-1 p-0.5 rounded-full bg-white/[0.03] border border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => setEntriesView("top")}
                  data-testid="admin-entries-view-top"
                  className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-widest transition-all ${
                    entriesView === "top" ? "text-black bg-[#00FFA3]" : "text-slate-400 hover:text-white"
                  }`}
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  <TrendingUp size={9} className="inline mr-1" />
                  Top
                </button>
                <button
                  type="button"
                  onClick={() => setEntriesView("bottom")}
                  data-testid="admin-entries-view-bottom"
                  className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-widest transition-all ${
                    entriesView === "bottom" ? "text-black bg-[#F5D300]" : "text-slate-400 hover:text-white"
                  }`}
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  <TrendingDown size={9} className="inline mr-1" />
                  Bottom
                </button>
              </div>
            </div>
            <ul className="space-y-1" data-testid="admin-entries-list">
              {shown.map((e) => {
                const max = Math.max(1, ...entries.map((x) => x.unlock_count));
                const bar = (e.unlock_count / max) * 100;
                const color = TIER_COLOR[e.tier] || TIER_COLOR[1];
                return (
                  <li key={e.slug} className="flex items-center gap-2 text-xs">
                    <span
                      className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: color, boxShadow: `0 0 4px ${color}` }}
                    />
                    <span className="text-slate-300 flex-shrink-0 min-w-[110px] truncate" title={e.name}>
                      {e.name}
                    </span>
                    <div className="flex-1 h-1 rounded-full bg-white/[0.05] overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${bar}%`, background: color }}
                      />
                    </div>
                    <span
                      className="text-white/80 font-bold min-w-[28px] text-right"
                      style={{ fontFamily: "monospace" }}
                    >
                      {e.unlock_count}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}

function MetricCell({ icon, label, value, color, testid }) {
  return (
    <div
      className="rounded-lg p-3 text-center"
      style={{ background: `${color}0f`, border: `1px solid ${color}22` }}
      data-testid={testid}
    >
      <p
        className="text-[9px] uppercase tracking-[0.28em] text-slate-500 mb-1 flex items-center justify-center gap-1"
        style={{ fontFamily: "Orbitron, sans-serif" }}
      >
        {icon}
        {label}
      </p>
      <p
        className="text-2xl font-black"
        style={{ color, fontFamily: "Orbitron, sans-serif" }}
      >
        {value}
      </p>
    </div>
  );
}
