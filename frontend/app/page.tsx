import PaperUpload from "./components/upload/PaperUpload";

export default function HomePage() {
  return (
    <main className="stack">
      <section>
        <h1>Paper2Repo</h1>
        <p className="muted">AI 论文理解与复现规划 Agent。本地 MVP 先跑通 PDF 上传、结构化分析和 Markdown 报告生成。</p>
      </section>

      <section className="panel stack">
        <h2>上传论文 PDF</h2>
        <PaperUpload />
      </section>

      <section className="grid">
        <div className="panel">
          <h3>读懂论文</h3>
          <p className="muted">结构化输出研究背景、核心问题、贡献、方法和实验。</p>
        </div>
        <div className="panel">
          <h3>规划复现</h3>
          <p className="muted">生成最小复现目标、模块拆解、目录骨架、风险点和 checklist。</p>
        </div>
      </section>
    </main>
  );
}
