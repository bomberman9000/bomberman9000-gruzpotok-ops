import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthGate } from "./components/AuthGate";
import { ToastProvider } from "./context/ToastContext";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <ToastProvider>
        <AuthGate>
          <App />
        </AuthGate>
      </ToastProvider>
    </BrowserRouter>
  </React.StrictMode>
);
