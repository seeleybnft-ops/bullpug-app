// Skin configuration for Speed Run game
export const SKINS = [
  {
    id: "default",
    name: "Guardian",
    description: "The original Bullpug Guardian",
    image: "https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png",
    bonusPercent: 0,
    price: 0,
    rarity: "common",
    color: "#00FFA3"
  },
  {
    id: "ethereal",
    name: "Ethereal",
    description: "Mythic cosmic guardian - Unlocked by collecting all skins",
    image: "https://customer-assets.emergentagent.com/job_b50eda93-3e28-4d4f-b3a4-f9545d162331/artifacts/nyk7s5uc_Ethereal.jpg",
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
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/h65ox4in_Diamond.jpg",
    bonusPercent: 5,
    price: 0.05,
    rarity: "legendary",
    color: "#E0F7FF"
  },
  {
    id: "gold",
    name: "Gold",
    description: "Pure golden glory for the champions",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/2c0zhxiz_Gold.jpg",
    bonusPercent: 5,
    price: 0.05,
    rarity: "legendary",
    color: "#FFD700"
  },
  {
    id: "silver",
    name: "Silver",
    description: "Sleek metallic sheen of the moon",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/2y3uyf7a_Silver.jpg",
    bonusPercent: 4,
    price: 0.04,
    rarity: "epic",
    color: "#C0C0C0"
  },
  {
    id: "heatmap",
    name: "Heatmap",
    description: "Thermal vision powered cosmic energy",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/3125yslg_Heatmap.jpg",
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#FF6B35"
  },
  {
    id: "radioactive",
    name: "Radioactive",
    description: "Glowing with nuclear power",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/0w5zprcs_Radioactive.jpg",
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#7FFF00"
  },
  {
    id: "zombie",
    name: "Zombie",
    description: "Risen from the crypto dead",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/jjtj6iwm_Zombie.jpg",
    bonusPercent: 3,
    price: 0.03,
    rarity: "rare",
    color: "#556B2F"
  },
  {
    id: "water",
    name: "Water",
    description: "Flowing with aquatic grace",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/x9l0yezz_Water.jpg",
    bonusPercent: 2,
    price: 0.02,
    rarity: "uncommon",
    color: "#00CED1"
  },
  {
    id: "fire",
    name: "Fire",
    description: "Blazing with infernal flames",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/mrdaks1w_Fire.jpg",
    bonusPercent: 2,
    price: 0.02,
    rarity: "uncommon",
    color: "#FF4500"
  },
  {
    id: "robot",
    name: "Robot",
    description: "Mechanical precision engineering",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/ek1n7jog_Robot.jpg",
    bonusPercent: 1,
    price: 0.01,
    rarity: "common",
    color: "#B87333"
  },
  {
    id: "skeletal",
    name: "Skeletal",
    description: "Bare bones speed demon",
    image: "https://customer-assets.emergentagent.com/job_9324cc3c-b03f-4596-b85c-b20d257c9660/artifacts/tip9zh8u_Skeletal.jpg",
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
