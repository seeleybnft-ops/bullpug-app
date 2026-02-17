import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useWallet } from "@solana/wallet-adapter-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Play, RotateCcw, Clock, User, Volume2, VolumeX, Store, Sparkles, Award, ChevronLeft, ChevronRight, ArrowUp } from "lucide-react";
import { playSoundIfEnabled, isSoundEnabled, setSoundEnabled, collectFeedback, winFeedback } from "@/utils/sounds";
import { getSkinById, SKINS } from "@/config/skins";
import SkinStore from "@/components/SkinStore";
import "@/styles/animations.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Game dimensions
const W = 800, H = 500;
const LANE_COUNT = 3;
const LANE_WIDTH = 100;

// Physics
const GRAVITY = 0.8;
const JUMP_FORCE = -16;

// 3D Perspective settings
const HORIZON_Y = 120;
const GROUND_Y = 420;
const VANISHING_X = W / 2;
const PLAYER_BASE_Y = GROUND_Y - 80;

// Character animation frames
const ANIM_RUN_FRAMES = 8;
const ANIM_JUMP_FRAMES = 4;

// Power-up configuration - Bullpug Lore themed
const POWERUP_TYPES = {
  shield: {
    name: 'Guardian Shield',
    description: 'Cosmic protection from one hit',
    color: '#00FFFF',
    glowColor: 'rgba(0, 255, 255, 0.6)',
    icon: '🛡️',
    duration: 10000 // 10 seconds
  },
  magnet: {
    name: 'Mooncake Magnet', 
    description: 'Attracts mooncakes from all lanes',
    color: '#FFD700',
    glowColor: 'rgba(255, 215, 0, 0.6)',
    icon: '🧲',
    duration: 10000
  },
  doubleScore: {
    name: 'Star Power',
    description: 'Double points from cosmic energy',
    color: '#FF00FF',
    glowColor: 'rgba(255, 0, 255, 0.6)',
    icon: '⭐',
    duration: 10000
  }
};

const POWERUP_SPAWN_INTERVAL = 720; // Every 12 seconds at 60fps

// Stage-specific background themes
const STAGE_BACKGROUNDS = {
  1: { name: 'Deep Space', hue: 240, nebulaDensity: 3, starBrightness: 0.7 },
  2: { name: 'Blue Nebula', hue: 200, nebulaDensity: 5, starBrightness: 0.8 },
  3: { name: 'Purple Galaxy', hue: 280, nebulaDensity: 6, starBrightness: 0.9 },
  4: { name: 'Cosmic Fire', hue: 20, nebulaDensity: 7, starBrightness: 1.0 },
  5: { name: 'Multiverse', hue: -1, nebulaDensity: 8, starBrightness: 1.0 } // -1 = rainbow
};

