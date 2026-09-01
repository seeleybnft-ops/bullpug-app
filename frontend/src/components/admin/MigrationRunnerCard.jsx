/**
 * MigrationRunnerCard — admin panel card for triggering the Phase A
 * wallet→user_id backfill directly on the deployed backend (which is
 * wired to production Mongo when accessed via the prod admin panel).
 *
 * Three modes:
 *   • Dry run — count what would change, write nothing
 *   • Apply   — actually backfill; requires an explicit second click
 *   • Verify  — read-only audit of current state
 *
 * The endpoint is `require_admin_jwt`-gated and, for apply, requires
 * an explicit `confirm=YES` param the UI attaches only after the
 * user clicks the destructive-styled confirm button.
 */
import React, { useCallback, useState } from "react";
import { RefreshCw, Play, ShieldCheck, ClipboardCheck, AlertTriangle, Database } from "lucide-react";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";
import { toast } from "sonner";

const MODE_META = {
  dry_run: { label: "Dry run", icon: ClipboardCheck, color: "#00C2FF", accent: "rgba(0,194,255,0.12)" },
  apply:   { label: "Apply",   icon: Play,           color: "#FF6B6B", accent: "rgba(255,107,107,0.12)" },
  verify:  { label: "Verify",  icon: ShieldCheck,    color: "#00FFA3", accent: "rgba(0,255,163,0.12)" },
};

