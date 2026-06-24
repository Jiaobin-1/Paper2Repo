import { text } from "./i18n";
import type { LanguageCode } from "./types";

export function batchCompletionMessage(completedRuns: boolean[], language: LanguageCode): string {
  return completedRuns.every(Boolean) ? text(language, "batchDone") : text(language, "batchPartialDone");
}
