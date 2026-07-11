import { requestJson } from "./client";
import type { KnowledgePaper, KnowledgeSearchResult } from "../types";

export function searchKnowledge(query: string, topK: number = 10): Promise<KnowledgeSearchResult[]> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  return requestJson<KnowledgeSearchResult[]>(`/api/knowledge/search?${params.toString()}`, {}, "知识库搜索失败。");
}

export function getKnowledgePapers(): Promise<KnowledgePaper[]> {
  return requestJson<KnowledgePaper[]>("/api/knowledge/papers", {}, "知识库论文加载失败。");
}
