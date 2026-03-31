import { useState, useEffect, useCallback } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import axios from "axios";
import {
  Shield, Users, DollarSign, BarChart3, Trophy, AlertTriangle,
  RefreshCw, Play, Ban, Clock, Wallet, CheckCircle, XCircle, ArrowDownRight, ArrowUpRight,
  Activity
} from "lucide-react";
import BotHealthDashboard from "../components/admin/BotHealthDashboard";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminPanel() {
  const { publicKey, connected } = useWallet();
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [bets, setBets] = useState([]);
  const [escrow, setEscrow] = useState(null);
  const [reconciliation, setReconciliation] = useState(null);
  const [reconLoading, setReconLoading] = useState(false);

  useEffect(() => {
    checkAdmin();
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
      if (data.is_admin) {
        fetchDashboard();
      }
    } catch (e) {
      setIsAdmin(false);
    }
    setLoading(false);
  };

  const fetchReconciliation = useCallback(async () => {
    setReconLoading(true);
    try {
      const { data } = await axios.get(`${API}/ledger/admin/reconciliation`);
      setReconciliation(data);
    } catch (e) {
      toast.error("Failed to load reconciliation data");
    }
    setReconLoading(false);
  }, []);

  const fetchDashboard = async () => {
    if (!publicKey) return;
    try {
      const [dashRes, challengesRes, betsRes, escrowRes] = await Promise.all([
        axios.get(`${API}/admin/dashboard?admin_wallet=${publicKey.toBase58()}`),
        axios.get(`${API}/admin/challenges?admin_wallet=${publicKey.toBase58()}&limit=50`),
        axios.get(`${API}/admin/bets?admin_wallet=${publicKey.toBase58()}&limit=50`),
        axios.get(`${API}/admin/escrow?admin_wallet=${publicKey.toBase58()}`)
      ]);
      setDashboard(dashRes.data);
      setChallenges(challengesRes.data.challenges);
      setBets(betsRes.data.bets);
      setEscrow(escrowRes.data);
    } catch (e) {
      toast.error("Failed to load admin data");
    }
    fetchReconciliation();
  };

  const cancelChallenge = async (challengeId) => {
    if (!window.confirm("Cancel this challenge?")) return;
    try {
      await axios.post(`${API}/admin/challenge/cancel`, {
        admin_wallet: publicKey.toBase58(),
        challenge_id: challengeId,
        action: "cancel"
      });
      toast.success("Challenge cancelled");
      fetchDashboard();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to cancel");
    }
  };

  const drawPot = async () => {
    if (!window.confirm("Draw the pot now? This will select a winner.")) return;
    try {
      const { data } = await axios.post(`${API}/admin/pot/draw`, {
        admin_wallet: publicKey.toBase58()
      });
      toast.success(`Pot drawn! Winner: ${data.winner_name} (${data.payout_sol} SOL)`);
      fetchDashboard();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to draw pot");
    }
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
            <p className="text-slate-500 text-sm mt-1">Manage P2P betting and platform</p>
          </div>
          <Button onClick={fetchDashboard} variant="outline" className="border-white/20">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>

        {dashboard && (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
              <StatCard icon={<BarChart3 />} label="Total Bets" value={dashboard.total_bets} color="#00FFA3" />
              <StatCard icon={<Users />} label="Challenges" value={dashboard.total_challenges} color="#00C2FF" />
              <StatCard icon={<Clock />} label="Open" value={dashboard.open_challenges} color="#F5D300" />
              <StatCard icon={<Trophy />} label="Completed" value={dashboard.completed_challenges} color="#D946EF" />
              <StatCard icon={<DollarSign />} label="Rake (SOL)" value={dashboard.total_rake_collected_sol?.toFixed(4)} color="#00FFA3" />
              <StatCard icon={<Users />} label="Est. Users" value={dashboard.estimated_users} color="#00C2FF" />
            </div>

            {/* Current Pot */}
            <div className="glass-card rounded-xl p-6 mb-8">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold uppercase text-[#D946EF]">Current Pot</h3>
                  <p className="text-3xl font-black text-[#D946EF] mt-2" style={{ fontFamily: 'Orbitron' }}>
                    {dashboard.current_pot?.total_amount_sol || 0} SOL
                  </p>
                  <p className="text-xs text-slate-500">{dashboard.current_pot?.entry_count || 0} entries</p>
                </div>
                <Button 
                  onClick={drawPot}
                  disabled={dashboard.current_pot?.entry_count < 2}
                  className="bg-[#D946EF] text-white font-bold px-6"
                >
                  <Play className="w-4 h-4 mr-2" /> Draw Winner
                </Button>
              </div>
            </div>
          </>
        )}

        <Tabs defaultValue="bot-health">
          <TabsList className="bg-black/40 border border-white/10 rounded-xl p-1 mb-6">
            <TabsTrigger value="bot-health" className="data-[state=active]:bg-[#00C2FF]/10 data-[state=active]:text-[#00C2FF]">
              Bot Health
            </TabsTrigger>
            <TabsTrigger value="fund-health" className="data-[state=active]:bg-[#FFB800]/10 data-[state=active]:text-[#FFB800]">
              Fund Health
            </TabsTrigger>
            <TabsTrigger value="challenges" className="data-[state=active]:bg-[#00FFA3]/10 data-[state=active]:text-[#00FFA3]">
              Challenges
            </TabsTrigger>
            <TabsTrigger value="bets" className="data-[state=active]:bg-[#00C2FF]/10 data-[state=active]:text-[#00C2FF]">
              Bet History
            </TabsTrigger>
            <TabsTrigger value="escrow" className="data-[state=active]:bg-[#D946EF]/10 data-[state=active]:text-[#D946EF]">
              Escrow
            </TabsTrigger>
          </TabsList>

          <TabsContent value="bot-health">
            <BotHealthDashboard adminWallet={publicKey?.toBase58()} />
          </TabsContent>

          <TabsContent value="fund-health">
            <ReconciliationDashboard
              data={reconciliation}
              loading={reconLoading}
              onRefresh={fetchReconciliation}
            />
          </TabsContent>

          <TabsContent value="challenges">
            <div className="glass-card rounded-xl p-4">
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-slate-500 uppercase border-b border-white/10">
                    <th className="text-left p-3">ID</th>
                    <th className="text-left p-3">Creator</th>
                    <th className="text-left p-3">Amount</th>
                    <th className="text-left p-3">Choice</th>
                    <th className="text-left p-3">Status</th>
                    <th className="text-left p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {challenges.map(c => (
                    <tr key={c.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                      <td className="p-3 text-xs text-slate-400">{c.id.slice(0, 8)}...</td>
                      <td className="p-3 text-sm">{c.creator_name}</td>
                      <td className="p-3 text-sm text-[#00FFA3] font-bold">{c.bet_amount_sol} SOL</td>
                      <td className="p-3 text-sm">{c.creator_choice}</td>
                      <td className="p-3">
                        <Badge className={`text-[10px] ${
                          c.status === "open" ? "bg-amber-500/10 text-amber-400" :
                          c.status === "completed" ? "bg-[#00FFA3]/10 text-[#00FFA3]" :
                          "bg-slate-500/10 text-slate-400"
                        }`}>
                          {c.status}
                        </Badge>
                      </td>
                      <td className="p-3">
                        {c.status === "open" && (
                          <button 
                            onClick={() => cancelChallenge(c.id)}
                            className="text-xs text-red-400 hover:text-red-300"
                          >
                            <Ban size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="bets">
            <div className="glass-card rounded-xl p-4 max-h-[500px] overflow-y-auto">
              <table className="w-full">
                <thead className="sticky top-0 bg-[#0a0a12]">
                  <tr className="text-xs text-slate-500 uppercase border-b border-white/10">
                    <th className="text-left p-3">Time</th>
                    <th className="text-left p-3">Type</th>
                    <th className="text-left p-3">Amount</th>
                    <th className="text-left p-3">Outcome</th>
                    <th className="text-left p-3">Rake</th>
                  </tr>
                </thead>
                <tbody>
                  {bets.map((b, i) => (
                    <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                      <td className="p-3 text-xs text-slate-500">
                        {new Date(b.timestamp).toLocaleString()}
                      </td>
                      <td className="p-3 text-sm">{b.type}</td>
                      <td className="p-3 text-sm text-[#00FFA3]">{b.bet_amount_sol || b.total_pot_sol} SOL</td>
                      <td className="p-3 text-sm">{b.outcome}</td>
                      <td className="p-3 text-sm text-amber-400">{b.rake_sol} SOL</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="escrow">
            {escrow && (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="glass-card rounded-xl p-4 text-center">
                    <p className="text-xs text-slate-500 uppercase">Total Deposited</p>
                    <p className="text-2xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron' }}>
                      {escrow.total_deposited_sol} SOL
                    </p>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <p className="text-xs text-slate-500 uppercase">Total Withdrawn</p>
                    <p className="text-2xl font-black text-red-400" style={{ fontFamily: 'Orbitron' }}>
                      {escrow.total_withdrawn_sol} SOL
                    </p>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <p className="text-xs text-slate-500 uppercase">Escrow Balance</p>
                    <p className="text-2xl font-black text-[#00C2FF]" style={{ fontFamily: 'Orbitron' }}>
                      {escrow.escrow_balance_sol} SOL
                    </p>
                  </div>
                </div>

                <div className="glass-card rounded-xl p-4">
                  <h4 className="text-sm font-bold text-slate-400 mb-4">Recent Deposits</h4>
                  <div className="space-y-2">
                    {escrow.recent_deposits?.map((d, i) => (
                      <div key={i} className="flex items-center justify-between text-xs p-2 bg-white/[0.02] rounded">
                        <span className="text-slate-500">{d.wallet_address?.slice(0, 12)}...</span>
                        <span className="text-[#00FFA3]">+{d.amount_sol} SOL</span>
                        <span className="text-slate-600">{new Date(d.created_at).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className="glass-card rounded-xl p-4 text-center">
      <div className="w-8 h-8 mx-auto mb-2 rounded-full flex items-center justify-center" 
           style={{ backgroundColor: `${color}15` }}>
        <span style={{ color }}>{icon}</span>
      </div>
      <p className="text-xl font-black" style={{ color, fontFamily: 'Orbitron' }}>{value}</p>
      <p className="text-[10px] text-slate-500 uppercase">{label}</p>
    </div>
  );
}

function ReconciliationDashboard({ data, loading, onRefresh }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <RefreshCw className="w-6 h-6 text-slate-500 animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-16">
        <Wallet className="w-10 h-10 mx-auto mb-3 text-slate-600" />
        <p className="text-slate-400 text-sm">No reconciliation data available</p>
        <Button onClick={onRefresh} variant="outline" size="sm" className="mt-4 border-white/20">
          <RefreshCw className="w-4 h-4 mr-2" /> Load Data
        </Button>
      </div>
    );
  }

  const healthy = data.healthy;
  const drift = data.drift_sol || 0;

  return (
    <div className="space-y-6" data-testid="reconciliation-dashboard">
      {/* Health Banner */}
      <div className={`rounded-xl p-5 border ${healthy ? "bg-[#00FFA3]/5 border-[#00FFA3]/20" : "bg-red-500/5 border-red-500/30"}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {healthy ? (
              <CheckCircle className="w-8 h-8 text-[#00FFA3]" />
            ) : (
              <XCircle className="w-8 h-8 text-red-400" />
            )}
            <div>
              <h3 className="text-lg font-bold" style={{ fontFamily: "Orbitron" }}>
                {healthy ? "Funds Healthy" : "Drift Detected"}
              </h3>
              <p className="text-xs text-slate-400">
                {healthy
                  ? "On-chain balance matches virtual ledger totals"
                  : `Discrepancy of ${drift.toFixed(6)} SOL between on-chain and ledger`}
              </p>
            </div>
          </div>
          <Button onClick={onRefresh} variant="outline" size="sm" className="border-white/20">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-[10px] text-slate-500 uppercase mb-1">On-Chain SOL</p>
          <p className="text-xl font-black text-[#00C2FF]" style={{ fontFamily: "Orbitron" }}>
            {data.total_on_chain_sol?.toFixed(6)}
          </p>
          <p className="text-[10px] text-slate-600">Custodial wallet balance</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-[10px] text-slate-500 uppercase mb-1">Available SOL</p>
          <p className="text-xl font-black text-[#00FFA3]" style={{ fontFamily: "Orbitron" }}>
            {(data.total_available_sol ?? 0).toFixed(6)}
          </p>
          <p className="text-[10px] text-slate-600">User funds (idle)</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-[10px] text-slate-500 uppercase mb-1">In Token Positions</p>
          <p className="text-xl font-black text-[#FFB800]" style={{ fontFamily: "Orbitron" }}>
            {(data.total_locked_in_tokens_sol ?? 0).toFixed(6)}
          </p>
          <p className="text-[10px] text-slate-600">SOL converted to tokens</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-[10px] text-slate-500 uppercase mb-1">Platform Rake</p>
          <p className="text-xl font-black text-[#D946EF]" style={{ fontFamily: "Orbitron" }}>
            {data.platform_rake_sol?.toFixed(6)}
          </p>
          <p className="text-[10px] text-slate-600">Collected fees</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-[10px] text-slate-500 uppercase mb-1">Drift</p>
          <p className={`text-xl font-black ${healthy ? "text-[#00FFA3]" : "text-red-400"}`} style={{ fontFamily: "Orbitron" }}>
            {drift >= 0 ? "+" : ""}{drift.toFixed(6)}
          </p>
          <p className="text-[10px] text-slate-600">On-chain − available − rake</p>
        </div>
      </div>

      {/* Per-User Breakdown */}
      <div className="glass-card rounded-xl p-4">
        <h4 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
          <Users className="w-4 h-4" />
          Per-User Fund Breakdown ({data.user_count || 0} users)
        </h4>
        {data.users && data.users.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="reconciliation-users-table">
              <thead>
                <tr className="text-[10px] text-slate-500 uppercase border-b border-white/10">
                  <th className="text-left p-3">User Wallet</th>
                  <th className="text-left p-3">Custodial</th>
                  <th className="text-right p-3">On-Chain SOL</th>
                  <th className="text-right p-3">Available</th>
                  <th className="text-right p-3">In Tokens</th>
                  <th className="text-right p-3">Total</th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((u) => (
                  <tr key={u.user_wallet} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="p-3 text-xs font-mono text-slate-300">{u.short_wallet}</td>
                    <td className="p-3 text-[10px] font-mono text-slate-500">
                      {u.custodial_address ? `${u.custodial_address.slice(0, 6)}...${u.custodial_address.slice(-4)}` : "N/A"}
                    </td>
                    <td className="p-3 text-xs text-right font-mono text-[#00C2FF]">
                      {u.on_chain_sol?.toFixed(6)}
                    </td>
                    <td className="p-3 text-xs text-right font-mono text-[#00FFA3]">
                      {(u.available_sol ?? 0).toFixed(6)}
                    </td>
                    <td className="p-3 text-xs text-right font-mono text-[#FFB800]">
                      {(u.locked_in_tokens_sol ?? 0).toFixed(6)}
                    </td>
                    <td className="p-3 text-xs text-right font-mono text-white">
                      {u.virtual_balance_sol?.toFixed(6)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-center text-xs text-slate-500 py-6">No users tracked yet. Balances appear after deposits.</p>
        )}
      </div>

      {/* Last check timestamp */}
      {data.checked_at && (
        <p className="text-[10px] text-slate-600 text-right">
          Last checked: {new Date(data.checked_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
