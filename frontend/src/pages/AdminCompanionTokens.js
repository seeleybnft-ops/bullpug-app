/**
 * AdminCompanionTokens — minimal management panel for physical companion tokens.
 *
 * Two operations:
 *   • List every token — value, claimed/unclaimed, wallet claimed, dates.
 *   • Generate a new unclaimed token (optionally attached to an order id + note).
 *
 * Order management, dropship integration, and payment linkage are
 * out-of-scope until the store ships. This is intentionally the
 * bare-minimum spec from Document 2.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Copy, Plus, RefreshCw, PawPrint, Search, Loader2 } from "lucide-react";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

const PAGE_SIZE = 50;

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function shorten(str, head = 4, tail = 4) {
  if (!str) return "";
  const s = String(str);
  return s.length <= head + tail + 1 ? s : `${s.slice(0, head)}…${s.slice(-tail)}`;
}

function CopyButton({ value, testid }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(value);
        setOk(true);
        setTimeout(() => setOk(false), 1400);
      }}
      data-testid={testid}
      className="inline-flex items-center gap-1 text-[10px] uppercase tracking-widest px-2 py-1 rounded border border-white/10 hover:border-white/25 text-slate-300 hover:text-white transition-colors"
      style={{ fontFamily: "Orbitron, sans-serif" }}
    >
      <Copy size={10} />
      {ok ? "copied" : "copy"}
    </button>
  );
}

export default function AdminCompanionTokens() {
  const { authFetch } = useSiwsAdmin();
  const [tokens, setTokens] = useState([]);
  const [counts, setCounts] = useState({ claimed: 0, unclaimed: 0 });
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [filter, setFilter] = useState("all"); // all | claimed | unclaimed
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [lastGenerated, setLastGenerated] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");

  // Where the token can be redeemed from. Kept as a runtime var so it
  // works both in preview + prod.
  const claimUrl = (t) =>
    `${window.location.origin}/companion?key=${encodeURIComponent(t)}`;

  const load = useCallback(
    async (mode = "reset") => {
      setLoading(true);
      setError(null);
      const nextSkip = mode === "reset" ? 0 : skip;
      try {
        const params = new URLSearchParams({
          limit: String(PAGE_SIZE),
          skip: String(nextSkip),
        });
        if (filter !== "all") params.set("status", filter);
        const { data } = await authFetch(`/admin/companions/tokens?${params}`);
        setTokens((prev) =>
          mode === "reset" ? data.tokens || [] : [...prev, ...(data.tokens || [])]
        );
        setTotal(data.total || 0);
        setCounts(data.counts || { claimed: 0, unclaimed: 0 });
        setSkip(nextSkip + (data.tokens || []).length);
      } catch (e) {
        setError(e?.response?.data?.detail || e?.message || "Failed to load tokens");
      } finally {
        setLoading(false);
      }
    },
    [authFetch, filter, skip]
  );

  // Initial + when filter changes
  useEffect(() => {
    load("reset");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const generate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const { data } = await authFetch("/admin/companions/tokens", {
        method: "POST",
        data: {}, // no order_id or note for now — spec is minimal
      });
      setLastGenerated(data.token);
      // Push into the top of the list without a full refetch
      setTokens((prev) => [
        {
          token: data.token,
          order_id: null,
          wallet_claimed: null,
          claimed_at: null,
          created_at: data.created_at,
          note: null,
        },
        ...prev,
      ]);
      setCounts((c) => ({ ...c, unclaimed: c.unclaimed + 1 }));
      setTotal((t) => t + 1);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Generate failed");
    } finally {
      setGenerating(false);
    }
  };

  const filtered = query
    ? tokens.filter(
        (t) =>
          (t.token || "").includes(query) ||
          (t.wallet_claimed || "").includes(query) ||
          (t.order_id || "").includes(query)
      )
    : tokens;

  return (
    <div className="min-h-[calc(100vh-4rem)] px-4 pt-8 pb-16" data-testid="admin-companion-tokens">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div
              className="w-11 h-11 rounded-xl flex items-center justify-center"
              style={{
                background:
                  "radial-gradient(circle at 35% 30%, #F5D300 0%, #C9A200 60%, #715c00 100%)",
                boxShadow: "0 0 20px rgba(245,211,0,0.35)",
              }}
            >
              <PawPrint size={20} strokeWidth={2.4} style={{ color: "#0a0a12" }} />
            </div>
            <div>
              <p
                className="text-[10px] uppercase tracking-[0.28em] text-yellow-300/80"
                style={{ fontFamily: "Orbitron, sans-serif" }}
              >
                Admin · Physical Companions
              </p>
              <h1
                className="text-xl font-bold text-white"
                style={{ fontFamily: "Orbitron, sans-serif" }}
              >
                Companion Tokens
              </h1>
            </div>
          </div>
          <button
            type="button"
            onClick={generate}
            disabled={generating}
            data-testid="companion-generate-btn"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-[11px] font-bold uppercase tracking-widest disabled:opacity-50"
            style={{
              background: "#F5D300",
              color: "#0a0a12",
              fontFamily: "Orbitron, sans-serif",
              boxShadow: "0 0 20px rgba(245,211,0,0.35)",
            }}
          >
            {generating ? <Loader2 className="animate-spin" size={13} /> : <Plus size={13} />}
            Generate token
          </button>
        </div>

        {/* Just-generated banner */}
        {lastGenerated && (
          <div
            className="mb-5 rounded-xl p-4 flex items-center justify-between gap-4"
            style={{
              background: "rgba(245,211,0,0.06)",
              border: "1px solid rgba(245,211,0,0.35)",
            }}
            data-testid="companion-last-generated"
          >
            <div>
              <p className="text-[10px] uppercase tracking-widest text-yellow-300/80 mb-1" style={{ fontFamily: "Orbitron, sans-serif" }}>
                New token created
              </p>
              <p className="text-sm text-white font-mono break-all">{lastGenerated}</p>
              <p className="text-[11px] text-slate-400 mt-1">
                Redeem URL: <span className="text-slate-200">{claimUrl(lastGenerated)}</span>
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <CopyButton value={lastGenerated} testid="companion-copy-token-btn" />
              <CopyButton value={claimUrl(lastGenerated)} testid="companion-copy-url-btn" />
            </div>
          </div>
        )}

        {/* Filters + count */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-1 p-1 rounded-full bg-white/[0.03] border border-white/[0.06]">
            {[
              { id: "all", label: `All · ${total}` },
              { id: "unclaimed", label: `Unclaimed · ${counts.unclaimed}` },
              { id: "claimed", label: `Claimed · ${counts.claimed}` },
            ].map((tab) => {
              const active = filter === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setFilter(tab.id)}
                  data-testid={`companion-filter-${tab.id}`}
                  className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all ${
                    active ? "text-black" : "text-slate-400 hover:text-white"
                  }`}
                  style={{
                    fontFamily: "Orbitron, sans-serif",
                    background: active ? "#F5D300" : "transparent",
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
          <div className="relative">
            <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value.trim())}
              data-testid="companion-search-input"
              placeholder="Search token / wallet / order"
              className="pl-8 pr-3 py-1.5 rounded-full bg-black/40 border border-white/10 focus:border-white/30 focus:outline-none text-xs text-white placeholder:text-slate-500 w-64"
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div
            className="mb-4 rounded-lg p-3 text-xs text-red-200"
            style={{ background: "rgba(255,0,0,0.06)", border: "1px solid rgba(255,80,80,0.35)" }}
            data-testid="companion-error-banner"
          >
            {error}
          </div>
        )}

        {/* Table */}
        <div
          className="rounded-xl overflow-hidden"
          style={{
            background: "rgba(10,15,30,0.55)",
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <div className="grid grid-cols-[minmax(140px,1.4fr)_minmax(120px,1.2fr)_minmax(120px,1fr)_minmax(120px,1fr)_auto] gap-3 px-4 py-2.5 text-[10px] uppercase tracking-widest text-slate-500 border-b border-white/5" style={{ fontFamily: "Orbitron, sans-serif" }}>
            <span>Token</span>
            <span>Claimed by</span>
            <span>Claimed at</span>
            <span>Created</span>
            <span className="text-right">Actions</span>
          </div>
          {loading && tokens.length === 0 ? (
            <div className="p-8 text-center text-[11px] uppercase tracking-widest text-slate-500" style={{ fontFamily: "monospace" }}>
              Loading tokens…
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center" data-testid="companion-empty">
              <p className="text-sm text-white/80 font-bold mb-1" style={{ fontFamily: "Orbitron, sans-serif" }}>
                No tokens yet
              </p>
              <p className="text-xs text-slate-400">
                Generate the first token to seed the system.
              </p>
            </div>
          ) : (
            filtered.map((t) => (
              <div
                key={t.token}
                className="grid grid-cols-[minmax(140px,1.4fr)_minmax(120px,1.2fr)_minmax(120px,1fr)_minmax(120px,1fr)_auto] gap-3 px-4 py-3 text-xs items-center border-b border-white/5 last:border-b-0 hover:bg-white/[0.02]"
                data-testid={`companion-row-${t.token}`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                      t.wallet_claimed ? "" : "animate-pulse"
                    }`}
                    style={{
                      background: t.wallet_claimed ? "#22c55e" : "#F5D300",
                      boxShadow: t.wallet_claimed
                        ? "0 0 6px rgba(34,197,94,0.6)"
                        : "0 0 6px rgba(245,211,0,0.6)",
                    }}
                  />
                  <span className="font-mono truncate text-white/90" title={t.token}>
                    {t.token}
                  </span>
                </div>
                <div className="font-mono text-slate-300 truncate" title={t.wallet_claimed || ""}>
                  {t.wallet_claimed ? shorten(t.wallet_claimed, 5, 5) : (
                    <span className="text-slate-600">—</span>
                  )}
                </div>
                <div className="text-slate-400">
                  {fmtDate(t.claimed_at)}
                </div>
                <div className="text-slate-400">
                  {fmtDate(t.created_at)}
                </div>
                <div className="flex items-center gap-1.5 justify-end">
                  <CopyButton value={t.token} testid={`companion-copy-token-${t.token}`} />
                  <CopyButton value={claimUrl(t.token)} testid={`companion-copy-url-${t.token}`} />
                </div>
              </div>
            ))
          )}
        </div>

        {/* Load more */}
        {tokens.length < total && !query && (
          <div className="text-center mt-4">
            <button
              type="button"
              onClick={() => load("append")}
              disabled={loading}
              data-testid="companion-load-more-btn"
              className="inline-flex items-center gap-2 text-[10px] uppercase tracking-widest px-4 py-2 rounded-full border border-white/10 hover:border-white/25 text-slate-300 hover:text-white transition-colors"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              {loading ? <Loader2 className="animate-spin" size={11} /> : <RefreshCw size={11} />}
              Load more · {total - tokens.length} left
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
