"use client";

import Link from "next/link";
import RunHistory from "@/components/history/RunHistory";
import PaperUpload from "@/components/upload/PaperUpload";
import { useAppLanguage } from "@/hooks/useAppLanguage";
import { text } from "@/lib/i18n";

function QuickActionIcon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}

export default function HomePage() {
  const language = useAppLanguage();
  const workflowSteps = [
    text(language, "uploadPdf"),
    text(language, "understandPaper"),
    text(language, "decomposeMethod"),
    text(language, "planReproduction"),
    text(language, "exportReproduction"),
  ];
  const quickActions = [
    {
      href: "/arxiv",
      label: text(language, "arxivImport"),
      icon: "M12 3v12m0-12L8 7m4-4 4 4M5 15v3a3 3 0 003 3h8a3 3 0 003-3v-3",
    },
    {
      href: "/batch",
      label: text(language, "batchAnalysis"),
      icon: "M5 20v-9h3v9H5zm6 0V4h3v16h-3zm6 0V8h3v12h-3z",
    },
    {
      href: "/knowledge",
      label: text(language, "knowledgeBase"),
      icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
    },
  ];

  return (
    <main className="stack home-page">
      <section className="page-heading home-heading">
        <div>
          <h1>Paper2Repo</h1>
          <p className="muted">{text(language, "appSubtitle")}</p>
        </div>
        <div className="home-actions">
          {quickActions.map((action) => (
            <Link className="button secondary" href={action.href} key={action.href}>
              <QuickActionIcon path={action.icon} />
              {action.label}
            </Link>
          ))}
        </div>
      </section>

      <section className="workflow-strip" aria-label="Paper2Repo workflow">
        {workflowSteps.map((label, index) => (
          <span
            className={index === 0 ? "current" : undefined}
            aria-current={index === 0 ? "step" : undefined}
            key={label}
          >
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
