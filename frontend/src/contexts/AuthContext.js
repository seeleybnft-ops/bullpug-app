/**
 * AuthContext — global user-session state.
 *
 * Coexists with `@solana/wallet-adapter-react`. When a wallet is
 * connected, wallet identity wins (`sessionType === "wallet"`); when
 * only an email JWT is stored, `sessionType === "email"`; otherwise
 * `"guest"`. Later phases layer "linked" on top when both are
 * present — Phase B keeps it simple.
 *
 * localStorage key: `bullpug_user_jwt` (mirrors the admin naming).
 * A quick `/api/auth/me` hydration on mount confirms the JWT is still
 * valid; a 401 wipes it so a returning visitor with a stale token
 * doesn't get stuck in a broken state.
 */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useWallet } from "@solana/wallet-adapter-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const JWT_KEY = "bullpug_user_jwt";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const { publicKey } = useWallet();
  const walletAddress = publicKey?.toBase58() || null;

  const [jwt, setJwt] = useState(() => {
    try { return localStorage.getItem(JWT_KEY); } catch { return null; }
  });
  const [emailUser, setEmailUser] = useState(null); // {user_id, email, ...}
  const [hydrating, setHydrating] = useState(!!jwt);

  // Hydrate the email session by hitting /me once at mount and whenever
  // the JWT changes. A 401 (expired / user deleted) purges the token
  // silently so the sign-in screen can offer a fresh flow.
  useEffect(() => {
    if (!jwt) {
      setEmailUser(null);
      setHydrating(false);
      return;
    }
    let cancelled = false;
    setHydrating(true);
    axios.get(`${API}/auth/me`, { headers: { Authorization: `Bearer ${jwt}` } })
      .then((r) => { if (!cancelled) setEmailUser(r.data); })
      .catch(() => {
        if (cancelled) return;
        try { localStorage.removeItem(JWT_KEY); } catch { /* ignore */ }
        setJwt(null);
        setEmailUser(null);
      })
      .finally(() => { if (!cancelled) setHydrating(false); });
    return () => { cancelled = true; };
  }, [jwt]);

  const signInWithJwt = useCallback((newJwt) => {
    try { localStorage.setItem(JWT_KEY, newJwt); } catch { /* ignore */ }
    setJwt(newJwt);
  }, []);

  const signOut = useCallback(() => {
    try { localStorage.removeItem(JWT_KEY); } catch { /* ignore */ }
    setJwt(null);
    setEmailUser(null);
  }, []);

  // Session type — wallet wins if connected (Phase B never blocks the
  // wallet flow, per user's 2b choice). Email is the fallback.
  const sessionType = walletAddress ? "wallet" : (jwt && emailUser ? "email" : "guest");

  // `identity` is what routes see: wallet address for wallet users,
  // user_id UUID for email users, null for guests. Every Archive
  // fetch that used to send `?wallet=` now sends this instead.
  const identity = walletAddress || emailUser?.user_id || null;

  // Auth header helper — non-empty only for email sessions. Wallet
  // sessions never carry a bearer (Phase B design).
  const authHeaders = useMemo(() => (
    sessionType === "email" && jwt ? { Authorization: `Bearer ${jwt}` } : {}
  ), [sessionType, jwt]);

  const value = useMemo(() => ({
    sessionType,
    identity,
    walletAddress,
    email: emailUser?.email || null,
    userId: emailUser?.user_id || null,
    jwt,
    hydrating,
    authHeaders,
    signInWithJwt,
    signOut,
  }), [sessionType, identity, walletAddress, emailUser, jwt, hydrating, authHeaders, signInWithJwt, signOut]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
