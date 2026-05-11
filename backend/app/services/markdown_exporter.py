from __future__ import annotations

from app.schemas.classification import PaperTypeClassification
from app.schemas.experiments import ExperimentAnalysis
from app.schemas.metadata import PaperMetadata
from app.schemas.method import MethodAnalysis
from app.schemas.reproduction import ReproductionPlan
from app.schemas.understanding import PaperUnderstanding


def _bullets(items: list[str]) -> str:
    if not items:
        return "- 未在当前 PDF 片段中明确提取到。\n"
    return "\n".join(f"- {item}" for item in items) + "\n"


def _checkboxes(items: list[str]) -> str:
    if not items:
        return "- [ ] 未生成 checklist。\n"
    return "\n".join(f"- [ ] {item}" for item in items) + "\n"


def _value(value: str) -> str:
    return value if value else "未在当前 PDF 片段中明确提取到。"


def build_markdown_report(
    metadata: PaperMetadata,
    classification: PaperTypeClassification,
    understanding: PaperUnderstanding,
    method: MethodAnalysis,
    experiments: ExperimentAnalysis,
    reproduction: ReproductionPlan,
) -> str:
    modules = "\n".join(
        "\n".join(
            [
                f"### {index}. {module.name}",
                f"- 职责：{_value(module.responsibility)}",
                f"- 输入：{', '.join(module.inputs) if module.inputs else '未明确'}",
                f"- 输出：{', '.join(module.outputs) if module.outputs else '未明确'}",
                f"- 实现要点：{'; '.join(module.implementation_notes) if module.implementation_notes else '未明确'}",
            ]
        )
        for index, module in enumerate(method.modules, start=1)
    ) or "未在当前 PDF 片段中明确拆出方法模块。"

    reproduction_modules = "\n".join(
        "\n".join(
            [
                f"### {index}. {module.name}",
                f"- 目的：{_value(module.purpose)}",
                f"- 输入：{', '.join(module.inputs) if module.inputs else '未明确'}",
                f"- 输出：{', '.join(module.outputs) if module.outputs else '未明确'}",
                f"- TODO：{'; '.join(module.todos) if module.todos else '未明确'}",
            ]
        )
        for index, module in enumerate(reproduction.required_modules, start=1)
    ) or "未生成必要模块。"

    datasets = "\n".join(
        f"- **{dataset.name}**：{dataset.role or '实验数据集'}；说明：{dataset.notes or '未明确'}"
        for dataset in experiments.datasets
    ) or "- 未在当前 PDF 片段中明确提取到数据集。\n"

    code_structure = "\n".join(
        f"- `{item.path}` ({item.type})：{item.purpose}；TODO：{item.todo}"
        for item in reproduction.code_structure
    ) or "- 未生成代码目录骨架。"

    steps = "\n".join(
        f"{step.step}. **{step.title}**：{step.description} 输出：{step.expected_output or '未明确'}"
        for step in reproduction.implementation_steps
    ) or "1. 未生成实现步骤。"

    risks = "\n".join(
        f"- **{risk.impact}**：{risk.risk}；缓解：{risk.mitigation or '未明确'}"
        for risk in reproduction.risk_points
    ) or "- 未识别风险点。"

    formulas = _bullets(method.key_formulas)
    dependencies = _bullets(method.implementation_dependencies)
    checklist = _checkboxes([item.item for item in reproduction.experiment_checklist])

    return f"""# {metadata.title}

> Paper2Repo 目标：先把论文读懂，再把论文拆成可执行的最小复现计划。以下内容基于 PDF 文本、章节标题和关键词检索生成；缺失项会明确标注，避免伪造实现细节。

## 1. 论文基本信息

- 标题：{metadata.title}
- 作者：{", ".join(metadata.authors) if metadata.authors else "未在当前 PDF 片段中明确提取到"}
- 方向：{classification.domain}
- 论文类型：{classification.paper_type}
- 推荐复现方式：{classification.reproduction_mode}
- 复现难度：{classification.difficulty}
- MVP 适配度：{classification.suitability_for_mvp}

### 类型判断依据
{_bullets(classification.reasons)}
### 可能资源需求
{_bullets(classification.required_resources)}
### 可能阻塞点
{_bullets(classification.likely_blockers)}

## 2. 读懂论文

### 研究背景
{_value(understanding.background)}

### 核心问题
{_value(understanding.core_problem)}

### 主要贡献
{_bullets(understanding.main_contributions)}
### 整体思路
{_value(understanding.overall_idea)}

### 结论
{_value(understanding.conclusion)}

### 局限性
{_bullets(understanding.limitations)}
### 适用场景
{_bullets(understanding.applicable_scenarios)}

## 3. 方法拆解

### 方法整体框架
{_value(method.system_framework or method.method_summary)}

### 方法概述
{_value(method.method_summary)}

### 关键模块、输入输出与实现要点
{modules}

### 算法流程
{_bullets([f"{step.step}. {step.name}: {step.description}" for step in method.algorithm_steps])}
### 关键公式
{formulas}
### 实现依赖
{dependencies}

## 4. 实验分析

### 数据集
{datasets}
### Baseline
{_bullets(experiments.baselines)}
### Metrics
{_bullets(experiments.metrics)}
### 实验设置 / 训练细节
{_bullets(experiments.training_details)}
### 评价协议
{_value(experiments.evaluation_protocol)}

### 主要结果
{_bullets(experiments.main_results)}
### 消融实验
{_bullets(experiments.ablation_studies)}

## 5. 复现规划

### 复现可行性
- 等级：{reproduction.feasibility_level}
- 说明：{_value(reproduction.feasibility_summary)}

### 最小复现目标
{_value(reproduction.minimum_reproduction_goal)}

### 复现范围
{_bullets(reproduction.reproduction_scope)}
### 必要模块
{reproduction_modules}

### 数据计划
{_bullets(reproduction.dataset_plan)}
### 评价计划
{_bullets(reproduction.evaluation_plan)}

### 建议代码目录骨架
{code_structure}

### 实现步骤
{steps}

### 风险点
{risks}

### 缺失信息
{_bullets(reproduction.missing_information)}
### 第一版简化策略
{_bullets(reproduction.suggested_simplifications)}

## 6. 实验 Checklist

{checklist}
"""
