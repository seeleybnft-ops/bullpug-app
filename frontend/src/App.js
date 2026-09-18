import { useMemo, useEffect, useState } from "react";
import "@/App.css";
import "@/i18n/config"; // Initialize i18n
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConnectionProvider, WalletProvider } from "@solana/wallet-adapter-react";
import { WalletModalProvider } from "@solana/wallet-adapter-react-ui";
import { PhantomWalletAdapter } from "@solana/wallet-adapter-phantom";
import { SolflareWalletAdapter } from "@solana/wallet-adapter-solflare";
import { clusterApiUrl } from "@solana/web3.js";
import { Toaster } from "@/components/ui/sonner";
import { EVMWalletProvider } from "@/providers/EVMWalletProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import EnhancedAIAssistant from "@/components/EnhancedAIAssistant";
import PrivateAccessGate from "@/components/PrivateAccessGate";
import HomePage from "@/pages/HomePage";
import WalletDashboard from "@/pages/WalletDashboard";
import Portfolio from "@/pages/Portfolio";
import Forum from "@/pages/Forum";
import AdminPanel from "@/pages/AdminPanel";
import AdminDropVault from "@/pages/AdminDropVault";
import AdminCompanionTokens from "@/pages/AdminCompanionTokens";
import AdminVisualCanon from "@/pages/AdminVisualCanon";
import AdminAuthGate from "@/components/AdminAuthGate";
import NotificationPermissionPrompt from "@/components/NotificationPermissionPrompt";
import WhatsNewToast from "@/components/WhatsNewToast";
import usePageviewTracker from "@/hooks/usePageviewTracker";
import Messages from "@/pages/Messages";
import ProfilePage from "@/pages/ProfilePage";
import Lore from "@/pages/Lore";
import PugBurn from "@/pages/PugBurn";
import Archive from "@/pages/Archive";
import Companion from "@/pages/Companion";
import Shop from "@/pages/Shop";

// Detect if running inside Phantom's in-app browser (mobile only)
const isPhantomBrowser = () => {
  if (typeof window === 'undefined') return false;
  const userAgent = navigator.userAgent || '';
  // Phantom mobile browser includes "Phantom" in user agent AND is mobile
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
  const hasPhantomUA = userAgent.includes('Phantom');
  // Only return true if it's mobile AND has Phantom in user agent
  // Desktop Phantom extension shouldn't trigger this
  return isMobile && hasPhantomUA;
};

// Detect any in-app browser (WebView) - mobile only
const isInAppBrowser = () => {
  if (typeof window === 'undefined') return false;
  const userAgent = navigator.userAgent || '';
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
  // Only check for in-app browsers on mobile devices
  return isMobile && /WebView|wv|FBAN|FBAV|Instagram|Twitter|Line|WhatsApp/i.test(userAgent);
};

// Tiny render-less component that lives inside <BrowserRouter> so it can
// use the `useLocation`-based pageview hook. Mounted once near the top of
// the tree — the hook is idempotent and self-debounced.
function RouteAnalytics() {
  usePageviewTracker();
  return null;
}

