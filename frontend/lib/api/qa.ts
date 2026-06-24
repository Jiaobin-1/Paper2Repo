import { apiUrl, formatApiError, jsonRequestOptions, requestJson } from "./client";
import type { QaMessage } from "../types";

export interface StreamEvent {
  type: "token" | "done" | "error";
  content?: string;
  message_id?: string;
}

export function getQaHistory(runId: string): Promise<QaMessage[]> {
  return requestJson<QaMessage[]>(`/api/runs/${runId}/qa`, {}, "对话历史加载失败。");
}

export function askQuestion(runId: string, question: string): Promise<QaMessage[]> {
  return requestJson<QaMessage[]>(
    `/api/runs/${runId}/qa`,
    jsonRequestOptions({ question }),
    "提问失败。",
  );
}

export async function* askQuestionStream(
  runId: string,
  question: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(apiUrl(`/api/runs/${runId}/qa/stream`), {
    ...jsonRequestOptions({ question }),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "提问失败。"));
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("Response body is not readable.");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;
        const jsonStr = trimmed.slice(6);
        try {
          yield JSON.parse(jsonStr) as StreamEvent;
        } catch {
          // Skip malformed SSE lines.
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
