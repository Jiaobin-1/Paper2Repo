import type { LlmConfig, Paper, Report, Run, RunListItem } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function uploadPaper(file: File): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/papers/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Upload failed."));
  }

  return response.json();
}

export async function startAnalysis(paperId: string): Promise<Run> {
  const response = await fetch(`${API_BASE_URL}/api/papers/${paperId}/runs`, {
    method: "POST",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Analysis failed."));
  }

  return response.json();
}

export async function getRun(runId: string): Promise<Run> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Failed to load run."));
  }

  return response.json();
}

export async function listRuns(options: { paperId?: string; limit?: number } = {}): Promise<RunListItem[]> {
  const params = new URLSearchParams();
  if (options.paperId) {
    params.set("paper_id", options.paperId);
  }
  if (options.limit) {
    params.set("limit", String(options.limit));
  }
  const query = params.toString();
  const response = await fetch(`${API_BASE_URL}/api/runs${query ? `?${query}` : ""}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Failed to load runs."));
  }

  return response.json();
}

export async function getReport(runId: string): Promise<Report> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/report`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Failed to load report."));
  }

  return response.json();
}

export function getReportPdfUrl(runId: string): string {
  return `${API_BASE_URL}/api/runs/${runId}/report.pdf`;
}

export function getReportMarkdownUrl(runId: string): string {
  return `${API_BASE_URL}/api/runs/${runId}/report.md`;
}

export async function getLlmConfig(): Promise<LlmConfig> {
  const response = await fetch(`${API_BASE_URL}/api/llm/config`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Failed to load LLM config."));
  }

  return response.json();
}

export async function updateLlmConfig(defaultModel: string): Promise<LlmConfig> {
  const response = await fetch(`${API_BASE_URL}/api/llm/config`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ default_model: defaultModel }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Failed to update LLM config."));
  }

  return response.json();
}

function formatApiError(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg ?? JSON.stringify(item)).join("; ");
  }
  return "Request failed.";
}
