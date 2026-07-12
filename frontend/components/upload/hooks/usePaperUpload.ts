"use client";

import { useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { getAppSettings, getQueueStatus, getReport, startAnalysis, uploadPaper } from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import { SETTINGS_UPDATED_EVENT } from "@/hooks/useAppLanguage";
import { formatFileSize } from "@/lib/format";
import { text } from "@/lib/i18n";
import { formatProgressMessage } from "@/lib/runPresentation";
import { pollRunUntilTerminal } from "@/lib/runPolling";
import type { AppSettings, LanguageCode, Paper, QueueStatus, Report, Run } from "@/lib/types";

const MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024;

export function usePaperUpload(language: LanguageCode) {
  const [file, setFile] = useState<File | null>(null);
  const [paper, setPaper] = useState<Paper | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [message, setMessage] = useState(text(language, "selectPdfStart"));
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [queueRetryAvailable, setQueueRetryAvailable] = useState(false);
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

  function validateAndSetFile(nextFile: File): boolean {
    if (!isPdfFile(nextFile)) {
      setMessage(text(language, "pdfOnly"));
      return false;
    }
    if (nextFile.size > MAX_PDF_SIZE_BYTES) {
      setMessage(`${text(language, "pdfTooLarge")}（${formatFileSize(nextFile.size)}），${text(language, "maxSize")}`);
      return false;
    }
    setFile(nextFile);
    return true;
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
    setQueueRetryAvailable(false);
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
    setQueueRetryAvailable(false);
    setMessage(text(language, "analysisStarting"));
    try {
      const startedRun = await startAnalysis(paper.id);
      setRun(startedRun);
      setMessage(startedRun.current_step === "queued" ? text(language, "queuedWaiting") : text(language, "analysisQueued"));
      refreshQueueStatus();

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
      if (error instanceof ApiError && error.status === 503) {
        const waitSeconds = error.retryAfterSeconds ?? queueStatus?.retry_after_seconds ?? 5;
        setQueueRetryAvailable(true);
        setMessage(`${text(language, "queueFullRetry")} ${language === "en" ? "Retry after" : "建议等待"} ${waitSeconds}s.`);
        refreshQueueStatus();
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

  function refreshQueueStatus() {
    void getQueueStatus()
      .then(setQueueStatus)
      .catch(() => undefined);
  }

  return {
    file,
    fileInputRef,
    handleAnalyze,
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleUpload,
    isAnalyzing,
    isDragging,
    isUploading,
    message,
    paper,
    queueRetryAvailable,
    queueStatus,
    report,
    run,
    settings,
    validateAndSetFile,
  };
}

function isPdfFile(file: File): boolean {
  return file.type === "application/pdf" || (!file.type && file.name.toLowerCase().endsWith(".pdf"));
}
