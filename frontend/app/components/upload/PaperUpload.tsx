"use client";

import { useState } from "react";
import { getReport, getRun, startAnalysis, uploadPaper } from "../../../lib/api";
import type { Paper, Report, Run } from "../../../lib/types";

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
      const latestRun = await getRun(startedRun.id);
      setRun(latestRun);
      if (latestRun.status === "completed") {
        const generatedReport = await getReport(latestRun.id);
        setReport(generatedReport);
        setMessage("分析完成，报告已生成。");
      } else if (latestRun.status === "failed") {
        setMessage(latestRun.error_message ?? "分析失败。");
      } else {
        setMessage(`当前任务状态：${latestRun.status}`);
      }
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
        <InfoBlock title="Run 状态" value={run?.status ?? "pending"} />
      </div>

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
