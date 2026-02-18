import { useState, useEffect, useCallback } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { useTranslation } from "react-i18next";
import { PublicKey, Transaction, SystemProgram, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Zap, Trophy, Users, Wallet, RefreshCw, Swords, Volume2, VolumeX, Loader2 } from "lucide-react";
import { playSoundIfEnabled, isSoundEnabled, setSoundEnabled, playCoinFlipSequence, winFeedback, loseFeedback, challengeCreatedFeedback, clickFeedback } from "@/utils/sounds";
import "@/styles/animations.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Send SOL to escrow wallet with wallet prompt
 */
async function sendSolToEscrow(connection, wallet, escrowAddress, amountSol) {
  if (!wallet.publicKey || !wallet.signTransaction) {
    throw new Error("Wallet not connected");
  }

  const escrowPubkey = new PublicKey(escrowAddress);
  const lamports = Math.floor(amountSol * LAMPORTS_PER_SOL);

  // Create transfer instruction
  const transaction = new Transaction().add(
    SystemProgram.transfer({
      fromPubkey: wallet.publicKey,
      toPubkey: escrowPubkey,
      lamports,
    })
  );

  // Get recent blockhash
  const { blockhash } = await connection.getLatestBlockhash();
  transaction.recentBlockhash = blockhash;
  transaction.feePayer = wallet.publicKey;

  // Sign and send
  const signed = await wallet.signTransaction(transaction);
  const signature = await connection.sendRawTransaction(signed.serialize());
  
  // Wait for confirmation
  await connection.confirmTransaction(signature, 'confirmed');
  
  return signature;
}

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
            <P2PCoinFlip walletAddress={publicKey?.toBase58()} connected={connected} config={config} wallet={{ publicKey, signTransaction: useWallet().signTransaction }} connection={useConnection().connection} />
          </TabsContent>
          <TabsContent value="pot">
            <P2PPotSystem walletAddress={publicKey?.toBase58()} connected={connected} config={config} wallet={{ publicKey, signTransaction: useWallet().signTransaction }} connection={useConnection().connection} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function P2PCoinFlip({ walletAddress, connected, config, wallet, connection }) {
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
  const [transferStep, setTransferStep] = useState(null); // 'prompting', 'signing', 'confirming'

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
      playSoundIfEnabled('error');
      return toast.error(`Bet must be between ${config.min_bet_sol} and ${config.max_bet_sol} SOL`);
    }

    clickFeedback();
    setCreating(true);
    setTransferStep('prompting');
    
    try {
      // Step 1: Prompt wallet to transfer SOL to escrow
      toast.info("Please approve the SOL transfer in your wallet...");
      setTransferStep('signing');
      
      const signature = await sendSolToEscrow(
        connection,
        wallet,
        config.distribution_wallet,
        amount
      );
      
      setTransferStep('confirming');
      toast.success("Transfer confirmed! Creating challenge...");
      
      // Step 2: Register challenge on backend with tx signature
      await axios.post(`${API}/betting/challenge/create`, {
        bet_amount_sol: amount,
        choice,
        wallet_address: walletAddress,
        display_name: displayName,
        tx_signature: signature
      });
      
      challengeCreatedFeedback();
      toast.success("Challenge created!");
      localStorage.setItem("bullpugName", displayName);
      fetchChallenges();
      setResult(null);
    } catch (e) {
      playSoundIfEnabled('error');
      if (e.message?.includes('User rejected')) {
        toast.error("Transaction cancelled by user");
      } else {
        toast.error(e.response?.data?.detail || e.message || "Failed to create challenge");
      }
    }
    setCreating(false);
    setTransferStep(null);
  };

  const acceptChallenge = async (challenge) => {
    if (!connected) return toast.error(t('common.connectWallet'));
    clickFeedback();
    setAccepting(challenge.id);
    setTransferStep('prompting');

    try {
      // Step 1: Prompt wallet to transfer SOL to escrow (matching bet amount)
      toast.info("Please approve the SOL transfer to match the bet...");
      setTransferStep('signing');
      
      const signature = await sendSolToEscrow(
        connection,
        wallet,
        config.distribution_wallet,
        challenge.bet_amount_sol
      );
      
      setTransferStep('confirming');
      toast.success("Transfer confirmed! Flipping coin...");
      
      setIsFlipping(true);
      
      // Step 2: Accept challenge on backend with tx signature
      const clientSeed = Math.random().toString(36).slice(2, 18);
      const { data } = await axios.post(`${API}/betting/challenge/accept`, {
        challenge_id: challenge.id,
        wallet_address: walletAddress,
        display_name: displayName,
        client_seed: clientSeed,
        tx_signature: signature
      });

      const won = data.winner_wallet === walletAddress;
      
      // Play coin flip animation sequence with haptic
      playCoinFlipSequence(won, () => {
        setIsFlipping(false);
        setResult({ ...data, won, my_wallet: walletAddress });
        
        if (won) {
          winFeedback();
          spawnConfetti();
          toast.success(t('betting.coinFlip.youWon', { amount: data.payout_sol }));
        } else {
          loseFeedback();
          toast.error(t('betting.coinFlip.youLost'));
        }
      });

      localStorage.setItem("bullpugName", displayName);
      fetchChallenges();
      axios.get(`${API}/betting/history?limit=10`).then(r => setHistory(r.data.history)).catch(() => {});
    } catch (e) {
      setIsFlipping(false);
      playSoundIfEnabled('error');
      if (e.message?.includes('User rejected')) {
        toast.error("Transaction cancelled by user");
      } else {
        toast.error(e.response?.data?.detail || e.message || "Failed to accept challenge");
      }
    }
    setAccepting(null);
    setTransferStep(null);
  };

  const cancelChallenge = async (challengeId) => {
    clickFeedback();
    try {
      await axios.post(`${API}/betting/challenge/cancel/${challengeId}?wallet_address=${walletAddress}`);
      playSoundIfEnabled('success');
      toast.success("Challenge cancelled");
      fetchChallenges();
    } catch (e) {
      playSoundIfEnabled('error');
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

        {/* Confetti Effect */}
        {showConfetti && (
          <div className="fixed inset-0 pointer-events-none z-50">
            {[...Array(30)].map((_, i) => (
              <div
                key={i}
                className="confetti-particle"
                style={{
                  left: `${Math.random() * 100}%`,
                  backgroundColor: ['#00FFA3', '#D946EF', '#F5D300', '#00C2FF'][Math.floor(Math.random() * 4)],
                  animationDelay: `${Math.random() * 0.5}s`,
                  borderRadius: Math.random() > 0.5 ? '50%' : '0',
                }}
              />
            ))}
          </div>
        )}

        {/* Flipping Animation */}
        {isFlipping && (
          <div className="glass-card rounded-xl p-8 text-center mb-4">
            <div className="coin-flip-animation inline-block">
              <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-[#F5D300] to-[#D4AF37] flex items-center justify-center text-3xl border-4 border-[#FFE066] shadow-lg">
                🪙
              </div>
            </div>
            <p className="text-slate-400 mt-4 text-sm animate-pulse">{t('betting.coinFlip.flipping')}...</p>
          </div>
        )}

        {result && !isFlipping && (
          <div className={`glass-card rounded-xl p-5 border-2 ${result.won ? "border-[#00FFA3] win-pulse" : "border-red-500 lose-pulse"}`} data-testid="flip-result">
            <div className="text-center">
              <div className={`coin-result-animation inline-block mb-3`}>
                <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center text-2xl border-4 ${
                  result.outcome === 'heads' ? 'bg-amber-500/20 border-amber-500' : 'bg-[#00C2FF]/20 border-[#00C2FF]'
                }`}>
                  {result.outcome === 'heads' ? '🪙' : '⭐'}
                </div>
              </div>
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

function P2PPotSystem({ walletAddress, connected, config, wallet, connection }) {
  const { t } = useTranslation();
  const [pot, setPot] = useState({ total_amount_sol: 0, entries: [], status: "open", rake_percent: 2.5, countdown_started: false, remaining_seconds: null });
  const [betAmount, setBetAmount] = useState("0.1");
  const [displayName, setDisplayName] = useState(() => localStorage.getItem("bullpugName") || "Guardian");
  const [joining, setJoining] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [transferStep, setTransferStep] = useState(null);

  useEffect(() => {
    const wsUrl = process.env.REACT_APP_BACKEND_URL.replace("https://", "wss://").replace("http://", "ws://");
    const socket = new WebSocket(`${wsUrl}/ws/pot`);
    socket.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "pot_update") {
        setPot(msg.data);
        if (msg.data.remaining_seconds !== null) {
          setCountdown(msg.data.remaining_seconds);
        }
      }
      if (msg.type === "pot_winner") {
        toast.success(t('betting.pot.won', { name: msg.data.winner_name, amount: msg.data.payout_sol }));
        setCountdown(null);
      }
    };
    axios.get(`${API}/betting/pot`).then(r => {
      setPot(r.data);
      if (r.data.remaining_seconds !== null) {
        setCountdown(r.data.remaining_seconds);
      }
    }).catch(() => {});
    return () => socket.close();
  }, [t]);

  // Countdown timer effect
  useEffect(() => {
    if (countdown === null || countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  const joinPot = async () => {
    if (!connected) return toast.error(t('common.connectWallet'));
    const amount = parseFloat(betAmount);
    if (amount < config.min_bet_sol) return toast.error(`Minimum bet is ${config.min_bet_sol} SOL`);

    setJoining(true);
    setTransferStep('prompting');
    
    try {
      // Step 1: Prompt wallet to transfer SOL to pot escrow
      toast.info("Please approve the SOL transfer to join the pot...");
      setTransferStep('signing');
      
      const signature = await sendSolToEscrow(
        connection,
        wallet,
        config.distribution_wallet,
        amount
      );
      
      setTransferStep('confirming');
      toast.success("Transfer confirmed! Joining pot...");
      
      // Step 2: Register entry on backend with tx signature
      const { data } = await axios.post(`${API}/betting/pot/join`, {
        bet_amount_sol: amount,
        wallet_address: walletAddress,
        display_name: displayName,
        tx_signature: signature
      });
      toast.success(data.message);
      localStorage.setItem("bullpugName", displayName);
      // Start countdown if it just started
      if (data.countdown_just_started && data.countdown_started) {
        setCountdown(60);
        toast.info("⏱️ 60 second countdown started! Draw imminent!");
      }
    } catch (e) {
      if (e.message?.includes('User rejected')) {
        toast.error("Transaction cancelled by user");
      } else {
        toast.error(e.response?.data?.detail || e.message || "Failed to join pot");
      }
    }
    setJoining(false);
    setTransferStep(null);
  };

  const formatCountdown = (seconds) => {
    if (seconds === null || seconds === undefined) return null;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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

          {/* Countdown Timer - Shows when 2+ participants */}
          {pot.countdown_started && countdown !== null && countdown > 0 && (
            <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-[#FF6B6B]/20 to-[#D946EF]/20 border border-[#FF6B6B]/40 animate-pulse">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#FF6B6B]/30 flex items-center justify-center">
                    <span className="text-xl">⏱️</span>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase">Draw Countdown</p>
                    <p className="text-sm text-white">Winner will be selected when timer ends!</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-3xl font-black ${countdown <= 10 ? 'text-[#FF6B6B] animate-bounce' : 'text-[#D946EF]'}`} 
                     style={{ fontFamily: 'Orbitron' }}
                     data-testid="pot-countdown">
                    {formatCountdown(countdown)}
                  </p>
                  <p className="text-[10px] text-slate-500">seconds remaining</p>
                </div>
              </div>
            </div>
          )}

          {/* Waiting for participants message - Enhanced */}
          {!pot.countdown_started && pot.entry_count < 2 && (
            <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-[#D946EF]/10 to-[#00FFA3]/10 border border-[#D946EF]/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full bg-[#D946EF]/20 flex items-center justify-center animate-pulse">
                      <Users className="w-6 h-6 text-[#D946EF]" />
                    </div>
                    {pot.entry_count === 1 && (
                      <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#00FFA3] flex items-center justify-center text-[10px] font-bold text-black">
                        1
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">
                      {pot.entry_count === 0 ? "Be the first to join!" : "1 player waiting..."}
                    </p>
                    <p className="text-xs text-slate-400">
                      {pot.entry_count === 0 
                        ? "Start the pot and wait for a challenger"
                        : "Join now to trigger the 60s countdown!"}
                    </p>
                  </div>
                </div>
                <div className="text-center">
                  <div className="flex items-center gap-1">
                    {[...Array(2)].map((_, i) => (
                      <div 
                        key={i}
                        className={`w-4 h-4 rounded-full border-2 transition-all ${
                          i < (pot.entry_count || 0)
                            ? 'bg-[#00FFA3] border-[#00FFA3]'
                            : 'border-slate-600 bg-transparent'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1">
                    {pot.entry_count || 0}/2 players
                  </p>
                </div>
              </div>
              {pot.entry_count === 1 && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  <p className="text-xs text-center text-[#00FFA3] animate-pulse">
                    ⚡ One more player triggers the countdown! ⚡
                  </p>
                </div>
              )}
            </div>
          )}

          {pot.winner && (
            <div className="p-4 rounded-xl bg-[#00FFA3]/10 border border-[#00FFA3]/30 mb-4">
              <p className="text-sm font-bold text-[#00FFA3]">
                {t('betting.pot.won', { name: pot.winner.winner_name, amount: pot.winner.payout_sol })}
              </p>
            </div>
          )}

          {pot.entries && pot.entries.length > 0 ? (
            <div className="space-y-4">
              {/* SPIN WHEEL - Live Odds Spinner like Solpot */}
              <div className="relative flex justify-center mb-6">
                <div className="relative w-64 h-64">
                  {/* Outer glow ring */}
                  <div className="absolute inset-0 rounded-full bg-gradient-to-r from-[#D946EF]/30 via-[#00FFA3]/30 to-[#D946EF]/30 blur-xl animate-spin" style={{ animationDuration: '8s' }} />
                  
                  {/* Main wheel container */}
                  <div className="absolute inset-2 rounded-full bg-black/80 border-4 border-[#D946EF]/50 overflow-hidden">
                    <svg viewBox="0 0 100 100" className="w-full h-full" style={{ animation: pot.countdown_started && countdown && countdown <= 10 ? 'spin 0.5s linear infinite' : 'spin 3s linear infinite' }}>
                      <defs>
                        {pot.entries.map((entry, i) => (
                          <linearGradient key={`grad-${i}`} id={`segment-grad-${i}`} x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor={`hsl(${(i * 360 / pot.entries.length + 280) % 360}, 70%, 50%)`} />
                            <stop offset="100%" stopColor={`hsl(${(i * 360 / pot.entries.length + 280) % 360}, 80%, 35%)`} />
                          </linearGradient>
                        ))}
                      </defs>
                      
                      {pot.entries.map((entry, i) => {
                        const total = pot.entries.length;
                        const startAngle = (i / total) * 360 - 90;
                        const endAngle = ((i + 1) / total) * 360 - 90;
                        const largeArc = (endAngle - startAngle) > 180 ? 1 : 0;
                        
                        const startRad = (startAngle * Math.PI) / 180;
                        const endRad = (endAngle * Math.PI) / 180;
                        
                        const x1 = 50 + 45 * Math.cos(startRad);
                        const y1 = 50 + 45 * Math.sin(startRad);
                        const x2 = 50 + 45 * Math.cos(endRad);
                        const y2 = 50 + 45 * Math.sin(endRad);
                        
                        return (
                          <path
                            key={i}
                            d={`M 50 50 L ${x1} ${y1} A 45 45 0 ${largeArc} 1 ${x2} ${y2} Z`}
                            fill={`url(#segment-grad-${i})`}
                            stroke="rgba(255,255,255,0.3)"
                            strokeWidth="0.5"
                          />
                        );
                      })}
                      
                      {/* Center circle */}
                      <circle cx="50" cy="50" r="12" fill="url(#center-grad)" stroke="#D946EF" strokeWidth="1" />
                      <defs>
                        <radialGradient id="center-grad">
                          <stop offset="0%" stopColor="#1a1a2e" />
                          <stop offset="100%" stopColor="#0a0a15" />
                        </radialGradient>
                      </defs>
                      
                      {/* Player initials on segments */}
                      {pot.entries.map((entry, i) => {
                        const total = pot.entries.length;
                        const midAngle = ((i + 0.5) / total) * 360 - 90;
                        const midRad = (midAngle * Math.PI) / 180;
                        const textX = 50 + 28 * Math.cos(midRad);
                        const textY = 50 + 28 * Math.sin(midRad);
                        
                        return (
                          <text
                            key={`text-${i}`}
                            x={textX}
                            y={textY}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fill="white"
                            fontSize="6"
                            fontWeight="bold"
                            style={{ textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}
                          >
                            {entry.display_name?.slice(0, 3).toUpperCase() || '???'}
                          </text>
                        );
                      })}
                    </svg>
                  </div>
                  
                  {/* Pointer/Arrow at top */}
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1 z-10">
                    <div className="w-0 h-0 border-l-[12px] border-l-transparent border-r-[12px] border-r-transparent border-t-[20px] border-t-[#00FFA3] drop-shadow-lg" />
                  </div>
                  
                  {/* Center pot amount */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="text-center">
                      <p className="text-2xl font-black text-[#D946EF]" style={{ fontFamily: 'Orbitron', textShadow: '0 0 10px rgba(217,70,239,0.5)' }}>
                        {pot.total_amount_sol?.toFixed(2)}
                      </p>
                      <p className="text-[10px] text-slate-400 uppercase">SOL</p>
                    </div>
                  </div>
                  
                  {/* Spinning particles around wheel */}
                  <div className="absolute inset-0 rounded-full overflow-hidden pointer-events-none">
                    {[...Array(8)].map((_, i) => (
                      <div
                        key={i}
                        className="absolute w-2 h-2 rounded-full bg-[#00FFA3]"
                        style={{
                          top: '50%',
                          left: '50%',
                          transform: `rotate(${i * 45}deg) translateY(-130px)`,
                          animation: `pulse 1.5s ease-in-out ${i * 0.2}s infinite`,
                          opacity: 0.6
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
              
              <style>{`
                @keyframes spin {
                  from { transform: rotate(0deg); }
                  to { transform: rotate(360deg); }
                }
                @keyframes pulse {
                  0%, 100% { opacity: 0.3; transform: scale(0.8) rotate(var(--rotation)) translateY(-130px); }
                  50% { opacity: 1; transform: scale(1.2) rotate(var(--rotation)) translateY(-130px); }
                }
              `}</style>
              
              {/* Participant list */}
              <p className="text-xs text-slate-500 uppercase mb-2">{t('betting.pot.participants')}</p>
              {pot.entries.map((e, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
                      style={{ backgroundColor: `hsl(${(i * 360 / pot.entries.length + 280) % 360}, 70%, 40%)` }}
                    >
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
