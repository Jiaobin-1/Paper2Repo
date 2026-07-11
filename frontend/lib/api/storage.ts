import { requestJson } from "./client";
import type { StorageCleanupResult, StorageSummary } from "../types";

export function getStorageSummary(): Promise<StorageSummary> {
  return requestJson<StorageSummary>("/api/storage/summary", {}, "存储信息加载失败。");
}

export function cleanupStorage(dryRun = false): Promise<StorageCleanupResult> {
  const params = new URLSearchParams({ dry_run: String(dryRun) });
  return requestJson<StorageCleanupResult>(
    `/api/storage/cleanup?${params.toString()}`,
    { method: "POST" },
    "存储清理失败。",
  );
}
