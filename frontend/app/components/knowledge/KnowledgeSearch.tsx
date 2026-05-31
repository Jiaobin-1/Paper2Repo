"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { searchKnowledge } from "../../../lib/api";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { KnowledgeSearchResult } from "../../../lib/types";

export default function KnowledgeSearch() {
  const language = useAppLanguage();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    const q = query.trim();
    if (!q || loading) return;

    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const data = await searchKnowledge(q);
      setResults(data);
    } catch {
      setError(text(language, "knowledgeSearchFailed"));
    } finally {
      setLoading(false);
    }
  }, [query, loading, language]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        handleSearch();
      }
    },
    [handleSearch],
  );

  const grouped = groupByPaper(results);

  return (
    <div className="stack">
      <div className="knowledge-search-row">
        <input
          className="input"
          placeholder={text(language, "knowledgeSearch")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button className="button" onClick={handleSearch} disabled={loading || !query.trim()} type="button">
          {loading ? text(language, "knowledgeLoading") : text(language, "knowledgeSearchBtn")}
        </button>
      </div>

      {error ? <p className="qa-error">{error}</p> : null}

      {loading ? (
        <div className="loading-state">
          <span className="spinner" />
          <p>{text(language, "knowledgeLoading")}</p>
        </div>
      ) : null}

      {searched && !loading && results.length === 0 && !error ? (
        <div className="empty-state">
          <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <p>{text(language, "knowledgeNoResults")}</p>
        </div>
      ) : null}

      {!searched && !loading ? (
        <div className="empty-state">
          <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <p>{text(language, "knowledgeEmpty")}</p>
        </div>
      ) : null}

      {grouped.map((group) => (
        <div key={group.paperId} className="knowledge-group">
          <div className="knowledge-group-header">
            <strong>{group.paperTitle || group.paperId.slice(0, 8)}</strong>
            {group.paperId ? (
              <Link href={`/papers/${group.paperId}`} className="knowledge-link">
                {text(language, "viewReport")}
              </Link>
            ) : null}
          </div>
          {group.chunks.map((chunk) => (
            <div key={`${chunk.paper_id}-${chunk.chunk_index}`} className="knowledge-chunk">
              <div className="knowledge-chunk-meta">
                {chunk.section_title ? <span className="knowledge-section">{chunk.section_title}</span> : null}
                <span className="muted">p.{chunk.page_start}</span>
                <span className="knowledge-score">{(chunk.score * 100).toFixed(0)}%</span>
              </div>
              <p className="knowledge-chunk-text">{chunk.chunk_content.slice(0, 300)}{chunk.chunk_content.length > 300 ? "..." : ""}</p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

interface PaperGroup {
  paperId: string;
  paperTitle: string | null;
  chunks: KnowledgeSearchResult[];
}

function groupByPaper(results: KnowledgeSearchResult[]): PaperGroup[] {
  const map = new Map<string, PaperGroup>();
  for (const r of results) {
    const key = r.paper_id || r.paper_title || "unknown";
    if (!map.has(key)) {
      map.set(key, { paperId: r.paper_id, paperTitle: r.paper_title, chunks: [] });
    }
    map.get(key)!.chunks.push(r);
  }
  return Array.from(map.values());
}
