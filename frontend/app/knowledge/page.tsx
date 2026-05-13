"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import KnowledgeSearch from "../components/knowledge/KnowledgeSearch";
import { getKnowledgePapers } from "../../lib/api";
import { text } from "../../lib/i18n";
import { useAppLanguage } from "../../lib/useAppLanguage";
import type { KnowledgePaper } from "../../lib/types";

export default function KnowledgePage() {
  const language = useAppLanguage();
  const [papers, setPapers] = useState<KnowledgePaper[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getKnowledgePapers()
      .then((data) => {
        setPapers(data);
        setLoaded(true);
      })
      .catch(() => {
        setLoaded(true);
      });
  }, []);

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>{text(language, "knowledgeBase")}</h1>
          <p className="muted">{text(language, "knowledgeBaseDesc")}</p>
        </div>
        <Link className="button secondary" href="/">
          {text(language, "backHome")}
        </Link>
      </section>

      <section className="panel stack">
        <KnowledgeSearch />
      </section>

      {loaded && papers.length > 0 ? (
        <section className="panel stack">
          <h2>{text(language, "knowledgePapers")}</h2>
          <div className="history-list">
            {papers.map((p) => (
              <div key={p.paper_id} className="history-item">
                <div>
                  <h3>{p.title || p.filename}</h3>
                  <p className="muted">{p.chunk_count} chunks</p>
                </div>
                <span className="muted">{new Date(p.created_at).toLocaleDateString()}</span>
                <Link className="button secondary" href={`/papers/${p.paper_id}`}>
                  {text(language, "viewReport")}
                </Link>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
