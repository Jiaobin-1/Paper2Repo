"use client";

import { useState } from "react";
import { uploadPaper } from "../../../lib/api";

export default function PaperUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleUpload() {
    if (!file) {
      setMessage("请先选择 PDF 文件。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const paper = await uploadPaper(file);
      setMessage(`上传成功：${paper.filename}。论文 ID：${paper.id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "上传失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stack">
      <input className="input" type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
      <button className="button" type="button" disabled={loading} onClick={handleUpload}>
        {loading ? "上传中..." : "上传 PDF"}
      </button>
      {message ? <p className="muted">{message}</p> : null}
    </div>
  );
}
