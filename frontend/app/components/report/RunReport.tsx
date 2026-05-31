"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { getReport, getReportHtmlUrl, getReportLatexUrl, getReportMarkdownUrl, getReportPdfUrl, getSkeletonUrl } from "../../../lib/api";
import { formatProgressMessage, formatRunStatusWithProgress } from "../../../lib/runPresentation";
import { pollRunUntilTerminal } from "../../../lib/runPolling";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { Report, Run } from "../../../lib/types";
import { WorkflowProgress } from "./RunProgress";
import QaPanel from "./QaPanel";
import PwcLinks from "./PwcLinks";
import CitationNetwork from "./CitationNetwork";
import InfoBlock from "../shared/InfoBlock";

export default function RunReport({ runId }: { runId: string }) {
  const language = useAppLanguage();
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [message, setMessage] = useState(text(language, "reportLoading"));
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const abortController = new AbortController();

    async function load() {
      try {
        setReport(null);
        setMessage(text(language, "reportLoading"));
        const terminalRun = await pollRunUntilTerminal(
          runId,
          {
            onRun: (loadedRun) => {
              if (!isMounted) return;
              setRun(loadedRun);
              if (loadedRun.status === "failed") {
                setMessage(loadedRun.error_message || text(language, "analysisFailed"));
              } else if (loadedRun.status === "completed") {
                setMessage(text(language, "reportLoadingContent"));
              } else {
                setMessage(formatProgressMessage(loadedRun, language));
              }
            },
            onRetry: (consecutiveErrors) => {
              if (!isMounted) return;
              setMessage(`${text(language, "retrying")} (${consecutiveErrors}/5)...`);
            },
          },
          { signal: abortController.signal, language },
        );
        if (!isMounted) return;
        setRun(terminalRun);

        if (terminalRun.status !== "completed") {
          setMessage(terminalRun.error_message || text(language, "analysisFailed"));
          return;
        }

        const loadedReport = await getReport(runId);
        if (!isMounted) return;
        setReport(loadedReport);
        setMessage(text(language, "reportReady"));
      } catch (error) {
        if (!isMounted) return;
        setMessage(error instanceof Error ? error.message : text(language, "reportLoadFailed"));
      }
    }

    load();
    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [runId, language]);

  return (
    <main className="stack report-page">
      <section className="page-heading">
        <div>
          <h1>{report?.title || text(language, "detailsTitle")}</h1>
          <p className="muted">{text(language, "detailsSubtitle")}</p>
        </div>
      </section>

      <section className="report-shell">
        <aside className="report-sidebar stack">
          <section className="panel stack">
            <h2>{text(language, "taskOverview")}</h2>
            <InfoBlock title={text(language, "taskStatus")} value={run ? formatRunStatusWithProgress(run, language) : text(language, "reportLoading")} />
            <InfoBlock title={text(language, "analysisModel")} value={run?.model_name || text(language, "notRecorded")} />
            <p className="muted">{message}</p>
          </section>
          {run ? <WorkflowProgress run={run} /> : (
            <section className="progress-panel">
              <div className="loading-state" style={{ padding: "24px 0" }}>
                <span className="spinner" />
                <p>{text(language, "reportLoading")}</p>
              </div>
            </section>
          )}
        </aside>

        <section className="report-main stack">
          <nav className="report-tabs" aria-label={text(language, "reportNavigation")}>
            <a href="#markdown-report">{text(language, "reportTab")}</a>
            <a href="#reproduction-tools">{text(language, "reproductionTab")}</a>
            <a href="#evidence-chain">{text(language, "evidenceTab")}</a>
            <a href="#export-actions">{text(language, "exportTab")}</a>
          </nav>

          {!report && !run?.error_message ? (
            <section className="panel">
              <div className="loading-state">
                <span className="spinner" />
                <p>{message}</p>
              </div>
            </section>
          ) : null}

          {run?.error_message ? (
            <section className="panel error-box">
              <h3>{text(language, "taskError")}</h3>
              <p>{run.error_message}</p>
            </section>
          ) : null}

          {report ? (
            <section
              className={`report-viewer panel ${fullscreen ? "report-fullscreen" : ""}`}
              id="markdown-report"
            >
              {fullscreen ? (
                <div className="report-fullscreen-toggle">
                  <button className="button secondary" type="button" onClick={() => setFullscreen(false)}>
                    {text(language, "exitFullscreen")}
                  </button>
                </div>
              ) : null}
              <div className="report-header">
                <div>
                  <h2>{text(language, "markdownReport")}</h2>
                  <p className="muted">{text(language, "reportViewHint")}</p>
                </div>
                {!fullscreen ? (
                  <button className="button secondary" type="button" onClick={() => setFullscreen(true)}>
                    {text(language, "fullscreen")}
                  </button>
                ) : null}
              </div>
              <article className="markdown-body">
                <ReactMarkdown>{report.content}</ReactMarkdown>
              </article>
            </section>
          ) : null}

          {report ? (
            <section className="panel stack report-export-panel" id="export-actions">
              <div className="section-header">
                <div>
                  <h2>{text(language, "exportFiles")}</h2>
                  <p className="muted">{text(language, "downloadSkeletonDesc")}</p>
                </div>
              </div>
              <div className="action-row">
                <a className="button secondary" href={getReportMarkdownUrl(runId)} download>
                  {text(language, "downloadMarkdown")}
                </a>
                <a className="button secondary" href={getReportPdfUrl(runId)} download>
                  {text(language, "downloadPdf")}
                </a>
                <a className="button secondary" href={getReportHtmlUrl(runId)} download>
                  {text(language, "downloadHtml")}
                </a>
                <a className="button secondary" href={getReportLatexUrl(runId)} download>
                  {text(language, "downloadLatex")}
                </a>
                <a className="button secondary" href={getSkeletonUrl(runId)} download>
                  {text(language, "downloadSkeleton")}
                </a>
              </div>
            </section>
          ) : null}

          <div id="reproduction-tools" className="report-section-anchor">
            {report ? (
              <>
                <PwcLinks runId={runId} />
                <QaPanel runId={runId} />
              </>
            ) : null}
          </div>

          <div id="evidence-chain" className="report-section-anchor">
            {report ? <CitationNetwork runId={runId} /> : null}
          </div>
        </section>
      </section>
    </main>
  );
}
