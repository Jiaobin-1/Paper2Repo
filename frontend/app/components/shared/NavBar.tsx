"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback } from "react";
import { updateAppSettings } from "../../../lib/api";
import { text } from "../../../lib/i18n";
import { SETTINGS_UPDATED_EVENT, useAppLanguage } from "../../../lib/useAppLanguage";
import { useTheme } from "../../../lib/useTheme";
import type { ThemeMode } from "../../../lib/types";

const links = [
  { href: "/", labelKey: "uploadPdf" as const },
  { href: "/batch", labelKey: "batchAnalysis" as const },
  { href: "/arxiv", labelKey: "arxivImport" as const },
  { href: "/knowledge", labelKey: "knowledgeBase" as const },
  { href: "/compare", labelKey: "compare" as const },
  { href: "/settings", labelKey: "settings" as const },
];

const themeCycle: Record<ThemeMode, ThemeMode> = {
  light: "dark",
  dark: "system",
  system: "light",
};

const themeIcon: Record<ThemeMode, string> = {
  light: "☀",
  dark: "☾",
  system: "⚙",
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
    <nav className="nav-bar">
      <Link href="/" className="nav-brand">
        <span className="nav-brand-icon">P</span>
        Paper2Repo
      </Link>
      <ul className="nav-links">
        {links.map((link) => {
          const isActive = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          return (
            <li key={link.href}>
              <Link href={link.href} className={isActive ? "active" : ""}>
                {text(language, link.labelKey)}
              </Link>
            </li>
          );
        })}
        <li>
          <button
            type="button"
            onClick={toggleTheme}
            className="nav-theme-toggle"
            title={text(language, `theme${theme.charAt(0).toUpperCase() + theme.slice(1)}` as "themeLight" | "themeDark" | "themeSystem")}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "18px",
              padding: "6px 8px",
              borderRadius: "var(--radius-sm)",
              color: "var(--muted)",
              lineHeight: 1,
              transition: "color 150ms var(--ease), background 150ms var(--ease)",
            }}
          >
            {themeIcon[theme]}
          </button>
        </li>
      </ul>
    </nav>
  );
}
