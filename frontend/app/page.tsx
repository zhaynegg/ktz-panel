"use client";

import { useEffect, useState } from "react";
import { fetchMe, logout, type UserInfo } from "@/lib/api";
import { LoginScreen } from "@/components/auth/LoginScreen";
import { DashboardView } from "@/components/dashboard/DashboardView";

export default function Page() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [themeMode, setThemeMode] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const saved =
      typeof window !== "undefined"
        ? window.localStorage.getItem("kzt-theme")
        : null;
    setThemeMode(saved === "light" ? "light" : "dark");
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = themeMode;
    window.localStorage.setItem("kzt-theme", themeMode);
  }, [themeMode]);

  useEffect(() => {
    let active = true;
    fetchMe()
      .then((me) => {
        if (!active) return;
        setUser(me);
        setAuthError(null);
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  function toggleTheme() {
    setThemeMode((prev) => (prev === "dark" ? "light" : "dark"));
  }

  if (authLoading) {
    return <div className="auth-shell"><div className="auth-card">Проверка сессии…</div></div>;
  }

  if (!user) {
    return (
      <LoginScreen
        error={authError}
        themeMode={themeMode}
        onLogin={(nextUser) => {
          setUser(nextUser);
          setAuthError(null);
        }}
        onError={setAuthError}
        onToggleTheme={toggleTheme}
      />
    );
  }

  return (
    <DashboardView
      user={user}
      themeMode={themeMode}
      onLogout={async () => {
        await logout();
        setUser(null);
      }}
      onToggleTheme={toggleTheme}
    />
  );
}
