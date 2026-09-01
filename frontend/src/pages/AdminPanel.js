import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useWallet } from "@solana/wallet-adapter-react";
import axios from "axios";
import {
  Shield, AlertTriangle, Wallet, Sparkles, ExternalLink, PawPrint, Images
} from "lucide-react";
import ClientErrorsCard from "@/components/ClientErrorsCard";
import TrafficCard from "@/components/TrafficCard";
import TinkerpugChatsCard from "@/components/TinkerpugChatsCard";
import ArchiveStatsCard from "@/components/admin/ArchiveStatsCard";
import ForumCleanupCard from "@/components/admin/ForumCleanupCard";
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminPanel() {
  const { publicKey, connected } = useWallet();
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAdmin();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [publicKey, connected]);

  const checkAdmin = async () => {
    if (!connected || !publicKey) {
      setIsAdmin(false);
      setLoading(false);
      return;
    }
    try {
      const { data } = await axios.get(`${API}/admin/check/${publicKey.toBase58()}`);
      setIsAdmin(data.is_admin);
    } catch (e) {
      setIsAdmin(false);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="pt-20 pb-16 min-h-screen">
        <div className="stars-bg fixed inset-0 -z-10" />
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <Shield className="w-12 h-12 mx-auto mb-4 text-slate-600 animate-pulse" />
          <p className="text-slate-500">Checking admin access...</p>
        </div>
      </div>
    );
  }

  if (!connected) {
    return (
      <div className="pt-20 pb-16 min-h-screen">
        <div className="stars-bg fixed inset-0 -z-10" />
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <Wallet className="w-12 h-12 mx-auto mb-4 text-slate-600" />
          <p className="text-slate-400">Connect your wallet to access admin panel</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="pt-20 pb-16 min-h-screen">
        <div className="stars-bg fixed inset-0 -z-10" />
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <p className="text-xl font-bold text-red-400">Access Denied</p>
          <p className="text-slate-500 mt-2">Your wallet is not authorized for admin access</p>
          <p className="text-xs text-slate-600 mt-4">{publicKey?.toBase58()}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-black uppercase flex items-center gap-3" style={{ fontFamily: 'Orbitron' }}>
              <Shield className="text-red-500" /> Admin Panel
            </h1>
            <p className="text-slate-500 text-sm mt-1">Bullpug platform ops</p>
          </div>
        </div>

        {/* Quick-link: Bullpug Drop Vault */}
        <Link
          to="/admin/drops"
          data-testid="admin-vault-link"
          className="block mb-6 group"
        >
          <div className="rounded-2xl border border-[#F5D300]/30 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] p-5 hover:border-[#F5D300]/60 hover:shadow-[0_0_30px_rgba(245,211,0,0.15)] transition-all">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-[#F5D300]/10 border border-[#F5D300]/30 flex items-center justify-center shrink-0">
                  <Sparkles className="w-5 h-5 text-[#F5D300]" />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-[0.25em] text-[#F5D300] font-bold mb-0.5">
                    Creator Vault
                  </p>
                  <h3
                    className="text-base md:text-lg font-bold text-white tracking-tight"
                    style={{ fontFamily: "Orbitron, sans-serif" }}
                  >
                    Bullpug Drop Vault →
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Browse every AI-generated Daily Drop across the entire userbase.
                    Filter by date, theme, or wallet. Download in one click.
                  </p>
                </div>
              </div>
              <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-[#F5D300] group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          </div>
        </Link>

        {/* Quick-link: Companion Tokens */}
        <Link
          to="/admin/companions"
          data-testid="admin-companions-link"
          className="block mb-6 group"
        >
          <div className="rounded-2xl border border-[#F5D300]/30 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] p-5 hover:border-[#F5D300]/60 hover:shadow-[0_0_30px_rgba(245,211,0,0.15)] transition-all">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-[#F5D300]/10 border border-[#F5D300]/30 flex items-center justify-center shrink-0">
                  <PawPrint className="w-5 h-5 text-[#F5D300]" />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-[0.25em] text-[#F5D300] font-bold mb-0.5">
                    Physical Companions
                  </p>
                  <h3
                    className="text-base md:text-lg font-bold text-white tracking-tight"
                    style={{ fontFamily: "Orbitron, sans-serif" }}
                  >
                    Companion Tokens →
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Generate and manage the tokens that ship with each Bullpug plushie.
                    Each token unlocks the "Companion's Secret" Archive entry once claimed.
                  </p>
                </div>
              </div>
              <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-[#F5D300] group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          </div>
        </Link>

        {/* Quick-link: Visual Canon Ledger */}
        <Link
          to="/admin/canon"
          data-testid="admin-canon-link"
          className="block mb-6 group"
        >
          <div className="rounded-2xl border border-[#00FFA3]/30 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] p-5 hover:border-[#00FFA3]/60 hover:shadow-[0_0_30px_rgba(0,255,163,0.15)] transition-all">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-[#00FFA3]/10 border border-[#00FFA3]/30 flex items-center justify-center shrink-0">
                  <Images className="w-5 h-5 text-[#00FFA3]" />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-[0.25em] text-[#00FFA3] font-bold mb-0.5">
                    Universe Visuals
                  </p>
                  <h3
                    className="text-base md:text-lg font-bold text-white tracking-tight"
                    style={{ fontFamily: "Orbitron, sans-serif" }}
                  >
                    Visual Canon Ledger →
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Every image the community has generated for a subject. Promote pending
                    entries to canon, retire stale ones, or replace an image with a curated version.
                  </p>
                </div>
              </div>
              <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-[#00FFA3] group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          </div>
        </Link>

        {/* Platform ops cards — website health, chat sessions, traffic, archive stats */}
        <div className="space-y-6">
          <ArchiveStatsCard />
          <ForumCleanupCard />
          <ClientErrorsCard />
          <TrafficCard />
          <TinkerpugChatsCard />
        </div>
      </div>
    </div>
  );
}
