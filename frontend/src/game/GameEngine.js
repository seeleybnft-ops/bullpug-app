/**
 * Game Engine - Core game logic, physics, spawning, and collision detection
 */

import {
  W, H, LANE_COUNT, GRAVITY, JUMP_FORCE, HORIZON_Y, GROUND_Y,
  VANISHING_X, PLAYER_BASE_Y, POWERUP_TYPES, OBSTACLE_STAGES,
  POWERUP_SPAWN_INTERVAL, SPEED_CONFIG, SPAWN_RATES, POINTS
} from './constants';

/**
 * Get lane X position based on 3D perspective depth
 * @param {number} lane - Lane index (0, 1, 2)
 * @param {number} depth - Depth from 0 (horizon) to 1 (player level)
 */
export function getLaneX(lane, depth) {
  const LANE_WIDTH = 100;
  const spreadAtBottom = LANE_WIDTH * 1.8;
  const spreadAtHorizon = 20;
  const spread = spreadAtHorizon + (spreadAtBottom - spreadAtHorizon) * depth;
  return VANISHING_X + (lane - 1) * spread;
}

/**
 * Get Y position based on depth
 */
export function getDepthY(depth) {
  return HORIZON_Y + (GROUND_Y - HORIZON_Y) * depth;
}

/**
 * Get scale based on depth
 */
export function getDepthScale(depth) {
  return 0.15 + depth * 0.85;
}

/**
 * Get current stage based on score
 */
export function getCurrentStage(score) {
  for (let i = 5; i >= 1; i--) {
    if (score >= OBSTACLE_STAGES[i].score) return i;
  }
  return 1;
}

/**
 * Check if a position is clear of other objects
 */
export function isPositionClear(game, lane, depth, minSeparation = 0.15) {
  // Check obstacles
  for (const o of game.obstacles) {
    if (o.lane === lane && Math.abs(o.depth - depth) < minSeparation) {
      return false;
    }
  }
  // Check collectibles
  for (const c of game.collectibles) {
    if (c.lane === lane && Math.abs(c.depth - depth) < minSeparation) {
      return false;
    }
  }
  // Check power-ups
  for (const p of game.powerups) {
    if (p.lane === lane && Math.abs(p.depth - depth) < minSeparation) {
      return false;
    }
  }
  return true;
}

/**
 * Initialize a new game state
 */
export function createInitialGameState(skinBonus = 0, skinColor = '#00FFA3') {
  return {
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
    activePowerups: {
      shield: null,
      magnet: null,
      doubleScore: null
    },
    lastPowerupSpawn: 0,
    // Background elements
    stars: Array.from({ length: 200 }, () => ({
      x: Math.random() * W,
      y: Math.random() * HORIZON_Y * 1.5,
      z: Math.random(),
      size: Math.random() * 2.5 + 0.5,
      twinkle: Math.random() * Math.PI * 2,
      speed: 0.2 + Math.random() * 0.5
    })),
    nebulas: Array.from({ length: 12 }, () => ({
      x: Math.random() * W * 1.5,
      y: Math.random() * HORIZON_Y,
      z: Math.random() * 0.8 + 0.2,
      size: 80 + Math.random() * 150,
      hue: Math.random() * 360,
      alpha: 0.06 + Math.random() * 0.1,
      speed: 0.3 + Math.random() * 0.5
    })),
    cosmicObjects: Array.from({ length: 5 }, () => ({
      x: Math.random() * W,
      y: 20 + Math.random() * (HORIZON_Y - 40),
      size: 15 + Math.random() * 40,
      type: Math.random() > 0.5 ? 'galaxy' : 'planet',
      hue: Math.random() * 360,
      rotation: Math.random() * Math.PI * 2,
      speed: 0.1 + Math.random() * 0.2
    })),
    shootingStars: [],
    shootingStarTimer: 0,
    speedLines: Array.from({ length: 30 }, () => ({
      angle: (Math.random() - 0.5) * Math.PI * 0.6,
      length: 20 + Math.random() * 80,
      speed: 2 + Math.random() * 4,
      distance: Math.random() * 200,
      alpha: 0.1 + Math.random() * 0.3
    })),
    backgroundHue: 240,
    frame: 0,
    speed: SPEED_CONFIG.minSpeed,
    startTime: Date.now(),
    score: 0,
    mooncakes: 0,
    running: true,
    stage: 1,
    trackOffset: 0,
    skinBonus,
    skinColor
  };
}

