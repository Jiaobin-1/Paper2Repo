import { getBatchStatus } from "./api";
import { isAbortError } from "./api/client";
import type { BatchStatusResponse, LanguageCode } from "./types";

const DEFAULT_INTERVAL_MS = 1000;
const DEFAULT_MAX_ATTEMPTS = 600;
const DEFAULT_MAX_CONSECUTIVE_ERRORS = 5;

type PollBatchHandlers = {
  onBatch?: (batch: BatchStatusResponse) => void;
  onRetry?: (consecutiveErrors: number) => void;
};

type PollBatchOptions = {
  signal?: AbortSignal;
  delayFirstPoll?: boolean;
  intervalMs?: number;
  maxAttempts?: number;
  maxConsecutiveErrors?: number;
  language?: LanguageCode;
};

export async function pollBatchUntilTerminal(
  batchId: string,
  handlers: PollBatchHandlers = {},
  options: PollBatchOptions = {},
): Promise<BatchStatusResponse> {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const maxAttempts = options.maxAttempts ?? DEFAULT_MAX_ATTEMPTS;
  const maxConsecutiveErrors = options.maxConsecutiveErrors ?? DEFAULT_MAX_CONSECUTIVE_ERRORS;
  const language = options.language ?? "zh";
  let consecutiveErrors = 0;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (attempt > 0 || options.delayFirstPoll) {
      await sleep(intervalMs, options.signal);
    }
    if (options.signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }

    try {
      const batch = await getBatchStatus(batchId, { signal: options.signal });
      consecutiveErrors = 0;
      handlers.onBatch?.(batch);
      if (isTerminalBatch(batch)) {
        return batch;
      }
    } catch (error) {
      if (isAbortError(error)) {
        throw error;
      }
      consecutiveErrors += 1;
      if (consecutiveErrors >= maxConsecutiveErrors) {
        throw new Error(
          language === "en"
            ? "Network connection lost. Batch monitoring stopped."
            : "网络连接中断，批量分析监控已停止。",
        );
      }
      handlers.onRetry?.(consecutiveErrors);
    }
  }

  throw new Error(
    language === "en"
      ? "Batch analysis is still running. Please refresh the page later."
      : "批量分析仍在运行，请稍后刷新任务状态。",
  );
}

export function isTerminalBatch(batch: BatchStatusResponse): boolean {
  return batch.runs.length > 0 && batch.runs.every((run) => run.status === "completed" || run.status === "failed");
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
