"use client";

import { useEffect, useState } from "react";
import { getCitations } from "../../../lib/api";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { CitationInfo } from "../../../lib/types";

export default function CitationNetwork({ runId }: { runId: string }) {
  const language = useAppLanguage();
  const [citations, setCitations] = useState<CitationInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    getCitations(runId)
      .then((data) => {
        if (isMounted) {
          setCitations(data.citations);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [runId]);

  if (loading) {
    return (
      <section className="panel stack">
        <h3>{text(language, "citations")}</h3>
        <p className="muted">{text(language, "citationsLoading")}</p>
      </section>
    );
  }

  if (citations.length === 0) {
    return null;
  }

  return (
    <section className="panel stack">
      <h3>{text(language, "citations")}</h3>
      <p className="muted">
        {language === "zh"
          ? `共 ${citations.length} 条引用`
          : `${citations.length} references found`}
      </p>
      <div className="citation-list">
        {citations.map((cite) => (
          <div key={cite.citation_index} className="citation-item">
            <span className="citation-index">[{cite.citation_index}]</span>
            <div className="citation-body">
              <span className="citation-authors">{cite.authors}</span>
              {cite.title && (
                <>
                  {" "}
                  <em>{cite.title}</em>
                </>
              )}
              {cite.venue && (
                <>
                  {" "}
                  <span className="citation-venue">{cite.venue}</span>
                </>
              )}
              {cite.year && (
                <>
                  {" "}
                  <span className="citation-year">({cite.year})</span>
                </>
              )}
              {cite.doi && (
                <>
                  {" "}
                  <span className="citation-doi">DOI: {cite.doi}</span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
