/**
 * PugBurn - Solana Account Cleanup & SOL Reclaim Page
 * Helps users recover SOL from empty token accounts by closing them.
 * 
 * Features:
 * - Scan wallet for vacant (empty) token accounts
 * - Display reclaimable SOL amount
 * - One-click cleanup with wallet signature
 * - Bullpug branding throughout
 */

import { useState, useEffect, useCallback } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { PublicKey, Transaction } from "@solana/web3.js";
import { TOKEN_PROGRAM_ID, createCloseAccountInstruction } from "@solana/spl-token";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import axios from "axios";
import {
  Flame, Wallet, RefreshCw, Loader2, CheckCircle, AlertTriangle,
  Trash2, Coins, ArrowRight, Info, Sparkles, Shield, Clock
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BULLPUG_LOGO = "https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png";

export default function PugBurn() {
  const { publicKey, connected, signTransaction } = useWallet();
  const { connection } = useConnection();
  const walletAddress = publicKey?.toString();

  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [selectedAccounts, setSelectedAccounts] = useState([]);
  const [cleaning, setCleaning] = useState(false);
  const [cleanupComplete, setCleanupComplete] = useState(false);

  // Auto-scan when wallet connects
  useEffect(() => {
    if (connected && walletAddress) {
      scanWallet();
    } else {
      setScanResult(null);
      setSelectedAccounts([]);
    }
  }, [connected, walletAddress]);

  // Scan wallet for vacant accounts
  const scanWallet = async () => {
    if (!walletAddress) return;
    
    setScanning(true);
    setScanResult(null);
    setSelectedAccounts([]);
    setCleanupComplete(false);
    
    try {
      const { data } = await axios.get(`${API}/pugburn/scan/${walletAddress}`);
      setScanResult(data);
      
      // Auto-select all vacant accounts
      if (data.vacant_accounts?.length > 0) {
        setSelectedAccounts(data.vacant_accounts.map(a => a.address));
        toast.success(`Found ${data.vacant_accounts.length} vacant accounts!`);
      } else {
        toast.info("No vacant accounts found - your wallet is clean!");
      }
    } catch (e) {
      console.error("Scan error:", e);
      toast.error("Failed to scan wallet");
    }
    
    setScanning(false);
  };

  // Toggle account selection
  const toggleAccount = (address) => {
    setSelectedAccounts(prev => 
      prev.includes(address)
        ? prev.filter(a => a !== address)
        : [...prev, address]
    );
  };

  // Select/deselect all
  const toggleAll = () => {
    if (selectedAccounts.length === scanResult?.vacant_accounts?.length) {
      setSelectedAccounts([]);
    } else {
      setSelectedAccounts(scanResult.vacant_accounts.map(a => a.address));
    }
  };

  // Execute cleanup - close selected accounts
  const executeCleanup = async () => {
    if (!signTransaction || !connection || selectedAccounts.length === 0) {
      toast.error("Cannot proceed - check wallet connection");
      return;
    }

    setCleaning(true);
    
    try {
      // Build close account instructions
      const transaction = new Transaction();
      const owner = publicKey;
      
      // Process in batches of 10 to avoid transaction size limits
      const batchSize = 10;
      const accountBatches = [];
      
      for (let i = 0; i < selectedAccounts.length; i += batchSize) {
        accountBatches.push(selectedAccounts.slice(i, i + batchSize));
      }
      
      let totalReclaimed = 0;
      let successCount = 0;
      
      for (const batch of accountBatches) {
        const batchTransaction = new Transaction();
        
        for (const accountAddress of batch) {
          try {
            const accountPubkey = new PublicKey(accountAddress);
            
            // Create close account instruction
            // Closing sends rent SOL to the owner
            const closeInstruction = createCloseAccountInstruction(
              accountPubkey,  // Account to close
              owner,          // Destination for rent SOL
              owner,          // Owner/authority
              [],             // No multi-signers
              TOKEN_PROGRAM_ID
            );
            
            batchTransaction.add(closeInstruction);
          } catch (e) {
            console.error(`Error creating instruction for ${accountAddress}:`, e);
          }
        }
        
        if (batchTransaction.instructions.length === 0) continue;
        
        // Get recent blockhash
        const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash();
        batchTransaction.recentBlockhash = blockhash;
        batchTransaction.feePayer = owner;
        
        // Sign and send
        const signedTx = await signTransaction(batchTransaction);
        const txSignature = await connection.sendRawTransaction(signedTx.serialize(), {
          skipPreflight: false,
          preflightCommitment: "confirmed"
        });
        
        // Wait for confirmation
        await connection.confirmTransaction({
          signature: txSignature,
          blockhash,
          lastValidBlockHeight
        });
        
        successCount += batch.length;
        totalReclaimed += batch.length * 0.00203928; // Approximate rent per account
        
        toast.success(
          <div>
            <p className="font-bold">Batch closed!</p>
            <p className="text-xs">
              <a 
                href={`https://solscan.io/tx/${txSignature}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#00FFA3] hover:underline"
              >
                View on Solscan →
              </a>
            </p>
          </div>
        );
      }
      
      setCleanupComplete(true);
      setScanResult(prev => ({
        ...prev,
        vacant_accounts: prev.vacant_accounts.filter(a => !selectedAccounts.includes(a.address)),
        total_reclaimable_sol: 0
      }));
      setSelectedAccounts([]);
      
      toast.success(
        <div>
          <p className="font-bold text-[#00FFA3]">Cleanup Complete!</p>
          <p className="text-sm">Closed {successCount} accounts</p>
          <p className="text-sm">Reclaimed ~{totalReclaimed.toFixed(4)} SOL</p>
        </div>,
        { duration: 10000 }
      );
      
    } catch (e) {
      console.error("Cleanup error:", e);
      const errorMsg = e.message || "Cleanup failed";
      
      if (errorMsg.includes("User rejected")) {
        toast.info("Transaction cancelled by user");
      } else {
        toast.error(
          <div>
            <p className="font-bold">Cleanup Failed</p>
            <p className="text-xs">{errorMsg}</p>
          </div>
        );
      }
    }
    
    setCleaning(false);
  };

  // Not connected view
  if (!connected) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] text-white pt-24 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <div className="relative inline-block mb-6">
            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-[#FF6B6B] to-[#FF8C00] p-1 shadow-lg shadow-[#FF6B6B]/30">
              <div className="w-full h-full rounded-xl bg-[#0A0A0F] flex items-center justify-center">
                <Flame className="w-12 h-12 text-[#FF6B6B]" />
              </div>
            </div>
            <img 
              src={BULLPUG_LOGO} 
              alt="Bullpug" 
              className="absolute -bottom-2 -right-2 w-10 h-10 rounded-full ring-2 ring-[#0A0A0F]"
            />
          </div>
          
          <h1 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Orbitron' }}>
            Pug<span className="text-[#FF6B6B]">Burn</span>
          </h1>
          <p className="text-lg text-slate-400 mb-2">Solana Account Cleanup</p>
          <p className="text-slate-500 mb-8 max-w-md mx-auto">
            Reclaim SOL locked in empty token accounts. Every closed account returns ~0.002 SOL to your wallet.
          </p>
          
          <Link to="/">
            <Button className="bg-gradient-to-r from-[#FF6B6B] to-[#FF8C00] px-8 py-6 text-lg font-bold rounded-xl hover:opacity-90">
              <Wallet className="w-5 h-5 mr-2" />
              Connect Wallet to Start
            </Button>
          </Link>
          
          {/* Feature cards */}
          <div className="grid md:grid-cols-3 gap-4 mt-12">
            <div className="bg-white/5 rounded-xl p-5 border border-white/10">
              <Coins className="w-8 h-8 text-[#00FFA3] mb-3" />
              <h3 className="font-bold mb-2">Reclaim SOL</h3>
              <p className="text-sm text-slate-400">Get back ~0.002 SOL for each empty account closed</p>
            </div>
            <div className="bg-white/5 rounded-xl p-5 border border-white/10">
              <Sparkles className="w-8 h-8 text-[#D946EF] mb-3" />
              <h3 className="font-bold mb-2">Clean Wallet</h3>
              <p className="text-sm text-slate-400">Remove clutter from airdrops and old tokens</p>
            </div>
            <div className="bg-white/5 rounded-xl p-5 border border-white/10">
              <Shield className="w-8 h-8 text-[#00C2FF] mb-3" />
              <h3 className="font-bold mb-2">Safe & Secure</h3>
              <p className="text-sm text-slate-400">Only closes empty accounts - your tokens are safe</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-white pt-20 pb-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#FF6B6B] to-[#FF8C00] p-0.5 shadow-lg shadow-[#FF6B6B]/20">
                <div className="w-full h-full rounded-xl bg-[#0A0A0F] flex items-center justify-center">
                  <Flame className="w-7 h-7 text-[#FF6B6B]" />
                </div>
              </div>
              <img 
                src={BULLPUG_LOGO} 
                alt="Bullpug" 
                className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full ring-2 ring-[#0A0A0F]"
              />
            </div>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2" style={{ fontFamily: 'Orbitron' }}>
                Pug<span className="text-[#FF6B6B]">Burn</span>
                <span className="px-2 py-0.5 text-[10px] bg-[#FF6B6B]/20 text-[#FF6B6B] rounded-full font-normal">
                  Powered by Bullpug
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Solana Account Cleanup & SOL Reclaim
              </p>
            </div>
          </div>
          
          <Button
            onClick={scanWallet}
            disabled={scanning}
            className="bg-gradient-to-r from-[#FF6B6B] to-[#FF8C00] hover:opacity-90"
            data-testid="scan-wallet-btn"
          >
            {scanning ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            {scanning ? "Scanning..." : "Scan Wallet"}
          </Button>
        </div>

        {/* Info Banner */}
        <div className="bg-gradient-to-r from-[#FF6B6B]/10 to-[#FF8C00]/10 rounded-xl p-4 mb-6 border border-[#FF6B6B]/20">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-[#FF6B6B] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-slate-300">
                <span className="font-bold text-white">How it works:</span> When you receive tokens on Solana, 
                a small amount of SOL (~0.002) is reserved as "rent" for each token account. 
                When those accounts are empty, you can close them and reclaim that SOL!
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Only empty accounts are shown. Your tokens and balances are completely safe.
              </p>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {scanning && (
          <div className="text-center py-20">
            <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-[#FF6B6B]" />
            <p className="text-slate-400">Scanning your wallet for empty accounts...</p>
            <p className="text-xs text-slate-500 mt-2">This may take a moment</p>
          </div>
        )}

        {/* Results */}
        {!scanning && scanResult && (
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard 
                icon={<Wallet className="w-5 h-5" />}
                label="Total Accounts"
                value={scanResult.total_accounts_scanned}
                color="#00C2FF"
              />
              <StatCard 
                icon={<Trash2 className="w-5 h-5" />}
                label="Empty Accounts"
                value={scanResult.vacant_accounts?.length || 0}
                color="#FF6B6B"
              />
              <StatCard 
                icon={<Coins className="w-5 h-5" />}
                label="Reclaimable SOL"
                value={`~${scanResult.total_reclaimable_sol?.toFixed(4) || 0}`}
                color="#00FFA3"
              />
              <StatCard 
                icon={<Clock className="w-5 h-5" />}
                label="Last Scan"
                value={new Date(scanResult.scan_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                color="#D946EF"
              />
            </div>

            {/* Cleanup Complete Banner */}
            {cleanupComplete && (
              <div className="bg-[#00FFA3]/10 rounded-xl p-6 border border-[#00FFA3]/30 text-center">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-[#00FFA3]" />
                <h3 className="text-xl font-bold text-[#00FFA3] mb-2">Cleanup Complete!</h3>
                <p className="text-slate-400">Your wallet is now squeaky clean.</p>
              </div>
            )}

            {/* Vacant Accounts List */}
            {scanResult.vacant_accounts?.length > 0 && !cleanupComplete && (
              <div className="bg-white/5 rounded-2xl border border-white/10 overflow-hidden">
                {/* Header */}
                <div className="p-4 border-b border-white/10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={toggleAll}
                      className="w-5 h-5 rounded border border-white/30 flex items-center justify-center hover:border-[#FF6B6B] transition-colors"
                      data-testid="select-all-btn"
                    >
                      {selectedAccounts.length === scanResult.vacant_accounts.length && (
                        <CheckCircle className="w-4 h-4 text-[#00FFA3]" />
                      )}
                    </button>
                    <span className="text-sm text-slate-400">
                      {selectedAccounts.length} of {scanResult.vacant_accounts.length} selected
                    </span>
                  </div>
                  
                  <Button
                    onClick={executeCleanup}
                    disabled={cleaning || selectedAccounts.length === 0}
                    className="bg-gradient-to-r from-[#FF6B6B] to-[#FF8C00] hover:opacity-90 disabled:opacity-50"
                    data-testid="cleanup-btn"
                  >
                    {cleaning ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Flame className="w-4 h-4 mr-2" />
                    )}
                    {cleaning ? "Burning..." : `Burn ${selectedAccounts.length} Accounts`}
                  </Button>
                </div>

                {/* Account List */}
                <div className="divide-y divide-white/5 max-h-[400px] overflow-y-auto">
                  {scanResult.vacant_accounts.map((account, idx) => (
                    <div 
                      key={account.address}
                      className={`p-4 flex items-center gap-4 hover:bg-white/5 transition-colors ${
                        selectedAccounts.includes(account.address) ? 'bg-[#FF6B6B]/5' : ''
                      }`}
                      onClick={() => toggleAccount(account.address)}
                      data-testid={`account-${idx}`}
                    >
                      <button
                        className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                          selectedAccounts.includes(account.address)
                            ? 'border-[#00FFA3] bg-[#00FFA3]/20'
                            : 'border-white/30'
                        }`}
                      >
                        {selectedAccounts.includes(account.address) && (
                          <CheckCircle className="w-4 h-4 text-[#00FFA3]" />
                        )}
                      </button>
                      
                      <div className="flex-1 min-w-0">
                        <p className="font-mono text-sm text-white truncate">
                          {account.address}
                        </p>
                        <p className="text-xs text-slate-500">
                          Mint: {account.mint?.slice(0, 8)}...{account.mint?.slice(-6)}
                        </p>
                      </div>
                      
                      <div className="text-right">
                        <p className="text-sm font-mono text-[#00FFA3]">
                          +{account.rent_recoverable?.toFixed(4)} SOL
                        </p>
                        <p className="text-xs text-slate-500">reclaimable</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Footer with total */}
                <div className="p-4 border-t border-white/10 bg-black/20 flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    Total reclaimable from selected:
                  </span>
                  <span className="text-lg font-bold text-[#00FFA3]">
                    ~{(selectedAccounts.length * 0.00203928).toFixed(4)} SOL
                  </span>
                </div>
              </div>
            )}

            {/* No vacant accounts */}
            {scanResult.vacant_accounts?.length === 0 && !cleanupComplete && (
              <div className="text-center py-16 bg-white/5 rounded-2xl border border-white/10">
                <CheckCircle className="w-16 h-16 mx-auto mb-4 text-[#00FFA3]" />
                <h3 className="text-xl font-bold mb-2">Your Wallet is Clean!</h3>
                <p className="text-slate-400 mb-4">
                  No empty token accounts found. Nothing to reclaim.
                </p>
                <Link to="/ai-trader">
                  <Button className="bg-gradient-to-r from-[#D946EF] to-[#00FFA3]">
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Go to Trading Bot
                  </Button>
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Initial state - no scan yet */}
        {!scanning && !scanResult && (
          <div className="text-center py-16 bg-white/5 rounded-2xl border border-white/10">
            <Flame className="w-16 h-16 mx-auto mb-4 text-[#FF6B6B]/50" />
            <h3 className="text-xl font-bold mb-2">Ready to Clean Up?</h3>
            <p className="text-slate-400 mb-6 max-w-md mx-auto">
              Click "Scan Wallet" to find empty token accounts and see how much SOL you can reclaim.
            </p>
            <Button
              onClick={scanWallet}
              className="bg-gradient-to-r from-[#FF6B6B] to-[#FF8C00] px-8 py-6 text-lg"
            >
              <RefreshCw className="w-5 h-5 mr-2" />
              Scan My Wallet
            </Button>
          </div>
        )}

        {/* Warning */}
        <div className="mt-8 p-4 bg-[#F5D300]/5 rounded-xl border border-[#F5D300]/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-[#F5D300] flex-shrink-0" />
            <div className="text-sm">
              <p className="text-[#F5D300] font-medium mb-1">Important Notice</p>
              <p className="text-slate-400">
                Only <span className="text-white">empty</span> token accounts (0 balance) are shown and can be closed. 
                This is a safe operation and won't affect any tokens you own. 
                Closing an account is <span className="text-white">permanent</span> - if you receive that token again, 
                a new account will be created automatically.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({ icon, label, value, color }) {
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
      <div className="flex items-center gap-2 text-slate-400 mb-2">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-xl font-bold" style={{ color }}>{value}</p>
    </div>
  );
}
