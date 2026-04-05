"use client";

import { useState, type FormEvent } from "react";
import { login, signUp, type UserInfo } from "@/lib/api";

type LoginScreenProps = {
  error: string | null;
  themeMode: "light" | "dark";
  onLogin: (user: UserInfo) => void;
  onError: (message: string | null) => void;
  onToggleTheme: () => void;
};

export function LoginScreen({
  error,
  themeMode,
  onLogin,
  onError,
  onToggleTheme,
}: LoginScreenProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    onError(null);

    try {
      if (mode === "signup") {
        const result = await signUp(username, password);
        if (result.needsEmailConfirm) {
          onError("Учётка создана. Подтверди email в письме и затем войди.");
        } else {
          const user = await login(username, password);
          onLogin(user);
        }
      } else {
        const user = await login(username, password);
        onLogin(user);
      }
    } catch {
      onError(mode === "signup" ? "Не удалось создать учётку" : "Неверный логин или пароль");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="auth-toolbar">
          <button className="btn auth-theme-btn" type="button" onClick={onToggleTheme}>
            {themeMode === "dark" ? "☀ Светлая тема" : "🌙 Тёмная тема"}
          </button>
        </div>
        <div className="auth-kicker">KZT Digital Twin</div>
        <h1 className="auth-title">Вход в панель мониторинга</h1>
        <p className="auth-copy">Используй логин и пароль, чтобы открыть дашборд и поток телеметрии.</p>

        <div className="auth-toolbar" style={{ justifyContent: "flex-start" }}>
          <button
            className="btn auth-theme-btn"
            type="button"
            onClick={() => {
              setMode("login");
              onError(null);
            }}
          >
            Вход
          </button>
          <button
            className="btn auth-theme-btn"
            type="button"
            onClick={() => {
              setMode("signup");
              onError(null);
            }}
          >
            Создать учётку
          </button>
        </div>

        <label className="auth-label" htmlFor="username">
          Email
        </label>
        <input
          id="username"
          className="auth-input"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
        />

        <label className="auth-label" htmlFor="password">
          Пароль
        </label>
        <input
          id="password"
          className="auth-input"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
        />

        {error ? <div className="auth-error">{error}</div> : null}

        <button className="auth-submit" type="submit" disabled={loading}>
          {loading ? "Подождите…" : mode === "signup" ? "Создать учётку" : "Войти"}
        </button>

        <div className="auth-hint">Вход и регистрация через Supabase Auth (email + password).</div>
      </form>
    </div>
  );
}
