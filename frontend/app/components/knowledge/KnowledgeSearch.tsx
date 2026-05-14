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

      {searched && !loading && results.length === 0 && !error ? (
        <p className="muted">{text(language, "knowledgeNoResults")}</p>
      ) : null}

      {!searched && !loading ? <p className="muted">{text(language, "knowledgeEmpty")}</p> : null}

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
