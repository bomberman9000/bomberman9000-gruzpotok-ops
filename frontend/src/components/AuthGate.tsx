import { useState } from "react";
import { setInternalToken, uiRequireAuth } from "../api/client";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [token, setTok] = useState(() => sessionStorage.getItem("internal_token") || "");
  const need = uiRequireAuth();

  if (!need) {
    return <>{children}</>;
  }

  if (!sessionStorage.getItem("internal_token")?.trim()) {
    return (
      <div className="app-main" style={{ maxWidth: 420 }}>
        <h1>Доступ</h1>
        <p className="muted">Введите internal token (тот же, что в INTERNAL_AUTH_TOKEN на backend).</p>
        <div className="stack" style={{ marginTop: "1rem" }}>
          <input
            type="password"
            autoComplete="off"
            placeholder="X-Internal-Token"
            value={token}
            onChange={(e) => setTok(e.target.value)}
            style={{ width: "100%" }}
          />
          <button
            type="button"
            className="primary"
            onClick={() => {
              setInternalToken(token.trim());
              window.location.reload();
            }}
          >
            Войти
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