/**
 * Spawn a new obstacle
 */
export function spawnObstacle(game) {
  const stage = getCurrentStage(game.score);
  const types = OBSTACLE_STAGES[stage].types;
  const type = types[Math.floor(Math.random() * types.length)];
  
  let lane = Math.floor(Math.random() * LANE_COUNT);
  for (let attempts = 0; attempts < 5; attempts++) {
    if (isPositionClear(game, lane, 0, 0.18)) break;
    lane = Math.floor(Math.random() * LANE_COUNT);
  }
  
  let size = 40;
  let isFlying = false;
  
  switch (type) {
    case 'meteor': size = 50 + Math.random() * 20; break;
    case 'debris': size = 35 + Math.random() * 20; break;
    case 'blackhole': size = 65; break;
    case 'satellite': size = 58; isFlying = Math.random() > 0.5; break;
    case 'alienship': size = 70; isFlying = true; break;
    default: break;
  }
  
  return {
    type, lane,
    depth: 0,
    size,
    isFlying,
    flyOffset: isFlying ? 40 + Math.random() * 30 : 0,
    rotation: Math.random() * Math.PI * 2,
    rotSpeed: (Math.random() - 0.5) * 0.15,
    pulse: Math.random() * Math.PI * 2
  };
}

/**
 * Spawn a new collectible (mooncake)
 */
export function spawnCollectible(game) {
  let lane = Math.floor(Math.random() * LANE_COUNT);
  for (let attempts = 0; attempts < 5; attempts++) {
    if (isPositionClear(game, lane, 0, 0.18)) break;
    lane = Math.floor(Math.random() * LANE_COUNT);
  }
  
  return {
    lane,
    depth: 0,
    collected: false,
    floatOffset: 30 + Math.random() * 20,
    glow: Math.random() * Math.PI * 2,
    sparkleParticles: []
  };
}

/**
 * Spawn a new power-up
 */
export function spawnPowerup(game) {
  const types = Object.keys(POWERUP_TYPES);
  const type = types[Math.floor(Math.random() * types.length)];
  
  let lane = Math.floor(Math.random() * LANE_COUNT);
  for (let attempts = 0; attempts < 5; attempts++) {
    if (isPositionClear(game, lane, 0, 0.25)) break;
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
}

/**
 * Check collision between player and an object
 */
export function checkCollision(player, obj, laneX, objY, objSize, isFlying = false) {
  const playerX = getLaneX(player.lane, 1);
  const playerY = player.y;
  
  // Player hitbox
  const playerHalfWidth = 25;
  const playerHeight = 70;
  
  // Object hitbox
  const objHalfSize = objSize * 0.4; // Slightly forgiving hitbox
  
  // Horizontal collision
  const horizontalOverlap = Math.abs(playerX - laneX) < (playerHalfWidth + objHalfSize);
  
  // Vertical collision - account for flying objects
  const objTop = isFlying ? objY - obj.flyOffset - objHalfSize : objY - objHalfSize;
  const objBottom = isFlying ? objY - obj.flyOffset + objHalfSize : objY + objHalfSize;
  const playerTop = playerY - playerHeight;
  const playerBottom = playerY;
  
  const verticalOverlap = playerBottom > objTop && playerTop < objBottom;
  
  return horizontalOverlap && verticalOverlap;
}

/**
 * Update game speed based on elapsed time
 */
export function updateGameSpeed(game) {
  const elapsedSeconds = (Date.now() - game.startTime) / 1000;
  const speedProgress = Math.min(elapsedSeconds / SPEED_CONFIG.rampUpTime, 1);
  game.speed = SPEED_CONFIG.minSpeed + (SPEED_CONFIG.maxSpeed - SPEED_CONFIG.minSpeed) * speedProgress;
}

/**
 * Calculate spawn rate based on current speed
 */
export function getObstacleSpawnRate(speed) {
  return Math.max(
    SPAWN_RATES.minObstacleRate,
    Math.floor(SPAWN_RATES.baseObstacleRate - speed * 3)
  );
}
