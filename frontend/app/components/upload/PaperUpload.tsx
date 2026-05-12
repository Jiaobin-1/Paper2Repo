"use client";

import { useEffect, useRef, useState, type ChangeEvent } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  getLlmConfig,
  getReport,
  getReportMarkdownUrl,
  getReportPdfUrl,
  getRun,
  startAnalysis,
  updateLlmConfig,
  uploadPaper,
} from "../../../lib/api";
import type { LlmConfig, Paper, Report, Run } from "../../../lib/types";

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
  const [llmConfig, setLlmConfig] = useState<LlmConfig | null>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [message, setMessage] = useState("选择一篇 PDF 后开始本地分析。");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSavingModel, setIsSavingModel] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const pollingAbortRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragCountRef = useRef(0);

  useEffect(() => {
    return () => {
      pollingAbortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    getLlmConfig()
      .then((config) => {
        if (!isMounted) {
          return;
        }
        setLlmConfig(config);
        setSelectedModel(config.default_model);
        if (!config.configured) {
          setMessage("LLM 未配置，将使用本地 fallback。");
        }
      })
      .catch((error) => {
        if (!isMounted) {
          return;
        }
        setMessage(error instanceof Error ? error.message : "模型配置加载失败。");
      });

    return () => {
      isMounted = false;
    };
  }, []);

  function validateAndSetFile(f: File): boolean {
    if (f.type !== "application/pdf") {
      setMessage("仅支持 PDF 文件。");
      return false;
    }
    const MAX_SIZE = 50 * 1024 * 1024; // 50 MB
    if (f.size > MAX_SIZE) {
      setMessage(`文件过大（${formatFileSize(f.size)}），上限 50 MB。`);
      return false;
    }
    setFile(f);
    return true;
  }

  function handleDragEnter(event: React.DragEvent) {
    event.preventDefault();
    dragCountRef.current += 1;
    setIsDragging(true);
  }

  function handleDragOver(event: React.DragEvent) {
    event.preventDefault();
  }

  function handleDragLeave(event: React.DragEvent) {
    event.preventDefault();
    dragCountRef.current -= 1;
    if (dragCountRef.current <= 0) {
      dragCountRef.current = 0;
      setIsDragging(false);
    }
  }

  function handleDrop(event: React.DragEvent) {
    event.preventDefault();
    dragCountRef.current = 0;
    setIsDragging(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) {
      validateAndSetFile(dropped);
    }
  }

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
      window.dispatchEvent(new Event("paper2repo:runs-updated"));
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

    pollingAbortRef.current?.abort();
    const abortController = new AbortController();
    pollingAbortRef.current = abortController;

    setIsAnalyzing(true);
    setRun(null);
    setReport(null);
    setMessage("正在运行论文理解与复现规划流程...");
    try {
      const startedRun = await startAnalysis(paper.id);
      setRun(startedRun);
      let latestRun = startedRun;
      setMessage("任务已提交，正在分析...");

      let consecutiveErrors = 0;
      for (let attempt = 0; attempt < 600; attempt += 1) {
        await sleep(1000, abortController.signal);
        try {
          latestRun = await getRun(startedRun.id);
          consecutiveErrors = 0;
        } catch {
          consecutiveErrors += 1;
          if (consecutiveErrors >= 5) {
            setMessage("网络连接中断，分析监控已停止。");
            return;
          }
          setMessage(`网络请求失败，正在重试 (${consecutiveErrors}/5)...`);
          continue;
        }
        if (abortController.signal.aborted) return;
        setRun(latestRun);

        if (latestRun.status === "completed") {
          const generatedReport = await getReport(latestRun.id);
          setReport(generatedReport);
          setMessage("分析完成，报告已生成。");
          window.dispatchEvent(new Event("paper2repo:runs-updated"));
          return;
        }

        if (latestRun.status === "failed") {
          setMessage(latestRun.error_message ?? "分析失败。");
          window.dispatchEvent(new Event("paper2repo:runs-updated"));
          return;
        }

        setMessage(`正在执行：${stepLabel(latestRun.current_step)} (${latestRun.progress_percent}%)`);
      }
      setMessage("分析仍在运行，请稍后刷新任务状态。");
    } catch (error) {
      if (abortController.signal.aborted) {
        return;
      }
      setMessage(error instanceof Error ? error.message : "分析失败。请确认后端服务正在运行。");
    } finally {
      if (pollingAbortRef.current === abortController) {
        pollingAbortRef.current = null;
        setIsAnalyzing(false);
      }
    }
  }

  async function handleModelChange(event: ChangeEvent<HTMLSelectElement>) {
    const nextModel = event.target.value;
    setSelectedModel(nextModel);
    setIsSavingModel(true);
    try {
      const updatedConfig = await updateLlmConfig(nextModel);
      setLlmConfig(updatedConfig);
      setSelectedModel(updatedConfig.default_model);
      setMessage(
        updatedConfig.configured
          ? `已切换默认模型：${updatedConfig.default_model}`
          : `已切换默认模型：${updatedConfig.default_model}。LLM 未配置，将使用本地 fallback。`,
      );
    } catch (error) {
      setSelectedModel(llmConfig?.default_model ?? "");
      setMessage(error instanceof Error ? error.message : "模型切换失败。");
    } finally {
      setIsSavingModel(false);
    }
  }

  return (
    <div className="stack">
      <section className="model-panel">
        <label className="field-label" htmlFor="model-select">
          分析模型
        </label>
        <select
          id="model-select"
          className="select"
          value={selectedModel}
          disabled={!llmConfig || isSavingModel || isUploading || isAnalyzing}
          onChange={handleModelChange}
        >
          {llmConfig ? (
            llmConfig.available_models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))
          ) : (
            <option value="">加载模型配置...</option>
          )}
        </select>
        <p className="muted">
          {llmConfig
            ? `${llmConfig.configured ? "LLM 已配置" : "LLM 未配置，本地 fallback"} · ${llmConfig.base_url}`
            : "正在读取后端模型配置..."}
        </p>
      </section>

      <div
        className={`drop-zone${isDragging ? " drop-zone-active" : ""}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
        }}
      >
        <input
          ref={fileInputRef}
          hidden
          type="file"
          accept="application/pdf"
          onChange={(event) => {
            const selected = event.target.files?.[0];
            if (selected) validateAndSetFile(selected);
          }}
        />
        <p className="muted">{file ? file.name : "拖拽 PDF 到此处，或点击选择文件"}</p>
      </div>
      <div className="upload-row">
        <button className="button" type="button" disabled={!file || isUploading || isAnalyzing} onClick={handleUpload}>
          {isUploading ? "上传中..." : "上传 PDF"}
        </button>
        <button className="button secondary" type="button" disabled={!paper || isUploading || isAnalyzing || isSavingModel} onClick={handleAnalyze}>
          {isAnalyzing ? "分析中..." : "启动分析"}
        </button>
      </div>

      <p className="muted">{message}</p>

      <div className="grid">
        <InfoBlock title="Paper ID" value={paper?.id ?? "上传后显示"} />
        <InfoBlock title="Run ID" value={run?.id ?? "启动分析后显示"} />
        <InfoBlock title="Run 状态" value={run ? `${run.status} · ${run.progress_percent}%` : "pending"} />
        <InfoBlock title="模型" value={run?.model_name ?? selectedModel ?? "模型配置加载中"} />
      </div>

      {run ? <WorkflowProgress run={run} /> : null}

      {paper ? (
        <section className="sub-panel">
          <h3>已上传论文</h3>
          <p>
            <strong>{paper.filename}</strong>
          </p>
          <p className="muted">文件大小：{formatFileSize(paper.file_size)}</p>
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
              <p className="muted">报告已生成，可打开详情页或下载文件。</p>
            </div>
            <div className="action-row">
              <Link className="button" href={`/runs/${report.run_id}`}>
                查看 Markdown
              </Link>
              <a className="button secondary" href={getReportMarkdownUrl(report.run_id)} download>
                下载 Markdown
              </a>
              <a className="button secondary" href={getReportPdfUrl(report.run_id)} download>
                下载 PDF
              </a>
            </div>
          </div>
          <article className="markdown-body">
            <ReactMarkdown>{report.content}</ReactMarkdown>
          </article>
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
  const currentStepIndex = WORKFLOW_STEPS.findIndex((s) => s.key === run.current_step);

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
          const isComplete = run.status === "completed" || (currentStepIndex >= 0 && index < currentStepIndex);
          const isActive = run.status !== "completed" && index === currentStepIndex;
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

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}
