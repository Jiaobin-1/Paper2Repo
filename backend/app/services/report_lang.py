from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lang:
    lang_code: str
    # fallbacks
    no_items: str
    no_checklist: str
    no_value: str
    # evidence / missing table headers
    ev_claim: str
    ev_location: str
    ev_section: str
    ev_quote: str
    ev_no_claim: str
    ev_no_location: str
    ev_no_section: str
    ev_no_quote: str
    ev_empty_row: str
    ms_category: str
    ms_severity: str
    ms_gap: str
    ms_action: str
    ms_empty_row: list[str]
    # experiment matrix headers
    mx_target: str
    mx_dataset: str
    mx_baseline: str
    mx_metric: str
    mx_protocol: str
    mx_result: str
    mx_status: str
    mx_gaps: str
    mx_empty_row: list[str]
    # reading tasks
    rt_no_evidence: str
    rt_next_fallback: str
    rt_empty: str
    # label maps
    status_labels: dict[str, str] = field(default_factory=dict)
    level_labels: dict[str, str] = field(default_factory=dict)
    paper_type_labels: dict[str, str] = field(default_factory=dict)
    reproduction_mode_labels: dict[str, str] = field(default_factory=dict)
    item_type_labels: dict[str, str] = field(default_factory=dict)
    priority_labels: dict[str, str] = field(default_factory=dict)
    # section headers
    h_audit: str = ""
    h_repro_level: str = ""
    h_audit_summary: str = ""
    h_first_step: str = ""
    h_biggest_blocker: str = ""
    h_confidence: str = ""
    h_blocking_gaps: str = ""
    h_evidence_map: str = ""
    h_metadata: str = ""
    h_title: str = ""
    h_authors: str = ""
    h_domain: str = ""
    h_paper_type: str = ""
    h_repro_mode: str = ""
    h_difficulty: str = ""
    h_mvp_suitability: str = ""
    h_class_reasons: str = ""
    h_resources: str = ""
    h_blockers: str = ""
    h_understanding: str = ""
    h_background: str = ""
    h_core_problem: str = ""
    h_contributions: str = ""
    h_overall_idea: str = ""
    h_conclusion: str = ""
    h_limitations: str = ""
    h_scenarios: str = ""
    h_assumptions: str = ""
    h_reading_checklist: str = ""
    h_understanding_gaps: str = ""
    h_method: str = ""
    h_framework: str = ""
    h_method_summary: str = ""
    h_modules: str = ""
    h_algorithm: str = ""
    h_formulas: str = ""
    h_formula_gaps: str = ""
    h_interfaces: str = ""
    h_dependencies: str = ""
    h_method_gaps: str = ""
    h_experiments: str = ""
    h_matrix: str = ""
    h_datasets: str = ""
    h_baselines: str = ""
    h_metrics: str = ""
    h_training: str = ""
    h_eval_protocol: str = ""
    h_main_results: str = ""
    h_ablation: str = ""
    h_experiment_gaps: str = ""
    h_plan: str = ""
    h_feasibility: str = ""
    h_feasibility_level: str = ""
    h_feasibility_summary: str = ""
    h_difficulty_breakdown: str = ""
    h_dependency_difficulty: str = ""
    h_data_difficulty: str = ""
    h_compute_difficulty: str = ""
    h_implementation_difficulty: str = ""
    h_min_goal: str = ""
    h_first_exp: str = ""
    h_scope: str = ""
    h_req_modules: str = ""
    h_dataset_plan: str = ""
    h_eval_plan: str = ""
    h_code_skeleton: str = ""
    h_impl_steps: str = ""
    h_acceptance: str = ""
    h_risks: str = ""
    h_missing_info: str = ""
    h_simplifications: str = ""
    h_checklist: str = ""
    # module fields
    m_responsibility: str = ""
    m_inputs: str = ""
    m_outputs: str = ""
    m_priority: str = ""
    m_contract: str = ""
    m_notes: str = ""
    m_not_specified: str = ""
    # reproduction module fields
    rm_purpose: str = ""
    rm_todos: str = ""
    # dataset / code / step / risk fields
    ds_role_default: str = ""
    ds_notes_label: str = ""
    cd_todo_label: str = ""
    st_output_label: str = ""
    rk_mitigation_label: str = ""
    # intro paragraph
    intro: str = ""
    # blockers default
    no_blockers: str = ""
    # no modules / no repro modules / no datasets / no code / no steps / no risks
    no_modules: str = ""
    no_repro_modules: str = ""
    no_datasets: str = ""
    no_code: str = ""
    no_steps: str = ""
    no_risks: str = ""


