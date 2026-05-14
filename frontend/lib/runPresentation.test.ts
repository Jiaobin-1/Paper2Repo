import { describe, expect, it } from "vitest";
import type { Run } from "./types";
import {
  WORKFLOW_STEPS,
  boundedProgress,
  displayProgressPercent,
  formatProgressMessage,
  formatRunStatus,
  formatRunStatusWithProgress,
  formatStepLabel,
  getStepStates,
} from "./runPresentation";

function makeRun(overrides: Partial<Run> = {}): Run {
  return {
    id: "run-1",
    paper_id: "paper-1",
    status: "pending",
    model_name: "gpt-4o",
    current_step: null,
    progress_percent: 0,
    error_message: null,
    started_at: null,
    completed_at: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("WORKFLOW_STEPS", () => {
  it("has 10 steps", () => {
    expect(WORKFLOW_STEPS).toHaveLength(10);
  });

  it("starts with parse_pdf_node", () => {
    expect(WORKFLOW_STEPS[0].key).toBe("parse_pdf_node");
  });

  it("ends with persist_result_node", () => {
    expect(WORKFLOW_STEPS[WORKFLOW_STEPS.length - 1].key).toBe("persist_result_node");
  });
});

describe("boundedProgress", () => {
  it("clamps to 0-100", () => {
    expect(boundedProgress(-10)).toBe(0);
    expect(boundedProgress(150)).toBe(100);
    expect(boundedProgress(50)).toBe(50);
  });

  it("handles null/undefined", () => {
    expect(boundedProgress(null)).toBe(0);
    expect(boundedProgress(undefined)).toBe(0);
  });
});

describe("displayProgressPercent", () => {
  it("forces completed runs to 100 percent", () => {
    expect(displayProgressPercent(makeRun({ status: "completed", progress_percent: 0 }))).toBe(100);
  });

  it("clamps non-completed runs", () => {
    expect(displayProgressPercent(makeRun({ status: "running", progress_percent: 120 }))).toBe(100);
    expect(displayProgressPercent(makeRun({ status: "running", progress_percent: -5 }))).toBe(0);
  });
});

describe("formatRunStatus", () => {
  it("returns Chinese labels by default", () => {
    expect(formatRunStatus("pending")).toBe("等待中");
    expect(formatRunStatus("running")).toBe("分析中");
    expect(formatRunStatus("completed")).toBe("已完成");
    expect(formatRunStatus("failed")).toBe("失败");
  });

  it("returns English labels when specified", () => {
    expect(formatRunStatus("pending", "en")).toBe("Pending");
    expect(formatRunStatus("running", "en")).toBe("Running");
    expect(formatRunStatus("completed", "en")).toBe("Completed");
    expect(formatRunStatus("failed", "en")).toBe("Failed");
  });

  it("handles null/unknown status", () => {
    expect(formatRunStatus(null)).toBe("等待启动");
    expect(formatRunStatus("unknown_status", "en")).toBe("Not started");
  });
});

describe("formatStepLabel", () => {
  it("returns known step labels in Chinese", () => {
    expect(formatStepLabel("parse_pdf_node")).toBe("解析 PDF");
    expect(formatStepLabel("generate_report_node")).toBe("生成报告");
  });

  it("returns known step labels in English", () => {
    expect(formatStepLabel("parse_pdf_node", "en")).toBe("Parse PDF");
    expect(formatStepLabel("generate_report_node", "en")).toBe("Generate Report");
  });

  it("handles special steps", () => {
    expect(formatStepLabel(null)).toBe("等待开始");
    expect(formatStepLabel("queued")).toBe("排队中");
    expect(formatStepLabel("completed")).toBe("已完成");
    expect(formatStepLabel("failed")).toBe("失败");
  });

  it("handles unknown step key", () => {
    expect(formatStepLabel("nonexistent_step", "en")).toContain("Unknown step");
  });
});

describe("formatProgressMessage", () => {
  it("handles null run", () => {
    expect(formatProgressMessage(null)).toBe("等待启动分析。");
    expect(formatProgressMessage(null, "en")).toBe("Waiting to start analysis.");
  });

  it("shows completion message", () => {
    const run = makeRun({ status: "completed" });
    expect(formatProgressMessage(run, "en")).toBe("Analysis complete. Report generated.");
  });

  it("shows error message for failed run", () => {
    const run = makeRun({ status: "failed", error_message: "PDF corrupted" });
    expect(formatProgressMessage(run, "en")).toBe("PDF corrupted");
  });

  it("shows progress for running run", () => {
    const run = makeRun({ status: "running", current_step: "parse_pdf_node", progress_percent: 20 });
    const msg = formatProgressMessage(run, "en");
    expect(msg).toContain("Running");
    expect(msg).toContain("20%");
  });
});

describe("formatRunStatusWithProgress", () => {
  it("formats status with progress percentage", () => {
    const run = makeRun({ status: "running", progress_percent: 45 });
    expect(formatRunStatusWithProgress(run, "en")).toBe("Running · 45%");
  });

  it("shows 100 percent for completed runs even if stored progress is stale", () => {
    const run = makeRun({ status: "completed", progress_percent: 0 });
    expect(formatRunStatusWithProgress(run, "en")).toBe("Completed · 100%");
  });

  it("handles null run", () => {
    expect(formatRunStatusWithProgress(null, "en")).toBe("Not started");
  });
});

describe("getStepStates", () => {
  it("all done when completed", () => {
    const run = makeRun({ status: "completed", progress_percent: 100 });
    const states = getStepStates(run);
    expect(states).toHaveLength(10);
    expect(states.every((s) => s === "done")).toBe(true);
  });

  it("marks failed step and steps before as done", () => {
    const run = makeRun({ status: "failed", current_step: "extract_metadata_node", progress_percent: 30 });
    const states = getStepStates(run);
    expect(states[0]).toBe("done");
    expect(states[1]).toBe("done");
    expect(states[2]).toBe("failed");
    expect(states[3]).toBe("pending");
  });

  it("marks active step for running status", () => {
    const run = makeRun({ status: "running", current_step: "chunk_paper_node", progress_percent: 15 });
    const states = getStepStates(run);
    expect(states[0]).toBe("done");
    expect(states[1]).toBe("active");
    expect(states[2]).toBe("pending");
  });
});
