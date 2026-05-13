import { getRun } from "./api";
import type { LanguageCode, Run } from "./types";

const DEFAULT_INTERVAL_MS = 1000;
const DEFAULT_MAX_ATTEMPTS = 600;
const DEFAULT_MAX_CONSECUTIVE_ERRORS = 5;

type PollRunHandlers = {
  onRun?: (run: Run) => void;
  onRetry?: (consecutiveErrors: number) => void;
};

type PollRunOptions = {
  signal?: AbortSignal;
  delayFirstPoll?: boolean;
  intervalMs?: number;
  maxAttempts?: number;
  maxConsecutiveErrors?: number;
  language?: LanguageCode;
};

export async function pollRunUntilTerminal(
  runId: string,
  handlers: PollRunHandlers = {},
  options: PollRunOptions = {},
): Promise<Run> {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const maxAttempts = options.maxAttempts ?? DEFAULT_MAX_ATTEMPTS;
  const maxConsecutiveErrors = options.maxConsecutiveErrors ?? DEFAULT_MAX_CONSECUTIVE_ERRORS;
  const lang = options.language ?? "zh";
  let consecutiveErrors = 0;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (attempt > 0 || options.delayFirstPoll) {
      await sleep(intervalMs, options.signal);
    }
    if (options.signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }

    try {
      const latestRun = await getRun(runId);
      consecutiveErrors = 0;
      handlers.onRun?.(latestRun);
      if (isTerminalRun(latestRun)) {
        return latestRun;
      }
    } catch {
      consecutiveErrors += 1;
      if (consecutiveErrors >= maxConsecutiveErrors) {
        throw new Error(lang === "en" ? "Network connection lost. Analysis monitoring stopped." : "网络连接中断，分析监控已停止。");
      }
      handlers.onRetry?.(consecutiveErrors);
    }
  }

  throw new Error(lang === "en" ? "Analysis is still running. Please refresh the page later." : "分析仍在运行，请稍后刷新任务状态。");
}

export function isTerminalRun(run: Run): boolean {
  return run.status === "completed" || run.status === "failed";
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}
