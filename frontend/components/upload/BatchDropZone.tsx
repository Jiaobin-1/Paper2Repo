import type { DragEvent, RefObject } from "react";
import { text } from "@/lib/i18n";
import type { LanguageCode } from "@/lib/types";

type BatchDropZoneProps = {
  inputRef: RefObject<HTMLInputElement | null>;
  isDragging: boolean;
  language: LanguageCode;
  onDragEnter: (event: DragEvent) => void;
  onDragLeave: (event: DragEvent) => void;
  onDragOver: (event: DragEvent) => void;
  onDrop: (event: DragEvent) => void;
  onFilesSelected: (files: FileList) => void;
};

export default function BatchDropZone({
  inputRef,
  isDragging,
  language,
  onDragEnter,
  onDragLeave,
  onDragOver,
  onDrop,
  onFilesSelected,
}: BatchDropZoneProps) {
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
        multiple
        onChange={(event) => {
          if (event.target.files) onFilesSelected(event.target.files);
        }}
      />
      <p className="muted">{text(language, "batchDropHint")}</p>
    </div>
  );
}