export default function MigrationRunnerCard() {
  const { authFetch } = useSiwsAdmin();
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(null);   // "dry_run" | "apply" | "verify"
  const [error, setError] = useState(null);
  const [confirmingApply, setConfirmingApply] = useState(false);

  const run = useCallback(async (mode) => {
    setBusy(mode);
    setError(null);
    try {
      const qs = mode === "apply" ? "?mode=apply&confirm=YES" : `?mode=${mode}`;
      const { data } = await authFetch(`/admin/run-migration${qs}`, { method: "POST" });
      setReport(data);
      const t = data.totals || {};
      if (mode === "verify") {
        toast.success(data.clean ? "Audit clean — no missing user_id" : `Audit shows ${data.audit.still_missing_user_id_total} holes`);
      } else if (mode === "dry_run") {
        toast.success(`Dry run: would write ${t.docs_written || 0} docs, upsert ${t.wallets_new || 0} users`);
      } else {
        toast.success(`Applied: ${t.docs_written || 0} docs written, ${t.wallets_new || 0} users upserted`);
      }
      if (mode === "apply") setConfirmingApply(false);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Migration call failed";
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(null);
    }
  }, [authFetch]);

  const a = report?.audit;

  return (
    <div className="glass-card rounded-xl p-5" data-testid="admin-migration-card">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Database className="w-4 h-4 text-[#B47CFF]" />
        <h3
          className="text-sm font-bold uppercase tracking-widest text-[#B47CFF]"
          style={{ fontFamily: "Orbitron, sans-serif" }}
        >
          Phase A · Wallet → user_id Migration
        </h3>
      </div>

      <p className="text-xs text-slate-400 leading-relaxed mb-4">
        Backfills a <code className="text-slate-300 bg-white/5 px-1 py-0.5 rounded text-[10px]">user_id</code> field
        onto every existing Archive doc that carries a wallet, and
        upserts a <code className="text-slate-300 bg-white/5 px-1 py-0.5 rounded text-[10px]">users</code> row per
        distinct wallet. Additive, idempotent, safe to re-run.
      </p>

      {/* Action row */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {["dry_run", "verify", "apply"].map((m) => {
          const meta = MODE_META[m];
          const Icon = meta.icon;
          const isBusy = busy === m;
          const isApplyConfirming = m === "apply" && confirmingApply;
          const onClick = () => {
            if (m === "apply" && !confirmingApply) {
              setConfirmingApply(true);
              return;
            }
            run(m);
          };
          return (
            <button
              key={m}
              type="button"
              onClick={onClick}
              disabled={!!busy}
              data-testid={`admin-migration-${m}-btn`}
              className="inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg font-bold uppercase tracking-widest text-[11px] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                background: isApplyConfirming ? meta.color : meta.accent,
                border: `1px solid ${meta.color}${isApplyConfirming ? "" : "55"}`,
                color: isApplyConfirming ? "#0a0a12" : meta.color,
                fontFamily: "Orbitron, sans-serif",
              }}
            >
              {isBusy ? <RefreshCw size={12} className="animate-spin" /> : <Icon size={12} />}
              {isApplyConfirming ? "Confirm" : meta.label}
            </button>
          );
        })}
      </div>

      {confirmingApply && (
        <div
          className="rounded-lg p-3 mb-4 text-xs text-[#FF6B6B] flex items-start gap-2"
          style={{ background: "rgba(255,107,107,0.08)", border: "1px solid rgba(255,107,107,0.3)" }}
        >
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-bold mb-1">Confirm mutation.</p>
            <p className="text-slate-300">This writes to the deployed backend's Mongo. Click <strong>Confirm</strong> to proceed, or any other button to cancel.</p>
            <button
              type="button"
              onClick={() => setConfirmingApply(false)}
              className="mt-2 text-[10px] uppercase tracking-widest text-slate-400 hover:text-white underline"
              data-testid="admin-migration-cancel-apply"
            >
              Cancel apply
            </button>
          </div>
        </div>
      )}

      {error && (
        <div
          className="rounded-lg p-3 mb-3 text-xs text-[#FF6B6B] flex items-start gap-2"
          style={{ background: "rgba(255,107,107,0.08)", border: "1px solid rgba(255,107,107,0.3)" }}
          data-testid="admin-migration-error"
        >
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Report */}
      {report && (
        <div className="space-y-3" data-testid="admin-migration-report">
          {/* Summary strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <SummaryTile label="Mode" value={report.mode} tint="#B47CFF" testid="admin-migration-mode" />
            <SummaryTile
              label="Docs written"
              value={report.totals?.docs_written ?? 0}
              tint="#00C2FF"
              testid="admin-migration-docs-written"
            />
            <SummaryTile
              label="Wallets upserted"
              value={report.totals?.wallets_new ?? 0}
              tint="#00FFA3"
              testid="admin-migration-wallets-new"
            />
            <SummaryTile
              label="Missing user_id"
              value={a?.still_missing_user_id_total ?? 0}
              tint={a?.still_missing_user_id_total === 0 ? "#00FFA3" : "#FF6B6B"}
              testid="admin-migration-holes"
            />
          </div>

          {/* Per-collection audit table */}
          {a?.rows && (
            <div
              className="rounded-lg border border-white/5 overflow-hidden"
              data-testid="admin-migration-audit-table"
            >
              <div className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-1.5 bg-white/[0.03] text-[9px] uppercase tracking-widest text-slate-500 font-bold">
                <span>Collection</span>
                <span className="text-right">Docs w/ wallet</span>
                <span className="text-right">Missing user_id</span>
              </div>
              <div className="max-h-56 overflow-y-auto">
                {a.rows.map((r) => (
                  <div
                    key={r.collection}
                    className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-1.5 text-[11px] border-b border-white/5 last:border-b-0"
                  >
                    <span className="text-slate-300 font-mono truncate">{r.collection}</span>
                    <span className="text-slate-400 text-right">{r.total_with_wallet}</span>
                    <span
                      className={`text-right font-bold ${r.still_missing_user_id === 0 ? "text-slate-500" : "text-[#FF6B6B]"}`}
                    >
                      {r.still_missing_user_id}
                    </span>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3 px-3 py-1.5 bg-white/[0.03] text-[10px] text-slate-400">
                <span>distinct wallets: <strong className="text-slate-200">{a.distinct_wallets}</strong></span>
                <span className="text-right">users rows: <strong className="text-slate-200">{a.users_rows_with_wallet}</strong></span>
              </div>
            </div>
          )}

          {/* Clean badge */}
          <div
            className="text-[10px] uppercase tracking-widest text-center py-1.5 rounded-full"
            style={{
              background: report.clean ? "rgba(0,255,163,0.08)" : "rgba(255,107,107,0.08)",
              color: report.clean ? "#00FFA3" : "#FF6B6B",
              border: `1px solid ${report.clean ? "rgba(0,255,163,0.35)" : "rgba(255,107,107,0.35)"}`,
              fontFamily: "Orbitron, sans-serif",
            }}
            data-testid="admin-migration-status"
          >
            {report.clean ? "✓ Audit clean" : `✗ ${a?.still_missing_user_id_total} document(s) still missing user_id`}
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryTile({ label, value, tint, testid }) {
  return (
    <div
      className="rounded-lg p-3 text-center"
      style={{ background: `${tint}14`, border: `1px solid ${tint}33` }}
      data-testid={testid}
    >
      <p className="text-[9px] uppercase tracking-widest text-slate-400">{label}</p>
      <p
        className="text-lg font-bold mt-0.5 break-all"
        style={{ color: tint, fontFamily: "Orbitron, sans-serif" }}
      >
        {value}
      </p>
    </div>
  );
}
