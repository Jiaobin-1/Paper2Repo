import { requestJson } from "./client";
import type { PwcLink } from "../types";

export async function getPwcLinks(runId: string): Promise<PwcLink[]> {
  const data = await requestJson<{ links?: PwcLink[] }>(
    `/api/runs/${runId}/pwc-links`,
    {},
    "Papers With Code 链接加载失败。",
  );
  return data.links ?? [];
}
