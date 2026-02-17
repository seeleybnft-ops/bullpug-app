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

// Obstacle stages
const OBSTACLE_STAGES = {
  1: { score: 0, types: ['meteor'] },
  2: { score: 500, types: ['meteor', 'debris'] },
  3: { score: 1000, types: ['meteor', 'debris', 'blackhole'] },
  4: { score: 2000, types: ['meteor', 'debris', 'blackhole', 'satellite'] },
  5: { score: 3000, types: ['meteor', 'debris', 'blackhole', 'satellite', 'alienship'] }
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
    particles: [],
    stars: Array.from({ length: 150 }, () => ({
      x: Math.random() * W,
      y: Math.random() * HORIZON_Y,
      size: Math.random() * 2 + 0.5,
      twinkle: Math.random() * Math.PI * 2
    })),
    nebulas: Array.from({ length: 8 }, () => ({
      x: Math.random() * W,
      y: Math.random() * (HORIZON_Y - 20),
      size: 60 + Math.random() * 100,
      hue: 240 + Math.random() * 80,
      alpha: 0.08 + Math.random() * 0.12
    })),
    frame: 0,
    speed: 2.5, // Start much slower (was 6)
    startTime: Date.now(), // Track game start time for progressive speed
    score: 0,
    mooncakes: 0,
    running: true,
    stage: 1,
    trackOffset: 0,
    skinBonus: currentSkin.bonusPercent / 100,
    skinColor: currentSkin.color
  });

  const spawnObstacle = (g) => {
    const stage = getCurrentStage(g.score);
    const types = OBSTACLE_STAGES[stage].types;
    const type = types[Math.floor(Math.random() * types.length)];
    const lane = Math.floor(Math.random() * LANE_COUNT);
    
    let size = 40;
    let isFlying = false;
    
    switch (type) {
      case 'meteor': size = 35 + Math.random() * 15; break;
      case 'debris': size = 25 + Math.random() * 15; break;
      case 'blackhole': size = 50; break;
      case 'satellite': size = 45; isFlying = Math.random() > 0.5; break;
      case 'alienship': size = 55; isFlying = true; break;
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

  const spawnCollectible = () => {
    return {
      lane: Math.floor(Math.random() * LANE_COUNT),
      depth: 0,
      collected: false,
      floatOffset: 30 + Math.random() * 20,
      glow: Math.random() * Math.PI * 2
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
      
      // Progressive speed over 60 seconds
      // Start at 2.5, max at 12 after 60 seconds (3600 frames at 60fps)
      const elapsedSeconds = (Date.now() - g.startTime) / 1000;
      const speedProgress = Math.min(elapsedSeconds / 60, 1); // 0 to 1 over 60 seconds
      const minSpeed = 2.5;
      const maxSpeed = 12;
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

      // Spawn obstacles
      const spawnRate = Math.max(35, 70 - g.stage * 7);
      if (g.frame % spawnRate === 0) {
        g.obstacles.push(spawnObstacle(g));
      }

      // Spawn collectibles
      if (g.frame % 50 === 0) {
        g.collectibles.push(spawnCollectible());
      }

      // Move obstacles DOWN the lane (depth increases from 0 to 1+)
      const depthSpeed = g.speed * 0.012;
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
      const playerW = 50;
      const playerH = 70;

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
              g.score += Math.floor(50 * (1 + g.skinBonus));
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
            // Fiery core
            const mGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, w * 0.6);
            mGrad.addColorStop(0, '#ffcc00');
            mGrad.addColorStop(0.4, '#ff6600');
            mGrad.addColorStop(0.8, '#cc2200');
            mGrad.addColorStop(1, '#440000');
            ctx.fillStyle = mGrad;
            ctx.beginPath();
            ctx.ellipse(0, 0, w * 0.5, h * 0.45, 0, 0, Math.PI * 2);
            ctx.fill();
            // Fire trail going UP (toward horizon since meteor comes down)
            ctx.fillStyle = `rgba(255, 100, 0, ${0.4 + Math.sin(o.pulse) * 0.2})`;
            ctx.beginPath();
            ctx.moveTo(-w * 0.3, -h * 0.2);
            ctx.quadraticCurveTo(0, -h * 1.2, w * 0.3, -h * 0.2);
            ctx.closePath();
            ctx.fill();
            break;
            
          case 'debris':
            ctx.rotate(o.rotation * 1.5);
            ctx.fillStyle = '#5a5a6a';
            ctx.beginPath();
            ctx.moveTo(-w * 0.4, -h * 0.2);
            ctx.lineTo(-w * 0.2, -h * 0.45);
            ctx.lineTo(w * 0.3, -h * 0.35);
            ctx.lineTo(w * 0.45, h * 0.2);
            ctx.lineTo(0, h * 0.4);
            ctx.lineTo(-w * 0.35, h * 0.25);
            ctx.closePath();
            ctx.fill();
            ctx.strokeStyle = '#8a8a9a';
            ctx.lineWidth = 1;
            ctx.stroke();
            break;
            
          case 'blackhole':
            // Event horizon
            const bhGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, w * 0.6);
            bhGrad.addColorStop(0, '#000000');
            bhGrad.addColorStop(0.5, '#1a0030');
            bhGrad.addColorStop(0.8, '#4a0080');
            bhGrad.addColorStop(1, 'transparent');
            ctx.fillStyle = bhGrad;
            ctx.beginPath();
            ctx.arc(0, 0, w * 0.6, 0, Math.PI * 2);
            ctx.fill();
            // Accretion disk
            ctx.strokeStyle = `rgba(200, 120, 255, ${0.6 + Math.sin(o.pulse * 2) * 0.3})`;
            ctx.lineWidth = 2 * scale;
            for (let ring = 0; ring < 3; ring++) {
              ctx.beginPath();
              ctx.ellipse(0, 0, w * (0.45 + ring * 0.1), h * (0.15 + ring * 0.05), o.rotation * 2, 0, Math.PI * 2);
              ctx.stroke();
            }
            break;
            
          case 'satellite':
            // Body
            ctx.fillStyle = '#7799bb';
            ctx.fillRect(-w * 0.2, -h * 0.35, w * 0.4, h * 0.7);
            // Solar panels
            ctx.fillStyle = '#2255aa';
            ctx.fillRect(-w * 0.5, -h * 0.15, w * 0.25, h * 0.3);
            ctx.fillRect(w * 0.25, -h * 0.15, w * 0.25, h * 0.3);
            // Antenna
            ctx.strokeStyle = '#aaccdd';
            ctx.lineWidth = 2 * scale;
            ctx.beginPath();
            ctx.moveTo(0, -h * 0.35);
            ctx.lineTo(0, -h * 0.55);
            ctx.stroke();
            // Blinking light
            if (Math.sin(o.pulse * 3) > 0) {
              ctx.fillStyle = '#ff0000';
              ctx.beginPath();
              ctx.arc(0, -h * 0.55, 3 * scale, 0, Math.PI * 2);
              ctx.fill();
            }
            break;
            
          case 'alienship':
            // UFO body
            ctx.fillStyle = '#40e0d0';
            ctx.beginPath();
            ctx.ellipse(0, 0, w * 0.5, h * 0.25, 0, 0, Math.PI * 2);
            ctx.fill();
            // Dome
            ctx.fillStyle = 'rgba(200, 255, 255, 0.5)';
            ctx.beginPath();
            ctx.ellipse(0, -h * 0.15, w * 0.25, h * 0.2, 0, Math.PI, 0);
            ctx.fill();
            // Lights
            for (let i = 0; i < 5; i++) {
              const lightPhase = o.pulse + (i / 5) * Math.PI * 2;
              ctx.fillStyle = `rgba(255, 255, 100, ${0.5 + Math.sin(lightPhase * 2) * 0.5})`;
              ctx.beginPath();
              ctx.arc((i - 2) * (w / 5), h * 0.15, 3 * scale, 0, Math.PI * 2);
              ctx.fill();
            }
            // Beam
            if (Math.sin(o.pulse) > 0.6) {
              ctx.fillStyle = 'rgba(100, 255, 200, 0.25)';
              ctx.beginPath();
              ctx.moveTo(-w * 0.2, h * 0.25);
              ctx.lineTo(-w * 0.4, h * 0.8);
              ctx.lineTo(w * 0.4, h * 0.8);
              ctx.lineTo(w * 0.2, h * 0.25);
              ctx.closePath();
              ctx.fill();
            }
            break;
        }
        ctx.restore();
      });

      // Draw collectibles
      g.collectibles.forEach(c => {
        if (c.collected || c.depth < 0.05 || c.depth > 1.15) return;
        
        const scale = getDepthScale(c.depth);
        const x = getLaneX(c.lane, c.depth);
        const y = getDepthY(c.depth) - c.floatOffset * scale - 15;
        const size = 20 * scale;
        
        // Glow
        const glowSize = size * (1.6 + Math.sin(c.glow) * 0.3);
        const glow = ctx.createRadialGradient(x, y, 0, x, y, glowSize);
        glow.addColorStop(0, 'rgba(255, 215, 0, 0.5)');
        glow.addColorStop(1, 'transparent');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, glowSize, 0, Math.PI * 2);
        ctx.fill();
        
        // Mooncake
        ctx.fillStyle = '#FFD700';
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#FFC000';
        ctx.beginPath();
        ctx.arc(x, y, size * 0.65, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(x - size * 0.3, y - size * 0.3, size * 0.18, 0, Math.PI * 2);
        ctx.fill();
      });

      // Draw 3D animated player character
      const pX = playerX;
      const pY = playerY;
      const pW = playerW;
      const pH = playerH;
      
      // Shadow
      ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
      ctx.beginPath();
      ctx.ellipse(pX, GROUND_Y - 3, pW * 0.5, 8, 0, 0, Math.PI * 2);
      ctx.fill();
      
      // Character glow
      const charGlow = ctx.createRadialGradient(pX, pY + pH / 2, 0, pX, pY + pH / 2, pW);
      charGlow.addColorStop(0, `${g.skinColor}50`);
      charGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = charGlow;
      ctx.beginPath();
      ctx.arc(pX, pY + pH / 2, pW, 0, Math.PI * 2);
      ctx.fill();
      
      // Animated 3D character rendering
      if (spriteRef.current) {
        // Draw sprite with animation bob
        const bobOffset = g.player.isJumping ? 0 : Math.sin(g.player.animFrame * 0.8) * 3;
        const stretchY = g.player.isJumping && g.player.vy < 0 ? 1.1 : 1;
        const squashY = g.player.isJumping && g.player.vy > 5 ? 0.9 : 1;
        
        ctx.save();
        ctx.translate(pX, pY + pH / 2 + bobOffset);
        ctx.scale(1, stretchY * squashY);
        
        // Draw sprite
        ctx.drawImage(spriteRef.current, -pW / 2, -pH / 2, pW, pH);
        ctx.restore();
        
        // Running particles
        if (!g.player.isJumping && g.frame % 6 === 0) {
          g.particles.push({
            x: pX + (Math.random() - 0.5) * 20,
            y: GROUND_Y - 5,
            vx: (Math.random() - 0.5) * 2,
            vy: -Math.random() * 2,
            life: 15,
            color: 'rgba(100, 80, 150, 0.5)'
          });
        }
      } else {
        // Fallback 3D box character with animation
        const bobOffset = g.player.isJumping ? 0 : Math.sin(g.player.animFrame * 0.8) * 4;
        
        ctx.save();
        ctx.translate(pX, pY + pH / 2 + bobOffset);
        
        // Body (3D-ish box)
        const grad = ctx.createLinearGradient(-pW / 2, -pH / 2, pW / 2, pH / 2);
        grad.addColorStop(0, g.skinColor);
        grad.addColorStop(1, shadeColor(g.skinColor, -30));
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(-pW / 2, -pH / 2, pW, pH, 12);
        ctx.fill();
        
        // Face
        ctx.fillStyle = '#000';
        ctx.beginPath();
        ctx.arc(-pW * 0.2, -pH * 0.15, 5, 0, Math.PI * 2);
        ctx.arc(pW * 0.2, -pH * 0.15, 5, 0, Math.PI * 2);
        ctx.fill();
        
        // Mouth
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(0, pH * 0.05, 10, 0.1 * Math.PI, 0.9 * Math.PI);
        ctx.stroke();
        
        // Legs animation
        const legAngle = g.player.isJumping ? 0.3 : Math.sin(g.player.animFrame * 1.2) * 0.4;
        ctx.fillStyle = shadeColor(g.skinColor, -50);
        ctx.save();
        ctx.translate(-pW * 0.2, pH * 0.35);
        ctx.rotate(legAngle);
        ctx.fillRect(-5, 0, 10, 20);
        ctx.restore();
        ctx.save();
        ctx.translate(pW * 0.2, pH * 0.35);
        ctx.rotate(-legAngle);
        ctx.fillRect(-5, 0, 10, 20);
        ctx.restore();
        
        ctx.restore();
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