ZH = Lang(
    lang_code="zh",
    no_items="- 未在当前 PDF 片段中明确提取到。\n",
    no_checklist="- [ ] 未生成检查清单。\n",
    no_value="未在当前 PDF 片段中明确提取到。",
    ev_claim="结论", ev_location="位置", ev_section="章节", ev_quote="摘录",
    ev_no_claim="未标注", ev_no_location="未知页码", ev_no_section="未知章节", ev_no_quote="未截取到原文",
    ev_empty_row="| 未找到明确证据 | - | - | - | - |\n",
    ms_category="类别", ms_severity="严重度", ms_gap="缺口", ms_action="建议动作",
    ms_empty_row=["暂未识别", "-", "当前片段未识别到明确阻塞缺口", "复现前仍需人工快速核查"],
    mx_target="目标", mx_dataset="数据集", mx_baseline="基线方法", mx_metric="指标",
    mx_protocol="协议", mx_result="论文结果", mx_status="状态", mx_gaps="缺口",
    mx_empty_row=["未生成", "-", "-", "-", "-", "-", "受阻", "未生成实验矩阵"],
    rt_no_evidence="未绑定证据", rt_next_fallback="继续核查原文", rt_empty="- [ ] 未生成读懂论文任务清单。\n",
    status_labels={"confirmed": "已确认", "unclear": "不明确", "missing": "缺失", "partial": "部分可复现", "blocked": "受阻", "faithful": "可忠实复现", "sanity_check": "只能做合理性检查"},
    level_labels={"high": "高", "medium": "中", "low": "低", "very_high": "很高", "good": "较好", "partial": "部分适配", "poor": "较差"},
    paper_type_labels={"experimental": "实验型", "system": "系统型", "benchmark": "基准评测型", "dataset": "数据集型", "theoretical": "理论型", "survey": "综述型"},
    reproduction_mode_labels={"training_from_scratch": "从零训练", "fine_tuning": "微调复现", "inference_pipeline": "推理流程复现", "benchmark_evaluation": "基准评测复现", "ablation_reproduction": "消融实验复现", "not_recommended": "不建议复现"},
    item_type_labels={"file": "文件", "directory": "目录"},
    priority_labels={"must": "必须实现", "should": "建议实现", "optional": "可选"},
    h_audit="## 0. 复现审计摘要",
    h_repro_level="可复现等级", h_audit_summary="审计结论", h_first_step="推荐第一步",
    h_biggest_blocker="最大阻塞", h_confidence="可信度",
    h_blocking_gaps="### 阻塞缺口审计", h_evidence_map="### 证据地图",
    h_metadata="## 1. 论文基本信息", h_title="标题", h_authors="作者",
    h_domain="方向", h_paper_type="论文类型", h_repro_mode="推荐复现方式",
    h_difficulty="复现难度", h_mvp_suitability="最小版本适配度",
    h_class_reasons="### 类型判断依据", h_resources="### 可能资源需求", h_blockers="### 可能阻塞点",
    h_understanding="## 2. 读懂论文", h_background="### 研究背景", h_core_problem="### 核心问题",
    h_contributions="### 主要贡献", h_overall_idea="### 整体思路", h_conclusion="### 结论",
    h_limitations="### 局限性", h_scenarios="### 适用场景", h_assumptions="### 关键假设",
    h_reading_checklist="### 读懂论文任务清单", h_understanding_gaps="### 读懂阶段缺失项",
    h_method="## 3. 方法拆解", h_framework="### 方法整体框架", h_method_summary="### 方法概述",
    h_modules="### 关键模块、输入输出与实现要点", h_algorithm="### 算法流程",
    h_formulas="### 关键公式", h_formula_gaps="### 公式 / 伪代码缺口",
    h_interfaces="### 实现接口", h_dependencies="### 实现依赖", h_method_gaps="### 方法阶段缺失项",
    h_experiments="## 4. 实验分析", h_matrix="### 实验复现矩阵", h_datasets="### 数据集",
    h_baselines="### 基线方法", h_metrics="### 评价指标", h_training="### 实验设置 / 训练细节",
    h_eval_protocol="### 评价协议", h_main_results="### 主要结果", h_ablation="### 消融实验",
    h_experiment_gaps="### 实验阶段缺失项",
    h_plan="## 5. 复现规划", h_feasibility="### 复现可行性", h_feasibility_level="等级",
    h_feasibility_summary="说明", h_difficulty_breakdown="### 复现难度拆解",
    h_dependency_difficulty="依赖可得性", h_data_difficulty="数据可得性",
    h_compute_difficulty="算力成本", h_implementation_difficulty="实现复杂度",
    h_min_goal="### 最小复现目标", h_first_exp="### 推荐第一项实验",
    h_scope="### 复现范围", h_req_modules="### 必要模块", h_dataset_plan="### 数据计划",
    h_eval_plan="### 评价计划", h_code_skeleton="### 建议代码目录骨架", h_impl_steps="### 实现步骤",
    h_acceptance="### 验收标准", h_risks="### 风险点", h_missing_info="### 缺失信息",
    h_simplifications="### 第一版简化策略", h_checklist="## 6. 实验检查清单",
    m_responsibility="职责", m_inputs="输入", m_outputs="输出", m_priority="优先级",
    m_contract="接口契约", m_notes="实现要点", m_not_specified="未明确",
    rm_purpose="目的", rm_todos="待办",
    ds_role_default="实验数据集", ds_notes_label="说明",
    cd_todo_label="待办", st_output_label="输出", rk_mitigation_label="缓解",
    intro="> Paper2Repo 目标：先把论文读懂，再把论文拆成可执行的最小复现计划。以下内容基于 PDF 文本、章节标题和关键词检索生成；缺失项会明确标注，避免伪造实现细节。",
    no_blockers="当前片段未识别到明确高优先级阻塞。",
    no_modules="未在当前 PDF 片段中明确拆出方法模块。",
    no_repro_modules="未生成必要模块。",
    no_datasets="- 未在当前 PDF 片段中明确提取到数据集。\n",
    no_code="未生成代码目录骨架。",
    no_steps="1. 未生成实现步骤。",
    no_risks="未识别风险点。",
)

