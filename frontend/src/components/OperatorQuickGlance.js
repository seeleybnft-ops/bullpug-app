import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Wallet } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const POLL_MS = 60000; // 60s — escrow doesn't change that fast

const STATUS = {
  healthy:  { dot: "#00FFA3", glow: "rgba(0,255,163,0.45)",  ring: "rgba(0,255,163,0.30)",  label: "Healthy" },
  ok:       { dot: "#F5D300", glow: "rgba(245,211,0,0.45)",  ring: "rgba(245,211,0,0.30)",  label: "OK" },
  low:      { dot: "#FB923C", glow: "rgba(251,146,60,0.55)", ring: "rgba(251,146,60,0.35)", label: "Low" },
  critical: { dot: "#EF4444", glow: "rgba(239,68,68,0.65)",  ring: "rgba(239,68,68,0.40)",  label: "Critical" },
  unknown:  { dot: "#64748B", glow: "rgba(100,116,139,0.35)", ring: "rgba(100,116,139,0.25)", label: "?" },
};

/**
 * Tiny admin-only navbar pill: coloured dot + free-capital amount, links to /admin.
 * Renders nothing if the connected wallet isn't an admin.
 *
 * Props:
 *   - adminWallet: string (the connected wallet base58)
 */
export default function OperatorQuickGlance({ adminWallet }) {
  const [data, setData] = useState(null);

  const fetchStatus = useCallback(async () => {
    if (!adminWallet) return;
    try {
      const res = await axios.get(`${API}/admin/escrow-status`, {
        params: { admin_wallet: adminWallet },
      });
      setData(res.data);
    } catch (e) {
      setData(null);
    }
  }, [adminWallet]);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, POLL_MS);
    return () => clearInterval(id);
  }, [fetchStatus]);

  if (!data) return null;
  const status = data?.headroom?.status || "unknown";
  const cfg = STATUS[status] || STATUS.unknown;
  const free = Number(data?.free_capital_sol || 0).toFixed(3);
  const pulse = status === "low" || status === "critical";

  return (
    <Link
      to="/admin"
      data-testid="operator-quick-glance"
      title={`Escrow ${cfg.label}\nFree capital: ${free} SOL\nOn-chain: ${Number(data?.balance_sol || 0).toFixed(4)} SOL\nClick for full breakdown`}
      className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/40 border hover:bg-black/60 transition-all"
      style={{ borderColor: cfg.ring }}
    >
      <span
        className={`relative inline-block w-2 h-2 rounded-full ${pulse ? "animate-pulse" : ""}`}
        style={{ background: cfg.dot, boxShadow: `0 0 6px ${cfg.glow}` }}
      />
      <Wallet className="w-3 h-3" style={{ color: cfg.dot }} />
      <span
        className="text-[10px] font-bold tracking-wider"
        style={{ fontFamily: "Orbitron, sans-serif", color: cfg.dot }}
      >
        {free}
      </span>
      <span className="text-[9px] text-slate-500 uppercase tracking-wider">SOL</span>
    </Link>
  );
}
