import { apiUrl, requestJson } from "./client";
import type { BatchStatusResponse, LlmUsageSummary, QueueStatus, Report, Run, RunListItem } from "../types";

type StatusRequestOptions = {
  signal?: AbortSignal;
};

export function getRun(runId: string, options: StatusRequestOptions = {}): Promise<Run> {
  return requestJson<Run>(`/api/runs/${runId}`, { signal: options.signal }, "任务状态加载失败。");
}

export function deleteRun(runId: string): Promise<Run> {
  return requestJson<Run>(`/api/runs/${runId}`, { method: "DELETE" }, "删除分析记录失败。");
}

export function listRuns(options: { paperId?: string; limit?: number } = {}): Promise<RunListItem[]> {
  const params = new URLSearchParams();
  if (options.paperId) {
    params.set("paper_id", options.paperId);
  }
  if (options.limit) {
    params.set("limit", String(options.limit));
  }
  const query = params.toString();
  return requestJson<RunListItem[]>(`/api/runs${query ? `?${query}` : ""}`, {}, "最近分析加载失败。");
}

export function getReport(runId: string): Promise<Report> {
  return requestJson<Report>(`/api/runs/${runId}/report`, {}, "报告加载失败。");
}

export function getRunUsage(runId: string): Promise<LlmUsageSummary> {
  return requestJson<LlmUsageSummary>(`/api/runs/${runId}/usage`, {}, "模型用量加载失败。");
}

export function getQueueStatus(): Promise<QueueStatus> {
  return requestJson<QueueStatus>("/api/runs/queue", {}, "队列状态加载失败。");
}

export function getReportPdfUrl(runId: string): string {
  return apiUrl(`/api/runs/${runId}/report.pdf`);
}

export function getReportMarkdownUrl(runId: string): string {
  return apiUrl(`/api/runs/${runId}/report.md`);
}

export function getReportHtmlUrl(runId: string): string {
  return apiUrl(`/api/runs/${runId}/report.html`);
}

export function getReportLatexUrl(runId: string): string {
  return apiUrl(`/api/runs/${runId}/report.tex`);
}

export function getSkeletonUrl(runId: string): string {
  return apiUrl(`/api/runs/${runId}/skeleton`);
}

export function getBatchStatus(
  batchId: string,
  options: StatusRequestOptions = {},
): Promise<BatchStatusResponse> {
  return requestJson<BatchStatusResponse>(
    `/api/runs/batches/${batchId}`,
    { signal: options.signal },
    "Batch status failed.",
  );
}
