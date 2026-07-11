import { requestJson } from "./client";
import type { BatchStartResponse, BatchUploadResponse, Paper, Run } from "../types";

export function uploadPaper(file: File): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson<Paper>(
    "/api/papers/upload",
    { method: "POST", body: formData },
    "上传失败。",
  );
}

export function startAnalysis(paperId: string): Promise<Run> {
  return requestJson<Run>(`/api/papers/${paperId}/runs`, { method: "POST" }, "分析启动失败。");
}

export function uploadPapers(files: File[]): Promise<BatchUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  return requestJson<BatchUploadResponse>(
    "/api/papers/upload-batch",
    { method: "POST", body: formData },
    "Batch upload failed.",
  );
}

export function startBatchAnalysis(paperIds: string[]): Promise<BatchStartResponse> {
  const params = new URLSearchParams({ paper_ids: paperIds.join(",") });
  return requestJson<BatchStartResponse>(
    `/api/papers/batch-start?${params.toString()}`,
    { method: "POST" },
    "Batch analysis failed.",
  );
}
