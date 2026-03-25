import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Sparkles, Lock, Eye } from "lucide-react";

const GALLERY = [
  "https://images.unsplash.com/photo-1511862190988-d7dd089c60e0?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85&w=600",
  "https://images.pexels.com/photos/1884500/pexels-photo-1884500.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
  "https://images.unsplash.com/photo-1549665611-985efeea9f39?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85&w=600",
  "https://images.unsplash.com/photo-1629755725339-efd38b8253bb?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85&w=600",
  "https://images.unsplash.com/photo-1629757257537-62cedbcffbe6?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85&w=600",
  "https://images.pexels.com/photos/3609068/pexels-photo-3609068.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
];

const RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"];
const RARITY_COLORS = { Common: "#94a3b8", Uncommon: "#00FFA3", Rare: "#00C2FF", Epic: "#D946EF", Legendary: "#F5D300", Mythic: "#FF3B30" };

const NFTS = GALLERY.map((img, i) => ({
  id: i + 1,
  name: `Bullpug Guardian #${String(i + 1).padStart(4, "0")}`,
  image: img,
  rarity: RARITIES[i % RARITIES.length],
  price: [0.5, 1, 2, 5, 10, 25][i % 6],
  minted: i < 4,
}));

export default function NFTGallery() {
  const [selected, setSelected] = useState(null);

  const mint = (nft) => {
    toast.success(`Minting ${nft.name} (simulated) - Coming Q4 2026!`);
  };

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-6xl mx-auto px-6 md:px-12">
        <div className="text-center mb-10">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase mb-3" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            NFT <span className="text-[#D946EF]">Gallery</span>
          </h1>
          <p className="text-slate-500 text-sm">Guardian avatars collection - Coming Q4 2026</p>
          <Badge className="mt-3 bg-[#D946EF]/10 text-[#D946EF] border-[#D946EF]/30 text-[10px]">Preview Collection</Badge>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {NFTS.map(nft => (
            <div key={nft.id}
              className="glass-card rounded-2xl overflow-hidden group hover:-translate-y-1 transition-all duration-300 cursor-pointer"
              onClick={() => setSelected(nft)}
              data-testid={`nft-${nft.id}`}>
              <div className="relative h-48 overflow-hidden">
                <img src={nft.image} alt={nft.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                <div className="absolute inset-0 bg-gradient-to-t from-[#05050A] via-transparent to-transparent" />
                <Badge className="absolute top-2 right-2 text-[10px]"
                  style={{ background: `${RARITY_COLORS[nft.rarity]}20`, color: RARITY_COLORS[nft.rarity], borderColor: `${RARITY_COLORS[nft.rarity]}40` }}>
                  {nft.rarity}
                </Badge>
                {!nft.minted && (
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <Eye className="w-6 h-6 text-white" />
                  </div>
                )}
              </div>
              <div className="p-3">
                <p className="text-xs font-bold truncate" style={{ fontFamily: 'Orbitron, sans-serif' }}>{nft.name}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-slate-500">{nft.price} SOL</span>
                  {nft.minted ? (
                    <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] text-[10px]">Minted</Badge>
                  ) : (
                    <Badge className="bg-white/5 text-slate-400 text-[10px]"><Lock className="w-2 h-2 mr-1" />Locked</Badge>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {selected && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={() => setSelected(null)}>
            <div className="glass-card rounded-2xl p-6 w-full max-w-lg m-4 border border-white/10" onClick={e => e.stopPropagation()}>
              <img src={selected.image} alt={selected.name} className="w-full h-64 object-cover rounded-xl mb-4" />
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-lg" style={{ fontFamily: 'Orbitron, sans-serif' }}>{selected.name}</h3>
                <Badge style={{ background: `${RARITY_COLORS[selected.rarity]}20`, color: RARITY_COLORS[selected.rarity] }}>
                  {selected.rarity}
                </Badge>
              </div>
              <p className="text-sm text-slate-400 mb-4">
                This Guardian NFT grants exclusive access to Bullpug lore chapters, game boosts, and governance voting power.
                Rarity determines the level of benefits.
              </p>
              <div className="flex items-center justify-between">
                <span className="font-bold" style={{ fontFamily: 'Orbitron, sans-serif' }}>{selected.price} SOL</span>
                <div className="flex gap-2">
                  <Button onClick={() => setSelected(null)} variant="outline" className="border-white/10 rounded-xl">Close</Button>
                  <Button onClick={() => { mint(selected); setSelected(null); }} data-testid="mint-btn"
                    className="bg-[#D946EF] text-white font-bold rounded-xl hover:scale-105 transition-transform">
                    <Sparkles className="w-4 h-4 mr-2" /> Mint NFT
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
