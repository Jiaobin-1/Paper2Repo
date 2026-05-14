"use client";

import { text } from "../../lib/i18n";
import { useAppLanguage } from "../../lib/useAppLanguage";
import BatchUpload from "../components/upload/BatchUpload";

export default function BatchPage() {
  const language = useAppLanguage();

  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>{text(language, "batchTitle")}</h1>
          <p className="muted">{text(language, "batchSubtitle")}</p>
        </div>
      </section>
      <BatchUpload />
    </main>
  );
}
