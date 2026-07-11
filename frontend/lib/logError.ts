// Lightweight, consistent console logging for errors that are intentionally
// swallowed in the UI (non-blocking background fetches, best-effort writes).
// Keeps failures debuggable without surfacing them to the user.
export function logError(context: string, error: unknown): void {
  console.error(`[paper2repo] ${context}`, error);
}
