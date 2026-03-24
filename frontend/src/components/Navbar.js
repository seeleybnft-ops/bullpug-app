import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useWallet } from "@solana/wallet-adapter-react";
import { useTranslation } from "react-i18next";
import { Menu, X, MessageCircle, MessageSquare, User, Bot, Flame } from "lucide-react";
import { FaXTwitter } from "react-icons/fa6";
import NotificationBell from "./NotificationBell";
import LanguageSwitcher from "./LanguageSwitcher";
import UnifiedWalletButton from "./UnifiedWalletButton";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO = "https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png";

// Check if wallet is admin
const ADMIN_WALLETS = [
  "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT",
  "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [profileImage, setProfileImage] = useState(null);
  const [pendingEntryCount, setPendingEntryCount] = useState(0);
  const location = useLocation();
  const { publicKey, connected } = useWallet();
  const { t } = useTranslation();
  
  const isAdmin = connected && publicKey && ADMIN_WALLETS.includes(publicKey.toBase58());

  // Fetch profile to get profile image
  useEffect(() => {
    if (connected && publicKey) {
      fetchProfile();
      fetchPendingEntries();
    } else {
      setProfileImage(null);
      setPendingEntryCount(0);
    }
  }, [connected, publicKey]);
  
  // Fetch pending journal entries count
  const fetchPendingEntries = async () => {
    if (!publicKey) return;
    try {
      const { data } = await axios.get(`${API}/journal/pending/${publicKey.toBase58()}`);
      setPendingEntryCount(data.count || 0);
    } catch (e) {
      console.error("Failed to fetch pending entries:", e);
    }
  };

  const fetchProfile = async () => {
    try {
      const { data } = await axios.get(`${API}/profile/${publicKey.toBase58()}`);
      if (data.profile_image_url) {
        setProfileImage(data.profile_image_url);
      } else if (data.profile_skin_id) {
        setProfileImage(`/images/${data.profile_skin_id}_cutout.png`);
      } else {
        setProfileImage("/images/guardian_cutout.png");
      }
    } catch (e) {
      setProfileImage("/images/guardian_cutout.png");
    }
  };

  const NAV_LINKS = [
    { name: t('nav.home'), path: "/", color: "#00FFA3" },
    { name: t('nav.lore') || "Origins", path: "/lore", color: "#FFFFFF" },
    { name: "Journal", path: "/journal", color: "#F5D300", badge: pendingEntryCount > 0 ? pendingEntryCount : null },
    { name: "Trading Bot", path: "/ai-trader", icon: <Bot className="w-3 h-3" />, color: "#D946EF", hasBorder: true },
    { name: t('nav.game') || "Game", path: "/game", color: "#00C2FF" },
    { name: "PugBurn", path: "/pugburn", icon: <Flame className="w-3 h-3" />, color: "#FF6B6B", hasBorder: true },
    { name: t('nav.arena') || "Arena", path: "/betting", color: "#00FFA3", comingSoon: true },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/50 backdrop-blur-xl border-b border-white/5" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2" data-testid="nav-logo">
            <img src={LOGO} alt="Bullpug" className="w-9 h-9 rounded-full ring-2 ring-[#00FFA3]/30" />
            <span className="font-black text-lg tracking-wider hidden sm:flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              BULL<span className="text-[#00FFA3]">PUG</span>
              <span className="text-[10px] font-bold text-[#F5D300] bg-[#F5D300]/10 px-2 py-0.5 rounded-full border border-[#F5D300]/30">BETA</span>
            </span>
          </Link>

          <div className="hidden lg:flex items-center gap-1">
            {NAV_LINKS.map(link => (
              <Link
                key={link.path}
                to={link.path}
                data-testid={`nav-${link.name.toLowerCase().replace(/\s/g, '-')}`}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200 flex items-center gap-1 ${
                  link.hasBorder
                    ? location.pathname === link.path
                      ? `bg-opacity-10 border`
                      : `hover:bg-opacity-10 border border-opacity-20`
                    : location.pathname === link.path
                      ? `bg-opacity-10`
                      : `hover:bg-white/5`
                }`}
                style={{ 
                  fontFamily: 'Space Grotesk, sans-serif',
                  color: link.color,
                  backgroundColor: location.pathname === link.path ? `${link.color}15` : 'transparent',
                  borderColor: link.hasBorder ? `${link.color}40` : 'transparent'
                }}
              >
                {link.icon && link.icon}
                {link.name}
                {link.badge && (
                  <span className="px-1.5 py-0.5 text-[9px] bg-[#D946EF] text-white rounded-full font-bold animate-pulse ml-1" title={`${link.badge} pending entries`}>
                    {link.badge}
                  </span>
                )}
                {link.comingSoon && <span className="text-[7px] px-1 py-0.5 bg-[#F5D300]/20 text-[#F5D300] rounded-full ml-1">SOON</span>}
              </Link>
            ))}

            {isAdmin && (
              <Link
                to="/admin"
                className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                  location.pathname === '/admin'
                    ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                    : 'text-red-400/70 hover:text-red-400 hover:bg-red-500/10'
                }`}
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}
              >
                Admin
              </Link>
            )}
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-2">
              <a href="https://x.com/Bullpugcoin" target="_blank" rel="noopener noreferrer"
                data-testid="nav-x-link"
                className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-[#00FFA3]/50 transition-all">
                <FaXTwitter size={14} />
              </a>
              <a href="https://t.me/bullpugcoinchat" target="_blank" rel="noopener noreferrer"
                data-testid="nav-telegram-link"
                className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-[#00C2FF] hover:border-[#00C2FF]/50 transition-all">
                <MessageCircle size={14} />
              </a>
              {connected && (
                <Link to="/messages"
                  data-testid="nav-messages-link"
                  className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-[#D946EF] hover:border-[#D946EF]/50 transition-all">
                  <MessageSquare size={14} />
                </Link>
              )}
              {connected && (
                <Link to="/profile"
                  data-testid="nav-profile-link"
                  className="w-8 h-8 rounded-full overflow-hidden border-2 border-[#00FFA3]/30 hover:border-[#00FFA3] transition-all">
                  {profileImage ? (
                    <img src={profileImage} alt="Profile" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full bg-white/5 flex items-center justify-center">
                      <User size={14} className="text-slate-400" />
                    </div>
                  )}
                </Link>
              )}
              <NotificationBell />
              <LanguageSwitcher />
            </div>
            <UnifiedWalletButton />
            <button
              className="lg:hidden text-slate-400 hover:text-white"
              onClick={() => setOpen(!open)}
              data-testid="mobile-menu-btn"
            >
              {open ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>

        {open && (
          <div className="lg:hidden pb-4 border-t border-white/5 mt-2 pt-3 space-y-1">
            {NAV_LINKS.map(link => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium`}
                style={{ 
                  fontFamily: 'Space Grotesk, sans-serif',
                  color: link.color,
                  backgroundColor: location.pathname === link.path ? `${link.color}15` : 'transparent'
                }}
              >
                {link.icon && link.icon}
                {link.name}
                {link.comingSoon && <span className="text-[8px] px-1.5 py-0.5 bg-[#F5D300]/20 text-[#F5D300] rounded-full">SOON</span>}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}
