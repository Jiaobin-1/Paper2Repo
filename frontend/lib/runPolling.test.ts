import { describe, expect, it, vi } from "vitest";
import { getRun } from "./api";
import { pollRunUntilTerminal } from "./runPolling";
import type { Run } from "./types";

vi.mock("./api", () => ({
  getRun: vi.fn(),
}));

function makeRun(overrides: Partial<Run> = {}): Run {
  return {
    id: "run-1",
    paper_id: "paper-1",
    status: "running",
    model_name: "test-model",
    current_step: "parse_pdf_node",
    progress_percent: 10,
    error_message: null,
    started_at: "2026-01-01T00:00:00Z",
    completed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("pollRunUntilTerminal", () => {
  it("retries transient getRun failures", async () => {
    const onRetry = vi.fn();
    vi.mocked(getRun)
      .mockRejectedValueOnce(new Error("temporary"))
      .mockResolvedValueOnce(makeRun({ status: "completed", current_step: "completed", progress_percent: 100 }));

    const run = await pollRunUntilTerminal(
      "run-1",
      { onRetry },
      { intervalMs: 0, maxAttempts: 3, maxConsecutiveErrors: 2, language: "en" },
    );

    expect(run.status).toBe("completed");
    expect(onRetry).toHaveBeenCalledWith(1);
  });

  it("passes abort signals to getRun", async () => {
    const controller = new AbortController();
    vi.mocked(getRun).mockResolvedValueOnce(makeRun({ status: "completed" }));

    await pollRunUntilTerminal("run-1", {}, { signal: controller.signal, intervalMs: 0 });

    expect(getRun).toHaveBeenCalledWith("run-1", { signal: controller.signal });
  });

  it("does not convert aborts into network lost errors", async () => {
    const abortError = new DOMException("Aborted", "AbortError");
    const onRetry = vi.fn();
    vi.mocked(getRun).mockRejectedValueOnce(abortError);

    await expect(
      pollRunUntilTerminal(
        "run-1",
        { onRetry },
        { intervalMs: 0, maxAttempts: 3, maxConsecutiveErrors: 1, language: "en" },
      ),
    ).rejects.toBe(abortError);
    expect(onRetry).not.toHaveBeenCalled();
  });
});
