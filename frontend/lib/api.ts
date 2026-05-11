import type { Paper, Report, Run } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function uploadPaper(file: File): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/papers/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Upload failed.");
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

export async function getReport(runId: string): Promise<Report> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/report`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Failed to load report."));
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
