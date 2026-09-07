/**
 * Unified Wallet Connect Button
 * 
 * Single button that opens a modal to connect either Solana or EVM wallets.
 * Shows connected status for both wallet types.
 * Enhanced for Phantom in-app browser compatibility.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import bs58 from 'bs58';
import { useWallet } from '@solana/wallet-adapter-react';
import { useWalletModal } from '@solana/wallet-adapter-react-ui';
import { useAccount, useConnect, useDisconnect, useChainId, useSwitchChain } from 'wagmi';
import { Button } from '@/components/ui/button';
import {
  Wallet, ChevronDown, LogOut, ExternalLink, Check, Loader2,
  Copy, X, Zap, AlertCircle, Mail, ArrowLeft, ShieldCheck, Link2,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import AccountMergeModal from '@/components/AccountMergeModal';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Chain configurations
const EVM_CHAINS = [
  { id: 1, name: 'Ethereum', icon: '⟠', color: '#627EEA' },
  { id: 8453, name: 'Base', icon: '🔵', color: '#0052FF' },
  { id: 42161, name: 'Arbitrum', icon: '🔷', color: '#28A0F0' },
];

// Detect if running inside Phantom's in-app browser (mobile only)
const isPhantomBrowser = () => {
  if (typeof window === 'undefined') return false;
  const userAgent = navigator.userAgent || '';
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
  // Only detect as Phantom browser if mobile AND has Phantom in user agent
  return isMobile && userAgent.includes('Phantom');
};

// Check if Phantom extension is available (desktop or mobile)
const isPhantomAvailable = () => {
  if (typeof window === 'undefined') return false;
  return window.phantom?.solana || window.solana?.isPhantom;
};

export default function UnifiedWalletButton() {
  const [showModal, setShowModal] = useState(false);
  const [copied, setCopied] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const modalRef = useRef(null);

  // Email auth (Phase B) — the modal has three states:
  //   • "idle"   — email input visible
  //   • "otp"    — user has requested a code, show 6-digit input
  //   • "signed" — user is already signed in with email; show shorthand + sign out
  const {
    email: signedInEmail,
    sessionType,
    signInWithJwt,
    signOut,
    linkedWallet,
    authHeaders,
    refreshEmailUser,
  } = useAuth();
  const [emailInput, setEmailInput] = useState('');
  const [emailStage, setEmailStage] = useState('idle'); // 'idle' | 'otp'
  const [emailSubmitting, setEmailSubmitting] = useState(false);
  const [emailError, setEmailError] = useState(null);
  const [otpDigits, setOtpDigits] = useState(Array(6).fill(''));
  const [otpSubmitting, setOtpSubmitting] = useState(false);
  const otpInputsRef = useRef([]);

  // Wallet-link (Phase C) — auto-triggered when an email-signed user
  // connects a Solana wallet that isn't already tied to their record.
  //   idle → signing → linking → (success | error | merge)
  const [linkStage, setLinkStage] = useState('idle');
  const [linkError, setLinkError] = useState(null);
  const [mergeInfo, setMergeInfo] = useState(null);
  const linkAttemptedRef = useRef(null); // wallet-address we last tried, to avoid loops

  // Solana wallet
  const { 
    publicKey: solanaPublicKey, 
    connected: solanaConnected, 
    disconnect: solanaDisconnect, 
    wallet: solanaWallet,
    select: selectWallet,
    wallets,
    connect: walletConnect,
    signMessage: solanaSignMessage,
  } = useWallet();
  const { setVisible: setSolanaModalVisible } = useWalletModal();

  // EVM wallet
  const { address: evmAddress, isConnected: evmConnected } = useAccount();
  const { connectors, connect: evmConnect, isPending: evmConnecting } = useConnect();
  const { disconnect: evmDisconnect } = useDisconnect();
  const evmChainId = useChainId();
  const { switchChain } = useSwitchChain();

  const currentChain = EVM_CHAINS.find(c => c.id === evmChainId) || EVM_CHAINS[0];

  // Close modal on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        setShowModal(false);
      }
    };
    if (showModal) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showModal]);

  // ── Wallet linking (Phase C) ──────────────────────────────────────
  // When an email user connects a Solana wallet that isn't already
  // linked to their record, run SIWS + POST /auth/wallet/link. On
  // merge_required we surface <AccountMergeModal /> globally so the
  // user picks which record survives.
  const runWalletLink = useCallback(async (walletAddr) => {
    if (!solanaSignMessage) {
      setLinkStage('error');
      setLinkError('this wallet does not support message signing.');
      return;
    }
    setLinkStage('signing');
    setLinkError(null);
    try {
      const nonceRes = await axios.post(`${API}/admin-auth/nonce`, { wallet: walletAddr });
      const { message } = nonceRes.data;
      const encoded = new TextEncoder().encode(message);
      const sigBytes = await solanaSignMessage(encoded);
      const signature = bs58.encode(sigBytes);

      setLinkStage('linking');
      const linkRes = await axios.post(
        `${API}/auth/wallet/link`,
        { wallet: walletAddr, message, signature },
        { headers: authHeaders },
      );

      if (linkRes.data?.merge_required) {
        setMergeInfo({
          email_user_id: linkRes.data.email_user_id,
          wallet_user_id: linkRes.data.wallet_user_id,
          email: linkRes.data.email,
          wallet: linkRes.data.wallet,
        });
        setLinkStage('merge');
        return;
      }

      setLinkStage('success');
      refreshEmailUser();
      // Keep the success banner visible for 4s — long enough for the
      // keeper's-log line to register, short enough it doesn't linger.
      setTimeout(() => setLinkStage('idle'), 4000);
    } catch (e) {
      // If the user rejected the signature we shouldn't treat it as a
      // hard failure — keep the wallet connected, just clear the ref
      // so they can retry manually.
      const rejected = e?.name === 'WalletSignMessageError' || /reject|denied/i.test(e?.message || '');
      const detail = e?.response?.data?.detail || e?.message || 'could not link wallet.';
      setLinkStage(rejected ? 'idle' : 'error');
      setLinkError(rejected ? null : detail);
      linkAttemptedRef.current = null;
    }
  }, [solanaSignMessage, authHeaders, refreshEmailUser]);

  useEffect(() => {
    // Preconditions: email session + a freshly connected Solana wallet
    // that isn't already the linked one and hasn't been attempted this
    // session.
    if (sessionType !== 'email') return;
    if (!solanaConnected || !solanaPublicKey) return;
    const addr = solanaPublicKey.toBase58();
    if (linkedWallet && linkedWallet === addr) return;
    if (linkAttemptedRef.current === addr) return;
    if (linkStage !== 'idle' && linkStage !== 'error') return;
    linkAttemptedRef.current = addr;
    runWalletLink(addr);
  }, [sessionType, solanaConnected, solanaPublicKey, linkedWallet, linkStage, runWalletLink]);

  const dismissMerge = () => {
    setMergeInfo(null);
    setLinkStage('idle');
    // Clear the attempt ref so the user could retry linking later if
    // they cancel out of the merge modal.
    linkAttemptedRef.current = null;
  };

  const formatAddress = (addr, length = 4) => {
    if (!addr) return '';
    return `${addr.slice(0, length + 2)}...${addr.slice(-length)}`;
  };

  const copyAddress = (address, type) => {
    navigator.clipboard.writeText(address);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };

  // Handle Solana wallet connection - use wallet adapter modal
  const handleSolanaConnect = useCallback(() => {
    // Simply open the wallet adapter modal - it handles everything properly
    setSolanaModalVisible(true);
    setShowModal(false);
  }, [setSolanaModalVisible]);

  // ── Email OTP request ──────────────────────────────────────────────
  const requestEmailOtp = async (e) => {
    e?.preventDefault?.();
    const cleaned = emailInput.trim().toLowerCase();
    if (!cleaned || !cleaned.includes('@')) {
      setEmailError("that doesn't look like an email.");
      return;
    }
    setEmailSubmitting(true);
    setEmailError(null);
    try {
      await axios.post(
        `${API}/auth/email/request`,
        { email: cleaned },
        { headers: { 'X-Bullpug-CSRF': '1' } },
      );
      setEmailStage('otp');
      // Focus digit 0 on the next tick after the render.
      setTimeout(() => otpInputsRef.current[0]?.focus(), 20);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setEmailError(detail || 'could not send an access code. try again shortly.');
    } finally {
      setEmailSubmitting(false);
    }
  };

  // ── OTP entry helpers ──────────────────────────────────────────────
  const setOtpDigit = (i, val) => {
    setEmailError(null);
    const only = (val || '').replace(/\D/g, '').slice(0, 1);
    setOtpDigits((prev) => {
      const next = [...prev];
      next[i] = only;
      return next;
    });
    if (only && i < 5) otpInputsRef.current[i + 1]?.focus();
  };
  const onOtpKeyDown = (e, i) => {
    if (e.key === 'Backspace' && !otpDigits[i] && i > 0) {
      otpInputsRef.current[i - 1]?.focus();
    }
  };
  const onOtpPaste = (e) => {
    const pasted = (e.clipboardData?.getData('text') || '').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;
    e.preventDefault();
    const next = Array(6).fill('');
    for (let k = 0; k < pasted.length; k++) next[k] = pasted[k];
    setOtpDigits(next);
    otpInputsRef.current[Math.min(pasted.length, 5)]?.focus();
  };

  const verifyEmailOtp = async () => {
    const code = otpDigits.join('');
    if (code.length !== 6 || !/^\d{6}$/.test(code) || otpSubmitting) return;
    setOtpSubmitting(true);
    setEmailError(null);
    try {
      const { data } = await axios.post(
        `${API}/auth/email/verify`,
        { email: emailInput.trim().toLowerCase(), otp: code },
        { headers: { 'X-Bullpug-CSRF': '1' } },
      );
      signInWithJwt(data.token);
      toast.success('signed in — the Archive is open.');
      // Reset modal state so the next open is fresh.
      setShowModal(false);
      setEmailStage('idle');
      setEmailInput('');
      setOtpDigits(Array(6).fill(''));
    } catch (err) {
      const detail = err?.response?.data?.detail || "couldn't verify. try again.";
      setEmailError(detail);
      setOtpDigits(Array(6).fill(''));
      otpInputsRef.current[0]?.focus();
    } finally {
      setOtpSubmitting(false);
    }
  };

  const handleEmailSignOut = () => {
    signOut();
    toast.success('signed out.');
  };

  // ── Button-state helpers ───────────────────────────────────────────
  const emailConnected = sessionType === 'email';

  const hasAnyWallet = solanaConnected || evmConnected;
  // Include email sessions in the "connected" count so an email-only
  // signed-in user still sees "1 Connected" instead of "Connect Wallet".
  const connectedCount =
    (solanaConnected ? 1 : 0) + (evmConnected ? 1 : 0) + (emailConnected ? 1 : 0);
  const anyIdentity = hasAnyWallet || emailConnected;

  // Check if we're in Phantom browser for UI hints
  const inPhantomBrowser = isPhantomBrowser();

  return (
    <div className="relative">
      {/* Main Button */}
      <Button
        onClick={() => setShowModal(!showModal)}
        data-testid="unified-wallet-btn"
        className={`font-bold rounded-full px-4 py-2 text-xs transition-all ${
          anyIdentity
            ? 'bg-gradient-to-r from-[#00C2FF] to-[#00FFA3] text-black hover:opacity-90'
            : 'bg-[#00FFA3] hover:bg-[#00FFA3]/80 text-black'
        }`}
      >
        <Wallet className="w-4 h-4 mr-2" />
        {anyIdentity ? (
          <>
            {connectedCount} Connected
            <ChevronDown className={`w-3 h-3 ml-1 transition-transform ${showModal ? 'rotate-180' : ''}`} />
          </>
        ) : (
          'Sign In'
        )}
      </Button>

      {/* Modal */}
      {showModal && (
        <div 
          ref={modalRef}
          className="absolute right-0 mt-2 w-80 bg-[#0a0a12] border border-white/10 rounded-2xl shadow-2xl z-50 flex flex-col max-h-[85vh] overflow-hidden"
        >
          {/* Header */}
          <div className="p-4 border-b border-white/5 flex items-center justify-between">
            <h3 className="font-bold text-white text-sm">Sign in to Bullpug</h3>
            <button 
              onClick={() => setShowModal(false)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Phantom browser notice */}
          {inPhantomBrowser && !solanaConnected && (
            <div className="mx-4 mt-3 p-2 bg-[#9945FF]/10 border border-[#9945FF]/30 rounded-lg">
              <p className="text-[10px] text-[#9945FF] flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Phantom browser detected - tap below to connect
              </p>
            </div>
          )}

          <div className="p-4 space-y-4 overflow-y-auto flex-1 min-h-0">
            {/* Email Section (Phase B — email first per UX spec) */}
            <div className="space-y-2" data-testid="unified-auth-email-section">
              <div className="flex items-center gap-2 text-xs text-slate-400 uppercase font-bold">
                <span className="text-[#B47CFF]"><Mail className="w-3 h-3" /></span> Email
                {emailConnected && <Check className="w-3 h-3 text-[#00FFA3]" />}
              </div>

              {emailConnected ? (
                <div
                  className="bg-[#B47CFF]/10 border border-[#B47CFF]/30 rounded-xl p-3 flex items-center justify-between"
                  data-testid="unified-auth-email-connected"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <ShieldCheck className="w-4 h-4 text-[#B47CFF] shrink-0" />
                    <span
                      className="text-sm text-white truncate"
                      style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
                    >
                      {signedInEmail}
                    </span>
                  </div>
                  <button
                    onClick={handleEmailSignOut}
                    data-testid="unified-auth-email-signout"
                    className="p-1.5 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400"
                    title="Sign out of email session"
                  >
                    <LogOut className="w-3 h-3" />
                  </button>
                </div>
              ) : emailStage === 'idle' ? (
                <form onSubmit={requestEmailOtp} data-testid="unified-auth-email-form">
                  <div className="flex gap-2">
                    <input
                      type="email"
                      value={emailInput}
                      onChange={(e) => { setEmailInput(e.target.value); setEmailError(null); }}
                      placeholder="your@email.com"
                      inputMode="email"
                      autoComplete="email"
                      data-testid="unified-auth-email-input"
                      className="flex-1 min-w-0 rounded-lg px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-[#B47CFF]"
                      style={{
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                      }}
                    />
                    <button
                      type="submit"
                      disabled={emailSubmitting}
                      data-testid="unified-auth-email-submit"
                      className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest disabled:opacity-50"
                      style={{
                        background: '#B47CFF',
                        color: '#0a0a12',
                        fontFamily: 'Orbitron, sans-serif',
                      }}
                    >
                      {emailSubmitting ? <Loader2 size={11} className="animate-spin" /> : <Mail size={11} />}
                      Send code
                    </button>
                  </div>
                  {emailError && (
                    <p className="text-[10px] text-[#FF6B6B] mt-1.5" data-testid="unified-auth-email-error">
                      {emailError}
                    </p>
                  )}
                  <p className="text-[10px] text-slate-600 mt-1.5">
                    signs you into the Archive — no wallet needed.
                  </p>
                </form>
              ) : (
                // emailStage === 'otp'
                <div data-testid="unified-auth-otp-form">
                  <button
                    type="button"
                    onClick={() => { setEmailStage('idle'); setEmailError(null); setOtpDigits(Array(6).fill('')); }}
                    className="inline-flex items-center gap-1 text-[10px] uppercase tracking-widest text-slate-500 hover:text-white mb-2"
                    data-testid="unified-auth-otp-back"
                  >
                    <ArrowLeft size={10} /> different email
                  </button>
                  <p className="text-[10px] text-slate-400 mb-2">
                    6-digit code sent to <span className="text-slate-200 font-mono">{emailInput.trim().toLowerCase()}</span>
                  </p>
                  <div className="flex gap-1.5 mb-2 justify-between" onPaste={onOtpPaste}>
                    {otpDigits.map((d, i) => (
                      <input
                        key={i}
                        ref={(el) => { otpInputsRef.current[i] = el; }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={d}
                        onChange={(e) => setOtpDigit(i, e.target.value)}
                        onKeyDown={(e) => onOtpKeyDown(e, i)}
                        disabled={otpSubmitting}
                        data-testid={`unified-auth-otp-digit-${i}`}
                        className="w-10 h-11 text-center text-base font-bold rounded-lg text-white focus:outline-none focus:ring-1 focus:ring-[#B47CFF] disabled:opacity-50"
                        style={{
                          background: 'rgba(255,255,255,0.04)',
                          border: '1px solid rgba(255,255,255,0.08)',
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                        }}
                      />
                    ))}
                  </div>
                  {emailError && (
                    <p className="text-[10px] text-[#FF6B6B] mb-2" data-testid="unified-auth-otp-error">
                      {emailError}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={verifyEmailOtp}
                    disabled={otpSubmitting || otpDigits.join('').length !== 6}
                    data-testid="unified-auth-otp-verify"
                    className="w-full inline-flex items-center justify-center gap-2 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest disabled:opacity-40"
                    style={{
                      background: '#B47CFF',
                      color: '#0a0a12',
                      fontFamily: 'Orbitron, sans-serif',
                    }}
                  >
                    {otpSubmitting ? <Loader2 size={11} className="animate-spin" /> : <ShieldCheck size={11} />}
                    Verify
                  </button>
                </div>
              )}
            </div>

            {/* Divider + wallet sections are hidden while the user is
                mid-OTP entry — keeps the modal focused on the code
                they're trying to type and prevents the Verify button
                from being pushed below the viewport. */}
            {emailStage !== 'otp' && (
              <>
                {/* Divider between email and wallet options — visual break
                    that reinforces "these are two equal paths to the Archive". */}
                <div className="flex items-center gap-2 pt-1" aria-hidden="true">
                  <div className="flex-1 h-px bg-white/5" />
                  <span className="text-[9px] uppercase tracking-widest text-slate-600">or connect a wallet</span>
                  <div className="flex-1 h-px bg-white/5" />
                </div>

                {/* Solana Section */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-slate-400 uppercase font-bold">
                <span className="text-[#9945FF]">◎</span> Solana
                {solanaConnected && <Check className="w-3 h-3 text-[#00FFA3]" />}
              </div>

              {solanaConnected && solanaPublicKey ? (
                <div className="bg-[#9945FF]/10 border border-[#9945FF]/30 rounded-xl p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {solanaWallet?.adapter?.icon && (
                        <img src={solanaWallet.adapter.icon} alt="" className="w-5 h-5 rounded" />
                      )}
                      <span className="text-sm font-mono text-white">
                        {formatAddress(solanaPublicKey.toBase58())}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyAddress(solanaPublicKey.toBase58(), 'solana')}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white"
                      >
                        {copied === 'solana' ? <Check className="w-3 h-3 text-[#00FFA3]" /> : <Copy className="w-3 h-3" />}
                      </button>
                      <button
                        onClick={() => { solanaDisconnect(); }}
                        className="p-1.5 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400"
                      >
                        <LogOut className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {/* Wallet-link status (Phase C). Only surfaces for
                      email-signed users — wallet-only users don't need
                      a link since their wallet IS the identity. */}
                  {sessionType === 'email' && (
                    <div className="mt-2 pt-2 border-t border-white/5" data-testid="wallet-link-status">
                      {linkStage === 'signing' && (
                        <p className="text-[10px] text-slate-400 flex items-center gap-1.5">
                          <Loader2 className="w-3 h-3 animate-spin text-[#B47CFF]" />
                          waiting for signature…
                        </p>
                      )}
                      {linkStage === 'linking' && (
                        <p className="text-[10px] text-slate-400 flex items-center gap-1.5">
                          <Loader2 className="w-3 h-3 animate-spin text-[#B47CFF]" />
                          linking to your archive…
                        </p>
                      )}
                      {linkStage === 'success' && (
                        <p className="text-[10px] text-[#00FFA3] flex items-center gap-1.5">
                          <Link2 className="w-3 h-3" /> linked to your email account
                        </p>
                      )}
                      {linkStage === 'idle' && linkedWallet === solanaPublicKey.toBase58() && (
                        <p className="text-[10px] text-[#00FFA3] flex items-center gap-1.5">
                          <Link2 className="w-3 h-3" /> linked to your email account
                        </p>
                      )}
                      {linkStage === 'error' && linkError && (
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-[10px] text-[#FF6B6B] truncate" data-testid="wallet-link-error">
                            {linkError}
                          </p>
                          <button
                            type="button"
                            onClick={() => {
                              linkAttemptedRef.current = null;
                              setLinkStage('idle');
                              setLinkError(null);
                              runWalletLink(solanaPublicKey.toBase58());
                            }}
                            data-testid="wallet-link-retry"
                            className="text-[10px] uppercase tracking-widest text-[#B47CFF] hover:text-white"
                          >
                            retry
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <button
                  onClick={handleSolanaConnect}
                  disabled={connecting}
                  className="w-full flex items-center justify-between p-3 bg-black/30 border border-white/10 rounded-xl hover:border-[#9945FF]/50 hover:bg-[#9945FF]/5 transition-all text-left disabled:opacity-50"
                  data-testid="connect-solana-btn"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#9945FF]/20 flex items-center justify-center">
                      {connecting ? (
                        <Loader2 className="w-4 h-4 text-[#9945FF] animate-spin" />
                      ) : (
                        <Zap className="w-4 h-4 text-[#9945FF]" />
                      )}
                    </div>
                    <div>
                      <span className="text-sm text-white block">
                        {inPhantomBrowser ? 'Connect Phantom' : 'Connect Solana'}
                      </span>
                      {inPhantomBrowser && (
                        <span className="text-[10px] text-slate-500">Tap to authorize</span>
                      )}
                    </div>
                  </div>
                  <ChevronDown className="w-4 h-4 text-slate-400 -rotate-90" />
                </button>
              )}
            </div>

            {/* EVM Section */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-slate-400 uppercase font-bold">
                <span className="text-[#627EEA]">⟠</span> EVM Chains
                {evmConnected && <Check className="w-3 h-3 text-[#00FFA3]" />}
              </div>

              {evmConnected && evmAddress ? (
                <div className="bg-[#627EEA]/10 border border-[#627EEA]/30 rounded-xl p-3 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span style={{ color: currentChain.color }}>{currentChain.icon}</span>
                      <span className="text-sm font-mono text-white">
                        {formatAddress(evmAddress)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyAddress(evmAddress, 'evm')}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white"
                      >
                        {copied === 'evm' ? <Check className="w-3 h-3 text-[#00FFA3]" /> : <Copy className="w-3 h-3" />}
                      </button>
                      <button
                        onClick={() => evmDisconnect()}
                        className="p-1.5 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400"
                      >
                        <LogOut className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {/* Chain Switcher */}
                  <div className="flex gap-1">
                    {EVM_CHAINS.map(chain => (
                      <button
                        key={chain.id}
                        onClick={() => switchChain?.({ chainId: chain.id })}
                        className={`flex-1 py-1.5 px-2 rounded-lg text-[10px] font-medium transition-all ${
                          chain.id === evmChainId
                            ? 'bg-white/10 text-white'
                            : 'text-slate-500 hover:text-white hover:bg-white/5'
                        }`}
                      >
                        {chain.icon} {chain.name}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {connectors.slice(0, 3).map((connector) => (
                    <button
                      key={connector.uid}
                      onClick={() => evmConnect({ connector })}
                      disabled={evmConnecting}
                      className="w-full flex items-center justify-between p-3 bg-black/30 border border-white/10 rounded-xl hover:border-[#627EEA]/50 hover:bg-[#627EEA]/5 transition-all text-left disabled:opacity-50"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-sm">
                          {connector.name === 'MetaMask' && '🦊'}
                          {connector.name === 'Coinbase Wallet' && '🔵'}
                          {connector.name === 'Injected' && '💼'}
                          {!['MetaMask', 'Coinbase Wallet', 'Injected'].includes(connector.name) && '🔗'}
                        </div>
                        <span className="text-sm text-white">{connector.name}</span>
                      </div>
                      {evmConnecting ? (
                        <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-400 -rotate-90" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="p-3 bg-black/30 border-t border-white/5">
            <p className="text-[10px] text-slate-600 text-center">
              email opens the Archive · wallet unlocks token features
            </p>
          </div>
        </div>
      )}

      {/* Account-merge modal — global (renders on top of everything)
          when the wallet-link flow discovers two candidate records. */}
      {mergeInfo && (
        <AccountMergeModal mergeInfo={mergeInfo} onDismiss={dismissMerge} />
      )}

      {/* Keeper's-log confirmation strip — brief, monospace, fades in
          then out over 4s. Matches the ambient signal style used at
          the top of /archive. No modal, no interruption. */}
      {linkStage === 'success' && (
        <>
          <style>{`
            @keyframes keeperLogFade {
              0%   { opacity: 0; transform: translateY(-4px); }
              10%  { opacity: 1; transform: translateY(0); }
              90%  { opacity: 1; transform: translateY(0); }
              100% { opacity: 0; transform: translateY(-4px); }
            }
          `}</style>
          <div
            className="fixed left-0 right-0 top-16 z-[80] flex justify-center pointer-events-none px-4"
            data-testid="wallet-link-keeper-log"
            style={{ animation: 'keeperLogFade 4s ease-in-out forwards' }}
          >
            <div
              className="rounded-md border border-white/[0.08] bg-[#05050A]/95 backdrop-blur px-4 py-1.5 shadow-lg"
            >
              <p
                className="text-[10px] uppercase tracking-widest text-slate-300"
                style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
              >
                keeper's log — wallet linked. the chain knows you now. your Archive progress is intact.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
