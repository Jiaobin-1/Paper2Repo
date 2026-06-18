"use client";

import BatchUpload from "@/components/upload/BatchUpload";
import { useAppLanguage } from "@/hooks/useAppLanguage";
import { text } from "@/lib/i18n";

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