// Obstacle stages - adjusted for halved points
const OBSTACLE_STAGES = {
  1: { score: 0, types: ['meteor'] },
  2: { score: 250, types: ['meteor', 'debris'] },       // Was 500
  3: { score: 500, types: ['meteor', 'debris', 'blackhole'] },  // Was 1000
  4: { score: 1000, types: ['meteor', 'debris', 'blackhole', 'satellite'] },  // Was 2000
  5: { score: 1500, types: ['meteor', 'debris', 'blackhole', 'satellite', 'alienship'] }  // Was 3000
};

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
  const [currentStage, setCurrentStage] = useState(1);
  const gameRef = useRef(null);
  const animRef = useRef(null);
  const spriteRef = useRef(null);
  const keysRef = useRef({ left: false, right: false, jump: false });

  const currentSkin = getSkinById(currentSkinId);

  const toggleSound = () => {
    const newValue = !soundOn;
    setSoundOn(newValue);
    setSoundEnabled(newValue);
    if (newValue) playSoundIfEnabled('click');
  };

  const handleSkinSelect = (skinId) => {
    setCurrentSkinId(skinId);
    localStorage.setItem("bullpugSkin", skinId);
  };

  // Preload character sprite
  useEffect(() => {
    const img = new Image();
    img.src = currentSkin.image;
    img.onload = () => { spriteRef.current = img; };
  }, [currentSkin.image]);

  const fetchLeaderboard = async () => {
    try {
      const { data } = await axios.get(`${API}/leaderboard?limit=10`);
      setLeaderboard(data.leaderboard);
      setLeaderboardMeta({ days_until_reset: data.days_until_reset, next_reset: data.next_reset });
    } catch (e) { console.error("Leaderboard fetch failed"); }
  };

  useEffect(() => { fetchLeaderboard(); }, []);

  const submitScore = async (finalScore, finalMooncakes) => {
    if (finalScore <= 0) return;
    try {
      const { data } = await axios.post(`${API}/leaderboard/submit`, {
        player_name: playerName, score: finalScore, mooncakes: finalMooncakes
      });
      toast.success(`Rank #${data.rank} this week!`);
      fetchLeaderboard();
    } catch (e) { console.error("Score submit failed"); }
  };

  const savePlayerName = (name) => {
    const trimmed = name.trim().slice(0, 20) || "Guardian";
    setPlayerName(trimmed);
    localStorage.setItem("bullpugPlayerName", trimmed);
    setShowNameInput(false);
    toast.success(`Name set to ${trimmed}`);
  };

  const getCurrentStage = (score) => {
    for (let i = 5; i >= 1; i--) {
      if (score >= OBSTACLE_STAGES[i].score) return i;
    }
    return 1;
  };

  // Get lane X position based on perspective depth (0 = horizon, 1 = player level)
  const getLaneX = (lane, depth) => {
    const spreadAtBottom = LANE_WIDTH * 1.8;
    const spreadAtHorizon = 20;
    const spread = spreadAtHorizon + (spreadAtBottom - spreadAtHorizon) * depth;
    return VANISHING_X + (lane - 1) * spread;
  };

  // Get Y position based on depth
  const getDepthY = (depth) => {
    return HORIZON_Y + (GROUND_Y - HORIZON_Y) * depth;
  };

  // Get scale based on depth
  const getDepthScale = (depth) => {
    return 0.15 + depth * 0.85;
  };

  const initGame = () => ({
    player: {
      lane: 1,
      targetLane: 1,
      y: PLAYER_BASE_Y,
      vy: 0,
      isJumping: false,
      animFrame: 0,
      animTimer: 0,
      laneTransition: 0
    },
    obstacles: [],
    collectibles: [],
    powerups: [],
    particles: [],
    // Active power-up effects
    activePowerups: {
      shield: null,    // { endTime: timestamp }
      magnet: null,
      doubleScore: null
    },
    lastPowerupSpawn: 0,
    // Dynamic background elements
    stars: Array.from({ length: 200 }, () => ({
      x: Math.random() * W,
      y: Math.random() * HORIZON_Y * 1.5,
      z: Math.random(), // depth for parallax
      size: Math.random() * 2.5 + 0.5,
      twinkle: Math.random() * Math.PI * 2,
      speed: 0.2 + Math.random() * 0.5
    })),
    nebulas: Array.from({ length: 12 }, () => ({
      x: Math.random() * W * 1.5,
      y: Math.random() * HORIZON_Y,
      z: Math.random() * 0.8 + 0.2, // depth
      size: 80 + Math.random() * 150,
      hue: Math.random() * 360,
      alpha: 0.06 + Math.random() * 0.1,
      speed: 0.3 + Math.random() * 0.5
    })),
    // Distant galaxies/planets
    cosmicObjects: Array.from({ length: 5 }, () => ({
      x: Math.random() * W,
      y: 20 + Math.random() * (HORIZON_Y - 40),
      size: 15 + Math.random() * 40,
      type: Math.random() > 0.5 ? 'galaxy' : 'planet',
      hue: Math.random() * 360,
      rotation: Math.random() * Math.PI * 2,
      speed: 0.1 + Math.random() * 0.2
    })),
    backgroundHue: 240,
    frame: 0,
    speed: 2.5,
    startTime: Date.now(),
    score: 0,
    mooncakes: 0,
    running: true,
    stage: 1,
    trackOffset: 0,
    skinBonus: currentSkin.bonusPercent / 100,
    skinColor: currentSkin.color
  });

  // Check if a lane/depth position is too close to existing objects
  const isPositionClear = (g, lane, depth, minSeparation = 0.15) => {
    // Check obstacles
    for (const o of g.obstacles) {
      if (o.lane === lane && Math.abs(o.depth - depth) < minSeparation) {
        return false;
      }
    }
    // Check collectibles
    for (const c of g.collectibles) {
      if (c.lane === lane && Math.abs(c.depth - depth) < minSeparation) {
        return false;
      }
    }
    // Check power-ups
    for (const p of g.powerups) {
      if (p.lane === lane && Math.abs(p.depth - depth) < minSeparation) {
        return false;
      }
    }
    return true;
  };

  // Spawn power-up - shiny cosmic items
  const spawnPowerup = (g) => {
    const types = Object.keys(POWERUP_TYPES);
    const type = types[Math.floor(Math.random() * types.length)];
    
    // Find clear lane
    let lane = Math.floor(Math.random() * LANE_COUNT);
    for (let attempts = 0; attempts < 5; attempts++) {
      if (isPositionClear(g, lane, 0, 0.25)) break;
      lane = Math.floor(Math.random() * LANE_COUNT);
    }
    
    return {
      type,
      lane,
      depth: 0,
      collected: false,
      floatOffset: 35 + Math.random() * 15,
      glow: Math.random() * Math.PI * 2,
      sparklePhase: Math.random() * Math.PI * 2,
      rotation: 0
    };
  };

  const spawnObstacle = (g) => {
    const stage = getCurrentStage(g.score);
    const types = OBSTACLE_STAGES[stage].types;
    const type = types[Math.floor(Math.random() * types.length)];
    
    // Try to find a clear lane (max 5 attempts)
    let lane = Math.floor(Math.random() * LANE_COUNT);
    for (let attempts = 0; attempts < 5; attempts++) {
      if (isPositionClear(g, lane, 0, 0.18)) break;
      lane = Math.floor(Math.random() * LANE_COUNT);
    }
    
    let size = 40;
    let isFlying = false;
    
    // LARGER obstacles - increased sizes by ~30%
    switch (type) {
      case 'meteor': size = 50 + Math.random() * 20; break;      // Was 35-50, now 50-70
      case 'debris': size = 35 + Math.random() * 20; break;      // Was 25-40, now 35-55
      case 'blackhole': size = 65; break;                         // Was 50, now 65
      case 'satellite': size = 58; isFlying = Math.random() > 0.5; break;  // Was 45, now 58
      case 'alienship': size = 70; isFlying = true; break;        // Was 55, now 70
      default: break;
    }
    
    return {
      type, lane, 
      depth: 0, // Start at horizon (0), move to player (1)
      size,
      isFlying,
      flyOffset: isFlying ? 40 + Math.random() * 30 : 0,
      rotation: Math.random() * Math.PI * 2,
      rotSpeed: (Math.random() - 0.5) * 0.15,
      pulse: Math.random() * Math.PI * 2
    };
  };

  const spawnCollectible = (g) => {
    // Try to find a clear lane (max 5 attempts)
    let lane = Math.floor(Math.random() * LANE_COUNT);
    for (let attempts = 0; attempts < 5; attempts++) {
      if (isPositionClear(g, lane, 0, 0.18)) break;
      lane = Math.floor(Math.random() * LANE_COUNT);
    }
    
    return {
      lane,
      depth: 0,
      collected: false,
      floatOffset: 30 + Math.random() * 20,
      glow: Math.random() * Math.PI * 2,
      sparkleParticles: [] // For sparkle effect
    };
  };

  const startGame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    
    gameRef.current = initGame();
    setGameState("playing");
    setScore(0);
    setMooncakes(0);
    setCurrentStage(1);
    playSoundIfEnabled('click');

    const loop = () => {
      const g = gameRef.current;
      if (!g || !g.running) return;
      
      g.frame++;
      
      // Progressive speed over 120 seconds
      // SLOWED DOWN: Start at 1.25 (was 2.5), max at 4.8 (was 12, now 20% less = 9.6, then halved = 4.8)
      const elapsedSeconds = (Date.now() - g.startTime) / 1000;
      const speedProgress = Math.min(elapsedSeconds / 120, 1); // 0 to 1 over 120 seconds
      const minSpeed = 1.25;  // Halved from 2.5
      const maxSpeed = 4.8;   // 12 * 0.8 * 0.5 = 4.8 (20% slower, then halved)
      g.speed = minSpeed + (maxSpeed - minSpeed) * speedProgress;
      
      // HALVED points: baseScore is now /6 instead of /3
      const baseScore = Math.floor(g.frame / 6);
      g.score = Math.floor(baseScore * (1 + g.skinBonus));
      g.trackOffset = (g.trackOffset + g.speed * 0.02) % 1;
      
      // Update stage
      const newStage = getCurrentStage(g.score);
      if (newStage !== g.stage) {
        g.stage = newStage;
        setCurrentStage(newStage);
        for (let i = 0; i < 25; i++) {
          g.particles.push({
            x: W / 2 + (Math.random() - 0.5) * 300,
            y: H / 2,
            vx: (Math.random() - 0.5) * 10,
            vy: (Math.random() - 0.5) * 10,
            life: 50,
            color: `hsl(${280 + Math.random() * 60}, 100%, 70%)`
          });
        }
      }

      // Handle controls
      const keys = keysRef.current;
      if (keys.left && g.player.targetLane > 0) {
        g.player.targetLane--;
        keys.left = false;
        playSoundIfEnabled('click');
      }
      if (keys.right && g.player.targetLane < 2) {
        g.player.targetLane++;
        keys.right = false;
        playSoundIfEnabled('click');
      }
      
      // Smooth lane transition
      if (g.player.lane !== g.player.targetLane) {
        g.player.laneTransition += 0.15;
        if (g.player.laneTransition >= 1) {
          g.player.lane = g.player.targetLane;
          g.player.laneTransition = 0;
        }
      }

      // Jump physics
      if (keys.jump && !g.player.isJumping) {
        g.player.vy = JUMP_FORCE;
        g.player.isJumping = true;
        keys.jump = false;
        playSoundIfEnabled('jump');
        for (let i = 0; i < 10; i++) {
          g.particles.push({
            x: getLaneX(g.player.lane, 1) + (Math.random() - 0.5) * 40,
            y: GROUND_Y,
            vx: (Math.random() - 0.5) * 5,
            vy: -Math.random() * 4,
            life: 25,
            color: g.skinColor || '#00FFA3'
          });
        }
      }
      
      g.player.vy += GRAVITY;
      g.player.y += g.player.vy;
      
      if (g.player.y >= PLAYER_BASE_Y) {
        g.player.y = PLAYER_BASE_Y;
        g.player.vy = 0;
        g.player.isJumping = false;
      }

      // Update player animation
      g.player.animTimer++;
      if (g.player.animTimer >= 4) {
        g.player.animTimer = 0;
        g.player.animFrame = (g.player.animFrame + 1) % (g.player.isJumping ? ANIM_JUMP_FRAMES : ANIM_RUN_FRAMES);
      }

      // Spawn obstacles - adjust rate based on current speed
      const baseSpawnRate = 70;
      const spawnRate = Math.max(25, Math.floor(baseSpawnRate - g.speed * 3));
      if (g.frame % spawnRate === 0) {
        g.obstacles.push(spawnObstacle(g));
      }

      // Spawn collectibles - pass g for collision checking
      if (g.frame % 60 === 0) {
        g.collectibles.push(spawnCollectible(g));
      }

      // Move obstacles DOWN the lane - speed based on game speed
      const depthSpeed = g.speed * 0.008; // Slower depth movement
      g.obstacles = g.obstacles.filter(o => {
        o.depth += depthSpeed;
        o.rotation += o.rotSpeed;
        o.pulse += 0.1;
        return o.depth < 1.3;
      });

      // Move collectibles
      g.collectibles = g.collectibles.filter(c => {
        c.depth += depthSpeed;
        c.glow += 0.15;
        return c.depth < 1.3 && !c.collected;
      });

      // Update particles
      g.particles = g.particles.filter(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.15;
        p.life--;
        return p.life > 0;
      });

      // Get player's current lane considering transition
      const playerLane = g.player.laneTransition > 0 
        ? g.player.lane + (g.player.targetLane - g.player.lane) * g.player.laneTransition
        : g.player.lane;
      const playerX = getLaneX(playerLane, 1);
      const playerY = g.player.y;
      const playerW = 70;  // Match render size
      const playerH = 90;  // Match render size

      // Collision detection - check when obstacles reach player depth (~0.85-1.0)
      for (const o of g.obstacles) {
        if (o.depth >= 0.82 && o.depth <= 1.05) {
          const scale = getDepthScale(o.depth);
          const obsX = getLaneX(o.lane, o.depth);
          const obsY = getDepthY(o.depth) - o.size * scale - (o.isFlying ? o.flyOffset * scale : 0);
          const obsW = o.size * scale * 1.2;
          const obsH = o.size * scale;
          
          // Check same lane collision
          if (Math.abs(o.lane - Math.round(playerLane)) < 0.5) {
            // Player can jump over ground obstacles
            if (!o.isFlying && playerY + playerH < obsY + obsH * 0.3) continue;
            // Player must jump over flying obstacles
            if (o.isFlying && playerY + playerH < obsY) continue;
            
            // Bounding box collision
            const px1 = playerX - playerW / 2 + 8;
            const px2 = playerX + playerW / 2 - 8;
            const py1 = playerY + 5;
            const py2 = playerY + playerH - 5;
            
            const ox1 = obsX - obsW / 2;
            const ox2 = obsX + obsW / 2;
            const oy1 = obsY;
            const oy2 = obsY + obsH;
            
            if (px2 > ox1 && px1 < ox2 && py2 > oy1 && py1 < oy2) {
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
              submitScore(g.score, g.mooncakes);
              return;
            }
          }
        }
      }

      // Collectible collision
      for (const c of g.collectibles) {
        if (!c.collected && c.depth >= 0.8 && c.depth <= 1.1) {
          if (Math.abs(c.lane - Math.round(playerLane)) < 0.5) {
            const scale = getDepthScale(c.depth);
            const colY = getDepthY(c.depth) - c.floatOffset * scale - 20;
            if (playerY < colY + 40 && playerY + playerH > colY - 10) {
              c.collected = true;
              g.mooncakes++;
              g.score += Math.floor(25 * (1 + g.skinBonus)); // HALVED from 50 to 25
              collectFeedback();
              
              const colX = getLaneX(c.lane, c.depth);
              for (let i = 0; i < 15; i++) {
                const angle = (Math.PI * 2 / 15) * i;
                g.particles.push({
                  x: colX, y: colY + 15,
                  vx: Math.cos(angle) * 5,
                  vy: Math.sin(angle) * 5 - 2,
                  life: 35,
                  color: `hsl(${45 + Math.random() * 20}, 100%, ${60 + Math.random() * 30}%)`
                });
              }
            }
          }
        }
      }

      setScore(g.score);
      setMooncakes(g.mooncakes);

      // ===== RENDERING =====
      // Deep space background
      const bgGrad = ctx.createLinearGradient(0, 0, 0, H);
      bgGrad.addColorStop(0, '#000008');
      bgGrad.addColorStop(0.4, '#0a0520');
      bgGrad.addColorStop(1, '#0f0a25');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, W, H);

      // Nebulas
      g.nebulas.forEach(n => {
        const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.size);
        grad.addColorStop(0, `hsla(${n.hue}, 60%, 35%, ${n.alpha})`);
        grad.addColorStop(0.6, `hsla(${n.hue + 30}, 50%, 25%, ${n.alpha * 0.5})`);
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Stars with twinkling
      g.stars.forEach(s => {
        s.twinkle += 0.03;
        const brightness = 0.4 + Math.sin(s.twinkle) * 0.4;
        ctx.fillStyle = `rgba(255, 255, 255, ${brightness})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // 3D Track/Ground
      // Draw track lanes with perspective
      ctx.strokeStyle = 'rgba(100, 60, 180, 0.4)';
      ctx.lineWidth = 1;
      
      // Lane dividers
      for (let i = 0; i <= LANE_COUNT; i++) {
        const topX = VANISHING_X + (i - 1.5) * 15;
        const bottomX = VANISHING_X + (i - 1.5) * LANE_WIDTH * 1.8;
        ctx.beginPath();
        ctx.moveTo(topX, HORIZON_Y);
        ctx.lineTo(bottomX, GROUND_Y);
        ctx.stroke();
      }

      // Ground plane
      const groundGrad = ctx.createLinearGradient(0, HORIZON_Y, 0, GROUND_Y);
      groundGrad.addColorStop(0, 'rgba(30, 15, 60, 0.3)');
      groundGrad.addColorStop(1, 'rgba(40, 20, 80, 0.7)');
      ctx.fillStyle = groundGrad;
      ctx.beginPath();
      ctx.moveTo(VANISHING_X - 25, HORIZON_Y);
      ctx.lineTo(VANISHING_X - LANE_WIDTH * 2.7, GROUND_Y);
      ctx.lineTo(VANISHING_X + LANE_WIDTH * 2.7, GROUND_Y);
      ctx.lineTo(VANISHING_X + 25, HORIZON_Y);
      ctx.closePath();
      ctx.fill();

      // Horizontal grid lines moving toward player
      ctx.strokeStyle = 'rgba(120, 80, 200, 0.25)';
      for (let i = 0; i < 15; i++) {
        const baseDepth = (i / 15 + g.trackOffset) % 1;
        const y = getDepthY(baseDepth);
        const spread = (W * 0.4) * baseDepth + 20;
        ctx.beginPath();
        ctx.moveTo(VANISHING_X - spread, y);
        ctx.lineTo(VANISHING_X + spread, y);
        ctx.stroke();
      }

      // Edge glow lines
      const edgeGrad = ctx.createLinearGradient(0, HORIZON_Y, 0, GROUND_Y);
      edgeGrad.addColorStop(0, 'rgba(0, 255, 163, 0.2)');
      edgeGrad.addColorStop(1, 'rgba(0, 255, 163, 0.7)');
      ctx.strokeStyle = edgeGrad;
      ctx.lineWidth = 3;
      
      ctx.beginPath();
      ctx.moveTo(VANISHING_X - 25, HORIZON_Y);
      ctx.lineTo(VANISHING_X - LANE_WIDTH * 2.7, GROUND_Y);
      ctx.stroke();
      
      ctx.beginPath();
      ctx.moveTo(VANISHING_X + 25, HORIZON_Y);
      ctx.lineTo(VANISHING_X + LANE_WIDTH * 2.7, GROUND_Y);
      ctx.stroke();

      // Draw obstacles (sorted by depth for proper rendering - far first)
      const sortedObstacles = [...g.obstacles].sort((a, b) => a.depth - b.depth);
      
      sortedObstacles.forEach(o => {
        if (o.depth < 0.05 || o.depth > 1.2) return;
        
        const scale = getDepthScale(o.depth);
        const x = getLaneX(o.lane, o.depth);
        const baseY = getDepthY(o.depth);
        const y = baseY - o.size * scale - (o.isFlying ? o.flyOffset * scale : 0);
        const w = o.size * scale * 1.2;
        const h = o.size * scale;
        
        ctx.save();
        ctx.translate(x, y + h / 2);
        
        switch (o.type) {
          case 'meteor':
            ctx.rotate(o.rotation);
            // Outer fire aura (pulsing)
            const fireAura = ctx.createRadialGradient(0, 0, 0, 0, 0, w * 0.85);
            fireAura.addColorStop(0, 'transparent');
            fireAura.addColorStop(0.5, `rgba(255, 80, 0, ${0.15 + Math.sin(o.pulse * 2) * 0.1})`);
            fireAura.addColorStop(0.8, `rgba(255, 30, 0, ${0.25 + Math.sin(o.pulse * 3) * 0.15})`);
            fireAura.addColorStop(1, 'transparent');
            ctx.fillStyle = fireAura;
            ctx.beginPath();
            ctx.arc(0, 0, w * 0.85, 0, Math.PI * 2);
            ctx.fill();
            
            // Fiery core with enhanced gradient
            const mGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, w * 0.55);
            mGrad.addColorStop(0, '#FFFFFF');
            mGrad.addColorStop(0.2, '#FFFF00');
            mGrad.addColorStop(0.4, '#FFA500');
            mGrad.addColorStop(0.65, '#FF4500');
            mGrad.addColorStop(0.85, '#CC0000');
            mGrad.addColorStop(1, '#660000');
            ctx.fillStyle = mGrad;
            ctx.beginPath();
            ctx.ellipse(0, 0, w * 0.5, h * 0.45, 0, 0, Math.PI * 2);
            ctx.fill();
            
            // Multiple fire trails going UP (toward horizon)
            for (let t = 0; t < 3; t++) {
              const trailOffset = (t - 1) * w * 0.15;
              const trailAlpha = 0.5 + Math.sin(o.pulse + t) * 0.25;
              ctx.fillStyle = `rgba(255, ${80 + t * 30}, 0, ${trailAlpha})`;
              ctx.beginPath();
              ctx.moveTo(trailOffset - w * 0.15, -h * 0.2);
              ctx.quadraticCurveTo(trailOffset, -h * (1.0 + t * 0.2), trailOffset + w * 0.15, -h * 0.2);
              ctx.closePath();
              ctx.fill();
            }
            
            // Fire embers/sparks
            for (let s = 0; s < 4; s++) {
              const sparkAngle = o.pulse * 2 + s * 1.5;
              const sparkDist = w * (0.4 + Math.sin(sparkAngle) * 0.15);
              const sparkX = Math.cos(sparkAngle) * sparkDist;
              const sparkY = Math.sin(sparkAngle) * sparkDist * 0.7;
              ctx.fillStyle = `rgba(255, ${200 + Math.floor(Math.random() * 55)}, 50, ${0.6 + Math.sin(sparkAngle * 2) * 0.4})`;
              ctx.beginPath();
              ctx.arc(sparkX, sparkY, 2 * scale, 0, Math.PI * 2);
              ctx.fill();
            }
            break;
            
          case 'debris':
            ctx.rotate(o.rotation * 1.5);
            // Burning debris with fire effect
            const debrisGrad = ctx.createLinearGradient(-w * 0.5, -h * 0.5, w * 0.5, h * 0.5);
            debrisGrad.addColorStop(0, '#6a5a5a');
            debrisGrad.addColorStop(0.5, '#4a4a5a');
            debrisGrad.addColorStop(1, '#3a3a4a');
            ctx.fillStyle = debrisGrad;
            ctx.beginPath();
            ctx.moveTo(-w * 0.4, -h * 0.2);
            ctx.lineTo(-w * 0.2, -h * 0.45);
            ctx.lineTo(w * 0.3, -h * 0.35);
            ctx.lineTo(w * 0.45, h * 0.2);
            ctx.lineTo(0, h * 0.4);
            ctx.lineTo(-w * 0.35, h * 0.25);
            ctx.closePath();
            ctx.fill();
            // Fire edge glow
            ctx.strokeStyle = `rgba(255, 100, 0, ${0.5 + Math.sin(o.pulse * 2) * 0.3})`;
            ctx.lineWidth = 3 * scale;
            ctx.stroke();
            // Inner stroke
            ctx.strokeStyle = '#9a8a8a';
            ctx.lineWidth = 1;
            ctx.stroke();
            // Ember spots
            for (let e = 0; e < 3; e++) {
              const ex = (Math.sin(o.pulse + e * 2) - 0.5) * w * 0.3;
              const ey = (Math.cos(o.pulse + e * 2) - 0.5) * h * 0.3;
              ctx.fillStyle = `rgba(255, ${150 + e * 30}, 0, ${0.4 + Math.sin(o.pulse * 3 + e) * 0.3})`;
              ctx.beginPath();
              ctx.arc(ex, ey, 3 * scale, 0, Math.PI * 2);
              ctx.fill();
            }
            break;
            
          case 'blackhole':
            // Outer danger glow
            const bhOuterGlow = ctx.createRadialGradient(0, 0, w * 0.5, 0, 0, w * 0.85);
            bhOuterGlow.addColorStop(0, 'transparent');
            bhOuterGlow.addColorStop(0.5, `rgba(180, 0, 255, ${0.15 + Math.sin(o.pulse) * 0.1})`);
            bhOuterGlow.addColorStop(1, 'transparent');
            ctx.fillStyle = bhOuterGlow;
            ctx.beginPath();
            ctx.arc(0, 0, w * 0.85, 0, Math.PI * 2);
            ctx.fill();
            
            // Event horizon
            const bhGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, w * 0.6);
            bhGrad.addColorStop(0, '#000000');
            bhGrad.addColorStop(0.4, '#0a0015');
            bhGrad.addColorStop(0.6, '#2a0050');
            bhGrad.addColorStop(0.85, '#5a00a0');
            bhGrad.addColorStop(1, 'transparent');
            ctx.fillStyle = bhGrad;
            ctx.beginPath();
            ctx.arc(0, 0, w * 0.6, 0, Math.PI * 2);
            ctx.fill();
            // Accretion disk with fire colors
            for (let ring = 0; ring < 4; ring++) {
              const ringAlpha = 0.7 - ring * 0.1 + Math.sin(o.pulse * 2 + ring) * 0.2;
              ctx.strokeStyle = `rgba(${220 + ring * 10}, ${100 - ring * 20}, 255, ${ringAlpha})`;
              ctx.lineWidth = (3 - ring * 0.5) * scale;
              ctx.beginPath();
              ctx.ellipse(0, 0, w * (0.42 + ring * 0.08), h * (0.14 + ring * 0.04), o.rotation * 2, 0, Math.PI * 2);
              ctx.stroke();
            }
            break;
            
          case 'satellite':
            // Danger glow
            const satGlow = ctx.createRadialGradient(0, 0, 0, 0, 0, w * 0.7);
            satGlow.addColorStop(0, 'transparent');
            satGlow.addColorStop(0.7, `rgba(255, 50, 50, ${0.1 + Math.sin(o.pulse * 2) * 0.08})`);
            satGlow.addColorStop(1, 'transparent');
            ctx.fillStyle = satGlow;
            ctx.beginPath();
            ctx.arc(0, 0, w * 0.7, 0, Math.PI * 2);
            ctx.fill();
            
            // Body
            ctx.fillStyle = '#7799bb';
            ctx.fillRect(-w * 0.2, -h * 0.35, w * 0.4, h * 0.7);
            // Solar panels
            ctx.fillStyle = '#2255aa';
            ctx.fillRect(-w * 0.5, -h * 0.15, w * 0.25, h * 0.3);
            ctx.fillRect(w * 0.25, -h * 0.15, w * 0.25, h * 0.3);
            // Panel reflections
            ctx.fillStyle = 'rgba(100, 180, 255, 0.3)';
            ctx.fillRect(-w * 0.48, -h * 0.12, w * 0.1, h * 0.1);
            ctx.fillRect(w * 0.35, -h * 0.12, w * 0.1, h * 0.1);
            // Antenna
            ctx.strokeStyle = '#aaccdd';
            ctx.lineWidth = 2 * scale;
            ctx.beginPath();
            ctx.moveTo(0, -h * 0.35);
            ctx.lineTo(0, -h * 0.55);
            ctx.stroke();
            // Blinking warning light
            const lightOn = Math.sin(o.pulse * 4) > 0;
            ctx.fillStyle = lightOn ? '#ff3333' : '#660000';
            ctx.beginPath();
            ctx.arc(0, -h * 0.55, 4 * scale, 0, Math.PI * 2);
            ctx.fill();
            if (lightOn) {
              ctx.fillStyle = 'rgba(255, 50, 50, 0.4)';
              ctx.beginPath();
              ctx.arc(0, -h * 0.55, 8 * scale, 0, Math.PI * 2);
              ctx.fill();
            }
            break;
            
          case 'alienship':
            // UFO danger aura
            const ufoAura = ctx.createRadialGradient(0, 0, 0, 0, 0, w * 0.7);
            ufoAura.addColorStop(0, 'transparent');
            ufoAura.addColorStop(0.6, `rgba(0, 255, 200, ${0.1 + Math.sin(o.pulse * 2) * 0.08})`);
            ufoAura.addColorStop(1, 'transparent');
            ctx.fillStyle = ufoAura;
            ctx.beginPath();
            ctx.arc(0, 0, w * 0.7, 0, Math.PI * 2);
            ctx.fill();
            
            // UFO body with gradient
            const ufoGrad = ctx.createLinearGradient(-w * 0.5, 0, w * 0.5, 0);
            ufoGrad.addColorStop(0, '#20b0a0');
            ufoGrad.addColorStop(0.5, '#50f0e0');
            ufoGrad.addColorStop(1, '#20b0a0');
            ctx.fillStyle = ufoGrad;
            ctx.beginPath();
            ctx.ellipse(0, 0, w * 0.5, h * 0.25, 0, 0, Math.PI * 2);
            ctx.fill();
            // Dome
            ctx.fillStyle = 'rgba(200, 255, 255, 0.6)';
            ctx.beginPath();
            ctx.ellipse(0, -h * 0.15, w * 0.25, h * 0.2, 0, Math.PI, 0);
            ctx.fill();
            // Animated lights
            for (let i = 0; i < 6; i++) {
              const lightPhase = o.pulse * 3 + (i / 6) * Math.PI * 2;
              const brightness = 0.4 + Math.sin(lightPhase) * 0.6;
              ctx.fillStyle = `rgba(255, 255, ${150 + Math.floor(brightness * 105)}, ${brightness})`;
              ctx.beginPath();
              ctx.arc((i - 2.5) * (w / 6), h * 0.12, 4 * scale * brightness, 0, Math.PI * 2);
              ctx.fill();
            }
            // Beam (more visible)
            if (Math.sin(o.pulse) > 0.4) {
              const beamAlpha = 0.2 + Math.sin(o.pulse * 2) * 0.15;
              ctx.fillStyle = `rgba(100, 255, 200, ${beamAlpha})`;
              ctx.beginPath();
              ctx.moveTo(-w * 0.25, h * 0.25);
              ctx.lineTo(-w * 0.5, h * 1.0);
              ctx.lineTo(w * 0.5, h * 1.0);
              ctx.lineTo(w * 0.25, h * 0.25);
              ctx.closePath();
              ctx.fill();
            }
            break;
        }
        ctx.restore();
      });

      // Draw collectibles (mooncakes - actual cake shape, distinct from obstacles)
      g.collectibles.forEach(c => {
        if (c.collected || c.depth < 0.05 || c.depth > 1.15) return;
        
        const scale = getDepthScale(c.depth);
        const x = getLaneX(c.lane, c.depth);
        const y = getDepthY(c.depth) - c.floatOffset * scale - 15;
        const cakeWidth = 28 * scale;  // Wider for cake shape
        const cakeHeight = 18 * scale; // Shorter height for cake
        
        // Soft golden glow around cake (distinct from fiery obstacle glow)
        const glowSize = cakeWidth * 1.8;
        const cakeGlow = ctx.createRadialGradient(x, y, 0, x, y, glowSize);
        cakeGlow.addColorStop(0, 'rgba(255, 230, 150, 0.5)');
        cakeGlow.addColorStop(0.5, 'rgba(255, 200, 100, 0.25)');
        cakeGlow.addColorStop(1, 'transparent');
        ctx.fillStyle = cakeGlow;
        ctx.beginPath();
        ctx.arc(x, y, glowSize, 0, Math.PI * 2);
        ctx.fill();
        
        // Floating sparkles around cake
        for (let s = 0; s < 4; s++) {
          const sparkleAngle = c.glow * 1.5 + (s / 4) * Math.PI * 2;
          const sparkleX = x + Math.cos(sparkleAngle) * (cakeWidth * 1.4);
          const sparkleY = y + Math.sin(sparkleAngle) * (cakeHeight * 1.4);
          const sparkleSize = (2 + Math.sin(c.glow * 3 + s) * 1.5) * scale;
          ctx.fillStyle = `rgba(255, 255, 220, ${0.6 + Math.sin(c.glow * 2 + s) * 0.3})`;
          ctx.beginPath();
          ctx.arc(sparkleX, sparkleY, sparkleSize, 0, Math.PI * 2);
          ctx.fill();
        }
        
        ctx.save();
        ctx.translate(x, y);
        
        // Cake side (3D effect - darker bottom edge)
        const sideGrad = ctx.createLinearGradient(0, -cakeHeight * 0.3, 0, cakeHeight * 0.5);
        sideGrad.addColorStop(0, '#D4A050');
        sideGrad.addColorStop(0.5, '#C49040');
        sideGrad.addColorStop(1, '#A07030');
        ctx.fillStyle = sideGrad;
        ctx.beginPath();
        ctx.ellipse(0, cakeHeight * 0.2, cakeWidth, cakeHeight * 0.4, 0, 0, Math.PI);
        ctx.fill();
        
        // Cake top surface (golden brown)
        const topGrad = ctx.createRadialGradient(-cakeWidth * 0.2, -cakeHeight * 0.2, 0, 0, 0, cakeWidth);
        topGrad.addColorStop(0, '#FFE4A0');
        topGrad.addColorStop(0.4, '#E8C060');
        topGrad.addColorStop(0.8, '#D4A050');
        topGrad.addColorStop(1, '#C49040');
        ctx.fillStyle = topGrad;
        ctx.beginPath();
        ctx.ellipse(0, -cakeHeight * 0.1, cakeWidth, cakeHeight * 0.5, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Decorative pattern on top (traditional mooncake pattern)
        ctx.strokeStyle = '#B08030';
        ctx.lineWidth = 1.5 * scale;
        
        // Outer ring pattern
        ctx.beginPath();
        ctx.ellipse(0, -cakeHeight * 0.1, cakeWidth * 0.8, cakeHeight * 0.38, 0, 0, Math.PI * 2);
        ctx.stroke();
        
        // Inner circle with design
        ctx.fillStyle = '#C8A050';
        ctx.beginPath();
        ctx.ellipse(0, -cakeHeight * 0.1, cakeWidth * 0.5, cakeHeight * 0.25, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Moon symbol in center (crescent)
        ctx.fillStyle = '#FFE090';
        ctx.beginPath();
        ctx.arc(-cakeWidth * 0.05, -cakeHeight * 0.15, cakeWidth * 0.25, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#C8A050';
        ctx.beginPath();
        ctx.arc(cakeWidth * 0.08, -cakeHeight * 0.12, cakeWidth * 0.2, 0, Math.PI * 2);
        ctx.fill();
        
        // Cross pattern for traditional look
        ctx.strokeStyle = '#A87020';
        ctx.lineWidth = 1 * scale;
        ctx.beginPath();
        ctx.moveTo(-cakeWidth * 0.75, -cakeHeight * 0.1);
        ctx.lineTo(cakeWidth * 0.75, -cakeHeight * 0.1);
        ctx.moveTo(0, -cakeHeight * 0.5);
        ctx.lineTo(0, cakeHeight * 0.3);
        ctx.stroke();
        
        // Highlight shine on top
        ctx.fillStyle = 'rgba(255, 255, 230, 0.5)';
        ctx.beginPath();
        ctx.ellipse(-cakeWidth * 0.35, -cakeHeight * 0.3, cakeWidth * 0.2, cakeHeight * 0.12, -0.3, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.restore();
        
        // Pulsing outline glow
        const pulseAlpha = 0.3 + Math.sin(c.glow * 2) * 0.2;
        ctx.strokeStyle = `rgba(255, 215, 100, ${pulseAlpha})`;
        ctx.lineWidth = 2 * scale;
        ctx.beginPath();
        ctx.ellipse(x, y - cakeHeight * 0.1, cakeWidth * 1.1, cakeHeight * 0.6, 0, 0, Math.PI * 2);
        ctx.stroke();
      });

      // Draw animated Bullpug character - galloping animation
      const pX = playerX;
      const pY = playerY;
      const pW = 110;  // Character width (larger for fluffy bullpug)
      const pH = 90;   // Character height
      
      // Galloping animation timing
      const runPhase = g.player.animFrame * 0.35; // Animation phase
      const gallop = Math.sin(runPhase * Math.PI * 2); // -1 to 1 galloping motion
      const gallopAbs = Math.abs(gallop); // 0 to 1 for bounce timing
      
      // Dynamic shadow
      const shadowScale = g.player.isJumping ? 0.2 + (1 - Math.min(Math.abs(pY - PLAYER_BASE_Y) / 100, 1)) * 0.25 : 0.5;
      ctx.fillStyle = `rgba(0, 0, 0, ${0.2 + shadowScale * 0.12})`;
      ctx.beginPath();
      ctx.ellipse(pX, GROUND_Y - 3, pW * shadowScale * 0.45, 8 * shadowScale, 0, 0, Math.PI * 2);
      ctx.fill();
      
      // Warm golden glow around bullpug
      const charGlow = ctx.createRadialGradient(pX, pY + pH / 2, 0, pX, pY + pH / 2, pW * 0.7);
      charGlow.addColorStop(0, 'rgba(212, 149, 106, 0.25)');
      charGlow.addColorStop(0.6, 'rgba(212, 149, 106, 0.08)');
      charGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = charGlow;
      ctx.beginPath();
      ctx.arc(pX, pY + pH / 2, pW * 0.7, 0, Math.PI * 2);
      ctx.fill();
      
      // Speed lines when running
      if (g.speed > 2 && !g.player.isJumping) {
        for (let i = 0; i < 3; i++) {
          const lineY = pY + pH * 0.15 + (i / 3) * pH * 0.5;
          const lineAlpha = 0.12 + Math.sin(g.frame * 0.25 + i) * 0.06;
          ctx.strokeStyle = `rgba(255, 220, 180, ${lineAlpha})`;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(pX - pW * 0.55 - g.speed * 10, lineY);
          ctx.lineTo(pX - pW * 0.35, lineY);
          ctx.stroke();
        }
      }
      
      // ANIMATE THE BULLPUG SPRITE - FACING DOWN THE LANE
      if (spriteRef.current) {
        ctx.save();
        
        // === RUNNING ANIMATION ===
        const bounce = g.player.isJumping ? 0 : gallopAbs * 6;     // Vertical bounce
        const tilt = g.player.isJumping ? 0 : gallop * 0.06;        // Gentle body rock
        const scaleBreath = 1 + (g.player.isJumping ? 0 : gallopAbs * 0.04); // Breathing/pumping effect
        
        // === JUMP ANIMATION ===
        let jumpStretchX = 1;
        let jumpStretchY = 1;
        let jumpRotation = 0;
        
        if (g.player.isJumping) {
          if (g.player.vy < -6) {
            // Rising - stretch up, curl body
            jumpStretchY = 1.12;
            jumpStretchX = 0.92;
            jumpRotation = -0.1;
          } else if (g.player.vy > 6) {
            // Falling - stretch forward, prepare to land
            jumpStretchY = 0.9;
            jumpStretchX = 1.1;
            jumpRotation = 0.08;
          } else {
            // Apex - slight curl
            jumpStretchX = 1.05;
            jumpStretchY = 0.95;
          }
        }
        
        // Position and transform
        ctx.translate(pX, pY + pH / 2 - bounce);
        
        // ORIENT TO FACE DOWN THE LANE (rotate sprite to face into screen)
        // Flip horizontally so pug faces forward, slight 3D perspective tilt
        ctx.scale(-1, 1); // Flip horizontally to face forward direction
        
        // Apply animation transforms
        ctx.rotate(tilt + jumpRotation);
        ctx.scale(jumpStretchX * scaleBreath, jumpStretchY);
        
        const spriteW = pW;
        const spriteH = pH;
        
        // Draw the full sprite (no clipping - fixes missing pixels)
        ctx.drawImage(spriteRef.current, -spriteW / 2, -spriteH / 2, spriteW, spriteH);
        
        // Galloping leg motion effect - draw slightly offset copies for motion blur
        if (!g.player.isJumping && g.speed > 1.5) {
          const legMotion = gallop * 4;
          
          // Motion blur for front legs area
          ctx.globalAlpha = 0.15;
          ctx.save();
          ctx.translate(legMotion, gallopAbs * 2);
          ctx.drawImage(spriteRef.current, -spriteW / 2, -spriteH / 2, spriteW, spriteH);
          ctx.restore();
          
          // Opposite blur for back legs area  
          ctx.save();
          ctx.translate(-legMotion, gallopAbs * 2);
          ctx.drawImage(spriteRef.current, -spriteW / 2, -spriteH / 2, spriteW, spriteH);
          ctx.restore();
          ctx.globalAlpha = 1;
        }
        
        // Jump curled body overlay effect
        if (g.player.isJumping) {
          ctx.globalAlpha = 0.1;
          ctx.scale(1.02, 0.96);
          ctx.drawImage(spriteRef.current, -spriteW / 2, -spriteH / 2 + 2, spriteW, spriteH);
          ctx.globalAlpha = 1;
        }
        
        ctx.restore();
        
        // Motion trail when moving (drawn in world space, not flipped)
        if (g.speed > 2.5 && !g.player.isJumping) {
          ctx.save();
          ctx.translate(pX, pY + pH / 2 - bounce);
          ctx.scale(-1, 1);
          ctx.globalAlpha = 0.1;
          ctx.translate(10, 0);
          ctx.drawImage(spriteRef.current, -spriteW / 2, -spriteH / 2, spriteW, spriteH);
          if (g.speed > 3.5) {
            ctx.globalAlpha = 0.05;
            ctx.translate(10, 0);
            ctx.drawImage(spriteRef.current, -spriteW / 2, -spriteH / 2, spriteW, spriteH);
          }
          ctx.restore();
        }
        
        // Dust particles from running
        if (!g.player.isJumping && g.frame % Math.max(6, 16 - Math.floor(g.speed * 3)) === 0) {
          g.particles.push({
            x: pX + (gallop > 0 ? -1 : 1) * pW * 0.2,
            y: GROUND_Y - 3,
            vx: -g.speed * 0.15 + (Math.random() - 0.5),
            vy: -Math.random() * 1.5 - 0.5,
            life: 14,
            color: 'rgba(180, 150, 120, 0.4)'
          });
        }
        
        // Fur wisps flying off
        if (!g.player.isJumping && g.speed > 2 && g.frame % 12 === 0) {
          g.particles.push({
            x: pX + pW * 0.3,
            y: pY + pH * 0.1 + Math.random() * pH * 0.3,
            vx: g.speed * 0.4 + Math.random(),
            vy: (Math.random() - 0.5) * 1.5,
            life: 10,
            color: 'rgba(212, 180, 150, 0.35)'
          });
        }
      } else {
        // Fallback character if sprite not loaded
        ctx.save();
        ctx.translate(pX, pY + pH / 2);
        ctx.fillStyle = g.skinColor;
        ctx.beginPath();
        ctx.ellipse(0, 0, pW * 0.4, pH * 0.35, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
      
      // Jump landing particles
      if (g.player.isJumping && g.player.vy > 6 && Math.abs(g.player.y - PLAYER_BASE_Y) < 12) {
        for (let i = 0; i < 5; i++) {
          const angle = (i / 5) * Math.PI;
          g.particles.push({
            x: pX + Math.cos(angle) * 12,
            y: GROUND_Y - 4,
            vx: Math.cos(angle) * 2.5,
            vy: -Math.random() * 2.5 - 0.8,
            life: 16,
            color: 'rgba(180, 150, 120, 0.4)'
          });
        }
      }

      // Draw particles
      g.particles.forEach(p => {
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.life / 50;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      // HUD
      ctx.fillStyle = '#FFF';
      ctx.font = 'bold 18px Orbitron, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`SCORE: ${g.score}`, 20, 35);
      ctx.fillStyle = '#FFD700';
      ctx.fillText(`MOONCAKES: ${g.mooncakes}`, 20, 60);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '13px monospace';
      ctx.fillText(`STAGE ${g.stage}`, 20, 82);
      
      // Stage bar
      const stageColors = ['#00FFA3', '#00CED1', '#D946EF', '#FF6B35', '#FF3B30'];
      ctx.fillStyle = stageColors[g.stage - 1] || '#FFF';
      ctx.fillRect(20, 88, 90 * (g.stage / 5), 5);
      ctx.strokeStyle = 'rgba(255,255,255,0.3)';
      ctx.lineWidth = 1;
      ctx.strokeRect(20, 88, 90, 5);
      
      ctx.textAlign = 'right';
      ctx.fillStyle = '#64748b';
      ctx.font = '12px monospace';
      ctx.fillText(`BEST: ${Math.max(g.score, highScore)}`, W - 20, 35);

      // Lane indicators
      ctx.textAlign = 'center';
      ctx.font = '12px monospace';
      for (let i = 0; i < LANE_COUNT; i++) {
        const lx = getLaneX(i, 1);
        ctx.fillStyle = Math.round(playerLane) === i ? '#00FFA3' : 'rgba(255,255,255,0.3)';
        ctx.fillText(Math.round(playerLane) === i ? '●' : '○', lx, H - 15);
      }

      // Controls hint
      ctx.fillStyle = 'rgba(255,255,255,0.4)';
      ctx.font = '11px sans-serif';
      ctx.fillText('← A/D → switch lanes  |  SPACE jump', W / 2, H - 35);

      animRef.current = requestAnimationFrame(loop);
    };
    
    animRef.current = requestAnimationFrame(loop);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highScore, totalMooncakes, playerName, currentSkin, currentSkinId]);

  // Helper function to shade colors
  const shadeColor = (color, percent) => {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.min(255, Math.max(0, (num >> 16) + amt));
    const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amt));
    const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt));
    return `#${(0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)}`;
  };

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (gameState !== "playing") {
        if (e.code === "Space" || e.code === "Enter") {
          e.preventDefault();
          startGame();
        }
        return;
      }
      
      switch (e.code) {
        case "ArrowLeft":
        case "KeyA":
          e.preventDefault();
          keysRef.current.left = true;
          break;
        case "ArrowRight":
        case "KeyD":
          e.preventDefault();
          keysRef.current.right = true;
          break;
        case "Space":
        case "ArrowUp":
        case "KeyW":
          e.preventDefault();
          keysRef.current.jump = true;
          break;
        default:
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [gameState, startGame]);

  // Touch controls
  const handleTouchStart = (e) => {
    if (gameState !== "playing") {
      startGame();
      return;
    }
    
    const touch = e.touches[0];
    const rect = canvasRef.current.getBoundingClientRect();
    const x = touch.clientX - rect.left;
    const third = rect.width / 3;
    
    if (x < third) keysRef.current.left = true;
    else if (x > third * 2) keysRef.current.right = true;
    else keysRef.current.jump = true;
  };

  useEffect(() => {
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, []);

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      
      <SkinStore 
        isOpen={showSkinStore} 
        onClose={() => setShowSkinStore(false)}
        onSkinSelect={handleSkinSelect}
        currentSkinId={currentSkinId}
      />

      <div className="max-w-5xl mx-auto px-4 md:px-12">
        <div className="text-center mb-6">
          <div className="flex items-center justify-center gap-3 mb-2">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Orbitron, sans-serif' }} data-testid="game-title">
              COSMIC <span className="text-[#D946EF]">RUNNER</span>
            </h1>
            <button onClick={() => setShowSkinStore(true)} data-testid="skin-store-btn"
              className="p-2 rounded-full bg-[#D946EF]/10 border border-[#D946EF]/30 text-[#D946EF] hover:bg-[#D946EF]/20 transition-all" title="Skin Store">
              <Store size={18} />
            </button>
            <Link to={connected ? `/showcase/${publicKey?.toBase58()}` : "/showcase"} data-testid="showcase-btn"
              className="p-2 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30 text-[#00FFA3] hover:bg-[#00FFA3]/20 transition-all" title="My Collection">
              <Award size={18} />
            </Link>
            <button onClick={toggleSound} data-testid="game-sound-toggle"
              className="p-2 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
              {soundOn ? <Volume2 size={18} /> : <VolumeX size={18} />}
            </button>
          </div>
          <p className="text-slate-500 text-sm">Dodge meteors, black holes & aliens through deep space!</p>
          
          {currentSkin.bonusPercent > 0 && (
            <div className="inline-flex items-center gap-2 mt-2 px-3 py-1 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30">
              <span className="text-xs text-[#00FFA3] font-bold">{currentSkin.name}</span>
              <Badge className="bg-[#F5D300]/10 text-[#F5D300] border-[#F5D300]/30 text-[10px]">
                <Sparkles className="w-3 h-3 mr-1" /> +{currentSkin.bonusPercent}% Bonus
              </Badge>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-3">
            <div className="glass-card rounded-2xl p-3 md:p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-[#00FFA3]" />
                  {showNameInput ? (
                    <div className="flex items-center gap-2">
                      <Input defaultValue={playerName} maxLength={20}
                        className="w-28 h-7 bg-black/50 border-white/10 text-white text-sm"
                        onKeyDown={(e) => { if (e.key === "Enter") savePlayerName(e.target.value); }}
                        autoFocus
                      />
                      <button onClick={(e) => savePlayerName(e.target.previousSibling.value)} className="text-xs text-[#00FFA3]">Save</button>
                    </div>
                  ) : (
                    <button onClick={() => setShowNameInput(true)} className="text-sm text-white hover:text-[#00FFA3]">{playerName}</button>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <Badge className={`text-[10px] ${currentStage >= 3 ? 'bg-purple-500/20 text-purple-300 border-purple-500/30' : 'bg-slate-500/20 text-slate-400 border-slate-500/30'}`}>
                    Stage {currentStage}/5
                  </Badge>
                  <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px]">
                    <Clock className="w-3 h-3 mr-1" /> Resets in {leaderboardMeta.days_until_reset}d
                  </Badge>
                </div>
              </div>

              <div className="relative mx-auto" style={{ maxWidth: W }}>
                <canvas ref={canvasRef} width={W} height={H} onTouchStart={handleTouchStart}
                  className="w-full rounded-xl border-2 border-[#D946EF]/30 cursor-pointer bg-[#000008]"
                  data-testid="game-canvas" 
                />

                {gameState === "idle" && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 rounded-xl">
                    <div className="relative mb-4">
                      <img src={currentSkin.image} alt="Character" className="w-24 h-24 rounded-xl border-2 object-cover" style={{ borderColor: currentSkin.color }} />
                      <div className="absolute inset-0 rounded-xl" style={{ boxShadow: `0 0 30px ${currentSkin.color}40` }} />
                    </div>
                    <h2 className="text-2xl font-black text-white mb-2" style={{ fontFamily: 'Orbitron' }}>COSMIC RUNNER</h2>
                    <p className="text-slate-400 text-sm mb-4">Navigate through 5 stages of space hazards!</p>
                    <Button onClick={startGame} data-testid="start-game-btn"
                      className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3] text-white font-bold rounded-full px-10 py-6 text-lg uppercase hover:scale-105 transition-transform shadow-[0_0_30px_rgba(217,70,239,0.4)]">
                      <Play className="w-6 h-6 mr-2" /> START
                    </Button>
                    <div className="flex items-center gap-6 mt-4 text-slate-500 text-xs">
                      <span className="flex items-center gap-1"><ChevronLeft size={14} /> A/D <ChevronRight size={14} /></span>
                      <span className="flex items-center gap-1"><ArrowUp size={14} /> SPACE</span>
                    </div>
                  </div>
                )}

                {gameState === "over" && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/85 rounded-xl" data-testid="game-over-screen">
                    <p className="text-4xl font-black text-red-400 mb-2" style={{ fontFamily: 'Orbitron' }}>GAME OVER</p>
                    <p className="text-2xl font-bold text-white mb-1">Score: {score}</p>
                    <p className="text-lg text-[#D946EF] mb-2">Stage {currentStage} Reached</p>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-[#FFD700] font-bold">+{mooncakes} Mooncakes</span>
                    </div>
                    {score >= highScore && score > 0 && (
                      <Badge className="bg-[#FFD700]/20 text-[#FFD700] border-[#FFD700]/40 mb-3 text-sm">
                        <Sparkles className="w-4 h-4 mr-1" /> NEW HIGH SCORE!
                      </Badge>
                    )}
                    <div className="flex items-center gap-3 mt-2">
                      <Button onClick={startGame} data-testid="restart-game-btn"
                        className="bg-[#00FFA3] text-black font-bold rounded-full px-6 py-3 uppercase hover:scale-105 transition-transform">
                        <RotateCcw className="w-4 h-4 mr-2" /> RETRY
                      </Button>
                      <Button onClick={() => {
                        const text = `I scored ${score} points in Cosmic Runner and reached Stage ${currentStage}! 🚀\n\nPlay now at bullpug.com #Bullpug #CosmicRunner #Solana`;
                        window.open(`https://x.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
                      }} className="bg-black text-white border border-white/30 font-bold rounded-full px-5 py-3 uppercase hover:bg-white/10">
                        Share 𝕏
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mt-3 px-2">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-xs text-slate-500">Score</p>
                    <p className="text-xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron' }}>{score}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">High Score</p>
                    <p className="text-xl font-black text-[#FFD700]" style={{ fontFamily: 'Orbitron' }}>{highScore}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <p className="text-xs text-slate-500">Mooncakes</p>
                    <p className="text-lg font-bold text-[#FFD700]">{totalMooncakes}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="px-2 py-1 rounded bg-slate-800/50">Shield</span>
                  <span className="px-2 py-1 rounded bg-slate-800/50">Magnet</span>
                  <span className="px-2 py-1 rounded bg-slate-800/50">2x Score</span>
                </div>
              </div>
            </div>
          </div>

          {/* Leaderboard */}
          <div className="lg:col-span-1">
            <div className="glass-card rounded-2xl p-4">
              <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                <span className="text-[#FFD700]">🏆</span> WEEKLY LEADERBOARD
              </h3>
              <div className="space-y-2">
                {leaderboard.slice(0, 8).map((entry, i) => (
                  <div key={i} className={`flex items-center justify-between p-2 rounded-lg ${i < 3 ? 'bg-gradient-to-r from-[#FFD700]/10 to-transparent' : 'bg-white/5'}`}>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${i === 0 ? 'text-[#FFD700]' : i === 1 ? 'text-slate-300' : i === 2 ? 'text-amber-600' : 'text-slate-500'}`}>
                        {i + 1}
                      </span>
                      <span className="text-sm text-white truncate max-w-[80px]">{entry.player_name}</span>
                    </div>
                    <span className="text-xs font-bold text-[#00FFA3]">{entry.score}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-500 mt-3 text-center">Resets every Monday 00:00 UTC</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
