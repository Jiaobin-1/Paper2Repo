"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback } from "react";
import { updateAppSettings } from "../../../lib/api";
import { text } from "../../../lib/i18n";
import { SETTINGS_UPDATED_EVENT, useAppLanguage } from "../../../lib/useAppLanguage";
import { useTheme } from "../../../lib/useTheme";
import type { ThemeMode } from "../../../lib/types";

function NavIcon({ path }: { path: string }) {
  return (
    <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}

const links = [
  { href: "/", labelKey: "uploadPdf" as const, icon: "M12 3v12m0 0l-4-4m4 4l4-4M5 15v3a3 3 0 003 3h8a3 3 0 003-3v-3" },
  { href: "/batch", labelKey: "batchAnalysis" as const, icon: "M4 6h16M4 10h16M4 14h16M4 18h16" },
  { href: "/arxiv", labelKey: "arxivImport" as const, icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" },
  { href: "/knowledge", labelKey: "knowledgeBase" as const, icon: "M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" },
  { href: "/compare", labelKey: "compare" as const, icon: "M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" },
  { href: "/settings", labelKey: "settings" as const, icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z" },
];

const themeCycle: Record<ThemeMode, ThemeMode> = {
  light: "dark",
  dark: "system",
  system: "light",
};

const themeIcons: Record<ThemeMode, { icon: string; label: string }> = {
  light: {
    icon: "M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z",
    label: "Light",
  },
  dark: {
    icon: "M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z",
    label: "Dark",
  },
  system: {
    icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
    label: "System",
  },
};

export default function NavBar() {
  const language = useAppLanguage();
  const pathname = usePathname();
  const theme = useTheme();

  const toggleTheme = useCallback(async () => {
    const next = themeCycle[theme];
    try {
      await updateAppSettings({ theme: next });
      window.dispatchEvent(new Event(SETTINGS_UPDATED_EVENT));
    } catch {
      // ignore
    }
  }, [theme]);

  return (
    <aside className="nav-bar">
      <div className="nav-top">
        <Link href="/" className="nav-brand">
          <img className="nav-brand-icon" src="/logo.svg" alt="" aria-hidden="true" />
          <span>Paper2Repo</span>
        </Link>
        <ul className="nav-links">
          {links.map((link) => {
            const isActive = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <li key={link.href}>
                <Link href={link.href} className={isActive ? "active" : ""}>
                  <NavIcon path={link.icon} />
                  {text(language, link.labelKey)}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
      <button
        type="button"
        onClick={toggleTheme}
        className="nav-theme-toggle"
        title={text(language, `theme${theme.charAt(0).toUpperCase() + theme.slice(1)}` as "themeLight" | "themeDark" | "themeSystem")}
      >
        <span className="nav-theme-mark">
          <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true" style={{ width: 14, height: 14 }}>
            <path d={themeIcons[theme].icon} />
          </svg>
        </span>
        <span className="nav-theme-label">
          {text(language, `theme${theme.charAt(0).toUpperCase() + theme.slice(1)}` as "themeLight" | "themeDark" | "themeSystem")}
        </span>
      </button>
    </aside>
  );
}
