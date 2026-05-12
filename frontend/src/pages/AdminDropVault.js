import { useState, useEffect, useCallback } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import {
  Shield, Search, Download, ChevronLeft, ChevronRight,
  Calendar, Sparkles, RefreshCw, ImageOff, Eye,
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PAGE_SIZE = 24;

function shortKey(k) {
  if (!k) return "";
  if (k.length <= 18) return k;
  return `${k.slice(0, 8)}…${k.slice(-6)}`;
}

function formatWhen(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch (e) {
    return iso;
  }
}

// Drop card — loads its thumbnail lazily via a one-shot fetch when it scrolls
// into view. Keeps the listing payload tiny (metadata only).
function DropCard({ drop, adminWallet, onPreview }) {
  const [img, setImg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errored, setErrored] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const observer = new IntersectionObserver(
      async (entries) => {
        if (entries[0].isIntersecting && !img && !errored) {
          observer.disconnect();
          try {
            const { data } = await axios.get(`${API}/ai/daily-drops/admin/one`, {
              params: { admin_wallet: adminWallet, user_key: drop.user_key, date_utc: drop.date_utc },
            });
            if (!cancelled) {
              setImg(data.image_base64);
              setLoading(false);
            }
          } catch (e) {
            if (!cancelled) {
              setErrored(true);
              setLoading(false);
            }
          }
        }
      },
      { rootMargin: "200px" }
    );
    const el = document.getElementById(`drop-${drop.user_key}-${drop.date_utc}`);
    if (el) observer.observe(el);
    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [drop.user_key, drop.date_utc, adminWallet, img, errored]);

  const handleDownload = async () => {
    let dataUrl = img;
    if (!dataUrl) {
      try {
        const { data } = await axios.get(`${API}/ai/daily-drops/admin/one`, {
          params: { admin_wallet: adminWallet, user_key: drop.user_key, date_utc: drop.date_utc },
        });
        dataUrl = data.image_base64;
      } catch (e) {
        toast.error("Failed to fetch full image");
        return;
      }
    }
    const a = document.createElement("a");
    a.href = dataUrl;
    const safeTheme = (drop.theme || "drop").replace(/[^a-z0-9_-]+/gi, "_").slice(0, 40);
    a.download = `bullpug_${drop.date_utc}_${safeTheme}_${shortKey(drop.user_key)}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div
      id={`drop-${drop.user_key}-${drop.date_utc}`}
      className="group relative rounded-xl overflow-hidden border border-white/10 bg-black/40 hover:border-[#00FFA3]/40 transition-colors"
      data-testid="vault-drop-card"
    >
      <div className="relative aspect-square bg-black/60 flex items-center justify-center overflow-hidden">
        {loading && !errored && (
          <RefreshCw className="w-6 h-6 text-slate-500 animate-spin" />
        )}
        {errored && (
          <div className="flex flex-col items-center text-slate-500">
            <ImageOff className="w-6 h-6 mb-1" />
            <span className="text-[10px]">Failed</span>
          </div>
        )}
        {img && (
          <img
            src={img}
            alt={drop.theme || "Bullpug Drop"}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 cursor-zoom-in"
            onClick={() => onPreview && onPreview({ ...drop, image_base64: img })}
          />
        )}
        <Badge
          className={`absolute top-2 left-2 text-[9px] uppercase tracking-wider ${
            drop.kind === "fresh"
              ? "bg-[#D946EF]/20 text-[#D946EF] border-[#D946EF]/40"
              : "bg-[#00FFA3]/20 text-[#00FFA3] border-[#00FFA3]/40"
          }`}
        >
          {drop.kind || "—"}
        </Badge>
        <Badge className="absolute top-2 right-2 text-[9px] uppercase tracking-wider bg-black/70 text-white border-white/15">
          {drop.date_utc}
        </Badge>
      </div>

      <div className="p-3 space-y-1.5">
        <p
          className="text-xs font-bold text-white tracking-tight line-clamp-1"
          style={{ fontFamily: "Orbitron, sans-serif" }}
          title={drop.theme}
        >
          {drop.theme || "Untitled"}
        </p>
        <p className="text-[10px] text-slate-400 line-clamp-2 leading-snug" title={drop.scene}>
          {drop.scene}
        </p>
        <div className="flex items-center justify-between pt-1.5">
          <span className="text-[9px] uppercase tracking-wider text-slate-500" title={drop.user_key}>
            {shortKey(drop.user_key)}
          </span>
          <span className="text-[9px] text-slate-600">{formatWhen(drop.created_at)}</span>
        </div>
        <div className="flex items-center gap-1.5 pt-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onPreview && onPreview({ ...drop, image_base64: img })}
            disabled={!img}
            className="flex-1 h-7 text-[10px] border-white/15 hover:bg-white/5"
            data-testid="vault-preview-btn"
          >
            <Eye className="w-3 h-3 mr-1" />
            View
          </Button>
          <Button
            size="sm"
            onClick={handleDownload}
            className="flex-1 h-7 text-[10px] bg-[#00FFA3] hover:bg-[#00FFA3]/90 text-black font-bold"
            data-testid="vault-download-btn"
          >
            <Download className="w-3 h-3 mr-1" />
            PNG
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function AdminDropVault() {
  const { publicKey, connected } = useWallet();
  const [search, setSearch] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [drops, setDrops] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [previewDrop, setPreviewDrop] = useState(null);
  const [error, setError] = useState(null);

  const adminWallet = publicKey ? publicKey.toBase58() : null;

  const loadDrops = useCallback(async () => {
    if (!adminWallet) return;
    setLoading(true);
    setError(null);
    try {
      const params = { admin_wallet: adminWallet, limit: PAGE_SIZE, offset };
      if (dateFilter) params.date_utc = dateFilter;
      const { data } = await axios.get(`${API}/ai/daily-drops/admin`, { params });
      setDrops(data.drops || []);
      setTotal(data.total || 0);
    } catch (e) {
      if (e.response?.status === 403) {
        setError("This wallet is not authorised to view the Vault.");
      } else {
        setError(e.response?.data?.detail || e.message);
      }
      setDrops([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [adminWallet, offset, dateFilter]);

  useEffect(() => {
    if (adminWallet) loadDrops();
  }, [adminWallet, loadDrops]);

  const filtered = drops.filter((d) => {
    if (!search.trim()) return true;
    const s = search.toLowerCase();
    return (
      (d.theme || "").toLowerCase().includes(s) ||
      (d.scene || "").toLowerCase().includes(s) ||
      (d.user_key || "").toLowerCase().includes(s)
    );
  });

  if (!connected) {
    return (
      <div className="min-h-screen pt-24 px-6 flex items-center justify-center" data-testid="vault-connect-prompt">
        <div className="text-center max-w-md">
          <Shield className="w-12 h-12 text-[#00FFA3] mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: "Orbitron, sans-serif" }}>
            Bullpug Vault
          </h1>
          <p className="text-slate-400 text-sm">
            Connect your admin wallet to view every Daily Drop ever generated.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-16 px-4 md:px-8" data-testid="vault-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F5D300]/10 border border-[#F5D300]/30 text-[#F5D300] text-[10px] font-bold uppercase tracking-wider mb-2">
              <Sparkles className="w-3 h-3" />
              Creator Vault
            </div>
            <h1
              className="text-3xl md:text-4xl font-black tracking-tighter text-white"
              style={{ fontFamily: "Orbitron, sans-serif" }}
            >
              Bullpug{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00FFA3] via-[#D946EF] to-[#FFD700]">
                Drop Vault
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Every Daily Drop ever generated · {total} on record
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => { setOffset(0); loadDrops(); }}
            disabled={loading}
            className="border-white/15 hover:bg-white/5"
            data-testid="vault-refresh-btn"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search theme, scene, or wallet…"
              className="pl-10 bg-black/40 border-white/10 text-white"
              data-testid="vault-search-input"
            />
          </div>
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            <Input
              type="date"
              value={dateFilter}
              onChange={(e) => { setDateFilter(e.target.value); setOffset(0); }}
              className="pl-10 bg-black/40 border-white/10 text-white md:w-48"
              data-testid="vault-date-filter"
            />
          </div>
          {(search || dateFilter) && (
            <Button
              variant="ghost"
              onClick={() => { setSearch(""); setDateFilter(""); setOffset(0); }}
              className="text-slate-400 hover:text-white"
              data-testid="vault-clear-filters"
            >
              Clear
            </Button>
          )}
        </div>

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-center mb-6" data-testid="vault-error">
            <p className="text-red-400 font-medium">{error}</p>
          </div>
        )}

        {/* Grid */}
        {!error && (
          <>
            {loading && drops.length === 0 ? (
              <div className="text-center py-20 text-slate-500" data-testid="vault-loading">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3" />
                Loading drops…
              </div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-20 text-slate-500" data-testid="vault-empty">
                <ImageOff className="w-10 h-10 mx-auto mb-3 opacity-60" />
                No drops match your filters yet.
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                {filtered.map((drop) => (
                  <DropCard
                    key={`${drop.user_key}-${drop.date_utc}`}
                    drop={drop}
                    adminWallet={adminWallet}
                    onPreview={setPreviewDrop}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {total > PAGE_SIZE && (
              <div className="flex items-center justify-center gap-3 mt-8" data-testid="vault-pagination">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0 || loading}
                  className="border-white/15"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Prev
                </Button>
                <span className="text-xs text-slate-400">
                  {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={offset + PAGE_SIZE >= total || loading}
                  className="border-white/15"
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Preview modal */}
      {previewDrop && (
        <div
          className="fixed inset-0 z-[70] bg-black/90 backdrop-blur-md p-4 flex items-center justify-center"
          onClick={() => setPreviewDrop(null)}
          data-testid="vault-preview-modal"
        >
          <div
            className="relative max-w-5xl w-full max-h-[95vh] overflow-auto rounded-2xl border border-white/10 bg-[#0D0D15]"
            onClick={(e) => e.stopPropagation()}
          >
            {previewDrop.image_base64 ? (
              <img
                src={previewDrop.image_base64}
                alt={previewDrop.theme}
                className="w-full h-auto block"
              />
            ) : (
              <div className="aspect-square flex items-center justify-center text-slate-500">
                Loading…
              </div>
            )}
            <div className="p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex-1 min-w-[200px]">
                  <p className="text-[10px] uppercase tracking-wider text-[#F5D300] font-bold mb-1">
                    {previewDrop.kind} · {previewDrop.date_utc}
                  </p>
                  <h3
                    className="text-xl md:text-2xl font-black text-white tracking-tight"
                    style={{ fontFamily: "Orbitron, sans-serif" }}
                  >
                    {previewDrop.theme}
                  </h3>
                  <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                    {previewDrop.scene}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-3 font-mono break-all">
                    {previewDrop.user_key}
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => {
                    const a = document.createElement("a");
                    a.href = previewDrop.image_base64;
                    const safeTheme = (previewDrop.theme || "drop").replace(/[^a-z0-9_-]+/gi, "_").slice(0, 40);
                    a.download = `bullpug_${previewDrop.date_utc}_${safeTheme}.png`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                  }}
                  className="bg-[#00FFA3] hover:bg-[#00FFA3]/90 text-black font-bold"
                  data-testid="vault-preview-download"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download PNG
                </Button>
              </div>
            </div>
            <button
              onClick={() => setPreviewDrop(null)}
              className="absolute top-3 right-3 w-9 h-9 rounded-full bg-black/70 border border-white/15 text-white flex items-center justify-center hover:scale-110 transition-transform"
              aria-label="Close preview"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
