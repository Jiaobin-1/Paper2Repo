import { apiUrl, formatApiError, requestJson } from "./client";
import type { BatchStartResponse, BatchUploadResponse, Paper, Run } from "../types";

export async function uploadPaper(file: File): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(apiUrl("/api/papers/upload"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "上传失败。"));
  }

  return response.json();
}

export function startAnalysis(paperId: string): Promise<Run> {
  return requestJson<Run>(`/api/papers/${paperId}/runs`, { method: "POST" }, "分析启动失败。");
}

export async function uploadPapers(files: File[]): Promise<BatchUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(apiUrl("/api/papers/upload-batch"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Batch upload failed."));
  }

  return response.json();
}

export function startBatchAnalysis(paperIds: string[]): Promise<BatchStartResponse> {
  const params = new URLSearchParams({ paper_ids: paperIds.join(",") });
  return requestJson<BatchStartResponse>(
    `/api/papers/batch-start?${params.toString()}`,
    { method: "POST" },
    "Batch analysis failed.",
  );
}
