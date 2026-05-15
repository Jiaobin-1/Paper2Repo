"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { deleteRun, listRuns } from "../../../lib/api";
import { displayProgressPercent, formatRunStatus } from "../../../lib/runPresentation";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { RunListItem } from "../../../lib/types";

export default function RunHistory({ compact = false }: { compact?: boolean }) {
  const language = useAppLanguage();
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [message, setMessage] = useState(text(language, "recentAnalysisLoading"));
  const [isLoading, setIsLoading] = useState(true);
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null);
  const hasActiveRuns = runs.some((run) => run.status === "pending" || run.status === "running");

  const loadRuns = useCallback(async (options: { silent?: boolean } = {}) => {
    if (!options.silent) {
      setIsLoading(true);
    }
    try {
      const items = await listRuns({ limit: 8 });
      setRuns(items);
      setMessage(items.length ? text(language, "recentAnalysisReady") : text(language, "recentAnalysisEmpty"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : text(language, "backendOfflineLoad"));
    } finally {
      if (!options.silent) {
        setIsLoading(false);
      }
    }
  }, [language]);

  useEffect(() => {
    void loadRuns();
    const onRefresh = () => {
      void loadRuns();
    };
    window.addEventListener("paper2repo:runs-updated", onRefresh);
    return () => window.removeEventListener("paper2repo:runs-updated", onRefresh);
  }, [loadRuns]);

  useEffect(() => {
    if (!hasActiveRuns) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadRuns({ silent: true });
    }, 3000);
    return () => window.clearInterval(timer);
  }, [hasActiveRuns, loadRuns]);

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
    <section className={`panel stack run-history${compact ? " run-history-compact" : ""}`}>
      <div className="section-header">
        <div>
          <h2>{compact ? text(language, "taskQueue") : text(language, "recentAnalysis")}</h2>
          <p className="muted">{message}</p>
        </div>
        <button className="button secondary" type="button" onClick={() => void loadRuns()} disabled={isLoading}>
          {text(language, "refresh")}
        </button>
      </div>

      {runs.length ? (
        <div className="history-list">
          {runs.map((run) => (
            <article className="history-item" key={run.id}>
              <div className="history-main">
                <h3>{run.paper_title || run.paper_filename}</h3>
                <p className="muted">{run.paper_filename}</p>
                <div className="history-progress-track" aria-label={`${displayProgressPercent(run)}%`}>
                  <span style={{ width: `${displayProgressPercent(run)}%` }} />
                </div>
              </div>
              <div className="history-meta">
                <StatusBadge status={run.status} language={language} />
                <span>{displayProgressPercent(run)}%</span>
                <span>{run.model_name || text(language, "modelNotRecorded")}</span>
              </div>
              <div className="action-row">
                <Link className="button secondary" href={`/runs/${run.id}`}>
                  {text(language, "viewReport")}
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
