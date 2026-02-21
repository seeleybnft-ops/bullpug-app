import { useMemo } from "react";
import "@/App.css";
import "@/i18n/config"; // Initialize i18n
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ConnectionProvider, WalletProvider } from "@solana/wallet-adapter-react";
import { WalletModalProvider } from "@solana/wallet-adapter-react-ui";
import { PhantomWalletAdapter, SolflareWalletAdapter } from "@solana/wallet-adapter-wallets";
import { clusterApiUrl } from "@solana/web3.js";
import { Toaster } from "@/components/ui/sonner";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import HomePage from "@/pages/HomePage";
import BettingArena from "@/pages/BettingArena";
import Shop from "@/pages/Shop";
import ExitSimulator from "@/pages/ExitSimulator";
import NFTGallery from "@/pages/NFTGallery";
import WalletDashboard from "@/pages/WalletDashboard";
import SpeedRunGame from "@/pages/SpeedRunGame";
import ReflectionsCalculator from "@/pages/ReflectionsCalculator";
import TradingJournal from "@/pages/TradingJournal";
import Forum from "@/pages/Forum";
import AdminPanel from "@/pages/AdminPanel";
import Messages from "@/pages/Messages";
import Showcase from "@/pages/Showcase";
import ProfilePage from "@/pages/ProfilePage";
import Lore from "@/pages/Lore";

function App() {
  const endpoint = useMemo(
    () => process.env.REACT_APP_SOLANA_RPC_URL || clusterApiUrl('mainnet-beta'),
    []
  );

  const wallets = useMemo(
    () => [new PhantomWalletAdapter(), new SolflareWalletAdapter()],
    []
  );

  return (
    <ConnectionProvider endpoint={endpoint}>
      <WalletProvider wallets={wallets} autoConnect>
        <WalletModalProvider>
          <BrowserRouter>
            <div className="min-h-screen bg-[#05050A] text-white relative overflow-x-hidden">
              <Navbar />
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/lore" element={<Lore />} />
                <Route path="/journal" element={<TradingJournal />} />
                <Route path="/exit-simulator" element={<ExitSimulator />} />
                <Route path="/game" element={<SpeedRunGame />} />
                <Route path="/betting" element={<BettingArena />} />
                <Route path="/reflections" element={<ReflectionsCalculator />} />
                <Route path="/forum" element={<Forum />} />
                <Route path="/shop" element={<Shop />} />
                <Route path="/nft" element={<NFTGallery />} />
                <Route path="/wallet" element={<WalletDashboard />} />
                <Route path="/admin" element={<AdminPanel />} />
                <Route path="/messages" element={<Messages />} />
                <Route path="/showcase" element={<Showcase />} />
                <Route path="/showcase/:walletAddress" element={<Showcase />} />
                <Route path="/profile" element={<ProfilePage />} />
              </Routes>
              <Footer />
              <Toaster theme="dark" />
            </div>
          </BrowserRouter>
        </WalletModalProvider>
      </WalletProvider>
    </ConnectionProvider>
  );
}

export default App;
