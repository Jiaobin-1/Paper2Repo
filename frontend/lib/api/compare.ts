import { requestJson } from "./client";
import type { AvailableRun, ComparisonRun } from "../types";

export function getAvailableRuns(): Promise<AvailableRun[]> {
  return requestJson<AvailableRun[]>("/api/compare/available", {}, "可比较任务加载失败。");
}

export function compareRuns(runIds: string[]): Promise<ComparisonRun[]> {
  const params = new URLSearchParams();
  params.set("run_ids", runIds.join(","));
  return requestJson<ComparisonRun[]>(`/api/compare?${params.toString()}`, {}, "比较失败。");
}
