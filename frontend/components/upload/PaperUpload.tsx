"use client";

import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { useAppLanguage } from "@/hooks/useAppLanguage";
import { formatFileSize } from "@/lib/format";
import { text } from "@/lib/i18n";
import { formatRunStatusWithProgress } from "@/lib/runPresentation";
import InfoBlock from "@/components/shared/InfoBlock";
import PaperDropZone from "./PaperDropZone";
import { WorkflowProgress } from "../report/RunProgress";
import { usePaperUpload } from "./hooks/usePaperUpload";
import {
  getReportHtmlUrl,
  getReportLatexUrl,
  getReportMarkdownUrl,
  getReportPdfUrl,
} from "@/lib/api";

export default function PaperUpload() {
  const language = useAppLanguage();
  const upload = usePaperUpload(language);

  return (
    <div className="stack">
      <PaperDropZone
        fileName={upload.file?.name}
        inputRef={upload.fileInputRef}
        isDragging={upload.isDragging}
        language={language}
        onDragEnter={upload.handleDragEnter}
        onDragLeave={upload.handleDragLeave}
        onDragOver={upload.handleDragOver}
        onDrop={upload.handleDrop}
        onFileSelected={upload.validateAndSetFile}
      />
      <div className="upload-row">
        <button className="button" type="button" disabled={!upload.file || upload.isUploading || upload.isAnalyzing} onClick={upload.handleUpload}>
          {upload.isUploading ? text(language, "uploadButtonBusy") : text(language, "uploadPdf")}
        </button>
        <button className="button secondary" type="button" disabled={!upload.paper || upload.isUploading || upload.isAnalyzing} onClick={upload.handleAnalyze}>
          {upload.isAnalyzing ? text(language, "analyzing") : text(language, "startAnalysis")}
        </button>
      </div>

      <p className="muted upload-message" aria-live="polite">{upload.message}</p>

      <div className="grid">
        <InfoBlock title={text(language, "taskStatus")} value={formatRunStatusWithProgress(upload.run, language)} />
        <InfoBlock title={text(language, "analysisModel")} value={upload.run?.model_name || upload.settings?.default_model || text(language, "loadingModelConfig")} />
      </div>

      {upload.run ? <WorkflowProgress run={upload.run} /> : null}

      {upload.paper ? (
        <section className="sub-panel">
          <h3>{text(language, "uploadedPaper")}</h3>
          <p>
            <strong>{upload.paper.filename}</strong>
          </p>
          <p className="muted">
            {text(language, "fileSize")}：{formatFileSize(upload.paper.file_size)}
          </p>
        </section>
      ) : null}

      {upload.run?.error_message ? (
        <section className="error-box" role="alert">
          <h3>{text(language, "taskError")}</h3>
          <p>{upload.run.error_message}</p>
        </section>
      ) : null}

      {upload.report ? (
        <section className="report-viewer">
          <div className="report-header">
            <div>
              <h3>{upload.report.title}</h3>
              <p className="muted">{text(language, "reportGeneratedHint")}</p>
            </div>
            <div className="action-row">
              <Link className="button" href={`/runs/${upload.report.run_id}`}>
                {text(language, "viewMarkdown")}
              </Link>
              <a className="button secondary" href={getReportMarkdownUrl(upload.report.run_id)} download>
                {text(language, "downloadMarkdown")}
              </a>
              <a className="button secondary" href={getReportPdfUrl(upload.report.run_id)} download>
                {text(language, "downloadPdf")}
              </a>
              <a className="button secondary" href={getReportHtmlUrl(upload.report.run_id)} download>
                {text(language, "downloadHtml")}
              </a>
              <a className="button secondary" href={getReportLatexUrl(upload.report.run_id)} download>
                {text(language, "downloadLatex")}
              </a>
            </div>
          </div>
          <article className="markdown-body">
            <ReactMarkdown>{upload.report.content}</ReactMarkdown>
          </article>
        </section>
      ) : null}
    </div>
  );
}
