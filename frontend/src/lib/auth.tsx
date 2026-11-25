"use client";

import { createContext, use, useCallback, useEffect, useMemo, useState } from "react";
import { browser } from "react-dom";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { api, setUnauthorizedHandler, tokenStore } from "./api";
import type { User } from "./types";

const USER_KEY = "nexis.user";

type AuthState = {
  user: User | null;
  login: (email: string, password: string) => Promise<User>;
  logout: (reason?: "expired") => void;
};

const AuthContext = createContext<AuthState | null>(null);

function readStoredUser(): User | null {
  if (!tokenStore.get()) return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // The token lives in this browser's storage, so this provider only renders in the browser.
  use(browser("Login state is stored in this browser."));
  const [user, setUser] = useState<User | null>(readStoredUser);
  const router = useRouter();
  const queryClient = useQueryClient();

  const logout = useCallback(
    (reason?: "expired") => {
      tokenStore.clear();
      window.localStorage.removeItem(USER_KEY);
      queryClient.clear();
      setUser(null);
      router.replace(reason === "expired" ? "/login?expired=1" : "/login");
    },
    [queryClient, router],
  );

  useEffect(() => {
    setUnauthorizedHandler(() => logout("expired"));
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    tokenStore.set(res.access_token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    setUser(res.user);
    return res.user;
  }, []);

  const value = useMemo(() => ({ user, login, logout }), [user, login, logout]);
  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth() {
  const ctx = use(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export const homeFor = (user: User) => (user.role === "instructor" ? "/instructor" : "/dashboard");