EN = Lang(
    lang_code="en",
    no_items="- Not clearly extracted from the current PDF context.\n",
    no_checklist="- [ ] No checklist was generated.\n",
    no_value="Not clearly extracted from the current PDF context.",
    ev_claim="Claim", ev_location="Location", ev_section="Section", ev_quote="Quote",
    ev_no_claim="Not labeled", ev_no_location="Unknown page", ev_no_section="Unknown section", ev_no_quote="No quote extracted",
    ev_empty_row="| No clear evidence found | - | - | - | - |\n",
    ms_category="Category", ms_severity="Severity", ms_gap="Gap", ms_action="Suggested action",
    ms_empty_row=["Not identified", "-", "No explicit blocking gap was identified in the current context", "Still perform a quick manual check before reproduction"],
    mx_target="Target", mx_dataset="Dataset", mx_baseline="Baseline", mx_metric="Metric",
    mx_protocol="Protocol", mx_result="Reported result", mx_status="Status", mx_gaps="Gaps",
    mx_empty_row=["Not generated", "-", "-", "-", "-", "-", "blocked", "No experiment matrix was generated"],
    rt_no_evidence="No linked evidence", rt_next_fallback="Keep checking the paper text", rt_empty="- [ ] No reading checklist was generated.\n",
    status_labels={},
    level_labels={},
    paper_type_labels={},
    reproduction_mode_labels={},
    item_type_labels={},
    priority_labels={"must": "Must implement", "should": "Should implement", "optional": "Optional"},
    h_audit="## 0. Reproduction Audit Summary",
    h_repro_level="Reproducibility level", h_audit_summary="Audit summary", h_first_step="Recommended first step",
    h_biggest_blocker="Biggest blocker", h_confidence="Confidence",
    h_blocking_gaps="### Blocking Gaps", h_evidence_map="### Evidence Map",
    h_metadata="## 1. Paper Metadata", h_title="Title", h_authors="Authors",
    h_domain="Domain", h_paper_type="Paper type", h_repro_mode="Recommended reproduction mode",
    h_difficulty="Reproduction difficulty", h_mvp_suitability="MVP suitability",
    h_class_reasons="### Classification Rationale", h_resources="### Likely Resource Needs", h_blockers="### Likely Blockers",
    h_understanding="## 2. Paper Understanding", h_background="### Background", h_core_problem="### Core Problem",
    h_contributions="### Main Contributions", h_overall_idea="### Overall Idea", h_conclusion="### Conclusion",
    h_limitations="### Limitations", h_scenarios="### Applicable Scenarios", h_assumptions="### Key Assumptions",
    h_reading_checklist="### Reading Checklist", h_understanding_gaps="### Understanding Gaps",
    h_method="## 3. Method Breakdown", h_framework="### Overall Framework", h_method_summary="### Method Summary",
    h_modules="### Key Modules, I/O, and Implementation Notes", h_algorithm="### Algorithm Flow",
    h_formulas="### Key Formulas", h_formula_gaps="### Formula / Pseudocode Gaps",
    h_interfaces="### Implementation Interfaces", h_dependencies="### Implementation Dependencies", h_method_gaps="### Method Gaps",
    h_experiments="## 4. Experiment Analysis", h_matrix="### Experiment Reproduction Matrix", h_datasets="### Datasets",
    h_baselines="### Baselines", h_metrics="### Metrics", h_training="### Settings / Training Details",
    h_eval_protocol="### Evaluation Protocol", h_main_results="### Main Results", h_ablation="### Ablation Studies",
    h_experiment_gaps="### Experiment Gaps",
    h_plan="## 5. Reproduction Plan", h_feasibility="### Feasibility", h_feasibility_level="Level",
    h_feasibility_summary="Summary", h_difficulty_breakdown="### Difficulty Breakdown",
    h_dependency_difficulty="Dependency Availability", h_data_difficulty="Data Availability",
    h_compute_difficulty="Compute Cost", h_implementation_difficulty="Implementation Complexity",
    h_min_goal="### Minimum Reproduction Goal", h_first_exp="### Recommended First Experiment",
    h_scope="### Scope", h_req_modules="### Required Modules", h_dataset_plan="### Dataset Plan",
    h_eval_plan="### Evaluation Plan", h_code_skeleton="### Suggested Code Skeleton", h_impl_steps="### Implementation Steps",
    h_acceptance="### Acceptance Criteria", h_risks="### Risks", h_missing_info="### Missing Information",
    h_simplifications="### First-Version Simplifications", h_checklist="## 6. Experiment Checklist",
    m_responsibility="Responsibility", m_inputs="Inputs", m_outputs="Outputs", m_priority="Priority",
    m_contract="Interface contract", m_notes="Implementation notes", m_not_specified="Not specified",
    rm_purpose="Purpose", rm_todos="To do",
    ds_role_default="experimental dataset", ds_notes_label="notes",
    cd_todo_label="to do", st_output_label="Output", rk_mitigation_label="mitigation",
    intro="> Paper2Repo goal: understand the paper first, then turn it into an executable minimal reproduction plan. This report is generated from PDF text, section-aware retrieval, and keyword retrieval. Missing details are marked explicitly to avoid inventing implementation facts.",
    no_blockers="No clear high-priority blocker was identified in the current context.",
    no_modules="No method modules were clearly identified in the current PDF context.",
    no_repro_modules="No required reproduction modules were generated.",
    no_datasets="- No dataset was clearly extracted from the current PDF context.\n",
    no_code="No code skeleton was generated.",
    no_steps="1. No implementation steps were generated.",
    no_risks="No risk points were identified.",
)
