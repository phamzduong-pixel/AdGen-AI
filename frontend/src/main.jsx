import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App.jsx";
import ToastProvider from "./components/ui/Toast/ToastProvider";
import ErrorBoundary from "./components/ui/ErrorBoundary/ErrorBoundary";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";

import "./index.css";
import "./styles/reset.css";
import "./styles/variables.css";
import "./styles/globals.css";
import "./styles/scrollbar.css";
import "./styles/animations.css";
import "./styles/markdown.css";

const savedTheme = localStorage.getItem("adgen_theme") || "system";
document.documentElement.dataset.theme = savedTheme;
const isInitialDark = savedTheme === "dark" || (savedTheme === "system" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
document.documentElement.classList.toggle("dark", Boolean(isInitialDark));

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <ThemeProvider>
          <AuthProvider>
            <ToastProvider>
              <App />
            </ToastProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
