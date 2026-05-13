"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { deleteRun, listRuns } from "../../../lib/api";
import { formatRunStatus } from "../../../lib/runPresentation";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { RunListItem } from "../../../lib/types";

export default function RunHistory() {
  const language = useAppLanguage();
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [message, setMessage] = useState(text(language, "recentAnalysisLoading"));
  const [isLoading, setIsLoading] = useState(true);
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null);

  async function loadRuns() {
    setIsLoading(true);
    try {
      const items = await listRuns({ limit: 8 });
      setRuns(items);
      setMessage(items.length ? text(language, "recentAnalysisReady") : text(language, "recentAnalysisEmpty"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : text(language, "backendOfflineLoad"));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
    const onRefresh = () => loadRuns();
    window.addEventListener("paper2repo:runs-updated", onRefresh);
    return () => window.removeEventListener("paper2repo:runs-updated", onRefresh);
  }, [language]);

  async function handleDelete(run: RunListItem) {
    if (!window.confirm(text(language, "deleteConfirm"))) {
      return;
    }
    setDeletingRunId(run.id);
    try {
      await deleteRun(run.id);
      setMessage(text(language, "deleteSuccess"));
      await loadRuns();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : text(language, "deleteFailed"));
    } finally {
      setDeletingRunId(null);
    }
  }

  return (
    <section className="panel stack">
      <div className="section-header">
        <div>
          <h2>{text(language, "recentAnalysis")}</h2>
          <p className="muted">{message}</p>
        </div>
        <button className="button secondary" type="button" onClick={loadRuns} disabled={isLoading}>
          {text(language, "refresh")}
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
                <StatusBadge status={run.status} language={language} />
                <span>{run.progress_percent}%</span>
                <span>{run.model_name || text(language, "modelNotRecorded")}</span>
              </div>
              <div className="action-row">
                <Link className="button secondary" href={`/runs/${run.id}`}>
                  {run.status === "completed" ? text(language, "viewReport") : text(language, "viewReport")}
                </Link>
                <button
                  className="button danger"
                  type="button"
                  disabled={run.status === "pending" || run.status === "running" || deletingRunId === run.id}
                  onClick={() => handleDelete(run)}
                >
                  {text(language, "delete")}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function StatusBadge({ status, language }: { status: string; language: "zh" | "en" }) {
  return <span className={`status-badge status-${status}`}>{formatRunStatus(status, language)}</span>;
}
