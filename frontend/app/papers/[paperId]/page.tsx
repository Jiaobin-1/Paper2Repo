"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listRuns } from "../../../lib/api";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { RunListItem } from "../../../lib/types";

export default function PaperDetailPage({ params }: { params: Promise<{ paperId: string }> }) {
  const language = useAppLanguage();
  const [paperId, setPaperId] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    params.then(({ paperId: id }) => setPaperId(id));
  }, [params]);

  useEffect(() => {
    if (!paperId) return;
    setLoading(true);
    listRuns({ paperId })
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, [paperId]);

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>{text(language, "paperDetail")}</h1>
          <p className="muted">{text(language, "paperDetailDesc")}</p>
        </div>
        <Link className="button secondary" href="/">
          {text(language, "backHome")}
        </Link>
      </section>

      <section className="panel stack">
        <h2>{text(language, "recentAnalysis")}</h2>
        {loading ? (
          <p className="muted">{text(language, "recentAnalysisLoading")}</p>
        ) : runs.length === 0 ? (
          <p className="muted">{text(language, "recentAnalysisEmpty")}</p>
        ) : (
          <ul className="run-list">
            {runs.map((run) => (
              <li key={run.id} className="run-item">
                <Link href={`/runs/${run.id}`} className="run-link">
                  <span className={`status-badge status-${run.status}`}>{run.status}</span>
                  <span>{run.paper_title || run.paper_filename}</span>
                  {run.progress_percent > 0 && (
                    <span className="muted">{run.progress_percent}%</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