function App() {
  const [isReady, setIsReady] = useState(false);
  
  const endpoint = useMemo(
    () => process.env.REACT_APP_SOLANA_RPC_URL || clusterApiUrl('mainnet-beta'),
    []
  );

  // Create wallet adapters with proper configuration
  const wallets = useMemo(() => {
    const adapters = [];
    
    try {
      // Always add Phantom adapter
      adapters.push(new PhantomWalletAdapter());
      
      // Add Solflare if not in Phantom browser (to avoid conflicts)
      if (!isPhantomBrowser()) {
        adapters.push(new SolflareWalletAdapter());
      }
    } catch (error) {
      console.error('Error initializing wallet adapters:', error);
    }
    
    return adapters;
  }, []);

  // Handle wallet adapter initialization
  useEffect(() => {
    // Give time for wallet adapters to initialize
    const timer = setTimeout(() => setIsReady(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // Wallet error handler
  const onError = (error) => {
    console.error('Wallet error:', error);
    // Don't show intrusive errors for common wallet issues
    if (error.name === 'WalletNotReadyError' || 
        error.name === 'WalletConnectionError' ||
        error.message?.includes('User rejected')) {
      return;
    }
  };

  // Don't use autoConnect in Phantom browser to avoid issues
  const shouldAutoConnect = !isPhantomBrowser() && !isInAppBrowser();

  if (!isReady) {
    return (
      <div className="min-h-screen bg-[#05050A] text-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[#00FFA3] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400 text-sm">Initializing...</p>
        </div>
      </div>
    );
  }

  return (
    <ConnectionProvider endpoint={endpoint}>
      <WalletProvider wallets={wallets} onError={onError} autoConnect={shouldAutoConnect}>
        <WalletModalProvider>
          <EVMWalletProvider>
            <AuthProvider>
            <BrowserRouter>
              <RouteAnalytics />
              {/* PrivateAccessGate lifted — site is now fully public.
                  To re-gate, wrap the <div> below in <PrivateAccessGate>
                  … </PrivateAccessGate> and update the password in
                  components/PrivateAccessGate.js. Import is kept so the
                  re-enable is a one-line change. */}
              <div className="min-h-screen bg-[#05050A] text-white relative overflow-x-hidden">
                  <Navbar />
                  <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/origins" element={<Lore />} />
                  {/* Legacy `/lore` URL — kept as a permanent redirect
                      so bookmarks, socials, and outbound links from
                      earlier drops still land on the Origins page. */}
                  <Route path="/lore" element={<Navigate to="/origins" replace />} />
                  <Route path="/archive" element={<Archive />} />
                  <Route path="/companion" element={<Companion />} />
                  <Route path="/pugburn" element={<PugBurn />} />
                  <Route path="/forum" element={<Forum />} />
                  <Route path="/shop" element={<Shop />} />
                  <Route path="/wallet" element={<WalletDashboard />} />
                  {/* Archived routes (moved to /archived/ on 10 Sep 2026):
                        /betting  → Pug Pit (BettingArena)
                        /game     → Cosmic Runner (SpeedRunGame)
                        /game/3d  → Cosmic Runner 3D (Phase1Runner3D)
                        /nft      → NFTGallery (Q4 2026 preview placeholder)
                        /showcase → Skin Showcase
                      To re-enable, restore the files from /archived/ and
                      re-add the imports + Route entries above. */}
                  <Route path="/admin" element={<AdminAuthGate title="Operator Console"><AdminPanel /></AdminAuthGate>} />
                  <Route path="/admin/drops" element={<AdminAuthGate title="Drop Vault"><AdminDropVault /></AdminAuthGate>} />
                  <Route path="/admin/companions" element={<AdminAuthGate title="Companion Tokens"><AdminCompanionTokens /></AdminAuthGate>} />
                  <Route path="/admin/canon" element={<AdminAuthGate title="Visual Canon"><AdminVisualCanon /></AdminAuthGate>} />
                  <Route path="/messages" element={<Messages />} />
                  <Route path="/profile" element={<ProfilePage />} />
                </Routes>
                <Footer />
                {/* The floating Tinkerpug chat widget has moved to
                    /archive (Phase B of the Archive feature). Import
                    kept so a re-enable is trivial: render
                    <EnhancedAIAssistant /> here again. */}
                <NotificationPermissionPrompt />
                {/* WhatsNewToast + BigWinToast removed — BigWinToast was
                    archived with the Pug Pit stack (10 Sep 2026). */}
                <Toaster theme="dark" />
              </div>
            </BrowserRouter>
            </AuthProvider>
          </EVMWalletProvider>
        </WalletModalProvider>
      </WalletProvider>
    </ConnectionProvider>
  );
}

export default App;
