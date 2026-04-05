"use client";

import { useState, type FormEvent } from "react";
import { login, type UserInfo } from "@/lib/api";

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
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    onError(null);

    try {
      const user = await login(username, password);
      onLogin(user);
    } catch {
      onError("Неверный логин или пароль");
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

        <label className="auth-label" htmlFor="username">
          Логин
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
          {loading ? "Входим…" : "Войти"}
        </button>

        <div className="auth-hint">По умолчанию: admin / admin123</div>
      </form>
    </div>
  );
}
