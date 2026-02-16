import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useWallet } from "@solana/wallet-adapter-react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import { useTranslation } from "react-i18next";
import { Menu, X, MessageCircle, MessageSquare } from "lucide-react";
import { FaXTwitter } from "react-icons/fa6";
import NotificationBell from "./NotificationBell";
import LanguageSwitcher from "./LanguageSwitcher";

const LOGO = "https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png";

// Check if wallet is admin
const ADMIN_WALLETS = [
  "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT",
  "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { publicKey, connected } = useWallet();
  const { t } = useTranslation();
  
  const isAdmin = connected && publicKey && ADMIN_WALLETS.includes(publicKey.toBase58());

  const NAV_LINKS = [
    { name: t('nav.home'), path: "/" },
    { name: t('nav.arena'), path: "/betting" },
    { name: t('nav.game'), path: "/game" },
    { name: t('nav.exitSim'), path: "/exit-simulator" },
    { name: t('nav.reflections'), path: "/reflections" },
    { name: t('nav.journal'), path: "/journal" },
    { name: t('nav.forum'), path: "/forum" },
    { name: t('nav.wallet'), path: "/wallet" },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/50 backdrop-blur-xl border-b border-white/5" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2" data-testid="nav-logo">
            <img src={LOGO} alt="Bullpug" className="w-9 h-9 rounded-full ring-2 ring-[#00FFA3]/30" />
            <span className="font-black text-lg tracking-wider hidden sm:block" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              BULL<span className="text-[#00FFA3]">PUG</span>
            </span>
          </Link>

          <div className="hidden lg:flex items-center gap-1">
            {NAV_LINKS.map(link => (
              <Link
                key={link.path}
                to={link.path}
                data-testid={`nav-${link.name.toLowerCase().replace(/\s/g, '-')}`}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200 ${
                  location.pathname === link.path
                    ? 'text-[#00FFA3] bg-[#00FFA3]/10'
                    : 'text-slate-500 hover:text-white hover:bg-white/5'
                }`}
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}
              >
                {link.name}
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
              <NotificationBell />
            </div>
            <WalletMultiButton
              data-testid="wallet-connect-btn"
              style={{
                background: '#00FFA3',
                color: '#000',
                fontWeight: 700,
                borderRadius: '9999px',
                fontSize: '12px',
                padding: '8px 16px',
                height: '36px',
                fontFamily: 'Space Grotesk, sans-serif',
              }}
            />
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
                className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                  location.pathname === link.path
                    ? 'text-[#00FFA3] bg-[#00FFA3]/10'
                    : 'text-slate-400 hover:text-white'
                }`}
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}
              >
                {link.name}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}
