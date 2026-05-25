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
import { Zap, Trophy, Users, Wallet, RefreshCw, Swords, Volume2, VolumeX, Loader2, Bone, Skull } from "lucide-react";
import { playSoundIfEnabled, isSoundEnabled, setSoundEnabled, playCoinFlipSequence, winFeedback, loseFeedback, challengeCreatedFeedback, clickFeedback } from "@/utils/sounds";
import "@/styles/animations.css";
import ArenaChat from "@/components/ArenaChat";
import PugPitFaceOff from "@/components/PugPitFaceOff";
import PackRingAvatar from "@/components/PackRingAvatar";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Tier helper — maps a bet amount (SOL) onto the Pug Pit stakes ladder.
 * Drives the stakes-meter label/color and the face-off backdrop tier.
 */
function stakeTier(amountSol) {
  const a = parseFloat(amountSol || 0);
  if (a >= 2)    return { name: "Cosmic Showdown", color: "#FF3A8A", percent: 100 };
  if (a >= 0.5)  return { name: "Coliseum Bout",   color: "#F5D300", percent: 80 };
  if (a >= 0.05) return { name: "Pit Match",       color: "#D946EF", percent: 50 };
  return                  { name: "Backyard Scuffle", color: "#00FFA3", percent: 20 };
}

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
  const [config, setConfig] = useState({ rake_percent: 2.5, distribution_wallet: "", min_bet_sol: 0.005, max_bet_sol: 10 });
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
            {/* Crossed-bone fight stamp on the left */}
            <Bone className="w-6 h-6 sm:w-7 sm:h-7 text-[#00FFA3]" style={{ transform: "rotate(45deg)" }} />
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Orbitron, sans-serif' }} data-testid="arena-title">
              PUG <span className="text-[#00FFA3] neon-text">PIT</span>
            </h1>
            <Skull className="w-6 h-6 sm:w-7 sm:h-7 text-[#D946EF]" />
            <button
              onClick={toggleSound}
              data-testid="sound-toggle"
              className="p-2 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-[#00FFA3]/50 transition-all"
              title={soundOn ? "Mute sounds" : "Enable sounds"}
            >
              {soundOn ? <Volume2 size={18} /> : <VolumeX size={18} />}
            </button>
          </div>
          <p className="text-slate-500 text-sm">Alpha-vs-alpha SOL wagers. {config.rake_percent}% house cut · provably fair · escrowed on-chain.</p>
          <div className="flex items-center justify-center gap-3 mt-3 flex-wrap">
            <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] border-[#00FFA3]/30 text-[10px]">
              <Wallet className="w-3 h-3 mr-1" /> {t('betting.solOnly')}
            </Badge>
            <Badge className="bg-[#F5D300]/10 text-[#F5D300] border-[#F5D300]/30 text-[10px]" data-testid="jackpot-contribution-badge">
              <Trophy className="w-3 h-3 mr-1" /> 25% of cut → Cosmic Runner Jackpot
            </Badge>
            <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px]">
              {t('betting.disclaimer')}
            </Badge>
          </div>
        </div>

        {!connected && (
          <div className="glass-card rounded-2xl p-8 text-center mb-8" data-testid="connect-wallet-prompt">
            <Wallet className="w-12 h-12 mx-auto mb-4 text-slate-600" />
            <p className="text-slate-400 mb-2">Connect your wallet to enter the pit.</p>
            <p className="text-xs text-slate-600">{t('betting.p2pRequiresWallet')}</p>
          </div>
        )}

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="grid w-full grid-cols-2 bg-black/40 border border-white/10 rounded-xl p-1 mb-8">
            <TabsTrigger value="coin-toss" data-testid="tab-coin-toss"
              className="data-[state=active]:bg-[#00FFA3]/10 data-[state=active]:text-[#00FFA3] rounded-lg font-bold text-xs uppercase">
              <Swords className="w-4 h-4 mr-2" />Snarl-Off
            </TabsTrigger>
            <TabsTrigger value="pot" data-testid="tab-pot"
              className="data-[state=active]:bg-[#D946EF]/10 data-[state=active]:text-[#D946EF] rounded-lg font-bold text-xs uppercase">
              <Trophy className="w-4 h-4 mr-2" />Pack Pile
            </TabsTrigger>
          </TabsList>
          <TabsContent value="coin-toss">
            <P2PCoinFlip walletAddress={publicKey?.toBase58()} connected={connected} config={config} wallet={{ publicKey, signTransaction: useWallet().signTransaction }} connection={useConnection().connection} />
          </TabsContent>
          <TabsContent value="pot">
            <P2PPotSystem walletAddress={publicKey?.toBase58()} connected={connected} config={config} wallet={{ publicKey, signTransaction: useWallet().signTransaction }} connection={useConnection().connection} />
          </TabsContent>
        </Tabs>

        {/* Live arena chat — talk smack while you wait for the next draw */}
        <div className="mt-10">
          <ArenaChat />
        </div>
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
  const [playerSkin] = useState(() => {
    try { return localStorage.getItem("bullpugSkin") || "default"; } catch { return "default"; }
  });
  const [creating, setCreating] = useState(false);
  const [accepting, setAccepting] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [isFlipping, setIsFlipping] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [transferStep, setTransferStep] = useState(null); // 'prompting', 'signing', 'confirming'
  // Pug Pit face-off opponent context. Set when the player accepts a
  // challenge (so the face-off card knows whose mini-pug to render on
  // the right) and cleared when the result toast is dismissed.
  const [faceOff, setFaceOff] = useState(null);

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
    // Surface the face-off card with this opponent (creator side) so the
    // player sees their pug squaring off against the creator's.
    setFaceOff({
      opponentWallet: challenge.creator_wallet,
      opponentName: challenge.creator_name || "Challenger",
      mode: "idle",
    });

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
      setFaceOff(prev => prev ? { ...prev, mode: "clashing" } : prev);
      
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
        setFaceOff(prev => prev ? { ...prev, mode: won ? "win" : "loss" } : prev);
        
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
      setFaceOff(null);
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
          <Input type="number" step="0.001" min="0.005" max="10" value={betAmount} onChange={e => setBetAmount(e.target.value)}
            className="bg-black/50 border-white/10 text-white text-lg font-bold" data-testid="bet-amount-input" />
          <div className="flex gap-2 mt-2">
            {["0.005", "0.05", "0.1", "0.5", "1"].map(amt => (
              <button key={amt} onClick={() => setBetAmount(amt)}
                className="text-[10px] px-2 py-1 rounded bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors" data-testid={`quickbet-${amt}`}>
                {amt}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-slate-600 mt-1">Min 0.005 SOL · Max 10 SOL per bet</p>
        </div>

        <div>
          <label className="text-xs text-slate-500 uppercase mb-1 block">Your side</label>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => setChoice("heads")} data-testid="choice-heads"
              className={`py-3 rounded-xl text-sm font-bold uppercase transition-all flex items-center justify-center gap-2 ${
                choice === "heads" ? "bg-[#F5D300] text-black scale-[1.02] shadow-lg shadow-[#F5D300]/30" : "bg-white/5 text-slate-400 hover:bg-white/10"
              }`}>
              <Bone className="w-4 h-4" /> BONE
            </button>
            <button onClick={() => setChoice("tails")} data-testid="choice-tails"
              className={`py-3 rounded-xl text-sm font-bold uppercase transition-all flex items-center justify-center gap-2 ${
                choice === "tails" ? "bg-[#D946EF] text-white scale-[1.02] shadow-lg shadow-[#D946EF]/30" : "bg-white/5 text-slate-400 hover:bg-white/10"
              }`}>
              <Skull className="w-4 h-4" /> SKULL
            </button>
          </div>
        </div>

        {/* Stakes Meter — tier ladder that grows with the bet amount */}
        {(() => {
          const tier = stakeTier(betAmount);
          return (
            <div data-testid="stakes-meter">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase tracking-wider text-slate-500">Stakes</span>
                <span className="text-[10px] uppercase font-bold" style={{ color: tier.color }}>{tier.name}</span>
              </div>
              <div className="relative h-2 rounded-full bg-black/40 border border-white/5 overflow-hidden">
                <div className="pugpit-stakes-track absolute inset-y-0 left-0" style={{ width: `${tier.percent}%`, opacity: 0.85 }} />
              </div>
              <p className="text-[9px] text-slate-600 mt-1">
                Backyard · Pit · Coliseum · Cosmic
              </p>
            </div>
          );
        })()}

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

        {/* Snarl-Off Animation — face-off when an opponent context exists,
            otherwise fall back to the legacy disk-flip */}
        {isFlipping && (
          <div className="glass-card rounded-xl p-6 text-center mb-4" data-testid="snarl-off-animation">
            {faceOff ? (
              <>
                <PugPitFaceOff
                  playerSkin={playerSkin}
                  playerName={displayName}
                  opponentWallet={faceOff.opponentWallet}
                  opponentName={faceOff.opponentName}
                  mode="clashing"
                  size={120}
                />
                <p className="text-amber-400 mt-4 text-sm uppercase font-bold tracking-wider animate-pulse" style={{ fontFamily: "Orbitron, sans-serif" }}>
                  Snarl-Off in progress…
                </p>
              </>
            ) : (
              <div className="coin-flip-animation inline-block">
                <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-[#F5D300] to-[#D4AF37] flex items-center justify-center border-4 border-[#FFE066] shadow-lg">
                  <Bone className="w-9 h-9 text-black" />
                </div>
                <p className="text-slate-400 mt-4 text-sm animate-pulse">Bone vs Skull…</p>
              </div>
            )}
          </div>
        )}

        {result && !isFlipping && (
          <div className={`glass-card rounded-xl p-5 border-2 ${result.won ? "border-[#00FFA3] win-pulse" : "border-red-500 lose-pulse"}`} data-testid="flip-result">
            <div className="text-center">
              {faceOff && (
                <div className="mb-4">
                  <PugPitFaceOff
                    playerSkin={playerSkin}
                    playerName={displayName}
                    opponentWallet={faceOff.opponentWallet}
                    opponentName={faceOff.opponentName}
                    mode={result.won ? "win" : "loss"}
                    size={110}
                  />
                </div>
              )}
              <div className={`coin-result-animation inline-block mb-3`}>
                <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center border-4 ${
                  result.outcome === 'heads' ? 'bg-[#F5D300]/20 border-[#F5D300]' : 'bg-[#D946EF]/20 border-[#D946EF]'
                }`}>
                  {result.outcome === 'heads' ? <Bone className="w-7 h-7 text-[#F5D300]" /> : <Skull className="w-7 h-7 text-[#D946EF]" />}
                </div>
              </div>
              <p className={`text-2xl font-black ${result.won ? "text-[#00FFA3]" : "text-red-400"}`} style={{ fontFamily: 'Orbitron' }}>
                {result.won ? "TOP DOG" : "TAIL TUCKED"}
              </p>
              <p className="text-sm text-slate-400 mt-1">
                {result.won
                  ? `+${result.payout_sol} SOL · Pit landed on `
                  : `Pit landed on `}
                <span className="text-white font-bold uppercase">{result.outcome === 'heads' ? 'BONE' : 'SKULL'}</span>
              </p>
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
            <p className="text-slate-500">No challengers in the pit yet.</p>
            <p className="text-xs text-slate-600 mt-1">Roar first — create a challenge and summon a pack.</p>
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
                  <Badge className={`text-[10px] flex items-center gap-1 ${c.creator_choice === "heads" ? "bg-[#F5D300]/10 text-[#F5D300]" : "bg-[#D946EF]/10 text-[#D946EF]"}`}>
                    {c.creator_choice === "heads" ? <Bone className="w-3 h-3" /> : <Skull className="w-3 h-3" />}
                    {c.creator_choice === "heads" ? "BONE" : "SKULL"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron' }}>{c.bet_amount_sol} SOL</p>
                    <p className="text-[10px] text-slate-500">You get {c.creator_choice === "heads" ? "SKULL" : "BONE"}</p>
                  </div>
                  <Button onClick={() => acceptChallenge(c)} disabled={accepting === c.id || !connected}
                    data-testid={`accept-${c.id}`}
                    className="bg-[#D946EF] text-white font-bold rounded-lg px-4 py-2 text-xs uppercase hover:scale-[1.02] transition-transform">
                    {accepting === c.id ? "Snarling…" : "Enter Pit"}
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
  // Pack-howl celebration — when a winner is announced via WS, set this
  // briefly so the ring can play the bone-drop + winner-rear animation
  // before the pot resets.
  const [winnerCelebration, setWinnerCelebration] = useState(null);

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
        // Hold the celebration on screen for 4s before clearing so the
        // bone-drop + rear/tuck animations have time to play.
        setWinnerCelebration({
          winner_wallet: msg.data.winner_wallet,
          winner_name: msg.data.winner_name,
          payout_sol: msg.data.payout_sol,
        });
        setTimeout(() => setWinnerCelebration(null), 4500);
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
      {/* Join Pack — left column */}
      <div className="glass-card rounded-2xl p-6 space-y-5">
        <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
          <Bone className="w-4 h-4 text-[#F5D300]" /> Howl Into the Pack
        </h3>

        <div>
          <label className="text-xs text-slate-500 uppercase mb-1 block">Your alpha name</label>
          <Input value={displayName} onChange={e => setDisplayName(e.target.value)} maxLength={20}
            className="bg-black/50 border-white/10 text-white" />
        </div>

        <div>
          <label className="text-xs text-slate-500 uppercase mb-1 block">Bone in (SOL)</label>
          <Input type="number" step="0.001" min="0.005" max="10" value={betAmount} onChange={e => setBetAmount(e.target.value)}
            className="bg-black/50 border-white/10 text-white text-lg font-bold" data-testid="pot-bet-input" />
          <div className="flex gap-2 mt-2">
            {["0.005", "0.1", "0.5", "1", "2"].map(amt => (
              <button key={amt} onClick={() => setBetAmount(amt)}
                className="text-[10px] px-2 py-1 rounded bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors" data-testid={`pot-quickbet-${amt}`}>
                {amt}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-slate-600 mt-1">Min 0.005 SOL · the bigger your bone, the louder your howl (up to 10 SOL total).</p>
        </div>

        {/* Stakes Meter — same tier ladder used by Snarl-Off */}
        {(() => {
          const tier = stakeTier(betAmount);
          return (
            <div data-testid="stakes-meter-pack">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase tracking-wider text-slate-500">Pack tier</span>
                <span className="text-[10px] uppercase font-bold" style={{ color: tier.color }}>{tier.name}</span>
              </div>
              <div className="relative h-2 rounded-full bg-black/40 border border-white/5 overflow-hidden">
                <div className="pugpit-stakes-track absolute inset-y-0 left-0" style={{ width: `${tier.percent}%`, opacity: 0.85 }} />
              </div>
            </div>
          );
        })()}

        <div className="p-3 rounded-lg bg-[#D946EF]/10 border border-[#D946EF]/30">
          <p className="text-xs text-slate-400">
            Bigger bone = louder howl = better odds. House takes {pot.rake_percent}%; 25% of that bolsters the Cosmic Runner Jackpot.
          </p>
        </div>

        <Button onClick={joinPot} disabled={joining || !connected} data-testid="join-pot-btn"
          className="w-full bg-gradient-to-r from-[#D946EF] to-[#F5D300] text-black font-bold rounded-xl py-5 text-sm uppercase hover:scale-[1.02] transition-transform">
          {joining ? "Howling…" : "Throw Bone In"}
        </Button>

        <div className="text-center">
          <p className="text-[10px] text-slate-600">
            Pile escrow: <span className="text-slate-400">{config.distribution_wallet?.slice(0, 12)}...</span>
          </p>
        </div>
      </div>

      {/* Pack Pile Status — right column */}
      <div className="lg:col-span-2 space-y-4">
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs text-slate-500 uppercase">Pack Pile</p>
              <p className="text-4xl font-black text-[#F5D300]" style={{ fontFamily: 'Orbitron' }}>
                {pot.total_amount_sol?.toFixed(2) || "0.00"} <span className="text-lg">SOL</span>
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500 uppercase">Pack size</p>
              <p className="text-2xl font-black text-white" style={{ fontFamily: 'Orbitron' }}>{pot.entry_count || 0}</p>
            </div>
          </div>

          {/* Countdown — Pack Howl tension build */}
          {pot.countdown_started && countdown !== null && countdown > 0 && (
            <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-[#FF6B6B]/20 to-[#D946EF]/20 border border-[#FF6B6B]/40 animate-pulse">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#FF6B6B]/30 flex items-center justify-center">
                    <Bone className="w-5 h-5 text-[#F5D300]" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase">Pack Howl in…</p>
                    <p className="text-sm text-white">One alpha walks away with the whole pile.</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-3xl font-black ${countdown <= 10 ? 'text-[#FF6B6B] animate-bounce' : 'text-[#F5D300]'}`} 
                     style={{ fontFamily: 'Orbitron' }}
                     data-testid="pot-countdown">
                    {formatCountdown(countdown)}
                  </p>
                  <p className="text-[10px] text-slate-500">until the howl</p>
                </div>
              </div>
            </div>
          )}

          {/* Waiting for participants */}
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
                      {pot.entry_count === 0 ? "Start the pack." : "Pack of 1. Needs another howl."}
                    </p>
                    <p className="text-xs text-slate-400">
                      {pot.entry_count === 0 
                        ? "Throw the first bone in and wait for the pack to gather."
                        : "One more alpha triggers the 60-second howl."}
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
                    {pot.entry_count || 0}/2 alphas
                  </p>
                </div>
              </div>
              {pot.entry_count === 1 && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  <p className="text-xs text-center text-[#00FFA3] animate-pulse">
                    One more bone triggers the howl
                  </p>
                </div>
              )}
            </div>
          )}

          {(pot.winner || winnerCelebration) && (
            <div className="p-4 rounded-xl bg-[#00FFA3]/10 border border-[#00FFA3]/30 mb-4">
              <p className="text-sm font-bold text-[#00FFA3]">
                TOP DOG: {(winnerCelebration?.winner_name || pot.winner?.winner_name)} took {(winnerCelebration?.payout_sol || pot.winner?.payout_sol)} SOL.
              </p>
            </div>
          )}

          {pot.entries && pot.entries.length > 0 ? (
            <div className="space-y-4">
              {/* ───── HOWL RING — pug avatars circling a golden bone ───── */}
              <div className="relative flex justify-center mb-6" data-testid="howl-ring">
                <div className="relative w-72 h-72">
                  {/* Outer aurora — gold/pink/green swirl behind the ring */}
                  <div className="absolute inset-0 rounded-full bg-gradient-to-r from-[#F5D300]/25 via-[#D946EF]/25 to-[#00FFA3]/25 blur-2xl animate-spin" style={{ animationDuration: '10s' }} />

                  {/* Probability wheel — kept under the avatars for visual
                      "stage" but muted; the real tension is the avatar ring */}
                  <div className="absolute inset-3 rounded-full bg-black/80 border-2 border-[#D946EF]/30 overflow-hidden opacity-60">
                    <svg viewBox="0 0 100 100" className="w-full h-full" style={{ animation: pot.countdown_started && countdown && countdown <= 10 ? 'spin 0.5s linear infinite' : 'spin 6s linear infinite' }}>
                      <defs>
                        {pot.entries.map((entry, i) => (
                          <linearGradient key={`grad-${i}`} id={`segment-grad-${i}`} x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor={`hsl(${(i * 360 / pot.entries.length + 280) % 360}, 70%, 35%)`} />
                            <stop offset="100%" stopColor={`hsl(${(i * 360 / pot.entries.length + 280) % 360}, 80%, 20%)`} />
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
                            stroke="rgba(255,255,255,0.15)"
                            strokeWidth="0.5"
                          />
                        );
                      })}
                    </svg>
                  </div>

                  {/* Center golden bone — pulses idle, drops on winner reveal */}
                  <div
                    className={`absolute top-1/2 left-1/2 ${winnerCelebration ? 'bone-drop' : 'bone-pulse'}`}
                    style={{ transform: 'translate(-50%, -50%)' }}
                    data-testid="pack-center-bone"
                  >
                    <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#FFE680] to-[#D4AF37] flex items-center justify-center border-4 border-[#FFE066] shadow-2xl">
                      <Bone className="w-10 h-10 text-black" strokeWidth={2.5} />
                    </div>
                    <div className="text-center mt-1">
                      <p className="text-[10px] text-[#F5D300] uppercase tracking-wider font-bold" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                        {pot.total_amount_sol?.toFixed(2)} SOL
                      </p>
                    </div>
                  </div>

                  {/* Pug avatars around the ring — capped at 12 visible so
                      the ring stays readable. Beyond that we show a "+N" pip. */}
                  {(() => {
                    const visible = pot.entries.slice(0, 12);
                    const total = visible.length;
                    const radius = 124; // px from center
                    const winnerWallet = winnerCelebration?.winner_wallet || pot.winner?.winner_wallet;
                    const tense = pot.countdown_started && countdown && countdown <= 10;
                    return visible.map((entry, i) => {
                      const angle = (i / total) * Math.PI * 2 - Math.PI / 2;
                      const x = Math.cos(angle) * radius;
                      const y = Math.sin(angle) * radius;
                      const isWinner = winnerWallet && entry.wallet_address === winnerWallet;
                      const isPlayer = walletAddress && entry.wallet_address?.includes(walletAddress.slice(0, 6));
                      let pose = "idle";
                      if (winnerCelebration) pose = isWinner ? "rear" : "tuck";
                      else if (tense) pose = "howl";
                      return (
                        <div
                          key={`av-${i}`}
                          className="absolute top-1/2 left-1/2"
                          style={{ transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))` }}
                        >
                          <PackRingAvatar
                            walletStr={entry.wallet_address}
                            initial={entry.display_name?.charAt(0) || "?"}
                            size={46}
                            pose={pose}
                            isPlayer={isPlayer}
                            forceSkin={isPlayer ? (typeof window !== "undefined" ? localStorage.getItem("bullpugSkin") || "default" : "default") : null}
                          />
                        </div>
                      );
                    });
                  })()}

                  {/* "+N more" pip when pack overflows */}
                  {pot.entries.length > 12 && (
                    <div className="absolute bottom-0 right-0 bg-[#D946EF] text-white text-[10px] font-bold rounded-full px-2 py-1">
                      +{pot.entries.length - 12} more
                    </div>
                  )}
                </div>
              </div>

              <style>{`
                @keyframes spin {
                  from { transform: rotate(0deg); }
                  to { transform: rotate(360deg); }
                }
              `}</style>
              
              {/* The Pack — participant roster */}
              <p className="text-xs text-slate-500 uppercase mb-2">The Pack</p>
              {pot.entries.map((e, i) => {
                const winnerWallet = winnerCelebration?.winner_wallet || pot.winner?.winner_wallet;
                const isWinner = winnerWallet && e.wallet_address === winnerWallet;
                return (
                  <div key={i} className={`flex items-center justify-between p-3 rounded-lg border ${isWinner ? "bg-[#F5D300]/10 border-[#F5D300]/40" : "bg-white/[0.02] border-white/5"}`}>
                    <div className="flex items-center gap-3">
                      <div 
                        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
                        style={{ backgroundColor: `hsl(${(i * 360 / pot.entries.length + 280) % 360}, 70%, 40%)` }}
                      >
                        {e.display_name?.charAt(0) || "?"}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-white flex items-center gap-2">
                          {e.display_name}
                          {isWinner && <span className="text-[10px] text-[#F5D300] font-black uppercase">Top dog</span>}
                        </p>
                        <p className="text-[10px] text-slate-500">{e.wallet_address}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-[#D946EF]">{e.amount_sol} SOL</p>
                      <p className="text-[10px] text-[#00FFA3]">{e.probability}% howl share</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <Bone className="w-10 h-10 mx-auto mb-3 text-slate-700" />
              <p className="text-slate-500">Empty pack. No bones in the pile yet.</p>
            </div>
          )}
        </div>

        <div className="glass-card rounded-xl p-4">
          <p className="text-xs text-slate-500 mb-2">How the howl works</p>
          <ul className="text-xs text-slate-400 space-y-1">
            <li>• Throw a bone in (any size SOL). The bigger the bone, the louder your howl.</li>
            <li>• When two or more alphas are in, a 60-second countdown starts.</li>
            <li>• When the timer hits zero the pack howls and the pile goes to one alpha — odds proportional to bone size.</li>
            <li>• House takes {pot.rake_percent}%. 25% of that swells the Cosmic Runner Jackpot.</li>
          </ul>
        </div>
      </div>

    </div>
  );
}
