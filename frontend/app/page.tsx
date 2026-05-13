"use client";

import Link from "next/link";
import PaperUpload from "./components/upload/PaperUpload";
import RunHistory from "./components/history/RunHistory";
import { text } from "../lib/i18n";
import { useAppLanguage } from "../lib/useAppLanguage";

export default function HomePage() {
  const language = useAppLanguage();

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>Paper2Repo</h1>
          <p className="muted">{text(language, "appSubtitle")}</p>
        </div>
        <div className="action-row">
          <Link className="button secondary" href="/arxiv">
            {text(language, "arxivImport")}
          </Link>
          <Link className="button secondary" href="/knowledge">
            {text(language, "knowledgeBase")}
          </Link>
          <Link className="button secondary" href="/compare">
            {text(language, "compare")}
          </Link>
          <Link className="button secondary" href="/settings">
            {text(language, "settings")}
          </Link>
        </div>
      </section>

      <section className="workflow-strip">
        <span>{text(language, "uploadPdf")}</span>
        <span>{text(language, "chooseModel")}</span>
        <span>{text(language, "backgroundAnalysis")}</span>
        <span>{text(language, "viewReport")}</span>
        <span>{text(language, "downloadResults")}</span>
      </section>

      <section className="panel stack">
        <h2>{text(language, "localWorkflow")}</h2>
        <PaperUpload />
      </section>

      <RunHistory />

      <section className="grid">
        <div className="panel">
          <h3>{text(language, "understandPaper")}</h3>
          <p className="muted">{text(language, "understandPaperDesc")}</p>
        </div>
        <div className="panel">
          <h3>{text(language, "planReproduction")}</h3>
          <p className="muted">{text(language, "planReproductionDesc")}</p>
        </div>
      </section>
    </main>
  );
}
