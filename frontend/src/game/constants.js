// Game constants for Cosmic Runner
// Extracted from SpeedRunGame.js for better modularity

// Canvas dimensions
export const CANVAS_WIDTH = 800;
export const CANVAS_HEIGHT = 500;
export const LANE_COUNT = 3;
export const LANE_WIDTH = 100;

// Physics
export const GRAVITY = 0.8;
export const JUMP_FORCE = -16;

// 3D Perspective settings
export const HORIZON_Y = 120;
export const GROUND_Y = 420;
export const VANISHING_X = CANVAS_WIDTH / 2;
export const PLAYER_BASE_Y = GROUND_Y - 80;

// Animation frames
export const ANIM_RUN_FRAMES = 8;
export const ANIM_JUMP_FRAMES = 4;

// Power-up configuration - Bullpug Lore themed
export const POWERUP_TYPES = {
  shield: {
    name: 'Guardian Shield',
    description: 'Cosmic protection from one hit',
    color: '#00FFFF',
    glowColor: 'rgba(0, 255, 255, 0.6)',
    icon: '🛡️',
    duration: 10000, // 10 seconds
  },
  magnet: {
    name: 'Mooncake Magnet',
    description: 'Attracts mooncakes from all lanes',
    color: '#FFD700',
    glowColor: 'rgba(255, 215, 0, 0.6)',
    icon: '🧲',
    duration: 10000,
  },
  doubleScore: {
    name: 'Star Power',
    description: 'Double points from cosmic energy',
    color: '#FF00FF',
    glowColor: 'rgba(255, 0, 255, 0.6)',
    icon: '⭐',
    duration: 10000,
  },
};

export const POWERUP_SPAWN_INTERVAL = 720; // Every 12 seconds at 60fps

// Stage-specific background themes
export const STAGE_BACKGROUNDS = {
  1: { name: 'Deep Space', hue: 240, nebulaDensity: 3, starBrightness: 0.7 },
  2: { name: 'Blue Nebula', hue: 200, nebulaDensity: 5, starBrightness: 0.8 },
  3: { name: 'Purple Galaxy', hue: 280, nebulaDensity: 6, starBrightness: 0.9 },
  4: { name: 'Cosmic Fire', hue: 20, nebulaDensity: 7, starBrightness: 1.0 },
  5: { name: 'Multiverse', hue: -1, nebulaDensity: 8, starBrightness: 1.0 }, // -1 = rainbow
};

// Obstacle stages - score thresholds
export const OBSTACLE_STAGES = {
  1: { score: 0, types: ['meteor'] },
  2: { score: 250, types: ['meteor', 'debris'] },
  3: { score: 500, types: ['meteor', 'debris', 'blackhole'] },
  4: { score: 1000, types: ['meteor', 'debris', 'blackhole', 'satellite'] },
  5: { score: 1500, types: ['meteor', 'debris', 'blackhole', 'satellite', 'alienship'] },
};

// Obstacle definitions for the guide
export const OBSTACLE_GUIDE = [
  { type: 'meteor', emoji: '☄️', name: 'Meteor', description: 'Fiery space rock. Jump or dodge!', color: 'text-orange-400', stage: 1 },
  { type: 'debris', emoji: '🪨', name: 'Space Debris', description: 'Floating wreckage. Appears in Stage 2+.', color: 'text-slate-400', stage: 2 },
  { type: 'blackhole', emoji: '🕳️', name: 'Black Hole', description: 'Dangerous gravity well. Stage 3+.', color: 'text-purple-400', stage: 3 },
  { type: 'satellite', emoji: '🛰️', name: 'Satellite', description: 'Can be flying! Stage 4+.', color: 'text-blue-400', stage: 4 },
  { type: 'alienship', emoji: '🛸', name: 'Alien Ship', description: 'UFO with beam. Always flying! Stage 5.', color: 'text-teal-400', stage: 5 },
];

// Collectible info for the guide
export const COLLECTIBLE_GUIDE = {
  mooncake: {
    emoji: '🥮',
    name: 'Mooncake',
    description: 'Collect for +25 points. The cosmic currency of the Bullpug universe!',
  },
};

// Power-up info for the guide
export const POWERUP_GUIDE = [
  { type: 'shield', emoji: '🛡️', name: 'Guardian Shield', description: 'Protects from one obstacle hit. 10 sec duration.', color: 'text-cyan-400' },
  { type: 'magnet', emoji: '🧲', name: 'Mooncake Magnet', description: 'Attracts mooncakes from all lanes. 10 sec duration.', color: 'text-yellow-400' },
  { type: 'doubleScore', emoji: '⭐', name: 'Star Power', description: 'Doubles points from mooncakes. 10 sec duration.', color: 'text-fuchsia-400' },
];
