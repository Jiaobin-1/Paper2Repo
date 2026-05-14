"use client";

import { useEffect, useState } from "react";
import { getAppSettings } from "./api";
import { SETTINGS_UPDATED_EVENT } from "./useAppLanguage";
import type { ThemeMode } from "./types";

const DEFAULT_THEME: ThemeMode = "light";

function resolveEffectiveTheme(theme: ThemeMode): "light" | "dark" {
  if (theme === "system") {
    if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }
  return theme;
}

function applyTheme(theme: ThemeMode) {
  const effective = resolveEffectiveTheme(theme);
  document.documentElement.setAttribute("data-theme", effective);
}

export function useTheme(): ThemeMode {
  const [theme, setTheme] = useState<ThemeMode>(DEFAULT_THEME);

  useEffect(() => {
    let isMounted = true;

    function load() {
      getAppSettings()
        .then((settings) => {
          if (!isMounted) return;
          setTheme(settings.theme);
          applyTheme(settings.theme);
        })
        .catch(() => {
          applyTheme(DEFAULT_THEME);
        });
    }

    load();
    window.addEventListener(SETTINGS_UPDATED_EVENT, load);

    return () => {
      isMounted = false;
      window.removeEventListener(SETTINGS_UPDATED_EVENT, load);
    };
  }, []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => applyTheme("system");
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  return theme;
}
