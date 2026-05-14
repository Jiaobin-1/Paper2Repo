"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  startBatchAnalysis,
  uploadPapers,
} from "../../../lib/api";
import { formatRunStatusWithProgress } from "../../../lib/runPresentation";
import { pollRunUntilTerminal } from "../../../lib/runPolling";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { LanguageCode, Paper, Run } from "../../../lib/types";

const MAX_FILE_SIZE = 50 * 1024 * 1024;
const MAX_FILES = 20;

type BatchFile = {
  file: File;
  paper: Paper | null;
  run: Run | null;
  status: BatchStatus;
  error: string | null;
};

type BatchStatus = "pending" | "uploading" | "uploaded" | "analyzing" | "completed" | "failed";

export default function BatchUpload() {
  const language = useAppLanguage();
  const [files, setFiles] = useState<BatchFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [message, setMessage] = useState(text(language, "batchDropHint"));
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragCountRef = useRef(0);
  const pollingAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      pollingAbortRef.current?.abort();
    };
  }, []);

  function validateAndAddFiles(newFiles: FileList | File[]) {
    const pdfFiles = Array.from(newFiles).filter(
      (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"),
    );
    if (pdfFiles.length === 0) {
      setMessage(text(language, "pdfOnly"));
      return;
    }
    if (files.length + pdfFiles.length > MAX_FILES) {
      setMessage(language === "zh" ? `最多 ${MAX_FILES} 个文件` : `Maximum ${MAX_FILES} files`);
      return;
    }
    const oversized = pdfFiles.find((f) => f.size > MAX_FILE_SIZE);
    if (oversized) {
      setMessage(`${language === "zh" ? "文件过大" : "File too large"}: ${oversized.name}`);
      return;
    }
    setFiles((prev) => [
      ...prev,
      ...pdfFiles.map((file) => ({
        file,
        paper: null,
        run: null,
        status: "pending" as const,
        error: null,
      })),
    ]);
    setMessage("");
  }

  function handleDragEnter(e: React.DragEvent) {
    e.preventDefault();
    dragCountRef.current += 1;
    setIsDragging(true);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    dragCountRef.current -= 1;
    if (dragCountRef.current <= 0) {
      dragCountRef.current = 0;
      setIsDragging(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    dragCountRef.current = 0;
    setIsDragging(false);
    validateAndAddFiles(e.dataTransfer.files);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleUpload() {
    const pendingFiles = files.filter((f) => f.status === "pending");
    if (pendingFiles.length === 0) return;
    setIsUploading(true);
    setMessage(text(language, "batchUploading"));
    setFiles((prev) =>
      prev.map((item) =>
        item.status === "pending" ? { ...item, status: "uploading" as const, error: null } : item,
      ),
    );

    try {
      const pdfFiles = pendingFiles.map((f) => f.file);
      const result = await uploadPapers(pdfFiles);
      let paperIndex = 0;

      setFiles((prev) =>
        prev.map((item) => {
          if (item.status !== "uploading") return item;
          const paper = result.papers[paperIndex];
          paperIndex += 1;
          return {
            ...item,
            paper: paper ?? null,
            status: paper ? "uploaded" as const : "pending" as const,
            error: paper ? null : text(language, "uploadFailed"),
          };
        }),
      );
      setMessage(text(language, "batchUploadDone"));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : text(language, "uploadFailed");
      setFiles((prev) =>
        prev.map((item) =>
          item.status === "uploading" ? { ...item, status: "pending" as const, error: errorMessage } : item,
        ),
      );
      setMessage(errorMessage);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleStartAnalysis() {
    const uploaded = files.filter((f) => f.status === "uploaded" && f.paper);
    if (uploaded.length === 0) return;

    pollingAbortRef.current?.abort();
    const abortController = new AbortController();
    pollingAbortRef.current = abortController;

    setIsAnalyzing(true);
    setMessage(text(language, "batchStarting"));

    try {
      const paperIds = uploaded.map((f) => f.paper!.id);
      const batchResult = await startBatchAnalysis(paperIds);

      setFiles((prev) =>
        prev.map((item) => {
          const run = batchResult.runs.find((r) => r.paper_id === item.paper?.id);
          return run ? { ...item, run, status: "analyzing" as const } : item;
        }),
      );

      await Promise.all(
        batchResult.runs.map(async (run) => {
          try {
            const terminalRun = await pollRunUntilTerminal(
              run.id,
              {
                onRun: (latestRun) => {
                  if (abortController.signal.aborted) return;
                  setFiles((prev) =>
                    prev.map((item) =>
                      item.run?.id === latestRun.id ? { ...item, run: latestRun } : item,
                    ),
                  );
                },
              },
              { signal: abortController.signal, delayFirstPoll: true, language },
            );
            setFiles((prev) =>
              prev.map((item) =>
                item.run?.id === terminalRun.id
                  ? { ...item, run: terminalRun, status: terminalRun.status === "completed" ? "completed" : "failed" }
                  : item,
              ),
            );
          } catch (error) {
            if (abortController.signal.aborted) return;
            const errorMessage = error instanceof Error ? error.message : text(language, "networkInterrupted");
            setFiles((prev) =>
              prev.map((item) =>
                item.run?.id === run.id ? { ...item, status: "failed" as const, error: errorMessage } : item,
              ),
            );
          }
        }),
      );

      setMessage(text(language, "batchDone"));
    } catch (error) {
      if (abortController.signal.aborted) return;
      setMessage(error instanceof Error ? error.message : text(language, "backendOffline"));
    } finally {
      if (pollingAbortRef.current === abortController) {
        pollingAbortRef.current = null;
        setIsAnalyzing(false);
      }
    }
  }

  const pendingCount = files.filter((f) => f.status === "pending").length;
  const uploadingCount = files.filter((f) => f.status === "uploading").length;
  const uploadedCount = files.filter((f) => f.status === "uploaded").length;
  const completedCount = files.filter((f) => f.status === "completed").length;
  const analyzingCount = files.filter((f) => f.status === "analyzing").length;
  const hasUploaded = files.some((f) => f.status === "uploaded");
  const isBusy = isUploading || isAnalyzing;

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
          multiple
          onChange={(e) => {
            if (e.target.files) validateAndAddFiles(e.target.files);
          }}
        />
        <p className="muted">{text(language, "batchDropHint")}</p>
      </div>

      <div className="upload-row">
        <button className="button" type="button" disabled={pendingCount === 0 || isBusy} onClick={handleUpload}>
          {isUploading ? text(language, "batchUploading") : text(language, "batchUploadAll")}
        </button>
        <button className="button secondary" type="button" disabled={!hasUploaded || isBusy} onClick={handleStartAnalysis}>
          {isAnalyzing ? text(language, "analyzing") : text(language, "batchStartAll")}
        </button>
      </div>

      <p className="muted">{message}</p>

      {files.length > 0 && (
        <section className="panel">
          <div className="batch-summary">
            <span>{files.length} {language === "zh" ? "个文件" : "files"}</span>
            {uploadingCount > 0 && <span className="batch-badge uploading">{uploadingCount} {batchStatusLabel("uploading", language)}</span>}
            {uploadedCount > 0 && <span className="batch-badge uploaded">{uploadedCount} {batchStatusLabel("uploaded", language)}</span>}
            {analyzingCount > 0 && <span className="batch-badge analyzing">{analyzingCount} {batchStatusLabel("analyzing", language)}</span>}
            {completedCount > 0 && <span className="batch-badge completed">{completedCount} {batchStatusLabel("completed", language)}</span>}
          </div>
          <div className="batch-list">
            {files.map((item, index) => (
              <div key={`${item.file.name}-${index}`} className="batch-item">
                <div className="batch-item-info">
                  <span className="batch-item-name">{item.file.name}</span>
                  <span className="batch-item-size">{formatSize(item.file.size)}</span>
                </div>
                <div className="batch-item-status">
                  <span className={`batch-badge ${item.status}`}>{batchStatusLabel(item.status, language)}</span>
                  {item.run && (
                    <span className="batch-item-progress">
                      {formatRunStatusWithProgress(item.run, language)}
                    </span>
                  )}
                  {item.error && <span className="batch-item-error">{item.error}</span>}
                </div>
                {item.status === "completed" && item.run && (
                  <Link className="button secondary batch-item-link" href={`/runs/${item.run.id}`}>
                    {text(language, "viewMarkdown")}
                  </Link>
                )}
                {!isBusy && (
                  <button
                    aria-label={language === "zh" ? "移除文件" : "Remove file"}
                    className="button secondary batch-item-remove"
                    type="button"
                    onClick={() => removeFile(index)}
                  >
                    x
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function batchStatusLabel(status: BatchStatus, language: LanguageCode): string {
  const labels: Record<LanguageCode, Record<BatchStatus, string>> = {
    zh: {
      pending: "待上传",
      uploading: "上传中",
      uploaded: "已上传",
      analyzing: "分析中",
      completed: "已完成",
      failed: "失败",
    },
    en: {
      pending: "pending",
      uploading: "uploading",
      uploaded: "uploaded",
      analyzing: "analyzing",
      completed: "done",
      failed: "failed",
    },
  };
  return labels[language][status];
}
