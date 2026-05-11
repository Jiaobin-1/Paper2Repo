export default function PaperReportPage({ params }: { params: { paperId: string } }) {
  return (
    <main className="stack">
      <section>
        <h1>Markdown 报告</h1>
        <p className="muted">Paper ID: {params.paperId}</p>
      </section>
      <section className="panel">
        <p className="muted">这里预留报告预览和下载入口。</p>
      </section>
    </main>
  );
}
