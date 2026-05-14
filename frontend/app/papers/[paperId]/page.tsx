"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { listRuns } from "../../../lib/api";
import { text } from "../../../lib/i18n";
import { displayProgressPercent, formatRunStatus } from "../../../lib/runPresentation";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { RunListItem } from "../../../lib/types";

export default function PaperDetailPage({ params }: { params: Promise<{ paperId: string }> }) {
  const language = useAppLanguage();
  const [paperId, setPaperId] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const hasActiveRuns = runs.some((run) => run.status === "pending" || run.status === "running");

  useEffect(() => {
    params.then(({ paperId: id }) => setPaperId(id));
  }, [params]);

  const loadRuns = useCallback(async (options: { silent?: boolean } = {}) => {
    if (!paperId) {
      return;
    }
    if (!options.silent) {
      setLoading(true);
    }
    try {
      const items = await listRuns({ paperId });
      setRuns(items);
    } catch {
      setRuns([]);
    } finally {
      if (!options.silent) {
        setLoading(false);
      }
    }
  }, [paperId]);

  useEffect(() => {
    if (!paperId) {
      return;
    }
    void loadRuns();
    const onRefresh = () => {
      void loadRuns();
    };
    window.addEventListener("paper2repo:runs-updated", onRefresh);
    return () => window.removeEventListener("paper2repo:runs-updated", onRefresh);
  }, [paperId, loadRuns]);

  useEffect(() => {
    if (!hasActiveRuns) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadRuns({ silent: true });
    }, 3000);
    return () => window.clearInterval(timer);
  }, [hasActiveRuns, loadRuns]);

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>{text(language, "paperDetail")}</h1>
          <p className="muted">{text(language, "paperDetailDesc")}</p>
        </div>
      </section>

      <section className="panel stack">
        <h2>{text(language, "recentAnalysis")}</h2>
        {loading ? (
          <p className="muted">{text(language, "recentAnalysisLoading")}</p>
        ) : runs.length === 0 ? (
          <p className="muted">{text(language, "recentAnalysisEmpty")}</p>
        ) : (
          <div className="history-list">
            {runs.map((run) => (
              <Link key={run.id} href={`/runs/${run.id}`} className="history-item">
                <div>
                  <h3>{run.paper_title || run.paper_filename}</h3>
                  <p className="muted">{run.paper_filename}</p>
                </div>
                <div className="history-meta">
                  <span className={`status-badge status-${run.status}`}>{formatRunStatus(run.status, language)}</span>
                  <span>{displayProgressPercent(run)}%</span>
                </div>
                <span className="button secondary" style={{ pointerEvents: "none" }}>
                  {text(language, "viewReport")}
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
