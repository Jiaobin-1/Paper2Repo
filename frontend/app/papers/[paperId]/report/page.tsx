export default async function PaperReportPage({ params }: { params: Promise<{ paperId: string }> }) {
  const { paperId } = await params;
  return (
    <main className="stack">
      <section>
        <h1>Markdown 报告</h1>
        <p className="muted">Paper ID: {paperId}</p>
      </section>
      <section className="panel stack">
        <p className="muted">报告详情页已迁移到 `/runs/[runId]`。请从首页的最近分析列表进入具体 Run 报告。</p>
        <a className="button secondary" href="/">
          返回首页
        </a>
      </section>
    </main>
  );
}
