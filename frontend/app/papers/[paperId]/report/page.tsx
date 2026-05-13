"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { listRuns } from "../../../../lib/api";

export default function PaperReportRedirect({ params }: { params: Promise<{ paperId: string }> }) {
  const router = useRouter();

  useEffect(() => {
    params.then(({ paperId }) => {
      listRuns({ paperId, limit: 1 })
        .then((runs) => {
          if (runs.length > 0 && runs[0].status === "completed") {
            router.replace(`/runs/${runs[0].id}`);
          } else {
            router.replace("/");
          }
        })
        .catch(() => router.replace("/"));
    });
  }, [params, router]);

  return (
    <main className="stack">
      <p className="muted">Redirecting...</p>
    </main>
  );
}
