"use client";

import { useEffect, useState } from "react";
import { checkLlmConnection, getAppSettings, updateAppSettings } from "../../lib/api";
import { text } from "../../lib/i18n";
import { SETTINGS_UPDATED_EVENT, useAppLanguage } from "../../lib/useAppLanguage";
import type { AppSettings, LanguageCode, ThemeMode } from "../../lib/types";

export default function SettingsPage() {
  const language = useAppLanguage();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [defaultModel, setDefaultModel] = useState("");
  const [uiLanguage, setUiLanguage] = useState<LanguageCode>("zh");
  const [reportLanguage, setReportLanguage] = useState<LanguageCode>("en");
  const [theme, setTheme] = useState<ThemeMode>("light");
  const [message, setMessage] = useState(text(language, "settingsLoadFailed"));
  const [isSaving, setIsSaving] = useState(false);
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    let isMounted = true;
    getAppSettings()
      .then((loadedSettings) => {
        if (!isMounted) return;
        setSettings(loadedSettings);
        setDefaultModel(loadedSettings.default_model);
        setUiLanguage(loadedSettings.ui_language);
        setReportLanguage(loadedSettings.report_language);
        setTheme(loadedSettings.theme);
        setMessage("");
      })
      .catch((error) => {
        if (!isMounted) return;
        setMessage(error instanceof Error ? error.message : text(language, "settingsLoadFailed"));
      });
    return () => {
      isMounted = false;
    };
  }, [language]);

  async function handleSave() {
    setIsSaving(true);
    try {
      const updated = await updateAppSettings({
        default_model: defaultModel,
        ui_language: uiLanguage,
        report_language: reportLanguage,
        theme,
      });
      setSettings(updated);
      setDefaultModel(updated.default_model);
      setUiLanguage(updated.ui_language);
      setReportLanguage(updated.report_language);
      setTheme(updated.theme);
      setMessage(text(updated.ui_language, "settingsSaved"));
      window.dispatchEvent(new Event(SETTINGS_UPDATED_EVENT));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : text(language, "settingsLoadFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCheckModel() {
    setIsChecking(true);
    try {
      const result = await checkLlmConnection();
      const latency = result.latency_ms === null ? "" : ` · ${Math.round(result.latency_ms)}ms`;
      const error = result.error ? ` · ${result.error}` : "";
      setMessage(`${text(language, result.ok ? "modelCheckPassed" : "modelCheckFailed")} · ${result.model}${latency}${error}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : text(language, "modelCheckFailed"));
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>{text(language, "settingsPageTitle")}</h1>
          <p className="muted">{text(language, "settingsPageDesc")}</p>
        </div>
      </section>

      <section className="panel stack">
        <label className="field-label" htmlFor="ui-language">
          {text(language, "uiLanguage")}
        </label>
        <select id="ui-language" className="select" value={uiLanguage} onChange={(event) => setUiLanguage(event.target.value as LanguageCode)}>
          <option value="zh">{text(language, "chinese")}</option>
          <option value="en">{text(language, "english")}</option>
        </select>

        <label className="field-label" htmlFor="report-language">
          {text(language, "reportLanguage")}
        </label>
        <select id="report-language" className="select" value={reportLanguage} onChange={(event) => setReportLanguage(event.target.value as LanguageCode)}>
          <option value="en">{text(language, "english")}</option>
          <option value="zh">{text(language, "chinese")}</option>
        </select>

        <label className="field-label" htmlFor="theme-mode">
          {text(language, "themeMode")}
        </label>
        <select id="theme-mode" className="select" value={theme} onChange={(event) => setTheme(event.target.value as ThemeMode)}>
          <option value="light">{text(language, "themeLight")}</option>
          <option value="dark">{text(language, "themeDark")}</option>
          <option value="system">{text(language, "themeSystem")}</option>
        </select>

        <label className="field-label" htmlFor="default-model">
          {text(language, "defaultModel")}
        </label>
        <select
          id="default-model"
          className="select"
          value={defaultModel}
          disabled={!settings}
          onChange={(event) => setDefaultModel(event.target.value)}
        >
          {settings ? (
            settings.available_models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))
          ) : (
            <option value="">{text(language, "loadingModelConfig")}</option>
          )}
        </select>

        <p className="muted">
          {settings
            ? `${settings.configured ? text(language, "modelConfigured") : text(language, "modelNotConfigured")} · ${settings.base_url} · ${text(language, "modelTimeoutSetting")} ${settings.timeout_seconds}s`
            : text(language, "loadingModelConfig")}
        </p>

        <div className="action-row">
          <button className="button" type="button" disabled={!settings || isSaving} onClick={handleSave}>
            {isSaving ? text(language, "savingSettings") : text(language, "saveSettings")}
          </button>
          <button className="button secondary" type="button" disabled={!settings || isChecking} onClick={handleCheckModel}>
            {isChecking ? text(language, "testingModelConnection") : text(language, "testModelConnection")}
          </button>
        </div>

        {message ? <p className="muted">{message}</p> : null}
      </section>
    </main>
  );
}
