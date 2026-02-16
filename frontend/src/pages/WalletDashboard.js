import { useState, useEffect } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { LAMPORTS_PER_SOL } from "@solana/web3.js";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip as ChartTooltip, Filler } from "chart.js";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import axios from "axios";
import { Wallet, Coins, Shield, Vote, TrendingUp, Star, ThumbsUp, ThumbsDown } from "lucide-react";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, ChartTooltip, Filler);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function WalletDashboard() {
  const { publicKey, connected } = useWallet();
  const { connection } = useConnection();
  const [balance, setBalance] = useState(null);
  const [guardianPoints, setGuardianPoints] = useState(() => parseInt(localStorage.getItem("guardianPoints") || "0"));
  const [proposals, setProposals] = useState([]);
  const [stakingResult, setStakingResult] = useState(null);
  const [stakeAmount, setStakeAmount] = useState("10000");
  const [stakeDays, setStakeDays] = useState([90]);
  const [stakeApy, setStakeApy] = useState([12]);

  useEffect(() => {
    if (connected && publicKey) {
      connection.getBalance(publicKey).then(b => setBalance(b / LAMPORTS_PER_SOL)).catch(() => setBalance(0));
    }
  }, [connected, publicKey, connection]);

  useEffect(() => {
    axios.get(`${API}/governance/proposals`).then(r => setProposals(r.data.proposals)).catch(() => {});
  }, []);

  const simulateStaking = async () => {
    try {
      const { data } = await axios.post(`${API}/staking/simulate`, {
        amount: parseFloat(stakeAmount), duration_days: stakeDays[0], apy: stakeApy[0],
      });
      setStakingResult(data);
      const pts = guardianPoints + data.guardian_points;
      setGuardianPoints(pts);
      localStorage.setItem("guardianPoints", String(pts));
      toast.success(`Staking sim complete! +${data.guardian_points} Guardian Points`);
    } catch (e) { toast.error("Simulation failed"); }
  };

  const vote = async (proposalId, voteChoice) => {
    try {
      await axios.post(`${API}/governance/vote`, {
        proposal_id: proposalId, vote: voteChoice, wallet_address: publicKey?.toBase58() || "anonymous",
      });
      toast.success("Vote cast!");
      axios.get(`${API}/governance/proposals`).then(r => setProposals(r.data.proposals));
    } catch (e) { toast.error(e.response?.data?.detail || "Vote failed"); }
  };

  const stakingChart = stakingResult ? {
    labels: stakingResult.chart_data.map(d => `Day ${d.day}`),
    datasets: [{
      label: "Balance", data: stakingResult.chart_data.map(d => d.balance),
      borderColor: "#00FFA3", backgroundColor: "rgba(0,255,163,0.1)", fill: true, tension: 0.4,
    }],
  } : null;

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-5xl mx-auto px-6 md:px-12">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase mb-8 text-center" style={{ fontFamily: 'Orbitron, sans-serif' }}>
          Wallet <span className="text-[#00FFA3] neon-text">Dashboard</span>
        </h1>

        {/* Wallet Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="glass-card rounded-2xl p-5 text-center" data-testid="wallet-balance-card">
            <Wallet className="w-6 h-6 mx-auto mb-2 text-[#00FFA3]" />
            <p className="text-xs text-slate-500 uppercase mb-1">SOL Balance</p>
            <p className="text-2xl font-black" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              {connected ? (balance !== null ? balance.toFixed(4) : "...") : "Not Connected"}
            </p>
            {connected && publicKey && (
              <p className="text-[10px] text-slate-600 mt-1 font-mono truncate">{publicKey.toBase58()}</p>
            )}
          </div>
          <div className="glass-card rounded-2xl p-5 text-center">
            <Coins className="w-6 h-6 mx-auto mb-2 text-[#F5D300]" />
            <p className="text-xs text-slate-500 uppercase mb-1">$BULLPUG (Sim)</p>
            <p className="text-2xl font-black text-[#F5D300]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              {connected ? "1,000,000" : "0"}
            </p>
          </div>
          <div className="glass-card rounded-2xl p-5 text-center" data-testid="guardian-points-card">
            <Star className="w-6 h-6 mx-auto mb-2 text-[#D946EF]" />
            <p className="text-xs text-slate-500 uppercase mb-1">Guardian Points</p>
            <p className="text-2xl font-black text-[#D946EF]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              {guardianPoints.toLocaleString()}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Staking */}
          <div className="glass-card rounded-2xl p-6 space-y-5">
            <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              <TrendingUp className="w-4 h-4 text-[#00FFA3]" /> Staking Simulator
            </h3>
            <div>
              <label className="text-xs text-slate-500 uppercase mb-1 block">Amount ($BULLPUG)</label>
              <Input type="number" value={stakeAmount} onChange={e => setStakeAmount(e.target.value)}
                data-testid="stake-amount-input" className="bg-black/50 border-white/10 text-white" />
            </div>
            <div>
              <div className="flex justify-between text-xs text-slate-500 mb-2">
                <span>Duration</span><span className="text-white font-bold">{stakeDays[0]} days</span>
              </div>
              <Slider value={stakeDays} onValueChange={setStakeDays} min={7} max={365} step={1}
                data-testid="stake-days-slider" className="my-2" />
            </div>
            <div>
              <div className="flex justify-between text-xs text-slate-500 mb-2">
                <span>APY</span><span className="text-[#00FFA3] font-bold">{stakeApy[0]}%</span>
              </div>
              <Slider value={stakeApy} onValueChange={setStakeApy} min={1} max={25} step={0.5}
                data-testid="stake-apy-slider" className="my-2" />
            </div>
            <Button onClick={simulateStaking} data-testid="simulate-staking-btn"
              className="w-full bg-[#00FFA3] text-black font-bold rounded-xl py-5 text-sm uppercase hover:scale-[1.02] transition-transform">
              Simulate Staking
            </Button>
            {stakingResult && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="p-3 rounded-xl border border-white/5">
                    <p className="text-xs text-slate-500">Rewards</p>
                    <p className="text-lg font-bold text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                      {stakingResult.total_rewards.toLocaleString()}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl border border-white/5">
                    <p className="text-xs text-slate-500">Points Earned</p>
                    <p className="text-lg font-bold text-[#D946EF]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                      +{stakingResult.guardian_points}
                    </p>
                  </div>
                </div>
                {stakingChart && (
                  <Line data={stakingChart} options={{
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                      x: { ticks: { color: "#64748b", font: { size: 9 } }, grid: { color: "rgba(255,255,255,0.03)" } },
                      y: { ticks: { color: "#64748b", font: { size: 9 } }, grid: { color: "rgba(255,255,255,0.03)" } },
                    },
                  }} />
                )}
              </div>
            )}
          </div>

          {/* Governance */}
          <div className="glass-card rounded-2xl p-6">
            <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2 mb-5" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              <Vote className="w-4 h-4 text-[#F5D300]" /> Governance
            </h3>
            <div className="space-y-4">
              {proposals.map(p => {
                const total = p.yes_votes + p.no_votes;
                const yesPct = total > 0 ? Math.round(p.yes_votes / total * 100) : 50;
                return (
                  <div key={p.id} className="p-4 rounded-xl border border-white/5 space-y-3" data-testid={`proposal-${p.id}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-sm font-bold">{p.title}</h4>
                        <p className="text-xs text-slate-500 mt-1">{p.description}</p>
                      </div>
                      <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] text-[10px] flex-shrink-0">{p.status}</Badge>
                    </div>
                    <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-[#00FFA3] rounded-full transition-all" style={{ width: `${yesPct}%` }} />
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#00FFA3]">Yes: {p.yes_votes}</span>
                      <span className="text-red-400">No: {p.no_votes}</span>
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={() => vote(p.id, "yes")} size="sm" data-testid={`vote-yes-${p.id}`}
                        className="flex-1 bg-[#00FFA3]/10 text-[#00FFA3] border border-[#00FFA3]/30 rounded-lg text-xs hover:bg-[#00FFA3]/20">
                        <ThumbsUp className="w-3 h-3 mr-1" /> Yes
                      </Button>
                      <Button onClick={() => vote(p.id, "no")} size="sm" data-testid={`vote-no-${p.id}`}
                        className="flex-1 bg-red-500/10 text-red-400 border border-red-500/30 rounded-lg text-xs hover:bg-red-500/20">
                        <ThumbsDown className="w-3 h-3 mr-1" /> No
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
