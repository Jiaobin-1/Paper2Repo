import PaperUpload from "./components/upload/PaperUpload";
import RunHistory from "./components/history/RunHistory";

export default function HomePage() {
  return (
    <main className="stack">
      <section className="page-heading">
        <div>
          <h1>Paper2Repo</h1>
          <p className="muted">AI 论文理解与复现规划 Agent。上传 PDF 后，本地完成解析、结构化分析，并生成 Markdown / PDF 复现报告。</p>
        </div>
      </section>

      <section className="workflow-strip">
        <span>上传 PDF</span>
        <span>选择模型</span>
        <span>后台分析</span>
        <span>查看报告</span>
        <span>下载结果</span>
      </section>

      <section className="panel stack">
        <h2>本地分析工作流</h2>
        <PaperUpload />
      </section>

      <RunHistory />

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
