// Skin configuration for Speed Run game
// Images hosted on Emergent static CDN to avoid CORS issues
const BULLPUG_DEFAULT_IMG = "https://static.prod-images.emergentagent.com/jobs/b75b6322-24e6-4d16-a4ec-ae3ed31f0fe4/images/698272adccc7c6f29bcfad37f56c6f7059f383d8a3d70720a8582be4499db4a8.png";

export const SKINS = [
  {
    id: "default",
    name: "Guardian",
    description: "The original Bullpug Guardian",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 0,
    price: 0,
    rarity: "common",
    color: "#00FFA3"
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
    color: "#E0F7FF"
  },
  {
    id: "gold",
    name: "Gold",
    description: "Pure golden glory for the champions",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 5,
    price: 0.05,
    rarity: "legendary",
    color: "#FFD700"
  },
  {
    id: "silver",
    name: "Silver",
    description: "Sleek metallic sheen of the moon",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 4,
    price: 0.04,
    rarity: "epic",
    color: "#C0C0C0"
  },
  {
    id: "heatmap",
    name: "Heatmap",
    description: "Thermal vision powered cosmic energy",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#FF6B35"
  },
  {
    id: "radioactive",
    name: "Radioactive",
    description: "Glowing with nuclear power",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#7FFF00"
  },
  {
    id: "zombie",
    name: "Zombie",
    description: "Risen from the crypto dead",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#556B2F"
  },
  {
    id: "water",
    name: "Water",
    description: "Flowing with aquatic grace",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 2,
    price: 0.02,
    rarity: "uncommon",
    color: "#00CED1"
  },
  {
    id: "fire",
    name: "Fire",
    description: "Blazing with infernal flames",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 2,
    price: 0.02,
    rarity: "uncommon",
    color: "#FF4500"
  },
  {
    id: "robot",
    name: "Robot",
    description: "Mechanical precision engineering",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 1,
    price: 0.01,
    rarity: "common",
    color: "#B87333"
  },
  {
    id: "skeletal",
    name: "Skeletal",
    description: "Bare bones speed demon",
    image: BULLPUG_DEFAULT_IMG,
    bonusPercent: 1,
    price: 0.01,
    rarity: "common",
    color: "#F5F5DC"
  }
];

export const RARITY_COLORS = {
  common: { bg: "bg-slate-500/10", border: "border-slate-500/30", text: "text-slate-400" },
  uncommon: { bg: "bg-green-500/10", border: "border-green-500/30", text: "text-green-400" },
  rare: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400" },
  epic: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400" },
  legendary: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400" },
  mythic: { bg: "bg-pink-500/10", border: "border-pink-500/30", text: "text-pink-300" }
};

// List of purchasable skin IDs (excludes default and achievement skins)
export const PURCHASABLE_SKIN_IDS = SKINS.filter(s => s.price > 0 && !s.achievement).map(s => s.id);

export const getSkinById = (id) => SKINS.find(s => s.id === id) || SKINS[0];
