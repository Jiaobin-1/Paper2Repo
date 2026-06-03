"use client";

import { useEffect } from "react";
import Link from "next/link";
import { text } from "../lib/i18n";
import { useAppLanguage } from "../lib/useAppLanguage";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const language = useAppLanguage();

  useEffect(() => {
    // Surface the error in the console for debugging; Next.js otherwise swallows it.
    console.error(error);
  }, [error]);

  return (
    <main className="stack">
      <section className="error-box" role="alert">
        <h3>{text(language, "errorBoundaryTitle")}</h3>
        <p>{text(language, "errorBoundaryHint")}</p>
        {error.message ? <p className="muted">{error.message}</p> : null}
        <div className="action-row">
          <button className="button" type="button" onClick={reset}>
            {text(language, "errorBoundaryRetry")}
          </button>
          <Link className="button secondary" href="/">
            {text(language, "errorBoundaryHome")}
          </Link>
        </div>
      </section>
    </main>
  );
}
