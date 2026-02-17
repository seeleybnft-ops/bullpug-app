import { useState, useEffect } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { PublicKey, Transaction, SystemProgram, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Store, Check, Lock, Sparkles, Zap, Crown, X } from "lucide-react";
import { SKINS, RARITY_COLORS, getSkinById } from "@/config/skins";
import { playSoundIfEnabled, clickFeedback } from "@/utils/sounds";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const STORE_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT";

export default function SkinStore({ isOpen, onClose, onSkinSelect, currentSkinId }) {
  const { publicKey, connected, sendTransaction } = useWallet();
  const { connection } = useConnection();
  const { t } = useTranslation();
  const [ownedSkins, setOwnedSkins] = useState(["default"]);
  const [purchasing, setPurchasing] = useState(null);
  const [selectedSkin, setSelectedSkin] = useState(currentSkinId || "default");

  useEffect(() => {
    if (connected && publicKey) {
      fetchOwnedSkins();
    }
  }, [connected, publicKey]);

  const fetchOwnedSkins = async () => {
    try {
      const { data } = await axios.get(`${API}/skins/owned/${publicKey.toBase58()}`);
      setOwnedSkins(["default", ...data.skins]);
    } catch (e) {
      console.error("Failed to fetch owned skins:", e);
    }
  };

  const purchaseSkin = async (skin) => {
    if (!connected || !publicKey) {
      toast.error("Connect your wallet to purchase");
      return;
    }

    if (ownedSkins.includes(skin.id)) {
      toast.info("You already own this skin!");
      return;
    }

    clickFeedback();
    setPurchasing(skin.id);

    try {
      // Create Solana transaction
      const lamports = Math.round(skin.price * LAMPORTS_PER_SOL);
      const transaction = new Transaction().add(
        SystemProgram.transfer({
          fromPubkey: publicKey,
          toPubkey: new PublicKey(STORE_WALLET),
          lamports
        })
      );

      // Get recent blockhash
      const { blockhash } = await connection.getLatestBlockhash();
      transaction.recentBlockhash = blockhash;
      transaction.feePayer = publicKey;

      // Send transaction
      const signature = await sendTransaction(transaction, connection);
      
      // Wait for confirmation
      await connection.confirmTransaction(signature, "confirmed");

      // Record purchase in backend
      await axios.post(`${API}/skins/purchase`, {
        wallet_address: publicKey.toBase58(),
        skin_id: skin.id,
        tx_signature: signature,
        amount_sol: skin.price
      });

      playSoundIfEnabled("success");
      toast.success(`${skin.name} skin unlocked!`);
      setOwnedSkins([...ownedSkins, skin.id]);
      
    } catch (e) {
      console.error("Purchase failed:", e);
      playSoundIfEnabled("error");
      toast.error(e.message || "Purchase failed");
    }

    setPurchasing(null);
  };

  const selectSkin = (skinId) => {
    if (!ownedSkins.includes(skinId)) return;
    setSelectedSkin(skinId);
    localStorage.setItem("bullpugSkin", skinId);
    onSkinSelect?.(skinId);
    playSoundIfEnabled("click");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-auto mx-4 glass-card rounded-2xl border border-white/10">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-[#0A0A12]/95 backdrop-blur border-b border-white/10 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#D946EF]/10 flex items-center justify-center">
              <Store className="w-5 h-5 text-[#D946EF]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                Skin Store
              </h2>
              <p className="text-xs text-slate-500">Unlock skins with bonus points</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Current Selection */}
        <div className="p-4 border-b border-white/5">
          <div className="flex items-center gap-4">
            <img 
              src={getSkinById(selectedSkin).image} 
              alt={getSkinById(selectedSkin).name}
              className="w-16 h-16 rounded-xl border-2 border-[#00FFA3]/50 object-cover"
            />
            <div>
              <p className="text-xs text-slate-500">Currently Equipped</p>
              <p className="text-lg font-bold text-white">{getSkinById(selectedSkin).name}</p>
              {getSkinById(selectedSkin).bonusPercent > 0 && (
                <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] border-[#00FFA3]/30 text-[10px]">
                  <Zap className="w-3 h-3 mr-1" /> +{getSkinById(selectedSkin).bonusPercent}% Bonus Points
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Skin Grid */}
        <div className="p-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {SKINS.map((skin) => {
              const owned = ownedSkins.includes(skin.id);
              const isSelected = selectedSkin === skin.id;
              const rarity = RARITY_COLORS[skin.rarity];

              return (
                <div
                  key={skin.id}
                  onClick={() => owned && selectSkin(skin.id)}
                  className={`relative rounded-xl border-2 transition-all cursor-pointer overflow-hidden group ${
                    isSelected 
                      ? "border-[#00FFA3] ring-2 ring-[#00FFA3]/30" 
                      : owned 
                        ? "border-white/10 hover:border-white/30" 
                        : "border-white/5 opacity-80"
                  }`}
                  data-testid={`skin-${skin.id}`}
                >
                  {/* Image */}
                  <div className="aspect-square relative">
                    <img 
                      src={skin.image} 
                      alt={skin.name}
                      className="w-full h-full object-cover"
                    />
                    
                    {/* Lock overlay for unowned */}
                    {!owned && (
                      <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                        <Lock className="w-8 h-8 text-slate-400" />
                      </div>
                    )}

                    {/* Selected check */}
                    {isSelected && (
                      <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-[#00FFA3] flex items-center justify-center">
                        <Check className="w-4 h-4 text-black" />
                      </div>
                    )}

                    {/* Rarity badge */}
                    <div className={`absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${rarity.bg} ${rarity.text} ${rarity.border} border`}>
                      {skin.rarity === "legendary" && <Crown className="w-3 h-3 inline mr-1" />}
                      {skin.rarity}
                    </div>
                  </div>

                  {/* Info */}
                  <div className="p-2 bg-black/40">
                    <p className="text-sm font-bold text-white truncate">{skin.name}</p>
                    <div className="flex items-center justify-between mt-1">
                      {skin.bonusPercent > 0 ? (
                        <span className="text-[10px] text-[#00FFA3] flex items-center gap-1">
                          <Sparkles className="w-3 h-3" /> +{skin.bonusPercent}%
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500">Default</span>
                      )}

                      {owned ? (
                        <span className="text-[10px] text-slate-400">Owned</span>
                      ) : (
                        <span className="text-[10px] text-[#D946EF] font-bold">{skin.price} SOL</span>
                      )}
                    </div>
                  </div>

                  {/* Purchase button overlay */}
                  {!owned && connected && (
                    <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <Button
                        onClick={(e) => { e.stopPropagation(); purchaseSkin(skin); }}
                        disabled={purchasing === skin.id}
                        className="bg-[#D946EF] text-white font-bold text-xs px-4 py-2 rounded-lg hover:bg-[#D946EF]/80"
                        data-testid={`buy-${skin.id}`}
                      >
                        {purchasing === skin.id ? "Buying..." : `Buy ${skin.price} SOL`}
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        {!connected && (
          <div className="p-4 border-t border-white/5 text-center">
            <p className="text-sm text-slate-400">Connect your wallet to purchase skins</p>
          </div>
        )}
      </div>
    </div>
  );
}
