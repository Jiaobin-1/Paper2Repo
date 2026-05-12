export default async function PaperDetailPage({ params }: { params: Promise<{ paperId: string }> }) {
  const { paperId } = await params;
  return (
    <main className="stack">
      <section>
        <h1>论文详情</h1>
        <p className="muted">Paper ID: {paperId}</p>
      </section>

      <section className="panel stack">
        <h2>历史分析</h2>
        <p className="muted">当前正式报告入口按 Run ID 管理。请回到首页的“最近论文 / 最近分析”列表进入对应报告。</p>
        <a className="button secondary" href="/">
          返回首页
        </a>
      </section>
    </main>
  );
}
