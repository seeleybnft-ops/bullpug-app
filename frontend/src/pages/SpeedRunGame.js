import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useWallet } from "@solana/wallet-adapter-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Play, RotateCcw, Clock, User, Volume2, VolumeX, Store, Sparkles, Award, ChevronLeft, ChevronRight, ArrowUp, Music, Music2, Trophy } from "lucide-react";
import { playSoundIfEnabled, isSoundEnabled, setSoundEnabled, collectFeedback, winFeedback, startBackgroundMusic, stopBackgroundMusic, isMusicPlaying, setMusicVolume, getMusicVolume } from "@/utils/sounds";
import { getSkinById, SKINS } from "@/config/skins";
import SkinStore from "@/components/SkinStore";
import JackpotDisplay from "@/components/JackpotDisplay";
import GameAchievements from "@/components/GameAchievements";
import LeaderboardPanel from "@/components/LeaderboardPanel";
import { CosmicRunner3DScene } from "@/pages/Phase1Runner3D";
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
    name: 'Moon Cheese Magnet', 
    description: 'Attracts moon cheese from all lanes',
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
  const scene3DRef = useRef(null);
  const [gameState, setGameState] = useState("idle");
  const [score, setScore] = useState(0);
  const [moonCheese, setMoonCheese] = useState(0);
  const [highScore, setHighScore] = useState(() => parseInt(localStorage.getItem("bullpugHighScore") || "0"));
  const [totalMoonCheese, setTotalMoonCheese] = useState(() => parseInt(localStorage.getItem("bullpugMoonCheese") || "0"));
  const [leaderboard, setLeaderboard] = useState([]);
  const [leaderboardMeta, setLeaderboardMeta] = useState({ days_until_reset: 0 });
  const [playerName, setPlayerName] = useState(() => localStorage.getItem("bullpugPlayerName") || "Guardian");
  const [showNameInput, setShowNameInput] = useState(false);
  const [soundOn, setSoundOn] = useState(isSoundEnabled());
  const [musicOn, setMusicOn] = useState(() => localStorage.getItem("bullpugMusicEnabled") !== "false");
  const [showSkinStore, setShowSkinStore] = useState(false);
  const [currentSkinId, setCurrentSkinId] = useState(() => localStorage.getItem("bullpugSkin") || "default");
  const [currentStage, setCurrentStage] = useState(1);
  const gameRef = useRef(null);
  const animRef = useRef(null);
  const spriteRef = useRef(null);
  const keysRef = useRef({ left: false, right: false, jump: false });

  const currentSkin = getSkinById(currentSkinId);

  // Moon cheese image ref
  const moonCheeseImgRef = useRef(null);
  const [moonCheeseImg, setMoonCheeseImg] = useState(null);

  const toggleSound = () => {
    const newValue = !soundOn;
    setSoundOn(newValue);
    setSoundEnabled(newValue);
    if (newValue) playSoundIfEnabled('click');
  };

  const toggleMusic = () => {
    const newValue = !musicOn;
    setMusicOn(newValue);
    localStorage.setItem("bullpugMusicEnabled", newValue ? "true" : "false");
    if (newValue) {
      startBackgroundMusic();
    } else {
      stopBackgroundMusic();
    }
  };

  // Stop music when component unmounts
  useEffect(() => {
    return () => {
      stopBackgroundMusic();
    };
  }, []);

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

  // Preload moon cheese image
  useEffect(() => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = "/moon-cheese.png";  // Local image to avoid CORS issues
    img.onload = () => { 
      moonCheeseImgRef.current = img;
      setMoonCheeseImg(img);
    };
  }, []);

  const fetchLeaderboard = async () => {
    try {
      const { data } = await axios.get(`${API}/leaderboard?limit=10`);
      setLeaderboard(data.leaderboard);
      setLeaderboardMeta({ days_until_reset: data.days_until_reset, next_reset: data.next_reset });
    } catch (e) { console.error("Leaderboard fetch failed"); }
  };

  useEffect(() => { fetchLeaderboard(); }, []);

  const submitScore = async (finalScore, finalMoonCheese) => {
    if (finalScore <= 0) return;
    try {
      const { data } = await axios.post(`${API}/leaderboard/submit`, {
        player_name: playerName, score: finalScore, moonCheese: finalMoonCheese
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
    // Dynamic background elements - ENHANCED for Subway Surfers style
    // Far background stars (slowest parallax layer)
    stars: Array.from({ length: 300 }, () => ({
      x: Math.random() * W,
      y: Math.random() * HORIZON_Y * 1.5,
      z: Math.random(), // depth for parallax
      size: Math.random() * 3 + 0.5,
      twinkle: Math.random() * Math.PI * 2,
      speed: 0.1 + Math.random() * 0.3,
      color: Math.random() > 0.8 ? 'blue' : Math.random() > 0.5 ? 'yellow' : 'white'
    })),
    // Nebulas - multiple layers
    nebulas: Array.from({ length: 15 }, () => ({
      x: Math.random() * W * 1.5,
      y: Math.random() * HORIZON_Y,
      z: Math.random() * 0.8 + 0.2,
      size: 100 + Math.random() * 200,
      hue: Math.random() * 360,
      alpha: 0.08 + Math.random() * 0.12,
      speed: 0.2 + Math.random() * 0.4,
      type: Math.random() > 0.5 ? 'swirl' : 'cloud'
    })),
    // Distant galaxies/planets - more variety
    cosmicObjects: Array.from({ length: 8 }, () => ({
      x: Math.random() * W,
      y: 15 + Math.random() * (HORIZON_Y - 30),
      size: 20 + Math.random() * 60,
      type: ['galaxy', 'planet', 'ring-planet', 'sun'][Math.floor(Math.random() * 4)],
      hue: Math.random() * 360,
      rotation: Math.random() * Math.PI * 2,
      speed: 0.05 + Math.random() * 0.15,
      rings: Math.random() > 0.5,
      moons: Math.floor(Math.random() * 3)
    })),
    // Mid-distance floating asteroids (NEW)
    asteroids: Array.from({ length: 20 }, () => ({
      x: Math.random() * W * 1.2,
      y: HORIZON_Y * 0.6 + Math.random() * (GROUND_Y - HORIZON_Y) * 0.5,
      z: 0.3 + Math.random() * 0.5,
      size: 8 + Math.random() * 25,
      rotation: Math.random() * Math.PI * 2,
      rotSpeed: (Math.random() - 0.5) * 0.02,
      speedX: 0.3 + Math.random() * 0.8,
      wobble: Math.random() * Math.PI * 2,
      type: Math.floor(Math.random() * 3) // 0: round, 1: jagged, 2: elongated
    })),
    // Cosmic dust particles (NEW - near-field particles)
    cosmicDust: Array.from({ length: 60 }, () => ({
      x: Math.random() * W,
      y: HORIZON_Y + Math.random() * (H - HORIZON_Y),
      z: Math.random(),
      size: 1 + Math.random() * 3,
      alpha: 0.1 + Math.random() * 0.4,
      speed: 1 + Math.random() * 3,
      color: Math.random() > 0.5 ? 'cyan' : Math.random() > 0.5 ? 'magenta' : 'gold'
    })),
    // Space station silhouettes in distance (NEW)
    spaceStations: Array.from({ length: 2 }, () => ({
      x: Math.random() * W * 0.8 + W * 0.1,
      y: HORIZON_Y * 0.5 + Math.random() * 30,
      size: 30 + Math.random() * 50,
      rotation: Math.random() * Math.PI * 0.1,
      rotSpeed: 0.0005 + Math.random() * 0.001,
      lights: Array.from({ length: 4 }, () => ({
        offset: Math.random() * 20 - 10,
        phase: Math.random() * Math.PI * 2,
        color: Math.random() > 0.5 ? '#00FFFF' : '#FF00FF'
      }))
    })),
    // Comet trails (NEW)
    comets: [],
    cometTimer: 0,
    // Shooting stars for dramatic space traversal effect
    shootingStars: [],
    shootingStarTimer: 0,
    // Speed lines (warp effect) emanating from horizon - MORE dramatic
    speedLines: Array.from({ length: 50 }, () => ({
      angle: (Math.random() - 0.5) * Math.PI * 0.7,
      length: 30 + Math.random() * 120,
      speed: 3 + Math.random() * 6,
      distance: Math.random() * 250,
      alpha: 0.15 + Math.random() * 0.35,
      color: Math.random() > 0.7 ? 'cyan' : Math.random() > 0.5 ? 'magenta' : 'white'
    })),
    // Glowing horizon line (NEW - Subway Surfers style)
    horizonGlow: {
      intensity: 0.5,
      hue: 280,
      pulse: 0
    },
    // Track edge lights (NEW - like street lights in Subway Surfers)
    trackLights: Array.from({ length: 12 }, (_, i) => ({
      depth: i / 12,
      brightness: 0.5 + Math.random() * 0.5,
      phase: Math.random() * Math.PI * 2
    })),
    backgroundHue: 240,
    frame: 0,
    speed: 2.5,
    startTime: Date.now(),
    score: 0,
    moonCheese: 0,
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
    setMoonCheese(0);
    setCurrentStage(1);
    playSoundIfEnabled('click');
    
    // Start background music when game starts (user interaction satisfies autoplay policy)
    if (musicOn) {
      startBackgroundMusic();
    }

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

      // Spawn power-ups every 12 seconds (720 frames at 60fps)
      if (g.frame - g.lastPowerupSpawn >= POWERUP_SPAWN_INTERVAL) {
        g.powerups.push(spawnPowerup(g));
        g.lastPowerupSpawn = g.frame;
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
        
        // Magnet effect - pull moon cheese towards player
        if (g.activePowerups.magnet && Date.now() < g.activePowerups.magnet.endTime) {
          if (c.depth > 0.5 && c.depth < 1.1) {
            // Gradually move moon cheese towards player's lane
            const playerLane = g.player.lane;
            if (c.lane !== playerLane) {
              c.lane += (playerLane - c.lane) * 0.05;
            }
          }
        }
        
        return c.depth < 1.3 && !c.collected;
      });

      // Move power-ups
      g.powerups = g.powerups.filter(p => {
        p.depth += depthSpeed;
        p.glow += 0.12;
        p.sparklePhase += 0.15;
        p.rotation += 0.03;
        return p.depth < 1.3 && !p.collected;
      });

      // Update background elements based on speed
      const bgSpeed = g.speed * 0.3;
      
      // Move stars with parallax
      g.stars.forEach(star => {
        star.x -= bgSpeed * star.speed * (1 - star.z * 0.5);
        star.twinkle += 0.05;
        if (star.x < -10) {
          star.x = W + 10;
          star.y = Math.random() * HORIZON_Y * 1.5;
        }
      });
      
      // Move nebulas
      g.nebulas.forEach(nebula => {
        nebula.x -= bgSpeed * nebula.speed * (1 - nebula.z * 0.3);
        if (nebula.x < -nebula.size) {
          nebula.x = W + nebula.size;
          nebula.y = Math.random() * HORIZON_Y;
          nebula.hue = (nebula.hue + 30) % 360;
        }
      });
      
      // Move cosmic objects (distant galaxies/planets)
      g.cosmicObjects.forEach(obj => {
        obj.x -= bgSpeed * obj.speed * 0.3;
        obj.rotation += 0.002;
        if (obj.x < -obj.size) {
          obj.x = W + obj.size;
          obj.y = 20 + Math.random() * (HORIZON_Y - 40);
          obj.hue = Math.random() * 360;
        }
      });

      // Move floating asteroids (NEW - mid-layer parallax)
      if (g.asteroids) {
        g.asteroids.forEach(ast => {
          ast.x -= bgSpeed * ast.speedX * (1 - ast.z * 0.3);
          ast.rotation += ast.rotSpeed;
          ast.wobble += 0.03;
          ast.y += Math.sin(ast.wobble) * 0.3; // Gentle floating
          if (ast.x < -ast.size * 2) {
            ast.x = W + ast.size * 2;
            ast.y = HORIZON_Y * 0.5 + Math.random() * (GROUND_Y - HORIZON_Y) * 0.4;
            ast.z = 0.3 + Math.random() * 0.5;
          }
        });
      }

      // Move cosmic dust particles (NEW - near-field particles for depth)
      if (g.cosmicDust) {
        g.cosmicDust.forEach(dust => {
          dust.x -= dust.speed * (1 + g.speed * 0.5);
          if (dust.x < -5) {
            dust.x = W + 5;
            dust.y = HORIZON_Y + Math.random() * (H - HORIZON_Y);
            dust.alpha = 0.1 + Math.random() * 0.4;
          }
        });
      }

      // Update space stations (NEW - slow rotation)
      if (g.spaceStations) {
        g.spaceStations.forEach(station => {
          station.rotation += station.rotSpeed;
          station.x -= bgSpeed * 0.1;
          if (station.x < -station.size) {
            station.x = W + station.size;
            station.y = HORIZON_Y * 0.4 + Math.random() * 40;
          }
          station.lights.forEach(light => {
            light.phase += 0.05;
          });
        });
      }

      // Spawn comets periodically (NEW - dramatic effect)
      if (g.cometTimer !== undefined) {
        g.cometTimer++;
        if (g.cometTimer > 300 && Math.random() < 0.02) { // Every ~5 seconds chance
          g.comets.push({
            x: W + 100,
            y: Math.random() * HORIZON_Y * 0.6,
            speed: 4 + Math.random() * 4,
            angle: Math.PI + (Math.random() - 0.5) * 0.2,
            size: 15 + Math.random() * 25,
            tailLength: 80 + Math.random() * 120,
            hue: Math.random() > 0.5 ? 180 : 30, // Cyan or orange
            alpha: 0.8
          });
          g.cometTimer = 0;
        }
      }

      // Move comets
      if (g.comets) {
        g.comets = g.comets.filter(comet => {
          comet.x += Math.cos(comet.angle) * comet.speed;
          comet.y += Math.sin(comet.angle) * comet.speed * 0.2;
          comet.alpha -= 0.003;
          return comet.x > -comet.tailLength && comet.alpha > 0;
        });
      }

      // Update horizon glow (NEW - pulsing effect)
      if (g.horizonGlow) {
        g.horizonGlow.pulse += 0.02;
        g.horizonGlow.intensity = 0.4 + Math.sin(g.horizonGlow.pulse) * 0.2;
        g.horizonGlow.hue = (g.backgroundHue + 40) % 360;
      }

      // Update track lights (NEW)
      if (g.trackLights) {
        g.trackLights.forEach(light => {
          light.phase += 0.08;
          light.brightness = 0.3 + Math.sin(light.phase) * 0.3 + 0.3;
        });
      }
      
      // Spawn shooting stars periodically (more at higher speeds)
      g.shootingStarTimer++;
      const shootingStarChance = 60 - Math.min(g.speed * 5, 40); // faster spawn at higher speed
      if (g.shootingStarTimer > shootingStarChance && Math.random() < 0.3) {
        g.shootingStars.push({
          x: W + 20,
          y: Math.random() * HORIZON_Y * 0.8,
          length: 40 + Math.random() * 80,
          speed: 8 + Math.random() * 12 + g.speed * 2,
          angle: Math.PI + (Math.random() - 0.5) * 0.3, // slightly varied angle
          alpha: 0.6 + Math.random() * 0.4,
          hue: Math.random() > 0.7 ? 180 + Math.random() * 60 : 30 + Math.random() * 30 // cyan or orange
        });
        g.shootingStarTimer = 0;
      }
      
      // Move shooting stars
      g.shootingStars = g.shootingStars.filter(ss => {
        ss.x += Math.cos(ss.angle) * ss.speed;
        ss.y += Math.sin(ss.angle) * ss.speed * 0.3;
        ss.alpha -= 0.008;
        return ss.x > -ss.length && ss.alpha > 0;
      });
      
      // Update speed lines (warp effect) - faster movement at higher game speeds
      g.speedLines.forEach(line => {
        line.distance += line.speed * (1 + g.speed * 0.3);
        if (line.distance > 350) {
          line.distance = 0;
          line.angle = (Math.random() - 0.5) * Math.PI * 0.6;
          line.length = 20 + Math.random() * 80;
          line.alpha = 0.1 + Math.random() * 0.3;
        }
      });
      
      // Update background hue based on stage
      const stageTheme = STAGE_BACKGROUNDS[g.stage];
      if (stageTheme.hue === -1) {
        // Rainbow effect for stage 5
        g.backgroundHue = (g.frame * 0.5) % 360;
      } else {
        // Smoothly transition to stage hue
        const targetHue = stageTheme.hue;
        g.backgroundHue += (targetHue - g.backgroundHue) * 0.02;
      }

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
              // Check if shield is active
              if (g.activePowerups.shield && Date.now() < g.activePowerups.shield.endTime) {
                // Shield absorbs hit
                g.activePowerups.shield = null;
                // Shield break effect
                for (let i = 0; i < 20; i++) {
                  const angle = (Math.PI * 2 / 20) * i;
                  g.particles.push({
                    x: playerX, y: playerY + playerH / 2,
                    vx: Math.cos(angle) * 8,
                    vy: Math.sin(angle) * 8,
                    life: 40,
                    color: `rgba(0, 255, 255, ${0.8 - i * 0.03})`
                  });
                }
                // Remove the obstacle
                o.depth = 2; // Mark for removal
                playSoundIfEnabled('collect');
                continue;
              }
              
              g.running = false;
              setGameState("over");
              setScore(g.score);
              setMoonCheese(g.moonCheese);
              const newTotal = totalMoonCheese + g.moonCheese;
              setTotalMoonCheese(newTotal);
              localStorage.setItem("bullpugMoonCheese", String(newTotal));
              if (g.score > highScore) {
                setHighScore(g.score);
                localStorage.setItem("bullpugHighScore", String(g.score));
                winFeedback();
                playSoundIfEnabled('newHighScore');
              } else {
                playSoundIfEnabled('gameover');
              }
              submitScore(g.score, g.moonCheese);
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
              g.moonCheese++;
              // Check for double score power-up
              const scoreMultiplier = (g.activePowerups.doubleScore && Date.now() < g.activePowerups.doubleScore.endTime) ? 2 : 1;
              g.score += Math.floor(25 * (1 + g.skinBonus) * scoreMultiplier);
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

      // Power-up collision
      for (const p of g.powerups) {
        if (!p.collected && p.depth >= 0.8 && p.depth <= 1.1) {
          if (Math.abs(p.lane - Math.round(playerLane)) < 0.5) {
            const scale = getDepthScale(p.depth);
            const powY = getDepthY(p.depth) - p.floatOffset * scale - 20;
            if (playerY < powY + 50 && playerY + playerH > powY - 15) {
              p.collected = true;
              
              // Activate power-up for 10 seconds
              const powerupConfig = POWERUP_TYPES[p.type];
              g.activePowerups[p.type] = {
                endTime: Date.now() + powerupConfig.duration
              };
              
              collectFeedback();
              playSoundIfEnabled('collect');
              
              // Sparkle burst effect
              const powX = getLaneX(p.lane, p.depth);
              for (let i = 0; i < 25; i++) {
                const angle = (Math.PI * 2 / 25) * i;
                g.particles.push({
                  x: powX, y: powY + 15,
                  vx: Math.cos(angle) * 7,
                  vy: Math.sin(angle) * 7 - 3,
                  life: 45,
                  color: powerupConfig.color
                });
              }
            }
          }
        }
      }

      setScore(g.score);
      setMoonCheese(g.moonCheese);

      // ===== RENDERING =====
      // Deep space background - color changes with stage (stageTheme already declared above)
      const bgGrad = ctx.createLinearGradient(0, 0, 0, H);
      const hue = g.backgroundHue;
      bgGrad.addColorStop(0, `hsl(${hue}, 50%, 1%)`);
      bgGrad.addColorStop(0.25, `hsl(${hue}, 55%, 4%)`);
      bgGrad.addColorStop(0.5, `hsl(${hue}, 50%, 6%)`);
      bgGrad.addColorStop(1, `hsl(${hue}, 45%, 10%)`);
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, W, H);

      // Draw comets (behind everything else) - NEW
      if (g.comets) {
        g.comets.forEach(comet => {
          ctx.save();
          ctx.translate(comet.x, comet.y);
          
          // Comet tail (gradient trail)
          const tailGrad = ctx.createLinearGradient(comet.tailLength, 0, 0, 0);
          tailGrad.addColorStop(0, 'transparent');
          tailGrad.addColorStop(0.3, `hsla(${comet.hue}, 80%, 60%, ${comet.alpha * 0.2})`);
          tailGrad.addColorStop(0.7, `hsla(${comet.hue}, 90%, 70%, ${comet.alpha * 0.5})`);
          tailGrad.addColorStop(1, `hsla(${comet.hue}, 100%, 90%, ${comet.alpha})`);
          
          ctx.strokeStyle = tailGrad;
          ctx.lineWidth = comet.size * 0.5;
          ctx.lineCap = 'round';
          ctx.beginPath();
          ctx.moveTo(comet.tailLength, 0);
          ctx.lineTo(0, 0);
          ctx.stroke();
          
          // Comet head (glowing nucleus)
          const headGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, comet.size);
          headGrad.addColorStop(0, `hsla(${comet.hue}, 100%, 95%, ${comet.alpha})`);
          headGrad.addColorStop(0.3, `hsla(${comet.hue}, 90%, 80%, ${comet.alpha * 0.7})`);
          headGrad.addColorStop(1, 'transparent');
          ctx.fillStyle = headGrad;
          ctx.beginPath();
          ctx.arc(0, 0, comet.size, 0, Math.PI * 2);
          ctx.fill();
          
          ctx.restore();
        });
      }

      // Draw space stations (silhouettes in far distance) - NEW
      if (g.spaceStations) {
        g.spaceStations.forEach(station => {
          ctx.save();
          ctx.translate(station.x, station.y);
          ctx.rotate(station.rotation);
          
          // Main structure (dark silhouette)
          ctx.fillStyle = 'rgba(20, 20, 40, 0.6)';
          // Central hub
          ctx.beginPath();
          ctx.arc(0, 0, station.size * 0.3, 0, Math.PI * 2);
          ctx.fill();
          // Solar panels
          ctx.fillRect(-station.size, -station.size * 0.08, station.size * 0.7, station.size * 0.16);
          ctx.fillRect(station.size * 0.3, -station.size * 0.08, station.size * 0.7, station.size * 0.16);
          // Antennae
          ctx.fillRect(-station.size * 0.05, -station.size * 0.5, station.size * 0.1, station.size * 0.3);
          
          // Blinking lights
          station.lights.forEach((light, i) => {
            const blinkAlpha = (Math.sin(light.phase) + 1) * 0.5;
            ctx.fillStyle = light.color;
            ctx.globalAlpha = blinkAlpha * 0.8;
            ctx.beginPath();
            ctx.arc(light.offset, (i - 1.5) * 8, 3, 0, Math.PI * 2);
            ctx.fill();
          });
          
          ctx.globalAlpha = 1;
          ctx.restore();
        });
      }

      // Cosmic objects (distant galaxies and planets) - ENHANCED
      g.cosmicObjects.forEach(obj => {
        ctx.save();
        ctx.translate(obj.x, obj.y);
        ctx.rotate(obj.rotation);
        
        if (obj.type === 'galaxy') {
          // Spiral galaxy with arms
          const galaxyGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, obj.size);
          galaxyGrad.addColorStop(0, `hsla(${obj.hue}, 80%, 90%, 0.5)`);
          galaxyGrad.addColorStop(0.2, `hsla(${obj.hue + 20}, 70%, 70%, 0.3)`);
          galaxyGrad.addColorStop(0.5, `hsla(${obj.hue + 40}, 60%, 50%, 0.15)`);
          galaxyGrad.addColorStop(1, 'transparent');
          ctx.fillStyle = galaxyGrad;
          ctx.beginPath();
          ctx.ellipse(0, 0, obj.size, obj.size * 0.4, 0, 0, Math.PI * 2);
          ctx.fill();
          // Spiral arm suggestion
          ctx.strokeStyle = `hsla(${obj.hue}, 60%, 70%, 0.2)`;
          ctx.lineWidth = 2;
          ctx.beginPath();
          for (let a = 0; a < Math.PI * 4; a += 0.1) {
            const r = obj.size * 0.1 + a * obj.size * 0.08;
            const x = Math.cos(a) * r * Math.cos(0.3);
            const y = Math.sin(a) * r * 0.4;
            a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
          }
          ctx.stroke();
        } else if (obj.type === 'ring-planet') {
          // Planet with rings (Saturn-like)
          const planetGrad = ctx.createRadialGradient(-obj.size * 0.15, -obj.size * 0.15, 0, 0, 0, obj.size * 0.4);
          planetGrad.addColorStop(0, `hsla(${obj.hue}, 40%, 70%, 0.7)`);
          planetGrad.addColorStop(0.6, `hsla(${obj.hue + 15}, 50%, 50%, 0.5)`);
          planetGrad.addColorStop(1, `hsla(${obj.hue + 30}, 40%, 30%, 0.3)`);
          // Rings (behind planet)
          ctx.strokeStyle = `hsla(${obj.hue + 60}, 30%, 60%, 0.4)`;
          ctx.lineWidth = obj.size * 0.15;
          ctx.beginPath();
          ctx.ellipse(0, 0, obj.size * 0.8, obj.size * 0.2, 0, Math.PI, Math.PI * 2);
          ctx.stroke();
          // Planet body
          ctx.fillStyle = planetGrad;
          ctx.beginPath();
          ctx.arc(0, 0, obj.size * 0.4, 0, Math.PI * 2);
          ctx.fill();
          // Rings (in front of planet)
          ctx.strokeStyle = `hsla(${obj.hue + 60}, 30%, 60%, 0.5)`;
          ctx.beginPath();
          ctx.ellipse(0, 0, obj.size * 0.8, obj.size * 0.2, 0, 0, Math.PI);
          ctx.stroke();
        } else if (obj.type === 'sun') {
          // Distant sun/star with corona
          const sunGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, obj.size);
          sunGrad.addColorStop(0, `hsla(40, 100%, 95%, 0.9)`);
          sunGrad.addColorStop(0.2, `hsla(30, 100%, 70%, 0.6)`);
          sunGrad.addColorStop(0.5, `hsla(20, 90%, 50%, 0.3)`);
          sunGrad.addColorStop(1, 'transparent');
          ctx.fillStyle = sunGrad;
          ctx.beginPath();
          ctx.arc(0, 0, obj.size, 0, Math.PI * 2);
          ctx.fill();
          // Solar flares
          ctx.strokeStyle = `hsla(35, 100%, 70%, 0.3)`;
          ctx.lineWidth = 2;
          for (let i = 0; i < 8; i++) {
            const angle = (Math.PI * 2 / 8) * i + obj.rotation * 2;
            const len = obj.size * (0.8 + Math.sin(g.frame * 0.05 + i) * 0.3);
            ctx.beginPath();
            ctx.moveTo(Math.cos(angle) * obj.size * 0.3, Math.sin(angle) * obj.size * 0.3);
            ctx.lineTo(Math.cos(angle) * len, Math.sin(angle) * len);
            ctx.stroke();
          }
        } else {
          // Regular planet
          const planetGrad = ctx.createRadialGradient(-obj.size * 0.2, -obj.size * 0.2, 0, 0, 0, obj.size * 0.8);
          planetGrad.addColorStop(0, `hsla(${obj.hue}, 50%, 65%, 0.7)`);
          planetGrad.addColorStop(0.5, `hsla(${obj.hue + 20}, 45%, 45%, 0.5)`);
          planetGrad.addColorStop(1, `hsla(${obj.hue + 40}, 35%, 25%, 0.25)`);
          ctx.fillStyle = planetGrad;
          ctx.beginPath();
          ctx.arc(0, 0, obj.size * 0.5, 0, Math.PI * 2);
          ctx.fill();
          // Surface detail lines
          ctx.strokeStyle = `hsla(${obj.hue + 30}, 30%, 40%, 0.3)`;
          ctx.lineWidth = 1;
          for (let i = 0; i < 3; i++) {
            const y = (i - 1) * obj.size * 0.15;
            ctx.beginPath();
            ctx.ellipse(0, y, obj.size * 0.45, obj.size * 0.08, 0, 0, Math.PI * 2);
            ctx.stroke();
          }
        }
        ctx.restore();
      });

      // Nebulas - moving with parallax
      g.nebulas.forEach(n => {
        // Use stage-influenced hue
        const nebulaHue = stageTheme.hue === -1 ? (n.hue + g.frame * 0.3) % 360 : (stageTheme.hue + n.hue * 0.3) % 360;
        const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.size);
        grad.addColorStop(0, `hsla(${nebulaHue}, 70%, 40%, ${n.alpha * stageTheme.nebulaDensity * 0.15})`);
        grad.addColorStop(0.4, `hsla(${nebulaHue + 30}, 60%, 30%, ${n.alpha * stageTheme.nebulaDensity * 0.08})`);
        grad.addColorStop(0.7, `hsla(${nebulaHue + 60}, 50%, 20%, ${n.alpha * stageTheme.nebulaDensity * 0.04})`);
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Stars with twinkling and parallax movement
      g.stars.forEach(s => {
        const brightness = (0.4 + Math.sin(s.twinkle) * 0.4) * stageTheme.starBrightness;
        // Color variation
        let starHue;
        if (s.color === 'blue') starHue = 220;
        else if (s.color === 'yellow') starHue = 45;
        else starHue = stageTheme.hue === -1 ? (g.frame * 2 + s.twinkle * 50) % 360 : (stageTheme.hue + 60 + Math.sin(s.twinkle) * 30);
        ctx.fillStyle = `hsla(${starHue}, ${s.color === 'white' ? '10' : '60'}%, 100%, ${brightness})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size * (0.8 + Math.sin(s.twinkle) * 0.2), 0, Math.PI * 2);
        ctx.fill();
        // Star glow for larger stars
        if (s.size > 2) {
          ctx.fillStyle = `hsla(${starHue}, 60%, 80%, ${brightness * 0.3})`;
          ctx.beginPath();
          ctx.arc(s.x, s.y, s.size * 2, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      // Floating asteroids in mid-distance (NEW)
      if (g.asteroids) {
        g.asteroids.forEach(ast => {
          ctx.save();
          ctx.translate(ast.x, ast.y);
          ctx.rotate(ast.rotation);
          
          const scale = 0.3 + ast.z * 0.7;
          const size = ast.size * scale;
          
          // Asteroid body with rocky texture
          ctx.fillStyle = `rgba(60, 50, 70, ${0.4 + ast.z * 0.4})`;
          ctx.beginPath();
          
          if (ast.type === 0) {
            // Rounded asteroid
            ctx.arc(0, 0, size, 0, Math.PI * 2);
          } else if (ast.type === 1) {
            // Jagged asteroid
            for (let i = 0; i < 8; i++) {
              const angle = (Math.PI * 2 / 8) * i;
              const r = size * (0.7 + Math.sin(i * 3.7) * 0.3);
              i === 0 ? ctx.moveTo(Math.cos(angle) * r, Math.sin(angle) * r) : ctx.lineTo(Math.cos(angle) * r, Math.sin(angle) * r);
            }
            ctx.closePath();
          } else {
            // Elongated asteroid
            ctx.ellipse(0, 0, size * 1.3, size * 0.6, 0, 0, Math.PI * 2);
          }
          ctx.fill();
          
          // Surface highlights
          ctx.fillStyle = `rgba(100, 90, 120, ${0.3 + ast.z * 0.2})`;
          ctx.beginPath();
          ctx.arc(-size * 0.2, -size * 0.2, size * 0.3, 0, Math.PI * 2);
          ctx.fill();
          
          // Shadow
          ctx.fillStyle = `rgba(20, 15, 30, ${0.3 + ast.z * 0.2})`;
          ctx.beginPath();
          ctx.arc(size * 0.2, size * 0.2, size * 0.4, 0, Math.PI * 2);
          ctx.fill();
          
          ctx.restore();
        });
      }

      // Shooting stars - dramatic streaks across the sky
      g.shootingStars.forEach(ss => {
        const tailX = ss.x - Math.cos(ss.angle) * ss.length;
        const tailY = ss.y - Math.sin(ss.angle) * ss.length * 0.3;
        
        // Glowing trail
        const trailGrad = ctx.createLinearGradient(tailX, tailY, ss.x, ss.y);
        trailGrad.addColorStop(0, 'transparent');
        trailGrad.addColorStop(0.5, `hsla(${ss.hue}, 80%, 70%, ${ss.alpha * 0.3})`);
        trailGrad.addColorStop(0.8, `hsla(${ss.hue}, 90%, 80%, ${ss.alpha * 0.7})`);
        trailGrad.addColorStop(1, `hsla(${ss.hue}, 100%, 95%, ${ss.alpha})`);
        
        ctx.strokeStyle = trailGrad;
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(tailX, tailY);
        ctx.lineTo(ss.x, ss.y);
        ctx.stroke();
        
        // Bright head
        ctx.fillStyle = `hsla(${ss.hue}, 100%, 95%, ${ss.alpha})`;
        ctx.beginPath();
        ctx.arc(ss.x, ss.y, 2.5, 0, Math.PI * 2);
        ctx.fill();
      });

      // Speed lines (warp effect) - emanate from vanishing point - ENHANCED with colors
      ctx.save();
      ctx.translate(VANISHING_X, HORIZON_Y);
      g.speedLines.forEach(line => {
        const startDist = line.distance;
        const endDist = line.distance + line.length * (1 + g.speed * 0.3);
        
        // Calculate alpha based on distance (fade out as they get further)
        const distAlpha = Math.max(0, 1 - line.distance / 350) * line.alpha * (g.speed / 3);
        
        if (distAlpha > 0.02) {
          const startX = Math.cos(line.angle) * startDist;
          const startY = Math.sin(line.angle) * startDist * 0.6;
          const endX = Math.cos(line.angle) * endDist;
          const endY = Math.sin(line.angle) * endDist * 0.6;
          
          // Color based on line.color
          let lineColor;
          if (line.color === 'cyan') lineColor = '180, 255, 255';
          else if (line.color === 'magenta') lineColor = '255, 100, 255';
          else lineColor = '200, 220, 255';
          
          const lineGrad = ctx.createLinearGradient(startX, startY, endX, endY);
          lineGrad.addColorStop(0, 'transparent');
          lineGrad.addColorStop(0.4, `rgba(${lineColor}, ${distAlpha * 0.3})`);
          lineGrad.addColorStop(1, `rgba(${lineColor}, ${distAlpha})`);
          
          ctx.strokeStyle = lineGrad;
          ctx.lineWidth = 1.5 + g.speed * 0.1;
          ctx.beginPath();
          ctx.moveTo(startX, startY);
          ctx.lineTo(endX, endY);
          ctx.stroke();
        }
      });
      ctx.restore();

      // Horizon glow effect (NEW - Subway Surfers style glowing horizon)
      if (g.horizonGlow) {
        const glowGrad = ctx.createRadialGradient(VANISHING_X, HORIZON_Y, 0, VANISHING_X, HORIZON_Y, 300);
        const glowHue = g.horizonGlow.hue;
        const glowIntensity = g.horizonGlow.intensity;
        glowGrad.addColorStop(0, `hsla(${glowHue}, 80%, 60%, ${glowIntensity * 0.4})`);
        glowGrad.addColorStop(0.3, `hsla(${glowHue + 30}, 70%, 50%, ${glowIntensity * 0.2})`);
        glowGrad.addColorStop(0.6, `hsla(${glowHue + 60}, 60%, 40%, ${glowIntensity * 0.1})`);
        glowGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = glowGrad;
        ctx.fillRect(0, 0, W, HORIZON_Y + 100);
      }

      // Cosmic dust particles (NEW - near-field floating particles)
      if (g.cosmicDust) {
        g.cosmicDust.forEach(dust => {
          let dustColor;
          if (dust.color === 'cyan') dustColor = '0, 255, 255';
          else if (dust.color === 'magenta') dustColor = '255, 0, 255';
          else dustColor = '255, 215, 0';
          
          ctx.fillStyle = `rgba(${dustColor}, ${dust.alpha})`;
          ctx.beginPath();
          ctx.arc(dust.x, dust.y, dust.size, 0, Math.PI * 2);
          ctx.fill();
        });
      }

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

      // Track lights on edges (NEW - Subway Surfers style)
      if (g.trackLights) {
        g.trackLights.forEach((light, i) => {
          const depth = (light.depth + g.trackOffset * 0.5) % 1;
          if (depth < 0.1) return;
          
          const y = getDepthY(depth);
          const spread = (LANE_WIDTH * 2.7 - 25) * depth + 25;
          const scale = getDepthScale(depth);
          const brightness = light.brightness * (0.5 + depth * 0.5);
          
          // Left light
          const leftX = VANISHING_X - spread;
          const lightGlow = ctx.createRadialGradient(leftX, y, 0, leftX, y, 20 * scale);
          lightGlow.addColorStop(0, `rgba(0, 255, 163, ${brightness})`);
          lightGlow.addColorStop(0.3, `rgba(0, 255, 163, ${brightness * 0.5})`);
          lightGlow.addColorStop(1, 'transparent');
          ctx.fillStyle = lightGlow;
          ctx.beginPath();
          ctx.arc(leftX, y, 20 * scale, 0, Math.PI * 2);
          ctx.fill();
          
          // Light core
          ctx.fillStyle = `rgba(255, 255, 255, ${brightness})`;
          ctx.beginPath();
          ctx.arc(leftX, y, 3 * scale, 0, Math.PI * 2);
          ctx.fill();
          
          // Right light
          const rightX = VANISHING_X + spread;
          const rightGlow = ctx.createRadialGradient(rightX, y, 0, rightX, y, 20 * scale);
          rightGlow.addColorStop(0, `rgba(217, 70, 239, ${brightness})`);
          rightGlow.addColorStop(0.3, `rgba(217, 70, 239, ${brightness * 0.5})`);
          rightGlow.addColorStop(1, 'transparent');
          ctx.fillStyle = rightGlow;
          ctx.beginPath();
          ctx.arc(rightX, y, 20 * scale, 0, Math.PI * 2);
          ctx.fill();
          
          // Light core
          ctx.fillStyle = `rgba(255, 255, 255, ${brightness})`;
          ctx.beginPath();
          ctx.arc(rightX, y, 3 * scale, 0, Math.PI * 2);
          ctx.fill();
        });
      }

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

      // Draw collectibles (Moon Cheese - using image!)
      g.collectibles.forEach(c => {
        if (c.collected || c.depth < 0.05 || c.depth > 1.15) return;
        
        const scale = getDepthScale(c.depth);
        const x = getLaneX(c.lane, c.depth);
        const y = getDepthY(c.depth) - c.floatOffset * scale - 15;
        const cheeseSize = 45 * scale;
        
        // Outer glow effect
        const glowPulse = 0.8 + Math.sin(c.glow * 2) * 0.2;
        const glowSize = cheeseSize * 1.8 * glowPulse;
        const outerGlow = ctx.createRadialGradient(x, y, 0, x, y, glowSize);
        outerGlow.addColorStop(0, 'rgba(255, 255, 150, 0.8)');
        outerGlow.addColorStop(0.3, 'rgba(255, 230, 80, 0.5)');
        outerGlow.addColorStop(0.6, 'rgba(255, 200, 50, 0.2)');
        outerGlow.addColorStop(1, 'transparent');
        ctx.fillStyle = outerGlow;
        ctx.beginPath();
        ctx.arc(x, y, glowSize, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw moon cheese image
        if (moonCheeseImg && moonCheeseImg.complete) {
          ctx.save();
          ctx.translate(x, y);
          // Slight rotation/wobble effect
          ctx.rotate(Math.sin(c.glow) * 0.1);
          ctx.drawImage(moonCheeseImg, -cheeseSize/2, -cheeseSize/2, cheeseSize, cheeseSize);
          ctx.restore();
        } else {
          // Fallback circle if image not loaded
          ctx.fillStyle = '#FFD700';
          ctx.beginPath();
          ctx.arc(x, y, cheeseSize/2, 0, Math.PI * 2);
          ctx.fill();
        }
        
        // Sparkle effects around the cheese
        for (let s = 0; s < 6; s++) {
          const sparkleAngle = c.glow * 2 + (s / 6) * Math.PI * 2;
          const sparkleRadius = cheeseSize * (0.8 + Math.sin(c.glow * 4 + s * 0.5) * 0.2);
          const sparkleX = x + Math.cos(sparkleAngle) * sparkleRadius;
          const sparkleY = y + Math.sin(sparkleAngle) * sparkleRadius;
          const sparkleSize = (2 + Math.sin(c.glow * 3 + s) * 1.5) * scale;
          const brightness = 0.6 + Math.sin(c.glow * 4 + s) * 0.3;
          
          ctx.fillStyle = `rgba(255, 255, 200, ${brightness})`;
          ctx.beginPath();
          ctx.arc(sparkleX, sparkleY, sparkleSize, 0, Math.PI * 2);
          ctx.fill();
        }
        
        // Update glow animation
        c.glow += 0.08;
      });

      // Draw power-ups (shiny, sparkly, cosmic items)
      g.powerups.forEach(p => {
        if (p.collected || p.depth < 0.05 || p.depth > 1.15) return;
        
        const scale = getDepthScale(p.depth);
        const x = getLaneX(p.lane, p.depth);
        const y = getDepthY(p.depth) - p.floatOffset * scale - 10;
        const size = 25 * scale;
        
        const config = POWERUP_TYPES[p.type];
        
        // Outer sparkle aura (very shiny)
        const auraSize = size * (2.5 + Math.sin(p.glow * 2) * 0.5);
        const auraGrad = ctx.createRadialGradient(x, y, 0, x, y, auraSize);
        auraGrad.addColorStop(0, config.glowColor);
        auraGrad.addColorStop(0.3, `${config.color}40`);
        auraGrad.addColorStop(0.6, `${config.color}15`);
        auraGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = auraGrad;
        ctx.beginPath();
        ctx.arc(x, y, auraSize, 0, Math.PI * 2);
        ctx.fill();
        
        // Sparkle rays (8-pointed star)
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(p.rotation);
        
        for (let i = 0; i < 8; i++) {
          const rayAngle = (i / 8) * Math.PI * 2;
          const rayLen = size * (1.5 + Math.sin(p.sparklePhase + i) * 0.4);
          const rayAlpha = 0.6 + Math.sin(p.sparklePhase * 2 + i) * 0.3;
          
          ctx.strokeStyle = `${config.color}${Math.floor(rayAlpha * 255).toString(16).padStart(2, '0')}`;
          ctx.lineWidth = 2 * scale;
          ctx.beginPath();
          ctx.moveTo(0, 0);
          ctx.lineTo(Math.cos(rayAngle) * rayLen, Math.sin(rayAngle) * rayLen);
          ctx.stroke();
        }
        ctx.restore();
        
        // Main orb with gradient
        const orbGrad = ctx.createRadialGradient(x - size * 0.2, y - size * 0.2, 0, x, y, size);
        orbGrad.addColorStop(0, '#FFFFFF');
        orbGrad.addColorStop(0.3, config.color);
        orbGrad.addColorStop(0.7, shadeColor(config.color, -30));
        orbGrad.addColorStop(1, shadeColor(config.color, -50));
        ctx.fillStyle = orbGrad;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
        
        // Inner icon/symbol
        ctx.fillStyle = '#FFFFFF';
        ctx.font = `${Math.floor(size * 0.9)}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(config.icon, x, y);
        
        // Highlight shine
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.beginPath();
        ctx.arc(x - size * 0.35, y - size * 0.35, size * 0.25, 0, Math.PI * 2);
        ctx.fill();
        
        // Orbiting sparkles
        for (let s = 0; s < 6; s++) {
          const sparkAngle = p.glow * 2.5 + (s / 6) * Math.PI * 2;
          const sparkDist = size * (1.4 + Math.sin(sparkAngle * 2) * 0.2);
          const sx = x + Math.cos(sparkAngle) * sparkDist;
          const sy = y + Math.sin(sparkAngle) * sparkDist;
          const sparkSize = (2 + Math.sin(sparkAngle * 3)) * scale;
          
          ctx.fillStyle = `rgba(255, 255, 255, ${0.7 + Math.sin(sparkAngle * 2) * 0.3})`;
          ctx.beginPath();
          ctx.arc(sx, sy, sparkSize, 0, Math.PI * 2);
          ctx.fill();
        }
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
      
      // Dynamic shadow - enhanced with multiple layers
      const shadowScale = g.player.isJumping ? 0.2 + (1 - Math.min(Math.abs(pY - PLAYER_BASE_Y) / 100, 1)) * 0.25 : 0.5;
      // Outer blur shadow
      ctx.fillStyle = `rgba(0, 0, 0, ${0.08 + shadowScale * 0.06})`;
      ctx.beginPath();
      ctx.ellipse(pX, GROUND_Y - 3, pW * shadowScale * 0.55, 12 * shadowScale, 0, 0, Math.PI * 2);
      ctx.fill();
      // Core shadow
      ctx.fillStyle = `rgba(0, 0, 0, ${0.2 + shadowScale * 0.15})`;
      ctx.beginPath();
      ctx.ellipse(pX, GROUND_Y - 3, pW * shadowScale * 0.42, 7 * shadowScale, 0, 0, Math.PI * 2);
      ctx.fill();
      
      // Prominent rim light for better visibility - ENHANCED
      const rimGlow = ctx.createRadialGradient(pX, pY + pH / 2, pW * 0.45, pX, pY + pH / 2, pW * 0.85);
      rimGlow.addColorStop(0, 'transparent');
      rimGlow.addColorStop(0.6, 'rgba(0, 255, 163, 0.12)');
      rimGlow.addColorStop(0.85, 'rgba(0, 194, 255, 0.18)');
      rimGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = rimGlow;
      ctx.beginPath();
      ctx.arc(pX, pY + pH / 2, pW * 0.85, 0, Math.PI * 2);
      ctx.fill();
      
      // Warm golden glow around bullpug - enhanced
      const charGlow = ctx.createRadialGradient(pX, pY + pH / 2, 0, pX, pY + pH / 2, pW * 0.65);
      charGlow.addColorStop(0, 'rgba(255, 200, 120, 0.28)');
      charGlow.addColorStop(0.4, 'rgba(212, 149, 106, 0.15)');
      charGlow.addColorStop(0.7, 'rgba(212, 149, 106, 0.05)');
      charGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = charGlow;
      ctx.beginPath();
      ctx.arc(pX, pY + pH / 2, pW * 0.65, 0, Math.PI * 2);
      ctx.fill();
      
      // Speed lines when running - enhanced with gradient
      if (g.speed > 2 && !g.player.isJumping) {
        for (let i = 0; i < 4; i++) {
          const lineY = pY + pH * 0.12 + (i / 4) * pH * 0.55;
          const lineAlpha = 0.15 + Math.sin(g.frame * 0.25 + i) * 0.08;
          const lineGrad = ctx.createLinearGradient(pX - pW * 0.6 - g.speed * 12, lineY, pX - pW * 0.35, lineY);
          lineGrad.addColorStop(0, 'transparent');
          lineGrad.addColorStop(0.3, `rgba(255, 230, 180, ${lineAlpha * 0.5})`);
          lineGrad.addColorStop(1, `rgba(255, 220, 180, ${lineAlpha})`);
          ctx.strokeStyle = lineGrad;
          ctx.lineWidth = 2.5 - i * 0.3;
          ctx.beginPath();
          ctx.moveTo(pX - pW * 0.6 - g.speed * 12, lineY);
          ctx.lineTo(pX - pW * 0.32, lineY);
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
      ctx.fillText(`MOON CHEESE: ${g.moonCheese}`, 20, 60);
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
      
      // Active Power-ups display
      let powerupX = 130;
      const now = Date.now();
      Object.entries(g.activePowerups).forEach(([type, data]) => {
        if (data && now < data.endTime) {
          const config = POWERUP_TYPES[type];
          const remaining = Math.ceil((data.endTime - now) / 1000);
          
          // Power-up icon background
          ctx.fillStyle = `${config.color}40`;
          ctx.beginPath();
          ctx.roundRect(powerupX, 15, 65, 30, 5);
          ctx.fill();
          ctx.strokeStyle = config.color;
          ctx.lineWidth = 2;
          ctx.stroke();
          
          // Icon and timer
          ctx.font = '16px Arial';
          ctx.textAlign = 'left';
          ctx.fillStyle = config.color;
          ctx.fillText(config.icon, powerupX + 5, 37);
          ctx.font = 'bold 12px monospace';
          ctx.fillStyle = '#FFF';
          ctx.fillText(`${remaining}s`, powerupX + 28, 35);
          
          powerupX += 72;
        }
      });
      
      // Shield visual effect around player
      if (g.activePowerups.shield && now < g.activePowerups.shield.endTime) {
        const shieldPulse = Math.sin(g.frame * 0.15) * 0.3 + 0.7;
        ctx.strokeStyle = `rgba(0, 255, 255, ${shieldPulse * 0.6})`;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(playerX, playerY + playerH / 2, 55, 0, Math.PI * 2);
        ctx.stroke();
        
        ctx.strokeStyle = `rgba(0, 255, 255, ${shieldPulse * 0.3})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(playerX, playerY + playerH / 2, 65, 0, Math.PI * 2);
        ctx.stroke();
      }
      
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

      // Controls hint (detect mobile)
      ctx.fillStyle = 'rgba(255,255,255,0.4)';
      ctx.font = '11px sans-serif';
      const isMobile = 'ontouchstart' in window;
      if (isMobile) {
        ctx.fillText('Swipe ← → to change lanes  |  Swipe ↑ or Tap center to jump', W / 2, H - 35);
      } else {
        ctx.fillText('← A/D → switch lanes  |  SPACE jump', W / 2, H - 35);
      }

      animRef.current = requestAnimationFrame(loop);
    };
    
    // 3D mode: kick the embedded scene instead of the 2D loop.
    scene3DRef.current?.reset();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highScore, totalMoonCheese, playerName, currentSkin, currentSkinId]);

  // ─────────────── 3D scene callbacks ───────────────
  const handle3DScoreTick = useCallback(({ score: liveScore, coins }) => {
    setScore(liveScore);
    setMoonCheese(coins);
  }, []);

  const handle3DDeath = useCallback(({ score: finalScore, coins }) => {
    setGameState("over");
    setScore(finalScore);
    setMoonCheese(coins);
    const newTotal = totalMoonCheese + coins;
    setTotalMoonCheese(newTotal);
    localStorage.setItem("bullpugMoonCheese", String(newTotal));
    if (finalScore > highScore) {
      setHighScore(finalScore);
      localStorage.setItem("bullpugHighScore", String(finalScore));
      winFeedback();
      playSoundIfEnabled('newHighScore');
    } else {
      playSoundIfEnabled('gameover');
    }
    submitScore(finalScore, coins);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highScore, totalMoonCheese, playerName]);


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

  // Touch controls with swipe support
  const touchStartRef = useRef({ x: 0, y: 0, time: 0 });
  
  const handleTouchStart = (e) => {
    if (gameState !== "playing") {
      startGame();
      return;
    }
    
    const touch = e.touches[0];
    const rect = canvasRef.current.getBoundingClientRect();
    touchStartRef.current = {
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top,
      time: Date.now()
    };
  };
  
  const handleTouchMove = (e) => {
    if (gameState !== "playing") return;
    e.preventDefault();
  };
  
  const handleTouchEnd = (e) => {
    if (gameState !== "playing") return;
    
    const touch = e.changedTouches[0];
    const rect = canvasRef.current.getBoundingClientRect();
    const endX = touch.clientX - rect.left;
    const endY = touch.clientY - rect.top;
    
    const deltaX = endX - touchStartRef.current.x;
    const deltaY = endY - touchStartRef.current.y;
    const deltaTime = Date.now() - touchStartRef.current.time;
    
    const minSwipeDistance = 30;
    const maxSwipeTime = 500;
    
    if (deltaTime < maxSwipeTime) {
      // Swipe detection
      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
        // Horizontal swipe - change lane
        if (deltaX > 0) {
          keysRef.current.right = true;
          setTimeout(() => keysRef.current.right = false, 100);
        } else {
          keysRef.current.left = true;
          setTimeout(() => keysRef.current.left = false, 100);
        }
      } else if (deltaY < -minSwipeDistance) {
        // Swipe up - jump
        keysRef.current.jump = true;
        setTimeout(() => keysRef.current.jump = false, 100);
      } else if (Math.abs(deltaX) < 15 && Math.abs(deltaY) < 15) {
        // Tap - also jump (or use position for lane change)
        const third = rect.width / 3;
        if (touchStartRef.current.x < third) {
          keysRef.current.left = true;
          setTimeout(() => keysRef.current.left = false, 100);
        } else if (touchStartRef.current.x > third * 2) {
          keysRef.current.right = true;
          setTimeout(() => keysRef.current.right = false, 100);
        } else {
          keysRef.current.jump = true;
          setTimeout(() => keysRef.current.jump = false, 100);
        }
      }
    }
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
            <button onClick={toggleMusic} data-testid="game-music-toggle"
              className={`p-2 rounded-full border transition-all ${musicOn ? 'bg-[#D946EF]/20 border-[#D946EF]/40 text-[#D946EF]' : 'bg-white/5 border-white/10 text-slate-400 hover:text-white'}`}
              title={musicOn ? "Music On" : "Music Off"}>
              {musicOn ? <Music size={18} /> : <Music2 size={18} />}
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
                    <Clock className="w-3 h-3 mr-1" /> Leaderboard resets in {leaderboardMeta.days_until_reset}d
                  </Badge>
                </div>
              </div>

              <div className="relative mx-auto" style={{ maxWidth: W }}>
                {/* 3D Cosmic Runner scene (replaces the legacy 2D canvas) */}
                <div
                  data-testid="game-canvas"
                  className="w-full rounded-xl border-2 border-[#D946EF]/30 cursor-pointer bg-[#000008] overflow-hidden"
                  style={{ aspectRatio: `${W} / ${H}`, maxWidth: W }}
                >
                  <CosmicRunner3DScene
                    ref={scene3DRef}
                    playing={gameState === "playing"}
                    onScoreTick={handle3DScoreTick}
                    onDeath={handle3DDeath}
                  />
                </div>
                {/* Hidden 2D canvas kept mounted only for legacy ref compatibility */}
                <canvas ref={canvasRef} width={W} height={H} className="hidden" aria-hidden="true" />

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
                      <span className="text-[#FFD700] font-bold">+{moonCheese} Moon Cheese</span>
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
                    <p className="text-xs text-slate-500">Moon Cheese</p>
                    <p className="text-lg font-bold text-[#FFD700]">{gameState === 'playing' ? moonCheese : totalMoonCheese}</p>
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
          <div className="lg:col-span-1 space-y-4">
            {/* Jackpot Display */}
            <JackpotDisplay />
            
            {/* Game Achievements */}
            <div className="glass-card rounded-2xl p-4">
              <GameAchievements 
                currentScore={score}
                totalMoonCheese={totalMoonCheese}
                currentStage={currentStage}
              />
            </div>
            
            {/* Enhanced Leaderboard Panel */}
            <LeaderboardPanel 
              leaderboard={leaderboard}
              playerName={playerName}
              onRefresh={fetchLeaderboard}
            />
          </div>
        </div>
        
        {/* Game Guide Section */}
        <div className="mt-8 max-w-4xl mx-auto">
          <div className="glass-card rounded-2xl p-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span className="text-[#00FFA3]">📖</span> GAME GUIDE
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Collectibles */}
              <div>
                <h4 className="text-sm font-bold text-[#FFD700] mb-3 flex items-center gap-2">
                  <span>✨</span> COLLECTIBLES
                </h4>
                <div className="space-y-3">
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">🥮</span>
                    <div>
                      <p className="text-sm font-semibold text-white">Moon Cheese</p>
                      <p className="text-xs text-slate-400">Collect for +25 points. The cosmic currency of the Bullpug universe!</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Power-ups */}
              <div>
                <h4 className="text-sm font-bold text-[#D946EF] mb-3 flex items-center gap-2">
                  <span>⚡</span> POWER-UPS
                </h4>
                <div className="space-y-3">
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">🛡️</span>
                    <div>
                      <p className="text-sm font-semibold text-cyan-400">Guardian Shield</p>
                      <p className="text-xs text-slate-400">Protects from one obstacle hit. 10 sec duration.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">🧲</span>
                    <div>
                      <p className="text-sm font-semibold text-yellow-400">Moon Cheese Magnet</p>
                      <p className="text-xs text-slate-400">Attracts moon cheese from all lanes. 10 sec duration.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">⭐</span>
                    <div>
                      <p className="text-sm font-semibold text-fuchsia-400">Star Power</p>
                      <p className="text-xs text-slate-400">Doubles points from moon cheese. 10 sec duration.</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Obstacles */}
              <div>
                <h4 className="text-sm font-bold text-[#FF6B35] mb-3 flex items-center gap-2">
                  <span>⚠️</span> OBSTACLES
                </h4>
                <div className="space-y-3">
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">☄️</span>
                    <div>
                      <p className="text-sm font-semibold text-orange-400">Meteor</p>
                      <p className="text-xs text-slate-400">Fiery space rock. Jump or dodge!</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">🪨</span>
                    <div>
                      <p className="text-sm font-semibold text-slate-400">Space Debris</p>
                      <p className="text-xs text-slate-400">Floating wreckage. Appears in Stage 2+.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">🕳️</span>
                    <div>
                      <p className="text-sm font-semibold text-purple-400">Black Hole</p>
                      <p className="text-xs text-slate-400">Dangerous gravity well. Stage 3+.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">🛰️</span>
                    <div>
                      <p className="text-sm font-semibold text-blue-400">Satellite</p>
                      <p className="text-xs text-slate-400">Can be flying! Stage 4+.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                    <span className="text-2xl">🛸</span>
                    <div>
                      <p className="text-sm font-semibold text-teal-400">Alien Ship</p>
                      <p className="text-xs text-slate-400">UFO with beam. Always flying! Stage 5.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Controls */}
            <div className="mt-6 pt-4 border-t border-white/10">
              <h4 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                <span>🎮</span> CONTROLS
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 rounded-lg bg-white/5">
                  <div className="text-lg font-mono text-[#00FFA3]">A / ←</div>
                  <div className="text-xs text-slate-400">Move Left</div>
                </div>
                <div className="text-center p-3 rounded-lg bg-white/5">
                  <div className="text-lg font-mono text-[#00FFA3]">D / →</div>
                  <div className="text-xs text-slate-400">Move Right</div>
                </div>
                <div className="text-center p-3 rounded-lg bg-white/5">
                  <div className="text-lg font-mono text-[#00FFA3]">SPACE / ↑</div>
                  <div className="text-xs text-slate-400">Jump</div>
                </div>
                <div className="text-center p-3 rounded-lg bg-white/5">
                  <div className="text-lg text-[#00FFA3]">📱 Swipe</div>
                  <div className="text-xs text-slate-400">Mobile Controls</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
