import type { RefObject } from "react";
import type { DragEvent } from "react";
import type { LanguageCode } from "@/lib/types";

type PaperDropZoneProps = {
  fileName?: string;
  inputRef: RefObject<HTMLInputElement | null>;
  isDragging: boolean;
  language: LanguageCode;
  onDragEnter: (event: DragEvent) => void;
  onDragLeave: (event: DragEvent) => void;
  onDragOver: (event: DragEvent) => void;
  onDrop: (event: DragEvent) => void;
  onFileSelected: (file: File) => void;
};

export default function PaperDropZone({
  fileName,
  inputRef,
  isDragging,
  language,
  onDragEnter,
  onDragLeave,
  onDragOver,
  onDrop,
  onFileSelected,
}: PaperDropZoneProps) {
  return (
    <div
      className={`drop-zone${isDragging ? " drop-zone-active" : ""}`}
      onDragEnter={onDragEnter}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
      }}
    >
      <input
        ref={inputRef}
        hidden
        type="file"
        accept="application/pdf"
        onChange={(event) => {
          const selected = event.target.files?.[0];
          if (selected) onFileSelected(selected);
        }}
      />
      <svg className="drop-zone-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3v12" />
        <path d="m7 8 5-5 5 5" />
        <path d="M5 15v3a3 3 0 0 0 3 3h8a3 3 0 0 0 3-3v-3" />
      </svg>
      <p className="muted">{fileName || (language === "en" ? "Drop a PDF here, or click to choose a file" : "拖拽 PDF 到此处，或点击选择文件")}</p>
    </div>
  );
}
