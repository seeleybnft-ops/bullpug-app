import { useState, useEffect, useRef } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import axios from "axios";
import { 
  User, Camera, Twitter, Send, Globe, Save, 
  Gamepad2, Trophy, Coins, ArrowLeft, Check, X, Sparkles 
} from "lucide-react";
import { BadgeShowcase, BadgeRow } from "@/components/BadgeDisplay";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ProfilePage() {
  const { publicKey, connected } = useWallet();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  
  const [profile, setProfile] = useState(null);
  const [availableSkins, setAvailableSkins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showSkinSelector, setShowSkinSelector] = useState(false);
  
  // Form state
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [twitter, setTwitter] = useState("");
  const [telegram, setTelegram] = useState("");
  const [discord, setDiscord] = useState("");
  const [website, setWebsite] = useState("");
  const [selectedSkin, setSelectedSkin] = useState(null);

  useEffect(() => {
    if (connected && publicKey) {
      fetchProfile();
      fetchAvailableSkins();
    } else {
      setLoading(false);
    }
  }, [connected, publicKey]);

  const fetchProfile = async () => {
    try {
      const { data } = await axios.get(`${API}/profile/${publicKey.toBase58()}`);
      setProfile(data);
      setDisplayName(data.display_name || "");
      setBio(data.bio || "");
      setTwitter(data.twitter_handle || "");
      setTelegram(data.telegram_handle || "");
      setDiscord(data.discord_handle || "");
      setWebsite(data.website_url || "");
      setSelectedSkin(data.profile_skin_id);
      setLoading(false);
    } catch (e) {
      console.error("Error fetching profile:", e);
      setLoading(false);
    }
  };

  const fetchAvailableSkins = async () => {
    try {
      const { data } = await axios.get(`${API}/profile/${publicKey.toBase58()}/skins`);
      setAvailableSkins(data.skins || []);
    } catch (e) {
      console.error("Error fetching skins:", e);
    }
  };

  const handleSave = async () => {
    if (!publicKey) return;
    
    setSaving(true);
    try {
      await axios.put(`${API}/profile/${publicKey.toBase58()}`, {
        display_name: displayName,
        bio: bio,
        twitter_handle: twitter,
        telegram_handle: telegram,
        discord_handle: discord,
        website_url: website,
        profile_skin_id: selectedSkin
      });
      toast.success("Profile updated!");
      fetchProfile();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update profile");
    }
    setSaving(false);
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (file.size > 500 * 1024) {
      toast.error("Image too large (max 500KB)");
      return;
    }
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      await axios.post(`${API}/profile/${publicKey.toBase58()}/upload-image`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      toast.success("Profile image uploaded!");
      setSelectedSkin(null);
      fetchProfile();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to upload image");
    }
  };

  const selectSkinAsProfile = (skinId) => {
    setSelectedSkin(skinId);
    setShowSkinSelector(false);
  };

  const getProfileImage = () => {
    if (profile?.profile_image_url) {
      return profile.profile_image_url;
    }
    if (selectedSkin) {
      const skin = availableSkins.find(s => s.id === selectedSkin);
      return skin?.image || "/images/guardian_cutout.png";
    }
    return "/images/guardian_cutout.png";
  };

  if (!connected) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] pt-24 px-4">
        <div className="max-w-2xl mx-auto text-center py-20">
          <User className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Connect Wallet</h1>
          <p className="text-slate-400">Connect your Solana wallet to access your profile.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] pt-24 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="w-32 h-32 rounded-full bg-white/10 mx-auto" />
            <div className="h-8 bg-white/10 rounded w-1/2 mx-auto" />
            <div className="h-24 bg-white/10 rounded" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0F] pt-24 px-4 pb-16">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <button 
          onClick={() => navigate(-1)} 
          className="flex items-center gap-2 text-slate-400 hover:text-white mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <div className="glass-card rounded-2xl p-6 md:p-8">
          <h1 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            <User className="w-6 h-6 text-[#00FFA3]" />
            Edit Profile
          </h1>

          {/* Profile Image Section */}
          <div className="flex flex-col items-center mb-8">
            <div className="relative">
              <div className="w-32 h-32 rounded-full overflow-hidden bg-black/50 border-4 border-[#00FFA3]/30">
                <img 
                  src={getProfileImage()} 
                  alt="Profile" 
                  className="w-full h-full object-cover"
                />
              </div>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="absolute bottom-0 right-0 w-10 h-10 rounded-full bg-[#00FFA3] text-black flex items-center justify-center hover:bg-[#00FFA3]/80 transition-colors"
              >
                <Camera className="w-5 h-5" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
            </div>
            
            <button
              onClick={() => setShowSkinSelector(!showSkinSelector)}
              className="mt-3 text-sm text-[#00FFA3] hover:underline"
            >
              Use Bullpug Skin as Profile Pic
            </button>

            {/* Skin Selector */}
            {showSkinSelector && (
              <div className="mt-4 p-4 bg-black/40 rounded-xl w-full">
                <p className="text-sm text-slate-400 mb-3">Select an owned skin:</p>
                <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
                  {availableSkins.map((skin) => (
                    <button
                      key={skin.id}
                      onClick={() => selectSkinAsProfile(skin.id)}
                      className={`relative p-2 rounded-lg border-2 transition-all ${
                        selectedSkin === skin.id 
                          ? "border-[#00FFA3] bg-[#00FFA3]/10" 
                          : "border-white/10 hover:border-white/30"
                      }`}
                    >
                      <img src={skin.image} alt={skin.name} className="w-full aspect-square object-contain" />
                      {selectedSkin === skin.id && (
                        <div className="absolute top-1 right-1 w-4 h-4 rounded-full bg-[#00FFA3] flex items-center justify-center">
                          <Check className="w-3 h-3 text-black" />
                        </div>
                      )}
                      <p className="text-[10px] text-slate-400 mt-1 truncate">{skin.name}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Form Fields */}
          <div className="space-y-4">
            <div>
              <label className="text-sm text-slate-400 block mb-1">Display Name</label>
              <Input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Enter your display name"
                maxLength={50}
                className="bg-black/40 border-white/10"
              />
            </div>

            <div>
              <label className="text-sm text-slate-400 block mb-1">Bio</label>
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Tell us about yourself..."
                maxLength={500}
                rows={3}
                className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-[#00FFA3]/50 resize-none"
              />
              <p className="text-xs text-slate-500 mt-1">{bio.length}/500</p>
            </div>

            {/* Social Links */}
            <div className="pt-4 border-t border-white/10">
              <p className="text-sm text-slate-400 mb-3">Social Links</p>
              
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Twitter className="w-5 h-5 text-[#1DA1F2]" />
                  <Input
                    value={twitter}
                    onChange={(e) => setTwitter(e.target.value)}
                    placeholder="Twitter handle"
                    className="bg-black/40 border-white/10 flex-1"
                  />
                </div>
                
                <div className="flex items-center gap-2">
                  <Send className="w-5 h-5 text-[#0088cc]" />
                  <Input
                    value={telegram}
                    onChange={(e) => setTelegram(e.target.value)}
                    placeholder="Telegram handle"
                    className="bg-black/40 border-white/10 flex-1"
                  />
                </div>
                
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded bg-[#5865F2] flex items-center justify-center text-white text-xs font-bold">D</div>
                  <Input
                    value={discord}
                    onChange={(e) => setDiscord(e.target.value)}
                    placeholder="Discord username"
                    className="bg-black/40 border-white/10 flex-1"
                  />
                </div>
                
                <div className="flex items-center gap-2">
                  <Globe className="w-5 h-5 text-slate-400" />
                  <Input
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    placeholder="Website URL"
                    className="bg-black/40 border-white/10 flex-1"
                  />
                </div>
              </div>
            </div>

            {/* Game Stats */}
            {profile?.game_stats && (
              <div className="pt-4 border-t border-white/10">
                <p className="text-sm text-slate-400 mb-3">Game Stats</p>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-3 rounded-lg bg-black/40">
                    <Trophy className="w-5 h-5 text-[#FFD700] mx-auto mb-1" />
                    <p className="text-lg font-bold text-white">{profile.game_stats.high_score}</p>
                    <p className="text-xs text-slate-500">High Score</p>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-black/40">
                    <Coins className="w-5 h-5 text-[#FFD700] mx-auto mb-1" />
                    <p className="text-lg font-bold text-white">{profile.game_stats.total_moon_cheese || profile.game_stats.total_mooncakes || 0}</p>
                    <p className="text-xs text-slate-500">Moon Cheese</p>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-black/40">
                    <Gamepad2 className="w-5 h-5 text-[#00FFA3] mx-auto mb-1" />
                    <p className="text-lg font-bold text-white">{profile.game_stats.games_played}</p>
                    <p className="text-xs text-slate-500">Games</p>
                  </div>
                </div>
              </div>
            )}

            {/* Badges Section */}
            <div className="pt-4 border-t border-white/10">
              <BadgeShowcase walletAddress={publicKey?.toBase58()} />
            </div>

            {/* Save Button */}
            <Button
              onClick={handleSave}
              disabled={saving}
              className="w-full mt-6 bg-[#00FFA3] hover:bg-[#00FFA3]/80 text-black font-bold"
            >
              {saving ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                  Saving...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Save className="w-4 h-4" />
                  Save Profile
                </span>
              )}
            </Button>
          </div>
        </div>

        {/* Wallet Address */}
        <p className="text-center text-xs text-slate-500 mt-4">
          Wallet: {publicKey?.toBase58().slice(0, 8)}...{publicKey?.toBase58().slice(-8)}
        </p>
      </div>
    </div>
  );
}
