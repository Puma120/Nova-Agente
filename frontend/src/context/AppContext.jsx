import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as api from "../lib/api";

const AppContext = createContext(null);

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside <AppProvider>");
  return ctx;
}

export function AppProvider({ children }) {
  // Pure read of the OAuth redirect param + localStorage — no side effects here.
  const [token, setToken] = useState(() => {
    const urlToken = new URLSearchParams(window.location.search).get("token");
    return urlToken || localStorage.getItem("nova_token");
  });
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("nova_user")); } catch { return null; }
  });
  const [authError, setAuthError] = useState("");
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);

  // Consume the OAuth redirect exactly once: persist the token and clean the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("token");
    const err = params.get("auth") === "error";
    if (urlToken) localStorage.setItem("nova_token", urlToken);
    if (err) setAuthError("No se pudo iniciar sesión con Google. Inténtalo de nuevo.");
    if (urlToken || err) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setConversations([]);
    setActiveConvId(null);
    localStorage.removeItem("nova_token");
    localStorage.removeItem("nova_user");
  }, []);

  useEffect(() => { api.setUnauthorizedHandler(logout); }, [logout]);

  const updateUser = useCallback((patch) => {
    setUser((prev) => {
      const next = { ...prev, ...patch };
      localStorage.setItem("nova_user", JSON.stringify(next));
      return next;
    });
  }, []);

  // Whenever we hold a token, refresh the user profile from the server.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await api.getMe(token);
        if (!cancelled) {
          setUser(me);
          localStorage.setItem("nova_user", JSON.stringify(me));
        }
      } catch {
        if (!cancelled) logout();
      }
    })();
    return () => { cancelled = true; };
  }, [token, logout]);

  const loadConversations = useCallback(async () => {
    if (!token) return;
    setConversations(await api.getConversations(token));
  }, [token]);

  useEffect(() => { if (token) loadConversations(); }, [token, loadConversations]);

  const deleteConversation = useCallback(async (id) => {
    await api.deleteConversation(token, id);
    setActiveConvId((cur) => (cur === id ? null : cur));
    loadConversations();
  }, [token, loadConversations]);

  const value = {
    token, user, authError,
    logout, updateUser,
    conversations, loadConversations,
    activeConvId, setActiveConvId, deleteConversation,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
