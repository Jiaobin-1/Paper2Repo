"use client";

import { useEffect, useState } from "react";
import { getAppSettings } from "./api";
import { DEFAULT_UI_LANGUAGE } from "./i18n";
import type { LanguageCode } from "./types";

export const SETTINGS_UPDATED_EVENT = "paper2repo:settings-updated";

export function useAppLanguage(): LanguageCode {
  const [language, setLanguage] = useState<LanguageCode>(DEFAULT_UI_LANGUAGE);

  useEffect(() => {
    let isMounted = true;

    async function loadLanguage() {
      try {
        const settings = await getAppSettings();
        if (isMounted) {
          setLanguage(settings.ui_language);
        }
      } catch {
        if (isMounted) {
          setLanguage(DEFAULT_UI_LANGUAGE);
        }
      }
    }

    loadLanguage();
    window.addEventListener(SETTINGS_UPDATED_EVENT, loadLanguage);
    return () => {
      isMounted = false;
      window.removeEventListener(SETTINGS_UPDATED_EVENT, loadLanguage);
    };
  }, []);

  return language;
}
