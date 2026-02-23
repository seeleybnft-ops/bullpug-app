/**
 * Game Constants - All configuration values for the Cosmic Runner game
 */

// Canvas dimensions
export const CANVAS_WIDTH = 800;
export const CANVAS_HEIGHT = 500;
export const W = CANVAS_WIDTH;
export const H = CANVAS_HEIGHT;

// Lane configuration
export const LANE_COUNT = 3;
export const LANE_WIDTH = 100;

// Physics
export const GRAVITY = 0.8;
export const JUMP_FORCE = -16;

// 3D Perspective settings
export const HORIZON_Y = 120;
export const GROUND_Y = 420;
export const VANISHING_X = W / 2;
export const PLAYER_BASE_Y = GROUND_Y - 80;

// Animation frames
export const ANIM_RUN_FRAMES = 8;
export const ANIM_JUMP_FRAMES = 4;

// Power-up types with Bullpug lore
export const POWERUP_TYPES = {
  shield: {
    name: 'Guardian Shield',
    description: 'Cosmic protection from one hit',
    color: '#00FFFF',
    glowColor: 'rgba(0, 255, 255, 0.6)',
    icon: '🛡️',
    duration: 10000
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

export const POWERUP_SPAWN_INTERVAL = 720; // Every 12 seconds at 60fps

// Stage-specific background themes
export const STAGE_BACKGROUNDS = {
  1: { name: 'Deep Space', hue: 240, nebulaDensity: 3, starBrightness: 0.7 },
  2: { name: 'Blue Nebula', hue: 200, nebulaDensity: 5, starBrightness: 0.8 },
  3: { name: 'Purple Galaxy', hue: 280, nebulaDensity: 6, starBrightness: 0.9 },
  4: { name: 'Cosmic Fire', hue: 20, nebulaDensity: 7, starBrightness: 1.0 },
  5: { name: 'Multiverse', hue: -1, nebulaDensity: 8, starBrightness: 1.0 } // -1 = rainbow
};

// Obstacle stages - score thresholds
export const OBSTACLE_STAGES = {
  1: { score: 0, types: ['meteor'] },
  2: { score: 250, types: ['meteor', 'debris'] },
  3: { score: 500, types: ['meteor', 'debris', 'blackhole'] },
  4: { score: 1000, types: ['meteor', 'debris', 'blackhole', 'satellite'] },
  5: { score: 1500, types: ['meteor', 'debris', 'blackhole', 'satellite', 'alienship'] }
};

// Obstacle types with visual properties
export const OBSTACLE_TYPES = {
  meteor: {
    name: 'Meteor',
    emoji: '☄️',
    baseSize: 50,
    sizeVariance: 20,
    canFly: false
  },
  debris: {
    name: 'Space Debris',
    emoji: '🪨',
    baseSize: 35,
    sizeVariance: 20,
    canFly: false
  },
  blackhole: {
    name: 'Black Hole',
    emoji: '🕳️',
    baseSize: 65,
    sizeVariance: 0,
    canFly: false
  },
  satellite: {
    name: 'Satellite',
    emoji: '🛰️',
    baseSize: 58,
    sizeVariance: 0,
    canFly: true,
    flyChance: 0.5
  },
  alienship: {
    name: 'Alien Ship',
    emoji: '🛸',
    baseSize: 70,
    sizeVariance: 0,
    canFly: true,
    flyChance: 1.0
  }
};

// Game speed configuration
export const SPEED_CONFIG = {
  minSpeed: 1.25,
  maxSpeed: 4.8,
  rampUpTime: 120, // seconds to reach max speed
};

// Spawn rates (in frames at 60fps)
export const SPAWN_RATES = {
  baseObstacleRate: 70,
  minObstacleRate: 25,
  collectibleRate: 60,
  powerupRate: 720
};

// Points configuration
export const POINTS = {
  moonCheeseValue: 25,
  frameScoreDivisor: 6, // Score = frame / this
};

// Collectible (Moon Cheese) visual settings
export const MOON_CHEESE_VISUALS = {
  baseRadius: 22,
  glowMultiplier: 2.8,
  sparkleCount: 8,
  rayCount: 8
};

// Player hitbox settings
export const PLAYER_HITBOX = {
  width: 50,
  height: 70,
  collisionPadding: 15
};
