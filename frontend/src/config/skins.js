// Skin configuration for Cosmic Runner game
// Each skin applies a color tint overlay to the base character sprite

const BULLPUG_DEFAULT_IMG = "/images/bullpug_default.png";

export const SKINS = [
  {
    id: "default",
    name: "Guardian",
    description: "The original Bullpug Guardian - protector of the cosmos",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 0,
    price: 0,
    rarity: "common",
    color: "#00FFA3",
    glowIntensity: 0.3
  },
  {
    id: "ethereal",
    name: "Ethereal",
    description: "Mythic cosmic guardian - Unlocked by collecting all skins",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 10,
    price: 0,
    rarity: "mythic",
    color: "#E8D5FF",
    glowIntensity: 0.8,
    achievement: true,
    unlockRequirement: "Own all 10 purchasable skins"
  },
  {
    id: "diamond",
    name: "Diamond",
    description: "Crystal-clear perfection with maximum sparkle",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 5,
    price: 0.05,
    rarity: "legendary",
    color: "#00FFFF",
    glowIntensity: 0.7
  },
  {
    id: "gold",
    name: "Gold",
    description: "Pure golden glory for the champions",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 5,
    price: 0.05,
    rarity: "legendary",
    color: "#FFD700",
    glowIntensity: 0.6
  },
  {
    id: "silver",
    name: "Silver",
    description: "Sleek metallic sheen of the moon",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 4,
    price: 0.04,
    rarity: "epic",
    color: "#C0C0C0",
    glowIntensity: 0.5
  },
  {
    id: "heatmap",
    name: "Heatmap",
    description: "Thermal vision powered cosmic energy",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#FF6B35",
    glowIntensity: 0.5
  },
  {
    id: "radioactive",
    name: "Radioactive",
    description: "Glowing with nuclear power",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#7FFF00",
    glowIntensity: 0.6
  },
  {
    id: "zombie",
    name: "Zombie",
    description: "Risen from the crypto dead",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#556B2F",
    glowIntensity: 0.4
  },
  {
    id: "water",
    name: "Aqua",
    description: "Flowing with cosmic aquatic grace",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 2,
    price: 0.02,
    rarity: "uncommon",
    color: "#00CED1",
    glowIntensity: 0.45
  },
  {
    id: "fire",
    name: "Inferno",
    description: "Blazing with stellar flames",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 2,
    price: 0.02,
    rarity: "uncommon",
    color: "#FF4500",
    glowIntensity: 0.55
  },
  {
    id: "robot",
    name: "Cyber",
    description: "Mechanical precision engineering",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 1,
    price: 0.01,
    rarity: "common",
    color: "#B87333",
    glowIntensity: 0.35
  },
  {
    id: "skeletal",
    name: "Phantom",
    description: "Ghostly speed demon of the void",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 1,
    price: 0.01,
    rarity: "common",
    color: "#F5F5DC",
    glowIntensity: 0.4
  }
];

export const RARITY_COLORS = {
  common: { bg: "bg-slate-500/10", border: "border-slate-500/30", text: "text-slate-400", glow: "rgba(100,116,139,0.3)" },
  uncommon: { bg: "bg-green-500/10", border: "border-green-500/30", text: "text-green-400", glow: "rgba(34,197,94,0.3)" },
  rare: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", glow: "rgba(59,130,246,0.3)" },
  epic: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400", glow: "rgba(168,85,247,0.4)" },
  legendary: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", glow: "rgba(245,158,11,0.5)" },
  mythic: { bg: "bg-pink-500/10", border: "border-pink-500/30", text: "text-pink-300", glow: "rgba(236,72,153,0.6)" }
};

// List of purchasable skin IDs (excludes default and achievement skins)
export const PURCHASABLE_SKIN_IDS = SKINS.filter(s => s.price > 0 && !s.achievement).map(s => s.id);

export const getSkinById = (id) => SKINS.find(s => s.id === id) || SKINS[0];

// Get skin display color with alpha
export const getSkinGlowColor = (id, alpha = 0.4) => {
  const skin = getSkinById(id);
  return skin.color + Math.round(alpha * 255).toString(16).padStart(2, '0');
};
