import { requestJson } from "./client";
import type { CitationEdge, CitationInfo } from "../types";

export function getCitations(
  runId: string,
): Promise<{ run_id: string; paper_id: string; citations: CitationInfo[] }> {
  return requestJson<{ run_id: string; paper_id: string; citations: CitationInfo[] }>(
    `/api/runs/${runId}/citations`,
    {},
    "Citations load failed.",
  );
}

export function getCitationNetwork(paperIds: string[]): Promise<{ edges: CitationEdge[] }> {
  const params = new URLSearchParams({ paper_ids: paperIds.join(",") });
  return requestJson<{ edges: CitationEdge[] }>(`/api/citations/network?${params.toString()}`, {}, "Citation network failed.");
}
