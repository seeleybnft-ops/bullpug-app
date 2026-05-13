/**
 * useSiwsAdmin — Sign-In-With-Solana admin login flow.
 *
 *   1. Backend POST /api/admin-auth/nonce → {message, nonce, expires_at}
 *   2. Phantom signMessage(message_bytes)
 *   3. Backend POST /api/admin-auth/verify → {access_token, ...}
 *   4. Token persisted in localStorage (`bullpug_admin_jwt`) so the page
 *      survives reloads. /me is hit on mount to confirm validity.
 *
 * Public API:
 *   const { isAdmin, wallet, loginAdmin, logoutAdmin, loading, error,
 *           authFetch } = useSiwsAdmin();
 *
 *   - `authFetch(url, opts?)` — pre-attaches the bearer header (or a no-op
 *     if not signed in).
 *
 * The hook only proves admin to the BACKEND. Hiding admin UI client-side
 * is convenience; the real auth is the server-side `require_admin_jwt`
 * (or `admin_auth_compat`) dependency.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import axios from "axios";
import bs58 from "bs58";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const STORAGE_KEY = "bullpug_admin_jwt";

function loadToken() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.token || !parsed?.expires_at) return null;
    if (new Date(parsed.expires_at).getTime() <= Date.now()) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch (e) {
    return null;
  }
}

function saveToken(token, expiresAtIso, wallet) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, expires_at: expiresAtIso, wallet }));
  } catch (e) { /* ignore */ }
}

function clearToken() {
  try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
}

export function useSiwsAdmin() {
  const { publicKey, signMessage, connected } = useWallet();
  const walletStr = publicKey?.toBase58() || null;
  const [tokenState, setTokenState] = useState(() => loadToken());
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  // Validate persisted token via /me on mount and whenever it changes.
  useEffect(() => {
    if (!tokenState?.token) { setIsAdmin(false); return; }
    let cancelled = false;
    (async () => {
      try {
        await axios.get(`${API}/admin-auth/me`, {
          headers: { Authorization: `Bearer ${tokenState.token}` },
        });
        if (!cancelled) setIsAdmin(true);
      } catch (e) {
        if (!cancelled) {
          clearToken();
          setTokenState(null);
          setIsAdmin(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [tokenState?.token]);

  // If the connected wallet changes away from the signed-in admin wallet,
  // wipe the session so admin actions can't be taken with a different key.
  useEffect(() => {
    if (tokenState && walletStr && tokenState.wallet !== walletStr) {
      clearToken();
      setTokenState(null);
      setIsAdmin(false);
    }
  }, [walletStr, tokenState]);

  const loginAdmin = useCallback(async () => {
    if (!connected || !publicKey || !signMessage) {
      setError("Connect a Solana wallet first");
      return false;
    }
    setLoading(true);
    setError("");
    try {
      // 1. Nonce + structured message
      const nonceResp = await axios.post(`${API}/admin-auth/nonce`, {
        wallet: publicKey.toBase58(),
      });
      const message = nonceResp.data?.message;
      if (!message) throw new Error("No message returned from nonce endpoint");

      // 2. Phantom signs the UTF-8 bytes
      const encoded = new TextEncoder().encode(message);
      const sigBytes = await signMessage(encoded);
      const sigB58 = bs58.encode(sigBytes);

      // 3. Verify → JWT
      const verifyResp = await axios.post(`${API}/admin-auth/verify`, {
        wallet: publicKey.toBase58(),
        signature: sigB58,
        message,
      });

      const { access_token: token, expires_in, wallet } = verifyResp.data || {};
      if (!token) throw new Error("Verify endpoint returned no token");
      const expiresAt = new Date(Date.now() + (expires_in || 0) * 1000).toISOString();
      saveToken(token, expiresAt, wallet);
      if (mounted.current) {
        setTokenState({ token, expires_at: expiresAt, wallet });
        setIsAdmin(true);
      }
      return true;
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.message || "Login failed";
      if (mounted.current) setError(detail);
      return false;
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [connected, publicKey, signMessage]);

  const logoutAdmin = useCallback(() => {
    clearToken();
    setTokenState(null);
    setIsAdmin(false);
  }, []);

  const authFetch = useCallback(
    async (url, opts = {}) => {
      const headers = { ...(opts.headers || {}) };
      if (tokenState?.token) {
        headers.Authorization = `Bearer ${tokenState.token}`;
      }
      return axios.request({
        url: url.startsWith("http") ? url : `${API}${url}`,
        ...opts,
        headers,
      });
    },
    [tokenState?.token]
  );

  return useMemo(
    () => ({
      isAdmin,
      wallet: tokenState?.wallet || walletStr,
      loading,
      error,
      loginAdmin,
      logoutAdmin,
      authFetch,
      token: tokenState?.token || null,
      expiresAt: tokenState?.expires_at || null,
    }),
    [isAdmin, tokenState, walletStr, loading, error, loginAdmin, logoutAdmin, authFetch]
  );
}

export default useSiwsAdmin;
