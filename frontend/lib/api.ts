import type { AppSettings, AppSettingsUpdate, ArxivInfo, AvailableRun, BatchStartResponse, BatchStatusResponse, BatchUploadResponse, CitationInfo, CitationEdge, ComparisonRun, KnowledgePaper, KnowledgeSearchResult, LlmCheck, LlmConfig, Paper, PwcLink, QaMessage, Report, Run, RunListItem } from "./types";

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
    throw new Error(formatApiError(body?.detail ?? "上传失败。"));
  }

  return response.json();
}

export async function startAnalysis(paperId: string): Promise<Run> {
  const response = await fetch(`${API_BASE_URL}/api/papers/${paperId}/runs`, {
    method: "POST",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "分析启动失败。"));
  }

  return response.json();
}

export async function getRun(runId: string): Promise<Run> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "任务状态加载失败。"));
  }

  return response.json();
}

export async function deleteRun(runId: string): Promise<Run> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "删除分析记录失败。"));
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
    throw new Error(formatApiError(body?.detail ?? "最近分析加载失败。"));
  }

  return response.json();
}

export async function getReport(runId: string): Promise<Report> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/report`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "报告加载失败。"));
  }

  return response.json();
}

export function getReportPdfUrl(runId: string): string {
  return `${API_BASE_URL}/api/runs/${runId}/report.pdf`;
}

export function getReportMarkdownUrl(runId: string): string {
  return `${API_BASE_URL}/api/runs/${runId}/report.md`;
}

export function getReportHtmlUrl(runId: string): string {
  return `${API_BASE_URL}/api/runs/${runId}/report.html`;
}

export function getReportLatexUrl(runId: string): string {
  return `${API_BASE_URL}/api/runs/${runId}/report.tex`;
}

export function getSkeletonUrl(runId: string): string {
  return `${API_BASE_URL}/api/runs/${runId}/skeleton`;
}

export async function getLlmConfig(): Promise<LlmConfig> {
  const response = await fetch(`${API_BASE_URL}/api/llm/config`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "模型配置加载失败。"));
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
    throw new Error(formatApiError(body?.detail ?? "模型配置更新失败。"));
  }

  return response.json();
}

export async function checkLlmConnection(): Promise<LlmCheck> {
  const response = await fetch(`${API_BASE_URL}/api/llm/check`, {
    method: "POST",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "模型连接测试失败。"));
  }

  return response.json();
}

export async function getAppSettings(): Promise<AppSettings> {
  const response = await fetch(`${API_BASE_URL}/api/settings`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "设置加载失败。"));
  }

  return response.json();
}

export async function updateAppSettings(payload: AppSettingsUpdate): Promise<AppSettings> {
  const response = await fetch(`${API_BASE_URL}/api/settings`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "设置保存失败。"));
  }

  return response.json();
}

export async function getQaHistory(runId: string): Promise<QaMessage[]> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/qa`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "对话历史加载失败。"));
  }

  return response.json();
}

export async function askQuestion(runId: string, question: string): Promise<QaMessage[]> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/qa`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "提问失败。"));
  }

  return response.json();
}

export interface StreamEvent {
  type: "token" | "done" | "error";
  content?: string;
  message_id?: string;
}

export async function* askQuestionStream(
  runId: string,
  question: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/qa/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
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
          // skip malformed SSE lines
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function getAvailableRuns(): Promise<AvailableRun[]> {
  const response = await fetch(`${API_BASE_URL}/api/compare/available`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "可比较任务加载失败。"));
  }

  return response.json();
}

export async function compareRuns(runIds: string[]): Promise<ComparisonRun[]> {
  const params = new URLSearchParams();
  params.set("run_ids", runIds.join(","));
  const response = await fetch(`${API_BASE_URL}/api/compare?${params.toString()}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "比较失败。"));
  }

  return response.json();
}

export async function importArxiv(arxivId: string): Promise<Paper> {
  const response = await fetch(`${API_BASE_URL}/api/arxiv/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ arxiv_id: arxivId }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "arXiv 导入失败。"));
  }

  return response.json();
}

export async function getArxivInfo(arxivId: string): Promise<ArxivInfo> {
  const response = await fetch(`${API_BASE_URL}/api/arxiv/${encodeURIComponent(arxivId)}/versions`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "arXiv 版本加载失败。"));
  }

  return response.json();
}

export async function searchKnowledge(query: string, topK: number = 10): Promise<KnowledgeSearchResult[]> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  const response = await fetch(`${API_BASE_URL}/api/knowledge/search?${params.toString()}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "知识库搜索失败。"));
  }

  return response.json();
}

export async function getKnowledgePapers(): Promise<KnowledgePaper[]> {
  const response = await fetch(`${API_BASE_URL}/api/knowledge/papers`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "知识库论文加载失败。"));
  }

  return response.json();
}

export async function getPwcLinks(runId: string): Promise<PwcLink[]> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/pwc-links`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Papers With Code 链接加载失败。"));
  }

  const data = await response.json();
  return data.links ?? [];
}

export async function getCitations(runId: string): Promise<{ run_id: string; paper_id: string; citations: CitationInfo[] }> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/citations`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Citations load failed."));
  }

  return response.json();
}

export async function getCitationNetwork(paperIds: string[]): Promise<{ edges: CitationEdge[] }> {
  const params = new URLSearchParams({ paper_ids: paperIds.join(",") });
  const response = await fetch(`${API_BASE_URL}/api/citations/network?${params.toString()}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Citation network failed."));
  }

  return response.json();
}

export async function uploadPapers(files: File[]): Promise<BatchUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${API_BASE_URL}/api/papers/upload-batch`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Batch upload failed."));
  }

  return response.json();
}

export async function startBatchAnalysis(paperIds: string[]): Promise<BatchStartResponse> {
  const params = new URLSearchParams({ paper_ids: paperIds.join(",") });
  const response = await fetch(`${API_BASE_URL}/api/papers/batch-start?${params.toString()}`, {
    method: "POST",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Batch analysis failed."));
  }

  return response.json();
}

export async function getBatchStatus(batchId: string): Promise<BatchStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/runs/batches/${batchId}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body?.detail ?? "Batch status failed."));
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
  return "请求失败。";
}
