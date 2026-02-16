import { useState, useEffect } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Zap, Trophy, Clock, Shield, ChevronDown, ChevronUp } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BettingArena() {
  const { publicKey } = useWallet();
  const [tab, setTab] = useState("coin-toss");
  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-5xl mx-auto px-6 md:px-12">
        <div className="text-center mb-10">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase mb-3" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            Betting <span className="text-[#00FFA3] neon-text">Arena</span>
          </h1>
          <p className="text-slate-500 text-sm">Wager on the stars. Provably fair.</p>
          <Badge className="mt-3 bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px]">
            For entertainment - check local laws
          </Badge>
        </div>
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="grid w-full grid-cols-2 bg-black/40 border border-white/10 rounded-xl p-1 mb-8">
            <TabsTrigger value="coin-toss" data-testid="tab-coin-toss"
              className="data-[state=active]:bg-[#00FFA3]/10 data-[state=active]:text-[#00FFA3] rounded-lg font-bold text-xs uppercase">
              <Zap className="w-4 h-4 mr-2" />Coin Toss
            </TabsTrigger>
            <TabsTrigger value="pot" data-testid="tab-pot"
              className="data-[state=active]:bg-[#D946EF]/10 data-[state=active]:text-[#D946EF] rounded-lg font-bold text-xs uppercase">
              <Trophy className="w-4 h-4 mr-2" />Winner Pot
            </TabsTrigger>
          </TabsList>
          <TabsContent value="coin-toss">
            <CoinToss walletAddress={publicKey?.toBase58()} />
          </TabsContent>
          <TabsContent value="pot">
            <PotSystem walletAddress={publicKey?.toBase58()} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function CoinToss({ walletAddress }) {
  const [clientSeed, setClientSeed] = useState(() => Math.random().toString(36).slice(2, 10));
  const [betAmount, setBetAmount] = useState("100");
  const [choice, setChoice] = useState("heads");
  const [flipping, setFlipping] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [showVerify, setShowVerify] = useState(false);

  useEffect(() => {
    axios.get(`${API}/betting/history?limit=10`).then(r => setHistory(r.data.history)).catch(() => {});
  }, []);

  const flip = async () => {
    setFlipping(true);
    setResult(null);
    try {
      const { data } = await axios.post(`${API}/betting/coin-toss`, {
        client_seed: clientSeed,
        bet_amount: parseFloat(betAmount),
        choice,
        wallet_address: walletAddress || "anonymous",
      });
      setTimeout(() => {
        setResult(data);
        setFlipping(false);
        data.won ? toast.success(`Won ${data.payout} $BULLPUG!`) : toast.error(`Lost. Coin: ${data.outcome}`);
        setHistory(prev => [data, ...prev.slice(0, 9)]);
        setClientSeed(Math.random().toString(36).slice(2, 10));
      }, 1500);
    } catch (e) {
      toast.error("Flip failed");
      setFlipping(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-6">
        <div className="glass-card rounded-2xl p-8 text-center">
          <div
            className={`w-32 h-32 mx-auto rounded-full border-4 flex items-center justify-center text-3xl font-black mb-6 transition-all ${
              flipping
                ? "animate-coin-flip border-[#F5D300]"
                : result?.won
                ? "border-[#00FFA3] shadow-[0_0_30px_rgba(0,255,163,0.4)]"
                : result
                ? "border-red-500"
                : "border-[#F5D300]/50"
            }`}
            style={{ fontFamily: "Orbitron" }}
          >
            {flipping ? "?" : result ? (result.outcome === "heads" ? "H" : "T") : "?"}
          </div>
          {result && (
            <p className={`text-lg font-bold animate-slide-up ${result.won ? "text-[#00FFA3]" : "text-red-400"}`}
              style={{ fontFamily: "Orbitron" }}>
              {result.won ? `WON ${result.payout} $BULLPUG!` : `Lost! Coin: ${result.outcome}`}
            </p>
          )}
        </div>

        <div className="glass-card rounded-2xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {["heads", "tails"].map(c => (
              <button key={c} onClick={() => setChoice(c)} data-testid={`choice-${c}`}
                className={`p-3 rounded-xl border text-sm font-bold uppercase transition-all ${
                  choice === c
                    ? c === "heads"
                      ? "border-[#00FFA3] bg-[#00FFA3]/10 text-[#00FFA3]"
                      : "border-[#D946EF] bg-[#D946EF]/10 text-[#D946EF]"
                    : "border-white/10 text-slate-400"
                }`}
                style={{ fontFamily: "Orbitron" }}
              >
                {c}
              </button>
            ))}
          </div>
          <div>
            <label className="text-xs text-slate-500 uppercase mb-1 block">Bet ($BULLPUG)</label>
            <Input type="number" value={betAmount} onChange={e => setBetAmount(e.target.value)}
              data-testid="bet-amount-input" className="bg-black/50 border-white/10 text-white" />
          </div>
          <div>
            <label className="text-xs text-slate-500 uppercase mb-1 block">Client Seed</label>
            <Input value={clientSeed} onChange={e => setClientSeed(e.target.value)}
              data-testid="client-seed-input" className="bg-black/50 border-white/10 text-white font-mono text-xs" />
          </div>
          <Button onClick={flip} disabled={flipping} data-testid="flip-btn"
            className="w-full bg-[#00FFA3] text-black font-bold rounded-xl py-5 text-sm uppercase hover:scale-[1.02] transition-transform shadow-[0_0_20px_rgba(0,255,163,0.3)]">
            {flipping ? "Flipping..." : "Flip Coin"}
          </Button>
          <p className="text-[10px] text-slate-600 text-center">5% house fee | 50/50 odds</p>
        </div>

        {result && (
          <div className="glass-card rounded-2xl p-5">
            <button onClick={() => setShowVerify(!showVerify)} data-testid="verify-toggle"
              className="flex items-center gap-2 text-xs text-[#00FFA3] font-bold uppercase">
              <Shield className="w-4 h-4" /> Verify{" "}
              {showVerify ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showVerify && (
              <div className="mt-3 space-y-1 text-[11px] font-mono text-slate-500 break-all">
                <p>Server Seed: {result.server_seed}</p>
                <p>Server Hash: {result.server_seed_hash}</p>
                <p>Client Seed: {result.client_seed}</p>
                <p>Result Hash: {result.result_hash}</p>
                <p className="text-[#00FFA3]">
                  Last hex: {result.result_hash?.slice(-1)} ={" "}
                  {parseInt(result.result_hash?.slice(-1), 16) % 2 === 0 ? "even(heads)" : "odd(tails)"}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="lg:col-span-2">
        <div className="glass-card rounded-2xl p-5 sticky top-20">
          <h3 className="text-sm font-bold uppercase mb-4 flex items-center gap-2" style={{ fontFamily: "Orbitron" }}>
            <Clock className="w-4 h-4 text-[#00FFA3]" /> Recent Flips
          </h3>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {history.length === 0 && <p className="text-xs text-slate-600">No flips yet</p>}
            {history.map((h, i) => (
              <div key={i}
                className={`flex items-center justify-between p-2.5 rounded-lg border text-xs ${
                  h.won ? "border-[#00FFA3]/20 bg-[#00FFA3]/5" : "border-red-500/20 bg-red-500/5"
                }`}>
                <span className={h.won ? "text-[#00FFA3]" : "text-red-400"}>
                  {h.won ? "WON" : "LOST"} - {h.outcome}
                </span>
                <span className={`font-bold ${h.won ? "text-[#00FFA3]" : "text-red-400"}`}>
                  {h.won ? `+${h.payout}` : `-${h.bet_amount}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function PotSystem({ walletAddress }) {
  const [pot, setPot] = useState(null);
  const [betAmount, setBetAmount] = useState("50");
  const [displayName, setDisplayName] = useState("Guardian");
  const [joining, setJoining] = useState(false);
  const [wsStatus, setWsStatus] = useState("connecting");

  const fetchPot = () => {
    axios.get(`${API}/betting/pot`).then(r => setPot(r.data)).catch(() => {});
  };

  useEffect(() => {
    fetchPot();
    // WebSocket for real-time updates
    const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
    const wsUrl = backendUrl.replace(/^http/, "ws") + "/ws/pot";
    let ws;
    let reconnectTimer;
    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        ws.onopen = () => setWsStatus("connected");
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === "pot_update") setPot(msg.data);
            if (msg.type === "pot_winner") {
              toast.success(`Winner: ${msg.data.winner} won ${msg.data.payout} $BULLPUG!`);
            }
          } catch {}
        };
        ws.onclose = () => { setWsStatus("reconnecting"); reconnectTimer = setTimeout(connect, 3000); };
        ws.onerror = () => { ws.close(); };
      } catch {
        setWsStatus("fallback");
      }
    };
    connect();
    // Fallback polling
    const iv = setInterval(fetchPot, 10000);
    return () => { clearInterval(iv); clearTimeout(reconnectTimer); if (ws) ws.close(); };
  }, []);

  const joinPot = async () => {
    if (!betAmount || parseFloat(betAmount) <= 0) return toast.error("Enter valid bet");
    setJoining(true);
    try {
      const { data } = await axios.post(`${API}/betting/pot/join`, {
        bet_amount: parseFloat(betAmount),
        wallet_address: walletAddress || "anon",
        display_name: displayName,
      });
      toast.success(data.message);
      fetchPot();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    }
    setJoining(false);
  };

  const drawWinner = async () => {
    try {
      const { data } = await axios.post(`${API}/betting/pot/draw`);
      toast.success(`Winner: ${data.winner} - ${data.payout} $BULLPUG!`);
      fetchPot();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Need 2+ entries");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <div className="glass-card rounded-2xl p-6 text-center">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-2" style={{ fontFamily: "Orbitron" }}>
            Current Pot
          </p>
          <p className="text-4xl md:text-5xl font-black text-[#F5D300] mb-2" style={{ fontFamily: "Orbitron" }}>
            {pot?.total_amount || 0}
          </p>
          <p className="text-xs text-slate-500">
            {pot?.entry_count || 0} entries | {pot?.house_fee_percent || 7}% fee
          </p>
          <Badge className={`mt-3 ${pot?.status === "open" ? "bg-[#00FFA3]/10 text-[#00FFA3]" : "bg-red-500/10 text-red-400"}`}>
            {pot?.status || "open"}
          </Badge>
          <div className="flex items-center gap-1 mt-2 justify-center">
            <div className={`w-1.5 h-1.5 rounded-full ${wsStatus === "connected" ? "bg-[#00FFA3]" : "bg-amber-400 animate-pulse"}`} />
            <span className="text-[9px] text-slate-600">{wsStatus === "connected" ? "Live" : "Connecting..."}</span>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6 space-y-4">
          <div>
            <label className="text-xs text-slate-500 uppercase mb-1 block">Name</label>
            <Input value={displayName} onChange={e => setDisplayName(e.target.value)}
              data-testid="pot-name-input" className="bg-black/50 border-white/10 text-white" />
          </div>
          <div>
            <label className="text-xs text-slate-500 uppercase mb-1 block">Bet ($BULLPUG)</label>
            <Input type="number" value={betAmount} onChange={e => setBetAmount(e.target.value)}
              data-testid="pot-amount-input" className="bg-black/50 border-white/10 text-white" />
          </div>
          <Button onClick={joinPot} disabled={joining} data-testid="pot-join-btn"
            className="w-full bg-[#D946EF] text-white font-bold rounded-xl py-5 text-sm uppercase hover:scale-[1.02] transition-transform">
            {joining ? "Joining..." : "Join Pot"}
          </Button>
          <Button onClick={drawWinner} variant="outline" data-testid="pot-draw-btn"
            className="w-full border-[#F5D300] text-[#F5D300] rounded-xl py-5 text-sm font-bold uppercase hover:bg-[#F5D300]/10">
            Draw Winner
          </Button>
        </div>
      </div>

      <div className="glass-card rounded-2xl p-5">
        <h3 className="text-sm font-bold uppercase mb-4" style={{ fontFamily: "Orbitron" }}>
          <Trophy className="inline w-4 h-4 text-[#F5D300] mr-2" />
          Participants
        </h3>
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {(!pot?.entries || pot.entries.length === 0) && (
            <p className="text-xs text-slate-600">No entries yet</p>
          )}
          {pot?.entries?.map((e, i) => (
            <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-white/5">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#D946EF] to-[#00FFA3] flex items-center justify-center text-[10px] font-bold text-black">
                  {i + 1}
                </div>
                <span className="text-sm">{e.display_name}</span>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold">{e.amount}</p>
                <p className="text-[10px] text-[#00FFA3]">{e.probability}%</p>
              </div>
            </div>
          ))}
        </div>
        {pot?.winner && (
          <div className="mt-4 p-3 rounded-xl border border-[#F5D300]/30 bg-[#F5D300]/5">
            <p className="text-xs text-[#F5D300] font-bold">Last Winner: {pot.winner.winner}</p>
            <p className="text-sm text-[#00FFA3]">Won {pot.winner.payout} $BULLPUG</p>
          </div>
        )}
      </div>
    </div>
  );
}
