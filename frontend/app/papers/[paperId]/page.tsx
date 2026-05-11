export default function PaperDetailPage({ params }: { params: { paperId: string } }) {
  return (
    <main className="stack">
      <section>
        <h1>论文详情</h1>
        <p className="muted">Paper ID: {params.paperId}</p>
      </section>

      <section className="panel stack">
        <h2>分析状态</h2>
        <p className="muted">这里预留启动分析、查看任务状态和展示结构化结果的位置。</p>
      </section>

      <section className="grid">
        <div className="panel">
          <h3>论文理解</h3>
          <p className="muted">背景、问题、贡献、方法、结论。</p>
        </div>
        <div className="panel">
          <h3>复现规划</h3>
          <p className="muted">最小目标、工程模块、代码骨架、风险点。</p>
        </div>
      </section>
    </main>
  );
}
