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

// Game dimensions - wider for 3-lane perspective
const W = 800, H = 450;
const LANE_COUNT = 3;
const LANE_WIDTH = 120;
const LANE_SPACING = 140;
const PLAYER_W = 60, PLAYER_H = 80;

// Physics
const GRAVITY = 0.6;
const JUMP_FORCE = -14;
const LANE_SWITCH_SPEED = 12;

// Perspective settings for 3D effect
const HORIZON_Y = 80;
const GROUND_Y = 380;
const VANISHING_POINT_X = W / 2;

// Obstacle types by stage
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

  // Preload character sprite (already has transparent background)
  useEffect(() => {
    const img = new Image();
    img.src = currentSkin.image;
    img.onload = () => { 
      spriteRef.current = img;
    };
  }, [currentSkin.image]);

  const fetchLeaderboard = async () => {
    try {
      const { data } = await axios.get(`${API}/leaderboard?limit=10`);
      setLeaderboard(data.leaderboard);
      setLeaderboardMeta({ days_until_reset: data.days_until_reset, next_reset: data.next_reset });
    } catch (e) {
      console.error("Failed to fetch leaderboard");
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, []);

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

  // Get current stage based on score
  const getCurrentStage = (score) => {
    for (let i = 5; i >= 1; i--) {
      if (score >= OBSTACLE_STAGES[i].score) return i;
    }
    return 1;
  };

  // Get lane X position with perspective
  const getLaneX = (lane, depth = 1) => {
    const centerX = VANISHING_POINT_X;
    const offset = (lane - 1) * LANE_SPACING;
    return centerX + offset * depth;
  };

  const initGame = () => ({
    player: {
      lane: 1, // 0 = left, 1 = center, 2 = right
      targetLane: 1,
      x: getLaneX(1),
      y: GROUND_Y - PLAYER_H,
      vy: 0,
      isJumping: false,
      laneProgress: 0
    },
    obstacles: [],
    collectibles: [],
    asteroidBelt: [],
    particles: [],
    stars: Array.from({ length: 100 }, () => ({
      x: Math.random() * W,
      y: Math.random() * (HORIZON_Y + 100),
      size: Math.random() * 2 + 0.5,
      speed: Math.random() * 0.5 + 0.2,
      brightness: Math.random()
    })),
    nebulaClouds: Array.from({ length: 5 }, () => ({
      x: Math.random() * W,
      y: Math.random() * HORIZON_Y,
      size: 80 + Math.random() * 120,
      hue: Math.random() * 60 + 240, // Purple-blue range
      alpha: 0.1 + Math.random() * 0.15
    })),
    frame: 0,
    speed: 5,
    score: 0,
    mooncakes: 0,
    running: true,
    stage: 1,
    groundOffset: 0,
    skinBonus: currentSkin.bonusPercent / 100,
    skinColor: currentSkin.color
  });

  // Spawn obstacle based on current stage
  const spawnObstacle = (g) => {
    const stage = getCurrentStage(g.score);
    const types = OBSTACLE_STAGES[stage].types;
    const type = types[Math.floor(Math.random() * types.length)];
    const lane = Math.floor(Math.random() * LANE_COUNT);
    
    let height = 40;
    let width = 50;
    let isFlying = false;
    
    switch (type) {
      case 'meteor':
        height = 45 + Math.random() * 20;
        width = 40 + Math.random() * 15;
        break;
      case 'debris':
        height = 30 + Math.random() * 15;
        width = 35 + Math.random() * 20;
        break;
      case 'blackhole':
        height = 60;
        width = 60;
        break;
      case 'satellite':
        height = 50;
        width = 70;
        isFlying = Math.random() > 0.5;
        break;
      case 'alienship':
        height = 40;
        width = 80;
        isFlying = true;
        break;
      default:
        break;
    }
    
    return {
      type,
      lane,
      z: 1000, // Distance from player (decreases as it approaches)
      width,
      height,
      isFlying,
      flyHeight: isFlying ? 80 + Math.random() * 40 : 0,
      rotation: 0,
      pulsePhase: Math.random() * Math.PI * 2
    };
  };

  // Spawn collectible (mooncake)
  const spawnCollectible = (g) => {
    const lane = Math.floor(Math.random() * LANE_COUNT);
    const isFloating = Math.random() > 0.3;
    return {
      lane,
      z: 1000,
      collected: false,
      floatHeight: isFloating ? 60 + Math.random() * 40 : 20,
      glowPhase: Math.random() * Math.PI * 2
    };
  };

  // Spawn asteroid belt obstacle (high area)
  const spawnAsteroidBelt = () => {
    return {
      z: 1000,
      asteroids: Array.from({ length: 5 + Math.floor(Math.random() * 5) }, () => ({
        xOffset: (Math.random() - 0.5) * 300,
        yOffset: HORIZON_Y + 20 + Math.random() * 60,
        size: 15 + Math.random() * 25,
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.1
      }))
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
      const baseScore = Math.floor(g.frame / 3);
      g.score = Math.floor(baseScore * (1 + g.skinBonus));
      g.speed = 5 + Math.min(g.score / 500, 8);
      g.groundOffset = (g.groundOffset + g.speed) % 100;
      
      // Update stage
      const newStage = getCurrentStage(g.score);
      if (newStage !== g.stage) {
        g.stage = newStage;
        setCurrentStage(newStage);
        // Stage up particles
        for (let i = 0; i < 20; i++) {
          g.particles.push({
            x: W / 2 + (Math.random() - 0.5) * 200,
            y: H / 2,
            vx: (Math.random() - 0.5) * 8,
            vy: (Math.random() - 0.5) * 8,
            life: 60,
            color: `hsl(${280 + Math.random() * 60}, 100%, 70%)`
          });
        }
      }

      // Handle lane switching
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
      const targetX = getLaneX(g.player.targetLane);
      const dx = targetX - g.player.x;
      if (Math.abs(dx) > 1) {
        g.player.x += dx * 0.2;
      } else {
        g.player.x = targetX;
        g.player.lane = g.player.targetLane;
      }

      // Jump physics
      if (keys.jump && !g.player.isJumping) {
        g.player.vy = JUMP_FORCE;
        g.player.isJumping = true;
        keys.jump = false;
        playSoundIfEnabled('jump');
        // Jump particles
        for (let i = 0; i < 8; i++) {
          g.particles.push({
            x: g.player.x + PLAYER_W / 2,
            y: GROUND_Y,
            vx: (Math.random() - 0.5) * 4,
            vy: -Math.random() * 3,
            life: 20,
            color: g.skinColor || '#00FFA3'
          });
        }
      }
      
      g.player.vy += GRAVITY;
      g.player.y += g.player.vy;
      
      if (g.player.y >= GROUND_Y - PLAYER_H) {
        g.player.y = GROUND_Y - PLAYER_H;
        g.player.vy = 0;
        g.player.isJumping = false;
      }

      // Spawn obstacles
      const spawnRate = Math.max(40, 80 - g.stage * 8);
      if (g.frame % spawnRate === 0) {
        g.obstacles.push(spawnObstacle(g));
      }

      // Spawn collectibles
      if (g.frame % 60 === 0) {
        g.collectibles.push(spawnCollectible(g));
      }

      // Spawn asteroid belt sections occasionally
      if (g.frame % 300 === 0 && g.stage >= 3) {
        g.asteroidBelt.push(spawnAsteroidBelt());
      }

      // Move obstacles (z decreases as they approach)
      g.obstacles = g.obstacles.filter(o => {
        o.z -= g.speed * 8;
        o.rotation += 0.02;
        o.pulsePhase += 0.1;
        return o.z > -100;
      });

      // Move collectibles
      g.collectibles = g.collectibles.filter(c => {
        c.z -= g.speed * 8;
        c.glowPhase += 0.15;
        return c.z > -100 && !c.collected;
      });

      // Move asteroid belts
      g.asteroidBelt = g.asteroidBelt.filter(ab => {
        ab.z -= g.speed * 6;
        ab.asteroids.forEach(a => {
          a.rotation += a.rotationSpeed;
        });
        return ab.z > -200;
      });

      // Update stars
      g.stars.forEach(s => {
        s.y += s.speed;
        if (s.y > HORIZON_Y + 100) {
          s.y = 0;
          s.x = Math.random() * W;
        }
        s.brightness = 0.5 + Math.sin(g.frame * 0.05 + s.x) * 0.5;
      });

      // Update particles
      g.particles = g.particles.filter(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.1;
        p.life--;
        return p.life > 0;
      });

      // Collision detection
      const playerHitbox = {
        left: g.player.x + 10,
        right: g.player.x + PLAYER_W - 10,
        top: g.player.y + 10,
        bottom: g.player.y + PLAYER_H
      };

      // Check obstacle collisions
      for (const o of g.obstacles) {
        if (o.z > 0 && o.z < 150) { // Near the player
          const scale = 1 - o.z / 1000;
          const obsX = getLaneX(o.lane, scale);
          const obsY = o.isFlying ? GROUND_Y - o.flyHeight - o.height : GROUND_Y - o.height * scale;
          const obsW = o.width * scale;
          const obsH = o.height * scale;
          
          if (o.lane === g.player.lane) {
            const obstacleHitbox = {
              left: obsX - obsW / 2 + 5,
              right: obsX + obsW / 2 - 5,
              top: obsY,
              bottom: obsY + obsH
            };
            
            // Skip if player jumped over flying obstacle
            if (o.isFlying && g.player.y > obsY + obsH) continue;
            // Skip if player is jumping over ground obstacle
            if (!o.isFlying && g.player.y + PLAYER_H < obsY + 10) continue;
            
            if (playerHitbox.right > obstacleHitbox.left &&
                playerHitbox.left < obstacleHitbox.right &&
                playerHitbox.bottom > obstacleHitbox.top &&
                playerHitbox.top < obstacleHitbox.bottom) {
              // Collision!
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

      // Check collectible collisions
      for (const c of g.collectibles) {
        if (!c.collected && c.z > 0 && c.z < 150 && c.lane === g.player.lane) {
          const scale = 1 - c.z / 1000;
          const colY = GROUND_Y - c.floatHeight * scale - 30;
          
          if (g.player.y < colY + 40 && g.player.y + PLAYER_H > colY) {
            c.collected = true;
            g.mooncakes++;
            const bonus = Math.floor(50 * (1 + g.skinBonus));
            g.score += bonus;
            collectFeedback();
            
            // Collection particles
            for (let i = 0; i < 12; i++) {
              const angle = (Math.PI * 2 / 12) * i;
              g.particles.push({
                x: getLaneX(c.lane, scale),
                y: colY + 15,
                vx: Math.cos(angle) * 4,
                vy: Math.sin(angle) * 4 - 2,
                life: 30,
                color: `hsl(${45 + Math.random() * 15}, 100%, ${60 + Math.random() * 30}%)`
              });
            }
          }
        }
      }

      setScore(g.score);
      setMooncakes(g.mooncakes);

      // ===== DRAW =====
      // Clear and draw deep space background
      const bgGrad = ctx.createLinearGradient(0, 0, 0, H);
      bgGrad.addColorStop(0, '#000005');
      bgGrad.addColorStop(0.3, '#050510');
      bgGrad.addColorStop(1, '#0a0a15');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, W, H);

      // Draw nebula clouds
      g.nebulaClouds.forEach(cloud => {
        const grad = ctx.createRadialGradient(cloud.x, cloud.y, 0, cloud.x, cloud.y, cloud.size);
        grad.addColorStop(0, `hsla(${cloud.hue}, 70%, 40%, ${cloud.alpha})`);
        grad.addColorStop(0.5, `hsla(${cloud.hue + 20}, 60%, 30%, ${cloud.alpha * 0.5})`);
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.fillRect(cloud.x - cloud.size, cloud.y - cloud.size, cloud.size * 2, cloud.size * 2);
      });

      // Draw stars
      g.stars.forEach(s => {
        ctx.fillStyle = `rgba(255, 255, 255, ${s.brightness * 0.8})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Draw horizon glow
      const horizonGrad = ctx.createLinearGradient(0, HORIZON_Y - 30, 0, HORIZON_Y + 50);
      horizonGrad.addColorStop(0, 'transparent');
      horizonGrad.addColorStop(0.5, 'rgba(100, 50, 150, 0.15)');
      horizonGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = horizonGrad;
      ctx.fillRect(0, HORIZON_Y - 30, W, 80);

      // Draw asteroid belt in background
      g.asteroidBelt.forEach(ab => {
        if (ab.z > 200) {
          const scale = Math.max(0.2, 1 - ab.z / 1500);
          ab.asteroids.forEach(a => {
            const ax = VANISHING_POINT_X + a.xOffset * scale;
            const ay = a.yOffset;
            const size = a.size * scale;
            
            ctx.save();
            ctx.translate(ax, ay);
            ctx.rotate(a.rotation);
            
            // Asteroid shape
            ctx.fillStyle = '#4a4a5a';
            ctx.beginPath();
            ctx.ellipse(0, 0, size, size * 0.7, 0, 0, Math.PI * 2);
            ctx.fill();
            
            // Crater details
            ctx.fillStyle = '#3a3a4a';
            ctx.beginPath();
            ctx.arc(size * 0.3, -size * 0.2, size * 0.2, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.restore();
          });
        }
      });

      // Draw 3D perspective ground (space runway)
      // Vanishing point lines
      ctx.strokeStyle = 'rgba(100, 50, 200, 0.3)';
      ctx.lineWidth = 1;
      
      for (let i = 0; i < LANE_COUNT + 1; i++) {
        const startX = VANISHING_POINT_X + (i - 1.5) * 20;
        const endX = VANISHING_POINT_X + (i - 1.5) * LANE_SPACING;
        ctx.beginPath();
        ctx.moveTo(startX, HORIZON_Y);
        ctx.lineTo(endX, GROUND_Y);
        ctx.stroke();
      }

      // Ground plane with grid
      ctx.fillStyle = 'rgba(20, 10, 40, 0.8)';
      ctx.beginPath();
      ctx.moveTo(VANISHING_POINT_X - 30, HORIZON_Y);
      ctx.lineTo(0, GROUND_Y);
      ctx.lineTo(W, GROUND_Y);
      ctx.lineTo(VANISHING_POINT_X + 30, HORIZON_Y);
      ctx.closePath();
      ctx.fill();

      // Energy grid lines
      ctx.strokeStyle = 'rgba(150, 100, 255, 0.2)';
      for (let z = 0; z < 10; z++) {
        const depth = ((z * 100 + g.groundOffset) % 1000) / 1000;
        const y = HORIZON_Y + (GROUND_Y - HORIZON_Y) * depth;
        const spread = (W / 2) * depth;
        
        ctx.beginPath();
        ctx.moveTo(VANISHING_POINT_X - spread, y);
        ctx.lineTo(VANISHING_POINT_X + spread, y);
        ctx.stroke();
      }

      // Glowing edge lines
      const edgeGrad = ctx.createLinearGradient(0, HORIZON_Y, 0, GROUND_Y);
      edgeGrad.addColorStop(0, 'rgba(0, 255, 163, 0.1)');
      edgeGrad.addColorStop(1, 'rgba(0, 255, 163, 0.5)');
      ctx.strokeStyle = edgeGrad;
      ctx.lineWidth = 2;
      
      // Left edge
      ctx.beginPath();
      ctx.moveTo(VANISHING_POINT_X - 30, HORIZON_Y);
      ctx.lineTo(VANISHING_POINT_X - LANE_SPACING * 1.5, GROUND_Y);
      ctx.stroke();
      
      // Right edge
      ctx.beginPath();
      ctx.moveTo(VANISHING_POINT_X + 30, HORIZON_Y);
      ctx.lineTo(VANISHING_POINT_X + LANE_SPACING * 1.5, GROUND_Y);
      ctx.stroke();

      // Draw obstacles (sorted by z for proper depth)
      const sortedObstacles = [...g.obstacles].sort((a, b) => b.z - a.z);
      
      sortedObstacles.forEach(o => {
        if (o.z > 0 && o.z < 1000) {
          const scale = Math.max(0.1, 1 - o.z / 1000);
          const x = getLaneX(o.lane, scale);
          const baseY = o.isFlying ? GROUND_Y - o.flyHeight * scale - o.height * scale : GROUND_Y - o.height * scale;
          const w = o.width * scale;
          const h = o.height * scale;
          
          ctx.save();
          ctx.translate(x, baseY + h / 2);
          
          switch (o.type) {
            case 'meteor':
              // Fiery meteor
              ctx.rotate(o.rotation);
              const meteorGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, w);
              meteorGrad.addColorStop(0, '#ff6600');
              meteorGrad.addColorStop(0.5, '#cc3300');
              meteorGrad.addColorStop(1, '#661100');
              ctx.fillStyle = meteorGrad;
              ctx.beginPath();
              ctx.ellipse(0, 0, w / 2, h / 2, 0, 0, Math.PI * 2);
              ctx.fill();
              
              // Fire trail
              ctx.fillStyle = `rgba(255, 100, 0, ${0.3 + Math.sin(o.pulsePhase) * 0.2})`;
              ctx.beginPath();
              ctx.moveTo(-w / 2, 0);
              ctx.quadraticCurveTo(-w, -h / 4, -w * 1.5, 0);
              ctx.quadraticCurveTo(-w, h / 4, -w / 2, 0);
              ctx.fill();
              break;
              
            case 'debris':
              // Space debris - rocky chunks
              ctx.rotate(o.rotation * 2);
              ctx.fillStyle = '#5a5a6a';
              ctx.beginPath();
              ctx.moveTo(-w / 2, -h / 4);
              ctx.lineTo(-w / 4, -h / 2);
              ctx.lineTo(w / 4, -h / 3);
              ctx.lineTo(w / 2, h / 4);
              ctx.lineTo(0, h / 2);
              ctx.lineTo(-w / 3, h / 4);
              ctx.closePath();
              ctx.fill();
              ctx.strokeStyle = '#7a7a8a';
              ctx.lineWidth = 1;
              ctx.stroke();
              break;
              
            case 'blackhole':
              // Swirling black hole
              const bhGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, w);
              bhGrad.addColorStop(0, '#000000');
              bhGrad.addColorStop(0.4, '#1a0030');
              bhGrad.addColorStop(0.7, '#3a0060');
              bhGrad.addColorStop(1, 'transparent');
              ctx.fillStyle = bhGrad;
              ctx.beginPath();
              ctx.arc(0, 0, w, 0, Math.PI * 2);
              ctx.fill();
              
              // Accretion disk
              ctx.strokeStyle = `rgba(200, 100, 255, ${0.5 + Math.sin(o.pulsePhase * 2) * 0.3})`;
              ctx.lineWidth = 3;
              for (let ring = 0; ring < 3; ring++) {
                ctx.beginPath();
                ctx.ellipse(0, 0, w * (0.6 + ring * 0.15), w * (0.2 + ring * 0.05), o.rotation * 3, 0, Math.PI * 2);
                ctx.stroke();
              }
              break;
              
            case 'satellite':
              // Space satellite
              ctx.fillStyle = '#8899aa';
              ctx.fillRect(-w / 4, -h / 3, w / 2, h / 1.5);
              
              // Solar panels
              ctx.fillStyle = '#2244aa';
              ctx.fillRect(-w / 2, -h / 6, w / 4, h / 3);
              ctx.fillRect(w / 4, -h / 6, w / 4, h / 3);
              
              // Antenna
              ctx.strokeStyle = '#aabbcc';
              ctx.lineWidth = 2;
              ctx.beginPath();
              ctx.moveTo(0, -h / 3);
              ctx.lineTo(0, -h / 2);
              ctx.stroke();
              
              // Blinking light
              if (Math.sin(o.pulsePhase * 3) > 0) {
                ctx.fillStyle = '#ff0000';
                ctx.beginPath();
                ctx.arc(0, -h / 2, 3, 0, Math.PI * 2);
                ctx.fill();
              }
              break;
              
            case 'alienship':
              // UFO-style alien ship
              ctx.fillStyle = '#40e0d0';
              ctx.beginPath();
              ctx.ellipse(0, 0, w / 2, h / 4, 0, 0, Math.PI * 2);
              ctx.fill();
              
              // Dome
              ctx.fillStyle = 'rgba(200, 255, 255, 0.6)';
              ctx.beginPath();
              ctx.ellipse(0, -h / 6, w / 4, h / 4, 0, Math.PI, 0);
              ctx.fill();
              
              // Lights
              const numLights = 5;
              for (let i = 0; i < numLights; i++) {
                const lightPhase = o.pulsePhase + (i / numLights) * Math.PI * 2;
                const alpha = 0.5 + Math.sin(lightPhase * 2) * 0.5;
                ctx.fillStyle = `rgba(255, 255, 0, ${alpha})`;
                const lx = (i - 2) * (w / 5);
                ctx.beginPath();
                ctx.arc(lx, h / 8, 3, 0, Math.PI * 2);
                ctx.fill();
              }
              
              // Beam (occasionally)
              if (Math.sin(o.pulsePhase) > 0.7) {
                ctx.fillStyle = 'rgba(100, 255, 200, 0.2)';
                ctx.beginPath();
                ctx.moveTo(-w / 4, h / 4);
                ctx.lineTo(-w / 2, h);
                ctx.lineTo(w / 2, h);
                ctx.lineTo(w / 4, h / 4);
                ctx.closePath();
                ctx.fill();
              }
              break;
              
            default:
              ctx.fillStyle = '#ff0000';
              ctx.fillRect(-w / 2, -h / 2, w, h);
          }
          
          ctx.restore();
        }
      });

      // Draw collectibles (mooncakes)
      g.collectibles.forEach(c => {
        if (!c.collected && c.z > 0 && c.z < 1000) {
          const scale = Math.max(0.1, 1 - c.z / 1000);
          const x = getLaneX(c.lane, scale);
          const y = GROUND_Y - c.floatHeight * scale - 15;
          const size = 25 * scale;
          
          // Glow
          const glowSize = size * (1.5 + Math.sin(c.glowPhase) * 0.3);
          const glow = ctx.createRadialGradient(x, y, 0, x, y, glowSize);
          glow.addColorStop(0, 'rgba(245, 211, 0, 0.4)');
          glow.addColorStop(1, 'transparent');
          ctx.fillStyle = glow;
          ctx.beginPath();
          ctx.arc(x, y, glowSize, 0, Math.PI * 2);
          ctx.fill();
          
          // Mooncake
          ctx.fillStyle = '#F5D300';
          ctx.beginPath();
          ctx.arc(x, y, size, 0, Math.PI * 2);
          ctx.fill();
          
          // Inner detail
          ctx.fillStyle = '#E5C300';
          ctx.beginPath();
          ctx.arc(x, y, size * 0.6, 0, Math.PI * 2);
          ctx.fill();
          
          // Sparkle
          ctx.fillStyle = '#FFFFFF';
          ctx.beginPath();
          ctx.arc(x - size * 0.3, y - size * 0.3, size * 0.15, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      // Draw player with 3D effect
      const playerX = g.player.x;
      const playerY = g.player.y;
      
      // Player shadow
      ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
      ctx.beginPath();
      ctx.ellipse(playerX + PLAYER_W / 2, GROUND_Y - 5, PLAYER_W / 2, 10, 0, 0, Math.PI * 2);
      ctx.fill();
      
      // Player glow based on skin color
      const playerGlow = ctx.createRadialGradient(
        playerX + PLAYER_W / 2, playerY + PLAYER_H / 2, 0,
        playerX + PLAYER_W / 2, playerY + PLAYER_H / 2, PLAYER_W
      );
      playerGlow.addColorStop(0, `${g.skinColor}40`);
      playerGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = playerGlow;
      ctx.beginPath();
      ctx.arc(playerX + PLAYER_W / 2, playerY + PLAYER_H / 2, PLAYER_W, 0, Math.PI * 2);
      ctx.fill();
      
      // Draw sprite or fallback
      if (spriteRef.current) {
        // Apply skin color tint
        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.drawImage(spriteRef.current, playerX, playerY, PLAYER_W, PLAYER_H);
        
        // Color overlay for skin variation
        if (currentSkinId !== 'default') {
          ctx.globalCompositeOperation = 'overlay';
          ctx.fillStyle = g.skinColor;
          ctx.globalAlpha = 0.4;
          ctx.fillRect(playerX, playerY, PLAYER_W, PLAYER_H);
        }
        ctx.restore();
      } else {
        // Fallback 3D character
        ctx.fillStyle = g.skinColor || '#D946EF';
        ctx.beginPath();
        ctx.roundRect(playerX, playerY, PLAYER_W, PLAYER_H, 10);
        ctx.fill();
        
        // Face
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(playerX + PLAYER_W * 0.35, playerY + PLAYER_H * 0.35, 5, 0, Math.PI * 2);
        ctx.arc(playerX + PLAYER_W * 0.65, playerY + PLAYER_H * 0.35, 5, 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw particles
      g.particles.forEach(p => {
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.life / 30;
        ctx.fillRect(p.x - 2, p.y - 2, 4, 4);
      });
      ctx.globalAlpha = 1;

      // Draw HUD
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 16px Orbitron, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`SCORE: ${g.score}`, 20, 30);
      ctx.fillStyle = '#F5D300';
      ctx.fillText(`MOONCAKES: ${g.mooncakes}`, 20, 55);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '12px monospace';
      ctx.fillText(`STAGE ${g.stage}`, 20, 75);
      
      // Stage indicator
      const stageColors = ['#00FFA3', '#00CED1', '#D946EF', '#FF6B35', '#FF3B30'];
      ctx.fillStyle = stageColors[g.stage - 1] || '#FFFFFF';
      ctx.fillRect(20, 80, 80 * (g.stage / 5), 4);
      ctx.strokeStyle = 'rgba(255,255,255,0.3)';
      ctx.strokeRect(20, 80, 80, 4);
      
      // Best score
      ctx.textAlign = 'right';
      ctx.fillStyle = '#64748b';
      ctx.font = '12px monospace';
      ctx.fillText(`BEST: ${Math.max(g.score, highScore)}`, W - 20, 30);

      // Lane indicators at bottom
      ctx.textAlign = 'center';
      ctx.font = '10px monospace';
      ctx.fillStyle = 'rgba(255,255,255,0.3)';
      for (let i = 0; i < LANE_COUNT; i++) {
        const lx = getLaneX(i);
        ctx.fillText(i === g.player.lane ? '●' : '○', lx, H - 10);
      }

      // Controls hint
      ctx.fillStyle = 'rgba(255,255,255,0.4)';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('← A/D → to switch lanes | SPACE to jump', W / 2, H - 25);

      animRef.current = requestAnimationFrame(loop);
    };
    
    animRef.current = requestAnimationFrame(loop);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highScore, totalMooncakes, playerName, currentSkin, currentSkinId]);

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

  // Touch controls for mobile
  const handleTouchStart = (e) => {
    if (gameState !== "playing") {
      startGame();
      return;
    }
    
    const touch = e.touches[0];
    const rect = canvasRef.current.getBoundingClientRect();
    const x = touch.clientX - rect.left;
    const third = rect.width / 3;
    
    if (x < third) {
      keysRef.current.left = true;
    } else if (x > third * 2) {
      keysRef.current.right = true;
    } else {
      keysRef.current.jump = true;
    }
  };

  // Cleanup animation on unmount
  useEffect(() => {
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
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
            <button
              onClick={() => setShowSkinStore(true)}
              data-testid="skin-store-btn"
              className="p-2 rounded-full bg-[#D946EF]/10 border border-[#D946EF]/30 text-[#D946EF] hover:bg-[#D946EF]/20 transition-all"
              title="Skin Store"
            >
              <Store size={18} />
            </button>
            <Link
              to={connected ? `/showcase/${publicKey?.toBase58()}` : "/showcase"}
              data-testid="showcase-btn"
              className="p-2 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30 text-[#00FFA3] hover:bg-[#00FFA3]/20 transition-all"
              title="My Collection"
            >
              <Award size={18} />
            </Link>
            <button
              onClick={toggleSound}
              data-testid="game-sound-toggle"
              className="p-2 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all"
            >
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
                      <Input 
                        defaultValue={playerName}
                        maxLength={20}
                        className="w-28 h-7 bg-black/50 border-white/10 text-white text-sm"
                        onKeyDown={(e) => { if (e.key === "Enter") savePlayerName(e.target.value); }}
                        autoFocus
                      />
                      <button onClick={(e) => savePlayerName(e.target.previousSibling.value)} className="text-xs text-[#00FFA3]">Save</button>
                    </div>
                  ) : (
                    <button onClick={() => setShowNameInput(true)} className="text-sm text-white hover:text-[#00FFA3]">
                      {playerName}
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <Badge className={`text-[10px] ${currentStage >= 3 ? 'bg-purple-500/20 text-purple-300 border-purple-500/30' : 'bg-slate-500/20 text-slate-400 border-slate-500/30'}`}>
                    Stage {currentStage}/5
                  </Badge>
                  <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px]">
                    <Clock className="w-3 h-3 mr-1" />
                    Resets in {leaderboardMeta.days_until_reset}d
                  </Badge>
                </div>
              </div>

              <div className="relative mx-auto" style={{ maxWidth: W }}>
                <canvas 
                  ref={canvasRef} 
                  width={W} 
                  height={H}
                  onTouchStart={handleTouchStart}
                  className="w-full rounded-xl border-2 border-[#D946EF]/30 cursor-pointer bg-[#000005]"
                  data-testid="game-canvas" 
                />

                {gameState === "idle" && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 rounded-xl">
                    <div className="relative mb-4">
                      <img src={currentSkin.image} alt="Bullpug" className="w-24 h-24 rounded-xl border-2" style={{ borderColor: currentSkin.color }} />
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
                    <p className="text-lg text-[#F5D300] mb-2">Stage {currentStage} Reached</p>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-[#F5D300] font-bold">+{mooncakes} Mooncakes</span>
                    </div>
                    {score >= highScore && score > 0 && (
                      <Badge className="bg-[#F5D300]/20 text-[#F5D300] border-[#F5D300]/40 mb-3 text-sm">
                        <Sparkles className="w-4 h-4 mr-1" /> NEW HIGH SCORE!
                      </Badge>
                    )}
                    <div className="flex items-center gap-3 mt-2">
                      <Button onClick={startGame} data-testid="restart-game-btn"
                        className="bg-[#00FFA3] text-black font-bold rounded-full px-6 py-3 uppercase hover:scale-105 transition-transform">
                        <RotateCcw className="w-4 h-4 mr-2" /> RETRY
                      </Button>
                      <Button 
                        onClick={() => {
                          const text = `I scored ${score} points in Cosmic Runner and reached Stage ${currentStage}!\n\nPlay now at bullpug.com #Bullpug #CosmicRunner #Solana`;
                          window.open(`https://x.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
                        }}
                        className="bg-black text-white border border-white/30 font-bold rounded-full px-5 py-3 uppercase hover:bg-white/10">
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
                    <p className="text-xl font-black text-[#F5D300]" style={{ fontFamily: 'Orbitron' }}>{highScore}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <p className="text-xs text-slate-500">Mooncakes</p>
                    <p className="text-lg font-bold text-[#F5D300]">{totalMooncakes}</p>
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
                <span className="text-[#F5D300]">🏆</span> WEEKLY LEADERBOARD
              </h3>
              <div className="space-y-2">
                {leaderboard.slice(0, 8).map((entry, i) => (
                  <div key={i} className={`flex items-center justify-between p-2 rounded-lg ${i < 3 ? 'bg-gradient-to-r from-[#F5D300]/10 to-transparent' : 'bg-white/5'}`}>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${i === 0 ? 'text-[#F5D300]' : i === 1 ? 'text-slate-300' : i === 2 ? 'text-amber-600' : 'text-slate-500'}`}>
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
