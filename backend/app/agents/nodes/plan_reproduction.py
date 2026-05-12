from app.agents.state import PaperAnalysisState
from app.agents.prompts import COMMON_SYSTEM_PROMPT, PLAN_REPRODUCTION_PROMPT
from app.agents.nodes.node_utils import context_block, llm_or_fallback
from app.schemas.reproduction import (
    ChecklistItem,
    CodeStructureItem,
    ImplementationStep,
    ReproductionModule,
    ReproductionPlan,
    RiskPoint,
)
from app.services.retrieval import retrieve_context


def plan_reproduction_node(state: PaperAnalysisState) -> PaperAnalysisState:
    classification = state["classification"]
    chunks = state["chunked_paper"].chunks
    context = retrieve_context(
        chunks,
        query="implementation dataset code reproduce training evaluation",
        section_hints=["method", "experiment", "implementation", "evaluation"],
        keywords=["implementation", "dataset", "code", "training", "evaluation", "hyperparameter"],
        top_k=8,
    )

    feasibility_level = "medium"
    if classification.suitability_for_mvp == "good":
        feasibility_level = "high"
    elif classification.suitability_for_mvp == "poor" or classification.difficulty == "very_high":
        feasibility_level = "low"

    datasets = [dataset.name for dataset in state["experiment_analysis"].datasets]
    metrics = state["experiment_analysis"].metrics
    method_modules = state["method_analysis"].modules
    missing_info = [
        item
        for item in [
            "原论文代码仓库或关键实现细节" if not state["method_analysis"].implementation_dependencies else "",
            "数据集下载地址或数据预处理脚本" if not datasets else "",
            "完整超参数、随机种子和训练资源配置",
            "主实验表格中每个结果的精确复现实验命令",
        ]
        if item
    ]

    required_modules = [
        ReproductionModule(
            name="data_pipeline",
            purpose=f"加载并预处理论文实验数据：{', '.join(datasets) if datasets else '论文未明确给出数据集名称'}。",
            inputs=["raw data", "paper preprocessing rules"],
            outputs=["train/dev/test splits", "cached features"],
            todos=["确认数据来源", "实现最小数据读取", "保存可复现实验划分"],
        )
    ]
    for module in method_modules[:4]:
        required_modules.append(
            ReproductionModule(
                name=module.name,
                purpose=module.responsibility,
                inputs=module.inputs,
                outputs=module.outputs,
                todos=module.implementation_notes or ["根据方法章节补齐实现细节"],
            )
        )
    required_modules.append(
        ReproductionModule(
            name="evaluation",
            purpose=f"复现论文报告的评价指标：{', '.join(metrics) if metrics else '指标待确认'}。",
            inputs=["predictions", "labels or references"],
            outputs=["metrics table", "Markdown result summary"],
            todos=["实现指标计算", "对齐论文 evaluation protocol", "输出可比较结果"],
        )
    )

    fallback = ReproductionPlan(
        feasibility_summary=(
            f"该论文被归类为 {classification.domain}/{classification.paper_type}，建议复现方式为 "
            f"{classification.reproduction_mode}。第一版应优先复现一个小规模主实验闭环，而不是完整重跑全部实验。"
        ),
        feasibility_level=feasibility_level,
        minimum_reproduction_goal=(
            f"围绕 {', '.join(datasets[:3]) if datasets else '论文中的一个可获得数据集或 toy subset'}，"
            f"实现数据加载、核心方法、{', '.join(metrics[:3]) if metrics else '主要评价指标'} 计算和一份结果报告。"
        ),
        reproduction_scope=[
            "只选择一个主实验或最能代表论文方法的任务。",
            "优先跑通小数据集/小模型闭环，再考虑扩展到完整设置。",
            "保留消融实验为 TODO，不在第一轮实现全部变体。",
        ],
        required_modules=required_modules,
        dataset_plan=[
            f"优先确认并下载：{', '.join(datasets)}。" if datasets else "论文片段未明确给出数据集名称，先建立 toy dataset 以验证 pipeline。",
            "将数据预处理规则写入独立脚本，并缓存中间结果，便于后续替换真实数据。",
        ],
        evaluation_plan=[
            f"实现指标：{', '.join(metrics)}。" if metrics else "从论文实验表中确认主指标后再实现。",
            "输出与论文主结果表对应的 Markdown/CSV，记录差距和实验配置。",
        ],
        code_structure=[
            CodeStructureItem(path="README.md", type="file", purpose="记录复现目标、环境、数据和运行命令", todo="补充论文链接、数据路径、最小实验命令。"),
            CodeStructureItem(path="configs/default.yaml", type="file", purpose="集中管理数据、模型、训练和评价配置", todo="填入最小复现实验配置。"),
            CodeStructureItem(path="src/data.py", type="file", purpose="数据下载、读取、清洗和 split 构造", todo="实现 dataset adapter 和 toy fallback。"),
            CodeStructureItem(path="src/method.py", type="file", purpose="论文核心方法模块", todo="按方法拆解实现核心 forward/inference 流程。"),
            CodeStructureItem(path="src/train.py", type="file", purpose="训练或微调入口", todo="若复现方式需要训练，则实现最小训练循环。"),
            CodeStructureItem(path="src/evaluate.py", type="file", purpose="评价指标计算和结果导出", todo="实现论文主指标并输出结果表。"),
            CodeStructureItem(path="scripts/run_minimal.sh", type="file", purpose="一键运行最小复现实验", todo="串联 data/method/evaluate。"),
        ],
        implementation_steps=[
            ImplementationStep(step=1, title="锁定最小复现目标", description="从论文主实验中选择一个数据集、一个核心设置和一组主指标。", expected_output="明确的 target experiment。"),
            ImplementationStep(step=2, title="实现数据闭环", description="完成数据读取、预处理、split 和 toy fallback。", expected_output="可被训练/推理脚本读取的数据对象。"),
            ImplementationStep(step=3, title="实现核心方法", description="按方法模块拆解实现最小可运行版本，先保证输入输出对齐。", expected_output="可运行的 method pipeline。"),
            ImplementationStep(step=4, title="实现评价", description="实现论文主指标，并生成和论文结果表可对照的输出。", expected_output="metrics JSON/CSV/Markdown。"),
            ImplementationStep(step=5, title="记录差距与风险", description="记录无法复现的超参数、数据、模型权重或闭源依赖。", expected_output="复现日志和风险清单。"),
        ],
        experiment_checklist=[
            ChecklistItem(item="已确认最小复现实验对应的数据集/任务。"),
            ChecklistItem(item="已实现数据读取和预处理脚本。"),
            ChecklistItem(item="已实现核心方法的输入输出接口。"),
            ChecklistItem(item="已实现论文主评价指标。"),
            ChecklistItem(item="已提供一键运行命令。"),
            ChecklistItem(item="已记录与论文结果的差距和原因。"),
        ],
        risk_points=[
            RiskPoint(risk="论文可能没有给出完整超参数或随机种子。", impact="medium", mitigation="将所有假设写入配置文件，并做小规模敏感性测试。"),
            RiskPoint(risk="数据集、模型权重或标注规则可能不可获得。", impact="high", mitigation="准备 toy fallback 或公开替代数据，只承诺最小闭环复现。"),
            RiskPoint(risk="完整实验可能依赖较高算力。", impact="medium", mitigation="优先 inference/small subset，再扩展训练规模。"),
        ],
        missing_information=missing_info,
        suggested_simplifications=["使用小数据子集", "优先跑 inference-only 或单 epoch", "先跳过昂贵消融实验", "用配置文件固定所有假设"],
    )
    plan, _used_llm = llm_or_fallback(
        system_prompt=COMMON_SYSTEM_PROMPT,
        task_prompt=PLAN_REPRODUCTION_PROMPT,
        schema_model=ReproductionPlan,
        fallback=fallback,
        context=context_block(context),
        extra=(
            f"Paper metadata: {state['metadata'].model_dump_json()}\n"
            f"Classification: {classification.model_dump_json()}\n"
            f"Understanding: {state['understanding'].model_dump_json()}\n"
            f"Method analysis: {state['method_analysis'].model_dump_json()}\n"
            f"Experiment analysis: {state['experiment_analysis'].model_dump_json()}"
        ),
        model_name=state.get("model_name"),
    )
    return {"reproduction_plan": plan, "status": "reproduction_planned"}
