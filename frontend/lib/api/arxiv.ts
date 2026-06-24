import { jsonRequestOptions, requestJson } from "./client";
import type { ArxivInfo, Paper } from "../types";

export function importArxiv(arxivId: string): Promise<Paper> {
  return requestJson<Paper>(
    "/api/arxiv/import",
    jsonRequestOptions({ arxiv_id: arxivId }),
    "arXiv 导入失败。",
  );
}

export function getArxivInfo(arxivId: string): Promise<ArxivInfo> {
  return requestJson<ArxivInfo>(
    `/api/arxiv/${encodeURIComponent(arxivId)}/versions`,
    {},
    "arXiv 版本加载失败。",
  );
}
