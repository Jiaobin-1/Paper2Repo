import Link from "next/link";
import { formatFileSize } from "@/lib/format";
import { text } from "@/lib/i18n";
import { formatRunStatusWithProgress } from "@/lib/runPresentation";
import type { LanguageCode } from "@/lib/types";
import type { BatchFile, BatchStatus } from "./hooks/useBatchUpload";

type BatchFileListProps = {
  analyzingCount: number;
  completedCount: number;
  files: BatchFile[];
  isBusy: boolean;
  language: LanguageCode;
  onRemove: (index: number) => void;
  uploadedCount: number;
  uploadingCount: number;
};

export default function BatchFileList({
  analyzingCount,
  completedCount,
  files,
  isBusy,
  language,
  onRemove,
  uploadedCount,
  uploadingCount,
}: BatchFileListProps) {
  if (files.length === 0) {
    return null;
  }

  return (
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
              <span className="batch-item-size">{formatFileSize(item.file.size)}</span>
            </div>
            <div className="batch-item-status">
              <span className={`batch-badge ${item.status}`}>{batchStatusLabel(item.status, language)}</span>
              {item.run ? (
                <span className="batch-item-progress">
                  {formatRunStatusWithProgress(item.run, language)}
                </span>
              ) : null}
              {item.error ? <span className="batch-item-error">{item.error}</span> : null}
            </div>
            {item.status === "completed" && item.run ? (
              <Link className="button secondary batch-item-link" href={`/runs/${item.run.id}`}>
                {text(language, "viewMarkdown")}
              </Link>
            ) : null}
            {!isBusy ? (
              <button
                aria-label={language === "zh" ? "移除文件" : "Remove file"}
                className="button secondary batch-item-remove"
                type="button"
                onClick={() => onRemove(index)}
              >
                x
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
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
