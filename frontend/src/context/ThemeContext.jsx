import { useEffect, useMemo, useState } from "react";

import {
  getPreferences,
  savePreferences,
} from "../utils/settingsStorage";
import ThemeContext from "./ThemeContextValue";

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => getPreferences().theme || "system");

  useEffect(() => {
    const applyTheme = (currentTheme) => {
      const isSystemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      const isDark = currentTheme === "dark" || (currentTheme === "system" && isSystemDark);

      document.documentElement.dataset.theme = currentTheme;
      document.documentElement.classList.toggle("dark", isDark);
    };

    applyTheme(theme);

    if (theme === "system" && window.matchMedia) {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = () => applyTheme("system");
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
  }, [theme]);

  const setTheme = (nextTheme) => {
    const safeTheme = ["light", "dark", "system"].includes(nextTheme)
      ? nextTheme
      : "system";
    setThemeState(safeTheme);
    const preferences = { ...getPreferences(), theme: safeTheme };
    savePreferences(preferences);
    localStorage.setItem("adgen_theme", safeTheme);
  };

  const value = useMemo(() => ({ theme, setTheme }), [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
