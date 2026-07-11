"use client";

import { useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { getQueueStatus, startBatchAnalysis, uploadPapers } from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import { batchCompletionMessage } from "@/lib/batchPresentation";
import { text } from "@/lib/i18n";
import { pollRunUntilTerminal } from "@/lib/runPolling";
import type { LanguageCode, Paper, QueueStatus, Run } from "@/lib/types";

const MAX_FILE_SIZE = 50 * 1024 * 1024;
const MAX_FILES = 20;

export type BatchStatus = "pending" | "uploading" | "uploaded" | "analyzing" | "completed" | "failed";

export type BatchFile = {
  file: File;
  paper: Paper | null;
  run: Run | null;
  status: BatchStatus;
  error: string | null;
};

export function useBatchUpload(language: LanguageCode) {
  const [files, setFiles] = useState<BatchFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [message, setMessage] = useState(text(language, "batchDropHint"));
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [queueRetryAvailable, setQueueRetryAvailable] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragCountRef = useRef(0);
  const pollingAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      pollingAbortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    getQueueStatus()
      .then((status) => {
        if (isMounted) {
          setQueueStatus(status);
        }
      })
      .catch(() => undefined);
    return () => {
      isMounted = false;
    };
  }, []);

  function validateAndAddFiles(newFiles: FileList | File[]) {
    const pdfFiles = Array.from(newFiles).filter(
      (file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"),
    );
    if (pdfFiles.length === 0) {
      setMessage(text(language, "pdfOnly"));
      return;
    }
    if (files.length + pdfFiles.length > MAX_FILES) {
      setMessage(language === "zh" ? `最多 ${MAX_FILES} 个文件` : `Maximum ${MAX_FILES} files`);
      return;
    }
    const oversized = pdfFiles.find((file) => file.size > MAX_FILE_SIZE);
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

  function handleDragEnter(event: DragEvent) {
    event.preventDefault();
    dragCountRef.current += 1;
    setIsDragging(true);
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
  }

  function handleDragLeave(event: DragEvent) {
    event.preventDefault();
    dragCountRef.current -= 1;
    if (dragCountRef.current <= 0) {
      dragCountRef.current = 0;
      setIsDragging(false);
    }
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    dragCountRef.current = 0;
    setIsDragging(false);
    validateAndAddFiles(event.dataTransfer.files);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, itemIndex) => itemIndex !== index));
  }

  async function handleUpload() {
    const pendingFiles = files.filter((file) => file.status === "pending");
    if (pendingFiles.length === 0) return;
    setIsUploading(true);
    setQueueRetryAvailable(false);
    setMessage(text(language, "batchUploading"));
    setFiles((prev) =>
      prev.map((item) =>
        item.status === "pending" ? { ...item, status: "uploading" as const, error: null } : item,
      ),
    );

    try {
      const pdfFiles = pendingFiles.map((item) => item.file);
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
    const uploaded = files.filter((file) => file.status === "uploaded" && file.paper);
    if (uploaded.length === 0) return;

    pollingAbortRef.current?.abort();
    const abortController = new AbortController();
    pollingAbortRef.current = abortController;

    setIsAnalyzing(true);
    setQueueRetryAvailable(false);
    setMessage(text(language, "batchStarting"));

    try {
      const paperIds = uploaded.map((file) => file.paper!.id);
      const beforeStartQueue = await getQueueStatus().catch(() => null);
      if (beforeStartQueue) {
        setQueueStatus(beforeStartQueue);
      }
      const batchResult = await startBatchAnalysis(paperIds);
      const afterStartQueue = await getQueueStatus().catch(() => null);
      if (afterStartQueue) {
        setQueueStatus(afterStartQueue);
      }

      setFiles((prev) =>
        prev.map((item) => {
          const run = batchResult.runs.find((candidate) => candidate.paper_id === item.paper?.id);
          return run ? { ...item, run, status: "analyzing" as const, error: null } : item;
        }),
      );

      const completedRuns = await Promise.all(
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
            return terminalRun.status === "completed";
          } catch (error) {
            if (abortController.signal.aborted) throw error;
            const errorMessage = error instanceof Error ? error.message : text(language, "networkInterrupted");
            setFiles((prev) =>
              prev.map((item) =>
                item.run?.id === run.id ? { ...item, status: "failed" as const, error: errorMessage } : item,
              ),
            );
            return false;
          }
        }),
      );

      setMessage(batchCompletionMessage(completedRuns, language));
    } catch (error) {
      if (abortController.signal.aborted) return;
      if (error instanceof ApiError && error.status === 503) {
        const waitSeconds = error.retryAfterSeconds ?? queueStatus?.retry_after_seconds ?? 5;
        setQueueRetryAvailable(true);
        setMessage(`${text(language, "queueFullRetry")} ${language === "en" ? "Retry after" : "建议等待"} ${waitSeconds}s.`);
        const latestQueue = await getQueueStatus().catch(() => null);
        if (latestQueue) {
          setQueueStatus(latestQueue);
        }
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

  const pendingCount = files.filter((file) => file.status === "pending").length;
  const uploadingCount = files.filter((file) => file.status === "uploading").length;
  const uploadedCount = files.filter((file) => file.status === "uploaded").length;
  const completedCount = files.filter((file) => file.status === "completed").length;
  const analyzingCount = files.filter((file) => file.status === "analyzing").length;
  const hasUploaded = files.some((file) => file.status === "uploaded");
  const isBusy = isUploading || isAnalyzing;

  return {
    analyzingCount,
    completedCount,
    fileInputRef,
    files,
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleStartAnalysis,
    handleUpload,
    hasUploaded,
    isAnalyzing,
    isBusy,
    isDragging,
    isUploading,
    message,
    pendingCount,
    queueRetryAvailable,
    queueStatus,
    removeFile,
    uploadedCount,
    uploadingCount,
    validateAndAddFiles,
  };
}
