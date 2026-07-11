import { messages } from "./i18n/messages";
import type { LanguageCode } from "./types";

export const DEFAULT_UI_LANGUAGE: LanguageCode = "zh";

export type MessageKey = keyof typeof messages.zh;

export function text(language: LanguageCode, key: MessageKey): string {
  return messages[language]?.[key] ?? messages.zh[key];
}
