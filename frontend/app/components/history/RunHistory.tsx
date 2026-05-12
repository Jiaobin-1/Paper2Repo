"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listRuns } from "../../../lib/api";
import type { RunListItem } from "../../../lib/types";

export default function RunHistory() {
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [message, setMessage] = useState("正在加载最近分析...");
  const [isLoading, setIsLoading] = useState(true);

  async function loadRuns() {
    setIsLoading(true);
    try {
      const items = await listRuns({ limit: 8 });
      setRuns(items);
      setMessage(items.length ? "最近分析记录" : "还没有分析记录，先上传一篇论文开始。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "无法连接后端，请确认 FastAPI 已启动。");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
    const onRefresh = () => loadRuns();
    window.addEventListener("paper2repo:runs-updated", onRefresh);
    return () => window.removeEventListener("paper2repo:runs-updated", onRefresh);
  }, []);

  return (
    <section className="panel stack">
      <div className="section-header">
        <div>
          <h2>最近论文 / 最近分析</h2>
          <p className="muted">{message}</p>
        </div>
        <button className="button secondary" type="button" onClick={loadRuns} disabled={isLoading}>
          刷新
        </button>
      </div>

      {runs.length ? (
        <div className="history-list">
          {runs.map((run) => (
            <article className="history-item" key={run.id}>
              <div>
                <h3>{run.paper_title || run.paper_filename}</h3>
                <p className="muted">{run.paper_filename}</p>
              </div>
              <div className="history-meta">
                <StatusBadge status={run.status} />
                <span>{run.progress_percent}%</span>
                <span>{run.model_name || "未记录模型"}</span>
              </div>
              <Link className="button secondary" href={`/runs/${run.id}`}>
                {run.status === "completed" ? "查看报告" : "查看任务"}
              </Link>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status}`}>{status}</span>;
}
