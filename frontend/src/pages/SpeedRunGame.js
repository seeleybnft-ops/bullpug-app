import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useWallet } from "@solana/wallet-adapter-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Gamepad2, Play, RotateCcw, Trophy, Shield, Magnet, Zap, Clock, Medal, User, Volume2, VolumeX, Store, Sparkles, Award } from "lucide-react";
import { playSoundIfEnabled, isSoundEnabled, setSoundEnabled, collectFeedback, winFeedback } from "@/utils/sounds";
import { getSkinById } from "@/config/skins";
import SkinStore from "@/components/SkinStore";
import "@/styles/animations.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const MOONCAKE_IMG = "/images/mooncake.png";

const W = 800, H = 340, GROUND_Y = 270, PLAYER_W = 50, PLAYER_H = 50;
const GRAVITY = 0.7, JUMP_FORCE = -13, DOUBLE_JUMP_FORCE = -11;

export default function SpeedRunGame() {
  const { t } = useTranslation();
  const { publicKey, connected } = useWallet();
  const canvasRef = useRef(null);
  const [gameState, setGameState] = useState("idle");
  const [score, setScore] = useState(0);
  const [mooncakes, setMooncakes] = useState(0);
  const [highScore, setHighScore] = useState(() => parseInt(localStorage.getItem("bullpugHighScore") || "0"));
  const [totalMooncakes, setTotalMooncakes] = useState(() => parseInt(localStorage.getItem("bullpugMooncakes") || "0"));
  const [leaderboard, setLeaderboard] = useState([]);
  const [leaderboardMeta, setLeaderboardMeta] = useState({ days_until_reset: 0 });
  const [playerName, setPlayerName] = useState(() => localStorage.getItem("bullpugPlayerName") || "Guardian");
  const [showNameInput, setShowNameInput] = useState(false);
  const [soundOn, setSoundOn] = useState(isSoundEnabled());
  const [showSkinStore, setShowSkinStore] = useState(false);
  const [currentSkinId, setCurrentSkinId] = useState(() => localStorage.getItem("bullpugSkin") || "default");
  const gameRef = useRef(null);
  const animRef = useRef(null);
  const spriteRef = useRef(null);
  const mooncakeRef = useRef(null);

  const currentSkin = getSkinById(currentSkinId);
  const GAME_IMG = currentSkin.image;

  const toggleSound = () => {
    const newValue = !soundOn;
    setSoundOn(newValue);
    setSoundEnabled(newValue);
    if (newValue) playSoundIfEnabled('click');
  };

  const handleSkinSelect = (skinId) => {
    setCurrentSkinId(skinId);
    // Reload sprite image
    const img = new Image(); 
    img.src = getSkinById(skinId).image;
    img.onload = () => { spriteRef.current = img; };
  };

  useEffect(() => {
    const img = new Image(); 
    img.src = GAME_IMG;
    img.onload = () => { spriteRef.current = img; };
    const mc = new Image(); 
    mc.src = MOONCAKE_IMG;
    mc.onload = () => { mooncakeRef.current = mc; };
    fetchLeaderboard();
  }, [GAME_IMG]);

  const fetchLeaderboard = async () => {
    try {
      const { data } = await axios.get(`${API}/leaderboard?limit=10`);
      setLeaderboard(data.leaderboard);
      setLeaderboardMeta({ days_until_reset: data.days_until_reset, next_reset: data.next_reset });
    } catch (e) {
      console.error("Failed to fetch leaderboard");
    }
  };

  const submitScore = async (finalScore, finalMooncakes) => {
    if (finalScore <= 0) return;
    try {
      const { data } = await axios.post(`${API}/leaderboard/submit`, {
        player_name: playerName,
        score: finalScore,
        mooncakes: finalMooncakes
      });
      toast.success(`Rank #${data.rank} this week!`);
      fetchLeaderboard();
    } catch (e) {
      console.error("Failed to submit score");
    }
  };

  const savePlayerName = (name) => {
    const trimmed = name.trim().slice(0, 20) || "Guardian";
    setPlayerName(trimmed);
    localStorage.setItem("bullpugPlayerName", trimmed);
    setShowNameInput(false);
    toast.success(`Name set to ${trimmed}`);
  };

  const initGame = () => ({
    player: { x: 60, y: GROUND_Y - PLAYER_H, vy: 0, jumps: 0, maxJumps: 2 },
    obstacles: [],
    collectibles: [],
    particles: [],
    powerups: [],
    activePowerups: { shield: 0, magnet: 0, doubleScore: 0 },
    frame: 0,
    speed: 4.5,
    score: 0,
    mooncakes: 0,
    combo: 0,
    comboTimer: 0,
    running: true,
    difficulty: 1,
    groundOffset: 0,
    skinBonus: currentSkin.bonusPercent / 100, // Apply skin bonus
  });

  const startGame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      console.error("Canvas not found!");
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      console.error("Could not get 2d context!");
      return;
    }
    console.log("Starting game, canvas:", canvas.width, canvas.height);
    gameRef.current = initGame();
    setGameState("playing");
    setScore(0);
    setMooncakes(0);
    playSoundIfEnabled('click');

    const loop = () => {
      const g = gameRef.current;
      if (!g || !g.running) return;
      g.frame++;
      g.difficulty = 1 + g.frame * 0.0003;
      g.speed = 4.5 + g.difficulty * 1.5;
      // Apply skin bonus to base score
      const baseScore = Math.floor(g.frame / 4);
      g.score = Math.floor(baseScore * (1 + g.skinBonus));
      g.groundOffset = (g.groundOffset + g.speed) % 40;
      if (g.comboTimer > 0) g.comboTimer--;
      else g.combo = 0;

      // Decay powerups
      for (const k of Object.keys(g.activePowerups)) {
        if (g.activePowerups[k] > 0) g.activePowerups[k]--;
      }

      // Physics
      g.player.vy += GRAVITY;
      g.player.y += g.player.vy;
      if (g.player.y >= GROUND_Y - PLAYER_H) {
        g.player.y = GROUND_Y - PLAYER_H;
        g.player.vy = 0;
        g.player.jumps = 0;
      }

      // Spawn obstacles
      const obstFreq = Math.max(35, 75 - Math.floor(g.difficulty * 8));
      if (g.frame % obstFreq === 0) {
        const h = 25 + Math.random() * 30 * g.difficulty;
        const types = ["meteor", "spike", "asteroid"];
        g.obstacles.push({ x: W + 20, w: 18 + Math.random() * 15, h: Math.min(h, 65), type: types[Math.floor(Math.random() * types.length)] });
      }

      // Spawn mooncakes
      if (g.frame % Math.max(25, 55 - Math.floor(g.difficulty * 3)) === 0) {
        const yPos = GROUND_Y - 60 - Math.random() * 120;
        g.collectibles.push({ x: W + 20, y: yPos, w: 28, h: 28, collected: false, glow: 0 });
      }

      // Spawn powerups (rare)
      if (g.frame % 300 === 0 && Math.random() < 0.5) {
        const types = ["shield", "magnet", "doubleScore"];
        const t = types[Math.floor(Math.random() * types.length)];
        g.powerups.push({ x: W + 20, y: GROUND_Y - 100 - Math.random() * 80, w: 24, h: 24, type: t });
      }

      // Move entities
      g.obstacles = g.obstacles.filter(o => { o.x -= g.speed; return o.x > -50; });
      g.collectibles = g.collectibles.filter(c => {
        c.x -= g.speed * 0.9;
        c.glow = (c.glow + 0.05) % (Math.PI * 2);
        // Magnet effect
        if (g.activePowerups.magnet > 0 && !c.collected) {
          const dx = g.player.x + PLAYER_W / 2 - c.x;
          const dy = g.player.y + PLAYER_H / 2 - c.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) { c.x += dx * 0.08; c.y += dy * 0.08; }
        }
        return c.x > -40 && !c.collected;
      });
      g.powerups = g.powerups.filter(p => { p.x -= g.speed; return p.x > -40; });

      // Update particles
      g.particles = g.particles.filter(p => { p.x += p.vx; p.y += p.vy; p.vy += 0.1; p.life--; return p.life > 0; });

      // Collision detection
      const px = g.player.x + 8, py = g.player.y + 5, pw = PLAYER_W - 16, ph = PLAYER_H - 10;

      // Obstacle collision
      if (g.activePowerups.shield <= 0) {
        for (const o of g.obstacles) {
          if (px + pw > o.x + 4 && px < o.x + o.w - 4 && py + ph > GROUND_Y - o.h) {
            g.running = false;
            setGameState("over");
            setScore(g.score);
            setMooncakes(g.mooncakes);
            const newTotal = totalMooncakes + g.mooncakes;
            setTotalMooncakes(newTotal);
            localStorage.setItem("bullpugMooncakes", String(newTotal));
            if (g.score > highScore) { 
              setHighScore(g.score); 
              localStorage.setItem("bullpugHighScore", String(g.score));
              winFeedback();
              playSoundIfEnabled('newHighScore');
            } else {
              playSoundIfEnabled('gameover');
            }
            // Submit to leaderboard
            submitScore(g.score, g.mooncakes);
            return;
          }
        }
      }

      // Collectible pickup
      for (const c of g.collectibles) {
        if (!c.collected && px + pw > c.x && px < c.x + c.w && py + ph > c.y && py < c.y + c.h) {
          c.collected = true;
          g.mooncakes++;
          g.combo++;
          g.comboTimer = 60;
          collectFeedback();
          const pts = g.activePowerups.doubleScore > 0 ? 2 : 1;
          // Apply skin bonus to collectible points
          const collectPoints = Math.floor(25 * pts * Math.min(g.combo, 5) * (1 + g.skinBonus));
          g.score += collectPoints;
          // Enhanced particle burst - circular explosion
          for (let i = 0; i < 12; i++) {
            const angle = (Math.PI * 2 / 12) * i;
            const speed = 3 + Math.random() * 2;
            g.particles.push({ 
              x: c.x + 14, 
              y: c.y + 14, 
              vx: Math.cos(angle) * speed, 
              vy: Math.sin(angle) * speed - 2, 
              life: 30, 
              color: `hsl(${40 + Math.random() * 20}, 100%, ${60 + Math.random() * 30}%)` 
            });
          }
        }
      }

      // Powerup pickup
      for (let i = g.powerups.length - 1; i >= 0; i--) {
        const p = g.powerups[i];
        if (px + pw > p.x && px < p.x + p.w && py + ph > p.y && py < p.y + p.h) {
          g.activePowerups[p.type] = 300;
          g.powerups.splice(i, 1);
          playSoundIfEnabled('powerup');
          // Enhanced powerup particle burst
          for (let j = 0; j < 16; j++) {
            const angle = (Math.PI * 2 / 16) * j;
            const speed = 4 + Math.random() * 3;
            const clr = p.type === "shield" ? "#00C2FF" : p.type === "magnet" ? "#D946EF" : "#F5D300";
            g.particles.push({ 
              x: p.x + 12, 
              y: p.y + 12, 
              vx: Math.cos(angle) * speed, 
              vy: Math.sin(angle) * speed, 
              life: 35, 
              color: clr 
            });
          }
        }
      }

      setScore(g.score);
      setMooncakes(g.mooncakes);

      // ===== DRAW =====
      ctx.fillStyle = "#05050A";
      ctx.fillRect(0, 0, W, H);

      // Distant stars
      for (let i = 0; i < 40; i++) {
        const sx = (i * 137 + g.frame * (0.1 + (i % 3) * 0.1)) % W;
        const sy = (i * 97 + Math.sin(g.frame * 0.01 + i) * 2) % (GROUND_Y - 20);
        const alpha = 0.15 + Math.sin(g.frame * 0.03 + i * 2) * 0.15;
        ctx.fillStyle = i % 5 === 0 ? `rgba(0,255,163,${alpha})` : `rgba(255,255,255,${alpha})`;
        ctx.fillRect(sx, sy, 1 + (i % 2), 1 + (i % 2));
      }

      // Ground
      ctx.strokeStyle = "#00FFA3";
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(0, GROUND_Y); ctx.lineTo(W, GROUND_Y); ctx.stroke();

      // Ground grid
      ctx.strokeStyle = "rgba(0,255,163,0.06)";
      ctx.lineWidth = 0.5;
      for (let gx = -g.groundOffset; gx < W; gx += 40) {
        ctx.beginPath(); ctx.moveTo(gx, GROUND_Y); ctx.lineTo(gx + 15, H); ctx.stroke();
      }
      ctx.fillStyle = "rgba(0,255,163,0.02)";
      ctx.fillRect(0, GROUND_Y, W, H - GROUND_Y);

      // Obstacles
      for (const o of g.obstacles) {
        if (o.type === "meteor") {
          const grad = ctx.createLinearGradient(o.x, GROUND_Y - o.h, o.x, GROUND_Y);
          grad.addColorStop(0, "#FF3B30"); grad.addColorStop(1, "#991b1b");
          ctx.fillStyle = grad;
          ctx.beginPath(); ctx.moveTo(o.x + o.w / 2, GROUND_Y - o.h); ctx.lineTo(o.x + o.w, GROUND_Y); ctx.lineTo(o.x, GROUND_Y); ctx.closePath(); ctx.fill();
          ctx.fillStyle = "rgba(255,59,48,0.15)";
          ctx.beginPath(); ctx.arc(o.x + o.w / 2, GROUND_Y - o.h * 0.4, o.w * 0.8, 0, Math.PI * 2); ctx.fill();
        } else if (o.type === "asteroid") {
          ctx.fillStyle = "#6b7280";
          ctx.beginPath(); ctx.arc(o.x + o.w / 2, GROUND_Y - o.h / 2, o.h / 2, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = "rgba(107,114,128,0.2)";
          ctx.beginPath(); ctx.arc(o.x + o.w / 2, GROUND_Y - o.h / 2, o.h / 2 + 4, 0, Math.PI * 2); ctx.fill();
        } else {
          ctx.fillStyle = "#F5D300";
          ctx.fillRect(o.x, GROUND_Y - o.h, o.w, o.h);
          ctx.fillStyle = "rgba(245,211,0,0.15)";
          ctx.fillRect(o.x - 3, GROUND_Y - o.h - 3, o.w + 6, o.h + 6);
        }
      }

      // Mooncake collectibles
      for (const c of g.collectibles) {
        if (c.collected) continue;
        const glowSize = 3 + Math.sin(c.glow) * 2;
        ctx.fillStyle = `rgba(245,211,0,${0.1 + Math.sin(c.glow) * 0.05})`;
        ctx.beginPath(); ctx.arc(c.x + 14, c.y + 14, 18 + glowSize, 0, Math.PI * 2); ctx.fill();
        if (mooncakeRef.current) {
          ctx.drawImage(mooncakeRef.current, c.x, c.y, c.w, c.h);
        } else {
          ctx.fillStyle = "#F5D300";
          ctx.beginPath(); ctx.arc(c.x + 14, c.y + 14, 12, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = "#000"; ctx.font = "8px sans-serif"; ctx.textAlign = "center";
          ctx.fillText("MC", c.x + 14, c.y + 17); ctx.textAlign = "left";
        }
      }

      // Powerups
      for (const p of g.powerups) {
        const colors = { shield: "#00C2FF", magnet: "#D946EF", doubleScore: "#F5D300" };
        const clr = colors[p.type];
        ctx.fillStyle = `${clr}30`;
        ctx.beginPath(); ctx.arc(p.x + 12, p.y + 12, 16, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = clr; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(p.x + 12, p.y + 12, 12, 0, Math.PI * 2); ctx.stroke();
        ctx.fillStyle = clr; ctx.font = "bold 10px sans-serif"; ctx.textAlign = "center";
        const icons = { shield: "S", magnet: "M", doubleScore: "2x" };
        ctx.fillText(icons[p.type], p.x + 12, p.y + 16);
        ctx.textAlign = "left";
      }

      // Player
      if (g.activePowerups.shield > 0) {
        ctx.strokeStyle = `rgba(0,194,255,${0.4 + Math.sin(g.frame * 0.1) * 0.2})`;
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(g.player.x + PLAYER_W / 2, g.player.y + PLAYER_H / 2, 32, 0, Math.PI * 2); ctx.stroke();
      }
      if (spriteRef.current) {
        ctx.drawImage(spriteRef.current, g.player.x, g.player.y, PLAYER_W, PLAYER_H);
      } else {
        ctx.fillStyle = "#D946EF";
        ctx.fillRect(g.player.x, g.player.y, PLAYER_W, PLAYER_H);
      }

      // Player glow
      const pGrad = ctx.createRadialGradient(g.player.x + PLAYER_W / 2, GROUND_Y, 0, g.player.x + PLAYER_W / 2, GROUND_Y, 25);
      pGrad.addColorStop(0, "rgba(0,255,163,0.25)"); pGrad.addColorStop(1, "transparent");
      ctx.fillStyle = pGrad;
      ctx.fillRect(g.player.x - 5, GROUND_Y - 5, PLAYER_W + 10, 12);

      // Particles
      for (const p of g.particles) {
        ctx.fillStyle = p.color || "#F5D300";
        ctx.globalAlpha = p.life / 30;
        ctx.fillRect(p.x - 2, p.y - 2, 4, 4);
      }
      ctx.globalAlpha = 1;

      // HUD
      ctx.textAlign = "right";
      ctx.fillStyle = "#00FFA3"; ctx.font = "bold 14px Orbitron, monospace";
      ctx.fillText(`SCORE: ${g.score}`, W - 15, 22);
      ctx.fillStyle = "#F5D300";
      ctx.fillText(`MOONCAKE: ${g.mooncakes}`, W - 15, 40);
      ctx.fillStyle = "#94a3b8"; ctx.font = "10px monospace";
      ctx.fillText(`BEST: ${Math.max(g.score, highScore)}`, W - 15, 55);

      // Combo display
      if (g.combo > 1 && g.comboTimer > 0) {
        ctx.fillStyle = "#F5D300"; ctx.font = "bold 16px Orbitron, monospace";
        ctx.fillText(`x${g.combo} COMBO!`, W / 2 + 40, 30);
      }

      // Active powerup indicators
      ctx.textAlign = "left";
      let pIdx = 0;
      for (const [k, v] of Object.entries(g.activePowerups)) {
        if (v > 0) {
          const colors = { shield: "#00C2FF", magnet: "#D946EF", doubleScore: "#F5D300" };
          ctx.fillStyle = colors[k]; ctx.font = "bold 10px monospace";
          ctx.fillText(`${k.toUpperCase()} ${Math.ceil(v / 60)}s`, 15, 22 + pIdx * 16);
          pIdx++;
        }
      }
      ctx.textAlign = "left";

      animRef.current = requestAnimationFrame(loop);
    };
    animRef.current = requestAnimationFrame(loop);
  }, [highScore, totalMooncakes, playerName, submitScore]);

  const jump = useCallback(() => {
    const g = gameRef.current;
    if (!g || !g.running) return;
    if (g.player.jumps < g.player.maxJumps) {
      g.player.vy = g.player.jumps === 0 ? JUMP_FORCE : DOUBLE_JUMP_FORCE;
      g.player.jumps++;
      playSoundIfEnabled('jump');
      for (let i = 0; i < 5; i++) {
        g.particles.push({ x: g.player.x + PLAYER_W / 2, y: g.player.y + PLAYER_H, vx: (Math.random() - 0.5) * 3, vy: Math.random() * 2, life: 15, color: "rgba(0,255,163,0.6)" });
      }
    }
  }, []);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.code === "Space" || e.code === "ArrowUp") {
        e.preventDefault();
        if (gameState === "playing") jump();
        else startGame();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => { window.removeEventListener("keydown", handleKey); if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [gameState, jump, startGame]);

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      
      {/* Skin Store Modal */}
      <SkinStore 
        isOpen={showSkinStore} 
        onClose={() => setShowSkinStore(false)}
        onSkinSelect={handleSkinSelect}
        currentSkinId={currentSkinId}
      />

      <div className="max-w-5xl mx-auto px-6 md:px-12">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-3">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Orbitron, sans-serif' }} data-testid="game-title">
              {t('game.title').split(' ')[0]} <span className="text-[#F5D300]">{t('game.title').split(' ')[1] || 'Run'}</span>
            </h1>
            <button
              onClick={() => setShowSkinStore(true)}
              data-testid="skin-store-btn"
              className="p-2 rounded-full bg-[#D946EF]/10 border border-[#D946EF]/30 text-[#D946EF] hover:bg-[#D946EF]/20 hover:border-[#D946EF]/50 transition-all"
              title="Skin Store"
            >
              <Store size={18} />
            </button>
            <Link
              to={connected ? `/showcase/${publicKey?.toBase58()}` : "/showcase"}
              data-testid="showcase-btn"
              className="p-2 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30 text-[#00FFA3] hover:bg-[#00FFA3]/20 hover:border-[#00FFA3]/50 transition-all"
              title="My Collection"
            >
              <Award size={18} />
            </Link>
            <button
              onClick={toggleSound}
              data-testid="game-sound-toggle"
              className="p-2 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-[#F5D300]/50 transition-all"
              title={soundOn ? "Mute sounds" : "Enable sounds"}
            >
              {soundOn ? <Volume2 size={18} /> : <VolumeX size={18} />}
            </button>
          </div>
          <p className="text-slate-500 text-sm">{t('game.subtitle')}</p>
          
          {/* Current Skin Indicator */}
          {currentSkin.bonusPercent > 0 && (
            <div className="inline-flex items-center gap-2 mt-2 px-3 py-1 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30">
              <img src={currentSkin.image} alt={currentSkin.name} className="w-5 h-5 rounded-full object-cover" />
              <span className="text-xs text-[#00FFA3] font-bold">{currentSkin.name}</span>
              <Badge className="bg-[#F5D300]/10 text-[#F5D300] border-[#F5D300]/30 text-[10px]">
                <Sparkles className="w-3 h-3 mr-1" /> +{currentSkin.bonusPercent}% Bonus
              </Badge>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Game Canvas */}
          <div className="lg:col-span-3">
            <div className="glass-card rounded-2xl p-4 md:p-6">
              {/* Player Name */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-[#00FFA3]" />
                  {showNameInput ? (
                    <div className="flex items-center gap-2">
                      <Input 
                        defaultValue={playerName}
                        maxLength={20}
                        className="w-32 h-8 bg-black/50 border-white/10 text-white text-sm"
                        onKeyDown={(e) => { if (e.key === "Enter") savePlayerName(e.target.value); }}
                        autoFocus
                      />
                      <button onClick={(e) => savePlayerName(e.target.previousSibling.value)} className="text-xs text-[#00FFA3] hover:underline">{t('common.save')}</button>
                    </div>
                  ) : (
                    <button onClick={() => setShowNameInput(true)} className="text-sm text-white hover:text-[#00FFA3] transition-colors">
                      {playerName}
                    </button>
                  )}
                </div>
                <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px]">
                  <Clock className="w-3 h-3 mr-1" />
                  {t('game.resetsIn', { days: leaderboardMeta.days_until_reset })}
                </Badge>
              </div>

              <div className="relative mx-auto" style={{ maxWidth: W }}>
                <canvas ref={canvasRef} width={W} height={H}
                  onClick={() => gameState === "playing" ? jump() : startGame()}
                  onTouchStart={(e) => { e.preventDefault(); gameState === "playing" ? jump() : startGame(); }}
                  className="w-full rounded-xl border-2 border-[#00FFA3]/20 cursor-pointer bg-[#05050A]"
                  data-testid="game-canvas" />

                {gameState === "idle" && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 rounded-xl">
                    <img src={GAME_IMG} alt="Bullpug" className="w-20 h-20 rounded-xl mb-3 border-2 border-[#00FFA3]/50" />
                    <Button onClick={startGame} data-testid="start-game-btn"
                      className="bg-[#00FFA3] text-black font-bold rounded-full px-8 py-5 text-sm uppercase hover:scale-105 transition-transform shadow-[0_0_20px_rgba(0,255,163,0.4)]">
                      <Play className="w-5 h-5 mr-2" /> {t('game.startGame')}
                    </Button>
                    <p className="text-xs text-slate-500 mt-3">{t('game.spaceToJump')}</p>
                  </div>
                )}

                {gameState === "over" && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/75 rounded-xl" data-testid="game-over-screen">
                    <p className="text-3xl font-black text-red-400 mb-1" style={{ fontFamily: 'Orbitron, sans-serif' }}>{t('game.gameOver')}</p>
                    <p className="text-lg font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>{t('game.score')}: {score}</p>
                    <div className="flex items-center gap-2 my-2">
                      <img src={MOONCAKE_IMG} alt="Mooncake" className="w-5 h-5 rounded" />
                      <span className="text-[#F5D300] font-bold">+{mooncakes} {t('game.mooncake')}</span>
                    </div>
                    {score >= highScore && score > 0 && <Badge className="bg-[#F5D300]/10 text-[#F5D300] border-[#F5D300]/30 mb-2">{t('game.newHighScore')}</Badge>}
                    <div className="flex items-center gap-2 mt-2">
                      <Button onClick={startGame} data-testid="restart-game-btn"
                        className="bg-[#00FFA3] text-black font-bold rounded-full px-6 py-3 text-sm uppercase hover:scale-105 transition-transform">
                        <RotateCcw className="w-4 h-4 mr-2" /> {t('game.playAgain')}
                      </Button>
                      <Button 
                        onClick={() => {
                          const text = t('game.shareText', { score }) + `\n\nPlay now at bullpug.com #Bullpug #Memecoin #Solana`;
                          window.open(`https://x.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
                        }}
                        data-testid="share-x-btn"
                        className="bg-black text-white border border-white/20 font-bold rounded-full px-4 py-3 text-sm uppercase hover:bg-white/10 transition-colors">
                        {t('game.shareOnX')} 𝕏
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mt-4 px-2">
                <div className="flex items-center gap-6">
                  <div>
                <p className="text-xs text-slate-500">{t('game.score')}</p>
                <p className="text-xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>{score}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">{t('game.highScore')}</p>
                <p className="text-xl font-black text-[#F5D300]" style={{ fontFamily: 'Orbitron, sans-serif' }}>{highScore}</p>
              </div>
              <div className="flex items-center gap-2">
                <img src={MOONCAKE_IMG} alt="Mooncake" className="w-6 h-6 rounded" />
                <div>
                  <p className="text-xs text-slate-500">{t('game.totalMooncake')}</p>
                  <p className="text-lg font-black text-[#F5D300]" style={{ fontFamily: 'Orbitron, sans-serif' }}>{totalMooncakes}</p>
                </div>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500 flex items-center gap-1 justify-end"><Gamepad2 className="w-3 h-3" /> {t('game.controls')}</p>
              <div className="flex gap-3 mt-1">
                {[
                  { icon: <Shield size={12} />, label: t('game.shield'), color: "#00C2FF" },
                  { icon: <Magnet size={12} />, label: t('game.magnet'), color: "#D946EF" },
                  { icon: <Zap size={12} />, label: t('game.doubleScore'), color: "#F5D300" },
                ].map((pw, i) => (
                  <div key={i} className="flex items-center gap-1 text-[10px]" style={{ color: pw.color }}>
                    {pw.icon} {pw.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
            </div>
          </div>

          {/* Leaderboard Sidebar */}
          <div className="glass-card rounded-2xl p-5 h-fit sticky top-20">
            <h3 className="text-sm font-bold uppercase mb-4 flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              <Trophy className="w-4 h-4 text-[#F5D300]" /> {t('game.weeklyLeaderboard')}
            </h3>
            <div className="space-y-2">
              {leaderboard.length === 0 ? (
                <p className="text-xs text-slate-600 text-center py-4">{t('game.noScoresYet')}</p>
              ) : (
                leaderboard.map((entry, i) => (
                  <div 
                    key={entry.id} 
                    className={`flex items-center justify-between p-2.5 rounded-lg border transition-colors ${
                      i === 0 ? "border-[#F5D300]/30 bg-[#F5D300]/5" :
                      i === 1 ? "border-slate-400/20 bg-slate-400/5" :
                      i === 2 ? "border-amber-700/20 bg-amber-700/5" :
                      "border-white/5 bg-white/[0.02]"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black ${
                        i === 0 ? "bg-[#F5D300] text-black" :
                        i === 1 ? "bg-slate-400 text-black" :
                        i === 2 ? "bg-amber-700 text-white" :
                        "bg-white/10 text-slate-400"
                      }`}>
                        {i < 3 ? <Medal size={12} /> : i + 1}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-white">{entry.player_name}</p>
                        <p className="text-[10px] text-slate-500">{entry.mooncakes} {t('game.mooncakes')}</p>
                      </div>
                    </div>
                    <p className="text-sm font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                      {entry.score}
                    </p>
                  </div>
                ))
              )}
            </div>
            <p className="text-[10px] text-slate-600 text-center mt-4">
              {t('game.resetMonday')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
