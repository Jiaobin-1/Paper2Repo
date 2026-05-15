import type { LanguageCode, Run } from "./types";

export const WORKFLOW_STEPS = [
  { key: "parse_pdf_node", label: { zh: "解析 PDF", en: "Parse PDF" } },
  { key: "chunk_paper_node", label: { zh: "切分论文", en: "Chunk Paper" } },
  { key: "extract_citations_node", label: { zh: "提取引用", en: "Extract Citations" } },
  { key: "extract_metadata_node", label: { zh: "提取元信息", en: "Extract Metadata" } },
  { key: "classify_paper_type_node", label: { zh: "判断论文类型", en: "Classify Paper" } },
  { key: "understand_paper_node", label: { zh: "理解论文", en: "Understand Paper" } },
  { key: "analyze_method_node", label: { zh: "拆解方法", en: "Analyze Method" } },
  { key: "analyze_experiments_node", label: { zh: "分析实验", en: "Analyze Experiments" } },
  { key: "plan_reproduction_node", label: { zh: "规划复现", en: "Plan Reproduction" } },
  { key: "generate_report_node", label: { zh: "生成报告", en: "Generate Report" } },
  { key: "persist_result_node", label: { zh: "保存结果", en: "Save Results" } },
] as const;

export type StepState = "done" | "active" | "pending" | "failed";

export function formatRunStatus(status: string | null | undefined, language: LanguageCode = "zh"): string {
  const labels = {
    zh: {
      pending: "等待中",
      running: "分析中",
      completed: "已完成",
      failed: "失败",
      unknown: "等待启动",
    },
    en: {
      pending: "Pending",
      running: "Running",
      completed: "Completed",
      failed: "Failed",
      unknown: "Not started",
    },
  };
  switch (status) {
    case "pending":
      return labels[language].pending;
    case "running":
      return labels[language].running;
    case "completed":
      return labels[language].completed;
    case "failed":
      return labels[language].failed;
    default:
      return labels[language].unknown;
  }
}

export function formatStepLabel(step: string | null | undefined, language: LanguageCode = "zh"): string {
  if (!step) {
    return language === "en" ? "Waiting to start" : "等待开始";
  }
  if (step === "queued") {
    return language === "en" ? "Queued" : "排队中";
  }
  if (step === "completed") {
    return language === "en" ? "Completed" : "已完成";
  }
  if (step === "failed") {
    return language === "en" ? "Failed" : "失败";
  }
  return WORKFLOW_STEPS.find((item) => item.key === step)?.label[language] ?? (language === "en" ? `Unknown step (${step})` : `未知步骤（${step}）`);
}

export function formatProgressMessage(run: Run | null, language: LanguageCode = "zh"): string {
  if (!run) {
    return language === "en" ? "Waiting to start analysis." : "等待启动分析。";
  }
  if (run.status === "completed") {
    return language === "en" ? "Analysis complete. Report generated." : "分析完成，报告已生成。";
  }
  if (run.status === "failed") {
    return run.error_message || (language === "en" ? "Analysis failed." : "分析失败。");
  }
  return language === "en"
    ? `Running: ${formatStepLabel(run.current_step, language)} (${displayProgressPercent(run)}%)`
    : `正在执行：${formatStepLabel(run.current_step, language)}（${displayProgressPercent(run)}%）`;
}

export function formatRunStatusWithProgress(run: Run | null, language: LanguageCode = "zh"): string {
  if (!run) {
    return language === "en" ? "Not started" : "等待启动";
  }
  return `${formatRunStatus(run.status, language)} · ${displayProgressPercent(run)}%`;
}

export function formatRunTiming(run: Run, language: LanguageCode = "zh", now: Date = new Date()): string {
  const updatedAt = Date.parse(run.updated_at);
  if (Number.isNaN(updatedAt)) {
    return language === "en" ? "Last update unknown" : "最近更新时间未知";
  }
  const elapsed = formatElapsed(now.getTime() - updatedAt, language);
  if (run.status === "running") {
    return language === "en" ? `Current step elapsed: ${elapsed}` : `当前步骤已运行：${elapsed}`;
  }
  return language === "en" ? `Last updated: ${elapsed} ago` : `最近更新：${elapsed}前`;
}

export function getStepStates(run: Run): StepState[] {
  const progress = displayProgressPercent(run);
  const completedByProgress = Math.min(WORKFLOW_STEPS.length, Math.floor(progress / stepPercent()));
  const currentIndex = WORKFLOW_STEPS.findIndex((step) => step.key === run.current_step);

  if (run.status === "completed") {
    return WORKFLOW_STEPS.map(() => "done");
  }

  if (run.status === "failed") {
    const failedIndex = currentIndex >= 0 ? currentIndex : Math.min(completedByProgress, WORKFLOW_STEPS.length - 1);
    return WORKFLOW_STEPS.map((_, index) => {
      if (index < failedIndex) return "done";
      if (index === failedIndex) return "failed";
      return "pending";
    });
  }

  const inferredActiveIndex =
    currentIndex >= 0 && completedByProgress > currentIndex
      ? Math.min(completedByProgress, WORKFLOW_STEPS.length - 1)
      : currentIndex;

  return WORKFLOW_STEPS.map((_, index) => {
    if (index < completedByProgress) return "done";
    if (index === inferredActiveIndex) return "active";
    return "pending";
  });
}

export function boundedProgress(value: number | null | undefined): number {
  return Math.max(0, Math.min(100, value ?? 0));
}

export function displayProgressPercent(run: Pick<Run, "status" | "progress_percent"> | null | undefined): number {
  if (!run) {
    return 0;
  }
  if (run.status === "completed") {
    return 100;
  }
  return boundedProgress(run.progress_percent);
}

function stepPercent(): number {
  return 100 / WORKFLOW_STEPS.length;
}

function formatElapsed(durationMs: number, language: LanguageCode): string {
  const seconds = Math.max(0, Math.floor(durationMs / 1000));
  if (seconds < 60) {
    return language === "en" ? `${seconds}s` : `${seconds}秒`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return language === "en" ? `${minutes}m` : `${minutes}分钟`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return language === "en" ? `${hours}h` : `${hours}小时`;
  }
  const days = Math.floor(hours / 24);
  return language === "en" ? `${days}d` : `${days}天`;
}
