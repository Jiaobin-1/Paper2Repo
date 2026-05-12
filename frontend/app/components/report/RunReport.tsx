"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { getReport, getReportMarkdownUrl, getReportPdfUrl, getRun } from "../../../lib/api";
import type { Report, Run } from "../../../lib/types";

export default function RunReport({ runId }: { runId: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [message, setMessage] = useState("正在加载任务详情...");

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const loadedRun = await getRun(runId);
        if (!isMounted) return;
        setRun(loadedRun);

        if (loadedRun.status !== "completed") {
          setMessage(
            loadedRun.status === "failed"
              ? loadedRun.error_message || "分析失败。"
              : `任务尚未完成：${loadedRun.status} · ${loadedRun.progress_percent}%`,
          );
          return;
        }

        const loadedReport = await getReport(runId);
        if (!isMounted) return;
        setReport(loadedReport);
        setMessage("报告已生成。");
      } catch (error) {
        if (!isMounted) return;
        setMessage(error instanceof Error ? error.message : "无法加载报告，请确认后端已启动。");
      }
    }

    load();
    return () => {
      isMounted = false;
    };
  }, [runId]);

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>{report?.title || "分析任务详情"}</h1>
          <p className="muted">Run ID: {runId}</p>
        </div>
        <Link className="button secondary" href="/">
          返回首页
        </Link>
      </section>

      <section className="panel stack">
        <div className="grid">
          <InfoBlock title="状态" value={run ? `${run.status} · ${run.progress_percent}%` : "加载中"} />
          <InfoBlock title="模型" value={run?.model_name || "未记录"} />
          <InfoBlock title="Paper ID" value={run?.paper_id || "加载中"} />
        </div>
        <p className="muted">{message}</p>
      </section>

      {report ? (
        <section className="report-viewer" id="markdown-report">
          <div className="report-header">
            <div>
              <h2>Markdown 报告</h2>
              <p className="muted">报告可在线查看，也可下载为 Markdown 或 PDF。</p>
            </div>
            <div className="action-row">
              <a className="button" href="#markdown-report">
                查看 Markdown
              </a>
              <a className="button secondary" href={getReportMarkdownUrl(runId)} download>
                下载 Markdown
              </a>
              <a className="button secondary" href={getReportPdfUrl(runId)} download>
                下载 PDF
              </a>
            </div>
          </div>
          <article className="markdown-body">
            <ReactMarkdown>{report.content}</ReactMarkdown>
          </article>
        </section>
      ) : null}
    </main>
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
