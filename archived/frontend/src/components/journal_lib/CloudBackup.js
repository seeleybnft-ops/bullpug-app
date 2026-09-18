/**
 * CloudBackup Component - Backup and restore trading history
 * Extracted from TradingJournal for better maintainability
 */

import { useState, useEffect } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { Button } from "@/components/ui/button";
import { Activity } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CloudBackup({ onRestore }) {
  const { publicKey, connected } = useWallet();
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (connected && publicKey) {
      fetchBackups();
    }
  }, [connected, publicKey]);

  const fetchBackups = async () => {
    if (!publicKey) return;
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/journal/backups/${publicKey.toBase58()}`);
      setBackups(data.backups);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const createBackup = async () => {
    if (!publicKey) return;
    setCreating(true);
    try {
      const { data } = await axios.post(`${API}/journal/backup`, {
        wallet_address: publicKey.toBase58()
      });
      toast.success(`Backup created! ${data.trade_count} trades saved.`);
      fetchBackups();
    } catch (e) {
      toast.error("Failed to create backup");
    }
    setCreating(false);
  };

  const restoreBackup = async (backupId) => {
    if (!publicKey) return;
    if (!window.confirm("Restore this backup? This will add trades that don't exist.")) return;
    try {
      const { data } = await axios.post(
        `${API}/journal/restore/${backupId}?wallet_address=${publicKey.toBase58()}`
      );
      toast.success(`Restored ${data.restored_count} trades!`);
      onRestore?.();
    } catch (e) {
      toast.error("Failed to restore backup");
    }
  };

  const deleteBackup = async (backupId) => {
    if (!publicKey) return;
    if (!window.confirm("Delete this backup?")) return;
    try {
      await axios.delete(`${API}/journal/backup/${backupId}?wallet_address=${publicKey.toBase58()}`);
      toast.success("Backup deleted");
      fetchBackups();
    } catch (e) {
      toast.error("Failed to delete backup");
    }
  };

  if (!connected) {
    return (
      <div className="glass-card rounded-xl p-10 text-center" data-testid="backup-connect-wallet">
        <Activity className="w-10 h-10 mx-auto mb-3 text-slate-700" />
        <p className="text-slate-500">Connect wallet to manage backups</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="cloud-backup">
      <div className="glass-card rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold uppercase text-[#D946EF]">Cloud Backup</h3>
            <p className="text-xs text-slate-500 mt-1">Your trades are automatically saved to MongoDB</p>
          </div>
          <Button
            onClick={createBackup}
            disabled={creating}
            className="bg-[#D946EF] text-white font-bold rounded-xl px-4"
            data-testid="create-backup-btn"
          >
            {creating ? "Creating..." : "Create Backup"}
          </Button>
        </div>

        <div className="p-4 rounded-lg bg-[#D946EF]/5 border border-[#D946EF]/20">
          <p className="text-xs text-slate-400">
            <strong className="text-[#D946EF]">How it works:</strong> Your trades are stored in the cloud and linked to your wallet address. 
            Create manual backups to save snapshots, and restore anytime to recover your trading history.
          </p>
        </div>
      </div>

      <div className="glass-card rounded-xl p-6">
        <h4 className="text-sm font-bold uppercase text-slate-400 mb-4">Your Backups</h4>
        
        {loading ? (
          <div className="text-center py-6">
            <Activity className="w-8 h-8 mx-auto mb-2 text-slate-600 animate-pulse" />
            <p className="text-slate-500 text-sm">Loading backups...</p>
          </div>
        ) : backups.length === 0 ? (
          <div className="text-center py-6">
            <Activity className="w-8 h-8 mx-auto mb-2 text-slate-700" />
            <p className="text-slate-600 text-sm">No backups yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {backups.map(backup => (
              <div 
                key={backup.id}
                className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5"
                data-testid={`backup-${backup.id}`}
              >
                <div>
                  <p className="text-sm font-bold text-white">{backup.trade_count} trades</p>
                  <p className="text-xs text-slate-500">
                    {new Date(backup.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => restoreBackup(backup.id)}
                    className="px-3 py-1.5 rounded-lg bg-[#00FFA3]/10 text-[#00FFA3] text-xs font-bold hover:bg-[#00FFA3]/20"
                    data-testid={`restore-${backup.id}`}
                  >
                    Restore
                  </button>
                  <button
                    onClick={() => deleteBackup(backup.id)}
                    className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs font-bold hover:bg-red-500/20"
                    data-testid={`delete-${backup.id}`}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
