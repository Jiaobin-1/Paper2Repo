"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  getAppSettings,
  getReport,
  getReportHtmlUrl,
  getReportLatexUrl,
  getReportMarkdownUrl,
  getReportPdfUrl,
  startAnalysis,
  uploadPaper,
} from "../../../lib/api";
import { formatProgressMessage, formatRunStatusWithProgress } from "../../../lib/runPresentation";
import { pollRunUntilTerminal } from "../../../lib/runPolling";
import { text } from "../../../lib/i18n";
import { SETTINGS_UPDATED_EVENT, useAppLanguage } from "../../../lib/useAppLanguage";
import type { AppSettings, Paper, Report, Run } from "../../../lib/types";
import { WorkflowProgress } from "../report/RunProgress";
import InfoBlock from "../shared/InfoBlock";

const MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024;

export default function PaperUpload() {
  const language = useAppLanguage();
  const [file, setFile] = useState<File | null>(null);
  const [paper, setPaper] = useState<Paper | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [message, setMessage] = useState(text(language, "selectPdfStart"));
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
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

    function loadSettings() {
      getAppSettings()
        .then((config) => {
          if (!isMounted) {
            return;
          }
          setSettings(config);
          if (!config.configured) {
            setMessage(text(config.ui_language, "modelNotConfigured"));
          }
        })
        .catch((error) => {
          if (!isMounted) {
            return;
          }
          setMessage(error instanceof Error ? error.message : text(language, "modelLoadFailed"));
        });
    }

    loadSettings();
    window.addEventListener(SETTINGS_UPDATED_EVENT, loadSettings);
    return () => {
      isMounted = false;
      window.removeEventListener(SETTINGS_UPDATED_EVENT, loadSettings);
    };
  }, [language]);

  useEffect(() => {
    setMessage((currentMessage) => {
      if (
        currentMessage === text(language === "zh" ? "en" : "zh", "selectPdfStart") ||
        currentMessage === text(language === "zh" ? "en" : "zh", "modelNotConfigured")
      ) {
        return settings?.configured ? text(language, "selectPdfStart") : text(language, "modelNotConfigured");
      }
      return currentMessage;
    });
  }, [language, settings?.configured]);

  function validateAndSetFile(f: File): boolean {
    if (!isPdfFile(f)) {
      setMessage(text(language, "pdfOnly"));
      return false;
    }
    if (f.size > MAX_PDF_SIZE_BYTES) {
      setMessage(`${text(language, "pdfTooLarge")}（${formatFileSize(f.size)}），${text(language, "maxSize")}`);
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
      setMessage(text(language, "choosePdfFirst"));
      return;
    }
    setIsUploading(true);
    setPaper(null);
    setRun(null);
    setReport(null);
    setMessage(text(language, "uploadingPdf"));
    try {
      const uploadedPaper = await uploadPaper(file);
      setPaper(uploadedPaper);
      setMessage(text(language, "uploadSuccess"));
      window.dispatchEvent(new Event("paper2repo:runs-updated"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : text(language, "uploadFailed"));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAnalyze() {
    if (!paper) {
      setMessage(text(language, "uploadPaperFirst"));
      return;
    }

    pollingAbortRef.current?.abort();
    const abortController = new AbortController();
    pollingAbortRef.current = abortController;

    setIsAnalyzing(true);
    setRun(null);
    setReport(null);
    setMessage(text(language, "analysisStarting"));
    try {
      const startedRun = await startAnalysis(paper.id);
      setRun(startedRun);
      setMessage(text(language, "analysisQueued"));

      const terminalRun = await pollRunUntilTerminal(
        startedRun.id,
        {
          onRun: (latestRun) => {
            if (abortController.signal.aborted) return;
            setRun(latestRun);
            if (latestRun.status !== "completed" && latestRun.status !== "failed") {
              setMessage(formatProgressMessage(latestRun, language));
            }
          },
          onRetry: (consecutiveErrors) => {
            setMessage(`${text(language, "retrying")} (${consecutiveErrors}/5)...`);
          },
        },
        { signal: abortController.signal, delayFirstPoll: true, language },
      );

      setRun(terminalRun);
      if (terminalRun.status === "completed") {
        const generatedReport = await getReport(terminalRun.id);
        setReport(generatedReport);
        setMessage(text(language, "analysisDone"));
        window.dispatchEvent(new Event("paper2repo:runs-updated"));
        return;
      }

      setMessage(terminalRun.error_message ?? text(language, "analysisFailed"));
      window.dispatchEvent(new Event("paper2repo:runs-updated"));
    } catch (error) {
      if (abortController.signal.aborted) {
        return;
      }
      setMessage(error instanceof Error ? error.message : text(language, "backendOffline"));
    } finally {
      if (pollingAbortRef.current === abortController) {
        pollingAbortRef.current = null;
        setIsAnalyzing(false);
      }
    }
  }

  return (
    <div className="stack">
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
        <p className="muted">{file ? file.name : language === "en" ? "Drop a PDF here, or click to choose a file" : "拖拽 PDF 到此处，或点击选择文件"}</p>
      </div>
      <div className="upload-row">
        <button className="button" type="button" disabled={!file || isUploading || isAnalyzing} onClick={handleUpload}>
          {isUploading ? text(language, "uploadButtonBusy") : text(language, "uploadPdf")}
        </button>
        <button className="button secondary" type="button" disabled={!paper || isUploading || isAnalyzing} onClick={handleAnalyze}>
          {isAnalyzing ? text(language, "analyzing") : text(language, "startAnalysis")}
        </button>
      </div>

      <p className="muted">{message}</p>

      <div className="grid">
        <InfoBlock title={text(language, "taskStatus")} value={formatRunStatusWithProgress(run, language)} />
        <InfoBlock title={text(language, "analysisModel")} value={run?.model_name || settings?.default_model || text(language, "loadingModelConfig")} />
      </div>

      {run ? <WorkflowProgress run={run} /> : null}

      {paper ? (
        <section className="sub-panel">
          <h3>{text(language, "uploadedPaper")}</h3>
          <p>
            <strong>{paper.filename}</strong>
          </p>
          <p className="muted">
            {text(language, "fileSize")}：{formatFileSize(paper.file_size)}
          </p>
        </section>
      ) : null}

      {run?.error_message ? (
        <section className="error-box">
          <h3>{text(language, "taskError")}</h3>
          <p>{run.error_message}</p>
        </section>
      ) : null}

      {report ? (
        <section className="report-viewer">
          <div className="report-header">
            <div>
              <h3>{report.title}</h3>
              <p className="muted">{text(language, "reportGeneratedHint")}</p>
            </div>
            <div className="action-row">
              <Link className="button" href={`/runs/${report.run_id}`}>
                {text(language, "viewMarkdown")}
              </Link>
              <a className="button secondary" href={getReportMarkdownUrl(report.run_id)} download>
                {text(language, "downloadMarkdown")}
              </a>
              <a className="button secondary" href={getReportPdfUrl(report.run_id)} download>
                {text(language, "downloadPdf")}
              </a>
              <a className="button secondary" href={getReportHtmlUrl(report.run_id)} download>
                {text(language, "downloadHtml")}
              </a>
              <a className="button secondary" href={getReportLatexUrl(report.run_id)} download>
                {text(language, "downloadLatex")}
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

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function isPdfFile(file: File): boolean {
  return file.type === "application/pdf" || (!file.type && file.name.toLowerCase().endsWith(".pdf"));
}
