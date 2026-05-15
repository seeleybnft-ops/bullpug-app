import { useState, useEffect } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { PublicKey, Transaction, SystemProgram, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Store, Check, Lock, Sparkles, Zap, Crown, X, Gift, Eye, Send, ArrowRight, User, Star, Trophy } from "lucide-react";
import { SKINS, RARITY_COLORS, getSkinById, PURCHASABLE_SKIN_IDS } from "@/config/skins";
import { playSoundIfEnabled, clickFeedback } from "@/utils/sounds";
import SkinPreview3D from "@/components/SkinPreview3D";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const STORE_WALLET = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT";

export default function SkinStore({ isOpen, onClose, onSkinSelect, currentSkinId }) {
  const { publicKey, connected, sendTransaction } = useWallet();
  const { connection } = useConnection();
  const { t } = useTranslation();
  const [ownedSkins, setOwnedSkins] = useState(["default"]);
  const [purchasing, setPurchasing] = useState(null);
  const [selectedSkin, setSelectedSkin] = useState(currentSkinId || "default");
  const [previewSkin, setPreviewSkin] = useState(null);
  const [giftModal, setGiftModal] = useState({ open: false, skin: null });
  const [giftRecipient, setGiftRecipient] = useState("");
  const [sendingGift, setSendingGift] = useState(false);
  const [giftHistory, setGiftHistory] = useState([]);
  const [achievementStatus, setAchievementStatus] = useState(null);

  useEffect(() => {
    if (connected && publicKey) {
      fetchOwnedSkins();
      fetchGiftHistory();
      fetchAchievementStatus();
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

  const fetchGiftHistory = async () => {
    try {
      const { data } = await axios.get(`${API}/skins/gifts/${publicKey.toBase58()}`);
      setGiftHistory(data.gifts || []);
    } catch (e) {
      console.error("Failed to fetch gift history:", e);
    }
  };

  const fetchAchievementStatus = async () => {
    try {
      const { data } = await axios.get(`${API}/skins/achievement-status/${publicKey.toBase58()}`);
      setAchievementStatus(data.ethereal);
      // If ethereal was just unlocked, refresh owned skins
      if (data.ethereal?.unlocked && !ownedSkins.includes("ethereal")) {
        fetchOwnedSkins();
      }
    } catch (e) {
      console.error("Failed to fetch achievement status:", e);
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
      const lamports = Math.round(skin.price * LAMPORTS_PER_SOL);
      const transaction = new Transaction().add(
        SystemProgram.transfer({
          fromPubkey: publicKey,
          toPubkey: new PublicKey(STORE_WALLET),
          lamports
        })
      );

      const { blockhash } = await connection.getLatestBlockhash();
      transaction.recentBlockhash = blockhash;
      transaction.feePayer = publicKey;

      const signature = await sendTransaction(transaction, connection);
      await connection.confirmTransaction(signature, "confirmed");

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

  const sendGift = async () => {
    if (!giftModal.skin || !giftRecipient.trim()) {
      toast.error("Please enter a recipient wallet address");
      return;
    }

    // Validate wallet address format
    try {
      new PublicKey(giftRecipient.trim());
    } catch {
      toast.error("Invalid wallet address");
      return;
    }

    if (giftRecipient.trim() === publicKey?.toBase58()) {
      toast.error("You cannot gift to yourself");
      return;
    }

    clickFeedback();
    setSendingGift(true);

    try {
      await axios.post(`${API}/skins/gift`, {
        sender_wallet: publicKey.toBase58(),
        recipient_wallet: giftRecipient.trim(),
        skin_id: giftModal.skin.id
      });

      playSoundIfEnabled("success");
      toast.success(`${giftModal.skin.name} sent to ${giftRecipient.slice(0, 8)}...!`);
      
      // Remove skin from owned
      setOwnedSkins(ownedSkins.filter(s => s !== giftModal.skin.id));
      
      // If gifted skin was selected, reset to default
      if (selectedSkin === giftModal.skin.id) {
        setSelectedSkin("default");
        localStorage.setItem("bullpugSkin", "default");
        onSkinSelect?.("default");
      }

      setGiftModal({ open: false, skin: null });
      setGiftRecipient("");
      fetchGiftHistory();
      
    } catch (e) {
      console.error("Gift failed:", e);
      playSoundIfEnabled("error");
      toast.error(e.response?.data?.detail || "Failed to send gift");
    }

    setSendingGift(false);
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
      <div className="w-full max-w-5xl max-h-[90vh] overflow-auto mx-4 glass-card rounded-2xl border border-white/10">
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
              <p className="text-xs text-slate-500">Unlock skins with bonus points • Gift to friends</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Current Selection */}
        <div className="p-4 border-b border-white/5">
          <div className="flex items-center gap-4">
            <div className="relative shrink-0">
              <SkinPreview3D
                skinId={selectedSkin}
                size={120}
                glowColor={getSkinById(selectedSkin).color}
              />
            </div>
            <div>
              <p className="text-xs text-slate-500">Currently Equipped</p>
              <p className="text-lg font-bold text-white" data-testid="equipped-skin-name">{getSkinById(selectedSkin).name}</p>
              <p className="text-xs text-slate-400 mt-1 max-w-[220px]">{getSkinById(selectedSkin).description}</p>
              {getSkinById(selectedSkin).bonusPercent > 0 && (
                <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] border-[#00FFA3]/30 text-[10px] mt-2">
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
              const isAchievement = skin.achievement;
              const isEthereal = skin.id === "ethereal";

              return (
                <div
                  key={skin.id}
                  className={`relative rounded-xl border-2 transition-all overflow-hidden group ${
                    isSelected 
                      ? "border-[#00FFA3] ring-2 ring-[#00FFA3]/30" 
                      : owned 
                        ? "border-white/10 hover:border-white/30 cursor-pointer" 
                        : isAchievement
                          ? "border-pink-500/30 bg-gradient-to-b from-pink-500/5 to-transparent"
                          : "border-white/5 opacity-80"
                  }`}
                  data-testid={`skin-${skin.id}`}
                >
                  {/* Image with Animation */}
                  <div 
                    className="aspect-square relative overflow-hidden bg-gradient-to-b from-slate-900 to-slate-800"
                    onMouseEnter={() => setPreviewSkin(skin)}
                    onMouseLeave={() => setPreviewSkin(null)}
                  >
                    <img 
                      src={skin.image} 
                      alt={skin.name}
                      className={`w-full h-full object-contain transition-transform duration-300 ${
                        previewSkin?.id === skin.id ? "scale-110" : ""
                      } ${!owned && isAchievement ? "grayscale" : ""}`}
                      style={{ 
                        filter: owned ? `drop-shadow(0 0 8px ${skin.color}40)` : undefined
                      }}
                    />
                    
                    {/* Animated Glow Effect on Hover */}
                    <div className={`absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent transition-opacity ${
                      previewSkin?.id === skin.id ? "opacity-100" : "opacity-0"
                    }`} />
                    
                    {/* Animated Border Glow */}
                    {previewSkin?.id === skin.id && (
                      <div 
                        className="absolute inset-0 rounded-xl animate-pulse"
                        style={{ 
                          boxShadow: `inset 0 0 30px ${skin.color}40, 0 0 20px ${skin.color}30`
                        }} 
                      />
                    )}
                    
                    {/* Lock overlay for unowned - special styling for achievement skins */}
                    {!owned && (
                      <div className={`absolute inset-0 flex flex-col items-center justify-center ${
                        isAchievement ? "bg-black/70" : "bg-black/60"
                      }`}>
                        {isAchievement ? (
                          <>
                            <Trophy className="w-8 h-8 text-pink-400 mb-1" />
                            <p className="text-[10px] text-pink-300 font-bold">ACHIEVEMENT</p>
                          </>
                        ) : (
                          <Lock className="w-8 h-8 text-slate-400" />
                        )}
                      </div>
                    )}

                    {/* Selected check */}
                    {isSelected && (
                      <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-[#00FFA3] flex items-center justify-center animate-bounce-in">
                        <Check className="w-4 h-4 text-black" />
                      </div>
                    )}

                    {/* Rarity badge */}
                    <div className={`absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${rarity.bg} ${rarity.text} ${rarity.border} border`}>
                      {skin.rarity === "legendary" && <Crown className="w-3 h-3 inline mr-1" />}
                      {skin.rarity === "mythic" && <Star className="w-3 h-3 inline mr-1" />}
                      {skin.rarity}
                    </div>

                    {/* Preview button */}
                    {previewSkin?.id === skin.id && (
                      <button 
                        onClick={(e) => { e.stopPropagation(); setPreviewSkin(skin); }}
                        className="absolute bottom-2 right-2 p-1.5 rounded-lg bg-black/70 text-white hover:bg-black/90 transition-colors"
                        data-testid={`preview-${skin.id}`}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  {/* Info */}
                  <div className="p-2 bg-black/40">
                    <p className="text-sm font-bold text-white truncate">{skin.name}</p>
                    <div className="flex items-center justify-between mt-1">
                      {skin.bonusPercent > 0 ? (
                        <span className={`text-[10px] flex items-center gap-1 ${isAchievement ? "text-pink-300" : "text-[#00FFA3]"}`}>
                          <Sparkles className="w-3 h-3" /> +{skin.bonusPercent}%
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500">Default</span>
                      )}

                      {owned ? (
                        <span className="text-[10px] text-slate-400">Owned</span>
                      ) : isAchievement ? (
                        achievementStatus ? (
                          <span className="text-[10px] text-pink-400 font-bold">
                            {achievementStatus.progress}/{achievementStatus.required}
                          </span>
                        ) : (
                          <span className="text-[10px] text-pink-400">Unlock</span>
                        )
                      ) : (
                        <span className="text-[10px] text-[#D946EF] font-bold">{skin.price} SOL</span>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons Overlay */}
                  <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 p-2">
                    {owned ? (
                      <>
                        <Button
                          onClick={(e) => { e.stopPropagation(); selectSkin(skin.id); }}
                          disabled={isSelected}
                          className={`w-full text-xs py-2 ${
                            isSelected 
                              ? "bg-[#00FFA3]/20 text-[#00FFA3] border border-[#00FFA3]/30" 
                              : "bg-[#00FFA3] text-black hover:bg-[#00FFA3]/80"
                          }`}
                          data-testid={`equip-${skin.id}`}
                        >
                          {isSelected ? "Equipped" : "Equip"}
                        </Button>
                        {skin.id !== "default" && !isAchievement && (
                          <Button
                            onClick={(e) => { e.stopPropagation(); setGiftModal({ open: true, skin }); }}
                            className="w-full bg-[#D946EF]/20 text-[#D946EF] border border-[#D946EF]/30 hover:bg-[#D946EF]/30 text-xs py-2"
                            data-testid={`gift-${skin.id}`}
                          >
                            <Gift className="w-3 h-3 mr-1" /> Gift
                          </Button>
                        )}
                        {isAchievement && (
                          <p className="text-[10px] text-pink-300 text-center italic">Achievement skins cannot be gifted</p>
                        )}
                      </>
                    ) : isAchievement ? (
                      <div className="text-center px-2">
                        <Trophy className="w-6 h-6 text-pink-400 mx-auto mb-2" />
                        <p className="text-xs text-pink-300 font-bold mb-1">Achievement Skin</p>
                        <p className="text-[10px] text-slate-400 mb-2">{skin.unlockRequirement}</p>
                        {achievementStatus && (
                          <div className="w-full bg-white/10 rounded-full h-2 mb-2">
                            <div 
                              className="bg-gradient-to-r from-pink-500 to-purple-500 h-2 rounded-full transition-all"
                              style={{ width: `${(achievementStatus.progress / achievementStatus.required) * 100}%` }}
                            />
                          </div>
                        )}
                        <p className="text-[10px] text-pink-400 font-bold">
                          {achievementStatus ? `${achievementStatus.progress}/${achievementStatus.required} skins owned` : "Loading..."}
                        </p>
                      </div>
                    ) : connected ? (
                      <Button
                        onClick={(e) => { e.stopPropagation(); purchaseSkin(skin); }}
                        disabled={purchasing === skin.id}
                        className="w-full bg-[#D946EF] text-white font-bold text-xs py-2 hover:bg-[#D946EF]/80"
                        data-testid={`buy-${skin.id}`}
                      >
                        {purchasing === skin.id ? "Buying..." : `Buy ${skin.price} SOL`}
                      </Button>
                    ) : (
                      <p className="text-xs text-slate-400 text-center">Connect wallet to buy</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Gift History */}
        {connected && giftHistory.length > 0 && (
          <div className="p-4 border-t border-white/5">
            <h3 className="text-sm font-bold text-slate-400 mb-3 flex items-center gap-2">
              <Gift className="w-4 h-4" /> Recent Gifts
            </h3>
            <div className="space-y-2 max-h-32 overflow-auto">
              {giftHistory.slice(0, 5).map((gift, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-white/5 text-xs">
                  <div className="flex items-center gap-2">
                    <img src={getSkinById(gift.skin_id).image} alt="" className="w-6 h-6 rounded object-cover" />
                    <span className="text-white font-bold">{getSkinById(gift.skin_id).name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-400">
                    {gift.type === "sent" ? (
                      <>
                        <ArrowRight className="w-3 h-3" />
                        <span>{gift.recipient_wallet?.slice(0, 6)}...</span>
                      </>
                    ) : (
                      <>
                        <span>From {gift.sender_wallet?.slice(0, 6)}...</span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        {!connected && (
          <div className="p-4 border-t border-white/5 text-center">
            <p className="text-sm text-slate-400">Connect your wallet to purchase or gift skins</p>
          </div>
        )}
      </div>

      {/* Animated Preview Modal */}
      {previewSkin && (
        <div 
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/90 backdrop-blur-md"
          onClick={() => setPreviewSkin(null)}
        >
          <div className="relative max-w-lg w-full mx-4" onClick={e => e.stopPropagation()}>
            {/* Animated Background Glow */}
            <div 
              className="absolute inset-0 blur-3xl opacity-50 animate-pulse"
              style={{ background: `radial-gradient(circle, ${previewSkin.color}40 0%, transparent 70%)` }}
            />
            
            <div className="relative glass-card rounded-2xl p-6 border-2" style={{ borderColor: `${previewSkin.color}50` }}>
              {/* Close button */}
              <button 
                onClick={() => setPreviewSkin(null)}
                className="absolute top-4 right-4 p-2 rounded-full bg-white/10 text-white hover:bg-white/20"
              >
                <X size={20} />
              </button>

              {/* Animated Skin Image */}
              <div className="relative w-48 h-48 mx-auto mb-6">
                <div 
                  className="absolute inset-0 rounded-full animate-spin-slow opacity-30"
                  style={{ 
                    background: `conic-gradient(from 0deg, ${previewSkin.color}, transparent, ${previewSkin.color})`,
                  }}
                />
                <img 
                  src={previewSkin.image} 
                  alt={previewSkin.name}
                  className="relative w-full h-full rounded-xl object-cover border-4 skin-float"
                  style={{ borderColor: previewSkin.color }}
                />
                
                {/* Sparkle particles */}
                <div className="absolute inset-0 pointer-events-none">
                  {[...Array(6)].map((_, i) => (
                    <div
                      key={i}
                      className="absolute w-2 h-2 rounded-full animate-sparkle"
                      style={{
                        background: previewSkin.color,
                        left: `${20 + Math.random() * 60}%`,
                        top: `${20 + Math.random() * 60}%`,
                        animationDelay: `${i * 0.3}s`,
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Skin Info */}
              <div className="text-center">
                <Badge className={`${RARITY_COLORS[previewSkin.rarity].bg} ${RARITY_COLORS[previewSkin.rarity].text} ${RARITY_COLORS[previewSkin.rarity].border} border mb-2`}>
                  {previewSkin.rarity === "legendary" && <Crown className="w-3 h-3 inline mr-1" />}
                  {previewSkin.rarity === "mythic" && <Star className="w-3 h-3 inline mr-1" />}
                  {previewSkin.rarity.toUpperCase()}
                </Badge>
                <h3 className="text-2xl font-black text-white mb-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                  {previewSkin.name}
                </h3>
                <p className="text-sm text-slate-400 mb-4">{previewSkin.description}</p>
                
                {previewSkin.bonusPercent > 0 && (
                  <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full mb-4 ${
                    previewSkin.achievement 
                      ? "bg-pink-500/10 border border-pink-500/30" 
                      : "bg-[#00FFA3]/10 border border-[#00FFA3]/30"
                  }`}>
                    <Sparkles className={`w-5 h-5 ${previewSkin.achievement ? "text-pink-400" : "text-[#00FFA3]"}`} />
                    <span className={`text-lg font-bold ${previewSkin.achievement ? "text-pink-300" : "text-[#00FFA3]"}`}>
                      +{previewSkin.bonusPercent}% Bonus Points
                    </span>
                  </div>
                )}

                {/* Achievement Progress Bar */}
                {previewSkin.achievement && !ownedSkins.includes(previewSkin.id) && achievementStatus && (
                  <div className="mb-4 px-4">
                    <p className="text-xs text-slate-500 mb-2">Collection Progress</p>
                    <div className="w-full bg-white/10 rounded-full h-3 mb-2">
                      <div 
                        className="bg-gradient-to-r from-pink-500 to-purple-500 h-3 rounded-full transition-all"
                        style={{ width: `${(achievementStatus.progress / achievementStatus.required) * 100}%` }}
                      />
                    </div>
                    <p className="text-sm text-pink-400 font-bold">
                      {achievementStatus.progress}/{achievementStatus.required} skins owned
                    </p>
                    {achievementStatus.missing_skins?.length > 0 && (
                      <p className="text-[10px] text-slate-500 mt-2">
                        Missing: {achievementStatus.missing_skins.map(s => {
                          const skin = SKINS.find(sk => sk.id === s);
                          return skin?.name || s;
                        }).join(", ")}
                      </p>
                    )}
                  </div>
                )}

                {/* Action Button */}
                {ownedSkins.includes(previewSkin.id) ? (
                  <div className="flex gap-2 justify-center flex-wrap">
                    <Button
                      onClick={() => { selectSkin(previewSkin.id); setPreviewSkin(null); }}
                      disabled={selectedSkin === previewSkin.id}
                      className="bg-[#00FFA3] text-black font-bold px-6"
                    >
                      {selectedSkin === previewSkin.id ? "Currently Equipped" : "Equip Now"}
                    </Button>
                    {previewSkin.id !== "default" && !previewSkin.achievement && (
                      <Button
                        onClick={() => { setGiftModal({ open: true, skin: previewSkin }); setPreviewSkin(null); }}
                        className="bg-[#D946EF] text-white font-bold px-6"
                      >
                        <Gift className="w-4 h-4 mr-2" /> Gift
                      </Button>
                    )}
                  </div>
                ) : previewSkin.achievement ? (
                  <div className="text-center">
                    <p className="text-sm text-pink-300 font-bold mb-2">Achievement Skin</p>
                    <p className="text-xs text-slate-400">{previewSkin.unlockRequirement}</p>
                  </div>
                ) : (
                  <Button
                    onClick={() => { purchaseSkin(previewSkin); setPreviewSkin(null); }}
                    disabled={purchasing === previewSkin.id || !connected}
                    className="bg-[#D946EF] text-white font-bold px-8 py-3 text-lg"
                  >
                    {!connected ? "Connect Wallet" : purchasing === previewSkin.id ? "Purchasing..." : `Buy for ${previewSkin.price} SOL`}
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Gift Modal */}
      {giftModal.open && giftModal.skin && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/90 backdrop-blur-md">
          <div className="relative max-w-md w-full mx-4 glass-card rounded-2xl p-6 border border-[#D946EF]/30">
            {/* Close button */}
            <button 
              onClick={() => { setGiftModal({ open: false, skin: null }); setGiftRecipient(""); }}
              className="absolute top-4 right-4 p-2 rounded-full bg-white/10 text-white hover:bg-white/20"
            >
              <X size={20} />
            </button>

            <div className="text-center mb-6">
              <div className="w-12 h-12 mx-auto rounded-full bg-[#D946EF]/10 flex items-center justify-center mb-3">
                <Gift className="w-6 h-6 text-[#D946EF]" />
              </div>
              <h3 className="text-xl font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                Gift Skin
              </h3>
              <p className="text-sm text-slate-400">Send {giftModal.skin.name} to a friend</p>
            </div>

            {/* Skin Preview */}
            <div className="flex items-center gap-4 p-3 rounded-xl bg-white/5 mb-4">
              <img 
                src={giftModal.skin.image} 
                alt={giftModal.skin.name}
                className="w-16 h-16 rounded-lg object-cover border-2"
                style={{ borderColor: giftModal.skin.color }}
              />
              <div>
                <p className="font-bold text-white">{giftModal.skin.name}</p>
                <Badge className={`${RARITY_COLORS[giftModal.skin.rarity].bg} ${RARITY_COLORS[giftModal.skin.rarity].text} text-[10px]`}>
                  {giftModal.skin.rarity}
                </Badge>
                {giftModal.skin.bonusPercent > 0 && (
                  <p className="text-xs text-[#00FFA3] mt-1">+{giftModal.skin.bonusPercent}% Bonus</p>
                )}
              </div>
            </div>

            {/* Recipient Input */}
            <div className="mb-4">
              <label className="text-xs text-slate-500 uppercase mb-1 block">Recipient Wallet Address</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <Input
                  value={giftRecipient}
                  onChange={(e) => setGiftRecipient(e.target.value)}
                  placeholder="Enter Solana wallet address..."
                  className="bg-black/50 border-white/10 text-white pl-10"
                  data-testid="gift-recipient-input"
                />
              </div>
            </div>

            {/* Warning */}
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 mb-4">
              <p className="text-xs text-amber-400">
                ⚠️ This action cannot be undone. The skin will be transferred to the recipient's wallet.
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                onClick={() => { setGiftModal({ open: false, skin: null }); setGiftRecipient(""); }}
                className="flex-1 bg-white/10 text-white hover:bg-white/20"
              >
                Cancel
              </Button>
              <Button
                onClick={sendGift}
                disabled={sendingGift || !giftRecipient.trim()}
                className="flex-1 bg-[#D946EF] text-white font-bold hover:bg-[#D946EF]/80"
                data-testid="send-gift-btn"
              >
                {sendingGift ? "Sending..." : (
                  <>
                    <Send className="w-4 h-4 mr-2" /> Send Gift
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* CSS for animations */}
      <style jsx>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(-2deg); }
          50% { transform: translateY(-10px) rotate(2deg); }
        }
        @keyframes sparkle {
          0%, 100% { opacity: 0; transform: scale(0); }
          50% { opacity: 1; transform: scale(1); }
        }
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes bounce-in {
          0% { transform: scale(0); }
          50% { transform: scale(1.2); }
          100% { transform: scale(1); }
        }
        @keyframes pulse-glow {
          0%, 100% { box-shadow: 0 0 10px currentColor; }
          50% { box-shadow: 0 0 25px currentColor; }
        }
        .skin-float {
          animation: float 3s ease-in-out infinite;
        }
        .skin-pulse {
          animation: pulse-glow 2s ease-in-out infinite;
        }
        .animate-sparkle {
          animation: sparkle 2s ease-in-out infinite;
        }
        .animate-spin-slow {
          animation: spin-slow 8s linear infinite;
        }
        .animate-bounce-in {
          animation: bounce-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
