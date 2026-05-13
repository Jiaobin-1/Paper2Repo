"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { compareRuns, getAvailableRuns } from "../../lib/api";
import { text } from "../../lib/i18n";
import { useAppLanguage } from "../../lib/useAppLanguage";
import type { AvailableRun, ComparisonRun } from "../../lib/types";

export default function ComparePage() {
  const language = useAppLanguage();
  const [available, setAvailable] = useState<AvailableRun[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [results, setResults] = useState<ComparisonRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getAvailableRuns()
      .then((runs) => {
        setAvailable(runs);
        setLoaded(true);
      })
      .catch(() => {
        setError(text(language, "compareLoadFailed"));
        setLoaded(true);
      });
  }, [language]);

  const toggleRun = useCallback((runId: string) => {
    setSelected((prev) => {
      if (prev.includes(runId)) return prev.filter((id) => id !== runId);
      if (prev.length >= 4) return prev;
      return [...prev, runId];
    });
  }, []);

  const handleCompare = useCallback(async () => {
    if (selected.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const data = await compareRuns(selected);
      setResults(data);
    } catch {
      setError(text(language, "compareFailed"));
    } finally {
      setLoading(false);
    }
  }, [selected, language]);

  if (!loaded) {
    return (
      <main className="stack">
        <p className="muted">{text(language, "compareLoading")}</p>
      </main>
    );
  }

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>{text(language, "compareTitle")}</h1>
          <p className="muted">{text(language, "compareSubtitle")}</p>
        </div>
        <Link className="button secondary" href="/">
          {text(language, "backHome")}
        </Link>
      </section>

      <section className="panel stack">
        <h2>{text(language, "selectRuns")}</h2>
        <p className="muted">{text(language, "selectRunsHint")}</p>
        {available.length === 0 ? (
          <p className="muted">{text(language, "noCompletedRuns")}</p>
        ) : (
          <div className="compare-selector">
            {available.map((run) => (
              <label
                key={run.run_id}
                className={`compare-option ${selected.includes(run.run_id) ? "compare-option-selected" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={selected.includes(run.run_id)}
                  onChange={() => toggleRun(run.run_id)}
                />
                <div>
                  <strong>{run.paper_title || run.paper_filename}</strong>
                  <span className="muted">
                    {run.model_name || text(language, "notRecorded")} &middot;{" "}
                    {new Date(run.created_at).toLocaleDateString()}
                  </span>
                </div>
              </label>
            ))}
          </div>
        )}

        <div className="action-row">
          <button
            className="button"
            type="button"
            disabled={selected.length < 2 || loading}
            onClick={handleCompare}
          >
            {loading ? text(language, "compareRunning") : text(language, "compareStart")}
          </button>
        </div>
      </section>

      {error ? <p className="qa-error">{error}</p> : null}

      {results.length > 0 ? <ComparisonTable results={results} language={language} /> : null}
    </main>
  );
}

function ComparisonTable({
  results,
  language,
}: {
  results: ComparisonRun[];
  language: "zh" | "en";
}) {
  return (
    <section className="panel stack">
      <h2>{text(language, "compareResults")}</h2>
      <div className="compare-table-wrap">
        <table className="compare-table" style={{ gridTemplateColumns: `200px repeat(${results.length}, 1fr)` }}>
          <thead>
            <tr>
              <th></th>
              {results.map((r) => (
                <th key={r.run_id}>
                  <Link href={`/runs/${r.run_id}`}>
                    {r.paper_title || r.paper_filename || r.run_id.slice(0, 8)}
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <CompareRow label={text(language, "compareModel")} values={results.map((r) => r.model_name || "-")} />
            <CompareRow label={text(language, "compareVenue")} values={results.map((r) => [r.metadata.venue, r.metadata.year].filter(Boolean).join(" ") || "-")} />
            <CompareRow label={text(language, "compareProblem")} values={results.map((r) => r.understanding.core_problem || "-")} />
            <CompareRow label={text(language, "compareContributions")} values={results.map((r) => r.understanding.main_contributions?.join("; ") || "-")} />
            <CompareRow label={text(language, "compareMethod")} values={results.map((r) => r.method.method_name || "-")} />
            <CompareRow label={text(language, "compareInnovations")} values={results.map((r) => r.method.key_innovations?.join("; ") || "-")} />
            <CompareRow label={text(language, "compareDatasets")} values={results.map((r) => r.experiments.datasets?.join(", ") || "-")} />
            <CompareRow label={text(language, "compareMetrics")} values={results.map((r) => r.experiments.metrics?.join(", ") || "-")} />
            <CompareRow label={text(language, "compareGoal")} values={results.map((r) => r.reproduction.reproduction_goal || "-")} />
            <CompareRow label={text(language, "compareEffort")} values={results.map((r) => r.reproduction.estimated_effort || "-")} />
          </tbody>
        </table>
      </div>
    </section>
  );
}

function CompareRow({ label, values }: { label: string; values: string[] }) {
  return (
    <tr>
      <td className="compare-label">{label}</td>
      {values.map((v, i) => (
        <td key={i}>{v}</td>
      ))}
    </tr>
  );
}
