import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { uiRequireAuth } from "../api/client";

export function Layout() {
  const [op, setOp] = useState(() => localStorage.getItem("operator_id") || "");
  const [authOk, setAuthOk] = useState(() => !!sessionStorage.getItem("internal_token")?.trim());

  useEffect(() => {
    setAuthOk(!!sessionStorage.getItem("internal_token")?.trim());
  }, []);

  useEffect(() => {
    if (op) localStorage.setItem("operator_id", op);
    else localStorage.removeItem("operator_id");
  }, [op]);

  useEffect(() => {
    const t = () => setAuthOk(!!sessionStorage.getItem("internal_token")?.trim());
    window.addEventListener("storage", t);
    return () => window.removeEventListener("storage", t);
  }, []);

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <strong style={{ marginRight: "1rem" }}>ГрузПоток AI</strong>
        {op && (
          <span className="badge ok" title="X-Reviewed-By">
            {op}
          </span>
        )}
        {uiRequireAuth() && authOk && (
          <span className="badge" title="Internal token">
            🔒
          </span>
        )}
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Dashboard
        </NavLink>
        <NavLink to="/queue" className={({ isActive }) => (isActive ? "active" : "")}>
          Очередь review
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
          История
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => (isActive ? "active" : "")}>
          Аналитика
        </NavLink>
        <NavLink to="/case" className={({ isActive }) => (isActive ? "active" : "")}>
          Панель кейса
        </NavLink>
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>Оператор (заголовок X-Reviewed-By):</span>
        <input
          placeholder="id или email"
          value={op}
          onChange={(e) => setOp(e.target.value)}
          aria-label="Operator id for X-Reviewed-By"
        />
      </footer>
    </div>
  );
}
