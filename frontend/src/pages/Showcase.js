import { useState, useEffect } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { 
  Trophy, Star, Crown, User, Share2, Settings, Lock, 
  Check, Sparkles, Gift, Award, TrendingUp, Eye, Edit2,
  ExternalLink, Copy, ChevronRight, Twitter, MessageCircle, Link2
} from "lucide-react";
import { SKINS, RARITY_COLORS, getSkinById } from "@/config/skins";
import Navbar from "@/components/Navbar";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Showcase() {
  const { walletAddress } = useParams();
  const { publicKey, connected } = useWallet();
  const { t } = useTranslation();
  const [showcase, setShowcase] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [settings, setSettings] = useState({ display_name: "", bio: "", is_public: true });
  const [leaderboard, setLeaderboard] = useState([]);
  const [recentAcquisitions, setRecentAcquisitions] = useState([]);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareData, setShareData] = useState(null);

  const isOwnShowcase = connected && publicKey && walletAddress === publicKey.toBase58();
  const displayWallet = walletAddress || (connected && publicKey?.toBase58());

  useEffect(() => {
    if (displayWallet) {
      fetchShowcase();
    }
    fetchLeaderboard();
    fetchRecentAcquisitions();
  }, [displayWallet]);

  const fetchShowcase = async () => {
    try {
      setLoading(true);
      const { data } = await axios.get(`${API}/showcase/${displayWallet}`);
      setShowcase(data);
      setSettings({
        display_name: data.display_name,
        bio: data.bio,
        is_public: data.is_public
      });
    } catch (e) {
      console.error("Failed to fetch showcase:", e);
      toast.error("Failed to load showcase");
    } finally {
      setLoading(false);
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const { data } = await axios.get(`${API}/showcase/leaderboard/collectors?limit=10`);
      setLeaderboard(data.leaderboard || []);
    } catch (e) {
      console.error("Failed to fetch leaderboard:", e);
    }
  };

  const fetchRecentAcquisitions = async () => {
    try {
      const { data } = await axios.get(`${API}/showcase/recent-acquisitions?limit=8`);
      setRecentAcquisitions(data.acquisitions || []);
    } catch (e) {
      console.error("Failed to fetch recent acquisitions:", e);
    }
  };

  const saveSettings = async () => {
    try {
      await axios.post(`${API}/showcase/settings`, {
        wallet_address: displayWallet,
        display_name: settings.display_name,
        bio: settings.bio,
        is_public: settings.is_public
      });
      toast.success("Showcase settings saved!");
      setEditing(false);
      fetchShowcase();
    } catch (e) {
      toast.error("Failed to save settings");
    }
  };

  const openShareModal = async () => {
    try {
      const { data } = await axios.get(`${API}/showcase/share-text/${displayWallet}`);
      setShareData(data);
      setShowShareModal(true);
    } catch (e) {
      console.error("Failed to fetch share data:", e);
      // Fallback share data
      setShareData({
        share_text: `Check out my Bullpug skin collection! 🚀\n\n${window.location.origin}/showcase/${displayWallet}\n\n#Bullpug #Solana`,
        stats: showcase?.stats || {}
      });
      setShowShareModal(true);
    }
  };

  const shareToTwitter = () => {
    const text = encodeURIComponent(shareData?.share_text || "Check out my Bullpug collection!");
    const url = encodeURIComponent(`${window.location.origin}/showcase/${displayWallet}`);
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, "_blank", "width=550,height=420");
  };

  const shareToTelegram = () => {
    const text = encodeURIComponent(shareData?.share_text || "Check out my Bullpug collection!");
    const url = encodeURIComponent(`${window.location.origin}/showcase/${displayWallet}`);
    window.open(`https://t.me/share/url?url=${url}&text=${text}`, "_blank");
  };

  const copyShareLink = async () => {
    try {
      const url = `${window.location.origin}/showcase/${displayWallet}`;
      await navigator.clipboard.writeText(url);
      toast.success("Showcase link copied!");
    } catch (e) {
      toast.error("Failed to copy link");
    }
  };

  const copyShareText = async () => {
    try {
      await navigator.clipboard.writeText(shareData?.share_text || "");
      toast.success("Share text copied!");
    } catch (e) {
      toast.error("Failed to copy text");
    }
  };

  const getRarityIcon = (rarity) => {
    switch (rarity) {
      case "mythic": return <Star className="w-4 h-4 text-pink-400" />;
      case "legendary": return <Crown className="w-4 h-4 text-amber-400" />;
      case "epic": return <Trophy className="w-4 h-4 text-purple-400" />;
      default: return null;
    }
  };

  if (!displayWallet) {
    return (
      <div className="min-h-screen bg-[#0A0A12]">
        <Navbar />
        <div className="container mx-auto px-4 py-20 text-center">
          <Trophy className="w-16 h-16 text-[#00FFA3] mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-4">Skin Collection Showcase</h1>
          <p className="text-slate-400 mb-8">Connect your wallet to view your collection</p>
          <Link to="/game">
            <Button className="bg-[#00FFA3] text-black font-bold">
              Go to Speed Run Game
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A12]">
      <Navbar />
      
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex flex-col lg:flex-row gap-8 mb-8">
          {/* Profile Card */}
          <div className="flex-1 bg-gradient-to-br from-[#0F0F1A] to-[#1A1A2E] rounded-2xl p-6 border border-white/10">
            {loading ? (
              <div className="animate-pulse">
                <div className="h-20 w-20 bg-white/10 rounded-full mb-4" />
                <div className="h-6 w-32 bg-white/10 rounded mb-2" />
                <div className="h-4 w-48 bg-white/10 rounded" />
              </div>
            ) : (
              <>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-4">
                    {/* Equipped Skin Avatar */}
                    <div className="relative">
                      <img 
                        src={getSkinById(showcase?.equipped_skin || "default").image}
                        alt="Avatar"
                        className="w-20 h-20 rounded-full border-4 border-[#00FFA3]/30 object-cover"
                      />
                      {showcase?.stats?.has_ethereal && (
                        <div className="absolute -bottom-1 -right-1 bg-pink-500 rounded-full p-1">
                          <Star className="w-4 h-4 text-white" />
                        </div>
                      )}
                    </div>
                    <div>
                      {editing ? (
                        <Input
                          value={settings.display_name}
                          onChange={(e) => setSettings({ ...settings, display_name: e.target.value })}
                          className="bg-white/5 border-white/20 text-white mb-2"
                          placeholder="Display Name"
                          maxLength={30}
                        />
                      ) : (
                        <h1 className="text-2xl font-bold text-white">{showcase?.display_name}</h1>
                      )}
                      <p className="text-sm text-slate-500 font-mono">
                        {displayWallet?.slice(0, 8)}...{displayWallet?.slice(-6)}
                      </p>
                    </div>
                  </div>
                  
                  {isOwnShowcase && (
                    <div className="flex gap-2">
                      {editing ? (
                        <>
                          <Button onClick={saveSettings} size="sm" className="bg-[#00FFA3] text-black">
                            Save
                          </Button>
                          <Button onClick={() => setEditing(false)} size="sm" variant="outline" className="border-white/20 text-white">
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button onClick={() => setEditing(true)} size="sm" variant="outline" className="border-white/20 text-white">
                            <Edit2 className="w-4 h-4 mr-1" /> Edit
                          </Button>
                          <Button onClick={openShareModal} size="sm" className="bg-[#D946EF] text-white" data-testid="share-btn">
                            <Share2 className="w-4 h-4 mr-1" /> Share
                          </Button>
                        </>
                      )}
                    </div>
                  )}
                </div>
                
                {editing ? (
                  <textarea
                    value={settings.bio}
                    onChange={(e) => setSettings({ ...settings, bio: e.target.value })}
                    className="w-full bg-white/5 border border-white/20 rounded-lg p-3 text-white text-sm resize-none"
                    placeholder="Tell others about your collection..."
                    rows={2}
                    maxLength={200}
                  />
                ) : (
                  <p className="text-slate-400 text-sm">{showcase?.bio || "No bio yet"}</p>
                )}
                
                {/* Stats Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
                  <div className="bg-white/5 rounded-xl p-3 text-center">
                    <p className="text-2xl font-bold text-[#00FFA3]">{showcase?.stats?.total_owned || 0}</p>
                    <p className="text-xs text-slate-500">Skins Owned</p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-3 text-center">
                    <p className="text-2xl font-bold text-white">{showcase?.stats?.completion_percent || 0}%</p>
                    <p className="text-xs text-slate-500">Collection</p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-3 text-center">
                    <p className="text-2xl font-bold text-[#D946EF]">+{showcase?.stats?.total_bonus || 0}%</p>
                    <p className="text-xs text-slate-500">Total Bonus</p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-3 text-center">
                    <p className="text-2xl font-bold text-amber-400">{showcase?.stats?.missing_for_ethereal || 10}</p>
                    <p className="text-xs text-slate-500">To Ethereal</p>
                  </div>
                </div>

                {/* Rarity Breakdown */}
                <div className="flex flex-wrap gap-2 mt-4">
                  {Object.entries(showcase?.stats?.rarity_counts || {}).map(([rarity, count]) => (
                    count > 0 && (
                      <Badge 
                        key={rarity} 
                        className={`${RARITY_COLORS[rarity]?.bg} ${RARITY_COLORS[rarity]?.text} ${RARITY_COLORS[rarity]?.border} border`}
                      >
                        {getRarityIcon(rarity)} {count} {rarity}
                      </Badge>
                    )
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Collector Leaderboard */}
          <div className="lg:w-80 bg-gradient-to-br from-[#0F0F1A] to-[#1A1A2E] rounded-2xl p-4 border border-white/10">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-[#00FFA3]" /> Top Collectors
            </h3>
            <div className="space-y-2">
              {leaderboard.slice(0, 5).map((collector, i) => (
                <Link 
                  key={collector.wallet_address}
                  to={`/showcase/${collector.wallet_address}`}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    i === 0 ? "bg-amber-500 text-black" :
                    i === 1 ? "bg-slate-400 text-black" :
                    i === 2 ? "bg-orange-600 text-white" :
                    "bg-white/10 text-white"
                  }`}>
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{collector.display_name}</p>
                    <p className="text-xs text-slate-500">{collector.skin_count} skins</p>
                  </div>
                  {collector.has_ethereal && <Star className="w-4 h-4 text-pink-400" />}
                </Link>
              ))}
            </div>
            <Link to="/showcase/leaderboard" className="block mt-4">
              <Button variant="outline" className="w-full border-white/20 text-white text-sm">
                View Full Leaderboard <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </div>
        </div>

        {/* Collection Grid */}
        <div className="bg-gradient-to-br from-[#0F0F1A] to-[#1A1A2E] rounded-2xl p-6 border border-white/10 mb-8">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#00FFA3]" /> Skin Collection
          </h2>
          
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {[...Array(12)].map((_, i) => (
                <div key={i} className="aspect-square bg-white/5 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {showcase?.collection?.map((skin) => {
                const skinData = getSkinById(skin.id);
                const rarity = RARITY_COLORS[skin.rarity] || RARITY_COLORS.common;
                
                return (
                  <div
                    key={skin.id}
                    className={`relative rounded-xl border-2 overflow-hidden transition-all ${
                      skin.owned 
                        ? `${rarity.border} hover:scale-105` 
                        : "border-white/5 opacity-40 grayscale"
                    }`}
                    data-testid={`showcase-skin-${skin.id}`}
                  >
                    <div className="aspect-square relative">
                      <img 
                        src={skinData.image} 
                        alt={skin.name}
                        className="w-full h-full object-cover"
                      />
                      
                      {/* Rarity badge */}
                      <div className={`absolute top-1 left-1 px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${rarity.bg} ${rarity.text} ${rarity.border} border`}>
                        {getRarityIcon(skin.rarity)}
                        {skin.rarity}
                      </div>
                      
                      {/* Lock overlay */}
                      {!skin.owned && (
                        <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                          <Lock className="w-6 h-6 text-slate-500" />
                        </div>
                      )}
                      
                      {/* Owned indicator */}
                      {skin.owned && (
                        <div className="absolute top-1 right-1 w-5 h-5 rounded-full bg-[#00FFA3] flex items-center justify-center">
                          <Check className="w-3 h-3 text-black" />
                        </div>
                      )}
                      
                      {/* Special indicators */}
                      {skin.is_gift && skin.owned && (
                        <div className="absolute bottom-1 right-1 w-5 h-5 rounded-full bg-[#D946EF] flex items-center justify-center">
                          <Gift className="w-3 h-3 text-white" />
                        </div>
                      )}
                      {skin.is_achievement && skin.owned && (
                        <div className="absolute bottom-1 right-1 w-5 h-5 rounded-full bg-pink-500 flex items-center justify-center">
                          <Award className="w-3 h-3 text-white" />
                        </div>
                      )}
                    </div>
                    
                    <div className="p-1.5 bg-black/40">
                      <p className="text-xs font-bold text-white truncate">{skin.name}</p>
                      {skin.bonus_percent > 0 && (
                        <p className={`text-[10px] ${skin.rarity === "mythic" ? "text-pink-400" : "text-[#00FFA3]"}`}>
                          +{skin.bonus_percent}%
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Acquisitions */}
        <div className="bg-gradient-to-br from-[#0F0F1A] to-[#1A1A2E] rounded-2xl p-6 border border-white/10">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[#D946EF]" /> Recent Acquisitions
          </h2>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {recentAcquisitions.map((acq, i) => {
              const rarity = RARITY_COLORS[acq.rarity] || RARITY_COLORS.common;
              return (
                <div 
                  key={i}
                  className="flex items-center gap-3 p-3 bg-white/5 rounded-xl border border-white/5"
                >
                  <img 
                    src={getSkinById(acq.skin_id).image}
                    alt={acq.skin_name}
                    className="w-12 h-12 rounded-lg object-cover"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge className={`${rarity.bg} ${rarity.text} ${rarity.border} border text-[10px]`}>
                        {acq.rarity}
                      </Badge>
                      {acq.acquisition_type === "gift" && <Gift className="w-3 h-3 text-[#D946EF]" />}
                      {acq.acquisition_type === "achievement" && <Award className="w-3 h-3 text-pink-400" />}
                    </div>
                    <p className="text-sm font-medium text-white truncate">{acq.skin_name}</p>
                    <Link 
                      to={`/showcase/${acq.wallet_address}`}
                      className="text-xs text-slate-500 hover:text-[#00FFA3] truncate block"
                    >
                      {acq.display_name}
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
