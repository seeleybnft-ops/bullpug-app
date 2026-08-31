/**
 * AdminVisualCanon — admin panel for the Visual Canon Ledger.
 *
 * Every image the community has generated for a subject lives here.
 * Admins can:
 *   • Browse by status filter (all / canon / pending / retired)
 *   • Promote a pending entry to canon
 *   • Retire a canon entry
 *   • Replace the image on any entry (upload a file → base64)
 *
 * Talks to /api/archive/admin/canon/* via the admin JWT.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw, CheckCircle2, ArchiveIcon, Upload, X, Loader2, Image as ImageIcon } from "lucide-react";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";

const PAGE_SIZE = 24;

const STATUS_COLORS = {
  canon: "#00FFA3",
  admin_override: "#F5D300",
  pending: "#00C2FF",
  retired: "#94A3B8",
};

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      day: "numeric", month: "short", year: "numeric",
    });
  } catch {
    return iso;
  }
}

async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => {
      const result = String(fr.result || "");
      const comma = result.indexOf(",");
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    fr.onerror = () => reject(new Error("read failed"));
    fr.readAsDataURL(file);
  });
}

export default function AdminVisualCanon() {
  const { authFetch } = useSiwsAdmin();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [filter, setFilter] = useState("all"); // all | canon | pending | retired
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState({}); // subject_tag → "promoting" | "retiring" | "uploading"
  const [selected, setSelected] = useState(null);

  const load = useCallback(async (mode = "reset") => {
    setLoading(true);
    setError(null);
    const nextSkip = mode === "reset" ? 0 : skip;
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        skip: String(nextSkip),
      });
      if (filter !== "all") params.set("status", filter);
      const { data } = await authFetch(`/archive/admin/canon?${params}`);
      setItems((prev) => (mode === "reset" ? data.items || [] : [...prev, ...(data.items || [])]));
      setTotal(data.total || 0);
      setSkip(nextSkip + (data.items || []).length);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Failed to load Visual Canon");
    } finally {
      setLoading(false);
    }
  }, [authFetch, filter, skip]);

  useEffect(() => { load("reset"); /* eslint-disable-next-line */ }, [filter]);

  const promote = async (tag, imageB64 = null, mime = null) => {
    setBusy((b) => ({ ...b, [tag]: "promoting" }));
    try {
      const { data } = await authFetch("/archive/admin/canon/promote", {
        method: "POST",
        data: { subject_tag: tag, image_base64: imageB64, image_mime: mime },
      });
      setItems((prev) => prev.map((it) => (it.subject_tag === tag ? { ...it, ...data } : it)));
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Promote failed");
    } finally {
      setBusy((b) => { const x = { ...b }; delete x[tag]; return x; });
    }
  };

  const retire = async (tag) => {
    if (!window.confirm(`Retire "${tag}"? It stays in the DB but stops being used as reference.`)) return;
    setBusy((b) => ({ ...b, [tag]: "retiring" }));
    try {
      const { data } = await authFetch("/archive/admin/canon/retire", {
        method: "POST",
        data: { subject_tag: tag },
      });
      setItems((prev) => prev.map((it) => (it.subject_tag === tag ? { ...it, ...data, status: "retired" } : it)));
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Retire failed");
    } finally {
      setBusy((b) => { const x = { ...b }; delete x[tag]; return x; });
    }
  };

  const uploadRefs = useRef({});
  const onFilePicked = async (tag, file) => {
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setError("Image must be ≤ 2 MB");
      return;
    }
    setBusy((b) => ({ ...b, [tag]: "uploading" }));
    try {
      const b64 = await fileToBase64(file);
      await promote(tag, b64, file.type || "image/png");
    } catch (e) {
      setError(e?.message || "Upload failed");
      setBusy((b) => { const x = { ...b }; delete x[tag]; return x; });
    }
  };

  const canLoadMore = items.length < total;

  return (
    <div className="min-h-[calc(100vh-4rem)] px-4 pt-8 pb-16" data-testid="admin-visual-canon-page">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p
              className="text-[10px] uppercase tracking-[0.28em] text-[#00FFA3]/80"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              Admin · Visual Canon Ledger
            </p>
            <h1
              className="text-xl font-bold text-white"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              Canon Entries · {total}
            </h1>
          </div>
          <button
            type="button"
            onClick={() => load("reset")}
            data-testid="admin-canon-refresh"
            className="text-[10px] uppercase tracking-widest text-slate-400 hover:text-white transition-colors"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            <RefreshCw size={11} className={`inline mr-1 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-1 p-1 rounded-full bg-white/[0.03] border border-white/[0.06] w-fit mb-6">
          {[
            { id: "all", label: "All" },
            { id: "canon", label: "Canon" },
            { id: "pending", label: "Pending" },
            { id: "retired", label: "Retired" },
          ].map((tab) => {
            const active = filter === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilter(tab.id)}
                data-testid={`admin-canon-filter-${tab.id}`}
                className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all ${
                  active ? "text-black bg-[#00FFA3]" : "text-slate-400 hover:text-white"
                }`}
                style={{ fontFamily: "Orbitron, sans-serif" }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {error && (
          <div className="mb-4 rounded-lg p-3 text-xs text-red-200"
               style={{ background: "rgba(255,0,0,0.06)", border: "1px solid rgba(255,80,80,0.35)" }}>
            {error}
          </div>
        )}

        {loading && items.length === 0 ? (
          <p className="text-center text-[11px] tracking-widest text-slate-500 py-16">
            Loading canon…
          </p>
        ) : items.length === 0 ? (
          <div className="rounded-xl p-8 text-center"
               style={{ background: "rgba(10,15,30,0.55)", border: "1px dashed rgba(0,255,163,0.25)" }}
               data-testid="admin-canon-empty">
            <ImageIcon size={28} className="mx-auto mb-2 text-slate-500" />
            <p className="text-sm text-white/80 font-bold mb-1" style={{ fontFamily: "Orbitron, sans-serif" }}>
              No entries in this bucket
            </p>
            <p className="text-xs text-slate-400">
              Change the filter or let visitors ask Tinkerpug to seed new canon.
            </p>
          </div>
        ) : (
          <div className="grid gap-4"
               style={{ gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }}
               data-testid="admin-canon-grid">
            {items.map((it) => {
              const color = STATUS_COLORS[it.status] || "#94A3B8";
              const isBusy = !!busy[it.subject_tag];
              return (
                <div
                  key={it.subject_tag}
                  className="rounded-xl overflow-hidden flex flex-col"
                  style={{ background: "rgba(10,15,30,0.55)", border: `1px solid ${color}33` }}
                  data-testid={`admin-canon-card-${it.subject_tag}`}
                >
                  <button
                    type="button"
                    onClick={() => setSelected(it)}
                    className="relative aspect-video w-full overflow-hidden bg-black/50"
                  >
                    {it.image_base64 ? (
                      <img
                        src={`data:${it.image_mime || "image/png"};base64,${it.image_base64}`}
                        alt={it.subject_display || it.subject_tag}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-600">
                        <ImageIcon size={24} />
                      </div>
                    )}
                    <span
                      className="absolute top-2 left-2 px-2 py-0.5 text-[9px] uppercase tracking-widest rounded-full font-bold"
                      style={{
                        fontFamily: "Orbitron, sans-serif",
                        background: `${color}22`,
                        color,
                        border: `1px solid ${color}66`,
                      }}
                    >
                      {it.status}
                    </span>
                  </button>
                  <div className="p-3 flex-1 flex flex-col">
                    <p className="text-[10px] text-slate-500 font-mono truncate" title={it.subject_tag}>
                      {it.subject_tag}
                    </p>
                    <p className="text-xs text-white/90 truncate mb-2" title={it.subject_display}>
                      {it.subject_display || "—"}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 mb-3"
                         style={{ fontFamily: "monospace" }}>
                      <span>Req · {it.request_count ?? 0}</span>
                      <span>{fmtDate(it.promoted_at || it.created_at)}</span>
                    </div>
                    <div className="mt-auto flex flex-wrap gap-1.5">
                      {it.status === "pending" && (
                        <button
                          type="button"
                          onClick={() => promote(it.subject_tag)}
                          disabled={isBusy}
                          data-testid={`admin-canon-promote-${it.subject_tag}`}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-widest disabled:opacity-50"
                          style={{
                            background: "#00FFA3",
                            color: "#0a0a12",
                            fontFamily: "Orbitron, sans-serif",
                          }}
                        >
                          {busy[it.subject_tag] === "promoting" ? <Loader2 size={9} className="animate-spin" /> : <CheckCircle2 size={9} />}
                          Promote
                        </button>
                      )}
                      {(it.status === "canon" || it.status === "admin_override") && (
                        <button
                          type="button"
                          onClick={() => retire(it.subject_tag)}
                          disabled={isBusy}
                          data-testid={`admin-canon-retire-${it.subject_tag}`}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-widest disabled:opacity-50"
                          style={{
                            background: "rgba(255,255,255,0.05)",
                            color: "rgba(255,255,255,0.7)",
                            border: "1px solid rgba(255,255,255,0.15)",
                            fontFamily: "Orbitron, sans-serif",
                          }}
                        >
                          {busy[it.subject_tag] === "retiring" ? <Loader2 size={9} className="animate-spin" /> : <ArchiveIcon size={9} />}
                          Retire
                        </button>
                      )}
                      {it.status !== "retired" && (
                        <>
                          <input
                            type="file"
                            accept="image/*"
                            ref={(el) => { uploadRefs.current[it.subject_tag] = el; }}
                            onChange={(e) => onFilePicked(it.subject_tag, e.target.files?.[0])}
                            className="hidden"
                            data-testid={`admin-canon-file-${it.subject_tag}`}
                          />
                          <button
                            type="button"
                            onClick={() => uploadRefs.current[it.subject_tag]?.click()}
                            disabled={isBusy}
                            data-testid={`admin-canon-replace-${it.subject_tag}`}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-widest disabled:opacity-50"
                            style={{
                              background: "rgba(245,211,0,0.12)",
                              color: "#F5D300",
                              border: "1px solid rgba(245,211,0,0.4)",
                              fontFamily: "Orbitron, sans-serif",
                            }}
                          >
                            {busy[it.subject_tag] === "uploading" ? <Loader2 size={9} className="animate-spin" /> : <Upload size={9} />}
                            Replace
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {canLoadMore && (
          <div className="text-center mt-6">
            <button
              type="button"
              onClick={() => load("append")}
              disabled={loading}
              data-testid="admin-canon-load-more"
              className="inline-flex items-center gap-2 text-[10px] uppercase tracking-widest px-4 py-2 rounded-full border border-white/10 hover:border-white/25 text-slate-300 hover:text-white transition-colors"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              {loading ? <Loader2 className="animate-spin" size={11} /> : <RefreshCw size={11} />}
              Load more · {total - items.length} left
            </button>
          </div>
        )}
      </div>

      {selected && (
        <div
          className="fixed inset-0 z-[80] flex items-center justify-center p-4"
          style={{ background: "rgba(3,5,14,0.82)", backdropFilter: "blur(6px)" }}
          onClick={() => setSelected(null)}
          data-testid="admin-canon-lightbox"
        >
          <div
            className="relative max-w-4xl max-h-[90vh] rounded-2xl overflow-hidden"
            style={{ border: "1px solid rgba(0,255,163,0.35)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="absolute top-3 right-3 rounded-full p-1.5 text-slate-300 hover:text-white hover:bg-white/10 transition-colors z-10"
              style={{ background: "rgba(0,0,0,0.6)" }}
            >
              <X size={16} />
            </button>
            {selected.image_base64 && (
              <img
                src={`data:${selected.image_mime || "image/png"};base64,${selected.image_base64}`}
                alt={selected.subject_display || selected.subject_tag}
                className="w-full h-auto"
              />
            )}
            <div className="absolute bottom-0 inset-x-0 p-4"
                 style={{ background: "linear-gradient(0deg, rgba(3,5,14,0.85) 0%, transparent 100%)" }}>
              <p className="text-xs text-slate-400 font-mono">{selected.subject_tag}</p>
              <p className="text-base text-white font-bold" style={{ fontFamily: "Orbitron, sans-serif" }}>
                {selected.subject_display}
              </p>
              {selected.first_prompt && (
                <p className="text-[11px] italic text-slate-500 mt-1">
                  first prompt: "{selected.first_prompt.slice(0, 200)}"
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
