import { useMemo, useEffect, useState } from "react";
import "@/App.css";
import "@/i18n/config"; // Initialize i18n
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ConnectionProvider, WalletProvider } from "@solana/wallet-adapter-react";
import { WalletModalProvider } from "@solana/wallet-adapter-react-ui";
import { PhantomWalletAdapter } from "@solana/wallet-adapter-phantom";
import { SolflareWalletAdapter } from "@solana/wallet-adapter-solflare";
import { clusterApiUrl } from "@solana/web3.js";
import { Toaster } from "@/components/ui/sonner";
import { EVMWalletProvider } from "@/providers/EVMWalletProvider";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import EnhancedAIAssistant from "@/components/EnhancedAIAssistant";
import PrivateAccessGate from "@/components/PrivateAccessGate";
import HomePage from "@/pages/HomePage";
import BettingArena from "@/pages/BettingArena";
import Shop from "@/pages/Shop";
import NFTGallery from "@/pages/NFTGallery";
import WalletDashboard from "@/pages/WalletDashboard";
import SpeedRunGame from "@/pages/SpeedRunGame";
import Phase1Runner3D from "@/pages/Phase1Runner3D";
import Portfolio from "@/pages/Portfolio";
import Forum from "@/pages/Forum";
import AdminPanel from "@/pages/AdminPanel";
import AdminDropVault from "@/pages/AdminDropVault";
import AdminAuthGate from "@/components/AdminAuthGate";
import BigWinToast from "@/components/BigWinToast";
import NotificationPermissionPrompt from "@/components/NotificationPermissionPrompt";
import WhatsNewToast from "@/components/WhatsNewToast";
import Messages from "@/pages/Messages";
import Showcase from "@/pages/Showcase";
import ProfilePage from "@/pages/ProfilePage";
import Lore from "@/pages/Lore";
import PugBurn from "@/pages/PugBurn";

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
            <PrivateAccessGate>
              <BrowserRouter>
                <div className="min-h-screen bg-[#05050A] text-white relative overflow-x-hidden">
                  <Navbar />
                  <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/lore" element={<Lore />} />
                  <Route path="/game" element={<SpeedRunGame />} />
                  <Route path="/game/3d" element={<Phase1Runner3D />} />
                  <Route path="/pugburn" element={<PugBurn />} />
                  <Route path="/betting" element={<BettingArena />} />
                  <Route path="/forum" element={<Forum />} />
                  <Route path="/shop" element={<Shop />} />
                  <Route path="/nft" element={<NFTGallery />} />
                  <Route path="/wallet" element={<WalletDashboard />} />
                  <Route path="/admin" element={<AdminAuthGate title="Operator Console"><AdminPanel /></AdminAuthGate>} />
                  <Route path="/admin/drops" element={<AdminAuthGate title="Drop Vault"><AdminDropVault /></AdminAuthGate>} />
                  <Route path="/messages" element={<Messages />} />
                  <Route path="/showcase" element={<Showcase />} />
                  <Route path="/showcase/:walletAddress" element={<Showcase />} />
                  <Route path="/profile" element={<ProfilePage />} />
                </Routes>
                <Footer />
                <EnhancedAIAssistant />
                <BigWinToast />
                <NotificationPermissionPrompt />
                <WhatsNewToast />
                <Toaster theme="dark" />
              </div>
            </BrowserRouter>
          </PrivateAccessGate>
          </EVMWalletProvider>
        </WalletModalProvider>
      </WalletProvider>
    </ConnectionProvider>
  );
}

export default App;
