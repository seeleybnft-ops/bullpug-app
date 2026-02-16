import { useState, useEffect, useCallback } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { useTranslation } from "react-i18next";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Zap, Trophy, Users, Wallet, RefreshCw, Swords, Volume2, VolumeX } from "lucide-react";
import { playSoundIfEnabled, isSoundEnabled, setSoundEnabled, playCoinFlipSequence } from "@/utils/sounds";
import "@/styles/animations.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BettingArena() {
  const { publicKey, connected } = useWallet();
  const { t } = useTranslation();
  const [tab, setTab] = useState("coin-toss");
  const [config, setConfig] = useState({ rake_percent: 2.5, distribution_wallet: "", min_bet_sol: 0.01, max_bet_sol: 10 });
  const [soundOn, setSoundOn] = useState(isSoundEnabled());

  useEffect(() => {
    axios.get(`${API}/betting/config`).then(r => setConfig(r.data)).catch(() => {});
  }, []);

  const toggleSound = () => {
    const newValue = !soundOn;
    setSoundOn(newValue);
    setSoundEnabled(newValue);
    if (newValue) playSoundIfEnabled('click');
  };

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-5xl mx-auto px-6 md:px-12">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-3">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Orbitron, sans-serif' }} data-testid="arena-title">
              {t('betting.title').split(' ')[0]} <span className="text-[#00FFA3] neon-text">{t('betting.title').split(' ')[1] || 'Arena'}</span>
            </h1>
            <button
              onClick={toggleSound}
              data-testid="sound-toggle"
              className="p-2 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-[#00FFA3]/50 transition-all"
              title={soundOn ? "Mute sounds" : "Enable sounds"}
            >
              {soundOn ? <Volume2 size={18} /> : <VolumeX size={18} />}
            </button>
          </div>
          <p className="text-slate-500 text-sm">{t('betting.subtitle', { rake: config.rake_percent })}</p>
          <div className="flex items-center justify-center gap-3 mt-3">
            <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] border-[#00FFA3]/30 text-[10px]">
              <Wallet className="w-3 h-3 mr-1" /> {t('betting.solOnly')}
            </Badge>
            <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px]">
              {t('betting.disclaimer')}
            </Badge>
          </div>
        </div>

        {!connected && (
          <div className="glass-card rounded-2xl p-8 text-center mb-8" data-testid="connect-wallet-prompt">
            <Wallet className="w-12 h-12 mx-auto mb-4 text-slate-600" />
            <p className="text-slate-400 mb-2">{t('betting.connectWalletToPlay')}</p>
            <p className="text-xs text-slate-600">{t('betting.p2pRequiresWallet')}</p>
          </div>
        )}

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="grid w-full grid-cols-2 bg-black/40 border border-white/10 rounded-xl p-1 mb-8">
            <TabsTrigger value="coin-toss" data-testid="tab-coin-toss"
              className="data-[state=active]:bg-[#00FFA3]/10 data-[state=active]:text-[#00FFA3] rounded-lg font-bold text-xs uppercase">
              <Swords className="w-4 h-4 mr-2" />{t('betting.coinFlip.title')}
            </TabsTrigger>
            <TabsTrigger value="pot" data-testid="tab-pot"
              className="data-[state=active]:bg-[#D946EF]/10 data-[state=active]:text-[#D946EF] rounded-lg font-bold text-xs uppercase">
              <Trophy className="w-4 h-4 mr-2" />{t('betting.pot.title')}
            </TabsTrigger>
          </TabsList>
          <TabsContent value="coin-toss">
            <P2PCoinFlip walletAddress={publicKey?.toBase58()} connected={connected} config={config} />
          </TabsContent>
          <TabsContent value="pot">
            <P2PPotSystem walletAddress={publicKey?.toBase58()} connected={connected} config={config} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function P2PCoinFlip({ walletAddress, connected, config }) {
  const { t } = useTranslation();
  const [challenges, setChallenges] = useState([]);
  const [betAmount, setBetAmount] = useState("0.1");
  const [choice, setChoice] = useState("heads");
  const [displayName, setDisplayName] = useState(() => localStorage.getItem("bullpugName") || "Guardian");
  const [creating, setCreating] = useState(false);
  const [accepting, setAccepting] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [isFlipping, setIsFlipping] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);

  const fetchChallenges = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/betting/challenges?limit=20`);
      setChallenges(data.challenges);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchChallenges();
    const interval = setInterval(fetchChallenges, 5000);
    axios.get(`${API}/betting/history?limit=10`).then(r => setHistory(r.data.history)).catch(() => {});
    return () => clearInterval(interval);
  }, [fetchChallenges]);

  // Spawn confetti particles
  const spawnConfetti = () => {
    setShowConfetti(true);
    setTimeout(() => setShowConfetti(false), 3000);
  };

  const createChallenge = async () => {
    if (!connected) return toast.error(t('common.connectWallet'));
    const amount = parseFloat(betAmount);
    if (amount < config.min_bet_sol || amount > config.max_bet_sol) {
      return toast.error(`Bet must be between ${config.min_bet_sol} and ${config.max_bet_sol} SOL`);
    }

    playSoundIfEnabled('click');
    setCreating(true);
    try {
      await axios.post(`${API}/betting/challenge/create`, {
        bet_amount_sol: amount,
        choice,
        wallet_address: walletAddress,
        display_name: displayName
      });
      toast.success("Challenge created!");
      localStorage.setItem("bullpugName", displayName);
      fetchChallenges();
      setResult(null);
    } catch (e) {
      playSoundIfEnabled('lose');
      toast.error(e.response?.data?.detail || "Failed to create challenge");
    }
    setCreating(false);
  };

  const acceptChallenge = async (challenge) => {
    if (!connected) return toast.error(t('common.connectWallet'));
    setAccepting(challenge.id);
    setIsFlipping(true);

    try {
      const clientSeed = Math.random().toString(36).slice(2, 18);
      const { data } = await axios.post(`${API}/betting/challenge/accept`, {
        challenge_id: challenge.id,
        wallet_address: walletAddress,
        display_name: displayName,
        client_seed: clientSeed
      });

      const won = data.winner_wallet === walletAddress;
      
      // Play coin flip animation sequence
      playCoinFlipSequence(won, () => {
        setIsFlipping(false);
        setResult({ ...data, won, my_wallet: walletAddress });
        
        if (won) {
          playSoundIfEnabled('win');
          spawnConfetti();
          toast.success(t('betting.coinFlip.youWon', { amount: data.payout_sol }));
        } else {
          playSoundIfEnabled('lose');
          toast.error(t('betting.coinFlip.youLost'));
        }
      });

      localStorage.setItem("bullpugName", displayName);
      fetchChallenges();
      axios.get(`${API}/betting/history?limit=10`).then(r => setHistory(r.data.history)).catch(() => {});
    } catch (e) {
      setIsFlipping(false);
      playSoundIfEnabled('lose');
      toast.error(e.response?.data?.detail || "Failed to accept challenge");
    }
    setAccepting(null);
  };

  const cancelChallenge = async (challengeId) => {
    try {
      await axios.post(`${API}/betting/challenge/cancel/${challengeId}?wallet_address=${walletAddress}`);
      toast.success("Challenge cancelled");
      fetchChallenges();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to cancel");
    }
  };

  const myChallenges = challenges.filter(c => c.creator_wallet === walletAddress);
  const openChallenges = challenges.filter(c => c.creator_wallet !== walletAddress);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Create Challenge */}
      <div className="glass-card rounded-2xl p-6 space-y-5">
        <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
          <Zap className="w-4 h-4 text-[#00FFA3]" /> {t('betting.coinFlip.createChallenge')}
        </h3>

        <div>
          <label className="text-xs text-slate-500 uppercase mb-1 block">{t('betting.coinFlip.yourName')}</label>
          <Input value={displayName} onChange={e => setDisplayName(e.target.value)} maxLength={20}
            className="bg-black/50 border-white/10 text-white" data-testid="display-name-input" />
        </div>

        <div>
          <label className="text-xs text-slate-500 uppercase mb-1 block">{t('betting.coinFlip.betAmount')}</label>
          <Input type="number" step="0.01" value={betAmount} onChange={e => setBetAmount(e.target.value)}
            className="bg-black/50 border-white/10 text-white text-lg font-bold" data-testid="bet-amount-input" />
          <div className="flex gap-2 mt-2">
            {["0.05", "0.1", "0.5", "1"].map(amt => (
              <button key={amt} onClick={() => setBetAmount(amt)}
                className="text-[10px] px-2 py-1 rounded bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors">
                {amt}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-500 uppercase mb-1 block">{t('betting.coinFlip.yourPick')}</label>
          <div className="grid grid-cols-2 gap-2">
            {["heads", "tails"].map(c => (
              <button key={c} onClick={() => setChoice(c)} data-testid={`choice-${c}`}
                className={`py-3 rounded-xl text-sm font-bold uppercase transition-all ${
                  choice === c ? "bg-[#00FFA3] text-black scale-[1.02]" : "bg-white/5 text-slate-400 hover:bg-white/10"
                }`}>
                {c === "heads" ? `🪙 ${t('betting.coinFlip.heads')}` : `⭐ ${t('betting.coinFlip.tails')}`}
              </button>
            ))}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-xs space-y-1">
          <div className="flex justify-between"><span className="text-slate-500">{t('betting.coinFlip.opponentBet')}:</span><span className="text-white">{betAmount} SOL</span></div>
          <div className="flex justify-between"><span className="text-slate-500">{t('betting.coinFlip.totalPot')}:</span><span className="text-[#00FFA3]">{(parseFloat(betAmount || 0) * 2).toFixed(2)} SOL</span></div>
          <div className="flex justify-between"><span className="text-slate-500">{t('betting.coinFlip.rake')} ({config.rake_percent}%):</span><span className="text-amber-400">{(parseFloat(betAmount || 0) * 2 * config.rake_percent / 100).toFixed(4)} SOL</span></div>
          <div className="flex justify-between"><span className="text-slate-500">{t('betting.coinFlip.winnerGets')}:</span><span className="text-[#00FFA3] font-bold">{(parseFloat(betAmount || 0) * 2 * (1 - config.rake_percent / 100)).toFixed(4)} SOL</span></div>
        </div>

        <Button onClick={createChallenge} disabled={creating || !connected} data-testid="create-challenge-btn"
          className="w-full bg-[#00FFA3] text-black font-bold rounded-xl py-5 text-sm uppercase hover:scale-[1.02] transition-transform">
          {creating ? t('betting.coinFlip.creating') : t('betting.coinFlip.createBtn')}
        </Button>

        {myChallenges.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-500 uppercase">{t('betting.coinFlip.yourOpenChallenges')}</p>
            {myChallenges.map(c => (
              <div key={c.id} className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-between">
                <div>
                  <p className="text-sm font-bold text-amber-400">{c.bet_amount_sol} SOL on {c.creator_choice}</p>
                  <p className="text-[10px] text-slate-500">{t('betting.coinFlip.waitingForOpponent')}</p>
                </div>
                <button onClick={() => cancelChallenge(c.id)} className="text-xs text-red-400 hover:text-red-300">{t('betting.coinFlip.cancel')}</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Open Challenges */}
      <div className="lg:col-span-2 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            <Users className="w-4 h-4 text-[#D946EF]" /> {t('betting.coinFlip.openChallenges')}
          </h3>
          <button onClick={fetchChallenges} className="text-xs text-slate-500 hover:text-white flex items-center gap-1">
            <RefreshCw size={12} /> {t('common.refresh')}
          </button>
        </div>

        {result && (
          <div className={`glass-card rounded-xl p-5 border-2 ${result.won ? "border-[#00FFA3]" : "border-red-500"}`} data-testid="flip-result">
            <div className="text-center">
              <p className={`text-2xl font-black ${result.won ? "text-[#00FFA3]" : "text-red-400"}`} style={{ fontFamily: 'Orbitron' }}>
                {result.won ? t('betting.coinFlip.youWon', { amount: result.payout_sol }) : t('betting.coinFlip.youLost')}
              </p>
              <p className="text-sm text-slate-400 mt-1">{t('betting.coinFlip.coinLandedOn')}: <span className="text-white font-bold uppercase">{result.outcome}</span></p>
              <div className="mt-3 p-3 rounded-lg bg-black/50 text-left">
                <p className="text-[10px] text-slate-500 uppercase mb-1">{t('betting.coinFlip.provablyFair')}</p>
                <p className="text-[10px] text-slate-400 break-all">{t('betting.coinFlip.serverSeed')}: {result.server_seed}</p>
                <p className="text-[10px] text-slate-400 break-all">{t('betting.coinFlip.clientSeed')}: {result.client_seed}</p>
                <p className="text-[10px] text-[#00FFA3] break-all">{t('betting.coinFlip.resultHash')}: {result.result_hash}</p>
              </div>
            </div>
          </div>
        )}

        {openChallenges.length === 0 ? (
          <div className="glass-card rounded-xl p-10 text-center">
            <Swords className="w-10 h-10 mx-auto mb-3 text-slate-700" />
            <p className="text-slate-500">{t('betting.coinFlip.noChallenges')}</p>
            <p className="text-xs text-slate-600 mt-1">{t('betting.coinFlip.createOrWait')}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {openChallenges.map(c => (
              <div key={c.id} className="glass-card rounded-xl p-4 hover:bg-white/[0.02] transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-[#D946EF]/10 flex items-center justify-center text-[#D946EF] text-xs font-bold">
                      {c.creator_name?.charAt(0) || "?"}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-white">{c.creator_name}</p>
                      <p className="text-[10px] text-slate-500">{c.creator_wallet?.slice(0, 8)}...</p>
                    </div>
                  </div>
                  <Badge className={`text-[10px] ${c.creator_choice === "heads" ? "bg-amber-500/10 text-amber-400" : "bg-[#00C2FF]/10 text-[#00C2FF]"}`}>
                    {t('betting.coinFlip.picked')} {c.creator_choice}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron' }}>{c.bet_amount_sol} SOL</p>
                    <p className="text-[10px] text-slate-500">{t('betting.coinFlip.youPick')}: {c.creator_choice === "heads" ? t('betting.coinFlip.tails').toUpperCase() : t('betting.coinFlip.heads').toUpperCase()}</p>
                  </div>
                  <Button onClick={() => acceptChallenge(c)} disabled={accepting === c.id || !connected}
                    data-testid={`accept-${c.id}`}
                    className="bg-[#D946EF] text-white font-bold rounded-lg px-4 py-2 text-xs uppercase hover:scale-[1.02] transition-transform">
                    {accepting === c.id ? t('betting.coinFlip.flipping') : t('betting.coinFlip.accept')}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Recent History */}
        {history.length > 0 && (
          <div className="glass-card rounded-xl p-4 mt-6">
            <h4 className="text-xs font-bold uppercase text-slate-500 mb-3">{t('betting.coinFlip.recentFlips')}</h4>
            <div className="space-y-2">
              {history.slice(0, 5).map((h, i) => (
                <div key={i} className="flex items-center justify-between text-xs p-2 rounded bg-white/[0.02]">
                  <span className="text-slate-400">{h.bet_amount_sol || h.bet_amount} SOL</span>
                  <span className={h.outcome === "heads" ? "text-amber-400" : "text-[#00C2FF]"}>{h.outcome}</span>
                  <span className="text-slate-600">{new Date(h.timestamp).toLocaleTimeString()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function P2PPotSystem({ walletAddress, connected, config }) {
  const { t } = useTranslation();
  const [pot, setPot] = useState({ total_amount_sol: 0, entries: [], status: "open", rake_percent: 2.5 });
  const [betAmount, setBetAmount] = useState("0.1");
  const [displayName, setDisplayName] = useState(() => localStorage.getItem("bullpugName") || "Guardian");
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    const wsUrl = process.env.REACT_APP_BACKEND_URL.replace("https://", "wss://").replace("http://", "ws://");
    const socket = new WebSocket(`${wsUrl}/ws/pot`);
    socket.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "pot_update") setPot(msg.data);
      if (msg.type === "pot_winner") {
        toast.success(t('betting.pot.won', { name: msg.data.winner_name, amount: msg.data.payout_sol }));
      }
    };
    axios.get(`${API}/betting/pot`).then(r => setPot(r.data)).catch(() => {});
    return () => socket.close();
  }, [t]);

  const joinPot = async () => {
    if (!connected) return toast.error(t('common.connectWallet'));
    const amount = parseFloat(betAmount);
    if (amount < config.min_bet_sol) return toast.error(`Minimum bet is ${config.min_bet_sol} SOL`);

    setJoining(true);
    try {
      const { data } = await axios.post(`${API}/betting/pot/join`, {
        bet_amount_sol: amount,
        wallet_address: walletAddress,
        display_name: displayName
      });
      toast.success(data.message);
      localStorage.setItem("bullpugName", displayName);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to join pot");
    }
    setJoining(false);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Join Pot */}
      <div className="glass-card rounded-2xl p-6 space-y-5">
        <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
          <Trophy className="w-4 h-4 text-[#D946EF]" /> {t('betting.pot.joinPot')}
        </h3>

        <div>
          <label className="text-xs text-slate-500 uppercase mb-1 block">{t('betting.pot.yourName')}</label>
          <Input value={displayName} onChange={e => setDisplayName(e.target.value)} maxLength={20}
            className="bg-black/50 border-white/10 text-white" />
        </div>

        <div>
          <label className="text-xs text-slate-500 uppercase mb-1 block">{t('betting.pot.betAmount')}</label>
          <Input type="number" step="0.01" value={betAmount} onChange={e => setBetAmount(e.target.value)}
            className="bg-black/50 border-white/10 text-white text-lg font-bold" data-testid="pot-bet-input" />
          <div className="flex gap-2 mt-2">
            {["0.1", "0.5", "1", "2"].map(amt => (
              <button key={amt} onClick={() => setBetAmount(amt)}
                className="text-[10px] px-2 py-1 rounded bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors">
                {amt}
              </button>
            ))}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-[#D946EF]/10 border border-[#D946EF]/30">
          <p className="text-xs text-slate-400">
            {t('betting.pot.higherBetHigherChance', { rake: pot.rake_percent })}
          </p>
        </div>

        <Button onClick={joinPot} disabled={joining || !connected} data-testid="join-pot-btn"
          className="w-full bg-[#D946EF] text-white font-bold rounded-xl py-5 text-sm uppercase hover:scale-[1.02] transition-transform">
          {joining ? t('betting.pot.joining') : t('betting.pot.joinBtn')}
        </Button>

        <div className="text-center">
          <p className="text-[10px] text-slate-600">
            {t('betting.pot.rakeGoesTo')}: <span className="text-slate-400">{config.distribution_wallet?.slice(0, 12)}...</span>
          </p>
        </div>
      </div>

      {/* Pot Status */}
      <div className="lg:col-span-2 space-y-4">
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs text-slate-500 uppercase">{t('betting.pot.currentPot')}</p>
              <p className="text-4xl font-black text-[#D946EF]" style={{ fontFamily: 'Orbitron' }}>
                {pot.total_amount_sol?.toFixed(2) || "0.00"} <span className="text-lg">SOL</span>
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500 uppercase">{t('betting.pot.entries')}</p>
              <p className="text-2xl font-black text-white" style={{ fontFamily: 'Orbitron' }}>{pot.entry_count || 0}</p>
            </div>
          </div>

          {pot.winner && (
            <div className="p-4 rounded-xl bg-[#00FFA3]/10 border border-[#00FFA3]/30 mb-4">
              <p className="text-sm font-bold text-[#00FFA3]">
                {t('betting.pot.won', { name: pot.winner.winner_name, amount: pot.winner.payout_sol })}
              </p>
            </div>
          )}

          {pot.entries && pot.entries.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-slate-500 uppercase mb-2">{t('betting.pot.participants')}</p>
              {pot.entries.map((e, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-[#D946EF]/10 flex items-center justify-center text-[#D946EF] text-xs font-bold">
                      {e.display_name?.charAt(0) || "?"}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-white">{e.display_name}</p>
                      <p className="text-[10px] text-slate-500">{e.wallet_address}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-[#D946EF]">{e.amount_sol} SOL</p>
                    <p className="text-[10px] text-[#00FFA3]">{e.probability}% {t('betting.pot.chance')}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Trophy className="w-10 h-10 mx-auto mb-3 text-slate-700" />
              <p className="text-slate-500">{t('betting.pot.noEntries')}</p>
            </div>
          )}
        </div>

        <div className="glass-card rounded-xl p-4">
          <p className="text-xs text-slate-500 mb-2">{t('betting.pot.howItWorks')}</p>
          <ul className="text-xs text-slate-400 space-y-1">
            <li>• {t('betting.pot.rule1')}</li>
            <li>• {t('betting.pot.rule2')}</li>
            <li>• {t('betting.pot.rule3')} ({pot.rake_percent}% {t('betting.coinFlip.rake').toLowerCase()})</li>
            <li>• {t('betting.pot.rule4')}</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
