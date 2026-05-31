"use client";

import Link from "next/link";
import PaperUpload from "./components/upload/PaperUpload";
import RunHistory from "./components/history/RunHistory";
import { text } from "../lib/i18n";
import { useAppLanguage } from "../lib/useAppLanguage";

export default function HomePage() {
  const language = useAppLanguage();
  const workflowSteps = [
    text(language, "uploadPdf"),
    text(language, "understandPaper"),
    text(language, "decomposeMethod"),
    text(language, "planReproduction"),
    text(language, "exportReproduction"),
  ];

  return (
    <main className="stack home-page">
      <section className="page-heading home-heading">
        <div>
          <h1>Paper2Repo</h1>
          <p className="muted">{text(language, "appSubtitle")}</p>
        </div>
        <div className="home-actions">
          <Link className="button secondary" href="/arxiv">
            {text(language, "arxivImport")}
          </Link>
          <Link className="button secondary" href="/batch">
            {text(language, "batchAnalysis")}
          </Link>
          <Link className="button secondary" href="/knowledge">
            {text(language, "knowledgeBase")}
          </Link>
        </div>
      </section>

      <section className="workflow-strip" aria-label="Paper2Repo workflow">
        {workflowSteps.map((label, index) => (
          <span key={label}>
            <b>{String(index + 1).padStart(2, "0")}</b>
            {label}
          </span>
        ))}
      </section>

      <section className="home-workbench">
        <section className="panel stack upload-panel fade-in">
          <div className="section-header section-header-compact">
            <div>
              <h2>{text(language, "localWorkflow")}</h2>
            </div>
          </div>
          <PaperUpload />
        </section>
        <aside className="home-rail stack slide-up">
          <RunHistory compact />
        </aside>
      </section>
    </main>
  );
}
