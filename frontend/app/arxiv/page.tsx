"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { getArxivInfo, importArxiv } from "../../lib/api";
import { text } from "../../lib/i18n";
import { useAppLanguage } from "../../lib/useAppLanguage";
import type { ArxivInfo } from "../../lib/types";

export default function ArxivPage() {
  const language = useAppLanguage();
  const router = useRouter();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<ArxivInfo | null>(null);

  const handleLookup = useCallback(async () => {
    const raw = input.trim();
    if (!raw || loading) return;

    setLoading(true);
    setError(null);

    try {
      const arxivId = extractId(raw);
      if (!arxivId) {
        setError(text(language, "arxivImportFailed"));
        setLoading(false);
        return;
      }
      const data = await getArxivInfo(arxivId);
      setInfo(data);
    } catch {
      setError(text(language, "arxivImportFailed"));
    } finally {
      setLoading(false);
    }
  }, [input, loading, language]);

  const handleImport = useCallback(async () => {
    const raw = input.trim();
    if (!raw || loading) return;

    setLoading(true);
    setError(null);

    try {
      const arxivId = extractId(raw);
      if (!arxivId) {
        setError(text(language, "arxivImportFailed"));
        setLoading(false);
        return;
      }
      const paper = await importArxiv(arxivId);
      router.push(`/papers/${paper.id}`);
    } catch {
      setError(text(language, "arxivImportFailed"));
    } finally {
      setLoading(false);
    }
  }, [input, loading, language, router]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        handleLookup();
      }
    },
    [handleLookup],
  );

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>{text(language, "arxivImport")}</h1>
          <p className="muted">{text(language, "arxivImportDesc")}</p>
        </div>
        <Link className="button secondary" href="/">
          {text(language, "backHome")}
        </Link>
      </section>

      <section className="panel stack">
        <div className="knowledge-search-row">
          <input
            className="input"
            placeholder={text(language, "arxivPlaceholder")}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button className="button secondary" onClick={handleLookup} disabled={loading || !input.trim()} type="button">
            {text(language, "arxivVersions")}
          </button>
          <button className="button" onClick={handleImport} disabled={loading || !input.trim()} type="button">
            {loading ? text(language, "arxivImporting") : text(language, "arxivImportBtn")}
          </button>
        </div>

        {error ? <p className="qa-error">{error}</p> : null}

        {info ? (
          <div className="arxiv-info">
            <h3>{info.title}</h3>
            <p className="muted">arXiv: {info.arxiv_id}</p>
            {info.versions.length > 0 ? (
              <div>
                <p className="field-label">{text(language, "arxivVersions")}</p>
                <div className="arxiv-versions">
                  {info.versions.map((v) => (
                    <span key={v.version} className="status-badge">
                      {v.version}
                      {v.date ? ` (${v.date.slice(0, 10)})` : ""}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
    </main>
  );
}

function extractId(raw: string): string | null {
  const urlMatch = raw.match(/arxiv\.org\/(?:abs|pdf)\/(\d{4}\.\d{4,5}(?:v\d+)?)/i);
  if (urlMatch) return urlMatch[1];

  const idMatch = raw.match(/(\d{4}\.\d{4,5}(?:v\d+)?)/);
  if (idMatch) return idMatch[1];

  const cleaned = raw.replace(/^arXiv[:\s]*/i, "").trim();
  if (/^\d{4}\.\d{4,5}(?:v\d+)?$/.test(cleaned)) return cleaned;

  return null;
}
