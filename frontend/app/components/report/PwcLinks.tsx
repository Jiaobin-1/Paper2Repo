"use client";

import { useEffect, useState } from "react";
import { getPwcLinks } from "../../../lib/api";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { PwcLink } from "../../../lib/types";

const TYPE_LABELS: Record<string, { zh: string; en: string }> = {
  paper: { zh: "论文", en: "Paper" },
  method: { zh: "方法", en: "Method" },
  keyword: { zh: "关键词", en: "Keyword" },
  contribution: { zh: "贡献", en: "Contribution" },
};

export default function PwcLinks({ runId }: { runId: string }) {
  const language = useAppLanguage();
  const [links, setLinks] = useState<PwcLink[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getPwcLinks(runId)
      .then((data) => {
        setLinks(data);
        setLoaded(true);
      })
      .catch(() => {
        setLoaded(true);
      });
  }, [runId]);

  if (!loaded || links.length === 0) return null;

  return (
    <section className="panel stack">
      <h2>{text(language, "pwcTitle")}</h2>
      <p className="muted">{text(language, "pwcHint")}</p>
      <ul className="pwc-links">
        {links.map((link, i) => (
          <li key={i} className="pwc-link-item">
            <a href={link.url} target="_blank" rel="noopener noreferrer" className="pwc-link">
              {link.label}
            </a>
            <span className="pwc-type">{TYPE_LABELS[link.type]?.[language] ?? link.type}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
