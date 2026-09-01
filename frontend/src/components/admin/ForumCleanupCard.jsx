/**
 * ForumCleanupCard — admin panel card for deleting `TEST_`-prefixed
 * forum posts (tester artifacts from the automated test suite).
 *
 * Flow:
 *   1. On mount, GET /admin/forum/tester-preview → surface how many
 *      tester rows exist (posts + reply + like cascade).
 *   2. Admin clicks "Clear tester posts" → confirmation state.
 *   3. Second click confirms → POST /admin/forum/clear-testers.
 *   4. Success toast + refresh the preview so counts drop to zero.
 *
 * The backend endpoints are gated by `require_admin_jwt`, so
 * authenticated admin only.
 */
import React, { useCallback, useEffect, useState } from "react";
import { RefreshCw, Trash2, MessagesSquare, AlertTriangle, Check } from "lucide-react";
import useSiwsAdmin from "@/hooks/useSiwsAdmin";
import { toast } from "sonner";

export default function ForumCleanupCard() {
  const { authFetch, isAdmin } = useSiwsAdmin();
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await authFetch("/admin/forum/tester-preview");
      setPreview(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Failed to load preview");
    } finally {
      setLoading(false);
    }
  }, [authFetch, isAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  const doClear = async () => {
    setClearing(true);
    setError(null);
    try {
      const { data } = await authFetch("/admin/forum/clear-testers", { method: "POST" });
      toast.success(
        `Cleared ${data.deleted_posts} post${data.deleted_posts === 1 ? "" : "s"}` +
        (data.deleted_replies ? ` · ${data.deleted_replies} replies` : "") +
        (data.deleted_likes ? ` · ${data.deleted_likes} likes` : "")
      );
      setConfirming(false);
      await load();
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Cleanup failed";
      setError(msg);
      toast.error(msg);
    } finally {
      setClearing(false);
    }
  };

  const posts = preview?.posts || [];
  const postCount = preview?.post_count ?? 0;
  const replyCount = preview?.reply_count ?? 0;
  const likeCount = preview?.like_count ?? 0;
  const nothingToDo = !loading && postCount === 0;

  return (
    <div className="glass-card rounded-xl p-5" data-testid="admin-forum-cleanup-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <MessagesSquare className="w-4 h-4 text-[#FF6B6B]" />
          <h3
            className="text-sm font-bold uppercase tracking-widest text-[#FF6B6B]"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Forum Tester Cleanup
          </h3>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          data-testid="admin-forum-cleanup-refresh"
          className="text-[10px] uppercase tracking-widest text-slate-400 hover:text-white transition-colors disabled:opacity-50"
          style={{ fontFamily: "Orbitron, sans-serif" }}
        >
          <RefreshCw size={11} className={`inline mr-1 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <p className="text-xs text-slate-400 leading-relaxed mb-4">
        Removes any <code className="text-slate-300 bg-white/5 px-1 py-0.5 rounded text-[10px]">TEST_</code>-prefixed forum
        post (seeded by the automated QA suite) plus its cascading
        replies and likes. Idempotent — safe to run any time.
      </p>

      {/* Counts row */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: "rgba(255,107,107,0.08)", border: "1px solid rgba(255,107,107,0.25)" }}
          data-testid="admin-forum-cleanup-post-count"
        >
          <p className="text-[10px] uppercase tracking-widest text-slate-400">Posts</p>
          <p className="text-2xl font-bold text-white mt-1" style={{ fontFamily: "Orbitron, sans-serif" }}>
            {loading ? "…" : postCount}
          </p>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: "rgba(255,107,107,0.05)", border: "1px solid rgba(255,107,107,0.15)" }}
          data-testid="admin-forum-cleanup-reply-count"
        >
          <p className="text-[10px] uppercase tracking-widest text-slate-400">Replies</p>
          <p className="text-2xl font-bold text-white mt-1" style={{ fontFamily: "Orbitron, sans-serif" }}>
            {loading ? "…" : replyCount}
          </p>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: "rgba(255,107,107,0.05)", border: "1px solid rgba(255,107,107,0.15)" }}
          data-testid="admin-forum-cleanup-like-count"
        >
          <p className="text-[10px] uppercase tracking-widest text-slate-400">Likes</p>
          <p className="text-2xl font-bold text-white mt-1" style={{ fontFamily: "Orbitron, sans-serif" }}>
            {loading ? "…" : likeCount}
          </p>
        </div>
      </div>

      {/* Preview list (up to 5 rows) */}
      {posts.length > 0 && (
        <div
          className="rounded-lg overflow-hidden mb-4 border border-white/5"
          data-testid="admin-forum-cleanup-preview-list"
        >
          <div className="max-h-40 overflow-y-auto">
            {posts.slice(0, 8).map((p) => (
              <div
                key={p.id}
                className="flex items-center gap-3 px-3 py-2 text-xs border-b border-white/5 last:border-b-0"
                data-testid={`admin-forum-cleanup-row-${p.id}`}
              >
                <span
                  className="text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded-full shrink-0"
                  style={{
                    color: "#FF6B6B",
                    background: "rgba(255,107,107,0.08)",
                    border: "1px solid rgba(255,107,107,0.25)",
                  }}
                >
                  {p.category || "?"}
                </span>
                <span className="text-slate-200 truncate flex-1">{p.title || p.id}</span>
                <span className="text-slate-500 text-[10px] shrink-0">
                  {(p.created_at || "").slice(0, 10)}
                </span>
              </div>
            ))}
          </div>
          {posts.length > 8 && (
            <p className="text-[10px] text-slate-500 text-center py-1.5 bg-white/[0.02]">
              + {posts.length - 8} more…
            </p>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          className="rounded-lg p-3 mb-3 text-xs text-[#FF6B6B] flex items-start gap-2"
          style={{ background: "rgba(255,107,107,0.08)", border: "1px solid rgba(255,107,107,0.3)" }}
          data-testid="admin-forum-cleanup-error"
        >
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Action */}
      {nothingToDo ? (
        <p
          className="text-xs text-slate-500 flex items-center gap-2"
          data-testid="admin-forum-cleanup-empty"
        >
          <Check size={13} className="text-[#00FFA3]" />
          No tester posts detected — nothing to clean.
        </p>
      ) : !confirming ? (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          disabled={loading || clearing || postCount === 0}
          data-testid="admin-forum-cleanup-btn"
          className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-bold text-xs uppercase tracking-widest transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: "rgba(255,107,107,0.12)",
            border: "1px solid rgba(255,107,107,0.5)",
            color: "#FF6B6B",
            fontFamily: "Orbitron, sans-serif",
          }}
        >
          <Trash2 size={13} />
          Clear {postCount} tester post{postCount === 1 ? "" : "s"}
        </button>
      ) : (
        <div className="flex gap-2" data-testid="admin-forum-cleanup-confirm-row">
          <button
            type="button"
            onClick={() => setConfirming(false)}
            disabled={clearing}
            data-testid="admin-forum-cleanup-cancel"
            className="flex-1 px-4 py-2.5 rounded-lg font-bold text-xs uppercase tracking-widest text-slate-300 border border-white/10 hover:border-white/20 transition-colors disabled:opacity-40"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={doClear}
            disabled={clearing}
            data-testid="admin-forum-cleanup-confirm"
            className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-bold text-xs uppercase tracking-widest transition-all disabled:opacity-40"
            style={{
              background: "#FF6B6B",
              color: "#0a0a12",
              fontFamily: "Orbitron, sans-serif",
              boxShadow: "0 0 20px rgba(255,107,107,0.45)",
            }}
          >
            {clearing ? (
              <RefreshCw size={13} className="animate-spin" />
            ) : (
              <Trash2 size={13} />
            )}
            {clearing ? "Clearing…" : "Confirm delete"}
          </button>
        </div>
      )}
    </div>
  );
}
