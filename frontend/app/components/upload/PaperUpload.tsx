"use client";

import { useState } from "react";
import { getReport, getRun, startAnalysis, uploadPaper } from "../../../lib/api";
import type { Paper, Report, Run } from "../../../lib/types";

const WORKFLOW_STEPS = [
  { key: "parse_pdf_node", label: "解析 PDF" },
  { key: "chunk_paper_node", label: "切分论文" },
  { key: "extract_metadata_node", label: "提取元信息" },
  { key: "classify_paper_type_node", label: "判断论文类型" },
  { key: "understand_paper_node", label: "理解论文" },
  { key: "analyze_method_node", label: "拆解方法" },
  { key: "analyze_experiments_node", label: "分析实验" },
  { key: "plan_reproduction_node", label: "规划复现" },
  { key: "generate_report_node", label: "生成报告" },
  { key: "persist_result_node", label: "保存结果" },
];

export default function PaperUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [paper, setPaper] = useState<Paper | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [message, setMessage] = useState("选择一篇 PDF 后开始本地分析。");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  async function handleUpload() {
    if (!file) {
      setMessage("请先选择 PDF 文件。");
      return;
    }
    setIsUploading(true);
    setPaper(null);
    setRun(null);
    setReport(null);
    setMessage("正在上传 PDF...");
    try {
      const uploadedPaper = await uploadPaper(file);
      setPaper(uploadedPaper);
      setMessage("上传成功，可以启动分析。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "上传失败。");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAnalyze() {
    if (!paper) {
      setMessage("请先上传 PDF。");
      return;
    }

    setIsAnalyzing(true);
    setRun(null);
    setReport(null);
    setMessage("正在运行论文理解与复现规划流程...");
    try {
      const startedRun = await startAnalysis(paper.id);
      setRun(startedRun);
      let latestRun = startedRun;
      setMessage("任务已提交，正在分析...");

      for (let attempt = 0; attempt < 600; attempt += 1) {
        await sleep(1000);
        latestRun = await getRun(startedRun.id);
        setRun(latestRun);

        if (latestRun.status === "completed") {
          const generatedReport = await getReport(latestRun.id);
          setReport(generatedReport);
          setMessage("分析完成，报告已生成。");
          return;
        }

        if (latestRun.status === "failed") {
          setMessage(latestRun.error_message ?? "分析失败。");
          return;
        }

        setMessage(`正在执行：${stepLabel(latestRun.current_step)} (${latestRun.progress_percent}%)`);
      }
      setMessage("分析仍在运行，请稍后刷新任务状态。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "分析失败。");
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <div className="stack">
      <div className="upload-row">
        <input
          className="input"
          type="file"
          accept="application/pdf"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <button className="button" type="button" disabled={isUploading || isAnalyzing} onClick={handleUpload}>
          {isUploading ? "上传中..." : "上传 PDF"}
        </button>
        <button className="button secondary" type="button" disabled={!paper || isUploading || isAnalyzing} onClick={handleAnalyze}>
          {isAnalyzing ? "分析中..." : "启动分析"}
        </button>
      </div>

      <p className="muted">{message}</p>

      <div className="grid">
        <InfoBlock title="Paper ID" value={paper?.id ?? "上传后显示"} />
        <InfoBlock title="Run ID" value={run?.id ?? "启动分析后显示"} />
        <InfoBlock title="Run 状态" value={run ? `${run.status} · ${run.progress_percent}%` : "pending"} />
      </div>

      {run ? <WorkflowProgress run={run} /> : null}

      {paper ? (
        <section className="sub-panel">
          <h3>已上传论文</h3>
          <p>
            <strong>{paper.filename}</strong>
          </p>
          <p className="muted">文件大小：{paper.file_size} bytes</p>
        </section>
      ) : null}

      {run?.error_message ? (
        <section className="error-box">
          <h3>任务错误</h3>
          <p>{run.error_message}</p>
        </section>
      ) : null}

      {report ? (
        <section className="report-viewer">
          <div className="report-header">
            <div>
              <h3>{report.title}</h3>
              <p className="muted">报告路径：{report.file_path}</p>
            </div>
          </div>
          <pre>{report.content}</pre>
        </section>
      ) : null}
    </div>
  );
}

function InfoBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="status-card">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}

function WorkflowProgress({ run }: { run: Run }) {
  const progress = Math.max(0, Math.min(100, run.progress_percent ?? 0));

  return (
    <section className="progress-panel">
      <div className="progress-header">
        <div>
          <h3>分析进度</h3>
          <p className="muted">当前步骤：{stepLabel(run.current_step)}</p>
        </div>
        <strong>{progress}%</strong>
      </div>
      <div className="progress-track" aria-label="analysis progress">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <ol className="stepper">
        {WORKFLOW_STEPS.map((step, index) => {
          const stepDoneThreshold = Math.round(((index + 1) / WORKFLOW_STEPS.length) * 100);
          const isComplete = run.status === "completed" || progress >= stepDoneThreshold;
          const isActive = run.current_step === step.key && run.status !== "completed";
          return (
            <li key={step.key} className={isComplete ? "done" : isActive ? "active" : ""}>
              <span>{isComplete ? "✓" : index + 1}</span>
              <strong>{step.label}</strong>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function stepLabel(step: string | null): string {
  if (!step) {
    return "等待开始";
  }
  if (step === "queued") {
    return "排队中";
  }
  if (step === "completed") {
    return "已完成";
  }
  if (step === "failed") {
    return "失败";
  }
  return WORKFLOW_STEPS.find((item) => item.key === step)?.label ?? step;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
