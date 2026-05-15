# Paper2RepoNet: Retrieval-Augmented Agents for Paper Reproduction

> Paper2Repo 示例报告：展示最终输出应如何同时覆盖“读懂论文”和“复现规划”。该示例用于 GitHub 展示，不代表真实论文结论。

## 1. 论文基本信息

- 标题：Paper2RepoNet: Retrieval-Augmented Agents for Paper Reproduction
- 作者：Alice Zhang, Bob Lee
- 方向：agent / rag
- 论文类型：experimental system
- 推荐复现方式：inference_pipeline + benchmark_evaluation
- 复现难度：medium
- MVP 适配度：good

## 2. 读懂到复现路线图

| 环节 | 读懂论文得到的信息 | 转化出的复现决策 | 证据来源 |
| --- | --- | --- | --- |
| 问题与目标 | 论文要连接 PDF 理解和工程复现规划。 | 第一版实现本地最小闭环：上传 PDF，输出复现报告和代码骨架。 | p.1 / Abstract / chunk-0: turn paper understanding into executable reproduction plans |
| 方法与模块 | 方法包含 PDF 解析、检索、结构化理解和复现规划。 | 代码拆成 parser、retrieval、agent nodes、exporter 四类模块。 | p.3 / Method / chunk-8: retrieval-augmented agents decompose papers into modules |
| 实验与验收 | 主实验验证报告是否覆盖数据集、指标、baseline 和风险项。 | 验收标准是生成可追溯报告、最小运行骨架和明确缺失信息。 | p.6 / Experiments / chunk-18: evaluate report completeness and reproduction readiness |
| 风险与缺口 | 闭源数据、权重和 PDF 文本质量会影响复现。 | 报告必须保留 blocking gaps，并给出 toy fallback 或人工核查动作。 | p.8 / Limitations / chunk-25: closed data and noisy PDFs remain blockers |

## 3. 读懂论文

### 研究背景

实验型 AI 论文通常把方法细节、数据集设置、baseline 和评价指标分散在多个章节中，读者即使理解了摘要，也很难直接转化为可执行的复现任务。

### 核心问题

论文关注的问题是：如何把论文理解过程和工程复现规划连接起来，让用户从 PDF 出发得到一个结构化、可执行的最小复现计划。

### 主要贡献

- 提出一个面向 AI 论文的 PDF 解析与章节感知检索流程。
- 将论文方法拆成输入、输出、关键模块和实现要点。
- 生成包含代码目录骨架、TODO、风险点和实验 checklist 的复现报告。

### 整体思路

系统先解析 PDF 并按章节切分 chunk，再使用关键词和章节标题检索相关上下文，最后由 Agent 节点分别完成论文理解、方法拆解、实验分析和复现规划。

### 局限性

- PDF 文本质量会影响抽取效果。
- 若论文依赖闭源数据或未公开权重，系统只能给出风险提示和替代方案。
- 第一版不做联网搜索和完整代码生成。

## 4. 方法拆解

### 方法整体框架

论文方法可拆成四个部分：PDF 解析、章节感知检索、结构化论文理解、复现任务规划。

### 关键模块、输入输出与实现要点

#### 1. PDF Parser

- 输入：论文 PDF
- 输出：raw text、page texts、section candidates
- 实现要点：使用 PyMuPDF 提取页级文本，并用规则识别章节标题。

#### 2. Retrieval

- 输入：paper chunks、section hints、keywords
- 输出：与节点任务相关的上下文片段
- 实现要点：第一版使用章节标题和关键词打分，不使用向量数据库。

#### 3. Reproduction Planner

- 输入：论文理解结果、方法分析、实验分析
- 输出：最小复现目标、代码目录骨架、实现步骤、风险点和 checklist
- 实现要点：复现计划必须依赖前序结构化结果，避免泛泛总结。

## 5. 实验分析

### 数据集

- ReproBench：用于测试论文复现规划质量。
- PaperQA：用于测试论文问答和信息定位能力。

### Baseline

- BM25 retrieval
- vanilla LLM summarizer
- long-context LLM baseline

### Metrics

- Accuracy
- F1
- Checklist completion rate
- Human preference score

### 消融实验

- 去掉 retrieval，只使用全文摘要。
- 去掉方法拆解节点，直接生成复现计划。
- 去掉实验分析节点，观察指标和数据集提取质量下降。

## 6. 复现规划

### 最小复现目标

实现一个本地可运行 pipeline：输入一篇 PDF，输出 Markdown 论文理解与复现规划报告，报告覆盖背景、问题、贡献、方法模块、实验设置、代码骨架和 checklist。

### 必要模块

- PDF 上传与解析
- chunk 切分
- keyword retrieval
- LangGraph workflow
- Pydantic schema 校验
- Markdown 报告导出
- 前端上传与报告展示

### 建议代码目录骨架

```text
backend/
  app/
    api/
    agents/
    schemas/
    services/
frontend/
  app/
  lib/
docs/
  examples/
```

### 实现步骤

1. 跑通 FastAPI 上传接口。
2. 使用 PyMuPDF 解析 PDF 并保存 chunk。
3. 串联 LangGraph 节点，生成结构化 JSON。
4. 将结构化结果导出为 Markdown 报告。
5. 在 Next.js 首页完成上传、启动分析、展示报告闭环。

### 风险点

- PDF 结构复杂导致章节识别不准。
- LLM 输出 JSON 不符合 schema。
- 论文缺少数据集、超参数或 baseline 细节。

### 实验 Checklist

- [ ] 上传 PDF 后生成 paper_id。
- [ ] 启动分析后生成 run_id。
- [ ] workflow 状态为 completed。
- [ ] 报告包含论文理解、方法拆解、实验分析和复现规划。
- [ ] 报告能指出缺失信息和复现风险。
