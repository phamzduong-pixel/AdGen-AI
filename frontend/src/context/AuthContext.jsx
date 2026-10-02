import { useCallback, useEffect, useMemo, useState } from "react";

import { getUserProfile } from "../services/api/userApi";
import { getMe, logoutCurrentSession } from "../services/api/authApi";
import tokenStorage from "../services/storage/tokenStorage";
import AuthContext from "./AuthContextValue";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(tokenStorage.hasAccessToken());

  const refreshUser = useCallback(async () => {
    if (!tokenStorage.hasAccessToken()) {
      setUser(null);
      setLoading(false);
      return null;
    }
    setLoading(true);
    try {
      const profile = await getUserProfile();
      setUser(profile);
      return profile;
    } finally {
      setLoading(false);
    }
  }, []);

  const completeLogin = useCallback(async (accessToken) => {
    tokenStorage.setAccessToken(accessToken);
    try {
      const authenticatedUser = await getMe();
      setUser(authenticatedUser);
      return authenticatedUser;
    } catch (error) {
      tokenStorage.removeAccessToken();
      setUser(null);
      throw error;
    }
  }, []);

  useEffect(() => {
    if (!tokenStorage.hasAccessToken()) return undefined;
    let active = true;
    getUserProfile()
      .then((profile) => {
        if (active) setUser(profile);
      })
      .catch(() => {
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const clearLocalSession = useCallback(() => {
    tokenStorage.removeAccessToken();
    localStorage.removeItem("currentConversationId");
    localStorage.removeItem("currentUser");
    setUser(null);
    window.google?.accounts?.id?.disableAutoSelect();
  }, []);

  const logout = useCallback(async ({ revoke = true } = {}) => {
    try {
      if (revoke && tokenStorage.hasAccessToken()) {
        await logoutCurrentSession();
      }
    } finally {
      clearLocalSession();
    }
  }, [clearLocalSession]);

  const value = useMemo(
    () => ({ user, loading, setUser, refreshUser, completeLogin, logout }),
    [user, loading, refreshUser, completeLogin, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
