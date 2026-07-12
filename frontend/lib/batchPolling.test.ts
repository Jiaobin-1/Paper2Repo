import { beforeEach, describe, expect, it, vi } from "vitest";
import { getBatchStatus } from "./api";
import { isTerminalBatch, pollBatchUntilTerminal } from "./batchPolling";
import type { BatchStatusResponse, RunListItem } from "./types";

vi.mock("./api", () => ({
  getBatchStatus: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(getBatchStatus).mockReset();
});

function makeRun(id: string, status = "running"): RunListItem {
  const paperId = `paper-${id}`;
  return {
    id,
    paper_id: paperId,
    paper_title: null,
    paper_filename: `${paperId}.pdf`,
    status,
    model_name: "test-model",
    current_step: status === "completed" ? "completed" : "parse_pdf_node",
    progress_percent: status === "completed" ? 100 : 10,
    error_message: status === "failed" ? "analysis failed" : null,
    started_at: "2026-01-01T00:00:00Z",
    completed_at: status === "running" ? null : "2026-01-01T00:01:00Z",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:01:00Z",
  };
}

function makeBatch(runs: RunListItem[]): BatchStatusResponse {
  return { batch_id: "batch-1", runs };
}

describe("pollBatchUntilTerminal", () => {
  it("polls one aggregate endpoint until every run is terminal", async () => {
    const onBatch = vi.fn();
    vi.mocked(getBatchStatus)
      .mockResolvedValueOnce(makeBatch([makeRun("run-1"), makeRun("run-2")]))
      .mockResolvedValueOnce(makeBatch([makeRun("run-1", "completed"), makeRun("run-2", "failed")]));

    const batch = await pollBatchUntilTerminal(
      "batch-1",
      { onBatch },
      { intervalMs: 0, maxAttempts: 3 },
    );

    expect(batch.runs.map((run) => run.status)).toEqual(["completed", "failed"]);
    expect(getBatchStatus).toHaveBeenCalledTimes(2);
    expect(onBatch).toHaveBeenCalledTimes(2);
  });

  it("retries transient failures without treating the batch as terminal", async () => {
    const onRetry = vi.fn();
    vi.mocked(getBatchStatus)
      .mockRejectedValueOnce(new Error("temporary"))
      .mockResolvedValueOnce(makeBatch([makeRun("run-1", "completed")]));

    const batch = await pollBatchUntilTerminal(
      "batch-1",
      { onRetry },
      { intervalMs: 0, maxAttempts: 3, maxConsecutiveErrors: 2 },
    );

    expect(batch.runs[0].status).toBe("completed");
    expect(onRetry).toHaveBeenCalledWith(1);
  });

  it("passes abort signals through and preserves abort errors", async () => {
    const controller = new AbortController();
    const abortError = new DOMException("Aborted", "AbortError");
    vi.mocked(getBatchStatus).mockRejectedValueOnce(abortError);

    await expect(
      pollBatchUntilTerminal(
        "batch-1",
        {},
        { signal: controller.signal, intervalMs: 0, maxConsecutiveErrors: 1 },
      ),
    ).rejects.toBe(abortError);
    expect(getBatchStatus).toHaveBeenCalledWith("batch-1", { signal: controller.signal });
  });

  it("stops after bounded consecutive monitoring failures", async () => {
    vi.mocked(getBatchStatus).mockRejectedValue(new Error("offline"));

    await expect(
      pollBatchUntilTerminal(
        "batch-1",
        {},
        { intervalMs: 0, maxAttempts: 5, maxConsecutiveErrors: 2, language: "en" },
      ),
    ).rejects.toThrow("Batch monitoring stopped");
    expect(getBatchStatus).toHaveBeenCalledTimes(2);
  });
});

describe("isTerminalBatch", () => {
  it("requires a non-empty batch with only completed or failed runs", () => {
    expect(isTerminalBatch(makeBatch([]))).toBe(false);
    expect(isTerminalBatch(makeBatch([makeRun("run-1", "completed"), makeRun("run-2")]))).toBe(false);
    expect(isTerminalBatch(makeBatch([makeRun("run-1", "completed"), makeRun("run-2", "failed")]))).toBe(true);
  });
});
