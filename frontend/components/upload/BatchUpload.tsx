"use client";

import { useAppLanguage } from "@/hooks/useAppLanguage";
import { text } from "@/lib/i18n";
import { formatQueueStatus } from "@/lib/runPresentation";
import InfoBlock from "@/components/shared/InfoBlock";
import BatchDropZone from "./BatchDropZone";
import BatchFileList from "./BatchFileList";
import { useBatchUpload } from "./hooks/useBatchUpload";

export default function BatchUpload() {
  const language = useAppLanguage();
  const batch = useBatchUpload(language);

  return (
    <div className="stack">
      <BatchDropZone
        inputRef={batch.fileInputRef}
        isDragging={batch.isDragging}
        language={language}
        onDragEnter={batch.handleDragEnter}
        onDragLeave={batch.handleDragLeave}
        onDragOver={batch.handleDragOver}
        onDrop={batch.handleDrop}
        onFilesSelected={batch.validateAndAddFiles}
      />

      <div className="upload-row">
        <button className="button" type="button" disabled={batch.pendingCount === 0 || batch.isBusy} onClick={batch.handleUpload}>
          {batch.isUploading ? text(language, "batchUploading") : text(language, "batchUploadAll")}
        </button>
        <button className="button secondary" type="button" disabled={!batch.hasUploaded || batch.isBusy} onClick={batch.handleStartAnalysis}>
          {batch.isAnalyzing ? text(language, "analyzing") : text(language, "batchStartAll")}
        </button>
        {batch.queueRetryAvailable ? (
          <button className="button secondary" type="button" disabled={!batch.hasUploaded || batch.isBusy} onClick={batch.handleStartAnalysis}>
            {text(language, "retrySubmit")}
          </button>
        ) : null}
      </div>

      <p className="muted" aria-live="polite">{batch.message}</p>

      <div className="grid">
        <InfoBlock title={text(language, "queueStatus")} value={formatQueueStatus(batch.queueStatus, language)} />
      </div>

      <BatchFileList
        analyzingCount={batch.analyzingCount}
        completedCount={batch.completedCount}
        files={batch.files}
        isBusy={batch.isBusy}
        language={language}
        onRemove={batch.removeFile}
        uploadedCount={batch.uploadedCount}
        uploadingCount={batch.uploadingCount}
      />
    </div>
  );
}
